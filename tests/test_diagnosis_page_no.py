from __future__ import annotations

import pytest
from fastapi import HTTPException

from src.api.routes import diagnosis
from src.mcp_servers.biz_api_client import BizAPIError


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


@pytest.mark.asyncio
async def test_drill_down_biz_error_returns_user_friendly_message(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get(tenant_id: str, endpoint: str, params: dict) -> dict:
        raise BizAPIError(
            status_code=404,
            message='{"status":404,"error":"Not Found","path":"/web/aia/account-coupon/statistics"}',
            url=endpoint,
        )

    monkeypatch.setattr(diagnosis._biz, "get", fake_get)

    with pytest.raises(HTTPException) as exc_info:
        await diagnosis._query_drill_data_from_wlwq(
            metric_code="coupon_redemption_rate",
            enterprise_id="tenant-001",
            days=30,
            page=1,
            page_size=10,
        )

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "调用业务侧接口失败，请稍后重试"
