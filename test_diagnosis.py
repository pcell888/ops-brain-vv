#!/usr/bin/env python3
"""诊断自动化测试 — 输入 tenant_id 自动执行诊断流程。"""

from __future__ import annotations

import asyncio
import json
import sys

import httpx
import websockets
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

BASE_URL = "http://127.0.0.1:8000"
API_PREFIX = "/api/v1"
AUTH_TOKEN = "mock"


async def run_diagnosis(tenant_id: str, store_id: str = "") -> None:
    """执行完整诊断流程。"""
    console.print(
        Panel(
            f"[bold cyan]开始诊断[/bold cyan]\ntenant_id: {tenant_id}\nstore_id: {store_id or '(全企业)'}",
            border_style="cyan",
        )
    )

    # 1. 启动诊断
    console.print("\n[yellow]>>> 启动诊断...[/yellow]")
    start_url = f"{BASE_URL}{API_PREFIX}/diagnosis/start"
    body = {
        "tenant_id": tenant_id,
        "store_id": store_id,
        "trigger_type": "manual",
        "auth_token": AUTH_TOKEN,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(start_url, json=body)
        if r.status_code != 200:
            console.print(f"[red]启动失败: HTTP {r.status_code} - {r.text[:200]}[/red]")
            return
        data = r.json()
        thread_id = data.get("thread_id")
        ws_url = data.get("ws_url", "")
        console.print(f"[green]✓[/green] thread_id: {thread_id}")

    # 2. WebSocket 监听进度
    console.print("\n[yellow]>>> 等待诊断完成...[/yellow]")
    ws_full_url = ws_url if ws_url.startswith("ws") else f"ws://127.0.0.1:8000{ws_url}"

    try:
        async with websockets.connect(ws_full_url, close_timeout=5, open_timeout=10) as ws:
            while True:
                raw = await asyncio.wait_for(ws.recv(), timeout=300.0)
                msg = json.loads(raw)
                msg_type = msg.get("type", "")
                message = msg.get("message", "")
                percent = msg.get("percent")

                # 显示进度
                if percent is not None:
                    bar = "█" * (percent // 5) + "░" * (20 - percent // 5)
                    console.print(f"  [{bar}] {percent}% {message}")
                elif message:
                    console.print(f"  [dim]{message}[/dim]")

                if msg_type in ("completed", "error"):
                    break
    except Exception as e:
        console.print(f"[red]WebSocket 异常: {e}[/red]")

    # 3. 获取报告
    console.print("\n[yellow]>>> 获取诊断报告...[/yellow]")
    report_url = f"{BASE_URL}{API_PREFIX}/diagnosis/{thread_id}/report"
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(report_url)
        if r.status_code != 200:
            console.print(f"[red]获取报告失败: HTTP {r.status_code}[/red]")
            return
        report = r.json()

    # 4. 打印报告摘要
    _print_report_summary(report)
    console.print(Panel("[bold green]诊断完成[/bold green]", border_style="green"))


def _print_report_summary(report: dict) -> None:
    """打印诊断报告摘要。"""
    health = report.get("health_score")
    anomalies = report.get("anomalies") or []
    root_causes = report.get("root_causes") or []
    dim_scores = report.get("dimension_scores") or {}

    health_val = float(health) if health is not None else 0
    if health_val >= 80:
        level = "[green]优秀[/green]"
    elif health_val >= 60:
        level = "[yellow]一般[/yellow]"
    else:
        level = "[red]预警[/red]"

    console.print()
    t = Table(title="诊断结果", show_header=True, header_style="bold magenta")
    t.add_column("项目", style="cyan", width=15)
    t.add_column("结果", style="white")
    t.add_row("健康评分", f"[bold]{health_val:.1f}[/bold] ({level})")
    t.add_row("异常指标数", str(len(anomalies)))
    t.add_row("根因分析数", str(len(root_causes)))
    console.print(t)

    if dim_scores:
        t2 = Table(title="维度得分", show_header=True, header_style="bold blue")
        t2.add_column("维度", style="cyan")
        t2.add_column("分数", style="green")
        t2.add_column("权重", style="white")
        for dim, item in dim_scores.items():
            if isinstance(item, dict):
                t2.add_row(str(dim), str(item.get("score", "-")), str(item.get("weight", "-")))
            else:
                t2.add_row(str(dim), str(item), "-")
        console.print(t2)

    if anomalies:
        t3 = Table(title="异常指标", show_header=True, header_style="bold red")
        t3.add_column("指标", style="cyan")
        t3.add_column("说明", style="white")
        t3.add_column("严重度", style="yellow")
        for a in anomalies[:5]:
            t3.add_row(
                str(a.get("indicator_name", a.get("indicator_code", ""))),
                str(a.get("description", ""))[:50],
                str(a.get("severity", "-")),
            )
        if len(anomalies) > 5:
            t3.add_row("...", f"共 {len(anomalies)} 项异常", "...")
        console.print(t3)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="诊断自动化测试工具")
    parser.add_argument("tenant_id", nargs="?", help="租户ID")
    parser.add_argument("store_id", nargs="?", default="", help="店铺ID（可选，默认全企业）")
    args = parser.parse_args()

    if args.tenant_id:
        # 命令行模式
        try:
            asyncio.run(run_diagnosis(args.tenant_id, args.store_id))
        except Exception as e:
            console.print(f"[red]执行异常: {e}[/red]")
    else:
        # 交互模式
        console.print(Panel("[bold]诊断自动化测试工具[/bold]\n输入 tenant_id 后回车开始诊断", border_style="blue"))
        while True:
            console.print()
            tenant_id = input("请输入 tenant_id (输入 q 退出): ").strip()
            if tenant_id.lower() == "q":
                console.print("[dim]再见![/dim]")
                break
            if not tenant_id:
                console.print("[yellow]tenant_id 不能为空[/yellow]")
                continue
            store_id = input("请输入 store_id (回车跳过=全企业诊断): ").strip()
            try:
                asyncio.run(run_diagnosis(tenant_id, store_id))
            except KeyboardInterrupt:
                console.print("\n[yellow]已取消[/yellow]")
            except Exception as e:
                console.print(f"[red]执行异常: {e}[/red]")


if __name__ == "__main__":
    main()
