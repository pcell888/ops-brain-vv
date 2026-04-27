"""业务常量"""

from __future__ import annotations

MOCK_TENANT_ID = "wlwq_local"


def is_mock_tenant(tenant_id: str) -> bool:
    return (tenant_id or "").strip() == MOCK_TENANT_ID
