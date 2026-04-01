#!/usr/bin/env python3
"""指标采集测试 — 查询租户配置后调用 MCP metrics-server 测试指标获取。"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

from src.mcp_servers.metrics_server import (
    get_crm_indicators,
    get_marketing_indicators,
    get_retention_indicators,
    get_efficiency_indicators,
)
from src.mcp_servers.crm_server import (
    get_customer_list,
    get_dept_tree,
    get_order_analytics,
    get_sales_contract_list,
    get_store_profile,
    get_users_by_dept,
)
from src.mcp_servers.tenant_router import TenantRouter, TenantNotFoundError
from src.core.calculator import INDICATOR_META


DIM_TOOLS = {
    "crm": ("CRM 客户管理", get_crm_indicators),
    "marketing": ("营销效果", get_marketing_indicators),
    "retention": ("客户留存", get_retention_indicators),
    "efficiency": ("运营效率", get_efficiency_indicators),
}


async def test_collect_profile(tenant_id: str, store_id: str = ""):
    """测试企业画像采集。"""
    console.print(Panel("[bold cyan]查询租户配置...[/bold cyan]", border_style="cyan"))
    router = TenantRouter()
    try:
        ctx = await router.resolve(tenant_id)
    except TenantNotFoundError:
        console.print(f"[red]租户不存在: {tenant_id}[/red]")
        return
    except Exception as e:
        console.print(f"[red]查询租户配置失败: {e}[/red]")
        return

    console.print(f"  企业名称: {ctx.tenant_name}")
    console.print(f"  API地址:  {ctx.api_base_url}")
    console.print(f"  行业代码: {ctx.industry_code or '-'}")
    console.print()

    console.print(
        Panel(
            f"[bold cyan]开始采集企业画像...[/bold cyan]\ntenant_id: {tenant_id}\nstore_id: {store_id or '(全企业)'}",
            border_style="cyan",
        )
    )

    now = datetime.now()
    start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    end_date = now.strftime("%Y-%m-%d %H:%M:%S")

    try:
        result = await get_store_profile(
            tenant_id=tenant_id,
            store_id=store_id,
        )
        _print_profile(result)
    except Exception as e:
        console.print(f"[red]企业画像失败: {e}[/red]")

    # GET /client-record/list
    try:
        console.print(Panel("[bold cyan]GET /client-record/list — 客户列表[/bold cyan]", border_style="cyan"))
        cl = await get_customer_list(
            tenant_id=tenant_id,
            store_id=store_id,
            filter_type="all",
            page=1,
            page_size=10,
        )
        _print_simple_rows(
            f"total={cl.get('total', 0)}",
            cl.get("items", []),
            ["id", "name", "phone", "tags", "lastOrderDays"],
        )
    except Exception as e:
        console.print(f"[red]客户列表失败: {e}[/red]")

    first_client_id: str | None = None
    try:
        cl2 = await get_customer_list(
            tenant_id=tenant_id,
            store_id=store_id,
            filter_type="all",
            page=1,
            page_size=1,
        )
        items = cl2.get("items") or []
        if items:
            first_client_id = str(items[0].get("id", "") or "")
    except Exception:
        pass

    # GET /sales-contract/list
    try:
        console.print(Panel("[bold cyan]GET /sales-contract/list — 销售合同列表[/bold cyan]", border_style="cyan"))
        sc = await get_sales_contract_list(
            tenant_id=tenant_id,
            # client_record_id=first_client_id or None,
        )
        _print_simple_rows(
            f"total={sc.get('total', 0)}"
            + (f" (clientRecordId={first_client_id})" if first_client_id else " (未筛选客户)"),
            sc.get("items", []),
            ["id", "amount", "status"],
        )
    except Exception as e:
        console.print(f"[red]销售合同列表失败: {e}[/red]")

    # GET /store-order/analytics
    try:
        console.print(Panel("[bold cyan]GET /store-order/analytics — 订单分析[/bold cyan]", border_style="cyan"))
        oa = await get_order_analytics(
            tenant_id=tenant_id,
            store_id=store_id,
            start_date=start_date,
            end_date=end_date,
            group_by="day",
        )
        _print_kv_block(oa)
    except Exception as e:
        console.print(f"[red]订单分析失败: {e}[/red]")

    # GET /sys-dept/tree + GET /sys-user/list（示例：第一个部门）
    dept_raw: list = []
    try:
        console.print(Panel("[bold cyan]GET /sys-dept/tree — 部门树[/bold cyan]", border_style="cyan"))
        dt = await get_dept_tree(tenant_id=tenant_id, store_id=store_id)
        dept_raw = list(dt.get("list") or dt.get("children") or [])
        _print_simple_rows(f"节点数={len(dept_raw)}", dept_raw, ["deptId", "deptName", "parentId", "id", "name"])
    except Exception as e:
        console.print(f"[red]部门树失败: {e}[/red]")

    try:
        first_dept_id: str | None = None
        for d in dept_raw:
            first_dept_id = str(d.get("deptId") or d.get("id") or "")
            if first_dept_id:
                break
        console.print(Panel("[bold cyan]GET /sys-user/list — 部门下用户[/bold cyan]", border_style="cyan"))
        if not first_dept_id:
            console.print("[yellow]  无部门节点，跳过用户列表[/yellow]")
        else:
            ul = await get_users_by_dept(tenant_id=tenant_id, dept_id=first_dept_id)
            users = ul.get("list", [])
            _print_simple_rows(f"deptId={first_dept_id}, 人数={len(users)}", users, ["userId", "userName", "deptId"])
    except Exception as e:
        console.print(f"[red]部门用户列表失败: {e}[/red]")

    await router.close()


def _print_profile(data: dict):
    """打印企业画像数据。"""
    if not data:
        console.print("[yellow]  无数据[/yellow]")
        return

    t = Table(show_header=True, header_style="bold blue")
    t.add_column("字段", style="cyan", width=20)
    t.add_column("值", style="green")

    for key, value in data.items():
        if isinstance(value, (list, dict)):
            display_value = f"{type(value).__name__} (len={len(value)})"
        else:
            display_value = str(value)
        t.add_row(key, display_value)

    console.print(t)


def _cell(row: dict, k: str) -> str:
    if k in row:
        return str(row[k])
    if k == "id":
        for alt in ("id", "deptId", "userId"):
            if alt in row:
                return str(row[alt])
    return "-"


def _print_simple_rows(subtitle: str, rows: list, keys: list[str]):
    if not rows:
        console.print(f"  [dim]{subtitle}[/dim] — [yellow]无数据[/yellow]")
        return
    console.print(f"  [dim]{subtitle}[/dim]")
    t = Table(show_header=True, header_style="bold blue")
    for k in keys:
        t.add_column(k, overflow="fold")
    for row in rows[:50]:
        if not isinstance(row, dict):
            t.add_row(str(row))
            continue
        t.add_row(*[_cell(row, k) for k in keys])
    if len(rows) > 50:
        console.print(f"  [dim]… 仅展示前 50 条，共 {len(rows)} 条[/dim]")
    console.print(t)


def _print_kv_block(data: dict):
    if not data:
        console.print("[yellow]  无数据[/yellow]")
        return
    t = Table(show_header=True, header_style="bold blue")
    t.add_column("字段", style="cyan")
    t.add_column("值", style="green")
    for k, v in data.items():
        t.add_row(str(k), str(v))
    console.print(t)


async def test_collect(tenant_id: str, store_id: str = "", dimensions: list[str] | None = None):
    """测试指标采集。"""
    if dimensions is None:
        dimensions = list(DIM_TOOLS.keys())

    # 查询租户配置
    console.print(Panel("[bold cyan]查询租户配置...[/bold cyan]", border_style="cyan"))
    router = TenantRouter()
    try:
        ctx = await router.resolve(tenant_id)
    except TenantNotFoundError:
        console.print(f"[red]租户不存在: {tenant_id}[/red]")
        return
    except Exception as e:
        console.print(f"[red]查询租户配置失败: {e}[/red]")
        return

    console.print(f"  企业名称: {ctx.tenant_name}")
    console.print(f"  API地址:  {ctx.api_base_url}")
    console.print(f"  行业代码: {ctx.industry_code or '-'}")
    console.print(f"  鉴权头:   {ctx.auth_headers}")
    console.print()

    now = datetime.now()
    start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    end_date = now.strftime("%Y-%m-%d %H:%M:%S")

    console.print(
        Panel(
            f"[bold cyan]开始采集指标[/bold cyan]\n"
            f"tenant_id: {tenant_id}\n"
            f"store_id: {store_id or '(全企业)'}\n"
            f"时间: {start_date} ~ {end_date}",
            border_style="cyan",
        )
    )

    for dim in dimensions:
        dim_name, tool_fn = DIM_TOOLS[dim]
        console.print(f"\n[yellow]>>> 采集 {dim_name}...[/yellow]")
        try:
            result = await tool_fn(
                tenant_id=tenant_id,
                store_id=store_id,
                start_date=start_date,
                end_date=end_date,
            )
            _print_indicators(result)
        except Exception as e:
            console.print(f"[red]采集失败: {e}[/red]")

    await router.close()


def _print_indicators(data: dict):
    """打印指标数据。"""
    indicators = data.get("indicators", {})
    if not indicators:
        console.print("[yellow]  无数据[/yellow]")
        return

    t = Table(show_header=True, header_style="bold blue")
    t.add_column("指标代码", style="cyan", width=25)
    t.add_column("指标名称", style="white", width=20)
    t.add_column("值", style="green", width=12)
    t.add_column("单位", style="blue", width=8)
    t.add_column("原始数据", style="dim")

    for code, ind_data in indicators.items():
        if not isinstance(ind_data, dict):
            continue
        meta = INDICATOR_META.get(code, {})
        t.add_row(
            code,
            meta.get("name", code),
            str(ind_data.get("value", "-")),
            ind_data.get("unit", ""),
            str(ind_data.get("raw_data", {})),
        )
    console.print(t)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="指标采集测试")
    parser.add_argument("tenant_id", help="企业ID")
    parser.add_argument("store_id", nargs="?", default="", help="店铺ID")
    parser.add_argument(
        "-d", "--dimensions", nargs="+", choices=["crm", "marketing", "retention", "efficiency", "profile"]
    )
    parser.add_argument("-p", "--profile", action="store_true", help="采集企业画像")
    args = parser.parse_args()

    if args.profile:
        asyncio.run(test_collect_profile(args.tenant_id, args.store_id))
    elif args.dimensions:
        asyncio.run(test_collect(args.tenant_id, args.store_id, args.dimensions))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
