#!/usr/bin/env python3
"""wlwq 服务测试诊断 CLI — 检查 MySQL、HTTP 健康及关键 API。"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.wlwq.config import get_mysql_config

console = Console()


async def check_mysql() -> tuple[bool, str]:
    """检查 MySQL 连接。"""
    try:
        import aiomysql
    except ImportError:
        return False, "aiomysql 未安装"
    cfg = get_mysql_config()
    try:
        conn = await aiomysql.connect(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
            db=cfg["db"],
        )
        await conn.ping()
        conn.close()
        return True, f"{cfg['user']}@{cfg['host']}:{cfg['port']}/{cfg['db']}"
    except Exception as e:
        return False, str(e)


async def check_http_health(base_url: str) -> tuple[bool, str]:
    """检查 /health 接口。"""
    url = base_url.rstrip("/") + "/health"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(url)
            if r.status_code == 200:
                data = r.json()
                return True, json.dumps(data, ensure_ascii=False)
            return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)


async def check_api(base_url: str, path: str, name: str) -> tuple[bool, str]:
    """检查单个 API 是否返回 code=0。"""
    url = base_url.rstrip("/") + path
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return False, f"HTTP {r.status_code}"
            data = r.json()
            code = data.get("code", -1)
            if code != 0:
                return False, data.get("msg", str(data))
            return True, json.dumps(data.get("data", {}), ensure_ascii=False)[:120]
    except Exception as e:
        return False, str(e)


async def run_diagnose(base_url: str | None, mysql_only: bool) -> int:
    """执行诊断，返回退出码 0=全通过 1=有失败。"""
    base_url = base_url or "http://127.0.0.1:8200"
    failed = 0

    # MySQL
    console.print(Panel("[bold]MySQL[/bold]", style="dim"))
    ok, msg = await check_mysql()
    if ok:
        console.print(Text("OK ", style="bold green") + Text(msg, style="dim"))
    else:
        console.print(Text("FAIL ", style="bold red") + Text(msg, style="red"))
        failed += 1

    if mysql_only:
        return 1 if failed else 0

    # HTTP /health
    console.print()
    console.print(Panel("[bold]HTTP /health[/bold]", style="dim"))
    ok, msg = await check_http_health(base_url)
    if ok:
        console.print(Text("OK ", style="bold green") + Text(msg, style="dim"))
    else:
        console.print(Text("FAIL ", style="bold red") + Text(msg, style="red"))
        failed += 1

    # API 抽样
    apis = [
        ("/client-record/statistics", "client-record/statistics"),
        ("/sales-contract/statistics", "sales-contract/statistics"),
        ("/examine-initiate/follow-stats", "examine-initiate/follow-stats"),
        ("/service-order/completion-stats", "mock service-order/completion-stats"),
    ]
    console.print()
    table = Table(title="API 抽样", show_header=True, header_style="bold")
    table.add_column("状态", width=6)
    table.add_column("接口", width=32)
    table.add_column("详情", overflow="fold")
    for path, name in apis:
        ok, msg = await check_api(base_url, path, name)
        detail = (msg[:60] + "...") if len(msg) > 60 else msg
        if ok:
            table.add_row("[bold green]OK[/bold green]", name, detail)
        else:
            table.add_row("[bold red]FAIL[/bold red]", name, msg)
            failed += 1
    console.print(table)

    return 1 if failed else 0


def main() -> int:
    p = argparse.ArgumentParser(description="wlwq 服务测试诊断")
    p.add_argument("--base-url", default="http://127.0.0.1:8200", help="wlwq 服务 base URL（默认 8200）")
    p.add_argument("--mysql-only", action="store_true", help="仅检查 MySQL")
    args = p.parse_args()
    return asyncio.run(run_diagnose(args.base_url, args.mysql_only))


if __name__ == "__main__":
    sys.exit(main())
