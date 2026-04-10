#!/usr/bin/env python3
"""验证 Langfuse Python SDK（span + generation + flush）。

仓库根目录:
  uv run python scripts/test_langfuse.py           # 投递一条测试 trace
  uv run python scripts/test_langfuse.py --check-only   # 仅检查密钥是否配置
  uv run python scripts/test_langfuse.py --auth       # 调用 Langfuse auth_check()

.env: LANGFUSE_PUBLIC_KEY、LANGFUSE_SECRET_KEY；自建部署可设 LANGFUSE_BASE_URL（或旧名 LANGFUSE_HOST）。
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _load_repo_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    root = Path(__file__).resolve().parents[1]
    env_file = root / ".env"
    if env_file.is_file():
        load_dotenv(env_file, override=False)


_load_repo_env()

from langfuse import get_client  # noqa: E402


def _print_env_status() -> None:
    keys = (
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_BASE_URL",
        "LANGFUSE_HOST",
        "LANGFUSE_TRACING_ENABLED",
        "LANGFUSE_TRACING_ENVIRONMENT",
    )
    for k in keys:
        v = (os.environ.get(k) or "").strip()
        if k.endswith("_KEY") and v:
            v = "(已设置)"
        print(f"  {k}={v or '(empty)'}")


def _keys_ok() -> bool:
    pub = (os.environ.get("LANGFUSE_PUBLIC_KEY") or "").strip()
    sec = (os.environ.get("LANGFUSE_SECRET_KEY") or "").strip()
    return bool(pub and sec)


def _run_smoke() -> int:
    if not _keys_ok():
        print("错误: 请设置 LANGFUSE_PUBLIC_KEY 与 LANGFUSE_SECRET_KEY。", file=sys.stderr)
        return 1

    client = get_client()
    trace_url: str | None = None
    try:
        with client.start_as_current_observation(
            as_type="span",
            name="ops-brain-test-langfuse",
            input={"note": "scripts/test_langfuse.py smoke"},
            metadata={"source": "test_langfuse"},
        ):
            with client.start_as_current_observation(
                as_type="generation",
                name="mock-llm",
                model="smoke-model",
                input="只回复一个词：pong",
                model_parameters={"temperature": 0},
            ) as gen:
                gen.update(
                    output="pong",
                    usage_details={
                        "prompt_tokens": 10,
                        "completion_tokens": 2,
                        "total_tokens": 12,
                    },
                )
            trace_url = client.get_trace_url()
        client.flush()
        print("[smoke] 已 flush。")
        if trace_url:
            print("[smoke] Trace URL:", trace_url)
        else:
            print("[smoke] 未能生成 Trace URL（可仍已在 UI 中看到新 trace）。")
        return 0
    finally:
        try:
            client.shutdown()
        except Exception:
            pass


def main() -> int:
    p = argparse.ArgumentParser(description="Langfuse SDK 冒烟测试")
    p.add_argument(
        "--check-only",
        action="store_true",
        help="只打印环境变量并检查密钥是否已配置",
    )
    p.add_argument(
        "--auth",
        action="store_true",
        help="在配置了密钥时请求 Langfuse auth_check()",
    )
    args = p.parse_args()

    print("Langfuse 环境（脱敏）:")
    _print_env_status()

    if not _keys_ok():
        print("tracing keys: 未完整配置（缺少 PUBLIC 或 SECRET）")
        if args.check_only:
            return 1
        if args.auth:
            print("--auth 需要密钥。", file=sys.stderr)
            return 1
        print("错误: 缺少 LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY。", file=sys.stderr)
        return 1

    print("tracing keys: 已配置")
    if args.check_only:
        return 0

    if args.auth:
        client = get_client()
        try:
            ok = client.auth_check()
        finally:
            try:
                client.shutdown()
            except Exception:
                pass
        print(f"auth_check() -> {ok}")
        return 0 if ok else 1

    return _run_smoke()


if __name__ == "__main__":
    sys.exit(main())
