"""行业基准数据 — 业务工具函数。"""

from __future__ import annotations

import json
import logging

import redis.asyncio as aioredis

from src.core.config import get_settings
from src.biz_tools.tenant_router import TenantRouter
from src.biz_tools.biz_api_client import BizAPIClient

logger = logging.getLogger(__name__)

router = TenantRouter()
biz = BizAPIClient(router)
_redis: aioredis.Redis | None = None
DEFAULT_BENCHMARKS: dict[str, dict] = {
    "lead_conversion_rate": {"avg_value": 5.2, "median_value": 4.8, "excellent_value": 8.5},
    "response_time_avg": {"avg_value": 6.0, "median_value": 5.5, "excellent_value": 2.0},
    "follow_up_count": {"avg_value": 800, "median_value": 750, "excellent_value": 1500},
    "coupon_redemption_rate": {"avg_value": 32.0, "median_value": 30.0, "excellent_value": 50.0},
    "browse_to_order_rate": {"avg_value": 5.8, "median_value": 5.0, "excellent_value": 10.0},
    "order_conversion_rate": {"avg_value": 85.0, "median_value": 83.0, "excellent_value": 95.0},
    "seckill_conversion_rate": {"avg_value": 30.0, "median_value": 28.0, "excellent_value": 55.0},
    "repurchase_rate": {"avg_value": 35.0, "median_value": 32.0, "excellent_value": 55.0},
    "refund_rate": {"avg_value": 5.0, "median_value": 4.5, "excellent_value": 2.0},
    "churn_rate": {"avg_value": 18.0, "median_value": 16.0, "excellent_value": 8.0},
    "positive_review_rate": {"avg_value": 82.0, "median_value": 80.0, "excellent_value": 95.0},
    "avg_customer_lifetime_value": {"avg_value": 1200.0, "median_value": 1000.0, "excellent_value": 2500.0},
    "service_completion_rate": {"avg_value": 80.0, "median_value": 78.0, "excellent_value": 95.0},
    "avg_shipping_hours": {"avg_value": 18.0, "median_value": 16.0, "excellent_value": 6.0},
}


def _normalize_code(code: str) -> str:
    return "".join(ch for ch in str(code).lower() if ch.isalnum())


def _to_float(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _extract_entry_code(entry: dict) -> str | None:
    for key in ("indicator_code", "indicatorCode", "code"):
        val = entry.get(key)
        if val:
            return str(val)
    return None


def _normalize_entry(entry) -> dict:
    if isinstance(entry, dict):
        return {
            "avg_value": _to_float(
                entry.get("avg_value", entry.get("avgValue", entry.get("average", entry.get("avg")))),
                0.0,
            ),
            "median_value": _to_float(
                entry.get("median_value", entry.get("medianValue", entry.get("median"))),
                0.0,
            ),
            "excellent_value": _to_float(
                entry.get("excellent_value", entry.get("excellentValue", entry.get("p90", entry.get("top_value")))),
                0.0,
            ),
        }
    return {"avg_value": _to_float(entry, 0.0), "median_value": 0.0, "excellent_value": 0.0}


def _normalize_all_benchmarks(raw) -> dict:
    by_code: dict[str, dict] = {}
    if isinstance(raw, dict):
        for code, entry in raw.items():
            by_code[str(code)] = _normalize_entry(entry)
        return by_code
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            code = _extract_entry_code(item)
            if not code:
                continue
            by_code[code] = _normalize_entry(item)
    return by_code


def _looks_like_zero_cache(all_benchmarks: dict, indicator_codes: list[str]) -> bool:
    if not all_benchmarks:
        return True
    targets = indicator_codes[: min(8, len(indicator_codes))]
    if not targets:
        return False
    zero_count = 0
    for code in targets:
        entry = all_benchmarks.get(code)
        if not isinstance(entry, dict):
            zero_count += 1
            continue
        if _to_float(entry.get("avg_value"), 0.0) == 0.0:
            zero_count += 1
    return zero_count == len(targets)


async def _fetch_benchmarks_from_platform(industry_code: str, period: str | None) -> dict:
    return {"benchmarks": DEFAULT_BENCHMARKS.copy()}


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def get_industry_benchmark(
    tenant_id: str,
    industry_code: str,
    indicator_codes: list[str],
    period: str | None = None,
) -> dict:
    logger.info(
        "Tool called: get_industry_benchmark tenant=%s industry=%s indicators=%s period=%s",
        tenant_id,
        industry_code,
        indicator_codes,
        period,
    )
    rd = await _get_redis()
    cache_key = f"benchmark:{tenant_id}:{industry_code}:{period or 'latest'}"
    cached = await rd.get(cache_key)
    if cached:
        all_benchmarks = _normalize_all_benchmarks(json.loads(cached))
        if _looks_like_zero_cache(all_benchmarks, indicator_codes):
            logger.warning("命中疑似全0基准缓存，准备重拉: %s", cache_key)
            cached = None
    if not cached:
        data = await _fetch_benchmarks_from_platform(industry_code, period)
        all_benchmarks = _normalize_all_benchmarks(data.get("benchmarks", data))
        if not all_benchmarks:
            logger.warning("行业基准为空，使用默认基准兜底: %s", industry_code)
            all_benchmarks = DEFAULT_BENCHMARKS.copy()
        settings = get_settings()
        await rd.set(cache_key, json.dumps(all_benchmarks), ex=settings.benchmark_cache_ttl)

    result: dict = {}
    normalized_index = {_normalize_code(k): v for k, v in all_benchmarks.items()}
    for code in indicator_codes:
        if code in all_benchmarks:
            result[code] = all_benchmarks[code]
        elif _normalize_code(code) in normalized_index:
            result[code] = normalized_index[_normalize_code(code)]
        elif code in DEFAULT_BENCHMARKS:
            result[code] = DEFAULT_BENCHMARKS[code]
        else:
            result[code] = {"avg_value": 0, "median_value": 0, "excellent_value": 0}

    return {
        "industry_code": industry_code,
        "period": period or "latest",
        "benchmarks": result,
    }


async def list_industries(tenant_id: str) -> list[dict]:
    logger.info("Tool called: list_industries tenant=%s", tenant_id)
    data = await biz.platform_get("/store-class/list", auth_tenant_id=tenant_id)
    return data.get("list", data) if isinstance(data, dict) else data


async def get_industry_trend(
    tenant_id: str,
    industry_code: str,
    indicator_code: str,
    periods: int = 6,
) -> list[dict]:
    logger.info(
        "Tool called: get_industry_trend tenant=%s industry=%s indicator=%s periods=%s",
        tenant_id,
        industry_code,
        indicator_code,
        periods,
    )
    data = await biz.platform_get(
        "/industry-trend-statistics/trend",
        {
            "industryCode": industry_code,
            "indicatorCode": indicator_code,
            "periods": periods,
        },
        auth_tenant_id=tenant_id,
    )
    return data.get("trends", data) if isinstance(data, dict) else data


async def get_project_enterprise_info(tenant_id: str) -> dict:
    logger.info("Tool called: get_project_enterprise_info tenant=%s", tenant_id)
    q = {"projectId": tenant_id}
    return await biz.platform_get("ai/customer/projectInfo", q, auth_tenant_id=tenant_id)
