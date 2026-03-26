#!/usr/bin/env python3
"""任务推送测试 — 输入诊断id，从库中拉取历史诊断计划执行任务，推送给业务系统。"""

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


async def fetch_exec_tasks(thread_id: str | None = None, plan_id: str | None = None) -> list[dict]:
    """根据诊断id从ai_exec_task表拉取任务历史。"""
    await ensure_ai_exec_task()
    conninfo = _uri_to_conninfo(get_settings().postgres_uri)

    async with await psycopg.AsyncConnection.connect(conninfo) as conn:
        async with conn.cursor() as cur:
            if thread_id:
                await cur.execute(
                    """
                    SELECT task_id, thread_id, tenant_id, store_id, plan_id, task_name, description,
                           assignee_user_id, assignee_account_id, assignee_dept_id, deadline, deadline_at, priority, status,
                           related_resources, created_at
                    FROM ai_exec_task
                    WHERE thread_id = %s
                    ORDER BY created_at ASC
                    """,
                    (thread_id,),
                )
            elif plan_id:
                await cur.execute(
                    """
                    SELECT task_id, thread_id, tenant_id, store_id, plan_id, task_name, description,
                           assignee_user_id, assignee_account_id, assignee_dept_id, deadline, deadline_at, priority, status,
                           related_resources, created_at
                    FROM ai_exec_task
                    WHERE plan_id = %s
                    ORDER BY created_at ASC
                    """,
                    (plan_id,),
                )
            else:
                console.print("[red]必须提供 thread_id 或 plan_id[/red]")
                return []
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
                    (row[11].astimezone(CN_TZ) if getattr(row[11], "tzinfo", None) else row[11].replace(tzinfo=CN_TZ)).isoformat()
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

    for task in tasks:
        tenant_id = task.get("tenant_id", "")
        store_id = task.get("store_id", "")
        plan_id = task.get("plan_id", "")

        if not tenant_id:
            console.print(f"  [dim]跳过 task_id={task.get('task_id')}: 缺少 tenant_id[/dim]")
            fail_count += 1
            continue

        payload_tasks = [
            {
                "taskName": task.get("task_name", ""),
                "description": task.get("description", ""),
                "assigneeUserId": task.get("assignee_user_id"),
                "assigneeAccountId": task.get("assignee_account_id", ""),
                "assigneeDeptId": task.get("assignee_dept_id", ""),
                "deadline": task.get("deadline", ""),
                "deadlineAt": task.get("deadline_at", ""),
                "priority": task.get("priority", ""),
                "relatedResources": task.get("related_resources", {}),
            }
        ]
        payload = {"storeId": store_id, "planId": plan_id, "tasks": payload_tasks}

        if dry_run:
            console.print(f"  [dim]DRY-RUN: 将推送任务到 tenant={tenant_id}[/dim]")
            console.print(f"    {json.dumps(payload, ensure_ascii=False)}")
            success_count += 1
            continue

        try:
            await biz.post(tenant_id, "/ai-diagnosis/exec-task/batch-create", payload)
            console.print(f"  [green]✓[/green] task_id={task.get('task_id')} 推送成功")
            success_count += 1
        except Exception as e:
            console.print(f"  [red]✗[/red] task_id={task.get('task_id')} 推送失败: {e}")
            fail_count += 1

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

    parser = argparse.ArgumentParser(description="任务推送测试工具")
    parser.add_argument("diagnosis_id", nargs="?", help="诊断thread_id或plan_id")
    parser.add_argument("--type", choices=["thread", "plan"], default="thread", help="diagnosis_id类型")
    parser.add_argument("--dry-run", action="store_true", help="仅展示任务，不实际推送")
    args = parser.parse_args()

    if args.diagnosis_id:
        try:
            diagnosis_id = args.diagnosis_id.strip()
            if args.type == "thread":
                tasks = asyncio.run(fetch_exec_tasks(thread_id=diagnosis_id))
            else:
                tasks = asyncio.run(fetch_exec_tasks(plan_id=diagnosis_id))

            if not tasks:
                console.print("[yellow]未找到该诊断的执行任务[/yellow]")
                return

            console.print(
                Panel(f"[bold cyan]任务推送测试[/bold cyan]\ndiagnosis_id: {diagnosis_id}", border_style="cyan")
            )
            console.print(f"[green]✓[/green] 共找到 {len(tasks)} 条执行任务记录")
            _print_task_list(tasks)

            if not args.dry_run:
                console.print()
                confirm = input("确认推送这些任务到业务系统? (y/N): ").strip().lower()
                if confirm != "y":
                    console.print("[yellow]已取消[/yellow]")
                    return

            asyncio.run(push_tasks_to_biz(tasks, dry_run=args.dry_run))
        except Exception as e:
            console.print(f"[red]执行异常: {e}[/red]")
    else:
        console.print(Panel("[bold]任务推送测试工具[/bold]\n输入诊断 thread_id 或 plan_id 后回车", border_style="blue"))
        while True:
            console.print()
            diagnosis_id = input("请输入诊断 ID (输入 q 退出): ").strip()
            if diagnosis_id.lower() == "q":
                console.print("[dim]再见![/dim]")
                break
            if not diagnosis_id:
                console.print("[yellow]diagnosis_id 不能为空[/yellow]")
                continue

            console.print("请选择 ID 类型:")
            console.print("  1) thread_id (诊断会话ID)")
            console.print("  2) plan_id (诊断方案ID)")
            selection = input("请输入选项(默认1): ").strip()
            id_type = {"1": "thread", "2": "plan", "": "thread"}.get(selection, "thread")

            if id_type == "thread":
                tasks = asyncio.run(fetch_exec_tasks(thread_id=diagnosis_id))
            else:
                tasks = asyncio.run(fetch_exec_tasks(plan_id=diagnosis_id))

            if not tasks:
                console.print("[yellow]未找到该诊断的执行任务[/yellow]")
                continue

            console.print(f"[green]✓[/green] 共找到 {len(tasks)} 条执行任务记录")
            _print_task_list(tasks)

            dry_run_input = input("是否仅展示不推送? (y/N): ").strip().lower()
            dry_run = dry_run_input == "y"

            if not dry_run:
                confirm = input("确认推送这些任务到业务系统? (y/N): ").strip().lower()
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
