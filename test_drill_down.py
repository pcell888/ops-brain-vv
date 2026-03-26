#!/usr/bin/env python3
"""钻取指标自动化测试 — 输入诊断报告ID，自动验证所有可钻取指标。"""

from __future__ import annotations

import asyncio
import json
import sys

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

BASE_URL = "http://127.0.0.1:8000"
API_PREFIX = "/api/v1"

# 所有可钻取指标及其预期字段
DRILLABLE_INDICATORS = {
    # CRM
    "lead_conversion_rate": {
        "name": "线索转化率",
        "dimension": "crm",
        "fields": ["client_record_id", "client_name", "contact_person", "contact_number", "create_time"],
    },
    "response_time_avg": {
        "name": "平均响应时间",
        "dimension": "crm",
        "fields": ["examine_initiate_id", "content", "create_time", "finish_time", "user_name"],
    },
    "follow_up_count": {
        "name": "跟进次数",
        "dimension": "crm",
        "fields": ["examine_initiate_id", "content", "create_time", "user_name"],
    },
    # 营销
    "coupon_redemption_rate": {
        "name": "优惠券核销率",
        "dimension": "marketing",
        "fields": ["account_coupon_id", "coupon_name", "phone", "use_status", "start_time", "end_time", "create_time"],
    },
    "browse_to_order_rate": {
        "name": "浏览转化率",
        "dimension": "marketing",
        "fields": ["account_id", "browse_time", "order_count", "first_order_time"],
    },
    "order_conversion_rate": {
        "name": "订单转化率",
        "dimension": "marketing",
        "fields": ["account_id", "order_sn", "pay_time", "pay_price", "order_status"],
    },
    "seckill_conversion_rate": {
        "name": "秒杀转化率",
        "dimension": "marketing",
        "fields": ["seckill_apply_id", "goods_name", "goods_num", "surplus_goods_num", "start_time", "end_time"],
    },
    # 客户留存
    "repurchase_rate": {
        "name": "复购率",
        "dimension": "retention",
        "fields": ["client_record_id", "client_name", "contact_number", "create_time"],
    },
    "refund_rate": {
        "name": "退款率",
        "dimension": "retention",
        "fields": [
            "store_refund_order_id",
            "store_order_id",
            "order_sn",
            "refund_price",
            "refund_cause",
            "refund_apply_time",
            "refund_success_time",
        ],
    },
    "churn_rate": {
        "name": "流失率",
        "dimension": "retention",
        "fields": ["client_record_id", "client_name", "contact_number", "create_time"],
    },
    "positive_review_rate": {
        "name": "好评率",
        "dimension": "retention",
        "fields": ["store_order_evaluate_id", "store_order_id", "star", "level", "content", "create_time"],
    },
    "avg_customer_lifetime_value": {
        "name": "平均客户生命周期价值",
        "dimension": "retention",
        "fields": ["account_id", "order_count", "total_amount", "last_order_time"],
    },
    # 运营效率
    "service_completion_rate": {
        "name": "服务订单完成率",
        "dimension": "efficiency",
        "fields": ["service_order_id", "order_sn", "order_status", "create_time", "finish_time"],
    },
    "avg_shipping_hours": {
        "name": "平均发货时效",
        "dimension": "efficiency",
        "fields": ["store_order_id", "order_sn", "pay_time", "delivery_time", "shipping_hours"],
    },
}


async def get_report(thread_id: str) -> dict | None:
    """获取诊断报告。"""
    url = f"{BASE_URL}{API_PREFIX}/diagnosis/{thread_id}/report"
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(url)
        if r.status_code != 200:
            return None
        return r.json()


async def drill_down_metric(
    metric_code: str,
    enterprise_id: str,
    page: int = 1,
    page_size: int = 10,
) -> dict | None:
    """调用钻取接口。"""
    url = f"{BASE_URL}{API_PREFIX}/diagnosis/drill-down/{metric_code}"
    params = {
        "enterprise_id": enterprise_id,
        "page": page,
        "page_size": page_size,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(url, params=params)
        if r.status_code != 200:
            return {"error": True, "status_code": r.status_code, "detail": r.text[:200]}
        return r.json()


async def test_drill_down(report_id: str, metrics: list[str] | None = None) -> None:
    """测试钻取指标功能。

    Args:
        report_id: 诊断报告ID (thread_id)
        metrics: 指定要测试的指标列表，如果不提供则测试报告中所有可钻取的异常指标
    """
    console.print(
        Panel(
            f"[bold cyan]钻取指标自动化测试[/bold cyan]\nreport_id: {report_id}",
            border_style="cyan",
        )
    )

    # 1. 获取诊断报告
    console.print("\n[yellow]>>> 获取诊断报告...[/yellow]")
    report = await get_report(report_id)
    if report is None:
        console.print("[red]获取报告失败，请检查 report_id 是否正确[/red]")
        return

    # 提取报告信息
    tenant_id = report.get("tenant_id", "")
    store_id = report.get("store_id", "")
    anomalies = report.get("anomalies") or []
    health_score = report.get("health_score", 0)

    # 从报告中提取 enterprise_id
    enterprise_id = tenant_id or store_id
    if not enterprise_id:
        console.print("[red]报告中缺少 tenant_id[/red]")
        return

    console.print(f"[green]✓[/green] 报告获取成功")
    console.print(f"  健康评分: {health_score}")
    console.print(f"  异常指标数: {len(anomalies)}")
    console.print(f"  enterprise_id: {enterprise_id}")

    # 2. 确定要测试的指标
    anomaly_codes = {a.get("indicator_code") for a in anomalies if a.get("indicator_code")}

    if metrics:
        test_codes = [m for m in metrics if m in DRILLABLE_INDICATORS]
    else:
        # 默认测试报告中所有异常且可钻取的指标
        test_codes = [c for c in anomaly_codes if c in DRILLABLE_INDICATORS]
        # 如果没有异常指标，测试所有可钻取指标
        if not test_codes:
            test_codes = list(DRILLABLE_INDICATORS.keys())

    console.print(f"\n[yellow]>>> 待测试指标: {len(test_codes)} 个[/yellow]")

    # 3. 逐个测试钻取接口
    results: list[dict] = []
    for metric_code in test_codes:
        meta = DRILLABLE_INDICATORS[metric_code]
        is_anomaly = metric_code in anomaly_codes
        tag = "[red]异常[/red]" if is_anomaly else "[dim]正常[/dim]"

        console.print(f"\n  测试 {metric_code} ({meta['name']}) {tag} ...")
        drill_url = f"{BASE_URL}{API_PREFIX}/diagnosis/drill-down/{metric_code}?enterprise_id={enterprise_id}"
        console.print(f"    [dim]URL: {drill_url}[/dim]")

        result = await drill_down_metric(metric_code, enterprise_id)
        if result is None:
            results.append(
                {
                    "metric_code": metric_code,
                    "metric_name": meta["name"],
                    "status": "FAIL",
                    "error": "请求无响应",
                }
            )
            console.print("    [red]✗ 请求无响应[/red]")
            continue

        if result.get("error"):
            results.append(
                {
                    "metric_code": metric_code,
                    "metric_name": meta["name"],
                    "status": "FAIL",
                    "error": f"HTTP {result['status_code']}: {result['detail']}",
                }
            )
            console.print(f"    [red]✗ {result['detail']}[/red]")
            continue

        # 验证响应结构
        validation_errors = []

        # 检查必填字段
        required_fields = [
            "metric_name",
            "metric_code",
            "dimension",
            "time_range",
            "data",
            "total",
            "page",
            "page_size",
            "field_labels",
        ]
        for field in required_fields:
            if field not in result:
                validation_errors.append(f"缺少字段: {field}")

        # 检查 time_range 结构
        time_range = result.get("time_range", {})
        if not time_range.get("start") or not time_range.get("end"):
            validation_errors.append("time_range 结构不完整")

        # 检查 data 是否为列表
        data = result.get("data")
        if not isinstance(data, list):
            validation_errors.append(f"data 应为列表，实际为 {type(data).__name__}")

        # 检查 field_labels
        field_labels = result.get("field_labels", {})
        expected_fields = meta["fields"]
        missing_labels = [f for f in expected_fields if f not in field_labels]
        if missing_labels:
            validation_errors.append(f"field_labels 缺少: {missing_labels}")

        if validation_errors:
            results.append(
                {
                    "metric_code": metric_code,
                    "metric_name": meta["name"],
                    "status": "FAIL",
                    "error": "; ".join(validation_errors),
                    "total": result.get("total", 0),
                }
            )
            console.print(f"    [red]✗ {'; '.join(validation_errors)}[/red]")
        else:
            total = result.get("total", 0)
            data_count = len(result.get("data", []))
            results.append(
                {
                    "metric_code": metric_code,
                    "metric_name": meta["name"],
                    "status": "PASS",
                    "total": total,
                    "data_count": data_count,
                    "has_data": data_count > 0,
                }
            )
            data_status = f"共 {total} 条，本页 {data_count} 条" if total > 0 else "无数据"
            console.print(f"    [green]✓ 验证通过[/green] ({data_status})")

    # 4. 输出测试报告
    _print_test_report(results)


def _print_test_report(results: list[dict]) -> None:
    """打印测试报告。"""
    console.print()
    t = Table(title="钻取指标测试报告", show_header=True, header_style="bold magenta")
    t.add_column("指标代码", style="cyan", width=25)
    t.add_column("指标名称", style="white", width=20)
    t.add_column("状态", width=8)
    t.add_column("详情", style="white")

    pass_count = 0
    fail_count = 0

    for r in results:
        if r["status"] == "PASS":
            status = "[green]PASS[/green]"
            pass_count += 1
            total = r.get("total", 0)
            detail = f"共 {total} 条记录"
            if not r.get("has_data"):
                detail += " (无数据)"
        else:
            status = "[red]FAIL[/red]"
            fail_count += 1
            detail = r.get("error", "未知错误")

        t.add_row(r["metric_code"], r["metric_name"], status, detail)

    console.print(t)

    # 汇总
    total_count = pass_count + fail_count
    pass_rate = (pass_count / total_count * 100) if total_count > 0 else 0

    summary_style = "green" if fail_count == 0 else "red"
    console.print(
        Panel(
            f"[bold {summary_style}]测试完成[/bold {summary_style}]\n"
            f"通过: {pass_count}/{total_count} ({pass_rate:.1f}%)\n"
            f"失败: {fail_count}",
            border_style=summary_style,
        )
    )

    # 输出失败详情
    if fail_count > 0:
        console.print("\n[bold red]失败详情:[/bold red]")
        for r in results:
            if r["status"] == "FAIL":
                console.print(f"  [red]✗[/red] {r['metric_code']} ({r['metric_name']}): {r.get('error', '')}")


async def test_single_metric(metric_code: str, enterprise_id: str, page: int = 1, page_size: int = 10) -> None:
    """测试单个指标的钻取。"""
    if metric_code not in DRILLABLE_INDICATORS:
        console.print(f"[red]不支持的指标: {metric_code}[/red]")
        console.print(f"支持的指标: {', '.join(DRILLABLE_INDICATORS.keys())}")
        return

    meta = DRILLABLE_INDICATORS[metric_code]
    console.print(
        Panel(
            f"[bold cyan]测试单个钻取指标[/bold cyan]\n"
            f"指标: {metric_code} ({meta['name']})\n"
            f"维度: {meta['dimension']}\n"
            f"enterprise_id: {enterprise_id}",
            border_style="cyan",
        )
    )
    drill_url = f"{BASE_URL}{API_PREFIX}/diagnosis/drill-down/{metric_code}?enterprise_id={enterprise_id}"
    console.print(f"  [dim]URL: {drill_url}[/dim]")

    result = await drill_down_metric(metric_code, enterprise_id, page, page_size)

    if result is None:
        console.print("[red]请求失败[/red]")
        return

    if result.get("error"):
        console.print(f"[red]错误: {result['detail']}[/red]")
        return

    # 展示响应详情
    console.print(f"\n[green]✓[/green] 请求成功")
    console.print(f"  metric_code: {result.get('metric_code')}")
    console.print(f"  dimension: {result.get('dimension')}")
    console.print(f"  total: {result.get('total')}")
    console.print(f"  page: {result.get('page')} / page_size: {result.get('page_size')}")

    time_range = result.get("time_range", {})
    console.print(f"  time_range: {time_range.get('start')} ~ {time_range.get('end')}")

    # 展示字段标签
    field_labels = result.get("field_labels", {})
    if field_labels:
        console.print(f"\n  [bold]字段标签:[/bold]")
        for key, label in field_labels.items():
            console.print(f"    {key}: {label}")

    # 展示数据样例
    data = result.get("data", [])
    if data:
        console.print(f"\n  [bold]数据样例 (前3条):[/bold]")
        for i, item in enumerate(data[:3], 1):
            console.print(f"    [{i}] {json.dumps(item, ensure_ascii=False, indent=6)}")
    else:
        console.print("\n  [dim]无数据[/dim]")


async def _test_all_indicators(enterprise_id: str) -> None:
    """测试所有15个可钻取指标，不依赖诊断报告。"""
    console.print(
        Panel(
            f"[bold cyan]钻取所有指标测试[/bold cyan]\nenterprise_id: {enterprise_id}",
            border_style="cyan",
        )
    )

    test_codes = list(DRILLABLE_INDICATORS.keys())
    console.print(f"\n[yellow]>>> 待测试指标: {len(test_codes)} 个[/yellow]")

    results: list[dict] = []
    for metric_code in test_codes:
        meta = DRILLABLE_INDICATORS[metric_code]
        console.print(f"\n  测试 {metric_code} ({meta['name']}) [{meta['dimension']}] ...")
        drill_url = f"{BASE_URL}{API_PREFIX}/diagnosis/drill-down/{metric_code}?enterprise_id={enterprise_id}"
        console.print(f"    [dim]URL: {drill_url}[/dim]")

        result = await drill_down_metric(metric_code, enterprise_id)
        if result is None:
            results.append(
                {
                    "metric_code": metric_code,
                    "metric_name": meta["name"],
                    "status": "FAIL",
                    "error": "请求无响应",
                }
            )
            console.print("    [red]✗ 请求无响应[/red]")
            continue

        if result.get("error"):
            results.append(
                {
                    "metric_code": metric_code,
                    "metric_name": meta["name"],
                    "status": "FAIL",
                    "error": f"HTTP {result['status_code']}: {result['detail']}",
                }
            )
            console.print(f"    [red]✗ {result['detail']}[/red]")
            continue

        # 验证响应结构
        validation_errors = []
        required_fields = [
            "metric_name",
            "metric_code",
            "dimension",
            "time_range",
            "data",
            "total",
            "page",
            "page_size",
            "field_labels",
        ]
        for field in required_fields:
            if field not in result:
                validation_errors.append(f"缺少字段: {field}")

        time_range = result.get("time_range", {})
        if not time_range.get("start") or not time_range.get("end"):
            validation_errors.append("time_range 结构不完整")

        data = result.get("data")
        if not isinstance(data, list):
            validation_errors.append(f"data 应为列表，实际为 {type(data).__name__}")

        field_labels = result.get("field_labels", {})
        expected_fields = meta["fields"]
        missing_labels = [f for f in expected_fields if f not in field_labels]
        if missing_labels:
            validation_errors.append(f"field_labels 缺少: {missing_labels}")

        if validation_errors:
            results.append(
                {
                    "metric_code": metric_code,
                    "metric_name": meta["name"],
                    "status": "FAIL",
                    "error": "; ".join(validation_errors),
                    "total": result.get("total", 0),
                }
            )
            console.print(f"    [red]✗ {'; '.join(validation_errors)}[/red]")
        else:
            total = result.get("total", 0)
            data_count = len(result.get("data", []))
            results.append(
                {
                    "metric_code": metric_code,
                    "metric_name": meta["name"],
                    "status": "PASS",
                    "total": total,
                    "data_count": data_count,
                    "has_data": data_count > 0,
                }
            )
            data_status = f"共 {total} 条，本页 {data_count} 条" if total > 0 else "无数据"
            console.print(f"    [green]✓ 验证通过[/green] ({data_status})")

    _print_test_report(results)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="钻取指标自动化测试工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # test-all: 测试报告中所有指标
    p_all = subparsers.add_parser("test-all", help="测试报告中所有可钻取指标")
    p_all.add_argument("report_id", help="诊断报告ID (thread_id)")
    p_all.add_argument("--metrics", "-m", nargs="+", help="指定要测试的指标代码")

    # test-all-indicators: 测试所有15个可钻取指标
    p_all_ind = subparsers.add_parser("test-all-indicators", help="钻取所有指标 (15个)")
    p_all_ind.add_argument("enterprise_id", help="企业ID")

    # test-one: 测试单个指标
    p_one = subparsers.add_parser("test-one", help="测试单个钻取指标")
    p_one.add_argument("metric_code", help="指标代码")
    p_one.add_argument("enterprise_id", help="企业ID")
    p_one.add_argument("--page", type=int, default=1, help="页码")
    p_one.add_argument("--page-size", type=int, default=10, help="每页数量")

    args = parser.parse_args()

    if args.command == "test-all":
        try:
            asyncio.run(test_drill_down(args.report_id, args.metrics))
        except KeyboardInterrupt:
            console.print("\n[yellow]已取消[/yellow]")
        except Exception as e:
            console.print(f"[red]执行异常: {e}[/red]")

    elif args.command == "test-all-indicators":
        try:
            # 直接测试所有15个指标，不依赖报告
            asyncio.run(_test_all_indicators(args.enterprise_id))
        except KeyboardInterrupt:
            console.print("\n[yellow]已取消[/yellow]")
        except Exception as e:
            console.print(f"[red]执行异常: {e}[/red]")

    elif args.command == "test-one":
        try:
            asyncio.run(test_single_metric(args.metric_code, args.enterprise_id, args.page, args.page_size))
        except KeyboardInterrupt:
            console.print("\n[yellow]已取消[/yellow]")
        except Exception as e:
            console.print(f"[red]执行异常: {e}[/red]")

    else:
        # 交互模式
        console.print(Panel("[bold]钻取指标自动化测试工具[/bold]\n输入诊断报告ID开始测试", border_style="blue"))
        while True:
            console.print()
            report_id = input("请输入诊断报告ID (输入 q 退出): ").strip()
            if report_id.lower() == "q":
                console.print("[dim]再见![/dim]")
                break
            if not report_id:
                console.print("[yellow]报告ID不能为空[/yellow]")
                continue

            console.print("\n选择测试模式:")
            console.print("  1. 测试报告中的异常指标 (默认)")
            console.print("  2. 钻取所有指标 (15个)")
            console.print("  3. 指定指标测试")
            mode = input("请选择 (1/2/3, 默认1): ").strip() or "1"

            metrics = None
            if mode == "3":
                metrics_input = input("请输入指标代码 (逗号分隔): ").strip()
                if metrics_input:
                    metrics = [m.strip() for m in metrics_input.split(",") if m.strip()]
            elif mode == "2":
                # 钻取所有指标
                metrics = list(DRILLABLE_INDICATORS.keys())

            try:
                asyncio.run(test_drill_down(report_id, metrics))
            except KeyboardInterrupt:
                console.print("\n[yellow]已取消[/yellow]")
            except Exception as e:
                console.print(f"[red]执行异常: {e}[/red]")


if __name__ == "__main__":
    main()
