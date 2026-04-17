"""HTTP 访问日志：写入 root handler（如 ops-brain.log），与 uvicorn 控制台 access 解耦。"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("src.api.access")


def _path_and_query(request: Request, *, max_query: int = 500) -> str:
    path = request.url.path or ""
    q = request.url.query
    if not q:
        return path
    if len(q) > max_query:
        q = q[:max_query] + "..."
    return f"{path}?{q}"


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except BaseException:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "HTTP %s %s %.1fms",
                request.method,
                _path_and_query(request),
                elapsed_ms,
            )
            raise
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "HTTP %s %s %d %.1fms",
            request.method,
            _path_and_query(request),
            response.status_code,
            elapsed_ms,
        )
        return response
