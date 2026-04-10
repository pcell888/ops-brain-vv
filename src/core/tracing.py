"""OpenTelemetry 初始化与 Tracer 获取。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _env_truthy(name: str) -> bool:
    v = (os.environ.get(name) or "").strip().lower()
    return v in ("1", "true", "yes", "on")


def apply_langsmith_env() -> None:
    """将 LangSmith / LangChain 追踪相关变量写入 os.environ。

    - 先 load 仓库根目录 .env，使仅写在 .env 里的 LANGSMITH_* 等进入进程环境（pydantic 不会代写 os.environ）。
    - 合并 Settings 与已有环境，并同时设置 LANGCHAIN_* 与 LANGSMITH_*（langsmith 优先读前者）。
    - 清除 langsmith.utils.get_env_var 的 lru_cache，避免在空环境下被错误缓存导致追踪永远关闭（见 langsmith.utils.tracing_is_enabled）。

    须在首次 import langchain_openai / langchain_core 之前调用（见 api/main.py 文件最顶部）。
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        load_dotenv = None  # type: ignore[misc, assignment]

    repo_root = Path(__file__).resolve().parents[2]
    env_file = repo_root / ".env"
    if load_dotenv is not None and env_file.is_file():
        load_dotenv(env_file, override=False)

    from src.core.config import get_settings

    s = get_settings()

    tracing = (
        s.langchain_tracing_v2
        or _env_truthy("LANGSMITH_TRACING_V2")
        or _env_truthy("LANGCHAIN_TRACING_V2")
    )
    val = "true" if tracing else "false"
    os.environ["LANGCHAIN_TRACING_V2"] = val
    os.environ["LANGSMITH_TRACING_V2"] = val

    api_key = (
        (s.langchain_api_key or "").strip()
        or (os.environ.get("LANGSMITH_API_KEY") or "").strip()
        or (os.environ.get("LANGCHAIN_API_KEY") or "").strip()
    )
    if api_key:
        os.environ["LANGCHAIN_API_KEY"] = api_key
        os.environ["LANGSMITH_API_KEY"] = api_key

    project = (
        (s.langchain_project or "").strip()
        or (os.environ.get("LANGSMITH_PROJECT") or "").strip()
        or (os.environ.get("LANGCHAIN_PROJECT") or "").strip()
    )
    if project:
        os.environ["LANGCHAIN_PROJECT"] = project
        os.environ["LANGSMITH_PROJECT"] = project

    endpoint = s.langchain_endpoint
    if endpoint:
        ep = str(endpoint).strip()
        os.environ["LANGCHAIN_ENDPOINT"] = ep
        os.environ["LANGSMITH_ENDPOINT"] = ep
    else:
        for k in ("LANGSMITH_ENDPOINT", "LANGCHAIN_ENDPOINT"):
            v = (os.environ.get(k) or "").strip()
            if v:
                os.environ["LANGCHAIN_ENDPOINT"] = v
                os.environ["LANGSMITH_ENDPOINT"] = v
                break

    try:
        from langsmith.utils import get_env_var

        get_env_var.cache_clear()
    except Exception:
        pass


def langgraph_config_for_llm() -> dict | None:
    """供 LangGraph 节点内嵌套 LLM 使用；Python 3.10 下图节点往往无 ContextVar，需由节点参数注入 config。"""
    try:
        from langgraph.config import get_config

        return get_config()
    except RuntimeError:
        return None


async def llm_traced_ainvoke(
    llm: Any,
    messages: Any,
    *,
    runnable_config: dict | None = None,
) -> Any:
    """在 LangGraph 节点内调用 ChatOpenAI 时使用：强制挂上 LangSmith tracer 并 flush。

    LangGraph 在 Py3.10 等环境不会为节点设置 var_child_runnable_config；仅传 config 仍可能缺 LangChainTracer。
    用 `tracing_v2_enabled()` 显式注册 tracer；结束时 `wait_for_all_tracers()` 避免异步上报丢失。
    """
    from langsmith.utils import tracing_is_enabled

    cfg = runnable_config if runnable_config is not None else langgraph_config_for_llm()
    if not tracing_is_enabled():
        return await llm.ainvoke(messages, config=cfg, stream=False)

    from langchain_core.tracers.context import tracing_v2_enabled
    from langchain_core.tracers.langchain import wait_for_all_tracers

    with tracing_v2_enabled():
        # 诊断主链通过 astream_events 运行时，LangChain 会因流式回调隐式切到 stream=True。
        # 对 DashScope/OpenAI 兼容接口，这会让 usage 更不稳定；这里显式关掉，保持与 direct ainvoke 一致。
        out = await llm.ainvoke(messages, config=cfg, stream=False)
    wait_for_all_tracers()
    return out


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


def to_langsmith_usage_metadata(usage: dict | None) -> dict | None:
    """转换为 LangSmith 接受的 usage_metadata 结构。"""
    if not isinstance(usage, dict):
        return None

    def _coerce_int(*keys: str) -> int | None:
        for key in keys:
            value = usage.get(key)
            try:
                if value is not None:
                    return int(value)
            except (TypeError, ValueError):
                continue
        return None

    input_tokens = _coerce_int("input_tokens", "prompt_tokens")
    output_tokens = _coerce_int("output_tokens", "completion_tokens")
    total_tokens = _coerce_int("total_tokens")
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    if input_tokens is None and output_tokens is None and total_tokens is None:
        return None
    return {
        "input_tokens": input_tokens or 0,
        "output_tokens": output_tokens or 0,
        "total_tokens": total_tokens or 0,
    }


def set_current_run_usage_metadata(
    usage: dict | None,
    *,
    runnable_config: dict | None = None,
) -> None:
    """尽力把 token 用量回填到当前 LangSmith run。"""
    usage_metadata = to_langsmith_usage_metadata(usage)
    if usage_metadata is None:
        return

    run_tree = None
    try:
        from langsmith.run_helpers import get_current_run_tree

        run_tree = get_current_run_tree()
    except Exception:
        run_tree = None

    if run_tree is None and runnable_config is not None:
        try:
            from langsmith.run_trees import RunTree

            run_tree = RunTree.from_runnable_config(runnable_config)
        except Exception:
            run_tree = None

    if run_tree is None:
        return

    try:
        run_tree.set(usage_metadata=usage_metadata)
    except Exception:
        try:
            run_tree.extra.setdefault("metadata", {})["usage_metadata"] = usage_metadata
        except Exception:
            return

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

_tracer_provider: TracerProvider | None = None


def setup_tracing(service_name: str | None = None) -> TracerProvider:
    """初始化 OpenTelemetry TracerProvider 并注册为全局。

    通过环境变量 OTEL_EXPORTER_OTLP_ENDPOINT 控制 exporter 目标地址。
    未设置时不导出 traces（本地开发不报错）。
    """
    global _tracer_provider
    if _tracer_provider is not None:
        return _tracer_provider

    name = service_name or os.getenv("OTEL_SERVICE_NAME", "ops-brain")
    resource = Resource.create({"service.name": name})

    provider = TracerProvider(resource=resource)
    endpoint = (os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or "").strip()

    if endpoint:
        exporter = OTLPSpanExporter(endpoint=endpoint)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)
    _tracer_provider = provider
    return provider


def get_tracer(name: str = "ops-brain") -> trace.Tracer:
    """获取命名 Tracer，用于在业务代码中创建 span。"""
    return trace.get_tracer(name)


def close_tracing() -> None:
    """关闭 TracerProvider（应用退出时调用）。"""
    global _tracer_provider
    if _tracer_provider is not None:
        try:
            _tracer_provider.shutdown()
        except Exception:
            pass
        _tracer_provider = None
