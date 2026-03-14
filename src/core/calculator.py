"""指标计算引擎 — 规则化评分与异常检测。"""

from __future__ import annotations

INDICATOR_META: dict[str, dict] = {
    # CRM维度
    "lead_conversion_rate": {"name": "线索转化率", "dimension": "crm", "direction": "higher_is_better", "unit": "%", "drillable": True, "drill_desc": "低转化线索客户列表"},
    "response_time_avg": {"name": "平均响应时间", "dimension": "crm", "direction": "lower_is_better", "unit": "小时", "drillable": True, "drill_desc": "响应慢的协同记录"},
    "follow_up_count": {"name": "跟进次数", "dimension": "crm", "direction": "higher_is_better", "unit": "次", "drillable": True, "drill_desc": "跟进记录明细"},
    # 营销维度
    "coupon_redemption_rate": {"name": "优惠券核销率", "dimension": "marketing", "direction": "higher_is_better", "unit": "%", "drillable": True, "drill_desc": "未核销优惠券列表"},
    "browse_to_order_rate": {"name": "浏览转化率", "dimension": "marketing", "direction": "higher_is_better", "unit": "%", "drillable": True, "drill_desc": "浏览-下单漏斗明细"},
    "order_conversion_rate": {"name": "订单转化率", "dimension": "marketing", "direction": "higher_is_better", "unit": "%", "drillable": True, "drill_desc": "订单转化漏斗明细"},
    "customer_acquisition_cost": {"name": "获客成本", "dimension": "marketing", "direction": "lower_is_better", "unit": "元", "drillable": True, "drill_desc": "高获客成本活动列表"},
    # 客户留存
    "repurchase_rate": {"name": "复购率", "dimension": "retention", "direction": "higher_is_better", "unit": "%", "drillable": True, "drill_desc": "未复购客户列表"},
    "refund_rate": {"name": "退款率", "dimension": "retention", "direction": "lower_is_better", "unit": "%", "drillable": True, "drill_desc": "退款订单列表"},
    "churn_rate": {"name": "流失率", "dimension": "retention", "direction": "lower_is_better", "unit": "%", "drillable": True, "drill_desc": "流失风险客户列表"},
    "positive_review_rate": {"name": "好评率", "dimension": "retention", "direction": "higher_is_better", "unit": "%", "drillable": True, "drill_desc": "差评订单列表"},
    "avg_customer_lifetime_value": {"name": "平均客户生命周期价值", "dimension": "retention", "direction": "higher_is_better", "unit": "元", "drillable": True, "drill_desc": "客户LTV明细"},
    # 运营效率
    "service_completion_rate": {"name": "服务订单完成率", "dimension": "efficiency", "direction": "higher_is_better", "unit": "%", "drillable": True, "drill_desc": "未完成服务订单列表"},
    "avg_shipping_hours": {"name": "平均发货时效", "dimension": "efficiency", "direction": "lower_is_better", "unit": "小时", "drillable": True, "drill_desc": "发货时效明细"},
    "task_on_time_rate": {"name": "任务按时完成率", "dimension": "efficiency", "direction": "higher_is_better", "unit": "%", "drillable": True, "drill_desc": "逾期任务列表"},
}

ALL_DIMENSIONS = ["crm", "marketing", "retention", "efficiency"]

DEFAULT_DIMENSION_WEIGHTS: dict[str, float] = {
    "crm": 0.25,
    "marketing": 0.30,
    "retention": 0.25,
    "efficiency": 0.20,
}

ANOMALY_THRESHOLD_PCT = 15.0  # 偏离行业均值超过此百分比视为异常


def list_available_indicators(
    dimensions: list[str] | None = None,
) -> dict[str, list[dict]]:
    """返回可选指标清单，按维度分组。"""
    result: dict[str, list[dict]] = {}
    for code, meta in INDICATOR_META.items():
        dim = meta["dimension"]
        if dimensions and dim not in dimensions:
            continue
        result.setdefault(dim, []).append({"code": code, **meta})
    return result


def resolve_active_indicators(
    selected_dimensions: list[str] | None = None,
    selected_indicators: list[str] | None = None,
) -> tuple[set[str], set[str]]:
    """
    根据用户选配，返回 (active_dimensions, active_indicator_codes)。
    - 都为空 → 全量
    - 仅 selected_dimensions → 该维度下全部指标
    - 仅 selected_indicators → 自动推导所属维度
    - 同时提供 → 取交集
    """
    if not selected_dimensions and not selected_indicators:
        return set(ALL_DIMENSIONS), set(INDICATOR_META.keys())

    if selected_indicators:
        ind_set = {c for c in selected_indicators if c in INDICATOR_META}
        dim_from_inds = {INDICATOR_META[c]["dimension"] for c in ind_set}
    else:
        ind_set = None
        dim_from_inds = None

    if selected_dimensions:
        dim_set = {d for d in selected_dimensions if d in ALL_DIMENSIONS}
    else:
        dim_set = dim_from_inds or set(ALL_DIMENSIONS)

    if ind_set is None:
        ind_set = {c for c, m in INDICATOR_META.items() if m["dimension"] in dim_set}
    else:
        ind_set = {c for c in ind_set if INDICATOR_META[c]["dimension"] in dim_set}

    return dim_set, ind_set


def rebalance_weights(active_dimensions: set[str]) -> dict[str, float]:
    """根据实际参与维度重新分配权重，总和为 1。"""
    if not active_dimensions:
        return DEFAULT_DIMENSION_WEIGHTS.copy()
    raw = {d: DEFAULT_DIMENSION_WEIGHTS[d] for d in active_dimensions if d in DEFAULT_DIMENSION_WEIGHTS}
    total = sum(raw.values()) or 1.0
    return {d: round(w / total, 4) for d, w in raw.items()}


def calculate_dimension_score(
    indicators: dict,
    benchmarks: dict,
    dimension: str,
    active_indicators: set[str] | None = None,
) -> tuple[float, list[dict]]:
    """
    计算单个维度的健康度得分(0-100)并识别异常指标。

    评分逻辑:
    - 每个指标与行业基准均值对比，计算偏差百分比
    - higher_is_better: 高于均值加分，低于均值扣分
    - lower_is_better: 低于均值加分，高于均值扣分
    - 基础分60，上限100，下限0
    """
    raw_indicators = indicators.get("indicators", indicators)
    benchmark_data = benchmarks.get("benchmarks", benchmarks)

    dim_indicators = {
        code: meta for code, meta in INDICATOR_META.items()
        if meta["dimension"] == dimension and (active_indicators is None or code in active_indicators)
    }

    if not dim_indicators:
        return 60.0, []

    total_score = 0.0
    count = 0
    anomalies: list[dict] = []

    for code, meta in dim_indicators.items():
        ind_data = raw_indicators.get(code)
        if ind_data is None:
            continue

        current_value = ind_data["value"] if isinstance(ind_data, dict) else ind_data
        bench = benchmark_data.get(code)
        if bench is None:
            total_score += 60
            count += 1
            continue

        avg_val = bench["avg_value"] if isinstance(bench, dict) else bench
        excellent_val = bench.get("excellent_value", avg_val * 1.3) if isinstance(bench, dict) else avg_val * 1.3

        if avg_val == 0:
            total_score += 60
            count += 1
            continue

        if meta["direction"] == "higher_is_better":
            deviation_pct = (current_value - avg_val) / avg_val * 100
        else:
            deviation_pct = (avg_val - current_value) / avg_val * 100

        indicator_score = 60 + deviation_pct * 0.4
        indicator_score = max(0, min(100, indicator_score))
        total_score += indicator_score
        count += 1

        if deviation_pct < -ANOMALY_THRESHOLD_PCT:
            severity = "high" if deviation_pct < -30 else ("medium" if deviation_pct < -20 else "low")
            anomalies.append({
                "indicator_code": code,
                "indicator_name": meta["name"],
                "dimension": dimension,
                "current_value": round(current_value, 2),
                "benchmark_avg": round(avg_val, 2),
                "benchmark_excellent": round(excellent_val, 2),
                "deviation_pct": round(deviation_pct, 2),
                "severity": severity,
                "description": f"{meta['name']}为{current_value}{meta['unit']}，低于行业均值{avg_val}{meta['unit']} ({abs(deviation_pct):.1f}%)",
            })

    final_score = total_score / count if count > 0 else 60.0
    return round(final_score, 2), anomalies


def extract_indicator_codes(*indicator_dicts: dict) -> list[str]:
    """从多个维度的指标数据中提取所有指标代码。"""
    codes: list[str] = []
    for d in indicator_dicts:
        if d and isinstance(d, dict):
            raw = d.get("indicators", d)
            codes.extend(raw.keys())
    return [c for c in codes if c in INDICATOR_META]


def build_diagnosis_report(
    store_profile: dict,
    health_score: float,
    dimension_scores: dict,
    anomalies: list[dict],
    root_causes: list[dict],
) -> dict:
    """组装完整的诊断报告数据结构。"""
    from datetime import datetime

    severity_order = {"high": 0, "medium": 1, "low": 2}
    sorted_anomalies = sorted(anomalies, key=lambda a: severity_order.get(a.get("severity", "low"), 2))

    summary_parts: list[str] = [
        f"企业「{store_profile.get('store_name', '')}」运营健康度评分为 {health_score:.1f} 分。"
    ]
    if sorted_anomalies:
        summary_parts.append(f"共发现 {len(sorted_anomalies)} 项异常指标，")
        high_count = sum(1 for a in sorted_anomalies if a.get("severity") == "high")
        if high_count:
            summary_parts.append(f"其中 {high_count} 项为高风险。")
        top = sorted_anomalies[0]
        summary_parts.append(f"最突出的问题是：{top['description']}。")
    else:
        summary_parts.append("各项指标表现正常，暂未发现异常。")

    return {
        "tenant_id": store_profile.get("tenant_id", ""),
        "store_id": store_profile.get("store_id", ""),
        "generated_at": datetime.now().isoformat(),
        "health_score": health_score,
        "dimension_scores": dimension_scores,
        "anomalies": sorted_anomalies,
        "root_causes": root_causes,
        "summary": "".join(summary_parts),
    }


def calculate_effect_changes(
    before: dict[str, dict],
    after: dict[str, dict],
    target_indicators: list[str],
) -> dict:
    """对比执行前后的指标变化。"""
    changes: list[dict] = []

    for dim_name, before_dim in before.items():
        after_dim = after.get(dim_name, {})
        before_inds = before_dim.get("indicators", before_dim) if isinstance(before_dim, dict) else {}
        after_inds = after_dim.get("indicators", after_dim) if isinstance(after_dim, dict) else {}

        for code in target_indicators:
            b_val = before_inds.get(code)
            a_val = after_inds.get(code)
            if b_val is None or a_val is None:
                continue

            bv = b_val["value"] if isinstance(b_val, dict) else b_val
            av = a_val["value"] if isinstance(a_val, dict) else a_val

            if bv == 0:
                change_pct = 100.0 if av > 0 else 0.0
            else:
                change_pct = (av - bv) / abs(bv) * 100

            meta = INDICATOR_META.get(code, {})
            improved = change_pct > 0 if meta.get("direction") == "higher_is_better" else change_pct < 0

            changes.append({
                "indicator_code": code,
                "before_value": round(bv, 2),
                "after_value": round(av, 2),
                "change_pct": round(change_pct, 2),
                "improved": improved,
            })

    improved_count = sum(1 for c in changes if c["improved"])
    achievement = (improved_count / len(changes) * 100) if changes else 0

    return {
        "indicator_changes": changes,
        "improved_count": improved_count,
        "total_tracked": len(changes),
        "overall_achievement_rate": round(achievement, 1),
    }
