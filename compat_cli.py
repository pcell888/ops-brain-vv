#!/usr/bin/env python3
"""兼容层 CLI：仅调用兼容接口，支持启动诊断、轮询状态、查看报告、方案采纳与钻取。"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()
DEFAULT_BASE = "http://127.0.0.1:8100"
API_PREFIX = "/api/v1"
FINAL_TYPES = ("completed", "failed", "error")


def _fmt_time(raw: object) -> str:
    if raw is None:
        return "-"
    if not isinstance(raw, str):
        return str(raw)
    s = raw.strip()
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            return raw
        return dt.astimezone(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(raw)


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


async def check_diagnosis_list(base_url: str, enterprise_id: str) -> tuple[bool, str]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/diagnosis/list"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, params={"enterprise_id": enterprise_id, "skip": 0, "limit": 5})
            if r.status_code != 200:
                return False, f"HTTP {r.status_code}: {r.text[:200]}"
            data = r.json()
            total = data.get("total", 0)
            return True, f"total={total} 条"
    except Exception as e:
        return False, str(e)


async def check_benchmark_dimensions(base_url: str) -> tuple[bool, str]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/diagnosis/benchmarks/dimension-scores"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, params={"industry": "general"})
            if r.status_code != 200:
                return False, f"HTTP {r.status_code}: {r.text[:200]}"
            data = r.json()
            items = data.get("dimension_scores") or []
            return True, f"industry={data.get('industry', '-')} dimensions={len(items)}"
    except Exception as e:
        return False, str(e)


async def start_diagnosis(base_url: str, enterprise_id: str) -> tuple[bool, str, dict | None]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/diagnosis/start"
    body = {
        "enterprise_id": enterprise_id,
        "trigger_type": "manual",
        "async_mode": True,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(url, json=body)
            if r.status_code != 200:
                return False, f"HTTP {r.status_code}: {r.text[:200]}", None
            data = r.json()
            diagnosis_id = data.get("diagnosis_id")
            if not diagnosis_id:
                return False, "响应缺少 diagnosis_id", None
            return True, f"diagnosis_id={diagnosis_id} status={data.get('status', '-')}", data
    except Exception as e:
        return False, str(e), None


async def fetch_status(base_url: str, diagnosis_id: str) -> tuple[bool, dict | str]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/diagnosis/status/{diagnosis_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return False, f"HTTP {r.status_code}: {r.text[:200]}"
            data = r.json()
            return True, data if isinstance(data, dict) else {}
    except Exception as e:
        return False, str(e)


async def wait_status_done(
    base_url: str,
    diagnosis_id: str,
    poll_interval: float,
    timeout_seconds: int,
) -> tuple[bool, dict | None]:
    started = asyncio.get_running_loop().time()
    while True:
        ok, data_or_msg = await fetch_status(base_url, diagnosis_id)
        if not ok:
            console.print(Text(f"状态查询失败: {data_or_msg}", style="red"))
            return False, None
        assert isinstance(data_or_msg, dict)
        status = str(data_or_msg.get("status", ""))
        progress = data_or_msg.get("progress", 0)
        message = data_or_msg.get("message", "")
        console.print(Text(f"  [{status}] {progress}% {message}", style="cyan"))
        if status in FINAL_TYPES:
            return status == "completed", data_or_msg
        if asyncio.get_running_loop().time() - started >= timeout_seconds:
            timeout_tip = f"轮询超时（>{timeout_seconds}s）"
            if status == "running" and int(progress or 0) >= 80:
                timeout_tip += "，当前处于方案生成阶段，可重试并增大 --timeout（如 600）"
            console.print(Text(timeout_tip, style="yellow"))
            return False, data_or_msg
        await asyncio.sleep(poll_interval)


async def fetch_report(base_url: str, diagnosis_id: str) -> tuple[bool, dict | str]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/diagnosis/report/{diagnosis_id}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return False, f"HTTP {r.status_code}: {r.text[:200]}"
            data = r.json()
            return True, data if isinstance(data, dict) else {}
    except Exception as e:
        return False, str(e)


async def fetch_solutions(base_url: str, diagnosis_id: str) -> tuple[bool, dict | str]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/solutions/list/{diagnosis_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            if r.status_code == 200:
                return True, r.json()
            return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)


async def fetch_drill_down(
    base_url: str,
    metric_name: str,
    enterprise_id: str,
    page: int = 1,
    page_size: int = 10,
) -> tuple[bool, dict | str]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/diagnosis/drill-down/{metric_name}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                url,
                params={
                    "enterprise_id": enterprise_id,
                    "page": page,
                    "page_size": page_size,
                },
            )
            if r.status_code != 200:
                return False, f"HTTP {r.status_code}: {r.text[:200]}"
            return True, r.json()
    except Exception as e:
        return False, str(e)


async def fetch_anomaly_detail(base_url: str, diagnosis_id: str, anomaly_id: str) -> tuple[bool, dict | str]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/diagnosis/anomaly/{diagnosis_id}/{anomaly_id}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return False, f"HTTP {r.status_code}: {r.text[:200]}"
            return True, r.json()
    except Exception as e:
        return False, str(e)


async def adopt_solution(base_url: str, solution_id: str) -> tuple[bool, dict | str]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/solutions/{solution_id}/adopt"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.put(url)
            if r.status_code != 200:
                return False, f"HTTP {r.status_code}: {r.text[:200]}"
            return True, r.json()
    except Exception as e:
        return False, str(e)


async def fetch_adopt_progress(base_url: str, solution_id: str) -> tuple[bool, dict | str]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/solutions/{solution_id}/adopt/progress"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return False, f"HTTP {r.status_code}: {r.text[:200]}"
            return True, r.json()
    except Exception as e:
        return False, str(e)


async def wait_adopt_done(base_url: str, solution_id: str, poll_interval: float, timeout_seconds: int) -> bool:
    started = asyncio.get_running_loop().time()
    while True:
        ok, data_or_msg = await fetch_adopt_progress(base_url, solution_id)
        if not ok:
            console.print(Text(f"采纳进度查询失败: {data_or_msg}", style="red"))
            return False
        assert isinstance(data_or_msg, dict)
        status = str(data_or_msg.get("status", ""))
        percent = data_or_msg.get("percent", 0)
        message = data_or_msg.get("message", "")
        console.print(Text(f"  [adopt:{status}] {percent}% {message}", style="cyan"))
        if status in FINAL_TYPES:
            return status == "completed"
        if asyncio.get_running_loop().time() - started >= timeout_seconds:
            console.print(Text(f"采纳进度轮询超时（>{timeout_seconds}s）", style="yellow"))
            return False
        await asyncio.sleep(poll_interval)


def print_report(report: dict) -> None:
    health = (report.get("health_score") or {}).get("total_score")
    status = report.get("status", "-")
    anomalies = report.get("anomalies") or []
    root_causes = report.get("root_cause_analyses") or []

    console.print(
        Panel(
            f"[bold cyan]兼容诊断报告[/bold cyan]\n[dim]diagnosis_id={report.get('diagnosis_id', '-')}[/dim]",
            border_style="cyan",
        )
    )

    overview = Table(show_header=False, box=None, pad_edge=False)
    overview.add_column("k", style="cyan", no_wrap=True, width=12)
    overview.add_column("v", style="white")
    overview.add_row("创建时间", _fmt_time(report.get("created_at")))
    overview.add_row("完成时间", _fmt_time(report.get("completed_at")))
    overview.add_row("状态", str(status))
    overview.add_row("健康分", str(health if health is not None else "-"))
    overview.add_row("异常指标数", str(len(anomalies)))
    overview.add_row("根因条目数", str(len(root_causes)))
    console.print(Panel(overview, title="总览", border_style="blue"))

    dims = (report.get("health_score") or {}).get("dimension_scores") or []
    if dims:
        t = Table(title="维度得分", show_header=True, header_style="bold magenta")
        t.add_column("维度", style="cyan")
        t.add_column("分数", style="green")
        t.add_column("权重", style="white")
        t.add_column("状态", style="yellow")
        for d in dims:
            t.add_row(
                str(d.get("dimension", "")),
                str(d.get("score", "")),
                str(d.get("weight", "")),
                str(d.get("status", "")),
            )
        console.print(t)

    if anomalies:
        t = Table(title="异常指标（兼容）", show_header=True, header_style="bold red")
        t.add_column("序号", style="magenta")
        t.add_column("ID", style="cyan")
        t.add_column("指标", style="cyan")
        t.add_column("维度", style="white")
        t.add_column("偏差%", style="yellow")
        for i, a in enumerate(anomalies, start=1):
            t.add_row(
                str(i),
                str(a.get("id", "")),
                str(a.get("rule_name") or a.get("metric_name", "")),
                str(a.get("dimension", "")),
                str(a.get("gap_percentage", "-")),
            )
        console.print(t)


def print_solution_list(data: dict) -> None:
    solutions = data.get("solutions") or []
    if not solutions:
        console.print(Text("无优化方案。", style="yellow"))
        return
    t = Table(title="优化方案列表（兼容）", show_header=True, header_style="bold")
    t.add_column("solution_id", style="cyan")
    t.add_column("方案名称", style="white")
    t.add_column("优先级", style="green")
    t.add_column("score", style="yellow")
    t.add_column("status", style="magenta")
    for s in solutions:
        t.add_row(
            str(s.get("solution_id", "")),
            str(s.get("name", "")),
            str(s.get("priority_level", "")),
            str(s.get("score", "")),
            str(s.get("status", "")),
        )
    console.print(t)


def print_drill_down(data: dict) -> None:
    rows = data.get("data") or []
    labels = data.get("field_labels") or {}
    console.print(
        Text(
            f"指标: {data.get('metric_name', '-')}  总数: {data.get('total', 0)}  "
            f"分页: {data.get('page', 1)}",
            style="dim",
        )
    )
    if not rows:
        console.print(Text("无钻取数据。", style="yellow"))
        return
    keys = list(labels.keys()) if isinstance(labels, dict) and labels else list(rows[0].keys())
    t = Table(title="指标钻取结果(前10)", show_header=True, header_style="bold")
    for k in keys:
        t.add_column(str(labels.get(k, k)), style="white")
    for row in rows[:10]:
        t.add_row(*[str((row or {}).get(k, "")) for k in keys])
    console.print(t)


async def post_actions(base_url: str, diagnosis_id: str, report: dict, enterprise_id: str, poll_interval: float) -> None:
    while True:
        console.print()
        console.print(Panel("[bold]接下来可执行[/bold]\n1. 查看 优化方案列表\n2. 查看 钻取 某个 指标数据\n3. 查看 某个 异常指标详情\n4. 采纳某个方案并查看进度\n0. 结束", style="dim"))
        choice = (input("请输入选项编号: ") or "").strip()
        if choice == "0":
            break
        if choice == "1":
            ok, data_or_msg = await fetch_solutions(base_url, diagnosis_id)
            if ok and isinstance(data_or_msg, dict):
                print_solution_list(data_or_msg)
            else:
                console.print(Text(f"查询失败: {data_or_msg}", style="red"))
            continue
        if choice == "2":
            metric_name = (input("请输入 metric_name（指标 code）: ") or "").strip()
            if not metric_name:
                console.print(Text("metric_name 不能为空。", style="yellow"))
                continue
            ok, data_or_msg = await fetch_drill_down(base_url, metric_name, enterprise_id)
            if ok and isinstance(data_or_msg, dict):
                print_drill_down(data_or_msg)
            else:
                console.print(Text(f"查询失败: {data_or_msg}", style="red"))
            continue
        if choice == "3":
            raw_input = (input("请输入异常指标 ID 或序号: ") or "").strip()
            anomalies = report.get("anomalies") or []
            anomaly_id = raw_input
            if raw_input.isdigit():
                idx = int(raw_input) - 1
                if 0 <= idx < len(anomalies):
                    anomaly_id = str((anomalies[idx] or {}).get("id", "")).strip()
            if not anomaly_id:
                console.print(Text("异常指标 ID 不能为空。", style="yellow"))
                continue
            ok, detail_or_msg = await fetch_anomaly_detail(base_url, diagnosis_id, anomaly_id)
            if ok and isinstance(detail_or_msg, dict):
                console.print(Panel(json.dumps(detail_or_msg, ensure_ascii=False, indent=2), title="异常指标详情", style="dim"))
            else:
                console.print(Text(f"查询失败: {detail_or_msg}", style="red"))
            continue
        if choice == "4":
            sid = (input("请输入 solution_id: ") or "").strip()
            if not sid:
                console.print(Text("solution_id 不能为空。", style="yellow"))
                continue
            ok, msg_or_data = await adopt_solution(base_url, sid)
            if not ok:
                console.print(Text(f"采纳失败: {msg_or_data}", style="red"))
                continue
            console.print(Text(f"采纳已提交: {msg_or_data}", style="green"))
            await wait_adopt_done(base_url, sid, poll_interval, 300)
            continue
        console.print(Text("无效选项，请输入 0/1/2/3/4。", style="yellow"))


async def run_solutions_by_diagnosis_id(base_url: str, diagnosis_id: str) -> int:
    did = diagnosis_id.strip()
    if not did:
        console.print(Text("诊断ID 不能为空。", style="red"))
        return 2
    console.print(Panel("[bold]按诊断ID查看优化方案（兼容）[/bold]", style="dim"))
    ok, data_or_msg = await fetch_solutions(base_url, did)
    if not ok:
        console.print(Text(f"请求失败: {data_or_msg}", style="red"))
        return 1
    assert isinstance(data_or_msg, dict)
    print_solution_list(data_or_msg)
    return 0


async def run_diagnose(
    base_url: str,
    enterprise_id: str,
    adopt_solution_id: str | None,
    poll_interval: float,
    timeout_seconds: int,
) -> int:
    failed = 0
    console.print(Panel("[bold]兼容层诊断 CLI[/bold]", style="dim"))
    console.print()

    console.print(Panel("[bold]/health[/bold]", style="dim"))
    ok, msg = await check_health(base_url)
    if ok:
        console.print(Text("OK ", style="bold green") + Text(msg, style="dim"))
    else:
        console.print(Text("FAIL ", style="bold red") + Text(msg, style="red"))
        failed += 1

    console.print()
    console.print(Panel("[bold]/api/v1/diagnosis/list[/bold]", style="dim"))
    ok, msg = await check_diagnosis_list(base_url, enterprise_id)
    if ok:
        console.print(Text("OK ", style="bold green") + Text(msg, style="dim"))
    else:
        console.print(Text("FAIL ", style="bold red") + Text(msg, style="red"))
        failed += 1

    console.print()
    console.print(Panel("[bold]/api/v1/diagnosis/benchmarks/dimension-scores[/bold]", style="dim"))
    ok, msg = await check_benchmark_dimensions(base_url)
    if ok:
        console.print(Text("OK ", style="bold green") + Text(msg, style="dim"))
    else:
        console.print(Text("FAIL ", style="bold red") + Text(msg, style="red"))
        failed += 1

    console.print()
    console.print(Panel(f"[bold]/api/v1/diagnosis/start[/bold] (enterprise_id={enterprise_id!r})", style="dim"))
    ok, msg, start_data = await start_diagnosis(base_url, enterprise_id)
    if not ok:
        console.print(Text("FAIL ", style="bold red") + Text(msg, style="red"))
        return 1 if failed else 1
    console.print(Text("OK ", style="bold green") + Text(msg, style="dim"))

    diagnosis_id = (start_data or {}).get("diagnosis_id")
    if not diagnosis_id:
        console.print(Text("FAIL diagnosis_id 缺失", style="red"))
        return 1 if failed else 1

    console.print()
    console.print(Panel("[bold]/api/v1/diagnosis/status/{diagnosis_id} (轮询)[/bold]", style="dim"))
    done_ok, _ = await wait_status_done(base_url, diagnosis_id, poll_interval, timeout_seconds)
    if not done_ok:
        failed += 1

    console.print()
    console.print(Panel("[bold]/api/v1/diagnosis/report/{diagnosis_id}[/bold]", style="dim"))
    ok, report_or_msg = await fetch_report(base_url, diagnosis_id)
    if not ok:
        console.print(Text("FAIL ", style="bold red") + Text(str(report_or_msg), style="red"))
        return 1 if failed else 1
    report = report_or_msg if isinstance(report_or_msg, dict) else {}
    print_report(report)

    if adopt_solution_id:
        console.print()
        console.print(Panel(f"[bold]自动采纳方案 {adopt_solution_id}[/bold]", style="dim"))
        ok, msg_or_data = await adopt_solution(base_url, adopt_solution_id)
        if not ok:
            console.print(Text(f"采纳失败: {msg_or_data}", style="red"))
            failed += 1
        else:
            console.print(Text(f"采纳已提交: {msg_or_data}", style="green"))
            adopt_ok = await wait_adopt_done(base_url, adopt_solution_id, poll_interval, timeout_seconds)
            if not adopt_ok:
                failed += 1
    else:
        await post_actions(base_url, diagnosis_id, report, enterprise_id, poll_interval)

    return 1 if failed else 0


def main() -> int:
    p = argparse.ArgumentParser(description="兼容接口 CLI（诊断/报告/方案/钻取/采纳）")
    p.add_argument("--base-url", default=DEFAULT_BASE, help=f"服务 base URL（默认 {DEFAULT_BASE}）")
    p.add_argument("--enterprise-id", default="wlwq_local", help="企业ID（默认 wlwq_local）")
    p.add_argument("--adopt", metavar="SOLUTION_ID", help="诊断完成后自动采纳该 solution_id")
    p.add_argument("--diagnosis-id", metavar="ID", default=None, help="仅查看该诊断的兼容方案列表")
    p.add_argument("--view-solutions", action="store_true", help="进入仅看方案模式")
    p.add_argument("--poll-interval", type=float, default=2.0, help="状态轮询间隔秒（默认 2）")
    p.add_argument("--timeout", type=int, default=300, help="轮询超时秒（默认 300）")
    args = p.parse_args()

    if args.view_solutions or args.diagnosis_id:
        did = (args.diagnosis_id or "").strip()
        if not did:
            did = (input("请输入诊断ID: ") or "").strip()
        if not did:
            console.print(Text("未提供诊断ID。", style="red"))
            return 2
        return asyncio.run(run_solutions_by_diagnosis_id(args.base_url, did))

    return asyncio.run(
        run_diagnose(
            base_url=args.base_url,
            enterprise_id=args.enterprise_id,
            adopt_solution_id=args.adopt,
            poll_interval=max(0.5, args.poll_interval),
            timeout_seconds=max(10, args.timeout),
        )
    )


if __name__ == "__main__":
    sys.exit(main())
