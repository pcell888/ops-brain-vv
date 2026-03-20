"""前端兼容层 — /ws/tasks/{enterpriseId} 企业级 WebSocket。

前端按企业 ID 订阅所有任务进度，后端按 thread_id 推送。
此模块桥接两者：维护 enterprise→websocket 映射，将诊断进度转换为前端 TaskStatusMessage 格式。
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.api.deps import manager as diagnosis_ws_manager, running_tasks

logger = logging.getLogger(__name__)
router = APIRouter()


class EnterpriseWSManager:
    """企业级 WebSocket 连接管理器。"""

    def __init__(self):
        self.connections: dict[str, set[WebSocket]] = {}

    async def connect(self, enterprise_id: str, ws: WebSocket):
        await ws.accept()
        self.connections.setdefault(enterprise_id, set()).add(ws)

    def disconnect(self, enterprise_id: str, ws: WebSocket):
        conns = self.connections.get(enterprise_id)
        if conns:
            conns.discard(ws)
            if not conns:
                del self.connections[enterprise_id]

    async def broadcast(self, enterprise_id: str, message: dict):
        conns = self.connections.get(enterprise_id)
        if not conns:
            return
        dead = []
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            conns.discard(ws)


enterprise_ws = EnterpriseWSManager()


def _progress_to_task_status(
    thread_id: str,
    enterprise_id: str,
    raw: dict,
) -> dict | None:
    """将诊断 WebSocket 原始消息转换为前端 TaskStatusMessage。"""
    msg_type = raw.get("type", "")

    if msg_type in ("progress", "node_start"):
        percent = raw.get("percent", 0)
        try:
            percent = int(float(percent)) if percent is not None else 0
        except (TypeError, ValueError):
            percent = 0
        return {
            "type": "task_status",
            "task_type": "diagnosis",
            "task_id": thread_id,
            "enterprise_id": enterprise_id,
            "status": "running",
            "progress": percent,
            "message": raw.get("message"),
            "data": None,
        }

    if msg_type == "node_complete":
        percent = raw.get("percent", 0)
        try:
            percent = int(float(percent)) if percent is not None else 0
        except (TypeError, ValueError):
            percent = 0
        return {
            "type": "task_status",
            "task_type": "diagnosis",
            "task_id": thread_id,
            "enterprise_id": enterprise_id,
            "status": "running",
            "progress": percent,
            "message": raw.get("message") or f"节点 {raw.get('node', '')} 完成",
            "data": None,
        }

    if msg_type == "diagnosis_result":
        return {
            "type": "task_status",
            "task_type": "diagnosis",
            "task_id": thread_id,
            "enterprise_id": enterprise_id,
            "status": "running",
            "progress": 70,
            "message": f"诊断完成，健康度 {raw.get('health_score', 0):.1f}分",
            "data": {
                "health_score": raw.get("health_score"),
                "anomaly_count": raw.get("anomaly_count"),
            },
        }

    if msg_type == "completed":
        return {
            "type": "task_status",
            "task_type": "diagnosis",
            "task_id": thread_id,
            "enterprise_id": enterprise_id,
            "status": "completed",
            "progress": 100,
            "message": raw.get("message", "诊断完成"),
            "data": None,
        }

    if msg_type == "error":
        return {
            "type": "task_status",
            "task_type": "diagnosis",
            "task_id": thread_id,
            "enterprise_id": enterprise_id,
            "status": "failed",
            "progress": 0,
            "message": raw.get("message", "诊断失败"),
            "data": None,
        }

    if msg_type == "cancelled":
        return {
            "type": "task_status",
            "task_type": "diagnosis",
            "task_id": thread_id,
            "enterprise_id": enterprise_id,
            "status": "failed",
            "progress": 0,
            "message": "已取消",
            "data": None,
        }

    if msg_type == "solutions_ready":
        return {
            "type": "task_status",
            "task_type": "solution",
            "task_id": thread_id,
            "enterprise_id": enterprise_id,
            "status": "completed",
            "progress": 100,
            "message": "方案已生成",
            "data": {"plans": raw.get("plans")},
        }

    return None


def install_enterprise_bridge(original_manager):
    """猴子补丁：在原始 diagnosis WS manager 的 send_progress 上挂钩，
    将消息同时广播到企业级 WebSocket。"""
    _original_send = original_manager.send_progress

    async def _bridged_send(thread_id: str, message: dict):
        await _original_send(thread_id, message)

        enterprise_id = _thread_to_enterprise.get(thread_id)
        if enterprise_id:
            converted = _progress_to_task_status(thread_id, enterprise_id, message)
            if converted:
                await enterprise_ws.broadcast(enterprise_id, converted)

    original_manager.send_progress = _bridged_send


_thread_to_enterprise: dict[str, str] = {}


def register_thread_enterprise(thread_id: str, enterprise_id: str):
    """注册 thread_id → enterprise_id 映射（启动诊断时调用）。"""
    _thread_to_enterprise[thread_id] = enterprise_id


def get_thread_enterprise(thread_id: str) -> str | None:
    """获取 thread_id 对应的 enterprise_id。"""
    return _thread_to_enterprise.get(thread_id)


def get_running_threads_for_enterprise(enterprise_id: str) -> list[str]:
    """返回属于指定 enterprise 的所有正在运行的 thread_id 列表。"""
    return [tid for tid, eid in _thread_to_enterprise.items() if eid == enterprise_id]


def unregister_thread(thread_id: str):
    _thread_to_enterprise.pop(thread_id, None)


@router.websocket("/ws/tasks/{enterprise_id}")
async def ws_enterprise_tasks(websocket: WebSocket, enterprise_id: str):
    """企业级 WebSocket：前端按 enterpriseId 订阅所有任务进度。"""
    await enterprise_ws.connect(enterprise_id, websocket)

    await websocket.send_json({
        "type": "connected",
        "message": f"已连接到企业 {enterprise_id} 的任务通道",
    })

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except (json.JSONDecodeError, TypeError):
                msg = {}

            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg.get("type") == "heartbeat":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        enterprise_ws.disconnect(enterprise_id, websocket)
    except Exception as e:
        logger.error("Enterprise WS error for %s: %s", enterprise_id, e)
        enterprise_ws.disconnect(enterprise_id, websocket)
