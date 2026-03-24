"""数据采集节点 — 并行采集企业画像 + 按选配维度动态采集指标 + 行业基准。"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from src.agent.state import DiagnosisState
from src.agent.tools import mcp_call, emit_progress, unwrap_mcp_json_value
from src.core.calculator import extract_indicator_codes, resolve_active_indicators, NOT_APPLICABLE_MAP
from src.core.config import CN_TZ, get_settings
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
    auth_token = state.get("auth_token")

    active_dims, active_inds = resolve_active_indicators(
        state.get("selected_dimensions"),
        state.get("selected_indicators"),
    )

    settings = get_settings()
    tenant_config = await get_tenant_config(tenant_id)
    lookback_days = tenant_config.get("analysis_period_days") or settings.diagnosis_lookback_days
    _now = datetime.now(CN_TZ)
    end_date = _now.strftime("%Y-%m-%d")
    start_date = (_now - timedelta(days=int(lookback_days))).strftime("%Y-%m-%d")

    scope_label = "全企业" if not store_id else f"店铺 {store_id}"
    emit_progress(
        state, f"开始采集{scope_label}运营数据（{len(active_dims)}个维度, {len(active_inds)}项指标）...", percent=10
    )

    common_args = {
        "tenant_id": tenant_id,
        "store_id": store_id,
        "start_date": start_date,
        "end_date": end_date,
        "auth_token": auth_token,
    }

    ordered_dims: list[str] = []
    for dim in ("crm", "marketing", "retention", "efficiency"):
        if dim in active_dims:
            ordered_dims.append(dim)

    total_calls = 1 + len(ordered_dims)  # profile + each dimension
    base_percent = 10
    end_percent = 23
    percent_step = (end_percent - base_percent) / total_calls if total_calls > 0 else 0

    DIM_DISPLAY: dict[str, str] = {"crm": "CRM", "marketing": "营销", "retention": "留存", "efficiency": "效率"}

    _done_calls = [0]

    async def _wrap_with_progress(coro, label: str):
        result = await coro
        _done_calls[0] += 1
        cur = min(int(base_percent + percent_step * _done_calls[0]), end_percent)
        emit_progress(state, f"已采集{label}数据（{_done_calls[0]}/{total_calls}）", percent=cur)
        return result

    profile_task = _wrap_with_progress(
        mcp_call(
            "crm-server", "get_store_profile", {"tenant_id": tenant_id, "store_id": store_id, "auth_token": auth_token}
        ),
        "企业画像",
    )
    dim_tasks = {
        dim: _wrap_with_progress(
            mcp_call("metrics-server", DIMENSION_TOOL_MAP[dim], common_args), DIM_DISPLAY.get(dim, dim)
        )
        for dim in ordered_dims
    }

    all_results = await asyncio.gather(profile_task, *dim_tasks.values())
    profile = all_results[0]
    dim_raw_results = dict(zip(dim_tasks.keys(), all_results[1:]))
    if not isinstance(profile, dict):
        profile = unwrap_mcp_json_value(profile)
    if not isinstance(profile, dict):
        profile = {}
    dim_results: dict[str, object] = {}
    for dim in ordered_dims:
        v = dim_raw_results.get(dim)
        if not isinstance(v, dict):
            v = unwrap_mcp_json_value(v)
        dim_results[dim] = v if isinstance(v, dict) else {}

    emit_progress(state, "数据采集完成，正在获取行业基准数据...", percent=25)

    indicator_dicts = [dim_results[d] for d in ordered_dims]
    all_indicator_codes = extract_indicator_codes(*indicator_dicts)
    filtered_codes = [c for c in all_indicator_codes if c in active_inds]

    benchmarks = await mcp_call(
        "benchmark-server",
        "get_industry_benchmark",
        {
            "industry_code": profile.get("industry_code", ""),
            "indicator_codes": filtered_codes,
        },
    )
    if not isinstance(benchmarks, dict):
        benchmarks = unwrap_mcp_json_value(benchmarks)
    if not isinstance(benchmarks, dict):
        benchmarks = {}

    emit_progress(state, f"已采集 {len(filtered_codes)} 项指标，行业基准数据就绪", percent=33)

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
