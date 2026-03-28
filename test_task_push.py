#!/usr/bin/env python3
"""任务推送诊断工具 — 输入诊断id，获取已采纳方案的任务，重新推送给业务系统。"""

from __future__ import annotations

import asyncio
import json
import sys

import psycopg
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.core.config import CN_TZ, get_settings
from src.core.db_init import _uri_to_conninfo, ensure_ai_exec_task
from src.core.logging_setup import setup_logging
from src.mcp_servers.biz_api_client import BizAPIClient
from src.mcp_servers.tenant_router import TenantRouter

setup_logging("mcp-servers")
console = Console()


async def get_adopted_plan_id(thread_id: str) -> str | None:
    """从 LangGraph checkpoint 获取已采纳方案的 plan_id。"""
    try:
        from src.api.deps import get_graph_app

        app = await get_graph_app()
        config = {"configurable": {"thread_id": thread_id}}
        state = await app.aget_state(config)
        values = state.values if state.values else {}
        adopted_ids = values.get("adopted_plan_ids") or []
        return adopted_ids[0] if adopted_ids else None
    except Exception as e:
        console.print(f"[red]获取已采纳方案失败: {e}[/red]")
        return None


async def fetch_adopted_plan_tasks(thread_id: str) -> list[dict]:
    """根据诊断id获取已采纳方案的任务。"""
    # 先获取已采纳方案的 plan_id
    adopted_plan_id = await get_adopted_plan_id(thread_id)
    if not adopted_plan_id:
        console.print("[yellow]该诊断未找到已采纳的方案[/yellow]")
        return []

    console.print(f"[green]✓[/green] 已采纳方案ID: {adopted_plan_id}")

    # 从 ai_exec_task 表查询该方案的任务
    await ensure_ai_exec_task()
    conninfo = _uri_to_conninfo(get_settings().postgres_uri)

    async with await psycopg.AsyncConnection.connect(conninfo) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT task_id, thread_id, tenant_id, store_id, plan_id, task_name, description,
                       assignee_user_id, assignee_account_id, assignee_dept_id, deadline, deadline_at, priority, status,
                       related_resources, created_at
                FROM ai_exec_task
                WHERE thread_id = %s AND plan_id = %s
                ORDER BY created_at ASC
                """,
                (thread_id, adopted_plan_id),
            )
            rows = await cur.fetchall()

    tasks = []
    for row in rows:
        tasks.append(
            {
                "task_id": row[0],
                "thread_id": row[1],
                "tenant_id": row[2],
                "store_id": row[3],
                "plan_id": row[4],
                "task_name": row[5],
                "description": row[6],
                "assignee_user_id": row[7],
                "assignee_account_id": row[8],
                "assignee_dept_id": row[9],
                "deadline": row[10],
                "deadline_at": (
                    (
                        row[11].astimezone(CN_TZ) if getattr(row[11], "tzinfo", None) else row[11].replace(tzinfo=CN_TZ)
                    ).isoformat()
                    if row[11]
                    else ""
                ),
                "priority": row[12],
                "status": row[13],
                "related_resources": row[14] if isinstance(row[14], dict) else json.loads(row[14] or "{}"),
                "created_at": row[15].isoformat() if row[15] else "",
            }
        )
    return tasks


async def push_tasks_to_biz(
    tasks: list[dict],
    dry_run: bool = False,
) -> None:
    """将任务推送到业务系统 /ai-diagnosis/exec-task/batch-create 接口。"""
    if not tasks:
        console.print("[yellow]没有可推送的任务[/yellow]")
        return

    console.print("\n[yellow]>>> 开始推送任务到业务系统...[/yellow]")
    router = TenantRouter()
    biz = BizAPIClient(router)

    success_count = 0
    fail_count = 0

    # 按 plan_id 分组推送
    plan_groups: dict[str, list[dict]] = {}
    for task in tasks:
        plan_id = task.get("plan_id", "")
        if plan_id not in plan_groups:
            plan_groups[plan_id] = []
        plan_groups[plan_id].append(task)

    for plan_id, plan_tasks in plan_groups.items():
        if not plan_tasks:
            continue

        tenant_id = plan_tasks[0].get("tenant_id", "")
        store_id = plan_tasks[0].get("store_id", "")

        if not tenant_id:
            console.print(f"  [dim]跳过 plan_id={plan_id}: 缺少 tenant_id[/dim]")
            fail_count += len(plan_tasks)
            continue

        payload_tasks = []
        for task in plan_tasks:
            payload_tasks.append(
                {
                    "task_name": task.get("task_name", ""),
                    "description": task.get("description", ""),
                    "assignee_user_id": task.get("assignee_user_id"),
                    "assignee_account_id": task.get("assignee_account_id", ""),
                    "assignee_dept_id": task.get("assignee_dept_id", ""),
                    "deadline": task.get("deadline", ""),
                    "deadline_at": task.get("deadline_at", ""),
                    "priority": task.get("priority", ""),
                    "related_resources": task.get("related_resources", {}),
                }
            )

        payload = {"storeId": store_id, "planId": plan_id, "tasks": payload_tasks}

        if dry_run:
            console.print(f"  [dim]DRY-RUN: 将推送 {len(payload_tasks)} 个任务到 tenant={tenant_id}[/dim]")
            console.print(f"    {json.dumps(payload, ensure_ascii=False)}")
            success_count += len(payload_tasks)
            continue

        try:
            await biz.post(tenant_id, "/ai-diagnosis/exec-task/batch-create", payload)
            for task in plan_tasks:
                console.print(f"  [green]✓[/green] task_id={task.get('task_id')} 推送成功")
            success_count += len(plan_tasks)
        except Exception as e:
            for task in plan_tasks:
                console.print(f"  [red]✗[/red] task_id={task.get('task_id')} 推送失败: {e}")
            fail_count += len(plan_tasks)

    console.print()
    _print_summary(success_count, fail_count, dry_run)


def _print_task_list(tasks: list[dict]) -> None:
    """打印任务列表。"""
    t = Table(title="执行任务", show_header=True, header_style="bold magenta")
    t.add_column("task_id", style="cyan", width=16)
    t.add_column("plan_id", style="blue", width=10)
    t.add_column("任务名称", style="white", width=25)
    t.add_column("状态", style="yellow", width=10)
    t.add_column("租户", style="green", width=10)
    t.add_column("创建时间", style="dim", width=20)

    for task in tasks:
        t.add_row(
            task.get("task_id", "")[:16],
            task.get("plan_id", "")[:10],
            (task.get("task_name") or "-")[:25],
            task.get("status", "-"),
            task.get("tenant_id", "-")[:10],
            task.get("created_at", "")[:19] if task.get("created_at") else "-",
        )
    console.print(t)

    console.print()
    detail_t = Table(title="任务详情", show_header=True, header_style="bold blue")
    detail_t.add_column("task_id", style="cyan", width=16)
    detail_t.add_column("负责人", style="yellow", width=12)
    detail_t.add_column("截止日期", style="green", width=12)
    detail_t.add_column("描述摘要", style="white", width=40)

    for task in tasks:
        assignee = task.get("assignee_account_id") or str(task.get("assignee_user_id", "-"))
        detail_t.add_row(
            task.get("task_id", "")[:16],
            assignee[:12],
            task.get("deadline", "-")[:12],
            (task.get("description") or "-")[:40],
        )
    console.print(detail_t)


def _print_summary(success: int, fail: int, dry_run: bool) -> None:
    """打印推送结果汇总。"""
    mode = "[yellow]DRY-RUN 模式（未实际推送）[/yellow]" if dry_run else "[green]实际推送模式[/green]"
    t = Table(title="推送结果汇总", show_header=False)
    t.add_column("项目", style="cyan", width=15)
    t.add_column("结果", style="white")
    t.add_row("执行模式", mode)
    t.add_row("成功数", str(success))
    t.add_row("失败数", str(fail))
    t.add_row("总计", str(success + fail))
    console.print(t)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="任务推送诊断工具 - 重新推送已采纳方案的任务")
    parser.add_argument("thread_id", nargs="?", help="诊断 thread_id")
    parser.add_argument("--dry-run", action="store_true", help="仅展示任务，不实际推送")
    args = parser.parse_args()

    if args.thread_id:
        try:
            thread_id = args.thread_id.strip()
            tasks = asyncio.run(fetch_adopted_plan_tasks(thread_id))

            if not tasks:
                console.print("[yellow]未找到该诊断已采纳方案的执行任务[/yellow]")
                return

            console.print(Panel(f"[bold cyan]任务推送诊断[/bold cyan]\nthread_id: {thread_id}", border_style="cyan"))
            console.print(f"[green]✓[/green] 共找到 {len(tasks)} 条已采纳方案的执行任务")
            _print_task_list(tasks)

            if not args.dry_run:
                console.print()
                confirm = input("确认重新推送这些任务到业务系统? (y/N): ").strip().lower()
                if confirm != "y":
                    console.print("[yellow]已取消[/yellow]")
                    return

            asyncio.run(push_tasks_to_biz(tasks, dry_run=args.dry_run))
        except Exception as e:
            console.print(f"[red]执行异常: {e}[/red]")
    else:
        console.print(
            Panel(
                "[bold]任务推送诊断工具[/bold]\n输入诊断 thread_id 后回车，将重新推送已采纳方案的任务",
                border_style="blue",
            )
        )
        while True:
            console.print()
            thread_id = input("请输入诊断 thread_id (输入 q 退出): ").strip()
            if thread_id.lower() == "q":
                console.print("[dim]再见![/dim]")
                break
            if not thread_id:
                console.print("[yellow]thread_id 不能为空[/yellow]")
                continue

            tasks = asyncio.run(fetch_adopted_plan_tasks(thread_id))

            if not tasks:
                console.print("[yellow]未找到该诊断已采纳方案的执行任务[/yellow]")
                continue

            console.print(f"[green]✓[/green] 共找到 {len(tasks)} 条已采纳方案的执行任务")
            _print_task_list(tasks)

            dry_run_input = input("是否仅展示不推送? (y/N): ").strip().lower()
            dry_run = dry_run_input == "y"

            if not dry_run:
                confirm = input("确认重新推送这些任务到业务系统? (y/N): ").strip().lower()
                if confirm != "y":
                    console.print("[yellow]已取消[/yellow]")
                    continue

            try:
                asyncio.run(push_tasks_to_biz(tasks, dry_run=dry_run))
            except KeyboardInterrupt:
                console.print("\n[yellow]已取消[/yellow]")
            except Exception as e:
                console.print(f"[red]执行异常: {e}[/red]")


if __name__ == "__main__":
    main()
