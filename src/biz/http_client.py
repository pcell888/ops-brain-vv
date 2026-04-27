"""HTTP 客户端封装 — 底层网络请求"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from src.core.tracing import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer("biz_http")


class HTTPClientError(Exception):
    def __init__(self, status_code: int, message: str, url: str):
        self.status_code = status_code
        self.message = message
        self.url = url
        super().__init__(self.message)


class HTTPClient:
    """HTTP 客户端封装 — 重试、超时、错误处理"""
    
    def __init__(self, base_url: str, headers: dict | None = None):
        self.base_url = base_url.rstrip("/")
        self.default_headers = headers or {}
        self._client: httpx.AsyncClient | None = None
        self._timeout = 30.0
        self._max_retries = 3
        self._retry_delay = 1.0
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Accept-Encoding": "identity", **self.default_headers},
                timeout=self._timeout,
                trust_env=False,
            )
        return self._client
    
    async def request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        json_data: dict | None = None,
        headers: dict | None = None,
    ) -> dict[str, Any]:
        client = await self._get_client()
        span_name = f"biz_http.{method}.{path}"
        
        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            start = time.time()
            try:
                resp = await asyncio.wait_for(
                    client.request(method, path, params=params, json=json_data, headers=headers),
                    timeout=self._timeout,
                )
            except asyncio.TimeoutError as e:
                elapsed = time.time() - start
                last_exc = e
                logger.warning("超时 %s %s %.2fs [%d/%d]", method, path, elapsed, attempt, self._max_retries)
            except httpx.HTTPStatusError as e:
                elapsed = time.time() - start
                try:
                    err_body = e.response.json()
                except Exception:
                    err_body = None
                msg = str(err_body)[:200] if err_body else e.response.text[:200]
                err = HTTPClientError(e.response.status_code, msg, path)
                if e.response.status_code < 500:
                    raise err
                last_exc = err
                logger.warning("HTTP %s %s %.2fs [%d] retry", method, path, elapsed, e.response.status_code)
            except Exception as e:
                elapsed = time.time() - start
                logger.error("异常 %s %s %.2fs %s", method, path, elapsed, str(e))
                raise
            else:
                elapsed = time.time() - start
                if resp.status_code >= 400:
                    try:
                        err_body = resp.json()
                    except Exception:
                        err_body = None
                    msg = str(err_body)[:200] if err_body else resp.text[:200]
                    err = HTTPClientError(resp.status_code, msg, path)
                    if resp.status_code < 500:
                        raise err
                    last_exc = err
                    logger.warning("HTTP %s %s %.2fs [%d] retry", method, path, elapsed, resp.status_code)
                else:
                    logger.info("HTTP %s %s %.2fs", method, path, elapsed)
                    try:
                        return resp.json()
                    except Exception:
                        return {"_raw": resp.text}

            if attempt < self._max_retries:
                await asyncio.sleep(self._retry_delay * attempt)
        
        raise last_exc  # type: ignore
    
    async def get(self, path: str, params: dict | None = None, headers: dict | None = None) -> dict:
        return await self.request("GET", path, params=params, headers=headers)
    
    async def post(self, path: str, json_data: dict | None = None, headers: dict | None = None) -> dict:
        return await self.request("POST", path, json_data=json_data, headers=headers)
    
    async def put(self, path: str, json_data: dict | None = None, headers: dict | None = None) -> dict:
        return await self.request("PUT", path, json_data=json_data, headers=headers)
    
    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
