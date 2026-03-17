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
            {"task_name": "线索跟进优化", "owner_dept": "销售", "timeline": "24小时内首次跟进"},
        ],
    },
    "coupon_redemption_rate": {
        "tasks": [
            {"task_name": "优惠券策略调整", "owner_dept": "运营", "timeline": "3天内"},
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
            {"task_name": "退款原因分析与商品质量改进", "owner_dept": "运营", "timeline": "5天内"},
        ],
    },
    "positive_review_rate": {
        "tasks": [
            {"task_name": "售后服务优化", "owner_dept": "售后", "timeline": "3天内"},
            {"task_name": "差评客户回访", "owner_dept": "客服", "timeline": "24小时内"},
        ],
    },
    "avg_shipping_hours": {
        "tasks": [
            {"task_name": "仓储发货流程优化", "owner_dept": "仓储", "timeline": "5天内"},
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
            {"task_name": "秒杀活动选品与定价优化", "owner_dept": "运营", "timeline": "3天内"},
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
