"""全系统通用异常定义。"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """全系统通用业务异常基类"""

    def __init__(self, message: str, **kwargs: Any):
        self.message = message
        self.context = kwargs
        super().__init__(message)

    def __str__(self) -> str:
        if self.context:
            ctx_str = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
            return f"{self.message} ({ctx_str})"
        return self.message
