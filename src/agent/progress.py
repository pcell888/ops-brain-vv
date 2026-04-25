"""进度推送 — emit_progress + progress_sender ContextVar。"""

from __future__ import annotations

import asyncio
import logging
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Callable

from src.core.config import CN_TZ

logger = logging.getLogger(__name__)

ProgressCacheWriter = Callable[[str, dict[str, Any]], None]

_progress_sender: ContextVar[tuple[str, Any, ProgressCacheWriter | None] | None] = ContextVar("progress_sender", default=None)


def set_progress_sender(
    thread_id: str,
    manager: Any,
    cache_writer: ProgressCacheWriter | None = None,
) -> None:
    _progress_sender.set((thread_id, manager, cache_writer))


def clear_progress_sender() -> None:
    _progress_sender.set(None)


def emit_progress(
    state: dict,
    message: str,
    percent: int | float | None = None,
    level: str = "info",
    *,
    for_adoption_ui: bool = True,
):
    state.setdefault("progress_messages", [])
    ts = datetime.now(CN_TZ).isoformat()
    payload: dict[str, Any] = {
        "type": "human",
        "content": message,
        "timestamp": ts,
    }
    if percent is not None:
        payload["percent"] = percent
    if level and level != "info":
        payload["level"] = level
    if not for_adoption_ui:
        payload["stage"] = "effect_track"
    state["progress_messages"].append(payload)

    sender = _progress_sender.get()
    if sender:
        thread_id, manager, cache_writer = sender
        try:
            if cache_writer:
                cache_entry: dict[str, Any] = {"message": message, "percent": percent, "timestamp": ts}
                if level and level != "info":
                    cache_entry["level"] = level
                if not for_adoption_ui:
                    cache_entry["stage"] = "effect_track"
                    cache_entry["type"] = "progress"
                cache_writer(thread_id, cache_entry)

            loop = asyncio.get_running_loop()
            ws_payload: dict[str, Any] = {
                "type": "progress",
                "message": message,
                "timestamp": ts,
                "stage": "effect_track" if not for_adoption_ui else "execution",
            }
            if percent is not None:
                ws_payload["percent"] = percent
            if level and level != "info":
                ws_payload["level"] = level
            loop.create_task(manager.send_progress(thread_id, ws_payload))
        except RuntimeError:
            pass
    else:
        thread_id = str(state.get("thread_id") or "").strip()
        if thread_id:
            try:
                from src.runtime.progress_store import write_progress_cache as _write_progress_cache

                cache_entry: dict[str, Any] = {"message": message, "percent": percent, "timestamp": ts}
                if level and level != "info":
                    cache_entry["level"] = level
                if not for_adoption_ui:
                    cache_entry["stage"] = "effect_track"
                    cache_entry["type"] = "progress"
                _write_progress_cache(thread_id, cache_entry)
            except Exception:
                pass
