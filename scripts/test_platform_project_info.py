#!/usr/bin/env python3
"""直连测试平台中台「项目信息」接口（与 BizAPIClient.platform_get 一致的路径与参数）。

用法示例:
  uv run python scripts/test_platform_project_info.py \\
    --base-url http://192.168.1.249/api/sys \\
    --token cb5f7be9-fde3-4026-885f-0d42f8046b29 \\
    --project-id 2016029835456937984

未传 --base-url / --token 时，可依赖 .env 中的 PLATFORM_CENTER_API_BASE、
自行 export BIZ_TEST_AUTHORIZATION='你的令牌'。

与 BizAPIClient / tenant_registry 约定一致：Authorization 为裸 token（UUID 等），
不要加「Bearer 」前缀；若你从别处复制了带 Bearer 的整串，脚本会自动去掉前缀。

Postman 正常而本脚本整段超时：多见于 shell/WSL 里配置了 HTTP_PROXY，httpx 默认会走代理；
本脚本默认 trust_env=False（直连）。若必须走公司代理请加 --trust-env。

"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

# 保障可导入 src（与仓库内其它脚本一致）
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import httpx


def _normalize_authorization(raw: str) -> str:
    """与业务中台一致：Authorization 头值为裸 token，不含 Bearer 前缀。"""
    s = raw.strip()
    low = s[:7].lower()
    if low == "bearer ":
        return s[7:].strip()
    return s


def _load_default_base_url() -> str | None:
    try:
        from src.core.config import get_settings

        s = get_settings()
        b = (s.platform_center_api_base or "").strip().rstrip("/")
        return b or None
    except Exception:
        return None


async def run(
    base_url: str,
    authorization: str,
    project_id: str,
    timeout: float,
 *,
    trust_env: bool,
    user_agent: str | None,
) -> int:
    base = base_url.rstrip("/")
    path = "ai/customer/projectInfo"
    headers = {"Authorization": _normalize_authorization(authorization)}
    params = {"projectId": project_id}

    # 与 http.client 接近：不显式协商 zstd/gzip（默认 identity），避免与少数服务端行为不一致
    client_default_headers = httpx.Headers({"Accept-Encoding": "identity"})
    if user_agent:
        client_default_headers["User-Agent"] = user_agent

    print(f"timeout={timeout}s (httpx)  trust_env={trust_env}  Accept-Encoding=identity（对齐 http.client 默认）")
    print("---")

    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(
            base_url=base,
            timeout=timeout,
            trust_env=trust_env,
            headers=client_default_headers,
        ) as client:
            req = client.build_request("GET", path, params=params, headers=headers)
            full_url = str(req.url)
            merged_headers = {k: v for k, v in req.headers.items()}
            print("请求方法: GET")
            print(f"请求 URL（完整）: {full_url}")
            print("请求头（全部，含 httpx 默认头）:")
            for name in sorted(merged_headers.keys()):
                print(f"  {name}: {merged_headers[name]}")
            print("---")
            resp = await client.send(req)
    except httpx.TimeoutException as e:
        elapsed = time.perf_counter() - t0
        print(f"FAIL: 超时 耗时={elapsed:.2f}s 错误={e}")
        print(
            "提示: Postman 能通而此处超时，可检查: (1) 环境变量 HTTP_PROXY/HTTPS_PROXY —— "
            "本脚本默认 trust_env=False（不走这些代理）；若 Postman 实际走了代理，请加 --trust-env。"
            "(2) WSL2 访问局域网 IP 与 Windows 上 Postman 路径不同，可在 PowerShell 里用 curl 对比。",
            file=sys.stderr,
        )
        return 1
    except httpx.RequestError as e:
        elapsed = time.perf_counter() - t0
        print(f"FAIL: 请求异常 耗时={elapsed:.2f}s 错误={e}")
        return 1

    elapsed = time.perf_counter() - t0
    print(f"HTTP {resp.status_code} 耗时={elapsed:.2f}s")

    ctype = (resp.headers.get("content-type") or "").lower()
    text = resp.text
    if "application/json" in ctype:
        try:
            body = resp.json()
            print(json.dumps(body, ensure_ascii=False, indent=2)[:8000])
            if len(json.dumps(body, ensure_ascii=False)) > 8000:
                print("... (已截断)")
        except json.JSONDecodeError:
            print(text[:2000])
    else:
        print(text[:2000])

    return 0 if resp.is_success else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="测试 GET ai/customer/projectInfo")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BIZ_TEST_BASE_URL") or _load_default_base_url(),
        help="API 根地址，如 http://192.168.1.249/api/sys；或环境变量 BIZ_TEST_BASE_URL",
    )
    parser.add_argument(
        "--token",
        "--authorization",
        dest="token",
        default=os.environ.get("BIZ_TEST_AUTHORIZATION"),
        help="Authorization 裸 token（无 Bearer 前缀）；或环境变量 BIZ_TEST_AUTHORIZATION",
    )
    parser.add_argument(
        "--project-id",
        default=os.environ.get("BIZ_TEST_PROJECT_ID", "2016029835456937984"),
        help="查询参数 projectId",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.environ.get("BIZ_TEST_TIMEOUT", "60")),
        help="httpx 超时（秒），默认 60",
    )
    parser.add_argument(
        "--trust-env",
        action="store_true",
        help="让 httpx 使用环境变量中的 HTTP_PROXY/HTTPS_PROXY/ALL_PROXY（默认关闭，与常见 Postman「不用系统代理」更接近）",
    )
    parser.add_argument(
        "--user-agent",
        default=os.environ.get("BIZ_TEST_USER_AGENT") or None,
        help="覆盖 User-Agent；不设则使用 httpx 默认。可设为与 Postman 一致以排除风控差异",
    )
    args = parser.parse_args()

    if not args.base_url:
        print("缺少 --base-url，或未配置 PLATFORM_CENTER_API_BASE / BIZ_TEST_BASE_URL", file=sys.stderr)
        sys.exit(2)
    if not args.token:
        print("缺少 --token，或环境变量 BIZ_TEST_AUTHORIZATION", file=sys.stderr)
        sys.exit(2)

    code = asyncio.run(
        run(
            base_url=args.base_url,
            authorization=args.token,
            project_id=args.project_id,
            timeout=args.timeout,
            trust_env=args.trust_env,
            user_agent=args.user_agent,
        )
    )
    sys.exit(code)


if __name__ == "__main__":
    main()
