"""WebSocket 端点 — 诊断进度实时推送。"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.api.deps import manager, progress_cache, running_tasks
from src.repositories.diagnosis_session import update_session_state
from src.repositories.tenant_registry import get_tenant_row
from src.runtime.task_runner import get_graph_state_values
from src.core.diagnosis_errors import public_diagnosis_error_message
from src.biz.client import tenant_client
from src.worker.arq_queue import enqueue_adoption_job
from src.services import async_job_service
from src.runtime.thread_enterprise import get_thread_enterprise

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
        level = raw.get("level")
        is_fatal = level == "error"
        data = None
        if level and level != "info":
            data = {"level": level}
        return {
            "type": "task_status",
            "task_type": "diagnosis",
            "task_id": thread_id,
            "enterprise_id": enterprise_id,
            "status": "failed" if is_fatal else "running",
            "progress": 0 if is_fatal else percent,
            "message": raw.get("message"),
            "data": data,
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

        enterprise_id = get_thread_enterprise(thread_id)
        if enterprise_id:
            converted = _progress_to_task_status(thread_id, enterprise_id, message)
            if converted:
                await enterprise_ws.broadcast(enterprise_id, converted)

    original_manager.send_progress = _bridged_send


@router.websocket("/ws/diagnosis/{thread_id}")
async def ws_diagnosis(websocket: WebSocket, thread_id: str):
    """
    WebSocket 端点: 实时接收诊断进度。
    客户端也可通过此连接发送采纳方案指令。
    """
    await manager.connect(thread_id, websocket)

    cached = await progress_cache.aget(thread_id)
    if cached:
        try:
            await websocket.send_json(cached)
        except Exception:
            pass

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("action") == "adopt_plans":
                try:
                    if data.get("plan_id"):
                        plan_ids = [str(data["plan_id"]).strip()]
                    else:
                        raw = data.get("plan_ids", []) or []
                        plan_ids = [str(x).strip() for x in raw if str(x).strip()]

                    if len(plan_ids) > 1:
                        await manager.send_progress(
                            thread_id,
                            {
                                "type": "error",
                                "message": "仅能采纳一个方案（互斥）",
                            },
                        )
                        continue

                    if not plan_ids:
                        await update_session_state(thread_id, {"adopted_plan_ids": []})
                        await manager.send_progress(
                            thread_id,
                            {
                                "type": "adoption_received",
                                "message": "未采纳任何方案",
                            },
                        )
                        continue

                    pid = plan_ids[0]
                    values, next_nodes = await get_graph_state_values(thread_id)
                    if "wait_adoption" not in next_nodes:
                        await manager.send_progress(
                            thread_id,
                            {
                                "type": "error",
                                "message": "该诊断不在待采纳状态",
                            },
                        )
                        continue
                    all_plan_ids = {p.get("plan_id") for p in (values.get("solution_plans") or [])}
                    if pid not in all_plan_ids:
                        await manager.send_progress(
                            thread_id,
                            {
                                "type": "error",
                                "message": f"无效的 plan_id: {pid}",
                            },
                        )
                        continue

                    existing = (values.get("adopted_plan_ids") or [])[:1]
                    if existing and existing[0] != pid:
                        await manager.send_progress(
                            thread_id,
                            {
                                "type": "error",
                                "message": "已有方案被采纳，不可再采纳其他方案",
                            },
                        )
                        continue

                    await update_session_state(thread_id, {"adopted_plan_ids": [pid]})
                    await manager.send_progress(
                        thread_id,
                        {
                            "type": "adoption_received",
                            "message": "已采纳方案，开始执行...",
                        },
                    )
                    tenant_id = str(values.get("tenant_id") or "")
                    if not tenant_id:
                        await manager.send_progress(
                            thread_id,
                            {
                                "type": "error",
                                "message": "缺少 tenant_id，无法派发执行任务",
                            },
                        )
                        continue
                    try:
                        tenant_row = await get_tenant_row(tenant_id)
                        reg_user_id = (tenant_row or {}).get("user_id")
                        if reg_user_id:
                            tc = tenant_client(tenant_id)
                            perm = await tc.has_create_task_permission(tenant_id=tenant_id, user_id=reg_user_id)
                            if not perm.get("has_permission"):
                                await manager.send_progress(
                                    thread_id,
                                    {
                                        "type": "error",
                                        "message": "请联系业务系统管理员赋予您创建任务的权限",
                                    },
                                )
                                continue
                    except Exception as e:
                        logger.warning("WS 采纳权限检查失败 tenant_id=%s: %s", tenant_id, e)
                    job_id = await enqueue_adoption_job(thread_id=thread_id)
                    await async_job_service.register_enqueued_job(
                        job_id=job_id,
                        thread_id=thread_id,
                        tenant_id=tenant_id,
                        job_kind="adoption",
                        payload={"thread_id": thread_id},
                    )
                    await running_tasks.register_job(thread_id, tenant_id, job_id)
                except Exception as e:
                    logger.exception("采纳方案失败 thread_id=%s", thread_id)
                    await manager.send_progress(
                        thread_id,
                        {
                            "type": "error",
                            "message": public_diagnosis_error_message(e),
                        },
                    )

            elif data.get("action") == "ping":
                await manager.send_progress(thread_id, {"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(thread_id)
    except Exception:
        logger.exception("WebSocket error for thread_id=%s", thread_id)
        manager.disconnect(thread_id)


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
    except Exception:
        logger.exception("Enterprise WS error enterprise_id=%s", enterprise_id)
        enterprise_ws.disconnect(enterprise_id, websocket)
