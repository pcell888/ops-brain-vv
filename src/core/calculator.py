"""指标计算引擎 — 规则化评分与异常检测。"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from .config import CN_TZ

INDICATOR_META: dict[str, dict] = {
    # CRM维度
    "lead_conversion_rate": {"name": "线索转化率", "dimension": "crm", "direction": "higher_is_better", "unit": "%", "drillable": True, "drill_desc": "低转化线索客户列表"},
    "response_time_avg": {"name": "平均响应时间", "dimension": "crm", "direction": "lower_is_better", "unit": "小时", "drillable": True, "drill_desc": "响应慢的协同记录"},
    "follow_up_count": {"name": "跟进次数", "dimension": "crm", "direction": "higher_is_better", "unit": "次", "drillable": True, "drill_desc": "跟进记录明细"},
    # 营销维度
    "coupon_redemption_rate": {"name": "优惠券核销率", "dimension": "marketing", "direction": "higher_is_better", "unit": "%", "drillable": True, "drill_desc": "未核销优惠券列表"},
    "browse_to_order_rate": {"name": "浏览转化率", "dimension": "marketing", "direction": "higher_is_better", "unit": "%", "drillable": True, "drill_desc": "浏览-下单漏斗明细"},
    "order_conversion_rate": {"name": "订单转化率", "dimension": "marketing", "direction": "higher_is_better", "unit": "%", "drillable": True, "drill_desc": "订单转化漏斗明细"},
    "seckill_conversion_rate": {"name": "秒杀转化率", "dimension": "marketing", "direction": "higher_is_better", "unit": "%", "drillable": True, "drill_desc": "秒杀商品销售明细"},
    # 客户留存
    "repurchase_rate": {"name": "复购率", "dimension": "retention", "direction": "higher_is_better", "unit": "%", "drillable": True, "drill_desc": "未复购客户列表"},
    "refund_rate": {"name": "退款率", "dimension": "retention", "direction": "lower_is_better", "unit": "%", "drillable": True, "drill_desc": "退款订单列表"},
    "churn_rate": {"name": "流失率", "dimension": "retention", "direction": "lower_is_better", "unit": "%", "drillable": True, "drill_desc": "流失风险客户列表"},
    "positive_review_rate": {"name": "好评率", "dimension": "retention", "direction": "higher_is_better", "unit": "%", "drillable": True, "drill_desc": "差评订单列表"},
    "avg_customer_lifetime_value": {"name": "平均客户生命周期价值", "dimension": "retention", "direction": "higher_is_better", "unit": "元", "drillable": True, "drill_desc": "客户LTV明细"},
    # 运营效率
    "service_completion_rate": {"name": "服务订单完成率", "dimension": "efficiency", "direction": "higher_is_better", "unit": "%", "drillable": True, "drill_desc": "未完成服务订单列表"},
    "avg_shipping_hours": {"name": "平均发货时效", "dimension": "efficiency", "direction": "lower_is_better", "unit": "小时", "drillable": True, "drill_desc": "发货时效明细"},
}

# 各指标钻取 items 中单条记录的约定字段（企业 API 返回 list/items 时应尽量符合）
DRILL_ITEM_FIELDS: dict[str, list[str]] = {
    # CRM — 客户记录列表
    "lead_conversion_rate": ["client_record_id", "client_name", "contact_person", "contact_number", "create_time"],
    "repurchase_rate": ["client_record_id", "client_name", "contact_number", "create_time"],
    "churn_rate": ["client_record_id", "client_name", "contact_number", "create_time"],
    # CRM — 跟进/审批明细
    "response_time_avg": ["examine_initiate_id", "content", "create_time", "finish_time", "user_name"],
    "follow_up_count": ["examine_initiate_id", "content", "create_time", "user_name"],
    # 营销
    "coupon_redemption_rate": ["account_coupon_id", "coupon_name", "phone", "use_status", "start_time", "end_time", "create_time"],
    "browse_to_order_rate": ["account_id", "browse_time", "order_count", "first_order_time"],
    "order_conversion_rate": ["account_id", "order_sn", "pay_time", "pay_price", "order_status"],
    "seckill_conversion_rate": ["seckill_apply_id", "goods_name", "goods_num", "surplus_goods_num", "start_time", "end_time"],
    # 留存
    "refund_rate": ["store_refund_order_id", "store_order_id", "order_sn", "refund_price", "refund_cause", "refund_apply_time", "refund_success_time"],
    "positive_review_rate": ["store_order_evaluate_id", "store_order_id", "star", "level", "content", "create_time"],
    "avg_customer_lifetime_value": ["account_id", "order_count", "total_amount", "last_order_time"],
    # 效率
    "service_completion_rate": ["service_order_id", "order_sn", "order_status", "create_time", "finish_time"],
    "avg_shipping_hours": ["store_order_id", "order_sn", "pay_time", "delivery_time", "shipping_hours"],
}

# 钻取字段 key -> 中文标签，供前端表头/展示用
DRILL_FIELD_LABELS: dict[str, str] = {
    "client_record_id": "客户ID",
    "client_name": "客户名称",
    "contact_person": "联系人",
    "contact_number": "联系电话",
    "create_time": "创建时间",
    "examine_initiate_id": "审批/跟进ID",
    "content": "内容",
    "finish_time": "完成时间",
    "user_name": "发起人",
    "account_coupon_id": "用户优惠券ID",
    "coupon_name": "优惠券名称",
    "phone": "手机号",
    "use_status": "使用状态",
    "start_time": "开始时间",
    "end_time": "结束时间",
    "account_id": "用户ID",
    "browse_time": "浏览时间",
    "order_count": "订单数",
    "first_order_time": "首单时间",
    "order_sn": "订单号",
    "pay_time": "支付时间",
    "pay_price": "实付金额",
    "order_status": "订单状态",
    "seckill_apply_id": "秒杀申请ID",
    "goods_name": "商品名称",
    "goods_num": "商品数量",
    "surplus_goods_num": "剩余数量",
    "store_refund_order_id": "退款单ID",
    "store_order_id": "订单ID",
    "refund_price": "退款金额",
    "refund_cause": "退款原因",
    "refund_apply_time": "申请退款时间",
    "refund_success_time": "退款成功时间",
    "store_order_evaluate_id": "评价ID",
    "star": "星级",
    "level": "评价等级",
    "total_amount": "累计金额",
    "last_order_time": "最近订单时间",
    "service_order_id": "服务订单ID",
    "delivery_time": "发货时间",
    "shipping_hours": "发货时效(小时)",
}


def camel_to_snake(name: str) -> str:
    """将 camelCase / PascalCase 转为 snake_case（与 Java/JavaScript 常见 JSON 字段兼容）。"""
    if not name:
        return name
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    return s2.lower()


def filter_drill_row_by_allowed_fields(row: Any, allowed: list[str] | None) -> dict:
    """按 DRILL_ITEM_FIELDS 白名单保留字段；键名可与白名单不一致（camelCase），输出统一为 snake_case。"""
    if not isinstance(row, dict):
        return {}
    if not allowed:
        return dict(row)
    allowed_set = frozenset(allowed)
    out: dict = {}
    for k, v in row.items():
        key = str(k)
        if key in allowed_set:
            canon = key
        else:
            canon = camel_to_snake(key)
            if canon not in allowed_set:
                continue
        out[canon] = v
    return out


NOT_APPLICABLE_MAP: dict[str, set[str]] = {
    "service": {"avg_shipping_hours", "seckill_conversion_rate", "browse_to_order_rate"},
    "mall":    {"service_completion_rate"},
}

ALL_DIMENSIONS = ["crm", "marketing", "retention", "efficiency"]

DEFAULT_DIMENSION_WEIGHTS: dict[str, float] = {
    "crm": 0.25,
    "marketing": 0.30,
    "retention": 0.30,
    "efficiency": 0.15,
}

ANOMALY_THRESHOLD_PCT = 15.0  # 偏离行业均值超过此百分比视为异常
DEFAULT_BENCHMARKS: dict[str, dict[str, float]] = {
    "lead_conversion_rate": {"avg_value": 5.2, "excellent_value": 8.5},
    "response_time_avg": {"avg_value": 6.0, "excellent_value": 2.0},
    "follow_up_count": {"avg_value": 800.0, "excellent_value": 1500.0},
    "coupon_redemption_rate": {"avg_value": 32.0, "excellent_value": 50.0},
    "browse_to_order_rate": {"avg_value": 5.8, "excellent_value": 10.0},
    "order_conversion_rate": {"avg_value": 85.0, "excellent_value": 95.0},
    "seckill_conversion_rate": {"avg_value": 30.0, "excellent_value": 55.0},
    "repurchase_rate": {"avg_value": 35.0, "excellent_value": 55.0},
    "refund_rate": {"avg_value": 5.0, "excellent_value": 2.0},
    "churn_rate": {"avg_value": 18.0, "excellent_value": 8.0},
    "positive_review_rate": {"avg_value": 82.0, "excellent_value": 95.0},
    "avg_customer_lifetime_value": {"avg_value": 1200.0, "excellent_value": 2500.0},
    "service_completion_rate": {"avg_value": 80.0, "excellent_value": 95.0},
    "avg_shipping_hours": {"avg_value": 18.0, "excellent_value": 6.0},
}


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
) -> tuple[float, list[dict], list[dict]]:
    """
    计算单个维度的健康度得分(0-100)、识别异常指标、返回各指标得分。

    评分逻辑:
    - 每个指标与行业基准均值对比，计算偏差百分比
    - higher_is_better: 高于均值加分，低于均值扣分
    - lower_is_better: 低于均值加分，高于均值扣分
    - 基础分60，上限100，下限0

    返回: (维度得分, 异常列表, 各指标得分列表)
    """
    raw_indicators = indicators.get("indicators", indicators)
    benchmark_data = benchmarks.get("benchmarks", benchmarks)

    dim_indicators = {
        code: meta for code, meta in INDICATOR_META.items()
        if meta["dimension"] == dimension and (active_indicators is None or code in active_indicators)
    }

    if not dim_indicators:
        return 60.0, [], []

    total_score = 0.0
    count = 0
    anomalies: list[dict] = []
    indicator_scores: list[dict] = []

    for code, meta in dim_indicators.items():
        ind_data = raw_indicators.get(code)
        if ind_data is None:
            continue
        if isinstance(ind_data, dict) and ind_data.get("not_applicable"):
            continue

        current_value = ind_data["value"] if isinstance(ind_data, dict) else ind_data
        bench = benchmark_data.get(code)
        if isinstance(bench, dict) and (bench.get("avg_value") in (None, 0)):
            bench = DEFAULT_BENCHMARKS.get(code, bench)
        elif bench in (None, 0):
            bench = DEFAULT_BENCHMARKS.get(code)
        if bench is None:
            total_score += 60
            count += 1
            indicator_scores.append({
                "indicator_code": code,
                "indicator_name": meta["name"],
                "score": 60.0,
                "current_value": round(current_value, 2),
                "unit": meta["unit"],
                "deviation_pct": None,
            })
            continue

        avg_val = bench["avg_value"] if isinstance(bench, dict) else bench
        excellent_val = bench.get("excellent_value", avg_val * 1.3) if isinstance(bench, dict) else avg_val * 1.3

        if avg_val == 0:
            total_score += 60
            count += 1
            indicator_scores.append({
                "indicator_code": code,
                "indicator_name": meta["name"],
                "score": 60.0,
                "current_value": round(current_value, 2),
                "unit": meta["unit"],
                "deviation_pct": None,
            })
            continue

        if meta["direction"] == "higher_is_better":
            deviation_pct = (current_value - avg_val) / avg_val * 100
        else:
            deviation_pct = (avg_val - current_value) / avg_val * 100

        indicator_score = 60 + deviation_pct * 0.4
        indicator_score = max(0, min(100, round(indicator_score, 2)))
        total_score += indicator_score
        count += 1

        indicator_scores.append({
            "indicator_code": code,
            "indicator_name": meta["name"],
            "score": indicator_score,
            "current_value": round(current_value, 2),
            "unit": meta["unit"],
            "deviation_pct": round(deviation_pct, 2),
        })

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
    return round(final_score, 2), anomalies, indicator_scores


def extract_indicator_codes(*indicator_dicts: dict) -> list[str]:
    """从多个维度的指标数据中提取所有指标代码。"""
    codes: list[str] = []
    for d in indicator_dicts:
        if d and isinstance(d, dict):
            raw = d.get("indicators", d)
            codes.extend(raw.keys())
    return [c for c in codes if c in INDICATOR_META]


def calculate_dimension_benchmarks_scores(
    dimension_benchmarks: dict[str, list[dict]],
) -> dict[str, float]:
    """按维度计算行业基准得分。"""
    dimension_benchmarks_scores: dict[str, float] = {}
    for dim in ALL_DIMENSIONS:
        items = dimension_benchmarks.get(dim) if isinstance(dimension_benchmarks, dict) else None
        if not isinstance(items, list) or not items:
            dimension_benchmarks_scores[dim] = 60.0
            continue

        indicator_base_scores: list[float] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            code = str(item.get("indicator_code") or "")
            meta = INDICATOR_META.get(code, {})
            direction = meta.get("direction", "higher_is_better")
            avg_val = item.get("avg_value")
            excellent_val = item.get("excellent_value")
            try:
                avg_num = float(avg_val)
                excellent_num = float(excellent_val)
                if avg_num <= 0 or excellent_num <= 0:
                    raise ValueError("invalid benchmark values")
                if direction == "lower_is_better":
                    score = excellent_num / avg_num * 100
                else:
                    score = avg_num / excellent_num * 100
                indicator_base_scores.append(max(0.0, min(100.0, round(score, 2))))
            except (TypeError, ValueError):
                indicator_base_scores.append(60.0)

        if not indicator_base_scores:
            dimension_benchmarks_scores[dim] = 60.0
        else:
            dimension_benchmarks_scores[dim] = round(sum(indicator_base_scores) / len(indicator_base_scores), 2)
    return dimension_benchmarks_scores


def normalize_llm_root_causes(root_causes: list[dict], anomalies: list[dict]) -> list[dict]:
    """将 LLM 返回的根因对齐到 anomalies 的 indicator_code（支持中文名、indicator_code 等别名）。"""
    if not anomalies:
        return list(root_causes or [])
    code_set = {a["indicator_code"] for a in anomalies}
    codes_order = [a["indicator_code"] for a in anomalies]
    name_to_code = {INDICATOR_META[c]["name"]: c for c in code_set if c in INDICATOR_META}
    by_code: dict[str, dict] = {}
    for rc in root_causes or []:
        if not isinstance(rc, dict):
            continue
        raw = (
            rc.get("anomaly_indicator")
            or rc.get("indicator_code")
            or rc.get("metric_code")
            or rc.get("code")
        )
        if raw is None:
            continue
        s = str(raw).strip()
        target: str | None = None
        if s in code_set:
            target = s
        elif s in name_to_code:
            target = name_to_code[s]
        else:
            for code in codes_order:
                meta = INDICATOR_META.get(code, {})
                name = meta.get("name", "")
                if name and (name == s or s in name or name in s):
                    target = code
                    break
        if not target:
            continue
        fixed = dict(rc)
        fixed["anomaly_indicator"] = target
        by_code[target] = fixed
    return list(by_code.values())


def build_diagnosis_report(
    store_profile: dict,
    health_score: float,
    dimension_scores: dict,
    dimension_indicator_scores: dict[str, list[dict]],
    dimension_benchmarks: dict[str, list[dict]],
    anomalies: list[dict],
    root_causes: list[dict],
) -> dict:
    """组装完整的诊断报告数据结构。包含：综合健康度、各维度得分、各维度指标得分、各维度行业基准、异常指标（含根因分析）。"""
    from copy import deepcopy

    severity_order = {"high": 0, "medium": 1, "low": 2}
    sorted_anomalies = sorted(anomalies, key=lambda a: severity_order.get(a.get("severity", "low"), 2))
    root_by_indicator = {rc.get("anomaly_indicator"): rc for rc in (root_causes or []) if rc.get("anomaly_indicator")}
    anomalies_with_root = []
    for a in sorted_anomalies:
        a_copy = deepcopy(a)
        rc = root_by_indicator.get(a.get("indicator_code"))
        if rc:
            rec_raw = rc.get("recommendations")
            rec_list: list[str] = []
            if isinstance(rec_raw, list):
                rec_list = [x.strip() for x in rec_raw if isinstance(x, str) and x.strip()]
            elif isinstance(rec_raw, str) and rec_raw.strip():
                rec_list = [rec_raw.strip()]
            a_copy["root_cause"] = {
                "cause": rc.get("cause", ""),
                "evidence": rc.get("evidence", ""),
                "confidence": rc.get("confidence", 0),
                "recommendations": rec_list,
            }
        else:
            a_copy["root_cause"] = None
        anomalies_with_root.append(a_copy)

    summary_parts: list[str] = [
        f"企业「{store_profile.get('store_name', '')}」运营健康度评分为 {health_score:.1f} 分。"
    ]
    if anomalies_with_root:
        summary_parts.append(f"共发现 {len(anomalies_with_root)} 项异常指标，")
        high_count = sum(1 for a in anomalies_with_root if a.get("severity") == "high")
        if high_count:
            summary_parts.append(f"其中 {high_count} 项为高风险。")
        top = anomalies_with_root[0]
        summary_parts.append(f"最突出的问题是：{top['description']}。")
    else:
        summary_parts.append("各项指标表现正常，暂未发现异常。")

    dimension_benchmarks_scores = calculate_dimension_benchmarks_scores(dimension_benchmarks)

    return {
        "tenant_id": store_profile.get("tenant_id", ""),
        "store_id": store_profile.get("store_id", ""),
        "generated_at": datetime.now(CN_TZ).isoformat(),
        "health_score": health_score,
        "dimension_scores": dimension_scores,
        "dimension_indicator_scores": dimension_indicator_scores,
        "dimension_benchmarks": dimension_benchmarks,
        "dimension_benchmarks_scores": dimension_benchmarks_scores,
        "anomalies": anomalies_with_root,
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
