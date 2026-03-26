from __future__ import annotations

import pytest

from src.api.routes import diagnosis


@pytest.mark.asyncio
async def test_drill_down_request_uses_page_no(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def fake_get(tenant_id: str, endpoint: str, params: dict) -> dict:
        captured["tenant_id"] = tenant_id
        captured["endpoint"] = endpoint
        captured["params"] = params
        return {"total": 0, "list": []}

    monkeypatch.setattr(diagnosis._biz, "get", fake_get)

    await diagnosis._query_drill_data_from_wlwq(
        metric_code="service_completion_rate",
        enterprise_id="tenant-001",
        days=30,
        page=2,
        page_size=10,
    )

    params = captured["params"]
    assert isinstance(params, dict)
    assert params.get("pageNo") == 2
    assert "page" not in params
