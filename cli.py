#!/usr/bin/env python3
"""8000 诊断服务测试 CLI — 检查 /health、/api/v1/diagnosis 等，支持完整诊断流程与进度推送。"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from urllib.parse import urlparse

import httpx
import websockets
from websockets.exceptions import ConnectionClosed
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()
DEFAULT_BASE = "http://127.0.0.1:8000"
API_PREFIX = "/api/v1"
FINAL_TYPES = ("completed", "error")


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


async def check_history(base_url: str, tenant_id: str, store_id: str) -> tuple[bool, str]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/diagnosis/history?tenant_id={tenant_id}&store_id={store_id}&page=1&page_size=5"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return False, f"HTTP {r.status_code}"
            data = r.json()
            total = data.get("total", 0)
            return True, f"total={total} 条"
    except Exception as e:
        return False, str(e)


async def check_indicators(base_url: str) -> tuple[bool, str]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/diagnosis/indicators"
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


def _http_to_ws(base_url: str, path: str) -> str:
    p = urlparse(base_url)
    scheme = "wss" if p.scheme == "https" else "ws"
    netloc = p.netloc or "127.0.0.1:8000"
    return f"{scheme}://{netloc}{path}"

async def check_start(base_url: str, tenant_id: str, store_id: str) -> tuple[bool, str, dict | None]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/diagnosis/start"
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
                return False, f"HTTP {r.status_code}: {r.text[:200]}", None
            data = r.json()
            thread_id = data.get("thread_id")
            ws_url = data.get("ws_url", "")
            if not thread_id:
                return False, "无 thread_id", None
            return True, f"thread_id={thread_id} ws_url={ws_url}", data
    except Exception as e:
        return False, str(e), None


def _format_progress(msg: dict) -> str:
    t = msg.get("type", "")
    if t == "node_start":
        return f"[节点开始] {msg.get('node', '')}"
    if t == "node_complete":
        return f"[节点完成] {msg.get('node', '')}"
    if t == "progress":
        return msg.get("message", "")
    if t == "diagnosis_result":
        return f"健康分={msg.get('health_score')} 异常数={msg.get('anomaly_count', 0)}"
    if t == "solutions_ready":
        plans = msg.get("plans") or []
        return f"方案已生成 {len(plans)} 个"
    if t == "waiting_adoption":
        return msg.get("message", "方案已生成，请选择需要采纳的方案")
    if t == "adoption_received":
        return msg.get("message", "")
    if t == "completed":
        return f"[完成] {msg.get('message', '')}"
    if t == "error":
        return f"[错误] {msg.get('message', '')}"
    if t in ("pong",):
        return ""
    return json.dumps(msg, ensure_ascii=False)


async def _fetch_solutions(base_url: str, thread_id: str) -> list[dict]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/solutions/{thread_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            if r.status_code == 200:
                return (r.json().get("solution_plans") or [])[:]
            return []
    except Exception:
        return []


def _interactive_adopt(plans: list[dict]) -> list[str]:
    """展示方案列表并提示用户输入要采纳的 plan_id，返回采纳的 id 列表。"""
    if not plans:
        console.print(Text("  无方案可选。", style="dim"))
        return []
    table = Table(title="优化方案列表", show_header=True, header_style="bold")
    table.add_column("plan_id", style="cyan")
    table.add_column("方案名称", style="white")
    table.add_column("优先级", style="green")
    for p in plans:
        table.add_row(
            p.get("plan_id", ""),
            p.get("plan_name", ""),
            p.get("priority_level", ""),
        )
    console.print(table)
    prompt = "输入要采纳的方案 ID（逗号分隔），留空则不采纳: "
    selected = input(prompt)
    chosen = [x.strip() for x in (selected or "").strip().split(",") if x.strip()]
    return [pid for pid in chosen if any(p.get("plan_id") == pid for p in plans)]


def _resolve_ws_url(base_url: str, ws_url: str | None, thread_id: str) -> str:
    if ws_url:
        if ws_url.startswith(("ws://", "wss://")):
            return ws_url
        return _http_to_ws(base_url, ws_url)
    return _http_to_ws(base_url, f"{API_PREFIX}/ws/diagnosis/{thread_id}")


async def run_ws_progress(
    base_url: str,
    thread_id: str,
    adopt_plan_ids: list[str] | None,
    ws_url: str | None = None,
) -> tuple[bool, list[dict]]:
    ws_url = _resolve_ws_url(base_url, ws_url, thread_id)
    received: list[dict] = []
    done = False
    success = False
    try:
        async with websockets.connect(ws_url, close_timeout=2, open_timeout=10) as ws:
            while not done:
                raw = await asyncio.wait_for(ws.recv(), timeout=300.0)
                msg = json.loads(raw)
                received.append(msg)
                t = msg.get("type", "")
                line = _format_progress(msg)
                if line:
                    console.print(Text("  ", style="dim") + Text(line, style="cyan"))
                if t == "waiting_adoption":
                    if adopt_plan_ids is not None:
                        await ws.send(json.dumps({"action": "adopt_plans", "plan_ids": adopt_plan_ids}))
                    else:
                        plans = next((m.get("plans") or [] for m in reversed(received) if m.get("type") == "solutions_ready"), [])
                        if not plans:
                            plans = await _fetch_solutions(base_url, thread_id)
                        chosen = await asyncio.to_thread(_interactive_adopt, plans)
                        await ws.send(json.dumps({"action": "adopt_plans", "plan_ids": chosen}))
                if t in FINAL_TYPES:
                    done = True
                    success = t == "completed"
    except asyncio.TimeoutError:
        console.print(Text("  [超时] 未在 300s 内收到 completed/error", style="yellow"))
    except ConnectionClosed as e:
        if any(m.get("type") in ("adoption_received", "completed") for m in received):
            success = True
        else:
            console.print(Text(f"  [WS 连接关闭] {e}", style="red"))
    except Exception as e:
        if any(m.get("type") in ("adoption_received", "completed") for m in received):
            success = True
        else:
            console.print(Text(f"  [WS 异常] {e}", style="red"))
    return success, received


async def run_diagnose(base_url: str, tenant_id: str, store_id: str, adopt_plan_ids: list[str] | None = None) -> int:
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
    console.print(Panel("[bold]/api/v1/diagnosis/indicators[/bold]", style="dim"))
    ok, msg = await check_indicators(base_url)
    if ok:
        console.print(Text("OK ", style="bold green") + Text(msg, style="dim"))
    else:
        console.print(Text("FAIL ", style="bold red") + Text(msg, style="red"))
        failed += 1

    console.print()
    console.print(Panel(f"[bold]/api/v1/diagnosis/start[/bold] (tenant_id={tenant_id!r} store_id={store_id!r})", style="dim"))
    ok, msg, start_data = await check_start(base_url, tenant_id, store_id)
    if ok:
        console.print(Text("OK ", style="bold green") + Text(msg, style="dim"))
        thread_id = start_data.get("thread_id") if start_data else None
        if thread_id:
            console.print()
            console.print(Panel("[bold]WebSocket 进度推送[/bold]", style="dim"))
            ws_ok, _ = await run_ws_progress(base_url, thread_id, adopt_plan_ids, start_data.get("ws_url"))
            if not ws_ok:
                failed += 1
                console.print(Text("进度流未正常完成 (completed)", style="red"))
            console.print()
            console.print(Panel("[bold]/api/v1/diagnosis/history[/bold] (验证落库)", style="dim"))
            ok, msg = await check_history(base_url, tenant_id, store_id)
            if ok:
                console.print(Text("OK ", style="bold green") + Text(msg, style="dim"))
            else:
                console.print(Text("FAIL ", style="bold red") + Text(msg, style="red"))
                failed += 1
    else:
        console.print(Text("FAIL ", style="bold red") + Text(msg, style="red"))
        failed += 1

    return 1 if failed else 0


def main() -> int:
    p = argparse.ArgumentParser(description="8000 诊断服务测试（含完整诊断流程与进度推送）")
    p.add_argument("--base-url", default=DEFAULT_BASE, help=f"服务 base URL（默认 {DEFAULT_BASE}）")
    p.add_argument("--tenant-id", default="wlwq_local", help="租户ID（默认 wlwq_local）")
    p.add_argument("--store-id", default="test-store", help="店铺ID（默认 test-store）")
    p.add_argument("--adopt", action="append", metavar="PLAN_ID", help="收到方案后采纳的 plan_id，可多次指定；不指定则仅跑到 waiting_adoption")
    args = p.parse_args()
    adopt_ids = args.adopt if args.adopt else None
    return asyncio.run(run_diagnose(args.base_url, args.tenant_id, args.store_id, adopt_ids))


if __name__ == "__main__":
    sys.exit(main())
