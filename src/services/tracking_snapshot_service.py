"""快照采集、列表与看板。"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta

from src.agent.tools import MCPToolInvocationError, mcp_call, unwrap_mcp_json_value
from src.core.calculator import (
    INDICATOR_META,
    NOT_APPLICABLE_MAP,
    calculate_dimension_score,
    extract_indicator_codes,
    rebalance_weights,
    resolve_active_indicators,
)
from src.core.compat_tracking_repo import (
    create_tracking,
    get_first_exec_task_plan_store,
    get_snapshot_by_id,
    get_tracking,
    insert_snapshot,
    list_snapshots,
    update_tracking_data,
)
from src.core.config import CN_TZ, get_settings
from src.core.db_init import ensure_ai_effect_tracking
from src.core.pending_review_repo import cancel_pending_review
from src.core.snapshot_repo import list_snapshots as list_effect_snapshots_for_thread
from src.core.tenant_config import get_tenant_config
from src.mcp_servers.biz_scope import effective_store_id_for_biz

from src.services.tracking_error_service import TrackingServiceError
from src.services.tracking_helper_service import _ser

logger = logging.getLogger(__name__)

_TRACKING_METRIC_TOOLS: dict[str, str] = {
    "crm": "get_crm_indicators",
    "marketing": "get_marketing_indicators",
    "retention": "get_retention_indicators",
    "efficiency": "get_efficiency_indicators",
}


async def _build_effect_tracking_snapshot(
    tenant_id: str,
    store_id_db: str,
    tracking_data: dict,
    *,
    snapshot_at: datetime,
    auth_token: str | None,
) -> dict:
    active_dims, active_inds = resolve_active_indicators(
        tracking_data.get("selected_dimensions"),
        tracking_data.get("selected_indicators"),
    )
    store_id = effective_store_id_for_biz(tenant_id, store_id_db or "")
    settings = get_settings()
    tenant_config = await get_tenant_config(tenant_id)
    lookback_days = int(tenant_config.get("analysis_period_days") or settings.diagnosis_lookback_days)
    end_date = snapshot_at.strftime("%Y-%m-%d %H:%M:%S")
    start_date = (snapshot_at - timedelta(days=lookback_days)).strftime("%Y-%m-%d %H:%M:%S")
    common_args: dict = {"tenant_id": tenant_id, "store_id": store_id, "start_date": start_date, "end_date": end_date}
    if auth_token:
        common_args["auth_token"] = auth_token

    ordered_dims = [d for d in ("crm", "marketing", "retention", "efficiency") if d in active_dims]
    profile_task = mcp_call(
        "crm-server",
        "get_store_profile",
        {"tenant_id": tenant_id, "store_id": store_id, **({"auth_token": auth_token} if auth_token else {})},
    )
    dim_tasks = [mcp_call("metrics-server", _TRACKING_METRIC_TOOLS[d], common_args) for d in ordered_dims]
    all_results = await asyncio.gather(profile_task, *dim_tasks)

    profile = all_results[0]
    if not isinstance(profile, dict):
        profile = unwrap_mcp_json_value(profile)
    if not isinstance(profile, dict):
        profile = {}

    dim_results: dict[str, dict] = {}
    for dim, raw in zip(ordered_dims, all_results[1:]):
        v = raw if isinstance(raw, dict) else unwrap_mcp_json_value(raw)
        dim_results[dim] = v if isinstance(v, dict) else {}

    business_mode = profile.get("business_mode", "hybrid")
    na_codes = NOT_APPLICABLE_MAP.get(business_mode, set())
    for _dim, dim_data in dim_results.items():
        if dim_data and na_codes:
            raw_inds = dim_data.get("indicators", {})
            if isinstance(raw_inds, dict):
                for code in na_codes:
                    if code in raw_inds and isinstance(raw_inds[code], dict):
                        raw_inds[code]["not_applicable"] = True

    indicator_dicts = [dim_results[d] for d in ordered_dims]
    codes_for_benchmark = [c for c in extract_indicator_codes(*indicator_dicts) if c in active_inds]
    benchmarks = await mcp_call(
        "benchmark-server",
        "get_industry_benchmark",
        {"tenant_id": tenant_id, "industry_code": profile.get("industry_code", ""), "indicator_codes": codes_for_benchmark},
    )
    if not isinstance(benchmarks, dict):
        benchmarks = unwrap_mcp_json_value(benchmarks)
    if not isinstance(benchmarks, dict):
        benchmarks = {}
    benchmark_payload = benchmarks.get("benchmarks", benchmarks)
    if not isinstance(benchmark_payload, dict):
        benchmark_payload = {}

    weights = rebalance_weights(active_dims)
    dimension_scores: dict = {}
    for dim_name in ("crm", "marketing", "retention", "efficiency"):
        if dim_name not in active_dims:
            continue
        indicators = dim_results.get(dim_name, {})
        weight = weights.get(dim_name, 0.0)
        if not indicators:
            dimension_scores[dim_name] = {"score": 60.0, "weight": weight}
            continue
        score, _, _ = calculate_dimension_score(
            indicators=indicators, benchmarks=benchmark_payload, dimension=dim_name, active_indicators=active_inds
        )
        dimension_scores[dim_name] = {"score": score, "weight": weight}

    health_score = sum(d["score"] * d["weight"] for d in dimension_scores.values())
    flat: dict[str, dict] = {}
    for dim_name in ordered_dims:
        pack = dim_results.get(dim_name) or {}
        inds = pack.get("indicators", {}) if isinstance(pack, dict) else {}
        if not isinstance(inds, dict):
            continue
        for code, spec in inds.items():
            if code not in INDICATOR_META:
                continue
            if isinstance(spec, dict) and spec.get("not_applicable"):
                continue
            meta = INDICATOR_META[code]
            raw_val = spec.get("value") if isinstance(spec, dict) else spec
            try:
                val_f = round(float(raw_val), 2)
            except (TypeError, ValueError):
                continue
            unit = meta.get("unit", "")
            if isinstance(spec, dict) and spec.get("unit"):
                unit = str(spec.get("unit"))
            flat[code] = {"name": meta["name"], "value": val_f, "unit": unit}

    return {
        "snapshot_at": snapshot_at.isoformat(),
        "health_score": round(float(health_score), 1),
        "indicators": flat,
        "snapshot_type": "periodic",
        "period": {"start_date": start_date, "end_date": end_date},
        "source": "mcp_metrics",
    }


async def _ensure_effect_tracking_row(thread_id: str, tenant_id: str) -> tuple[str, str, dict]:
    row = await get_tracking(thread_id)
    if row:
        if row["tenant_id"] != tenant_id:
            raise TrackingServiceError(403, "追踪记录与当前企业不匹配")
        td = row["tracking_data"] or {}
        if isinstance(td, str):
            td = json.loads(td)
        return row["store_id"], row["tenant_id"], td

    et = await get_first_exec_task_plan_store(thread_id, tenant_id)
    plan_id = (et["plan_id"] or "") if et else ""
    store_id = (et["store_id"] or "") if et else ""
    now = datetime.now(CN_TZ)
    td = {
        "plan_id": plan_id,
        "status": "active",
        "solution_name": (f"方案 {plan_id[:8]}" if plan_id else "效果追踪"),
        "current_score": None,
        "snapshot_count": 0,
        "started_at": now.isoformat(),
        "last_snapshot_at": None,
        "completed_at": None,
        "source": "bootstrap_snapshot",
    }
    await create_tracking(
        thread_id=thread_id,
        tenant_id=tenant_id,
        store_id=store_id,
        tracking_data=td,
        created_at=now,
    )
    try:
        await cancel_pending_review(thread_id)
    except Exception as e:
        logger.warning("取消待复盘记录（bootstrap）: %s", e)
    return store_id, tenant_id, td


async def take_tracking_snapshot(tracking_id: str, enterprise_id: str | None, auth_token: str | None) -> dict:
    now = datetime.now(CN_TZ)
    try:
        await ensure_ai_effect_tracking()
        tenant_id = ""
        store_id = ""
        td: dict = {}
        row = await get_tracking(tracking_id)
        if not row:
            if not enterprise_id:
                raise TrackingServiceError(400, "尚无效果追踪记录，请在请求体中传入 enterprise_id 以首次创建并采集快照")
            store_id, tenant_id, td = await _ensure_effect_tracking_row(tracking_id, enterprise_id.strip())
        else:
            td = row["tracking_data"] or {}
            if isinstance(td, str):
                td = json.loads(td)
            tenant_id = row["tenant_id"]
            store_id = row["store_id"]
        snapshot_count_before = int(td.get("snapshot_count") or 0)
        try:
            snapshot_data = await _build_effect_tracking_snapshot(tenant_id, store_id, td, snapshot_at=now, auth_token=auth_token)
        except MCPToolInvocationError as e:
            logger.exception("采集快照 MCP 业务错误 tracking_id=%s", tracking_id)
            raise TrackingServiceError(502, "指标采集失败，请稍后重试") from e
        except RuntimeError as err:
            logger.exception("采集快照指标服务不可用 tracking_id=%s", tracking_id)
            raise TrackingServiceError(502, "指标服务暂不可用，请稍后重试") from err

        snapshot_data["snapshot_type"] = "baseline" if snapshot_count_before <= 0 else "periodic"
        td["snapshot_count"] = snapshot_count_before + 1
        td["last_snapshot_at"] = now.isoformat()
        td["current_score"] = snapshot_data.get("health_score")
        await update_tracking_data(tracking_id, td)
        await insert_snapshot(
            thread_id=tracking_id,
            tenant_id=tenant_id,
            store_id=store_id,
            snapshot_data=snapshot_data,
            snapshot_at=now,
        )
        return {"status": "ok", "message": "快照已采集", "snapshot_at": now.isoformat()}
    except TrackingServiceError:
        raise
    except Exception as e:
        logger.exception("采集快照失败 tracking_id=%s", tracking_id)
        raise TrackingServiceError(500, "采集快照失败，请稍后重试") from e


async def list_tracking_snapshots_view(tracking_id: str) -> dict:
    try:
        rows = await list_snapshots(tracking_id, with_id=True)
        items: list[dict] = []
        prev_indicators: dict[str, float] = {}
        for row in rows:
            sd = row["snapshot_data"] or {}
            if isinstance(sd, str):
                sd = json.loads(sd)
            indicators = sd.get("indicators", {}) or {}
            indicator_changes: list[dict] = []
            current_indicators: dict[str, float] = {}
            for code, raw in indicators.items():
                if isinstance(raw, dict):
                    name, value, unit = raw.get("name", code), raw.get("value"), raw.get("unit", "")
                else:
                    name, value, unit = code, raw, ""
                if value is None:
                    continue
                try:
                    num = float(value)
                except (TypeError, ValueError):
                    continue
                last_val = prev_indicators.get(code)
                delta = None if last_val is None else round(num - last_val, 2)
                current_indicators[code] = num
                indicator_changes.append(
                    {"indicator_code": code, "name": name, "value": round(num, 2), "unit": unit, "delta_vs_prev": delta}
                )
            indicator_changes.sort(key=lambda x: abs(x["delta_vs_prev"]) if x["delta_vs_prev"] is not None else -1, reverse=True)
            items.append(
                {
                    "snapshot_id": str(row["id"]),
                    "snapshot_at": _ser(row["snapshot_at"]),
                    "health_score": sd.get("health_score"),
                    "snapshot_type": sd.get("snapshot_type", "periodic"),
                    "indicator_count": len(indicator_changes),
                    "indicator_changes": indicator_changes,
                }
            )
            prev_indicators = current_indicators
        items.reverse()
        return {"items": items, "total": len(items)}
    except Exception:
        logger.exception("查询快照列表失败")
        return {"items": [], "total": 0}


async def get_snapshot_dashboard_payload(snapshot_id: str) -> dict:
    try:
        row = await get_snapshot_by_id(int(snapshot_id))
        if not row:
            raise TrackingServiceError(404, "快照不存在")
        sd = row["snapshot_data"] or {}
        if isinstance(sd, str):
            sd = json.loads(sd)
        return {
            "snapshot_id": snapshot_id,
            "snapshot_at": _ser(row["snapshot_at"]),
            "health_score": sd.get("health_score"),
            "indicators": sd.get("indicators", {}),
        }
    except TrackingServiceError:
        raise
    except ValueError:
        raise TrackingServiceError(400, "无效的快照ID")
    except Exception as e:
        logger.exception("查询快照看板失败")
        raise TrackingServiceError(500, "查询失败，请稍后重试") from e


async def get_effect_snapshots_standard(thread_id: str) -> dict:
    """与 `snapshot_repo.list_snapshots` 相同语义（时间正序、snapshot_at 已序列化）。"""
    snapshots = await list_effect_snapshots_for_thread(thread_id)
    return {"thread_id": thread_id, "count": len(snapshots), "snapshots": snapshots}
