"""统一的 LLM 构造与 LangSmith 元数据覆盖。"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models import LangSmithParams
from langchain_openai import ChatOpenAI
from pydantic import Field

from src.core.config import get_settings


class ConfiguredChatOpenAI(ChatOpenAI):
    """覆盖 LangSmith provider/model 元数据，使其与 .env 保持一致。"""

    langsmith_provider: str | None = Field(default=None, exclude=True)
    langsmith_model_name: str | None = Field(default=None, exclude=True)

    def _get_ls_params(
        self, stop: list[str] | None = None, **kwargs: Any
    ) -> LangSmithParams:
        params = super()._get_ls_params(stop=stop, **kwargs)

        provider = str(self.langsmith_provider or "").strip()
        model_name = str(
            kwargs.get("model") or self.langsmith_model_name or self.model_name or ""
        ).strip()

        if provider:
            params["ls_provider"] = provider
        if model_name:
            params["ls_model_name"] = model_name
        return params


def build_chat_llm(**overrides: Any) -> ConfiguredChatOpenAI:
    """按项目配置创建带 LangSmith 元数据覆盖的 ChatOpenAI。"""
    settings = get_settings()
    model_name = str(overrides.pop("model", settings.llm_model)).strip() or settings.llm_model
    langsmith_provider = str(
        overrides.pop("langsmith_provider", settings.llm_provider)
    ).strip()
    langsmith_model_name = str(
        overrides.pop("langsmith_model_name", model_name)
    ).strip() or model_name

    return ConfiguredChatOpenAI(
        model=model_name,
        api_key=overrides.pop("api_key", settings.llm_api_key),
        base_url=overrides.pop("base_url", settings.llm_base_url),
        timeout=overrides.pop("timeout", settings.llm_httpx_timeout()),
        langsmith_provider=langsmith_provider or None,
        langsmith_model_name=langsmith_model_name,
        **overrides,
    )
