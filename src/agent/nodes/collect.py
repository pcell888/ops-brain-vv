"""数据采集节点 — 并行采集企业画像 + 按选配维度动态采集指标 + 行业基准。"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from src.agent.state import DiagnosisState
from src.agent.tools import mcp_call, emit_progress
from src.core.calculator import extract_indicator_codes, resolve_active_indicators, NOT_APPLICABLE_MAP
from src.core.config import get_settings
from src.core.tenant_config import get_tenant_config

DIMENSION_TOOL_MAP: dict[str, str] = {
    "crm": "get_crm_indicators",
    "marketing": "get_marketing_indicators",
    "retention": "get_retention_indicators",
    "efficiency": "get_efficiency_indicators",
}

DIMENSION_STATE_KEY: dict[str, str] = {
    "crm": "crm_indicators",
    "marketing": "marketing_indicators",
    "retention": "retention_indicators",
    "efficiency": "efficiency_indicators",
}


async def collect_data_node(state: DiagnosisState) -> dict:
    tenant_id = state["tenant_id"]
    store_id = state["store_id"]

    active_dims, active_inds = resolve_active_indicators(
        state.get("selected_dimensions"),
        state.get("selected_indicators"),
    )

    settings = get_settings()
    tenant_config = await get_tenant_config(tenant_id)
    lookback_days = tenant_config.get("analysis_period_days") or settings.diagnosis_lookback_days
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=int(lookback_days))).strftime("%Y-%m-%d")

    scope_label = "全企业" if not store_id else f"店铺 {store_id}"
    emit_progress(state, f"开始采集{scope_label}运营数据（{len(active_dims)}个维度, {len(active_inds)}项指标）...")

    common_args = {
        "tenant_id": tenant_id,
        "store_id": store_id,
        "start_date": start_date,
        "end_date": end_date,
    }

    tasks = [mcp_call("crm-server", "get_store_profile", {"tenant_id": tenant_id, "store_id": store_id})]
    ordered_dims: list[str] = []
    for dim in ("crm", "marketing", "retention", "efficiency"):
        if dim in active_dims:
            tasks.append(mcp_call("metrics-server", DIMENSION_TOOL_MAP[dim], common_args))
            ordered_dims.append(dim)

    results = await asyncio.gather(*tasks)
    profile = results[0]
    dim_results = dict(zip(ordered_dims, results[1:]))

    emit_progress(state, "数据采集完成，正在获取行业基准数据...")

    indicator_dicts = [dim_results[d] for d in ordered_dims]
    all_indicator_codes = extract_indicator_codes(*indicator_dicts)
    filtered_codes = [c for c in all_indicator_codes if c in active_inds]

    benchmarks = await mcp_call("benchmark-server", "get_industry_benchmark", {
        "industry_code": profile.get("industry_code", ""),
        "indicator_codes": filtered_codes,
    })

    emit_progress(state, f"已采集 {len(filtered_codes)} 项指标，行业基准数据就绪")

    business_mode = profile.get("business_mode", "hybrid")
    na_codes = NOT_APPLICABLE_MAP.get(business_mode, set())

    output: dict = {
        "store_profile": profile,
        "benchmarks": benchmarks,
    }
    for dim in ("crm", "marketing", "retention", "efficiency"):
        dim_data = dim_results.get(dim)
        if dim_data and na_codes:
            raw = dim_data.get("indicators", {})
            for code in na_codes:
                if code in raw:
                    raw[code]["not_applicable"] = True
        output[DIMENSION_STATE_KEY[dim]] = dim_data

    return output
