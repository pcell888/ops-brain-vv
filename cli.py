#!/usr/bin/env python3
"""8000 诊断服务测试 CLI — 检查 /health、/api/diagnosis 等。"""

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

console = Console()
DEFAULT_BASE = "http://127.0.0.1:8000"


async def check_health(base_url: str) -> tuple[bool, str]:
    url = base_url.rstrip("/") + "/health"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(url)
            if r.status_code == 200:
                return True, json.dumps(r.json(), ensure_ascii=False)
            return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)


async def check_indicators(base_url: str) -> tuple[bool, str]:
    url = base_url.rstrip("/") + "/api/diagnosis/indicators"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return False, f"HTTP {r.status_code}"
            data = r.json()
            total = data.get("total", 0)
            dims = data.get("dimensions", [])
            return True, f"total={total} dimensions={dims}"
    except Exception as e:
        return False, str(e)


async def check_start(base_url: str, tenant_id: str, store_id: str) -> tuple[bool, str]:
    url = base_url.rstrip("/") + "/api/diagnosis/start"
    body = {
        "tenant_id": tenant_id,
        "store_id": store_id,
        "trigger_type": "manual",
        "triggered_by": "cli-test",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(url, json=body)
            if r.status_code != 200:
                return False, f"HTTP {r.status_code}: {r.text[:200]}"
            data = r.json()
            thread_id = data.get("thread_id")
            ws_url = data.get("ws_url", "")
            if not thread_id:
                return False, "无 thread_id"
            return True, f"thread_id={thread_id} ws_url={ws_url}"
    except Exception as e:
        return False, str(e)


async def run_diagnose(base_url: str, tenant_id: str, store_id: str) -> int:
    base_url = base_url or DEFAULT_BASE
    failed = 0

    console.print(Panel("[bold]8000 诊断服务[/bold]", style="dim"))
    console.print()

    console.print(Panel("[bold]/health[/bold]", style="dim"))
    ok, msg = await check_health(base_url)
    if ok:
        console.print(Text("OK ", style="bold green") + Text(msg, style="dim"))
    else:
        console.print(Text("FAIL ", style="bold red") + Text(msg, style="red"))
        failed += 1

    console.print()
    console.print(Panel("[bold]/api/diagnosis/indicators[/bold]", style="dim"))
    ok, msg = await check_indicators(base_url)
    if ok:
        console.print(Text("OK ", style="bold green") + Text(msg, style="dim"))
    else:
        console.print(Text("FAIL ", style="bold red") + Text(msg, style="red"))
        failed += 1

    console.print()
    console.print(Panel(f"[bold]/api/diagnosis/start[/bold] (tenant_id={tenant_id!r} store_id={store_id!r})", style="dim"))
    ok, msg = await check_start(base_url, tenant_id, store_id)
    if ok:
        console.print(Text("OK ", style="bold green") + Text(msg, style="dim"))
    else:
        console.print(Text("FAIL ", style="bold red") + Text(msg, style="red"))
        failed += 1

    return 1 if failed else 0


def main() -> int:
    p = argparse.ArgumentParser(description="8000 诊断服务测试")
    p.add_argument("--base-url", default=DEFAULT_BASE, help=f"服务 base URL（默认 {DEFAULT_BASE}）")
    p.add_argument("--tenant-id", default="wlwq_local", help="租户ID，需在 tenant_registry 中存在（默认 wlwq_local 指向本地 wlwq）")
    p.add_argument("--store-id", default="test-store", help="店铺ID（默认 test-store）")
    args = p.parse_args()
    return asyncio.run(run_diagnose(args.base_url, args.tenant_id, args.store_id))


if __name__ == "__main__":
    sys.exit(main())
