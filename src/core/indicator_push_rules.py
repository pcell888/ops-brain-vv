"""5.2.3 各异常指标对应的具体推送动作 — 规则表，执行节点按此补全推送。

优先从 config/indicator_push_rules.json 加载；文件不存在或解析失败时 fallback 到下方默认值。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "indicator_push_rules.json"

DEFAULT_PUSH_RULES: dict[str, dict] = {
    "lead_conversion_rate": {
        "tasks": [
            {
                "task_name": "线索跟进优化",
                "owner_dept": "销售",
                "timeline": "24小时内首次跟进",
                "implementation_steps": [
                    "导出近7日新线索及负责人清单",
                    "在 CRM 为每条线索配置首次跟进截止时间提醒",
                    "抽查当日首次响应达标率并在周会复盘",
                ],
            },
        ],
    },
    "coupon_redemption_rate": {
        "tasks": [
            {
                "task_name": "优惠券策略调整",
                "owner_dept": "运营",
                "timeline": "3天内",
                "implementation_steps": [
                    "统计近30天券面额、门槛与核销率",
                    "对比行业/历史最优券组并拟定两套试跑方案",
                    "小流量 A/B 上线并设定 3 日复盘指标",
                ],
            },
        ],
        "message": {
            "type": "coupon_expiring_reminder",
            "target_segment": "coupon_expiring_soon",
            "title": "优惠券即将过期提醒",
            "content_tpl": "您有未使用的优惠券即将过期，请尽快使用。",
        },
    },
    "repurchase_rate": {
        "coupon_campaign": {
            "coupon_name": "老客户回馈优惠券",
            "coupon_type": 1,
            "full_price": 0,
            "reduce_price": 30,
            "target_customers": "no_repurchase_90d",
            "start_time": "",
            "end_time": "",
        },
    },
    "refund_rate": {
        "tasks": [
            {
                "task_name": "退款原因分析与商品质量改进",
                "owner_dept": "运营",
                "timeline": "5天内",
                "implementation_steps": [
                    "导出近30天退款单及原因标签分布",
                    "对 TOP SKU 做质量/描述一致性核查",
                    "形成改进清单并对接采购/质检闭环",
                ],
            },
        ],
    },
    "positive_review_rate": {
        "tasks": [
            {
                "task_name": "售后服务优化",
                "owner_dept": "售后",
                "timeline": "3天内",
                "implementation_steps": [
                    "梳理近14天差评与工单闭环时效",
                    "补齐标准话术与补偿审批流程",
                    "设定差评 24h 响应 SLA 并抽查执行",
                ],
            },
            {
                "task_name": "差评客户回访",
                "owner_dept": "客服",
                "timeline": "24小时内",
                "implementation_steps": [
                    "导出待回访差评订单与联系方式",
                    "按话术逐条外呼/在线沟通并记录结果",
                    "将可整改问题转交责任部门并跟进闭环",
                ],
            },
        ],
    },
    "avg_shipping_hours": {
        "tasks": [
            {
                "task_name": "仓储发货流程优化",
                "owner_dept": "仓储",
                "timeline": "5天内",
                "implementation_steps": [
                    "统计各环节停留时长与瓶颈库位",
                    "优化拣货路径或增加波次策略试跑",
                    "设定发货时效 KPI 与每日异常看板",
                ],
            },
        ],
    },
    "churn_rate": {
        "coupon_campaign": {
            "coupon_name": "挽回优惠券",
            "coupon_type": 1,
            "full_price": 0,
            "reduce_price": 20,
            "target_customers": "churn_risk",
            "start_time": "",
            "end_time": "",
        },
        "message": {
            "type": "churn_care",
            "target_segment": "churn_risk",
            "title": "专属关怀",
            "content_tpl": "感谢您一直以来的支持，我们为您准备了专属福利，期待再次为您服务。",
        },
    },
    "seckill_conversion_rate": {
        "tasks": [
            {
                "task_name": "秒杀活动选品与定价优化",
                "owner_dept": "运营",
                "timeline": "3天内",
                "implementation_steps": [
                    "复盘近3场秒杀的曝光-加购-转化漏斗",
                    "圈选高转化 SKU 与目标价带",
                    "更新排期与库存锁量并小流量试跑",
                ],
            },
        ],
        "message": {
            "type": "ai_targeted",
            "target_segment": "low_conversion",
            "title": "限时秒杀提醒",
            "content_tpl": "精选好物限时秒杀中，数量有限，快来抢购！",
        },
    },
}


def load_push_rules() -> dict[str, dict]:
    """从 JSON 配置文件加载推送规则，失败时 fallback 到代码默认值。"""
    try:
        if _CONFIG_PATH.exists():
            data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data:
                logger.info("Loaded push rules from %s (%d indicators)", _CONFIG_PATH, len(data))
                return data
    except Exception:
        logger.warning("Failed to load %s, using default rules", _CONFIG_PATH, exc_info=True)
    return DEFAULT_PUSH_RULES.copy()


INDICATOR_PUSH_RULES: dict[str, dict] = load_push_rules()


def enrich_task_spec_with_default_steps(spec: dict) -> dict:
    """JSON 规则可能省略 implementation_steps，用代码默认表补齐。"""
    ind = spec.get("indicator_code")
    if not ind:
        return spec
    impl = spec.get("implementation_steps")
    if isinstance(impl, list) and len(impl) >= 2:
        return spec
    default = DEFAULT_PUSH_RULES.get(ind) or {}
    for dt in default.get("tasks") or []:
        if dt.get("task_name") == spec.get("task_name"):
            merged = dict(dt)
            merged.update(spec)
            return merged
    return spec


def collect_mandatory_task_specs(anomalies: list[object]) -> list[dict]:
    """按异常指标去重后，收集 5.2.3 规则中 tasks[] 条目（含 indicator_code），供方案生成保底。"""
    seen_ind: set[str] = set()
    out: list[dict] = []
    for a in anomalies:
        if not isinstance(a, dict):
            continue
        ind = a.get("indicator_code")
        if not ind or not isinstance(ind, str) or ind in seen_ind:
            continue
        seen_ind.add(ind)
        rule = INDICATOR_PUSH_RULES.get(ind)
        if not rule:
            continue
        for t in rule.get("tasks") or []:
            if not isinstance(t, dict):
                continue
            item = {"indicator_code": ind, **t}
            out.append(enrich_task_spec_with_default_steps(item))
    return out


def format_indicator_rules_for_prompt(anomalies: list[object]) -> str:
    """将当前异常涉及的 5.2.3 规则片段格式化为方案生成 Prompt（按 indicator_code 去重）。"""
    if not anomalies:
        return "（无异常指标。）"
    seen: set[str] = set()
    parts: list[str] = []
    for a in anomalies:
        if not isinstance(a, dict):
            continue
        ind = a.get("indicator_code")
        if not ind or not isinstance(ind, str) or ind in seen:
            continue
        seen.add(ind)
        rule = INDICATOR_PUSH_RULES.get(ind)
        if not rule:
            continue
        parts.append(json.dumps({ind: rule}, ensure_ascii=False, indent=2))
    if not parts:
        return (
            "（当前异常指标在 5.2.3 规则表中无条目；请依据异常与根因设计可执行步骤，"
            "必要时在 auto_actions 中配置优惠券等自动化动作。）"
        )
    return "\n\n".join(parts)
