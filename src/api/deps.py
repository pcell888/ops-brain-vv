"""FastAPI 依赖 — 从 runtime 再导出，供路由 Depends 使用。"""

from __future__ import annotations

from src.runtime.diagnosis_ws_manager import ConnectionManager, manager, send_thread_progress
from src.runtime.graph_app import generate_thread_id
from src.runtime.progress_store import ProgressStore, progress_cache, write_progress_cache
from src.runtime.running_tasks import RunningTaskStore, running_tasks

__all__ = [
    "ProgressStore",
    "RunningTaskStore",
    "ConnectionManager",
    "manager",
    "send_thread_progress",
    "progress_cache",
    "write_progress_cache",
    "running_tasks",
    "generate_thread_id",
]
