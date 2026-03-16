"""WebSocket 端点 — 诊断进度实时推送。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.api.deps import manager, get_graph_app

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/diagnosis/{thread_id}")
async def ws_diagnosis(websocket: WebSocket, thread_id: str):
    """
    WebSocket 端点: 实时接收诊断进度。
    客户端也可通过此连接发送采纳方案指令。
    """
    await manager.connect(thread_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()

            if data.get("action") == "adopt_plans":
                plan_ids = data.get("plan_ids", []) or []
                try:
                    app = await get_graph_app()
                    config = {"configurable": {"thread_id": thread_id}}
                    await app.aupdate_state(config, {"adopted_plan_ids": plan_ids})
                    await manager.send_progress(thread_id, {
                        "type": "adoption_received",
                        "message": f"已采纳 {len(plan_ids)} 个方案，开始执行...",
                    })
                    if plan_ids:
                        import asyncio
                        from src.api.routes.solutions import _resume_after_adoption
                        asyncio.create_task(_resume_after_adoption(thread_id, config))
                except Exception as e:
                    logger.exception("采纳方案失败: %s", e)
                    await manager.send_progress(thread_id, {
                        "type": "error",
                        "message": f"采纳失败: {str(e)}",
                    })

            elif data.get("action") == "ping":
                await manager.send_progress(thread_id, {"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(thread_id)
    except Exception as e:
        logger.error("WebSocket error for %s: %s", thread_id, e)
        manager.disconnect(thread_id)
