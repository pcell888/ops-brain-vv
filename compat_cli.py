#!/usr/bin/env python3
"""兼容层 CLI：仅调用兼容接口，支持启动诊断、按 diagnosis_id 查进度、轮询状态、查看报告、方案采纳与钻取。"""

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
DEFAULT_BASE = "http://127.0.0.1:38000"
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


def _normalize_progress(raw: object) -> int | None:
    if raw is None:
        return None
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def _progress_signature(
    status: object,
    progress: object,
    message: object,
    timestamp: object | None = None,
) -> tuple[str, int | None, str, str | None]:
    normalized_timestamp = None
    if isinstance(timestamp, str):
        normalized_timestamp = timestamp.strip() or None
    elif timestamp is not None:
        normalized_timestamp = str(timestamp)
    return (
        str(status or "").strip(),
        _normalize_progress(progress),
        str(message or "").strip(),
        normalized_timestamp,
    )


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


async def start_diagnosis(base_url: str, enterprise_id: str, store_id: str = "") -> tuple[bool, str, dict | None]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/diagnosis/start"
    body = {
        "enterprise_id": enterprise_id,
        "store_id": (store_id or "").strip(),
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
    seen_history_signatures: set[tuple[str, int | None, str, str | None]] = set()
    last_current_signature: tuple[str, int | None, str, str | None] | None = None
    while True:
        ok, data_or_msg = await fetch_status(base_url, diagnosis_id)
        if not ok:
            console.print(Text(f"状态查询失败: {data_or_msg}", style="red"))
            return False, None
        assert isinstance(data_or_msg, dict)
        status = str(data_or_msg.get("status", ""))
        progress = _normalize_progress(data_or_msg.get("progress", 0)) or 0
        message = str(data_or_msg.get("message", ""))

        last_history_summary: tuple[str, int | None, str] | None = None
        for item in data_or_msg.get("recent_progress_messages") or []:
            if not isinstance(item, dict):
                continue
            history_sig = _progress_signature(
                item.get("status"),
                item.get("progress"),
                item.get("message"),
                item.get("timestamp"),
            )
            history_status, history_progress, history_message, _ = history_sig
            if not history_message:
                continue
            last_history_summary = (history_status, history_progress, history_message)
            if history_sig in seen_history_signatures:
                continue
            seen_history_signatures.add(history_sig)
            console.print(
                Text(
                    f"  [{history_status}] {0 if history_progress is None else history_progress}% {history_message}",
                    style="cyan",
                )
            )

        current_sig = _progress_signature(status, progress, message)
        current_summary = current_sig[:3]
        if current_summary != last_history_summary and current_sig != last_current_signature:
            console.print(Text(f"  [{status}] {progress}% {message}", style="cyan"))
            last_current_signature = current_sig

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


async def fetch_solution_detail(base_url: str, solution_id: str) -> tuple[bool, dict | str]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/solutions/detail/{solution_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            if r.status_code == 200:
                return True, r.json()
            return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)


async def fetch_execution_tasks(base_url: str, diagnosis_id: str, limit: int = 100) -> tuple[bool, dict | str]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/execution/tasks"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                url,
                params={"thread_id": diagnosis_id, "skip": 0, "limit": max(1, min(limit, 500))},
            )
            if r.status_code == 200:
                return True, r.json()
            return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)


async def fetch_tracking_list(
    base_url: str,
    diagnosis_id: str,
    limit: int = 20,
    enterprise_id: str | None = None,
) -> tuple[bool, dict | str]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/tracking/list"
    try:
        params: dict[str, str | int] = {"diagnosis_id": diagnosis_id, "skip": 0, "limit": max(1, min(limit, 100))}
        if enterprise_id:
            params["enterprise_id"] = enterprise_id.strip()
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, params=params)
            if r.status_code == 200:
                return True, r.json()
            return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)


async def fetch_tracking_summary(base_url: str, tracking_id: str) -> tuple[bool, dict | str]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/tracking/{tracking_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            if r.status_code == 200:
                return True, r.json()
            return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)


async def fetch_tracking_report(base_url: str, tracking_id: str) -> tuple[bool, dict | str]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/tracking/{tracking_id}/report"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.get(url)
            if r.status_code == 200:
                return True, r.json()
            return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)


async def post_tracking_snapshot(
    base_url: str,
    tracking_id: str,
    *,
    enterprise_id: str | None = None,
) -> tuple[bool, dict | str]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/tracking/{tracking_id}/snapshot"
    body: dict[str, str] = {}
    if enterprise_id:
        body["enterprise_id"] = enterprise_id.strip()
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(url, json=body or {})
            if r.status_code != 200:
                return False, f"HTTP {r.status_code}: {r.text[:200]}"
            return True, r.json()
    except Exception as e:
        return False, str(e)


async def post_tracking_complete(base_url: str, tracking_id: str) -> tuple[bool, dict | str]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/tracking/{tracking_id}/complete"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(url)
            if r.status_code != 200:
                return False, f"HTTP {r.status_code}: {r.text[:200]}"
            return True, r.json()
    except Exception as e:
        return False, str(e)


async def post_tracking_cancel(base_url: str, tracking_id: str) -> tuple[bool, dict | str]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/tracking/{tracking_id}/cancel"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url)
            if r.status_code != 200:
                return False, f"HTTP {r.status_code}: {r.text[:200]}"
            return True, r.json()
    except Exception as e:
        return False, str(e)


async def fetch_execution_task_detail(base_url: str, task_id: str) -> tuple[bool, dict | str]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/execution/tasks/{task_id}"
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


async def fetch_enterprises(base_url: str) -> tuple[bool, dict | str]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/enterprises"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return False, f"HTTP {r.status_code}: {r.text[:200]}"
            return True, r.json()
    except Exception as e:
        return False, str(e)


async def fetch_enterprise_detail(base_url: str, tenant_id: str) -> tuple[bool, dict | str]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/enterprises/{tenant_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return False, f"HTTP {r.status_code}: {r.text[:200]}"
            return True, r.json()
    except Exception as e:
        return False, str(e)


async def sync_enterprise_info(base_url: str, tenant_id: str) -> tuple[bool, dict | str]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/enterprises/{tenant_id}"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.put(url, json={})
            if r.status_code != 200:
                return False, f"HTTP {r.status_code}: {r.text[:200]}"
            return True, r.json()
    except Exception as e:
        return False, str(e)


async def fetch_diagnosis_history(base_url: str, tenant_id: str, limit: int = 20) -> tuple[bool, dict | str]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/diagnosis/list"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                url,
                params={"enterprise_id": tenant_id, "skip": 0, "limit": max(1, min(limit, 100))},
            )
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


def print_enterprise_list(data: dict) -> None:
    enterprises = data.get("enterprises") or []
    total = data.get("total", len(enterprises))
    if not enterprises:
        console.print(Text("企业列表为空。", style="yellow"))
        return
    t = Table(title=f"企业列表（total={total}）", show_header=True, header_style="bold")
    t.add_column("tenant_id", style="cyan")
    t.add_column("tenant_name", style="white")
    for e in enterprises:
        t.add_row(str(e.get("id", "")), str(e.get("name", "")))
    console.print(t)


def print_diagnosis_history_list(tenant_id: str, data: dict) -> None:
    items = data.get("items") or []
    total = data.get("total", len(items))
    if not items:
        console.print(Text(f"企业 {tenant_id} 无诊断历史。", style="yellow"))
        return
    t = Table(title=f"诊断历史（tenant_id={tenant_id}, total={total}）", show_header=True, header_style="bold")
    t.add_column("序号", style="magenta")
    t.add_column("diagnosis_id", style="cyan")
    t.add_column("status", style="magenta")
    t.add_column("progress", style="yellow")
    t.add_column("health_score", style="green")
    t.add_column("anomaly_count", style="white")
    t.add_column("created_at", style="white")
    for idx, item in enumerate(items, start=1):
        t.add_row(
            str(idx),
            str(item.get("diagnosis_id", "")),
            str(item.get("status", "")),
            f"{item.get('progress', '-')}%",
            str(item.get("health_score", "-")),
            str(item.get("anomaly_count", "-")),
            _fmt_time(item.get("created_at")),
        )
    console.print(t)


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
    t.add_column("序号", style="magenta")
    t.add_column("solution_id", style="cyan")
    t.add_column("方案名称", style="white")
    t.add_column("优先级", style="green")
    t.add_column("score", style="yellow")
    t.add_column("status", style="magenta")
    for idx, s in enumerate(solutions, start=1):
        t.add_row(
            str(idx),
            str(s.get("solution_id", "")),
            str(s.get("name", "")),
            str(s.get("priority_level", "")),
            str(s.get("score", "")),
            str(s.get("status", "")),
        )
    console.print(t)


def print_execution_task_list(diagnosis_id: str, data: dict) -> None:
    items = data.get("items") or []
    total = data.get("total", len(items))
    if not items:
        console.print(Text(f"诊断 {diagnosis_id} 无执行任务。", style="yellow"))
        return
    t = Table(
        title=f"执行任务列表（diagnosis_id={diagnosis_id}, total={total}）", show_header=True, header_style="bold"
    )
    t.add_column("序号", style="magenta")
    t.add_column("task_id", style="cyan")
    t.add_column("任务名", style="white")
    t.add_column("status", style="magenta")
    t.add_column("plan_id", style="green")
    t.add_column("owner", style="yellow")
    t.add_column("updated_at", style="white")
    for idx, item in enumerate(items, start=1):
        t.add_row(
            str(idx),
            str(item.get("task_id", "")),
            str(item.get("task_name") or item.get("name") or "-"),
            str(item.get("status", "")),
            str(item.get("plan_id", "")),
            str(item.get("owner") or item.get("assignee") or "-"),
            _fmt_time(item.get("updated_at")),
        )
    console.print(t)


def print_tracking_list(diagnosis_id: str, data: dict) -> None:
    items = data.get("items") or []
    total = data.get("total", len(items))
    if not items:
        console.print(Text(f"诊断 {diagnosis_id} 无效果追踪记录。", style="yellow"))
        return
    t = Table(
        title=f"效果追踪列表（diagnosis_id={diagnosis_id}, total={total}）", show_header=True, header_style="bold"
    )
    t.add_column("序号", style="magenta")
    t.add_column("tracking_id", style="cyan")
    t.add_column("方案", style="white")
    t.add_column("status", style="magenta")
    t.add_column("current_score", style="green")
    t.add_column("snapshots", style="yellow")
    t.add_column("started_at", style="white")
    for idx, item in enumerate(items, start=1):
        t.add_row(
            str(idx),
            str(item.get("tracking_id", "")),
            str(item.get("solution_name", "-")),
            str(item.get("status", "")),
            str(item.get("current_score", "-")),
            str(item.get("snapshot_count", "-")),
            _fmt_time(item.get("started_at")),
        )
    console.print(t)


def print_drill_down(data: dict) -> None:
    rows = data.get("data") or []
    labels = data.get("field_labels") or {}
    mn = str(data.get("metric_name") or "-")
    md = str(data.get("metric_display_name") or "").strip()
    label_line = f"指标: {md}（{mn}）" if md else f"指标: {mn}"
    console.print(
        Text(
            f"{label_line}  总数: {data.get('total', 0)}  分页: {data.get('page', 1)}",
            style="dim",
        )
    )
    if not rows:
        console.print(Text("无钻取数据。", style="yellow"))
        return
    keys = list(labels.keys()) if isinstance(labels, dict) and labels else list(rows[0].keys())
    tbl_title = "指标钻取结果(前10)"
    if md:
        tbl_title = f"{tbl_title} · {md}"
    t = Table(title=tbl_title, show_header=True, header_style="bold")
    for k in keys:
        t.add_column(str(labels.get(k, k)), style="white")
    for row in rows[:10]:
        t.add_row(*[str((row or {}).get(k, "")) for k in keys])
    console.print(t)


async def post_actions(
    base_url: str, diagnosis_id: str, report: dict, enterprise_id: str, poll_interval: float
) -> None:
    while True:
        console.print()
        console.print(
            Panel(
                "[bold]接下来可执行[/bold]\n1. 查看 优化方案列表\n2. 查看 钻取 某个 指标数据\n3. 查看 某个 异常指标详情\n4. 采纳某个方案并查看进度\n0. 结束",
                style="dim",
            )
        )
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
                console.print(
                    Panel(json.dumps(detail_or_msg, ensure_ascii=False, indent=2), title="异常指标详情", style="dim")
                )
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


def print_diagnosis_status(data: dict) -> None:
    """打印 GET /diagnosis/status/{id} 返回的核心字段。"""
    t = Table(show_header=False, box=None, pad_edge=False, title="诊断进度")
    t.add_column("k", style="cyan", no_wrap=True, width=18)
    t.add_column("v", style="white")
    rows = [
        ("diagnosis_id", str(data.get("diagnosis_id", "-"))),
        ("status", str(data.get("status", "-"))),
        ("phase", str(data.get("phase", "-"))),
        ("phase_name", str(data.get("phase_name", "-"))),
        ("progress", f"{data.get('progress', '-')}%"),
        ("overall_progress", f"{data.get('overall_progress', '-')}%"),
        ("next_phase", str(data.get("next_phase", "-"))),
        ("health_score", str(data.get("health_score", "-"))),
        ("message", str(data.get("message", "-"))),
    ]
    for k, v in rows:
        t.add_row(k, v)
    console.print(Panel(t, border_style="cyan"))


async def run_progress_by_diagnosis_id(
    base_url: str,
    diagnosis_id: str,
    poll_interval: float,
    timeout_seconds: int,
) -> int:
    did = diagnosis_id.strip()
    if not did:
        console.print(Text("诊断ID 不能为空。", style="red"))
        return 2
    console.print(Panel(f"[bold]按 diagnosis_id 查询进度（轮询至结束）[/bold]\n[dim]{did}[/dim]", style="dim"))
    console.print(Panel("[bold]/api/v1/diagnosis/status/{id}[/bold]", style="dim"))
    done_ok, last = await wait_status_done(base_url, did, poll_interval, timeout_seconds)
    if isinstance(last, dict) and last:
        console.print()
        print_diagnosis_status(last)
    return 0 if done_ok else 1


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


async def post_history_actions(base_url: str, history_items: list[dict]) -> None:
    while True:
        console.print()
        console.print(
            Panel(
                "[bold]历史列表子命令[/bold]\n1. 查看报告（需 diagnosis_id 或序号）\n2. 查看方案列表（需 diagnosis_id 或序号）\n3. 查看执行任务列表（需 diagnosis_id 或序号）\n4. 查看效果追踪（需 diagnosis_id 或序号）\n0. 返回",
                style="dim",
            )
        )
        choice = (input("请输入选项编号: ") or "").strip()
        if choice == "0":
            return
        if choice not in {"1", "2", "3", "4"}:
            console.print(Text("无效选项，请输入 0/1/2/3/4。", style="yellow"))
            continue
        raw = (input("请输入 diagnosis_id 或序号: ") or "").strip()
        if not raw:
            console.print(Text("diagnosis_id 不能为空。", style="yellow"))
            continue
        diagnosis_id = raw
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(history_items):
                diagnosis_id = str((history_items[idx] or {}).get("diagnosis_id", "")).strip()
        if not diagnosis_id:
            console.print(Text("未找到有效 diagnosis_id。", style="yellow"))
            continue
        if choice == "1":
            ok, report_or_msg = await fetch_report(base_url, diagnosis_id)
            if not ok:
                console.print(Text(f"查询报告失败: {report_or_msg}", style="red"))
                continue
            report = report_or_msg if isinstance(report_or_msg, dict) else {}
            print_report(report)
            continue
        if choice == "3":
            ok, tasks_or_msg = await fetch_execution_tasks(base_url, diagnosis_id)
            if not ok:
                console.print(Text(f"查询执行任务列表失败: {tasks_or_msg}", style="red"))
                continue
            if isinstance(tasks_or_msg, dict):
                print_execution_task_list(diagnosis_id, tasks_or_msg)
                tasks = tasks_or_msg.get("items") or []
                if tasks:
                    while True:
                        console.print()
                        console.print(
                            Panel(
                                "[bold]执行任务列表子命令[/bold]\n1. 查看详情（需 task_id 或序号）\n0. 返回",
                                style="dim",
                            )
                        )
                        task_action = (input("请输入选项编号: ") or "").strip()
                        if task_action == "0":
                            break
                        if task_action != "1":
                            console.print(Text("无效选项，请输入 0/1。", style="yellow"))
                            continue
                        raw_task = (input("请输入 task_id 或序号: ") or "").strip()
                        if not raw_task:
                            console.print(Text("task_id 不能为空。", style="yellow"))
                            continue
                        task_id = raw_task
                        if raw_task.isdigit():
                            tidx = int(raw_task) - 1
                            if 0 <= tidx < len(tasks):
                                task_id = str((tasks[tidx] or {}).get("task_id", "")).strip()
                        if not task_id:
                            console.print(Text("未找到有效 task_id。", style="yellow"))
                            continue
                        ok_task, task_detail_or_msg = await fetch_execution_task_detail(base_url, task_id)
                        if not ok_task:
                            console.print(Text(f"查询任务详情失败: {task_detail_or_msg}", style="red"))
                            continue
                        console.print(
                            Panel(
                                json.dumps(task_detail_or_msg, ensure_ascii=False, indent=2),
                                title=f"任务详情 task_id={task_id}",
                                style="dim",
                            )
                        )
            else:
                console.print(Text("执行任务列表响应格式异常。", style="red"))
            continue
        if choice == "4":
            ok, track_or_msg = await fetch_tracking_list(base_url, diagnosis_id)
            if not ok:
                console.print(Text(f"查询效果追踪列表失败: {track_or_msg}", style="red"))
                continue
            if isinstance(track_or_msg, dict):
                print_tracking_list(diagnosis_id, track_or_msg)
                track_items = track_or_msg.get("items") or []
                if track_items:
                    while True:
                        console.print()
                        console.print(
                            Panel(
                                "[bold]效果追踪列表子命令[/bold]\n"
                                "1. 查看摘要（需 tracking_id 或序号）\n"
                                "2. 采集快照（需 tracking_id 或序号）\n"
                                "3. 完成最终（需 tracking_id 或序号）\n"
                                "4. 停止（需 tracking_id 或序号）\n"
                                "5. 查看复盘报告（需 tracking_id 或序号）\n"
                                "0. 返回",
                                style="dim",
                            )
                        )
                        track_action = (input("请输入选项编号: ") or "").strip()
                        if track_action == "0":
                            break
                        if track_action not in {"1", "2", "3", "4", "5"}:
                            console.print(Text("无效选项，请输入 0/1/2/3/4/5。", style="yellow"))
                            continue
                        raw_tid = (input("请输入 tracking_id 或序号: ") or "").strip()
                        if not raw_tid:
                            console.print(Text("tracking_id 不能为空。", style="yellow"))
                            continue
                        tracking_id = raw_tid
                        if raw_tid.isdigit():
                            tr_idx = int(raw_tid) - 1
                            if 0 <= tr_idx < len(track_items):
                                tracking_id = str((track_items[tr_idx] or {}).get("tracking_id", "")).strip()
                        if not tracking_id:
                            console.print(Text("未找到有效 tracking_id。", style="yellow"))
                            continue
                        if track_action == "1":
                            ok_sum, sum_or_msg = await fetch_tracking_summary(base_url, tracking_id)
                            if not ok_sum:
                                console.print(Text(f"查询追踪摘要失败: {sum_or_msg}", style="red"))
                                continue
                            console.print(
                                Panel(
                                    json.dumps(sum_or_msg, ensure_ascii=False, indent=2),
                                    title=f"效果追踪摘要 tracking_id={tracking_id}",
                                    style="dim",
                                )
                            )
                        elif track_action == "2":
                            ok_snap, snap_or_msg = await post_tracking_snapshot(base_url, tracking_id)
                            if not ok_snap:
                                console.print(Text(f"采集快照失败: {snap_or_msg}", style="red"))
                                continue
                            payload = snap_or_msg if isinstance(snap_or_msg, dict) else {"detail": snap_or_msg}
                            console.print(
                                Panel(
                                    json.dumps(payload, ensure_ascii=False, indent=2),
                                    title=f"采集快照结果 tracking_id={tracking_id}",
                                    style="dim",
                                )
                            )
                        elif track_action == "3":
                            ok_cmp, cmp_or_msg = await post_tracking_complete(base_url, tracking_id)
                            if not ok_cmp:
                                console.print(Text(f"完成追踪失败: {cmp_or_msg}", style="red"))
                                continue
                            payload = cmp_or_msg if isinstance(cmp_or_msg, dict) else {"detail": cmp_or_msg}
                            console.print(
                                Panel(
                                    json.dumps(payload, ensure_ascii=False, indent=2),
                                    title=f"完成追踪结果 tracking_id={tracking_id}",
                                    style="dim",
                                )
                            )
                        elif track_action == "4":
                            ok_can, can_or_msg = await post_tracking_cancel(base_url, tracking_id)
                            if not ok_can:
                                console.print(Text(f"停止追踪失败: {can_or_msg}", style="red"))
                                continue
                            payload = can_or_msg if isinstance(can_or_msg, dict) else {"detail": can_or_msg}
                            console.print(
                                Panel(
                                    json.dumps(payload, ensure_ascii=False, indent=2),
                                    title=f"停止追踪结果 tracking_id={tracking_id}",
                                    style="dim",
                                )
                            )
                        else:
                            ok_rep, rep_or_msg = await fetch_tracking_report(base_url, tracking_id)
                            if not ok_rep:
                                console.print(Text(f"查询复盘报告失败: {rep_or_msg}", style="red"))
                                continue
                            console.print(
                                Panel(
                                    json.dumps(rep_or_msg, ensure_ascii=False, indent=2),
                                    title=f"复盘报告 tracking_id={tracking_id}",
                                    style="dim",
                                )
                            )
            else:
                console.print(Text("效果追踪列表响应格式异常。", style="red"))
            continue
        ok, solutions_or_msg = await fetch_solutions(base_url, diagnosis_id)
        if not ok:
            console.print(Text(f"查询方案列表失败: {solutions_or_msg}", style="red"))
            continue
        if isinstance(solutions_or_msg, dict):
            print_solution_list(solutions_or_msg)
            solutions = solutions_or_msg.get("solutions") or []
            if solutions:
                while True:
                    console.print()
                    console.print(
                        Panel(
                            "[bold]方案列表子命令[/bold]\n1. 采纳（需 solution_id 或序号）\n2. 查看详情（需 solution_id 或序号）\n0. 返回",
                            style="dim",
                        )
                    )
                    action = (input("请输入选项编号: ") or "").strip()
                    if action == "0":
                        break
                    if action not in {"1", "2"}:
                        console.print(Text("无效选项，请输入 0/1/2。", style="yellow"))
                        continue
                    raw_solution = (input("请输入 solution_id 或序号: ") or "").strip()
                    if not raw_solution:
                        console.print(Text("solution_id 不能为空。", style="yellow"))
                        continue
                    solution_id = raw_solution
                    if raw_solution.isdigit():
                        sidx = int(raw_solution) - 1
                        if 0 <= sidx < len(solutions):
                            solution_id = str((solutions[sidx] or {}).get("solution_id", "")).strip()
                    if not solution_id:
                        console.print(Text("未找到有效 solution_id。", style="yellow"))
                        continue
                    if action == "1":
                        ok_adopt, adopt_msg_or_data = await adopt_solution(base_url, solution_id)
                        if not ok_adopt:
                            console.print(Text(f"采纳失败: {adopt_msg_or_data}", style="red"))
                            continue
                        console.print(Text(f"采纳已提交: {adopt_msg_or_data}", style="green"))
                        await wait_adopt_done(base_url, solution_id, 2.0, 300)
                        continue
                    ok_detail, detail_or_msg = await fetch_solution_detail(base_url, solution_id)
                    if not ok_detail:
                        console.print(Text(f"查询方案详情失败: {detail_or_msg}", style="red"))
                        continue
                    console.print(
                        Panel(
                            json.dumps(detail_or_msg, ensure_ascii=False, indent=2),
                            title=f"方案详情 solution_id={solution_id}",
                            style="dim",
                        )
                    )
        else:
            console.print(Text("方案列表响应格式异常。", style="red"))


async def run_enterprises(base_url: str, detail_tenant_id: str | None, sync_tenant_id: str | None) -> int:
    if detail_tenant_id:
        tenant_id = detail_tenant_id.strip()
        if not tenant_id:
            console.print(Text("tenant_id 不能为空。", style="red"))
            return 2
        ok, data_or_msg = await fetch_enterprise_detail(base_url, tenant_id)
        if not ok:
            console.print(Text(f"查询详情失败: {data_or_msg}", style="red"))
            return 1
        console.print(
            Panel(
                json.dumps(data_or_msg, ensure_ascii=False, indent=2),
                title=f"企业详情 tenant_id={tenant_id}",
                style="dim",
            )
        )
        return 0

    if sync_tenant_id:
        tenant_id = sync_tenant_id.strip()
        if not tenant_id:
            console.print(Text("tenant_id 不能为空。", style="red"))
            return 2
        ok, data_or_msg = await sync_enterprise_info(base_url, tenant_id)
        if not ok:
            console.print(Text(f"同步企业失败: {data_or_msg}", style="red"))
            return 1
        console.print(Text(f"同步企业成功 tenant_id={tenant_id}", style="green"))
        console.print(Panel(json.dumps(data_or_msg, ensure_ascii=False, indent=2), title="同步结果", style="dim"))
        return 0

    console.print(Panel("[bold]查看企业列表[/bold]\n[dim]/api/v1/enterprises[/dim]", style="dim"))
    ok, data_or_msg = await fetch_enterprises(base_url)
    if not ok:
        console.print(Text(f"查询企业列表失败: {data_or_msg}", style="red"))
        return 1
    assert isinstance(data_or_msg, dict)
    print_enterprise_list(data_or_msg)

    while True:
        console.print()
        console.print(
            Panel(
                "[bold]企业子命令[/bold]\n1. 查看详情（需 tenant_id）\n2. 同步企业信息（需 tenant_id）\n3. 查看诊断历史列表（需 tenant_id）\n0. 结束",
                style="dim",
            )
        )
        choice = (input("请输入选项编号: ") or "").strip()
        if choice == "0":
            return 0
        if choice not in {"1", "2", "3"}:
            console.print(Text("无效选项，请输入 0/1/2/3。", style="yellow"))
            continue
        tenant_id = (input("请输入 tenant_id: ") or "").strip()
        if not tenant_id:
            console.print(Text("tenant_id 不能为空。", style="yellow"))
            continue
        if choice == "1":
            ok, detail_or_msg = await fetch_enterprise_detail(base_url, tenant_id)
            if ok:
                console.print(
                    Panel(
                        json.dumps(detail_or_msg, ensure_ascii=False, indent=2),
                        title=f"企业详情 tenant_id={tenant_id}",
                        style="dim",
                    )
                )
            else:
                console.print(Text(f"查询详情失败: {detail_or_msg}", style="red"))
            continue
        if choice == "2":
            ok, sync_or_msg = await sync_enterprise_info(base_url, tenant_id)
            if ok:
                console.print(Text(f"同步企业成功 tenant_id={tenant_id}", style="green"))
                console.print(
                    Panel(json.dumps(sync_or_msg, ensure_ascii=False, indent=2), title="同步结果", style="dim")
                )
            else:
                console.print(Text(f"同步企业失败: {sync_or_msg}", style="red"))
            continue
        ok, history_or_msg = await fetch_diagnosis_history(base_url, tenant_id)
        if ok and isinstance(history_or_msg, dict):
            print_diagnosis_history_list(tenant_id, history_or_msg)
            history_items = history_or_msg.get("items") or []
            if history_items:
                await post_history_actions(base_url, history_items)
        else:
            console.print(Text(f"查询诊断历史失败: {history_or_msg}", style="red"))


async def run_diagnose(
    base_url: str,
    enterprise_id: str,
    store_id: str,
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
    console.print(
        Panel(
            f"[bold]/api/v1/diagnosis/start[/bold] (enterprise_id={enterprise_id!r}, store_id={(store_id or '').strip()!r})",
            style="dim",
        )
    )
    ok, msg, start_data = await start_diagnosis(base_url, enterprise_id, store_id)
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
    p.add_argument(
        "--store-id",
        default="",
        help="门店ID；空则全企业诊断（兼容层 /diagnosis/start 的 store_id）",
    )
    p.add_argument("--adopt", metavar="SOLUTION_ID", help="诊断完成后自动采纳该 solution_id")
    p.add_argument("--diagnosis-id", metavar="ID", default=None, help="配合 --view-solutions / --progress 指定诊断 ID")
    p.add_argument("--view-solutions", action="store_true", help="进入仅看方案模式")
    p.add_argument("--view-enterprises", action="store_true", help="查看企业列表，并支持详情/同步子命令")
    p.add_argument("--enterprise-detail", metavar="TENANT_ID", help="直接查看企业详情（tenant_id）")
    p.add_argument("--sync-enterprise", metavar="TENANT_ID", help="直接同步企业信息（tenant_id）")
    p.add_argument(
        "--progress",
        action="store_true",
        help="按 diagnosis_id 轮询诊断进度直至完成/失败/超时（需 --diagnosis-id 或交互输入）",
    )
    p.add_argument("--poll-interval", type=float, default=2.0, help="状态轮询间隔秒（默认 2）")
    p.add_argument("--timeout", type=int, default=300, help="轮询超时秒（默认 300）")
    args = p.parse_args()

    if args.view_enterprises or args.enterprise_detail or args.sync_enterprise:
        return asyncio.run(
            run_enterprises(
                args.base_url,
                args.enterprise_detail,
                args.sync_enterprise,
            )
        )

    if args.progress:
        did = (args.diagnosis_id or "").strip()
        if not did:
            did = (input("请输入诊断ID: ") or "").strip()
        if not did:
            console.print(Text("未提供诊断ID。", style="red"))
            return 2
        return asyncio.run(
            run_progress_by_diagnosis_id(
                args.base_url,
                did,
                poll_interval=max(0.5, args.poll_interval),
                timeout_seconds=max(10, args.timeout),
            )
        )

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
            store_id=(args.store_id or "").strip(),
            adopt_solution_id=args.adopt,
            poll_interval=max(0.5, args.poll_interval),
            timeout_seconds=max(10, args.timeout),
        )
    )


if __name__ == "__main__":
    sys.exit(main())
