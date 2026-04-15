"""WebSocket 端点 — 诊断进度实时推送。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.api.deps import manager, get_graph_app, progress_cache, running_tasks
from src.core.diagnosis_errors import public_diagnosis_error_message
from src.worker.arq_queue import enqueue_adoption_job
from src.services import async_job_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/diagnosis/{thread_id}")
async def ws_diagnosis(websocket: WebSocket, thread_id: str):
    """
    WebSocket 端点: 实时接收诊断进度。
    客户端也可通过此连接发送采纳方案指令。
    """
    await manager.connect(thread_id, websocket)

    # 重连时发送缓存的进度
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
                    app = await get_graph_app()
                    config = {"configurable": {"thread_id": thread_id}}

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
                        await app.aupdate_state(config, {"adopted_plan_ids": []})
                        await manager.send_progress(
                            thread_id,
                            {
                                "type": "adoption_received",
                                "message": "未采纳任何方案",
                            },
                        )
                        continue

                    pid = plan_ids[0]
                    state = await app.aget_state(config)
                    if not (state.next and "wait_adoption" in state.next):
                        await manager.send_progress(
                            thread_id,
                            {
                                "type": "error",
                                "message": "该诊断不在待采纳状态",
                            },
                        )
                        continue
                    all_plan_ids = {p.get("plan_id") for p in (state.values.get("solution_plans") or [])}
                    if pid not in all_plan_ids:
                        await manager.send_progress(
                            thread_id,
                            {
                                "type": "error",
                                "message": f"无效的 plan_id: {pid}",
                            },
                        )
                        continue

                    existing = (state.values.get("adopted_plan_ids") or [])[:1]
                    if existing and existing[0] != pid:
                        await manager.send_progress(
                            thread_id,
                            {
                                "type": "error",
                                "message": "已有方案被采纳，不可再采纳其他方案",
                            },
                        )
                        continue

                    await app.aupdate_state(config, {"adopted_plan_ids": [pid]})
                    await manager.send_progress(
                        thread_id,
                        {
                            "type": "adoption_received",
                            "message": "已采纳方案，开始执行...",
                        },
                    )
                    tenant_id = str((state.values or {}).get("tenant_id") or "")
                    if not tenant_id:
                        await manager.send_progress(
                            thread_id,
                            {
                                "type": "error",
                                "message": "缺少 tenant_id，无法派发执行任务",
                            },
                        )
                        continue
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
