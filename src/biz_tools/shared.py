"""biz_tools 子包内共享：单例 TenantRouter + BizAPIClient。"""

from __future__ import annotations

from src.biz_tools.biz_api_client import BizAPIClient
from src.biz_tools.tenant_router import TenantRouter

router = TenantRouter()
biz = BizAPIClient(router)
