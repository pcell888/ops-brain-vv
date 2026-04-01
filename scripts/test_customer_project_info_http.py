#!/usr/bin/env python3
"""Standalone test: GET /api/sys/ai/customer/projectInfo via http.client.

默认与此前手写示例一致；可用环境变量或命令行覆盖，避免把 token 写死在仓库里。

示例:
  uv run python scripts/test_customer_project_info_http.py
  HOST=192.168.1.249 PORT=8083 uv run python scripts/test_customer_project_info_http.py
  uv run python scripts/test_customer_project_info_http.py --timeout 30

说明: .env 里 PLATFORM_CENTER_API_BASE 无端口时即 80；若仍超时，多为本机到 192.168.* 不可达。

WSL 里超时、Windows 里正常: WSL2 默认是独立虚拟网卡，访问局域网行为常与宿主机不一致。
可行做法（任选）:
  1) 在 Windows 下跑同一脚本（PowerShell / 「适用于 Linux」外的本机 Python），HOST 仍填 192.168.*。
  2) 开启 WSL「镜像网络」: 用户目录下 `.wslconfig` 增加 [wsl2] networkingMode=mirrored，
     保存后 `wsl --shutdown` 再开 WSL，使 WSL 与 Windows 共用上网方式以便访问同网段。
  3) 仍不行时再查 VPN/防火墙是否仅对 Windows 网卡生效。
"""

from __future__ import annotations

import argparse
import errno
import http.client
import os
import sys


def _parse_port(raw: str | None, default: int) -> int:
    if not raw:
        return default
    return int(raw, 10)


def _is_timeout(err: BaseException) -> bool:
    if isinstance(err, TimeoutError):
        return True
    if isinstance(err, OSError) and err.errno in (errno.ETIMEDOUT, errno.EHOSTUNREACH):
        return True
    msg = str(err).lower()
    return "timed out" in msg or "timeout" in msg


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--host",
        default=os.environ.get("HOST", "192.168.1.249"),
        help="目标主机（默认 env HOST 或 192.168.1.249）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=_parse_port(os.environ.get("PORT"), 80),
        help="端口（默认 env PORT 或 80；与 PLATFORM_CENTER_API_BASE 中 :port 一致）",
    )
    parser.add_argument(
        "--project-id",
        default=os.environ.get("PROJECT_ID", "2016029835456937984"),
        help="projectId 查询参数",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get(
            "TOKEN",
            os.environ.get(
                "BIZ_TEST_AUTHORIZATION",
                "cb5f7be9-fde3-4026-885f-0d42f8046b29",
            ),
        ),
        help="Authorization 头（裸 token；可用 env TOKEN 或 BIZ_TEST_AUTHORIZATION）",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.environ.get("HTTP_TEST_TIMEOUT", "30")),
        help="连接/读超时秒数（默认 30）",
    )
    args = parser.parse_args()

    path = f"/api/sys/ai/customer/projectInfo?projectId={args.project_id}"
    headers = {"authorization": args.token}
    conn = http.client.HTTPConnection(args.host, args.port, timeout=args.timeout)

    try:
        conn.request("GET", path, "", headers)
        res = conn.getresponse()
        body = res.read()
        print(f"status: {res.status} {res.reason}")
        print(body.decode("utf-8"))
    except (OSError, TimeoutError) as e:
        print(f"network error: {e}", file=sys.stderr)
        print(
            f"  request: http://{args.host}:{args.port}{path} (timeout={args.timeout}s)",
            file=sys.stderr,
        )
        if _is_timeout(e):
            print(
                "  连接超时：请确认本机能访问该地址（同网段/VPN、WSL 能否访问宿主机局域网）、"
                "服务是否在运行；若中台实际监听非 80 端口，请设置 --port 或环境变量 PORT。",
                file=sys.stderr,
            )
        return 1
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
