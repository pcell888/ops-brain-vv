"""效果追踪异常类型。"""

from __future__ import annotations


class TrackingServiceError(Exception):
    """供路由映射为 HTTP 错误。"""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class LLMReviewReportError(Exception):
    """完成追踪等场景在 strict_llm 下要求 LLM 成功。"""
