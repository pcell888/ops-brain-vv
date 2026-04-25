"""业务 MCP 与租户解析共用常量。"""

from __future__ import annotations

BIZ_MOCK_TENANT_ID = "wlwq_local"


def is_biz_mock_tenant(tenant_id: str) -> bool:
    return (tenant_id or "").strip() == BIZ_MOCK_TENANT_ID
