"""进度相关小工具 — 提取真正重复的代码模式。"""

from __future__ import annotations

from typing import Any

from src.runtime.running_tasks import running_tasks


async def is_thread_running_full(thread_id: str) -> bool:
    task = running_tasks.get(thread_id)
    return (task is not None and not task.done()) or await running_tasks.is_running(thread_id)


def safe_percent(value: Any) -> int:
    try:
        return max(0, min(100, int(float(value))))
    except (TypeError, ValueError):
        return 0
