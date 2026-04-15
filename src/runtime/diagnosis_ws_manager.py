"""按 thread_id 绑定的诊断 WebSocket 管理器与进度推送。"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import WebSocket

from src.core.config import CN_TZ
from src.runtime.progress_store import progress_cache

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 连接管理器。"""

    def __init__(self):
        self.active: dict[str, WebSocket] = {}

    async def connect(self, thread_id: str, ws: WebSocket):
        await ws.accept()
        self.active[thread_id] = ws

    def disconnect(self, thread_id: str):
        self.active.pop(thread_id, None)

    async def send_progress(self, thread_id: str, message: dict):
        ws = self.active.get(thread_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(thread_id)


manager = ConnectionManager()


async def send_thread_progress(thread_id: str, payload: dict) -> None:
    """写入 progress_cache 并推送到该 thread 的 WebSocket（重连可读缓存）。"""
    data = dict(payload)
    data["timestamp"] = datetime.now(CN_TZ).isoformat()
    await progress_cache.aset(thread_id, data)
    await manager.send_progress(thread_id, data)
