"""业务系统API调用封装 — 统一处理错误、重试、日志；API 不可达时返回模拟数据。"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
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
    "/store/list": {
        "list": [
            {
                "storeId": "s001",
                "storeName": "杭州旗舰店",
                "storeType": "retail",
                "industryCode": "retail_general",
                "province": "浙江省",
                "city": "杭州市",
                "customerCount": 3280,
                "monthlyGmv": 425000,
                "employeeCount": 18,
                "adminAccountIds": ["admin-001", "admin-002"],
            },
            {
                "storeId": "s002",
                "storeName": "上海体验店",
                "storeType": "retail",
                "industryCode": "retail_general",
                "province": "上海市",
                "city": "上海市",
                "customerCount": 2150,
                "monthlyGmv": 310000,
                "employeeCount": 12,
                "adminAccountIds": ["admin-003"],
            },
        ],
    },
    "/store/{id}": {
        "storeName": "AI示范店",
        "storeType": "retail",
        "businessMode": "mall",
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
    "/seckill-apply/conversion-stats": {"totalSeckillGoods": 500, "soldGoods": 185},
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
            "seckill_conversion_rate": {"avg_value": 30.0, "median_value": 28.0, "excellent_value": 55.0},
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
    "/ai-diagnosis/exec-task/{id}/status": {},
    "/examine-initiate/create": {"id": "mock-approval-001"},
    "/coupon/create": {"couponId": "mock-coupon-001"},
    "/coupon/distribute": {"count": 500},
    "/seckill-apply/create": {"id": "mock-seckill-001"},
    # ── Notify ──
    "/message-remind/batch-create": {},
    "/message-remind/targeted": {"sent_count": 0},
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
        auth_token: str | None = None,
    ) -> dict[str, Any]:
        return await self._safe_request(tenant_id, "GET", path, params=params, auth_token=auth_token)

    async def post(
        self,
        tenant_id: str,
        path: str,
        json_data: dict | None = None,
        auth_token: str | None = None,
    ) -> dict[str, Any]:
        return await self._safe_request(tenant_id, "POST", path, json_data=json_data, auth_token=auth_token)

    async def put(
        self,
        tenant_id: str,
        path: str,
        json_data: dict | None = None,
        auth_token: str | None = None,
    ) -> dict[str, Any]:
        return await self._safe_request(tenant_id, "PUT", path, json_data=json_data, auth_token=auth_token)

    async def platform_get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        """调用平台中台API。"""
        return await self._safe_request("__platform__", "GET", path, params=params)

    # 租户解析(Redis/PG)或请求 wlwq 无响应时会阻塞，整次请求加超时后降级 mock
    _REQUEST_TIMEOUT = 15.0
    _MAX_RETRIES = 3
    _RETRY_DELAY = 1.0  # 秒

    async def _safe_request(
        self,
        tenant_id: str,
        method: str,
        path: str,
        params: dict | None = None,
        json_data: dict | None = None,
        auth_token: str | None = None,
    ) -> dict[str, Any]:
        # 记录所有请求（包括GET）
        if method in ("POST", "PUT") and json_data is not None:
            logger.info(
                "业务API请求: tenant=%s %s %s json=%s",
                tenant_id,
                method,
                path,
                json.dumps(json_data, ensure_ascii=False),
            )
        else:
            logger.info(
                "业务API请求: tenant=%s %s %s params=%s",
                tenant_id,
                method,
                path,
                params,
            )

        async def _do():
            client = await self.router.get_client(tenant_id)
            extra_headers = {}
            if auth_token:
                extra_headers["Authorization"] = auth_token
            return await self._request(
                client, method, path, params=params, json_data=json_data, extra_headers=extra_headers
            )

        last_exception = None
        for attempt in range(1, self._MAX_RETRIES + 1):
            start_time = time.time()
            try:
                result = await asyncio.wait_for(_do(), timeout=self._REQUEST_TIMEOUT)
                elapsed = time.time() - start_time
                logger.info(
                    "业务API响应成功: tenant=%s %s %s 耗时=%.2fs 尝试=%d/%d",
                    tenant_id,
                    method,
                    path,
                    elapsed,
                    attempt,
                    self._MAX_RETRIES,
                )
                return result
            except asyncio.TimeoutError as e:
                elapsed = time.time() - start_time
                last_exception = e
                logger.warning(
                    "业务API请求超时: tenant=%s %s %s 耗时=%.2fs 超时限制=%ss 尝试=%d/%d",
                    tenant_id,
                    method,
                    path,
                    elapsed,
                    self._REQUEST_TIMEOUT,
                    attempt,
                    self._MAX_RETRIES,
                )
            except httpx.HTTPStatusError as e:
                elapsed = time.time() - start_time
                last_exception = e
                # 4xx错误不重试
                if 400 <= e.response.status_code < 500:
                    logger.error(
                        "业务API客户端错误(不重试): tenant=%s %s %s 状态码=%s 耗时=%.2fs",
                        tenant_id,
                        method,
                        path,
                        e.response.status_code,
                        elapsed,
                    )
                    raise
                logger.warning(
                    "业务API服务端错误: tenant=%s %s %s 状态码=%s 耗时=%.2fs 尝试=%d/%d",
                    tenant_id,
                    method,
                    path,
                    e.response.status_code,
                    elapsed,
                    attempt,
                    self._MAX_RETRIES,
                )
            except Exception as e:
                elapsed = time.time() - start_time
                last_exception = e
                logger.warning(
                    "业务API请求异常: tenant=%s %s %s 耗时=%.2fs 错误=%s 尝试=%d/%d",
                    tenant_id,
                    method,
                    path,
                    elapsed,
                    str(e),
                    attempt,
                    self._MAX_RETRIES,
                )

            # 如果不是最后一次尝试，等待后重试
            if attempt < self._MAX_RETRIES:
                await asyncio.sleep(self._RETRY_DELAY * attempt)

        # 所有重试都失败
        logger.error(
            "业务API请求最终失败: tenant=%s %s %s 重试次数=%d",
            tenant_id,
            method,
            path,
            self._MAX_RETRIES,
        )
        raise last_exception

    async def _request(
        self,
        client: httpx.AsyncClient,
        method: str,
        path: str,
        params: dict | None = None,
        json_data: dict | None = None,
        extra_headers: dict | None = None,
    ) -> dict[str, Any]:
        url = path
        try:
            headers = dict(client.headers)
            if extra_headers:
                headers.update(extra_headers)
            resp = await client.request(method, url, params=params, json=json_data, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(
                "业务API HTTP错误: %s %s 状态码=%s 响应=%s",
                method,
                url,
                e.response.status_code,
                e.response.text[:500],
            )
            raise BizAPIError(e.response.status_code, e.response.text[:500], str(url))
        except httpx.RequestError as e:
            logger.error("业务API请求异常: %s %s 错误=%s", method, url, str(e))
            raise BizAPIError(0, str(e), str(url))

        body = resp.json()
        logger.debug(
            "业务API响应: %s %s 状态码=%s 响应体=%s",
            method,
            url,
            resp.status_code,
            json.dumps(body, ensure_ascii=False)[:500],
        )

        if isinstance(body, dict) and "code" in body:
            if body["code"] not in (0, 200, "0", "200"):
                error_msg = body.get("msg", "unknown error")
                logger.error(
                    "业务API业务错误: %s %s code=%s msg=%s",
                    method,
                    url,
                    body["code"],
                    error_msg,
                )
                raise BizAPIError(resp.status_code, error_msg, str(url))
            return body.get("data", body)

        return body
