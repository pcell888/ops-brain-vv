#!/usr/bin/env python3
"""8000 诊断服务测试 CLI — 检查 /health、/api/v1/diagnosis 等，支持完整诊断流程与进度推送。"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
from datetime import datetime
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

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


def _draw_line(grid: list[list[str]], x0: int, y0: int, x1: int, y1: int, ch: str) -> None:
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        if 0 <= y0 < len(grid) and 0 <= x0 < len(grid[0]) and grid[y0][x0] == " ":
            grid[y0][x0] = ch
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def _print_dimension_radar(dim_scores: dict, dim_benchmark_scores: dict) -> None:
    if not isinstance(dim_scores, dict) or not dim_scores:
        return
    if not isinstance(dim_benchmark_scores, dict) or not dim_benchmark_scores:
        return

    dims = [d for d in dim_scores.keys() if d in dim_benchmark_scores]
    if len(dims) < 3:
        return
    dims = dims[:8]

    size = 25
    center = size // 2
    radius = center - 3
    grid = [[" " for _ in range(size)] for _ in range(size)]

    def _score_value(v: object) -> float:
        try:
            return max(0.0, min(100.0, float(v)))
        except (TypeError, ValueError):
            return 0.0

    score_points: list[tuple[int, int]] = []
    bench_points: list[tuple[int, int]] = []
    axis_ends: list[tuple[int, int]] = []
    dim_labels: list[tuple[int, int, str]] = []

    for i, dim in enumerate(dims):
        angle = -math.pi / 2 + (2 * math.pi * i / len(dims))
        ex = int(round(center + radius * math.cos(angle)))
        ey = int(round(center + radius * math.sin(angle)))
        axis_ends.append((ex, ey))
        _draw_line(grid, center, center, ex, ey, ".")

        label_x = int(round(center + (radius + 2) * math.cos(angle)))
        label_y = int(round(center + (radius + 2) * math.sin(angle)))
        dim_labels.append((label_x, label_y, str(dim)))

        s = _score_value((dim_scores.get(dim) or {}).get("score") if isinstance(dim_scores.get(dim), dict) else dim_scores.get(dim))
        b = _score_value(dim_benchmark_scores.get(dim))
        sx = int(round(center + radius * (s / 100.0) * math.cos(angle)))
        sy = int(round(center + radius * (s / 100.0) * math.sin(angle)))
        bx = int(round(center + radius * (b / 100.0) * math.cos(angle)))
        by = int(round(center + radius * (b / 100.0) * math.sin(angle)))
        score_points.append((sx, sy))
        bench_points.append((bx, by))

    for i in range(len(score_points)):
        x0, y0 = score_points[i]
        x1, y1 = score_points[(i + 1) % len(score_points)]
        _draw_line(grid, x0, y0, x1, y1, "#")
    for i in range(len(bench_points)):
        x0, y0 = bench_points[i]
        x1, y1 = bench_points[(i + 1) % len(bench_points)]
        _draw_line(grid, x0, y0, x1, y1, "+")

    for x, y in score_points:
        if 0 <= y < size and 0 <= x < size:
            grid[y][x] = "●"
    for x, y in bench_points:
        if 0 <= y < size and 0 <= x < size:
            grid[y][x] = "○"
    if 0 <= center < size:
        grid[center][center] = "┼"

    lines = ["".join(row).rstrip() for row in grid]
    chart = "\n".join(lines).rstrip()

    label_lines = []
    for _, _, dim in dim_labels:
        cur = (dim_scores.get(dim) or {}).get("score") if isinstance(dim_scores.get(dim), dict) else dim_scores.get(dim)
        base = dim_benchmark_scores.get(dim)
        label_lines.append(f"{dim}: 当前={cur} 基准={base}")
    legend = "图例: ● 当前维度得分  ○ 行业基准得分"
    console.print(Panel(f"{chart}\n\n{legend}\n" + "\n".join(label_lines), title="维度得分 vs 行业基准（雷达图）", border_style="bright_blue"))


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


async def _fetch_drill_down(
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


async def _fetch_anomaly_detail(base_url: str, thread_id: str, indicator_code: str) -> tuple[bool, dict | str]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/diagnosis/{thread_id}/anomalies/{indicator_code}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return False, f"HTTP {r.status_code}: {r.text[:200]}"
            return True, r.json()
    except Exception as e:
        return False, str(e)


def _print_solution_list(plans: list[dict]) -> None:
    if not plans:
        console.print(Text("无优化方案。", style="yellow"))
        return
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


def _print_drill_down(data: dict) -> None:
    rows = data.get("data") or []
    labels = data.get("field_labels") or {}
    console.print(
        Text(
            f"指标: {data.get('metric_code', data.get('metric_name', '-'))}  "
            f"总数: {data.get('total', 0)}  "
            f"分页: {data.get('page', 1)}/{max(1, (int(data.get('total', 0)) + int(data.get('page_size', 10)) - 1) // int(data.get('page_size', 10)))}",
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


async def _post_diagnosis_actions(base_url: str, thread_id: str, report: dict, tenant_id: str) -> None:
    while True:
        console.print()
        console.print(Panel("[bold]接下来可执行[/bold]\n1. 查看 优化方案列表\n2. 查看 钻取 某个 指标数据\n3. 查看 某个 异常指标详情\n0. 结束", style="dim"))
        choice = (input("请输入选项编号: ") or "").strip()
        if choice == "0":
            break
        if choice == "1":
            plans = await _fetch_solutions(base_url, thread_id)
            _print_solution_list(plans)
            continue
        if choice == "2":
            metric_name = (input("请输入 metric_name（指标 code 或 name）: ") or "").strip()
            if not metric_name:
                console.print(Text("metric_name 不能为空。", style="yellow"))
                continue
            ok, data_or_msg = await _fetch_drill_down(base_url, metric_name, tenant_id)
            if ok and isinstance(data_or_msg, dict):
                _print_drill_down(data_or_msg)
            else:
                console.print(Text(f"查询失败: {data_or_msg}", style="red"))
            continue
        if choice == "3":
            raw_input = (input("请输入异常指标 ID 或序号: ") or "").strip()
            anomalies = report.get("anomalies") or []
            indicator_code = raw_input
            if raw_input.isdigit():
                idx = int(raw_input) - 1
                if 0 <= idx < len(anomalies):
                    indicator_code = str((anomalies[idx] or {}).get("indicator_code", "")).strip()
            if not indicator_code:
                if anomalies:
                    console.print(Text("可选异常指标（序号 -> ID）:", style="dim"))
                    for i, a in enumerate(anomalies, start=1):
                        console.print(Text(f"  {i}. {a.get('indicator_code', '')}", style="dim"))
                console.print(Text("异常指标 ID 不能为空。", style="yellow"))
                continue
            ok, detail_or_msg = await _fetch_anomaly_detail(base_url, thread_id, indicator_code)
            if ok and isinstance(detail_or_msg, dict):
                console.print(Panel(json.dumps(detail_or_msg, ensure_ascii=False, indent=2), title="异常指标详情", style="dim"))
            else:
                console.print(Text(f"查询失败: {detail_or_msg}", style="red"))
            continue
        console.print(Text("无效选项，请输入 0/1/2/3。", style="yellow"))


async def fetch_report(base_url: str, thread_id: str) -> tuple[bool, dict | str]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/diagnosis/{thread_id}/report"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return False, f"HTTP {r.status_code}: {r.text[:200]}"
            data = r.json()
            if isinstance(data, dict):
                return True, data
            return False, "报告格式异常"
    except Exception as e:
        return False, str(e)


def _format_generated_at_display(raw: object) -> str:
    """展示报告时间：新数据已为中国时区；旧 UTC 存证仍换算为东八区显示。"""
    if raw is None:
        return "[dim]-[/dim]"
    if not isinstance(raw, str):
        return str(raw)
    s = raw.strip()
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            return f"{raw} [dim](无时区)[/dim]"
        return dt.astimezone(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OSError):
        return str(raw)


def print_report(report: dict) -> None:
    health = report.get("health_score")
    anomalies = report.get("anomalies") or []
    root_causes = report.get("root_causes") or []
    health_value = float(health) if health is not None else None
    if health_value is None:
        level_text = "[dim]-[/dim]"
    elif health_value >= 80:
        level_text = "[bold green]优秀[/bold green]"
    elif health_value >= 60:
        level_text = "[bold yellow]一般[/bold yellow]"
    else:
        level_text = "[bold red]预警[/bold red]"

    console.print(
        Panel(
            f"[bold cyan]诊断报告[/bold cyan]\n"
            f"[dim]本次诊断核心结果如下[/dim]",
            border_style="cyan",
        )
    )
    overview = Table(show_header=False, box=None, pad_edge=False)
    overview.add_column("k", style="cyan", no_wrap=True, width=12)
    overview.add_column("v", style="white")
    overview.add_row("诊断时间", _format_generated_at_display(report.get("generated_at")))
    overview.add_row("健康分", f"[bold]{round(health_value, 2) if health_value is not None else '-'}[/bold]")
    overview.add_row("健康等级", level_text)
    overview.add_row("异常指标数", str(len(anomalies)))
    overview.add_row("根因条目数", str(len(root_causes)))
    console.print(Panel(overview, title="总览", border_style="blue"))

    dim_scores = report.get("dimension_scores") or {}
    dim_indicator_scores = report.get("dimension_indicator_scores") or {}
    dim_benchmarks = report.get("dimension_benchmarks") or {}
    dim_benchmarks_scores = report.get("dimension_benchmarks_scores") or {}
    if isinstance(dim_scores, dict) and dim_scores:
        t = Table(title="维度得分", show_header=True, header_style="bold magenta")
        t.add_column("维度", style="cyan")
        t.add_column("分数", style="green")
        t.add_column("权重", style="white")
        for dim, item in dim_scores.items():
            if isinstance(item, dict):
                score = item.get("score", "-")
                weight = item.get("weight", "-")
            else:
                score = item
                weight = "-"
            t.add_row(str(dim), str(score), str(weight))
        console.print(t)
        _print_dimension_radar(dim_scores, dim_benchmarks_scores)

    if isinstance(dim_benchmarks, dict) and dim_benchmarks:
        t = Table(title="维度指标与行业基准（前12）", show_header=True, header_style="bold blue")
        t.add_column("维度", style="cyan")
        t.add_column("指标", style="cyan")
        t.add_column("得分", style="green")
        t.add_column("当前值", style="white")
        t.add_column("偏差%", style="yellow")
        t.add_column("均值", style="green")
        t.add_column("中位值", style="white")
        t.add_column("优秀值", style="yellow")
        t.add_column("单位", style="white")

        def _fmt(v: object) -> str:
            if v is None:
                return "-"
            return str(v)

        score_index: dict[tuple[str, str], dict] = {}
        if isinstance(dim_indicator_scores, dict):
            for dim, items in dim_indicator_scores.items():
                if not isinstance(items, list):
                    continue
                for row in items:
                    if not isinstance(row, dict):
                        continue
                    code = str(row.get("indicator_code") or "")
                    name = str(row.get("indicator_name") or "")
                    if code:
                        score_index[(str(dim), code)] = row
                    if name:
                        score_index[(str(dim), name)] = row

        shown = 0
        for dim, items in dim_benchmarks.items():
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                indicator_code = str(item.get("indicator_code") or "")
                indicator_name = str(item.get("indicator_name") or indicator_code or "-")
                score_item = score_index.get((str(dim), indicator_code)) or score_index.get((str(dim), indicator_name)) or {}
                t.add_row(
                    str(dim),
                    indicator_name,
                    _fmt(score_item.get("score")),
                    _fmt(score_item.get("current_value")),
                    _fmt(score_item.get("deviation_pct")),
                    _fmt(item.get("avg_value")),
                    _fmt(item.get("median_value")),
                    _fmt(item.get("excellent_value")),
                    _fmt(item.get("unit")),
                )
                shown += 1
                if shown >= 12:
                    break
            if shown >= 12:
                break
        if shown > 0:
            console.print(t)

    if anomalies:
        t = Table(title="异常指标（全部）", show_header=True, header_style="bold red")
        t.add_column("序号", style="magenta")
        t.add_column("ID", style="cyan")
        t.add_column("指标", style="cyan")
        t.add_column("说明", style="white")
        t.add_column("偏差", style="yellow")
        for i, a in enumerate(anomalies, start=1):
            indicator_code = str(a.get("indicator_code", ""))
            indicator_name = str(a.get("indicator_name", indicator_code))
            t.add_row(
                str(i),
                indicator_code,
                indicator_name,
                str(a.get("description", "")),
                str(a.get("deviation", "-")),
            )
        console.print(t)

    if root_causes:
        t = Table(title="根因分析（前5）", show_header=True, header_style="bold yellow")
        t.add_column("关联指标", style="cyan")
        t.add_column("根因说明", style="white")
        t.add_column("置信度", style="green")
        for rc in root_causes[:5]:
            if isinstance(rc, dict):
                related_codes: list[str] = []
                for key in ("indicator_code", "anomaly_indicator", "metric_code"):
                    val = rc.get(key)
                    if isinstance(val, str) and val.strip():
                        related_codes.append(val.strip())
                for key in ("related_indicators", "target_indicators", "indicator_codes"):
                    val = rc.get(key)
                    if isinstance(val, list):
                        related_codes.extend([str(x).strip() for x in val if str(x).strip()])
                indicator_text = "、".join(dict.fromkeys(related_codes)) if related_codes else "-"
                t.add_row(
                    indicator_text,
                    str(rc.get("cause", rc.get("description", "-"))),
                    str(rc.get("confidence", "-")),
                )
            else:
                t.add_row("-", str(rc), "-")
        console.print(t)


def _interactive_adopt(plans: list[dict]) -> list[str]:
    """展示方案列表并提示用户输入要采纳的 plan_id（至多一个），返回 [plan_id] 或 []。"""
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
    prompt = "输入要采纳的一个方案 ID，留空则不采纳: "
    selected = (input(prompt) or "").strip()
    if not selected:
        return []
    # 仅采纳第一个有效 id（互斥）
    for part in [x.strip() for x in selected.split(",") if x.strip()]:
        if any(p.get("plan_id") == part for p in plans):
            return [part]
    return []


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
                line = json.dumps(msg, ensure_ascii=False)
                console.print(Text("  ", style="dim") + Text(line, style="cyan"))
                if t == "waiting_adoption":
                    if adopt_plan_ids is not None:
                        payload = {"action": "adopt_plans", "plan_ids": adopt_plan_ids[:1]}
                        await ws.send(json.dumps(payload))
                    else:
                        # 交互模式下不在 WS 阶段采纳，直接退出进度流，后续由菜单驱动。
                        done = True
                        success = True
                        break
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
            console.print(Panel("[bold]/api/v1/diagnosis/{thread_id}/report[/bold]", style="dim"))
            ok, report_or_msg = await fetch_report(base_url, thread_id)
            if ok:
                report = report_or_msg if isinstance(report_or_msg, dict) else {}
                print_report(report)
                await _post_diagnosis_actions(base_url, thread_id, report, tenant_id)
            else:
                console.print(Text("FAIL ", style="bold red") + Text(str(report_or_msg), style="red"))
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
    p.add_argument("--adopt", metavar="PLAN_ID", help="收到方案后采纳的唯一 plan_id（互斥）；不指定则仅跑到 waiting_adoption")
    args = p.parse_args()
    adopt_ids = [args.adopt] if args.adopt else None
    return asyncio.run(run_diagnose(args.base_url, args.tenant_id, args.store_id, adopt_ids))


if __name__ == "__main__":
    sys.exit(main())
