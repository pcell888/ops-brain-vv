"""统一的 LLM 构造。"""

from __future__ import annotations

from typing import Any

from langchain_openai import ChatOpenAI

from src.core.config import get_settings


def build_chat_llm(**overrides: Any) -> ChatOpenAI:
    """按项目配置创建 ChatOpenAI。"""
    settings = get_settings()
    model_name = str(overrides.pop("model", settings.llm_model)).strip() or settings.llm_model

    return ChatOpenAI(
        model=model_name,
        api_key=overrides.pop("api_key", settings.llm_api_key),
        base_url=overrides.pop("base_url", settings.llm_base_url),
        timeout=overrides.pop("timeout", settings.llm_httpx_timeout()),
        **overrides,
    )
