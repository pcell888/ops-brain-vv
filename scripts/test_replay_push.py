#!/usr/bin/env python3
"""推送消息重放测试 — 输入诊断id，从库中拉取消息历史并重新推送给业务系统。"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime

import psycopg
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.core.config import get_settings
from src.core.db_init import _uri_to_conninfo, ensure_ai_push_log
from src.core.logging_setup import setup_logging
from src.mcp_servers.biz_api_client import BizAPIClient
from src.mcp_servers.biz_scope import effective_store_id_for_biz
from src.mcp_servers.tenant_router import TenantRouter

setup_logging("mcp-servers")
console = Console()


async def fetch_push_logs(thread_id: str) -> list[dict]:
    """根据诊断id从ai_push_log表拉取消息历史。"""
    await ensure_ai_push_log()
    conninfo = _uri_to_conninfo(get_settings().postgres_uri)

    async with await psycopg.AsyncConnection.connect(conninfo) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, thread_id, tenant_id, store_id, kind, message_type, title, content, extra, created_at
                FROM ai_push_log
                WHERE thread_id = %s
                ORDER BY created_at ASC
                """,
                (thread_id,),
            )
            rows = await cur.fetchall()

    logs = []
    for row in rows:
        logs.append(
            {
                "id": row[0],
                "thread_id": row[1],
                "tenant_id": row[2],
                "store_id": row[3],
                "kind": row[4],
                "message_type": row[5],
                "title": row[6],
                "content": row[7],
                "extra": row[8] if isinstance(row[8], dict) else json.loads(row[8] or "{}"),
                "created_at": row[9].isoformat() if row[9] else "",
            }
        )
    return logs


def _match_push_type(kind: str, push_type: str) -> bool:
    """按测试选型匹配记录类型。"""
    if push_type == "all":
        return True
    if push_type == "targeted_message":
        return kind == "message"
    if push_type == "task":
        return kind == "task"
    return True


def _push_type_label(push_type: str) -> str:
    if push_type == "targeted_message":
        return "定向人群消息推送"
    if push_type == "task":
        return "任务推送"
    return "全部"


async def replay_push_messages(
    thread_id: str,
    dry_run: bool = False,
    default_account_id: str = "",
    push_type: str = "all",
    default_target_segment: str = "low_conversion",
) -> None:
    """重新推送指定诊断id的消息历史到业务系统。"""
    console.print(Panel(f"[bold cyan]消息重放工具[/bold cyan]\nthread_id: {thread_id}", border_style="cyan"))

    # 1. 拉取消息历史
    console.print("\n[yellow]>>> 从数据库拉取消息历史...[/yellow]")
    try:
        logs = await fetch_push_logs(thread_id)
    except Exception as e:
        console.print(f"[red]拉取失败: {e}[/red]")
        return

    if not logs:
        console.print("[yellow]未找到该诊断的推送记录[/yellow]")
        return

    filtered_logs = [log for log in logs if _match_push_type(log.get("kind", ""), push_type)]
    console.print(f"[green]✓[/green] 共找到 {len(logs)} 条推送记录，选型=[cyan]{_push_type_label(push_type)}[/cyan]")
    console.print(f"[green]✓[/green] 选型命中 {len(filtered_logs)} 条")

    if not filtered_logs:
        console.print("[yellow]当前选型下没有可推送记录[/yellow]")
        return

    # 2. 展示消息列表
    _print_push_logs(filtered_logs)

    # 3. 确认是否推送
    if not dry_run:
        console.print()
        confirm = input("确认重新推送这些消息? (y/N): ").strip().lower()
        if confirm != "y":
            console.print("[yellow]已取消[/yellow]")
            return

    # 4. 执行推送
    console.print("\n[yellow]>>> 开始推送消息...[/yellow]")
    router = TenantRouter()
    biz = BizAPIClient(router)

    success_count = 0
    fail_count = 0

    for log in filtered_logs:
        tenant_id = log["tenant_id"]
        message_type = log["message_type"]
        title = log["title"]
        content = log["content"]
        extra = log.get("extra", {})

        # 从extra中提取accountId等信息
        account_id = extra.get("accountId", extra.get("account_id", ""))
        jump_url = extra.get("jumpUrl", extra.get("jump_url", ""))
        biz_id = extra.get("bizId", extra.get("biz_id", ""))
        target_segment = extra.get("targetSegment", extra.get("target_segment", default_target_segment))

        # 定向人群推送走 /message-remind/targeted，不依赖 accountId
        if push_type == "targeted_message":
            payload = {
                "storeId": effective_store_id_for_biz(tenant_id, log.get("store_id", "")),
                "targetSegment": target_segment or default_target_segment,
                "title": title,
                "content": content,
                "type": message_type or "ai_targeted",
            }
            if dry_run:
                console.print(f"  [dim]DRY-RUN: 将定向推送到 tenant={tenant_id}[/dim]")
                console.print(f"    {json.dumps(payload, ensure_ascii=False)}")
                success_count += 1
                continue
            try:
                await biz.post(tenant_id, "/message-remind/targeted", payload)
                console.print(f"  [green]✓[/green] id={log['id']} 定向推送成功")
                success_count += 1
            except Exception as e:
                console.print(f"  [red]✗[/red] id={log['id']} 定向推送失败: {e}")
                fail_count += 1
            continue

        if not account_id and default_account_id:
            account_id = default_account_id

        if not account_id:
            # 这里的“跳过”通常意味着历史写入 ai_push_log 时没有把 accountId 放进 extra。
            extra_keys = sorted(list(extra.keys())) if isinstance(extra, dict) else []
            extra_preview = (
                json.dumps(extra, ensure_ascii=False)[:400] + "..."
                if isinstance(extra, dict) and extra
                else str(extra)
            )
            console.print(
                f"  [dim]跳过 id={log['id']}: 缺少 accountId; tenant={tenant_id} type={message_type} "
                f"extra_keys={extra_keys} extra_preview={extra_preview}[/dim]"
            )
            fail_count += 1
            continue

        message = {
            "accountId": str(account_id),
            "title": title,
            "content": content,
            "type": message_type,
        }
        if jump_url:
            message["jumpUrl"] = jump_url
        if biz_id:
            message["bizId"] = biz_id

        if dry_run:
            console.print(f"  [dim]DRY-RUN: 将推送到 tenant={tenant_id}[/dim]")
            console.print(f"    {json.dumps(message, ensure_ascii=False)}")
            success_count += 1
            continue

        try:
            await biz.post(tenant_id, "/message-remind/batch-create", {"messages": [message]})
            console.print(f"  [green]✓[/green] id={log['id']} 推送成功")
            success_count += 1
        except Exception as e:
            console.print(f"  [red]✗[/red] id={log['id']} 推送失败: {e}")
            fail_count += 1

    # 5. 汇总结果
    console.print()
    _print_summary(success_count, fail_count, dry_run)


def _print_push_logs(logs: list[dict]) -> None:
    """打印推送记录列表。"""
    t = Table(title="推送记录", show_header=True, header_style="bold magenta")
    t.add_column("ID", style="cyan", width=6)
    t.add_column("类型", style="green", width=12)
    t.add_column("标题", style="white", width=30)
    t.add_column("租户", style="yellow", width=12)
    t.add_column("创建时间", style="dim", width=20)

    for log in logs:
        t.add_row(
            str(log["id"]),
            log["kind"] or "-",
            (log["title"] or "-")[:30],
            log["tenant_id"] or "-",
            log["created_at"][:19] if log["created_at"] else "-",
        )
    console.print(t)

    # 展示消息详情
    console.print()
    detail_t = Table(title="消息详情", show_header=True, header_style="bold blue")
    detail_t.add_column("ID", style="cyan", width=6)
    detail_t.add_column("消息类型", style="green", width=16)
    detail_t.add_column("账号ID", style="yellow", width=12)
    detail_t.add_column("内容摘要", style="white", width=40)

    for log in logs:
        extra = log.get("extra", {})
        account_id = extra.get("accountId", extra.get("account_id", "-"))
        detail_t.add_row(
            str(log["id"]),
            log["message_type"] or "-",
            str(account_id),
            (log["content"] or "-")[:40],
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

    parser = argparse.ArgumentParser(description="推送消息重放测试工具")
    parser.add_argument("thread_id", nargs="?", help="诊断thread_id")
    parser.add_argument("--dry-run", action="store_true", help="仅展示消息，不实际推送")
    parser.add_argument(
        "--default-account-id",
        default="",
        help="当历史记录缺少 accountId 时，使用该值作为兜底（谨慎使用）",
    )
    parser.add_argument(
        "--push-type",
        choices=["all", "targeted_message", "task"],
        default="all",
        help="测试选型：targeted_message=定向人群消息推送，task=任务推送，all=全部",
    )
    parser.add_argument(
        "--target-segment",
        default="low_conversion",
        help="定向人群推送默认分群（仅 push-type=targeted_message 生效）",
    )
    args = parser.parse_args()

    if args.thread_id:
        try:
            asyncio.run(
                replay_push_messages(
                    args.thread_id,
                    dry_run=args.dry_run,
                    default_account_id=args.default_account_id,
                    push_type=args.push_type,
                    default_target_segment=args.target_segment,
                )
            )
        except Exception as e:
            console.print(f"[red]执行异常: {e}[/red]")
    else:
        # 交互模式
        console.print(Panel("[bold]推送消息重放测试工具[/bold]\n输入诊断 thread_id 后回车", border_style="blue"))
        while True:
            console.print()
            thread_id = input("请输入 thread_id (输入 q 退出): ").strip()
            if thread_id.lower() == "q":
                console.print("[dim]再见![/dim]")
                break
            if not thread_id:
                console.print("[yellow]thread_id 不能为空[/yellow]")
                continue
            console.print("\n请选择测试选型:")
            console.print("  1) 定向人群消息推送")
            console.print("  2) 任务推送")
            console.print("  3) 全部")
            selection = input("请输入选项(默认3): ").strip()
            push_type = {"1": "targeted_message", "2": "task", "3": "all", "": "all"}.get(selection, "all")
            dry_run_input = input("是否仅展示不推送? (y/N): ").strip().lower()
            dry_run = dry_run_input == "y"
            target_segment = "low_conversion"
            if push_type == "targeted_message":
                target_segment = input(
                    "定向分群 targetSegment (默认 low_conversion): "
                ).strip() or "low_conversion"
            default_account_id = input("缺少 accountId 时是否使用兜底 accountId? (留空表示不兜底): ").strip()
            try:
                asyncio.run(
                    replay_push_messages(
                        thread_id,
                        dry_run=dry_run,
                        default_account_id=default_account_id,
                        push_type=push_type,
                        default_target_segment=target_segment,
                    )
                )
            except KeyboardInterrupt:
                console.print("\n[yellow]已取消[/yellow]")
            except Exception as e:
                console.print(f"[red]执行异常: {e}[/red]")


if __name__ == "__main__":
    main()
