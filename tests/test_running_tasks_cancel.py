from __future__ import annotations

import asyncio

import pytest

from src.runtime.running_tasks import RunningTaskStore


@pytest.mark.asyncio
async def test_request_cancel_marks_local_when_redis_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    store = RunningTaskStore()

    async def _no_redis():
        return None

    monkeypatch.setattr(store, "_get_redis", _no_redis)

    await store.request_cancel("diag_local_cancel")
    assert await store.is_cancel_requested("diag_local_cancel") is True


@pytest.mark.asyncio
async def test_request_cancel_cancels_local_task_immediately(monkeypatch: pytest.MonkeyPatch) -> None:
    store = RunningTaskStore()

    async def _no_redis():
        return None

    monkeypatch.setattr(store, "_get_redis", _no_redis)

    task = asyncio.create_task(asyncio.sleep(10))
    store["diag_task"] = task

    await store.request_cancel("diag_task")
    await asyncio.sleep(0)

    assert task.cancelled() is True
    assert await store.is_cancel_requested("diag_task") is True
