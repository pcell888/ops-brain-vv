"""业务系统API调用封装 — 统一处理错误、重试、日志。"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from src.biz_tools.biz_constants import is_biz_mock_tenant
from src.biz_tools.tenant_router import PLATFORM_TENANT_ID, TenantNotFoundError, TenantRouter
from src.core.tracing import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer("biz_api")


def _full_request_url(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    params: dict | None,
    json_data: dict | None,
) -> str:
    req = client.build_request(method, path, params=params, json=json_data)
    return str(req.url)


def _method_path_query_for_log(method: str, path: str, params: dict | None) -> str:
    p = str(path).strip()
    if p.startswith(("http://", "https://")):
        merged = str(httpx.Request(method, p, params=params).url)
        parsed = urlparse(merged)
        pq = (parsed.path or "/") + (f"?{parsed.query}" if parsed.query else "")
        return f"{method} {pq}"
    rel = f"/{p.lstrip('/')}"
    if not params:
        return f"{method} {rel}"
    q = str(httpx.QueryParams(params))
    return f"{method} {rel}?{q}" if q else f"{method} {rel}"


def _log_route_label(method: str, path: str) -> str:
    s = str(path).strip()
    if s.startswith(("http://", "https://")):
        u = urlparse(s)
        p = u.path or "/"
        return f"{method} {p}"
    return f"{method} /{s.lstrip('/')}"


def _log_outgoing_biz_request(
    method: str,
    path: str,
    params: dict | None,
    json_data: dict | None,
    tenant_id: str,
    base_url: str,
) -> None:
    parts: list[str] = [_method_path_query_for_log(method, path, params)]
    if method in ("POST", "PUT") and json_data is not None:
        parts.append(f"json={json.dumps(json_data, ensure_ascii=False)}")
    parts.append(f"tenant={tenant_id}")
    parts.append(f"base={base_url}")
    logger.info(" ".join(parts))


def _normalize_biz_error_message(payload: Any, status_code: int, fallback_text: str = "") -> str:
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
        return await self._safe_request(
            PLATFORM_TENANT_ID,
            "GET",
            path,
            params=params,
            platform_auth_tenant_id=auth_tenant_id,
            platform_auth_authorization_override=auth_authorization_override,
        )

    _REQUEST_TIMEOUT = 30.0
    _MAX_RETRIES = 3
    _RETRY_DELAY = 1.0

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
        _log_outgoing_biz_request(method, path, params, json_data, tenant_id, base_url)

        if is_biz_mock_tenant(tenant_id):
            return await self._execute_via_mock(method, path, params, json_data, tenant_id)

        return await self._execute_via_http_with_retries(
            tenant_id,
            method,
            path,
            params=params,
            json_data=json_data,
            auth_token=auth_token,
            platform_auth_tenant_id=platform_auth_tenant_id,
            platform_auth_authorization_override=platform_auth_authorization_override,
        )

    async def _execute_via_mock(
        self,
        method: str,
        path: str,
        params: dict | None,
        json_data: dict | None,
        tenant_id: str,
    ) -> dict[str, Any]:
        from src.biz_tools.mock.dispatch import dispatch_biz_mock  # noqa: F811

        start_time = time.time()
        result = await dispatch_biz_mock(method, path, params, json_data)
        elapsed = time.time() - start_time
        logger.info(
            "成功 %s %.2fs tenant=%s",
            _log_route_label(method, path),
            elapsed,
            tenant_id,
        )
        return result

    async def _execute_via_http_with_retries(
        self,
        tenant_id: str,
        method: str,
        path: str,
        *,
        params: dict | None,
        json_data: dict | None,
        auth_token: str | None,
        platform_auth_tenant_id: str | None,
        platform_auth_authorization_override: str | None,
    ) -> dict[str, Any]:
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
            return await self._request(
                client_try, method, path, params=params, json_data=json_data, headers=req_headers
            )

        last_exception = None
        for attempt in range(1, self._MAX_RETRIES + 1):
            start_time = time.time()
            try:
                result = await asyncio.wait_for(_do(), timeout=self._REQUEST_TIMEOUT)
                elapsed = time.time() - start_time
                retry = f" [{attempt}/{self._MAX_RETRIES}]" if attempt > 1 else ""
                logger.info(
                    "成功 %s %.2fs tenant=%s%s",
                    _log_route_label(method, path),
                    elapsed,
                    tenant_id,
                    retry,
                )
                return result
            except BizAPIError:
                raise
            except asyncio.TimeoutError as e:
                elapsed = time.time() - start_time
                last_exception = e
                logger.warning(
                    "超时 %s %.2fs limit=%ss tenant=%s [%d/%d]",
                    _log_route_label(method, path),
                    elapsed,
                    self._REQUEST_TIMEOUT,
                    tenant_id,
                    attempt,
                    self._MAX_RETRIES,
                )
            except httpx.HTTPStatusError as e:
                elapsed = time.time() - start_time
                logger.error(
                    "错误 %s HTTP=%s %.2fs tenant=%s",
                    _log_route_label(method, path),
                    e.response.status_code,
                    elapsed,
                    tenant_id,
                )
                raise
            except TenantNotFoundError as e:
                elapsed = time.time() - start_time
                logger.error(
                    "错误 %s %.2fs %s tenant=%s",
                    _log_route_label(method, path),
                    elapsed,
                    str(e),
                    tenant_id,
                )
                raise
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(
                    "异常 %s %.2fs %s tenant=%s",
                    _log_route_label(method, path),
                    elapsed,
                    str(e),
                    tenant_id,
                )
                raise

            if attempt < self._MAX_RETRIES:
                await asyncio.sleep(self._RETRY_DELAY * attempt)

        logger.error(
            "失败 %s 已重试%d次 tenant=%s",
            _log_route_label(method, path),
            self._MAX_RETRIES,
            tenant_id,
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
            span.set_attribute("http.status_code", e.response.status_code)
            span.record_exception(e)
            err_payload: Any
            try:
                err_payload = e.response.json()
            except Exception:
                err_payload = None
            error_msg = _normalize_biz_error_message(err_payload, e.response.status_code, e.response.text[:500])
            logger.error(
                "HTTP错误 %s %s code=%s msg=%s",
                method,
                full_url,
                e.response.status_code,
                error_msg,
            )
            raise BizAPIError(e.response.status_code, error_msg, str(url))
        except httpx.RequestError as e:
            logger.error("请求异常: %s %s 错误=%s", method, full_url, str(e))
            span.record_exception(e)
            raise BizAPIError(0, str(e), str(url))

        body = resp.json()
        span.set_attribute("http.status_code", resp.status_code)
        if isinstance(body, dict) and "code" in body:
            if body["code"] not in (0, 200, "0", "200"):
                error_msg = _normalize_biz_error_message(body, resp.status_code)
                logger.error(
                    "响应错误: %s %s code=%s msg=%s",
                    method,
                    full_url,
                    body["code"],
                    error_msg,
                )
                raise BizAPIError(resp.status_code, error_msg, str(url))
            return body.get("data", body)

        return body
