#!/usr/bin/env python3
"""诊断全流程自动化测试 CLI：按流程图顺序调用兼容层 API；ENTER 处暂停等待人工回车。"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

import compat_cli as cc

console = Console()
API_PREFIX = cc.API_PREFIX
FINAL_TYPES = ("completed", "failed", "error")


def wait_enter(label: str) -> None:
    console.print(Panel(f"[bold]{label}[/bold]\n[dim]按 Enter 继续[/dim]", border_style="dim"))
    input()


async def fetch_review_progress(base_url: str, tracking_id: str) -> tuple[bool, dict | str]:
    url = base_url.rstrip("/") + f"{API_PREFIX}/tracking/{tracking_id}/review/progress"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return False, f"HTTP {r.status_code}: {r.text[:200]}"
            data = r.json()
            return True, data if isinstance(data, dict) else {}
    except Exception as e:
        return False, str(e)


async def wait_review_progress_done(
    base_url: str,
    tracking_id: str,
    poll_interval: float,
    timeout_seconds: int,
) -> tuple[bool, dict | None]:
    started = asyncio.get_running_loop().time()
    while True:
        ok, data_or_msg = await fetch_review_progress(base_url, tracking_id)
        if not ok:
            console.print(Text(f"复盘进度查询失败: {data_or_msg}", style="red"))
            return False, None
        assert isinstance(data_or_msg, dict)
        status = str(data_or_msg.get("status", ""))
        pct = data_or_msg.get("overall_progress", data_or_msg.get("progress", data_or_msg.get("percent", "")))
        msg = str(data_or_msg.get("message", ""))
        console.print(Text(f"  [review:{status}] {pct}% {msg}", style="cyan"))
        if status in FINAL_TYPES:
            return status == "completed", data_or_msg
        if asyncio.get_running_loop().time() - started >= timeout_seconds:
            console.print(Text(f"复盘轮询超时（>{timeout_seconds}s）", style="yellow"))
            return False, data_or_msg
        await asyncio.sleep(poll_interval)


async def fetch_tracking_get(
    base_url: str, path_after_prefix: str
) -> tuple[bool, object]:
    url = base_url.rstrip("/") + f"{API_PREFIX}{path_after_prefix}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return False, f"HTTP {r.status_code}: {r.text[:200]}"
            try:
                return True, r.json() if r.content else {}
            except Exception:
                return True, {"raw": r.text[:500]}
    except Exception as e:
        return False, str(e)


async def dump_tracking_detail_views(
    base_url: str,
    tracking_id: str,
    banner: str,
) -> int:
    """追踪摘要 + analyze / trends / snapshots（与⑪ 中详情块一致）。"""
    failed_local = 0
    console.print(Panel(banner, style="dim"))
    ok_sum, summary = await cc.fetch_tracking_summary(base_url, tracking_id)
    if ok_sum and isinstance(summary, dict):
        console.print(
            Panel(
                json.dumps(summary, ensure_ascii=False, indent=2),
                title=f"追踪摘要 GET /tracking/{tracking_id}",
                style="dim",
            )
        )
    else:
        console.print(Text(f"追踪摘要失败: {summary}", style="red"))
        failed_local += 1

    for sub, title in (
        (f"/tracking/{tracking_id}/analyze", "效果分析 GET …/analyze"),
        (f"/tracking/{tracking_id}/trends", "指标趋势 GET …/trends"),
        (f"/tracking/{tracking_id}/snapshots", "快照列表 GET …/snapshots"),
    ):
        ok_sc, payload = await fetch_tracking_get(base_url, sub)
        if ok_sc and isinstance(payload, (dict, list)):
            preview = json.dumps(payload, ensure_ascii=False, indent=2)
            console.print(Panel(preview[:3500], title=title, style="dim"))
        else:
            console.print(Text(f"{title} 失败: {payload}", style="yellow"))

    return failed_local


def pick_recommended_solution_id(solutions: list) -> str | None:
    if not solutions:
        return None
    scored: list[tuple[float, str]] = []
    for s in solutions:
        if not isinstance(s, dict):
            continue
        sid = str(s.get("solution_id") or "").strip()
        if not sid:
            continue
        raw = s.get("score")
        try:
            score = float(raw) if raw is not None else float("-inf")
        except (TypeError, ValueError):
            score = float("-inf")
        scored.append((score, sid))
    if not scored:
        return None
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


def anomaly_metric_code(anomaly: dict) -> str:
    return str(
        anomaly.get("metric_name")
        or anomaly.get("rule_code")
        or anomaly.get("code")
        or ""
    ).strip()


async def run_flow(
    base_url: str,
    enterprise_id: str,
    store_id: str,
    poll_interval: float,
    timeout_seconds: int,
    snapshot_interval: float,
    snapshot_times: int,
) -> int:
    failed = 0
    flow_t0 = time.perf_counter()

    console.print(Panel("[bold]诊断全流程 E2E（兼容层）[/bold]", style="cyan"))

    # ① 执行诊断 + 轮询进度
    console.print(Panel("[bold]① 执行诊断[/bold] [dim]/diagnosis/start → status 轮询[/dim]", style="dim"))
    t_diag = time.perf_counter()
    ok, msg, start_data = await cc.start_diagnosis(base_url, enterprise_id, store_id)
    if not ok:
        console.print(Text(f"启动诊断失败: {msg}", style="red"))
        return 1
    console.print(Text(f"OK {msg}", style="green"))
    diagnosis_id = str((start_data or {}).get("diagnosis_id") or "").strip()
    if not diagnosis_id:
        console.print(Text("缺少 diagnosis_id", style="red"))
        return 1

    done_ok, _ = await cc.wait_status_done(base_url, diagnosis_id, poll_interval, timeout_seconds)
    diag_secs = time.perf_counter() - t_diag
    console.print(Text(f"诊断阶段耗时（启动 → 状态结束）: {diag_secs:.1f}s", style="dim"))
    if not done_ok:
        failed += 1

    # ② 查看诊断报告
    console.print(Panel("[bold]② 查看诊断报告[/bold] [dim]/diagnosis/report[/dim]", style="dim"))
    ok, report_or_msg = await cc.fetch_report(base_url, diagnosis_id)
    if not ok:
        console.print(Text(f"拉取报告失败: {report_or_msg}", style="red"))
        return 1
    report = report_or_msg if isinstance(report_or_msg, dict) else {}
    cc.print_report(report)
    anomalies = report.get("anomalies") or []

    # ENTER → ③④⑤ 异常指标
    wait_enter("③ 查看异常指标列表 → ④ 单个详情 → ⑤ 拾取指标（钻取）")
    if not anomalies:
        console.print(Text("报告中无异常指标，跳过 ③④⑤。", style="yellow"))
    else:
        t = cc.Table(title="③ 异常指标列表（遍历）", show_header=True, header_style="bold red")
        t.add_column("序号", style="magenta")
        t.add_column("anomaly_id", style="cyan")
        t.add_column("指标", style="white")
        for i, a in enumerate(anomalies, start=1):
            if not isinstance(a, dict):
                continue
            t.add_row(
                str(i),
                str(a.get("id", "")),
                str(a.get("rule_name") or a.get("metric_name", "")),
            )
        console.print(t)

        for i, a in enumerate(anomalies, start=1):
            if not isinstance(a, dict):
                continue
            aid = str(a.get("id", "")).strip()
            if not aid:
                continue
            console.print(Panel(f"[bold]④ 异常指标详情 [{i}/{len(anomalies)}][/bold] anomaly_id={aid}", style="dim"))
            ok_d, detail_or_msg = await cc.fetch_anomaly_detail(base_url, diagnosis_id, aid)
            if ok_d and isinstance(detail_or_msg, dict):
                console.print(Panel(json.dumps(detail_or_msg, ensure_ascii=False, indent=2), title="详情", style="dim"))
            else:
                console.print(Text(f"详情失败: {detail_or_msg}", style="red"))
                failed += 1

            metric_name = anomaly_metric_code(a)
            if metric_name:
                rule_cn = str(a.get("rule_name") or "").strip()
                if rule_cn == metric_name:
                    rule_cn = ""
                cn_suffix = f"  中文名：{rule_cn}" if rule_cn else ""
                console.print(
                    Panel(
                        f"[bold]⑤ 拾取指标（钻取）[/bold] metric_name={metric_name}{cn_suffix}",
                        style="dim",
                    )
                )
                ok_dr, drill_or_msg = await cc.fetch_drill_down(base_url, metric_name, enterprise_id)
                if ok_dr and isinstance(drill_or_msg, dict):
                    cc.print_drill_down(drill_or_msg)
                else:
                    console.print(Text(f"钻取失败: {drill_or_msg}", style="yellow"))
            else:
                console.print(Text("⑤ 跳过：无 metric_name/rule_code。", style="yellow"))

    # ENTER → ⑥⑦ 方案列表与详情
    wait_enter("⑥ 查看方案列表 → ⑦ 遍历方案详情")
    ok, sol_or_msg = await cc.fetch_solutions(base_url, diagnosis_id)
    if not ok:
        console.print(Text(f"方案列表失败: {sol_or_msg}", style="red"))
        return 1
    solutions = (sol_or_msg or {}).get("solutions") or [] if isinstance(sol_or_msg, dict) else []
    cc.print_solution_list(sol_or_msg if isinstance(sol_or_msg, dict) else {})
    for idx, s in enumerate(solutions, start=1):
        if not isinstance(s, dict):
            continue
        sid = str(s.get("solution_id", "")).strip()
        if not sid:
            continue
        console.print(Panel(f"[bold]⑦ 方案详情 [{idx}/{len(solutions)}][/bold] solution_id={sid}", style="dim"))
        ok_det, det = await cc.fetch_solution_detail(base_url, sid)
        if ok_det and isinstance(det, dict):
            console.print(Panel(json.dumps(det, ensure_ascii=False, indent=2), title="方案详情", style="dim"))
        else:
            console.print(Text(f"详情失败: {det}", style="red"))
            failed += 1

    # ENTER → ⑧ 采纳推荐方案（score 最高）
    wait_enter("⑧ 采纳推荐方案（score 最高的一条）")
    chosen = pick_recommended_solution_id(solutions)
    if not chosen:
        console.print(Text("无可采纳方案。", style="red"))
        return 1
    console.print(Text(f"采纳 solution_id={chosen}", style="bold green"))
    ok_ad, adopt_msg = await cc.adopt_solution(base_url, chosen)
    if not ok_ad:
        console.print(Text(f"采纳失败: {adopt_msg}", style="red"))
        return 1
    console.print(Text(str(adopt_msg), style="dim"))
    adopt_ok = await cc.wait_adopt_done(base_url, chosen, poll_interval, min(timeout_seconds, 600))
    if not adopt_ok:
        failed += 1

    # ENTER → ⑨⑩ 方案生成任务列表 + 任务详情
    wait_enter("⑨ 查看方案生成任务列表 → ⑩ 遍历任务详情")
    ok_t, tasks_or_msg = await cc.fetch_execution_tasks(base_url, diagnosis_id)
    if not ok_t:
        console.print(Text(f"任务列表失败: {tasks_or_msg}", style="red"))
        failed += 1
    elif isinstance(tasks_or_msg, dict):
        cc.print_execution_task_list(diagnosis_id, tasks_or_msg)
        tasks = tasks_or_msg.get("items") or []
        for ti, task in enumerate(tasks, start=1):
            if not isinstance(task, dict):
                continue
            tid = str(task.get("task_id", "")).strip()
            if not tid:
                continue
            console.print(Panel(f"[bold]⑩ 任务详情 [{ti}/{len(tasks)}][/bold] task_id={tid}", style="dim"))
            ok_td, td = await cc.fetch_execution_task_detail(base_url, tid)
            if ok_td:
                console.print(Panel(json.dumps(td, ensure_ascii=False, indent=2), title="任务详情", style="dim"))
            else:
                console.print(Text(f"任务详情失败: {td}", style="red"))
                failed += 1

    # ENTER → ⑪ 追踪详情（path 参数与前端一致：tracking_id == 诊断 thread_id）
    wait_enter("⑪ 查看追踪详情")
    tracking_id = diagnosis_id
    console.print(
        Text(
            f"tracking_id 使用诊断 thread_id（与前端 /api/v1/tracking/{{id}} 一致）: {tracking_id}",
            style="dim",
        )
    )
    ok_list, track_data = await cc.fetch_tracking_list(
        base_url, diagnosis_id, enterprise_id=enterprise_id
    )
    if ok_list and isinstance(track_data, dict):
        cc.print_tracking_list(diagnosis_id, track_data)
    else:
        console.print(Text(f"追踪列表（可选展示）失败或无数据: {track_data}", style="yellow"))

    failed += await dump_tracking_detail_views(
        base_url, tracking_id, "[bold]⑪ 追踪详情[/bold]（摘要 + analyze / trends / snapshots）"
    )

    # ENTER → ⑫ 每 10 秒自动采集快照，共 3 次
    wait_enter(f"⑫ 自动采集快照（间隔 {snapshot_interval}s，共 {snapshot_times} 次）— 确认后开始")
    for n in range(1, snapshot_times + 1):
        console.print(Text(f"  快照 [{n}/{snapshot_times}] POST /tracking/{{id}}/snapshot", style="cyan"))
        ok_snap, snap = await cc.post_tracking_snapshot(
            base_url, tracking_id, enterprise_id=enterprise_id
        )
        if ok_snap:
            console.print(Panel(json.dumps(snap, ensure_ascii=False, indent=2)[:4000], title=f"快照结果 {n}", style="dim"))
        else:
            console.print(Text(f"快照失败: {snap}", style="red"))
            failed += 1
        if n < snapshot_times:
            await asyncio.sleep(snapshot_interval)

    failed += await dump_tracking_detail_views(
        base_url,
        tracking_id,
        "[bold]⑫ 完成后自动刷新追踪详情[/bold]（摘要 + analyze / trends / snapshots）",
    )

    # ENTER → ⑬ 完成追踪 + 轮询复盘进度
    wait_enter("⑬ 完成追踪（轮询复盘进度）")
    t_complete = time.perf_counter()
    ok_c, cmp_res = await cc.post_tracking_complete(base_url, tracking_id)
    if not ok_c:
        console.print(Text(f"完成追踪提交失败: {cmp_res}", style="red"))
        failed += 1
    else:
        console.print(Panel(json.dumps(cmp_res, ensure_ascii=False, indent=2)[:2000], title="complete 响应", style="dim"))
    rev_ok, _ = await wait_review_progress_done(
        base_url, tracking_id, poll_interval, max(timeout_seconds, 300)
    )
    if not rev_ok:
        failed += 1
    complete_secs = time.perf_counter() - t_complete
    console.print(
        Text(
            f"完成追踪阶段耗时（POST complete → 复盘进度结束）: {complete_secs:.1f}s",
            style="dim",
        )
    )

    # ENTER → ⑭ 复盘报告
    wait_enter("⑭ 查看复盘报告")
    ok_rep, rep = await cc.fetch_tracking_report(base_url, tracking_id)
    if ok_rep and isinstance(rep, dict):
        console.print(Panel(json.dumps(rep, ensure_ascii=False, indent=2)[:8000], title=f"复盘报告 tracking_id={tracking_id}", style="dim"))
    else:
        console.print(Text(f"复盘报告失败: {rep}", style="red"))
        failed += 1

    total_secs = time.perf_counter() - flow_t0
    console.print(Text(f"全流程累计耗时（含人工停顿时长）: {total_secs:.1f}s", style="dim"))
    return 1 if failed else 0


def main() -> int:
    p = argparse.ArgumentParser(description="诊断全流程 E2E 测试 CLI（ENTER 暂停）")
    p.add_argument("--base-url", default=cc.DEFAULT_BASE, help=f"服务地址（默认 {cc.DEFAULT_BASE}）")
    p.add_argument("--enterprise-id", default="", help="企业 ID；省略则在启动时交互输入")
    p.add_argument("--store-id", default="", help="门店 ID；省略为空则全企业（兼容层 store_id）")
    p.add_argument("--poll-interval", type=float, default=2.0, help="轮询间隔秒")
    p.add_argument("--timeout", type=int, default=600, help="诊断/采纳等轮询超时秒")
    p.add_argument("--snapshot-interval", type=float, default=10.0, help="⑫ 快照间隔秒（默认 10）")
    p.add_argument("--snapshot-times", type=int, default=3, help="⑫ 快照次数（默认 3）")
    args = p.parse_args()

    eid = (args.enterprise_id or "").strip()
    if not eid:
        console.print("[bold]输入企业 ID[/bold]（enterprise_id）:", style="cyan")
        eid = (input().strip())
    if not eid:
        console.print(Text("enterprise_id 不能为空", style="red"))
        return 2

    return asyncio.run(
        run_flow(
            base_url=args.base_url.rstrip("/"),
            enterprise_id=eid,
            store_id=(args.store_id or "").strip(),
            poll_interval=max(0.5, args.poll_interval),
            timeout_seconds=max(30, args.timeout),
            snapshot_interval=max(1.0, args.snapshot_interval),
            snapshot_times=max(1, args.snapshot_times),
        )
    )


if __name__ == "__main__":
    sys.exit(main())
