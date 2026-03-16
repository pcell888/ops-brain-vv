"""5.2.3 指标推送规则表 — 结构与覆盖度。"""

from __future__ import annotations

import pytest

from src.core.indicator_push_rules import INDICATOR_PUSH_RULES
from src.core.calculator import INDICATOR_META


# 文档 5.2.3 要求有规则的动作指标
EXPECTED_RULE_INDICATORS = {
    "lead_conversion_rate",
    "coupon_redemption_rate",
    "repurchase_rate",
    "refund_rate",
    "positive_review_rate",
    "avg_shipping_hours",
    "churn_rate",
}


def test_rule_keys_match_doc():
    """规则表应覆盖文档中列出的全部异常指标。"""
    for code in EXPECTED_RULE_INDICATORS:
        assert code in INDICATOR_PUSH_RULES, f"缺少指标规则: {code}"


def test_rule_has_at_least_one_action():
    """每条规则至少包含 tasks / coupon_campaign / message 之一。"""
    for code, rule in INDICATOR_PUSH_RULES.items():
        has = "tasks" in rule or "coupon_campaign" in rule or "message" in rule
        assert has, f"{code} 规则无任何动作"


def test_tasks_spec_structure():
    """tasks 项应为 list，元素含 task_name, owner_dept。"""
    for code, rule in INDICATOR_PUSH_RULES.items():
        tasks = rule.get("tasks", [])
        for t in tasks:
            assert "task_name" in t and "owner_dept" in t, f"{code} task 缺字段: {t}"


def test_coupon_campaign_structure():
    """coupon_campaign 应含 coupon_name, target_customers 等。"""
    for code, rule in INDICATOR_PUSH_RULES.items():
        camp = rule.get("coupon_campaign")
        if not camp:
            continue
        assert "coupon_name" in camp
        assert "target_customers" in camp


def test_message_structure():
    """message 应含 type, target_segment, title。"""
    for code, rule in INDICATOR_PUSH_RULES.items():
        msg = rule.get("message")
        if not msg:
            continue
        assert "type" in msg and "target_segment" in msg and "title" in msg


def test_rule_indicators_in_meta():
    """规则中的指标 code 均应在 calculator.INDICATOR_META 中存在。"""
    for code in INDICATOR_PUSH_RULES:
        assert code in INDICATOR_META, f"规则指标 {code} 不在 INDICATOR_META"
