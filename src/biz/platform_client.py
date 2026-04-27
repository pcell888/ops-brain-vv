"""平台中台 API 客户端 — 复用 HTTPClient，专注中台接口调用 + 行业基准。"""

from __future__ import annotations

import logging

from src.biz.http_client import HTTPClient, HTTPClientError
from src.core.config import get_settings

logger = logging.getLogger(__name__)


class PlatformAPIError(Exception):
    def __init__(self, status_code: int, message: str, url: str):
        self.status_code = status_code
        self.message = message
        self.url = url
        super().__init__(self.message)


DEFAULT_BENCHMARKS: dict[str, dict] = {
    "lead_conversion_rate": {"avg_value": 5.2, "median_value": 4.8, "excellent_value": 8.5},
    "response_time_avg": {"avg_value": 6.0, "median_value": 5.5, "excellent_value": 2.0},
    "follow_up_count": {"avg_value": 800, "median_value": 750, "excellent_value": 1500},
    "coupon_redemption_rate": {"avg_value": 32.0, "median_value": 30.0, "excellent_value": 50.0},
    "browse_to_order_rate": {"avg_value": 5.8, "median_value": 5.0, "excellent_value": 10.0},
    "order_conversion_rate": {"avg_value": 85.0, "median_value": 83.0, "excellent_value": 95.0},
    "seckill_conversion_rate": {"avg_value": 30.0, "median_value": 28.0, "excellent_value": 55.0},
    "repurchase_rate": {"avg_value": 35.0, "median_value": 32.0, "excellent_value": 55.0},
    "refund_rate": {"avg_value": 5.0, "median_value": 4.5, "excellent_value": 2.0},
    "churn_rate": {"avg_value": 18.0, "median_value": 16.0, "excellent_value": 8.0},
    "positive_review_rate": {"avg_value": 82.0, "median_value": 80.0, "excellent_value": 95.0},
    "avg_customer_lifetime_value": {"avg_value": 1200.0, "median_value": 1000.0, "excellent_value": 2500.0},
    "service_completion_rate": {"avg_value": 80.0, "median_value": 78.0, "excellent_value": 95.0},
    "avg_shipping_hours": {"avg_value": 18.0, "median_value": 16.0, "excellent_value": 6.0},
}


def _normalize_code(code: str) -> str:
    return "".join(ch for ch in str(code).lower() if ch.isalnum())


async def _get_platform_auth_headers(enterprise_tenant_id: str) -> dict:
    import psycopg.rows
    from src.biz.router import TenantNotFoundError
    from src.core.db_pool import get_conn

    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                "SELECT auth_type, auth_credential, platform_auth_credential "
                "FROM tenant_registries WHERE tenant_id=%s AND status=1",
                (enterprise_tenant_id,),
            )
            row = await cur.fetchone()

    if not row:
        raise TenantNotFoundError(f"租户 {enterprise_tenant_id} 不存在或已停用")

    cred = (row.get("platform_auth_credential") or "").strip()
    if not cred:
        cred = row["auth_credential"]
    auth_type = row["auth_type"]
    if auth_type == "token":
        return {"Authorization": cred}
    elif auth_type == "hmac":
        return {"X-Service-Signature": cred}
    return {}


async def _resolve_auth_headers(auth_tenant_id: str | None, auth_override: str | None) -> dict:
    if auth_override:
        return {"Authorization": auth_override}
    if auth_tenant_id:
        return await _get_platform_auth_headers(auth_tenant_id)
    return {}


class PlatformClient:
    def __init__(self) -> None:
        self._http: HTTPClient | None = None

    def _get_base_url(self) -> str:
        from src.core.config import get_settings
        settings = get_settings()
        base = (settings.platform_center_api_base or "").strip().rstrip("/")
        if not base:
            raise ValueError("未配置 PLATFORM_CENTER_API_BASE，请在 .env 中设置该地址")
        return base

    async def _ensure_http(self) -> HTTPClient:
        if self._http is None:
            self._http = HTTPClient(self._get_base_url())
        return self._http

    async def get_industry_benchmark(
        self,
        tenant_id: str,
        industry_code: str,
        indicator_codes: list[str],
        period: str | None = None,
    ) -> dict:
        logger.info(
            "Tool called: get_industry_benchmark tenant=%s industry=%s indicators=%s period=%s",
            tenant_id, industry_code, indicator_codes, period,
        )
        all_benchmarks = DEFAULT_BENCHMARKS.copy()
        result: dict = {}
        normalized_index = {_normalize_code(k): v for k, v in all_benchmarks.items()}
        for code in indicator_codes:
            if code in all_benchmarks:
                result[code] = all_benchmarks[code]
            elif _normalize_code(code) in normalized_index:
                result[code] = normalized_index[_normalize_code(code)]
            else:
                result[code] = {"avg_value": 0, "median_value": 0, "excellent_value": 0}
        return {"industry_code": industry_code, "period": period or "latest", "benchmarks": result}

    async def list_industries(self, tenant_id: str) -> list[dict]:
        logger.info("Tool called: list_industries tenant=%s", tenant_id)
        http = await self._ensure_http()
        headers = await _get_platform_auth_headers(tenant_id)
        data = await http.get("/store-class/list", headers=headers)
        return data.get("list", data) if isinstance(data, dict) else data

    async def get_industry_trend(
        self,
        tenant_id: str,
        industry_code: str,
        indicator_code: str,
        periods: int = 6,
    ) -> list[dict]:
        logger.info(
            "Tool called: get_industry_trend tenant=%s industry=%s indicator=%s periods=%s",
            tenant_id, industry_code, indicator_code, periods,
        )
        http = await self._ensure_http()
        headers = await _get_platform_auth_headers(tenant_id)
        data = await http.get(
            "/industry-trend-statistics/trend",
            params={"industryCode": industry_code, "indicatorCode": indicator_code, "periods": periods},
            headers=headers,
        )
        return data.get("trends", data) if isinstance(data, dict) else data

    async def get_project_enterprise_info(self, tenant_id: str) -> dict:
        logger.info("Tool called: get_project_enterprise_info tenant=%s", tenant_id)
        http = await self._ensure_http()
        headers = await _get_platform_auth_headers(tenant_id)
        return await http.get("ai/customer/projectInfo", params={"projectId": tenant_id}, headers=headers)

    async def close(self) -> None:
        if self._http:
            await self._http.close()
            self._http = None


platform_client = PlatformClient()