"""业务系统API调用封装 — 统一处理错误、重试、日志。"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import httpx

from src.mcp_servers.tenant_router import PLATFORM_TENANT_ID, TenantContext, TenantNotFoundError, TenantRouter
from src.core.tracing import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer("biz_api")


def _auth_source_label_ctx(ctx: TenantContext, auth_token: str | None) -> str:
    """说明鉴权来源（不记录密钥明文）。默认来自 tenant_registry.auth_credential。"""
    if auth_token:
        return "Authorization=请求参数覆盖"
    h = ctx.auth_headers
    if (h.get("Authorization") or "").strip():
        return "鉴权=tenant_registry.auth_credential(Authorization)"
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


def _compose_request_url(base_url: str, path: str) -> str:
    if str(path).startswith(("http://", "https://")):
        return str(path)
    return f"{base_url.rstrip('/')}/{str(path).lstrip('/')}"


def _request_url_for_log(base_url: str, method: str, path: str, params: dict | None) -> str:
    """与 httpx 编码一致的可读 URL（GET 等会把 params 并入 query）。"""
    full = _compose_request_url(base_url, path)
    if not params:
        return full
    return str(httpx.Request(method, full, params=params).url)


def _normalize_biz_error_message(payload: Any, status_code: int, fallback_text: str = "") -> str:
    """优先按业务错误码映射标准文案，避免依赖字符串清洗。"""
    if isinstance(payload, dict):
        biz_code = payload.get("code")
        if biz_code in (401, "401"):
            return "认证失败，无法访问系统资源"
        msg = payload.get("message") or payload.get("msg") or payload.get("error")
        if isinstance(msg, str) and msg.strip():
            return msg.strip()
    if isinstance(fallback_text, str) and fallback_text.strip():
        return fallback_text.strip()
    if status_code == 401:
        return "认证失败，无法访问系统资源"
    return "unknown error"


def _response_body_for_log(body: Any, http_status: int) -> Any:
    """日志用响应体：业务失败时改写 msg/message，与 BizAPIError 一致，不重复打原始拼接文案。"""
    if not isinstance(body, dict) or "code" not in body:
        return body
    if body["code"] in (0, 200, "0", "200"):
        return body
    norm = _normalize_biz_error_message(body, http_status)
    out = dict(body)
    if "msg" in out:
        out["msg"] = norm
    if "message" in out:
        out["message"] = norm
    return out


class BizAPIError(Exception):
    def __init__(self, status_code: int, message: str, url: str):
        self.status_code = status_code
        self.message = (message or "").strip()
        self.url = url
        super().__init__(self.message)


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
        request_url = _request_url_for_log(base_url, method, path, params)
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
                "调用业务侧接口: tenant=%s %s %s %s json=%s",
                tenant_id,
                auth_label,
                method,
                request_url,
                json.dumps(json_data, ensure_ascii=False),
            )
        else:
            logger.info(
                "调用业务侧接口: tenant=%s %s %s %s",
                tenant_id,
                auth_label,
                method,
                request_url,
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
            if auth_hdr:
                logger.info(
                    "请求业务API: tenant=%s %s %s Authorization=%s",
                    tenant_id,
                    method,
                    request_url,
                    auth_hdr,
                )
            else:
                logger.info(
                    "请求业务API: tenant=%s %s %s (无 Authorization)",
                    tenant_id,
                    method,
                    request_url,
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
                    "业务API返回成功: tenant=%s %s %s 耗时=%.2fs 尝试=%d/%d",
                    tenant_id,
                    method,
                    request_url,
                    elapsed,
                    attempt,
                    self._MAX_RETRIES,
                )
                return result
            except BizAPIError:
                raise
            except asyncio.TimeoutError as e:
                elapsed = time.time() - start_time
                last_exception = e
                logger.warning(
                    "业务API返回超时: tenant=%s %s %s 耗时=%.2fs 超时限制=%ss 尝试=%d/%d",
                    tenant_id,
                    method,
                    request_url,
                    elapsed,
                    self._REQUEST_TIMEOUT,
                    attempt,
                    self._MAX_RETRIES,
                )
            except httpx.HTTPStatusError as e:
                elapsed = time.time() - start_time
                logger.error(
                    "业务API返回错误: tenant=%s %s %s 状态码=%s 耗时=%.2fs",
                    tenant_id,
                    method,
                    request_url,
                    e.response.status_code,
                    elapsed,
                )
                raise
            except TenantNotFoundError as e:
                elapsed = time.time() - start_time
                logger.error(
                    "业务API返回错误: tenant=%s %s %s 耗时=%.2fs 错误=%s",
                    tenant_id,
                    method,
                    request_url,
                    elapsed,
                    str(e),
                )
                raise
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(
                    "业务API返回错误异常: tenant=%s %s %s 耗时=%.2fs 错误=%s",
                    tenant_id,
                    method,
                    request_url,
                    elapsed,
                    str(e),
                )
                raise

            # 如果不是最后一次尝试，等待后重试
            if attempt < self._MAX_RETRIES:
                await asyncio.sleep(self._RETRY_DELAY * attempt)

        # 所有重试都失败
        logger.error(
            "调用业务API失败: tenant=%s %s %s 重试次数=%d",
            tenant_id,
            method,
            request_url,
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
        span_name = f"biz_api.{method}.{path}"
        with tracer.start_as_current_span(span_name) as span:
            span.set_attribute("http.method", method)
            span.set_attribute("http.url", full_url)
            span.set_attribute("http.path", path)
            return await self._do_request(
                client, method, path, params, json_data, headers, full_url, url, span
            )

    async def _do_request(
        self,
        client: httpx.AsyncClient,
        method: str,
        path: str,
        params: dict | None,
        json_data: dict | None,
        headers: dict[str, str] | None,
        full_url: str,
        url: str,
        span,
    ) -> dict[str, Any]:
        try:
            resp = await client.request(method, path, params=params, json=json_data, headers=dict(headers or {}))
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            err_preview = e.response.text[:500]
            try:
                err_j = e.response.json()
                if isinstance(err_j, dict):
                    err_preview = json.dumps(
                        _response_body_for_log(err_j, e.response.status_code), ensure_ascii=False
                    )[:500]
            except Exception:
                pass
            span.set_attribute("http.status_code", e.response.status_code)
            span.record_exception(e)
            err_payload: Any
            try:
                err_payload = e.response.json()
            except Exception:
                err_payload = None
            error_msg = _normalize_biz_error_message(err_payload, e.response.status_code, e.response.text[:500])
            logger.error(
                "调用业务侧接口错误: %s %s code=%s msg=%s",
                method,
                full_url,
                e.response.status_code,
                error_msg,
            )
            raise BizAPIError(e.response.status_code, error_msg, str(url))
        except httpx.RequestError as e:
            logger.error("调用业务API异常: %s %s 错误=%s", method, full_url, str(e))
            span.record_exception(e)
            raise BizAPIError(0, str(e), str(url))

        body = resp.json()
        span.set_attribute("http.status_code", resp.status_code)
        if isinstance(body, dict) and "code" in body:
            if body["code"] not in (0, 200, "0", "200"):
                # 支持 msg 和 message 两种错误字段格式
                error_msg = _normalize_biz_error_message(body, resp.status_code)
                logger.error(
                    "调用业务API错误: %s %s code=%s msg=%s",
                    method,
                    full_url,
                    body["code"],
                    error_msg,
                )
                raise BizAPIError(resp.status_code, error_msg, str(url))
            return body.get("data", body)

        return body
