"""Metrics dispatch — 供 dispatch 路由。"""

from __future__ import annotations

from src.biz.mock.handlers import client_sales_examine
from src.biz.mock.handlers import stats


_METRIC_GET_HANDLERS: tuple[tuple[str, ...], ...] = (
    ("client-record/statistics", client_sales_examine.client_record_statistics),
    ("sales-contract/statistics", client_sales_examine.sales_contract_statistics),
    ("examine-initiate/follow-stats", client_sales_examine.examine_follow_stats),
    ("examine-initiate/turnaround-stats", client_sales_examine.examine_turnaround_stats),
    ("service-order/completion-stats", stats.service_completion_stats),
    ("store-order/shipping-stats", stats.shipping_stats),
    ("account-coupon/statistics", stats.coupon_statistics),
    ("manage-data/exposure-stats", stats.exposure_stats),
    ("store-order/conversion-stats", stats.conversion_stats),
    ("seckill-apply/conversion-stats", stats.seckill_conversion_stats),
    ("store-refund-order/statistics", stats.refund_statistics),
    ("store-order-evaluate/statistics", stats.evaluate_statistics),
    ("store-order/repurchase-stats", stats.repurchase_stats),
)


def try_raw_request(method: str, path: str, q: dict, body: dict) -> dict | None:
    if method.upper() != "GET":
        return None
    for p, fn in _METRIC_GET_HANDLERS:
        if path == p:
            return fn(q)
    _ = body
    return None