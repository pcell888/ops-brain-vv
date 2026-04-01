"""业务系统API调用封装 — 统一处理错误、重试、日志；API 不可达时返回模拟数据。"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any

import httpx

from src.mcp_servers.tenant_router import PLATFORM_TENANT_ID, TenantContext, TenantNotFoundError, TenantRouter

logger = logging.getLogger(__name__)


def _auth_source_label_ctx(ctx: TenantContext, auth_token: str | None) -> str:
    """说明鉴权来源（不记录密钥明文）。默认来自 tenant_registry.auth_credential。"""
    if auth_token:
        return "Authorization=请求参数覆盖"
    h = ctx.auth_headers
    if (h.get("Authorization") or "").strip():
        return "鉴权=tenant_registry.auth_credential(Authorization)"
    if (h.get("X-Service-Signature") or "").strip():
        return "鉴权=tenant_registry.auth_credential(HMAC)"
    return "鉴权=未配置"


def _full_request_url(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    params: dict | None,
    json_data: dict | None,
) -> str:
    req = client.build_request(method, path, params=params, json=json_data)
    return str(req.url)


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
    "ai/customer/projectInfo": {
        "projectId": "2018877462439526400",
        "customerId": "2021775485087776768",
        "customerName": "客户F002",
        "projectNo": "F002",
        "projectName": "服务002",
        "projectDesc": "服务002",
        "progress": 4,
        "isPermit": True,
        "state": True,
        "deliveredTime": "2026-02-04",
        "serveUrl": "http://192.168.1.249:8083",
        "logoUrl": "https://qiniu.chaolianweilai.com/2034898974276444160.png",
        "projectShortName": "服务002",
        "projectType": 2,
        "discountRate": 10.00,
        "accountTokenRate": 50.00,
        "platformTokenRate": 45.00,
        "middleTokenRate": 5.00,
        "invitationTokenRate": 1.00,
        "reflowTokenRate": 50.00,
        "businessClassCode": 1019,
        "businessClassName": "国际组织",
        "createTime": "2026-02-04T02:41:11",
        "remark": "F002",
        "projectTypeName": "电商类",
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

    async def platform_get(
        self,
        path: str,
        params: dict | None = None,
        *,
        auth_tenant_id: str | None = None,
        auth_authorization_override: str | None = None,
    ) -> dict[str, Any]:
        """调用平台中台 API（连接键为 __platform__）。
        auth_tenant_id: 使用该企业的 platform_auth_credential（或 auth_credential）访问中台。
        auth_authorization_override: 直接作为 Authorization 头（首访租户尚未入库时使用）。
        二者同时存在时优先 override。"""
        return await self._safe_request(
            PLATFORM_TENANT_ID,
            "GET",
            path,
            params=params,
            platform_auth_tenant_id=auth_tenant_id,
            platform_auth_authorization_override=auth_authorization_override,
        )

    # 租户解析(Redis/PG) + 取鉴权头 + HTTP 共享此时长；须 ≤ TenantRouter 中 httpx.AsyncClient 的 timeout
    _REQUEST_TIMEOUT = 30.0
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
        platform_auth_tenant_id: str | None = None,
        platform_auth_authorization_override: str | None = None,
    ) -> dict[str, Any]:
        ctx0 = await self.router.resolve(tenant_id)
        base_url = ctx0.api_base_url.rstrip("/")
        if auth_token:
            auth_label = "Authorization=请求参数覆盖"
        elif platform_auth_authorization_override and tenant_id == PLATFORM_TENANT_ID:
            auth_label = "Authorization=中台首访覆盖"
        elif platform_auth_tenant_id and tenant_id == PLATFORM_TENANT_ID:
            auth_label = f"鉴权=企业platform_auth_credential(tenant={platform_auth_tenant_id})"
        else:
            auth_label = _auth_source_label_ctx(ctx0, auth_token)

        # 记录所有请求（包括GET）；base_url / 鉴权标签来自当次 resolve（重试时会再次 resolve）
        if method in ("POST", "PUT") and json_data is not None:
            logger.info(
                "业务API请求: tenant=%s base_url=%s %s %s %s json=%s",
                tenant_id,
                base_url,
                auth_label,
                method,
                path,
                json.dumps(json_data, ensure_ascii=False),
            )
        else:
            logger.info(
                "业务API请求: tenant=%s base_url=%s %s %s %s params=%s",
                tenant_id,
                base_url,
                auth_label,
                method,
                path,
                params,
            )

        async def _do():
            ctx_try = await self.router.resolve(tenant_id)
            client_try = await self.router.get_client(tenant_id, ctx=ctx_try)
            if tenant_id == PLATFORM_TENANT_ID and platform_auth_authorization_override:
                req_headers = {"Authorization": platform_auth_authorization_override}
            elif platform_auth_tenant_id and tenant_id == PLATFORM_TENANT_ID:
                req_headers = await self.router.get_platform_api_auth_headers(platform_auth_tenant_id)
            else:
                req_headers = dict(ctx_try.auth_headers)
            if auth_token:
                req_headers = dict(req_headers)
                req_headers["Authorization"] = auth_token
            auth_hdr = (req_headers.get("Authorization") or "").strip()
            sig_hdr = (req_headers.get("X-Service-Signature") or "").strip()
            if auth_hdr:
                logger.info(
                    "业务API使用令牌: tenant=%s %s %s Authorization=%s",
                    tenant_id,
                    method,
                    path,
                    auth_hdr,
                )
            elif sig_hdr:
                logger.info(
                    "业务API使用令牌: tenant=%s %s %s X-Service-Signature=%s",
                    tenant_id,
                    method,
                    path,
                    sig_hdr,
                )
            else:
                logger.info(
                    "业务API使用令牌: tenant=%s %s %s (无 Authorization/X-Service-Signature)",
                    tenant_id,
                    method,
                    path,
                )
            return await self._request(
                client_try, method, path, params=params, json_data=json_data, headers=req_headers
            )

        last_exception = None
        for attempt in range(1, self._MAX_RETRIES + 1):
            start_time = time.time()
            try:
                result = await asyncio.wait_for(_do(), timeout=self._REQUEST_TIMEOUT)
                elapsed = time.time() - start_time
                logger.info(
                    "业务API响应成功: tenant=%s base_url=%s %s %s 耗时=%.2fs 尝试=%d/%d",
                    tenant_id,
                    base_url,
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
                    "业务API请求超时: tenant=%s base_url=%s %s %s 耗时=%.2fs 超时限制=%ss 尝试=%d/%d",
                    tenant_id,
                    base_url,
                    method,
                    path,
                    elapsed,
                    self._REQUEST_TIMEOUT,
                    attempt,
                    self._MAX_RETRIES,
                )
            except httpx.HTTPStatusError as e:
                elapsed = time.time() - start_time
                logger.error(
                    "业务API HTTP错误(不重试): tenant=%s base_url=%s %s %s 状态码=%s 耗时=%.2fs",
                    tenant_id,
                    base_url,
                    method,
                    path,
                    e.response.status_code,
                    elapsed,
                )
                raise
            except TenantNotFoundError as e:
                elapsed = time.time() - start_time
                logger.error(
                    "业务API请求失败(不可重试): tenant=%s base_url=%s %s %s 耗时=%.2fs 错误=%s",
                    tenant_id,
                    base_url,
                    method,
                    path,
                    elapsed,
                    str(e),
                )
                raise
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(
                    "业务API请求异常(不重试): tenant=%s base_url=%s %s %s 耗时=%.2fs 错误=%s",
                    tenant_id,
                    base_url,
                    method,
                    path,
                    elapsed,
                    str(e),
                )
                raise

            # 如果不是最后一次尝试，等待后重试
            if attempt < self._MAX_RETRIES:
                await asyncio.sleep(self._RETRY_DELAY * attempt)

        # 所有重试都失败
        logger.error(
            "业务API请求最终失败: tenant=%s base_url=%s %s %s 重试次数=%d",
            tenant_id,
            base_url,
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
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = path
        full_url = _full_request_url(client, method, path, params, json_data)
        base_url = str(client.base_url).rstrip("/")
        try:
            resp = await client.request(method, url, params=params, json=json_data, headers=dict(headers or {}))
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            # 兼容历史配置：若 base_url 误带 /web/ai，404 时自动回退到去前缀地址再试一次
            if e.response.status_code == 404 and base_url.endswith("/web/ai"):
                fallback_base = base_url[: -len("/web/ai")].rstrip("/")
                fallback_url = f"{fallback_base}/{str(path).lstrip('/')}"
                logger.warning(
                    "业务API 404，尝试去掉 /web/ai 前缀重试: %s %s -> %s",
                    method,
                    full_url,
                    fallback_url,
                )
                try:
                    resp = await client.request(
                        method,
                        fallback_url,
                        params=params,
                        json=json_data,
                        headers=dict(headers or {}),
                    )
                    resp.raise_for_status()
                except httpx.HTTPStatusError:
                    pass
                except httpx.RequestError:
                    pass
                else:
                    body = resp.json()
                    logger.info(
                        "业务API前缀回退成功: %s %s 状态码=%s",
                        method,
                        fallback_url,
                        resp.status_code,
                    )
                    if isinstance(body, dict) and "code" in body:
                        if body["code"] not in (0, 200, "0", "200"):
                            error_msg = body.get("msg") or body.get("message") or "unknown error"
                            raise BizAPIError(resp.status_code, error_msg, str(path))
                        return body.get("data", body)
                    return body
            logger.error(
                "业务API HTTP错误: base_url=%s %s %s 状态码=%s 响应=%s",
                base_url,
                method,
                full_url,
                e.response.status_code,
                e.response.text[:500],
            )
            raise BizAPIError(e.response.status_code, e.response.text[:500], str(url))
        except httpx.RequestError as e:
            logger.error("业务API请求异常: base_url=%s %s %s 错误=%s", base_url, method, full_url, str(e))
            raise BizAPIError(0, str(e), str(url))

        body = resp.json()
        logger.debug(
            "业务API响应: base_url=%s %s %s 状态码=%s 响应体=%s",
            base_url,
            method,
            full_url,
            resp.status_code,
            json.dumps(body, ensure_ascii=False)[:500],
        )

        if isinstance(body, dict) and "code" in body:
            if body["code"] not in (0, 200, "0", "200"):
                # 支持 msg 和 message 两种错误字段格式
                error_msg = body.get("msg") or body.get("message") or "unknown error"
                logger.error(
                    "业务API业务错误: base_url=%s %s %s code=%s msg=%s 响应体=%s",
                    base_url,
                    method,
                    full_url,
                    body["code"],
                    error_msg,
                    json.dumps(body, ensure_ascii=False)[:1000],
                )
                raise BizAPIError(resp.status_code, error_msg, str(url))
            return body.get("data", body)

        return body
