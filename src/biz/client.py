"""业务系统 API 客户端 — 入口"""

from __future__ import annotations

from src.biz.biz_constants import is_mock_tenant


def tenant_client(tenant_id: str) -> TenantClient:
    """工厂函数 — 根据 tenant_id 返回对应客户端实例"""
    if is_mock_tenant(tenant_id):
        from src.biz.mock.client import MockTenantClient
        return MockTenantClient(tenant_id)
    from src.biz.real.client import RealTenantClient
    return RealTenantClient(tenant_id)
