from __future__ import annotations

import asyncio

import pytest

from src.runtime.progress_store import ProgressStore


@pytest.mark.asyncio
async def test_progress_store_keeps_recent_history_without_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    store = ProgressStore()

    async def _no_redis():
        return None

    monkeypatch.setattr(store, "_get_redis", _no_redis)

    await store.aset("diag-1", {"message": "10%", "percent": 10})
    await store.aset("diag-1", {"message": "33%", "percent": 33})
    await store.aset("diag-1", {"message": "35%", "percent": 35})

    assert await store.aget("diag-1") == {"message": "35%", "percent": 35}
    assert await store.aget_history("diag-1", limit=2) == [
        {"message": "33%", "percent": 33},
        {"message": "35%", "percent": 35},
    ]


@pytest.mark.asyncio
async def test_progress_store_serializes_concurrent_writes_same_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = ProgressStore()

    async def _fake_redis():
        return None

    monkeypatch.setattr(store, "_get_redis", _fake_redis)

    async def write_i(i: int) -> None:
        await store.aset("t1", {"seq": i})

    await asyncio.gather(*(write_i(i) for i in range(30)))
    hist = await store.aget_history("t1", limit=50)
    assert len(hist) == 30
    assert {h["seq"] for h in hist} == set(range(30))


@pytest.mark.asyncio
async def test_progress_store_aclear_run_resets_history(monkeypatch: pytest.MonkeyPatch) -> None:
    store = ProgressStore()

    async def _no_redis():
        return None

    monkeypatch.setattr(store, "_get_redis", _no_redis)

    await store.aset("x", {"n": 1})
    await store.aset("x", {"n": 2})
    await store.aclear_run("x")
    await store.aset("x", {"n": 3})

    assert await store.aget("x") == {"n": 3}
    assert await store.aget_history("x", limit=10) == [{"n": 3}]
