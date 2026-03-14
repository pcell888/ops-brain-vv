"""
benchmark-server: 行业基准数据
传输: stdio
数据来源: 平台中台（非企业API）
"""

from __future__ import annotations

import json
import logging

import redis.asyncio as aioredis
from mcp.server import FastMCP

from src.core.config import get_settings
from src.mcp_servers.tenant_router import TenantRouter
from src.mcp_servers.biz_api_client import BizAPIClient

logger = logging.getLogger(__name__)

server = FastMCP("benchmark-server")
router = TenantRouter()
biz = BizAPIClient(router)
_redis: aioredis.Redis | None = None


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


@server.tool()
async def get_industry_benchmark(
    industry_code: str,
    indicator_codes: list[str],
    period: str | None = None,
) -> dict:
    """
    获取指定行业的基准数据。
    返回: 每个指标的 avg_value / median_value / excellent_value (P90)。
    优先从 Redis 缓存读取，缓存未命中调用平台中台API。
    """
    rd = await _get_redis()
    cache_key = f"benchmark:{industry_code}:{period or 'latest'}"
    cached = await rd.get(cache_key)
    if cached:
        all_benchmarks = json.loads(cached)
    else:
        data = await biz.platform_get("/industry-trend-statistics/benchmark", {
            "industryCode": industry_code,
            "period": period or "",
        })
        all_benchmarks = data.get("benchmarks", data)
        settings = get_settings()
        await rd.set(cache_key, json.dumps(all_benchmarks), ex=settings.benchmark_cache_ttl)

    result: dict = {}
    for code in indicator_codes:
        if code in all_benchmarks:
            result[code] = all_benchmarks[code]
        else:
            result[code] = {"avg_value": 0, "median_value": 0, "excellent_value": 0}

    return {
        "industry_code": industry_code,
        "period": period or "latest",
        "benchmarks": result,
    }


@server.tool()
async def list_industries() -> list[dict]:
    """获取所有行业编码及名称列表。"""
    data = await biz.platform_get("/store-class/list")
    return data.get("list", data) if isinstance(data, dict) else data


@server.tool()
async def get_industry_trend(
    industry_code: str,
    indicator_code: str,
    periods: int = 6,
) -> list[dict]:
    """获取行业指标趋势数据（最近N个月，用于对比分析图表）。"""
    data = await biz.platform_get("/industry-trend-statistics/trend", {
        "industryCode": industry_code,
        "indicatorCode": indicator_code,
        "periods": periods,
    })
    return data.get("trends", data) if isinstance(data, dict) else data


# ── stdio Transport ──────────────────────────────────────────────

if __name__ == "__main__":
    server.run(transport="stdio")
