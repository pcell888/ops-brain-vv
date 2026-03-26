from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.api.routes import compat_diagnosis


class _FakeGraphApp:
    def __init__(self, state: SimpleNamespace) -> None:
        self._state = state

    async def aget_state(self, _config: dict) -> SimpleNamespace:
        return self._state


class _DoneTask:
    def done(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_status_returns_failed_when_not_running_but_next_nodes_exist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    diagnosis_id = "diag_failed_1"
    state = SimpleNamespace(
        next=("diagnose",),
        values={"progress_messages": [{"content": "正在采集企业运营数据", "percent": 10}]},
    )

    async def fake_get_report(_tid: str):
        return None

    async def fake_get_graph_app():
        return _FakeGraphApp(state)

    monkeypatch.setattr(compat_diagnosis, "get_report_from_db", fake_get_report)
    monkeypatch.setattr(compat_diagnosis, "get_graph_app", fake_get_graph_app)
    compat_diagnosis.running_tasks.pop(diagnosis_id, None)
    compat_diagnosis.progress_cache[diagnosis_id] = {"message": "业务接口 404", "percent": 0}

    result = await compat_diagnosis.compat_diagnosis_status(diagnosis_id)

    assert result["status"] == "failed"
    assert result["progress"] == 0
    assert "404" in result["message"]
    compat_diagnosis.running_tasks.pop(diagnosis_id, None)


@pytest.mark.asyncio
async def test_status_failed_uses_last_progress_message_when_cache_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    diagnosis_id = "diag_failed_2"
    state = SimpleNamespace(
        next=None,
        values={"progress_messages": [{"content": "诊断流程出错: 调用业务接口失败"}]},
    )

    async def fake_get_report(_tid: str):
        return None

    async def fake_get_graph_app():
        return _FakeGraphApp(state)

    monkeypatch.setattr(compat_diagnosis, "get_report_from_db", fake_get_report)
    monkeypatch.setattr(compat_diagnosis, "get_graph_app", fake_get_graph_app)
    compat_diagnosis.running_tasks[diagnosis_id] = _DoneTask()
    compat_diagnosis.progress_cache.pop(diagnosis_id, None)

    result = await compat_diagnosis.compat_diagnosis_status(diagnosis_id)

    assert result["status"] == "failed"
    assert result["message"] == "诊断流程出错: 调用业务接口失败"
    compat_diagnosis.running_tasks.pop(diagnosis_id, None)
