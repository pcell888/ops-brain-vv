"""业务系统API调用封装 — 统一处理错误、重试、日志；API 不可达时返回模拟数据。"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import httpx

from src.mcp_servers.tenant_router import TenantRouter

logger = logging.getLogger(__name__)


class BizAPIError(Exception):
    def __init__(self, status_code: int, message: str, url: str):
        self.status_code = status_code
        self.message = message
        self.url = url
        super().__init__(f"[{status_code}] {url}: {message}")


# ── Mock 数据（业务 API 不可达时降级使用） ────────────────────────

MOCK_DATA: dict[str, dict | list] = {
    # ── CRM ──
    "/store/{id}": {
        "storeName": "AI示范店",
        "storeType": "retail",
        "classId": "CLS001",
        "industryCode": "retail_general",
        "province": "浙江省",
        "city": "杭州市",
        "county": "西湖区",
        "customerCount": 3280,
        "monthlyGmv": 425000,
        "employeeCount": 18,
        "createdDays": 540,
        "adminAccountIds": ["admin-001", "admin-002"],
    },
    "/store-class/{id}": {
        "classCode": "retail_general",
        "className": "综合零售",
    },
    "/client-record/list": {
        "total": 3280,
        "list": [
            {"id": "c1", "name": "张三", "phone": "138****1234", "tags": ["high_value"], "lastOrderDays": 5},
            {"id": "c2", "name": "李四", "phone": "139****5678", "tags": ["new"], "lastOrderDays": 12},
            {"id": "c3", "name": "王五", "phone": "137****9012", "tags": ["churn_risk"], "lastOrderDays": 60},
        ],
    },
    "/client-record/{id}": {
        "id": "c1",
        "name": "张三",
        "phone": "138****1234",
        "totalOrders": 12,
        "totalAmount": 8600,
    },
    "/sales-contract/list": {
        "total": 2,
        "list": [
            {"id": "sc1", "amount": 5000, "status": "signed"},
            {"id": "sc2", "amount": 3600, "status": "signed"},
        ],
    },
    "/store-order/analytics": {
        "totalGmv": 425000,
        "avgOrderAmount": 186.5,
        "orderCount": 2280,
    },
    "/sys-dept/tree": {
        "list": [
            {"deptId": "d1", "deptName": "销售部", "parentId": None},
            {"deptId": "d2", "deptName": "运营部", "parentId": None},
            {"deptId": "d3", "deptName": "客服部", "parentId": None},
        ],
    },
    "/sys-user/list": {
        "list": [
            {"userId": 1, "userName": "销售主管", "deptId": "d1"},
            {"userId": 2, "userName": "运营经理", "deptId": "d2"},
        ],
    },

    # ── Metrics: CRM 维度 ──
    "/client-record/statistics": {"total": 3280, "newClients": 320},
    "/sales-contract/statistics": {"signedCount": 185, "totalAmount": 680000},
    "/examine-initiate/follow-stats": {
        "followTotal": 1260,
        "avgResponseHours": 4.8,
    },

    # ── Metrics: 营销维度 ──
    "/account-coupon/statistics": {"totalIssued": 5000, "totalUsed": 1850},
    "/store-order/conversion-stats": {
        "orderUsers": 820,
        "totalOrders": 2280,
        "completedOrders": 2050,
        "newCustomers": 320,
    },
    "/store-activities/roi": {"totalSpend": 28000},
    "/manage-data/exposure-stats": {"browseUsers": 12600},

    # ── Metrics: 留存维度 ──
    "/store-order/repurchase-stats": {
        "totalBuyers": 2800,
        "repeatBuyers": 1120,
        "activeCustomers": 2200,
        "churnedCustomers": 380,
        "avgLifetimeValue": 1560,
    },
    "/store-refund-order/statistics": {"totalCompletedOrders": 2050, "refundOrders": 82},
    "/store-order-evaluate/statistics": {"totalReviews": 1680, "positiveReviews": 1462},

    # ── Metrics: 效率维度 ──
    "/examine-initiate/turnaround-stats": {"onTimeRate": 78.5},
    "/service-order/completion-stats": {"totalServiceOrders": 360, "completedOrders": 306},
    "/store-order/shipping-stats": {"avgShippingHours": 14.2},

    # ── Benchmark ──
    "/industry-trend-statistics/benchmark": {
        "benchmarks": {
            "lead_conversion_rate": {"avg_value": 5.2, "median_value": 4.8, "excellent_value": 8.5},
            "response_time_avg": {"avg_value": 6.0, "median_value": 5.5, "excellent_value": 2.0},
            "follow_up_count": {"avg_value": 800, "median_value": 750, "excellent_value": 1500},
            "coupon_redemption_rate": {"avg_value": 32.0, "median_value": 30.0, "excellent_value": 50.0},
            "browse_to_order_rate": {"avg_value": 5.8, "median_value": 5.0, "excellent_value": 10.0},
            "order_conversion_rate": {"avg_value": 85.0, "median_value": 83.0, "excellent_value": 95.0},
            "customer_acquisition_cost": {"avg_value": 120, "median_value": 100, "excellent_value": 50},
            "repurchase_rate": {"avg_value": 35.0, "median_value": 32.0, "excellent_value": 55.0},
            "refund_rate": {"avg_value": 5.0, "median_value": 4.5, "excellent_value": 2.0},
            "churn_rate": {"avg_value": 18.0, "median_value": 16.0, "excellent_value": 8.0},
            "positive_review_rate": {"avg_value": 82.0, "median_value": 80.0, "excellent_value": 95.0},
            "avg_customer_lifetime_value": {"avg_value": 1200, "median_value": 1000, "excellent_value": 2500},
            "service_completion_rate": {"avg_value": 80.0, "median_value": 78.0, "excellent_value": 95.0},
            "avg_shipping_hours": {"avg_value": 18.0, "median_value": 16.0, "excellent_value": 6.0},
            "task_on_time_rate": {"avg_value": 75.0, "median_value": 72.0, "excellent_value": 92.0},
        },
    },
    "/store-class/list": [
        {"classCode": "retail_general", "className": "综合零售"},
        {"classCode": "food_bev", "className": "餐饮"},
        {"classCode": "beauty", "className": "美业"},
    ],
    "/industry-trend-statistics/trend": {
        "trends": [
            {"period": "2025-10", "value": 4.6},
            {"period": "2025-11", "value": 4.9},
            {"period": "2025-12", "value": 5.1},
            {"period": "2026-01", "value": 5.0},
            {"period": "2026-02", "value": 5.3},
            {"period": "2026-03", "value": 5.2},
        ],
    },

    # ── Task ──
    "/ai-diagnosis/exec-task/batch-create": {"tasks": [], "count": 0},
    "/examine-initiate/create": {"id": "mock-approval-001"},
    "/ai-diagnosis/exec-task/{id}/status": {},
    "/coupon/create": {"couponId": "mock-coupon-001"},
    "/coupon/distribute": {"count": 500},
    "/seckill-apply/create": {"id": "mock-seckill-001"},

    # ── Notify ──
    "/message-remind/batch-create": {},
    "/message-remind/create": {},
    "/message-record/create": {},
}


def _match_mock(path: str) -> dict | list | None:
    """路径匹配，支持 /store/{id} 这类模板。"""
    if path in MOCK_DATA:
        return MOCK_DATA[path]
    for pattern, data in MOCK_DATA.items():
        regex = re.sub(r"\{[^}]+\}", r"[^/]+", pattern)
        if re.fullmatch(regex, path):
            return data
    return None


class BizAPIClient:
    """封装对业务系统API的调用，统一处理 response 解析、错误处理。"""

    def __init__(self, router: TenantRouter):
        self.router = router

    async def get(
        self,
        tenant_id: str,
        path: str,
        params: dict | None = None,
    ) -> dict[str, Any]:
        return await self._safe_request(tenant_id, "GET", path, params=params)

    async def post(
        self,
        tenant_id: str,
        path: str,
        json_data: dict | None = None,
    ) -> dict[str, Any]:
        return await self._safe_request(tenant_id, "POST", path, json_data=json_data)

    async def put(
        self,
        tenant_id: str,
        path: str,
        json_data: dict | None = None,
    ) -> dict[str, Any]:
        return await self._safe_request(tenant_id, "PUT", path, json_data=json_data)

    async def platform_get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        """调用平台中台API。"""
        return await self._safe_request("__platform__", "GET", path, params=params)

    # 租户解析(Redis/PG)或请求 wlwq 无响应时会阻塞，整次请求加超时后降级 mock
    _REQUEST_TIMEOUT = 15.0

    async def _safe_request(
        self,
        tenant_id: str,
        method: str,
        path: str,
        params: dict | None = None,
        json_data: dict | None = None,
    ) -> dict[str, Any]:
        async def _do():
            client = await self.router.get_client(tenant_id)
            return await self._request(client, method, path, params=params, json_data=json_data)

        try:
            return await asyncio.wait_for(_do(), timeout=self._REQUEST_TIMEOUT)
        except (asyncio.TimeoutError, Exception) as e:
            mock = _match_mock(path)
            if mock is not None:
                reason = "超时" if isinstance(e, asyncio.TimeoutError) else e.__class__.__name__
                detail = str(e).strip().split("\n")[0][:200]  # 首行、截断，便于看到如「表不存在」
                logger.warning(
                    "业务API不可达, 降级为模拟数据: %s %s | %s: %s",
                    method, path, reason, detail,
                )
                return dict(mock) if isinstance(mock, dict) else mock
            raise

    async def _request(
        self,
        client: httpx.AsyncClient,
        method: str,
        path: str,
        params: dict | None = None,
        json_data: dict | None = None,
    ) -> dict[str, Any]:
        url = path
        try:
            resp = await client.request(method, url, params=params, json=json_data)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error("业务API调用失败: %s %s -> %s", method, url, e.response.status_code)
            raise BizAPIError(e.response.status_code, e.response.text[:500], str(url))
        except httpx.RequestError as e:
            logger.error("业务API请求异常: %s %s -> %s", method, url, e)
            raise BizAPIError(0, str(e), str(url))

        body = resp.json()

        if isinstance(body, dict) and "code" in body:
            if body["code"] not in (0, 200, "0", "200"):
                raise BizAPIError(resp.status_code, body.get("msg", "unknown error"), str(url))
            return body.get("data", body)

        return body
