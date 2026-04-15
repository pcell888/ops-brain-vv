"""biz MCP 子包内共享：单例 TenantRouter + BizAPIClient。"""

from __future__ import annotations

from src.mcp_servers.biz_api_client import BizAPIClient
from src.mcp_servers.tenant_router import TenantRouter

router = TenantRouter()
biz = BizAPIClient(router)
