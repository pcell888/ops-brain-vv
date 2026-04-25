"""标准化 LLM 调用流程 — 统一 invoke→解析→usage 记录。"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.core.config import get_settings
from src.core.json_utils import strip_json_fence
from src.core.llm import build_chat_llm
from src.core.tracing import (
    extract_or_estimate_llm_usage,
    llm_ainvoke_in_graph,
    llm_usage_probe,
)

logger = logging.getLogger(__name__)


def _extract_text(resp: Any) -> str:
    c = getattr(resp, "content", "")
    if isinstance(c, str):
        return c.strip()
    if isinstance(c, list):
        parts: list[str] = []
        for block in c:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "".join(parts).strip()
    return str(c).strip()


_NO_THINK_SUFFIX = "/no_think"


async def llm_call_json(
    *,
    system_prompt: str,
    user_prompt: str,
    label: str = "LLM",
    temperature: float = 0.3,
    max_tokens: int | None = None,
    runnable_config: Any | None = None,
    model: str | None = None,
) -> tuple[Any, str, dict | None]:
    """统一的 LLM JSON 调用流程。

    Returns:
        (parsed_json | None, raw_text, usage_dict | None)

    parsed_json 为解析后的 dict/list；解析失败时为 None，raw_text 保留原始输出。
    调用方可根据 parsed_json 是否为 None 决定降级策略。
    """
    settings = get_settings()
    overrides: dict[str, Any] = {"temperature": temperature}
    if max_tokens is not None:
        overrides["max_tokens"] = max_tokens
    overrides["timeout"] = settings.llm_httpx_timeout()

    if not settings.llm_thinking_enabled:
        overrides["extra_body"] = {"enable_thinking": False}

    if model is not None:
        overrides["model"] = model

    llm = build_chat_llm(**overrides)

    effective_user_prompt = user_prompt
    if not settings.llm_thinking_enabled:
        effective_user_prompt = user_prompt.rstrip() + _NO_THINK_SUFFIX

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": effective_user_prompt},
    ]

    resp = await llm_ainvoke_in_graph(llm, messages, runnable_config=runnable_config)

    probe = llm_usage_probe(resp)
    logger.info(
        "%s usage probe: usage_metadata=%s response_token_usage=%s",
        label,
        probe.get("usage_metadata"),
        probe.get("response_token_usage"),
    )

    usage = extract_or_estimate_llm_usage(resp, llm=llm, messages=messages)
    if usage:
        logger.info(
            "%s tokens(%s): prompt=%s completion=%s total=%s calls=%s",
            label,
            usage.get("usage_source", "unknown"),
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
            usage.get("total_tokens", 0),
            usage.get("calls", 1),
        )

    text = _extract_text(resp)
    clean = strip_json_fence(text)
    if not clean:
        return None, text, usage

    try:
        parsed = json.loads(clean)
        if isinstance(parsed, str):
            try:
                return json.loads(parsed), text, usage
            except (json.JSONDecodeError, TypeError):
                return parsed, text, usage
        return parsed, text, usage
    except (json.JSONDecodeError, TypeError):
        logger.warning("%s JSON 解析失败，前 400 字: %s", label, clean[:400])
        return None, text, usage
