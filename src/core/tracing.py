"""OpenTelemetry 初始化与 Tracer 获取。"""

from __future__ import annotations

import json
from typing import Any


async def llm_ainvoke_in_graph(
    llm: Any,
    messages: Any,
    *,
    runnable_config: dict | None = None,
) -> Any:
    """调用 LLM：固定 stream=False 以稳定 usage。runnable_config 参数保留以兼容旧调用方签名，但不再使用。"""
    return await llm.ainvoke(messages, stream=False)


def extract_llm_usage(resp: Any) -> dict | None:
    """从 LangChain LLM 响应中提取标准化 token 用量。"""
    usage: dict[str, Any] = {}

    raw_usage = getattr(resp, "usage_metadata", None)
    if isinstance(raw_usage, dict):
        usage.update(raw_usage)

    response_metadata = getattr(resp, "response_metadata", None)
    if isinstance(response_metadata, dict):
        token_usage = response_metadata.get("token_usage")
        if isinstance(token_usage, dict):
            usage.setdefault("prompt_tokens", token_usage.get("prompt_tokens"))
            usage.setdefault("completion_tokens", token_usage.get("completion_tokens"))
            usage.setdefault("total_tokens", token_usage.get("total_tokens"))

    prompt_tokens = usage.get("prompt_tokens", usage.get("input_tokens"))
    completion_tokens = usage.get("completion_tokens", usage.get("output_tokens"))
    total_tokens = usage.get("total_tokens")

    try:
        prompt_tokens = int(prompt_tokens) if prompt_tokens is not None else None
    except (TypeError, ValueError):
        prompt_tokens = None
    try:
        completion_tokens = int(completion_tokens) if completion_tokens is not None else None
    except (TypeError, ValueError):
        completion_tokens = None
    try:
        total_tokens = int(total_tokens) if total_tokens is not None else None
    except (TypeError, ValueError):
        total_tokens = None

    if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
        total_tokens = prompt_tokens + completion_tokens

    if prompt_tokens is None and completion_tokens is None and total_tokens is None:
        return None

    out = {
        "prompt_tokens": prompt_tokens or 0,
        "completion_tokens": completion_tokens or 0,
        "total_tokens": total_tokens or 0,
        "input_tokens": prompt_tokens or 0,
        "output_tokens": completion_tokens or 0,
        "calls": 1,
    }
    model_name = getattr(resp, "response_metadata", {}) or {}
    if isinstance(model_name, dict) and model_name.get("model_name"):
        out["model_name"] = str(model_name["model_name"])
    return out


def _content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                item_type = str(item.get("type") or "").strip().lower()
                if item_type == "text":
                    parts.append(str(item.get("text") or ""))
                elif "content" in item:
                    parts.append(_content_to_text(item.get("content")))
                else:
                    try:
                        parts.append(json.dumps(item, ensure_ascii=False, sort_keys=True))
                    except TypeError:
                        parts.append(str(item))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    if isinstance(content, dict):
        if "text" in content:
            return str(content.get("text") or "")
        if "content" in content:
            return _content_to_text(content.get("content"))
        try:
            return json.dumps(content, ensure_ascii=False, sort_keys=True)
        except TypeError:
            return str(content)
    return str(content)


def _message_to_text(message: Any) -> str:
    role = "message"
    name = ""
    content: Any = message
    if isinstance(message, dict):
        role = str(message.get("role") or message.get("type") or role)
        name = str(message.get("name") or "")
        content = message.get("content")
    else:
        role = str(getattr(message, "role", None) or getattr(message, "type", None) or role)
        name = str(getattr(message, "name", "") or "")
        if hasattr(message, "content"):
            content = getattr(message, "content")

    body = _content_to_text(content).strip()
    head = f"[{role}]"
    if name:
        head += f" {name}"
    return f"{head}\n{body}" if body else head


def _response_text(resp: Any) -> str:
    if hasattr(resp, "content"):
        return _content_to_text(getattr(resp, "content")).strip()
    return _content_to_text(resp).strip()


def estimate_llm_usage(
    llm: Any,
    messages: Any,
    resp: Any,
) -> dict | None:
    """在 provider 未返回 usage 时，本地近似估算 token。"""
    try:
        if isinstance(messages, (list, tuple)):
            blocks = [_message_to_text(message) for message in messages]
            prompt_text = "\n\n".join(block for block in blocks if block)
            message_count = len(messages)
        else:
            prompt_text = _content_to_text(messages)
            message_count = 1 if prompt_text else 0
        completion_text = _response_text(resp)
        prompt_tokens = int(llm.get_num_tokens(prompt_text)) if prompt_text else 0
        completion_tokens = int(llm.get_num_tokens(completion_text)) if completion_text else 0
    except Exception:
        return None

    # 兼容 OpenAI chat 风格的报文包裹开销，作为本地粗略补偿。
    framing_tokens = message_count * 4 + (3 if message_count else 0)
    prompt_tokens += framing_tokens
    total_tokens = prompt_tokens + completion_tokens
    model_name = getattr(resp, "response_metadata", {}) or {}
    out = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "input_tokens": prompt_tokens,
        "output_tokens": completion_tokens,
        "calls": 1,
        "estimated": True,
        "usage_source": "local_tiktoken",
    }
    if isinstance(model_name, dict) and model_name.get("model_name"):
        out["model_name"] = str(model_name["model_name"])
    elif getattr(llm, "model_name", None):
        out["model_name"] = str(getattr(llm, "model_name"))
    return out


def extract_or_estimate_llm_usage(
    resp: Any,
    *,
    llm: Any | None = None,
    messages: Any | None = None,
) -> dict | None:
    """优先读取 provider usage，缺失时回退到本地 token 估算。"""
    usage = extract_llm_usage(resp)
    if usage is not None:
        usage["estimated"] = False
        usage["usage_source"] = "provider"
        return usage
    if llm is None or messages is None:
        return None
    return estimate_llm_usage(llm, messages, resp)


def llm_usage_probe(resp: Any) -> dict[str, Any]:
    """提取排障用的原始 usage 相关字段。"""
    response_metadata = getattr(resp, "response_metadata", None)
    token_usage = None
    metadata_keys: list[str] | None = None
    if isinstance(response_metadata, dict):
        token_usage = response_metadata.get("token_usage")
        metadata_keys = sorted(str(k) for k in response_metadata.keys())
    return {
        "usage_metadata": getattr(resp, "usage_metadata", None),
        "response_token_usage": token_usage,
        "response_metadata_keys": metadata_keys,
    }


def merge_llm_usage(*items: dict | None) -> dict | None:
    """合并多个标准化 token 用量。"""
    merged: dict[str, Any] | None = None
    for item in items:
        if not isinstance(item, dict):
            continue
        if merged is None:
            merged = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "calls": 0,
            }
        for key in ("prompt_tokens", "completion_tokens", "total_tokens", "input_tokens", "output_tokens", "calls"):
            try:
                merged[key] += int(item.get(key) or 0)
            except (TypeError, ValueError):
                pass
        if not merged.get("usage_source") and item.get("usage_source"):
            merged["usage_source"] = item["usage_source"]
        if not merged.get("model_name") and item.get("model_name"):
            merged["model_name"] = item["model_name"]
        if item.get("estimated"):
            merged["estimated"] = True
            merged["usage_source"] = "mixed" if merged.get("usage_source") and merged.get("usage_source") != item.get("usage_source") else item.get("usage_source")
    return merged


class _NoopSpan:
    def set_attribute(self, key: str, value: Any) -> None:
        return None

    def record_exception(self, exc: Exception) -> None:
        return None

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        return None

    def set_status(self, status: Any) -> None:
        return None

    def end(self) -> None:
        return None

    def __enter__(self) -> "_NoopSpan":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False


class _NoopTracer:
    def start_as_current_span(self, name: str, **kwargs: Any) -> _NoopSpan:
        return _NoopSpan()


_NOOP_TRACER = _NoopTracer()


def setup_tracing(service_name: str | None = None) -> None:
    return None


def get_tracer(name: str = "ops-brain") -> _NoopTracer:
    """获取兼容接口的 no-op tracer。"""
    return _NOOP_TRACER


def close_tracing() -> None:
    return None
