from __future__ import annotations

import asyncio

from src.mcp_servers import crm_server


def test_get_tenant_profile_uses_router_context(monkeypatch) -> None:
    async def _run() -> None:
        async def fake_get(tenant_id: str, path: str, auth_token=None):
            assert tenant_id == "tenant_demo"
            assert path == "/store/list"
            return {
                "list": [
                    {
                        "storeId": "s1",
                        "storeName": "门店A",
                        "customerCount": 2,
                        "monthlyGmv": 100.0,
                        "employeeCount": 3,
                        "adminAccountIds": ["u1"],
                    }
                ]
            }

        async def fake_get_tenant_basic_info(tenant_id: str):
            assert tenant_id == "tenant_demo"
            return "演示企业", "retail_general"

        monkeypatch.setattr(crm_server.biz, "get", fake_get)
        monkeypatch.setattr(crm_server.router, "get_tenant_basic_info", fake_get_tenant_basic_info)

        result = await crm_server._get_tenant_profile("tenant_demo")
        assert result["store_name"] == "演示企业（全企业）"
        assert result["industry_code"] == "retail_general"

    asyncio.run(_run())
