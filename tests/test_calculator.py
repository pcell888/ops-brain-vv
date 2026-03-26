"""指标计算引擎 — 指标解析与权重。"""

from __future__ import annotations

import pytest

from src.core.calculator import (
    ALL_DIMENSIONS,
    DRILL_ITEM_FIELDS,
    INDICATOR_META,
    camel_to_snake,
    filter_drill_row_by_allowed_fields,
    list_available_indicators,
    rebalance_weights,
    resolve_active_indicators,
)


def test_list_available_indicators_all():
    out = list_available_indicators()
    assert set(out.keys()) == set(ALL_DIMENSIONS)
    for dim, items in out.items():
        assert isinstance(items, list)
        for it in items:
            assert "code" in it and "name" in it and "dimension" in it


def test_list_available_indicators_filter_dim():
    out = list_available_indicators(dimensions=["crm", "retention"])
    assert set(out.keys()) == {"crm", "retention"}
    for it in out["crm"]:
        assert it["dimension"] == "crm"


def test_resolve_active_indicators_empty():
    dims, inds = resolve_active_indicators()
    assert dims == set(ALL_DIMENSIONS)
    assert inds == set(INDICATOR_META.keys())


def test_resolve_active_indicators_by_dimensions():
    dims, inds = resolve_active_indicators(selected_dimensions=["crm"])
    assert dims == {"crm"}
    assert all(INDICATOR_META[c]["dimension"] == "crm" for c in inds)


def test_resolve_active_indicators_by_indicators():
    dims, inds = resolve_active_indicators(selected_indicators=["lead_conversion_rate", "refund_rate"])
    assert "lead_conversion_rate" in inds
    assert "refund_rate" in inds
    assert dims.issuperset({"crm", "retention"})


def test_rebalance_weights():
    w = rebalance_weights({"crm", "marketing"})
    assert abs(sum(w.values()) - 1.0) < 1e-6
    assert set(w.keys()) == {"crm", "marketing"}


def test_camel_to_snake():
    assert camel_to_snake("serviceOrderId") == "service_order_id"
    assert camel_to_snake("orderSN") == "order_sn"
    assert camel_to_snake("createTime") == "create_time"
    assert camel_to_snake("order_sn") == "order_sn"
    assert camel_to_snake("id") == "id"


def test_filter_drill_row_camel_case_compatible():
    allowed = DRILL_ITEM_FIELDS["service_completion_rate"]
    raw = {
        "serviceOrderId": "2035909650134208512",
        "orderSn": "2035909650121625600",
        "orderStatus": 5,
        "createTime": "2026-03-23T10:41:01.000+08:00",
        "finishTime": None,
        "extraIgnored": 1,
    }
    got = filter_drill_row_by_allowed_fields(raw, allowed)
    assert got == {
        "service_order_id": "2035909650134208512",
        "order_sn": "2035909650121625600",
        "order_status": 5,
        "create_time": "2026-03-23T10:41:01.000+08:00",
        "finish_time": None,
    }


def test_filter_drill_row_snake_case_unchanged():
    allowed = DRILL_ITEM_FIELDS["service_completion_rate"]
    raw = {
        "service_order_id": "x",
        "order_sn": "y",
        "order_status": 1,
        "create_time": "t",
        "finish_time": None,
    }
    assert filter_drill_row_by_allowed_fields(raw, allowed) == raw
