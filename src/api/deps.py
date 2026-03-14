"""FastAPI 依赖注入 — 提供 LangGraph app 单例和 WebSocket 连接管理。"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import WebSocket


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

_graph_app = None


async def get_graph_app():
    global _graph_app
    if _graph_app is None:
        from src.agent.graph import compile_graph
        _graph_app = await compile_graph()
    return _graph_app


def generate_thread_id() -> str:
    return f"diag_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
