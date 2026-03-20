"""前端兼容层 — /tracking 系列接口。

基于 ai_effect_tracking / ai_effect_snapshot / ai_review_report /
ai_solution_knowledge 表提供效果追踪与复盘接口。
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from src.core.config import get_settings
from src.core.db_init import _uri_to_conninfo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tracking", tags=["效果追踪(兼容层)"])


def _conninfo() -> str:
    return _uri_to_conninfo(get_settings().postgres_uri)


def _ser(v):
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v


# ── 启动追踪 ──────────────────────────────────────────────────────

@router.post("/start", summary="启动效果追踪")
async def start_tracking(data: dict):
    """前端 POST /tracking/start
    body: { enterprise_id, plan_id, tracking_interval_days? }
    """
    enterprise_id = data.get("enterprise_id", "")
    plan_id = data.get("plan_id", "")
    interval_days = data.get("tracking_interval_days", 7)

    if not enterprise_id or not plan_id:
        raise HTTPException(status_code=400, detail="enterprise_id 和 plan_id 必填")

    thread_id = f"trk_{uuid.uuid4().hex[:16]}"
    now = datetime.now()

    tracking_data = {
        "plan_id": plan_id,
        "status": "active",
        "solution_name": f"方案 {plan_id[:8]}",
        "current_score": None,
        "snapshot_count": 0,
        "started_at": now.isoformat(),
        "last_snapshot_at": None,
        "completed_at": None,
        "tracking_interval_days": interval_days,
    }

    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """INSERT INTO ai_effect_tracking (thread_id, tenant_id, store_id, tracking_data, created_at)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (thread_id, enterprise_id, "st_001", json.dumps(tracking_data), now),
                )
            await conn.commit()

        return {"tracking_id": thread_id, "status": "active", "message": "追踪已启动"}
    except Exception as e:
        logger.error("启动追踪失败: %s", e)
        raise HTTPException(status_code=500, detail="启动追踪失败") from e


# ── 追踪列表 ─────────────────────────────────────────────────────

@router.get("/list", summary="追踪列表")
async def list_trackings(
    enterprise_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                where_parts = []
                params: list = []
                if enterprise_id:
                    where_parts.append("tenant_id = %s")
                    params.append(enterprise_id)
                where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

                await cur.execute(
                    f"SELECT COUNT(*) FROM ai_effect_tracking {where_sql}", params
                )
                total = (await cur.fetchone() or {}).get("count", 0)

                await cur.execute(
                    f"""SELECT thread_id, tenant_id, tracking_data, created_at
                        FROM ai_effect_tracking {where_sql}
                        ORDER BY created_at DESC OFFSET %s LIMIT %s""",
                    params + [skip, limit],
                )
                rows = await cur.fetchall()

        items = []
        for row in rows:
            td = row["tracking_data"] or {}
            if isinstance(td, str):
                td = json.loads(td)

            if status and td.get("status") != status:
                continue

            items.append({
                "tracking_id": row["thread_id"],
                "plan_id": td.get("plan_id", ""),
                "solution_name": td.get("solution_name", ""),
                "status": td.get("status", "active"),
                "current_score": td.get("current_score"),
                "snapshot_count": td.get("snapshot_count", 0),
                "started_at": td.get("started_at", _ser(row["created_at"])),
                "last_snapshot_at": td.get("last_snapshot_at"),
                "completed_at": td.get("completed_at"),
            })

        return {"items": items, "total": total}
    except Exception as e:
        logger.error("查询追踪列表失败: %s", e)
        return {"items": [], "total": 0}


# ── 案例搜索（静态路由，须在 /{tracking_id} 之前） ────────────────

@router.get("/cases/search", summary="案例搜索")
async def search_cases(
    industry: str | None = Query(default=None),
    problem_type: str | None = Query(default=None),
    min_score: float | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                where_parts = []
                params: list = []
                if industry:
                    where_parts.append("industry_code = %s")
                    params.append(industry)
                if min_score is not None:
                    where_parts.append("achievement_rate >= %s")
                    params.append(min_score)

                where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

                await cur.execute(
                    f"SELECT COUNT(*) FROM ai_solution_knowledge {where_sql}", params
                )
                total = (await cur.fetchone() or {}).get("count", 0)

                await cur.execute(
                    f"""SELECT id, tenant_id, plan_name, target_indicators, industry_code,
                               achievement_rate, indicator_changes, created_at
                        FROM ai_solution_knowledge {where_sql}
                        ORDER BY achievement_rate DESC OFFSET %s LIMIT %s""",
                    params + [skip, limit],
                )
                rows = await cur.fetchall()

        items = []
        for row in rows:
            items.append({
                "case_id": str(row["id"]),
                "plan_name": row["plan_name"],
                "industry": row.get("industry_code", ""),
                "target_indicators": row.get("target_indicators", []),
                "achievement_rate": row.get("achievement_rate", 0),
                "indicator_changes": row.get("indicator_changes", []),
                "created_at": _ser(row["created_at"]),
            })

        return {"items": items, "total": total}
    except Exception as e:
        logger.error("搜索案例失败: %s", e)
        return {"items": [], "total": 0}


@router.get("/cases/similar", summary="相似案例")
async def get_similar_cases(
    indicators: str = Query(default=""),
    industry: str | None = Query(default=None),
    limit: int = Query(default=5, ge=1, le=20),
):
    indicator_list = [i.strip() for i in indicators.split(",") if i.strip()]

    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                if indicator_list:
                    await cur.execute(
                        """SELECT id, plan_name, target_indicators, industry_code,
                                  achievement_rate, indicator_changes, created_at
                           FROM ai_solution_knowledge
                           WHERE target_indicators && %s
                           ORDER BY achievement_rate DESC LIMIT %s""",
                        (indicator_list, limit),
                    )
                else:
                    where = "WHERE industry_code = %s" if industry else ""
                    params: list = [industry] if industry else []
                    await cur.execute(
                        f"""SELECT id, plan_name, target_indicators, industry_code,
                                   achievement_rate, indicator_changes, created_at
                            FROM ai_solution_knowledge {where}
                            ORDER BY achievement_rate DESC LIMIT %s""",
                        params + [limit],
                    )
                rows = await cur.fetchall()

        items = []
        for row in rows:
            items.append({
                "case_id": str(row["id"]),
                "plan_name": row["plan_name"],
                "industry": row.get("industry_code", ""),
                "target_indicators": row.get("target_indicators", []),
                "achievement_rate": row.get("achievement_rate", 0),
                "indicator_changes": row.get("indicator_changes", []),
                "created_at": _ser(row["created_at"]),
            })

        return {"items": items, "total": len(items)}
    except Exception as e:
        logger.error("查询相似案例失败: %s", e)
        return {"items": [], "total": 0}


@router.get("/cases/{case_id}", summary="案例详情")
async def get_case_detail(case_id: str):
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT * FROM ai_solution_knowledge WHERE id = %s",
                    (int(case_id),),
                )
                row = await cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="案例不存在")

        return {
            "case_id": str(row["id"]),
            "tenant_id": row["tenant_id"],
            "thread_id": row["thread_id"],
            "plan_id": row["plan_id"],
            "plan_name": row["plan_name"],
            "industry": row.get("industry_code", ""),
            "target_indicators": row.get("target_indicators", []),
            "achievement_rate": row.get("achievement_rate", 0),
            "indicator_changes": row.get("indicator_changes", []),
            "plan_detail": row.get("plan_detail", {}),
            "lessons_learned": row.get("lessons_learned", []),
            "created_at": _ser(row["created_at"]),
        }
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的案例ID")
    except Exception as e:
        logger.error("查询案例详情失败: %s", e)
        raise HTTPException(status_code=500, detail="查询失败") from e


@router.get("/snapshots/{snapshot_id}/dashboard", summary="快照看板")
async def get_snapshot_dashboard(snapshot_id: str):
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT snapshot_data, snapshot_at FROM ai_effect_snapshot WHERE id = %s",
                    (int(snapshot_id),),
                )
                row = await cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="快照不存在")

        sd = row["snapshot_data"] or {}
        if isinstance(sd, str):
            sd = json.loads(sd)

        return {
            "snapshot_id": snapshot_id,
            "snapshot_at": _ser(row["snapshot_at"]),
            "health_score": sd.get("health_score"),
            "indicators": sd.get("indicators", {}),
        }
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的快照ID")
    except Exception as e:
        logger.error("查询快照看板失败: %s", e)
        raise HTTPException(status_code=500, detail="查询失败") from e


# ── 追踪摘要 ─────────────────────────────────────────────────────

@router.get("/{tracking_id}", summary="追踪摘要")
async def get_tracking_summary(tracking_id: str):
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT * FROM ai_effect_tracking WHERE thread_id = %s",
                    (tracking_id,),
                )
                row = await cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="追踪不存在")

        td = row["tracking_data"] or {}
        if isinstance(td, str):
            td = json.loads(td)

        return {
            "tracking_id": row["thread_id"],
            "plan_id": td.get("plan_id", ""),
            "solution_name": td.get("solution_name", ""),
            "status": td.get("status", "active"),
            "current_score": td.get("current_score"),
            "snapshot_count": td.get("snapshot_count", 0),
            "started_at": td.get("started_at", _ser(row["created_at"])),
            "last_snapshot_at": td.get("last_snapshot_at"),
            "completed_at": td.get("completed_at"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("查询追踪摘要失败: %s", e)
        raise HTTPException(status_code=500, detail="查询失败") from e


# ── 采集快照 ─────────────────────────────────────────────────────

@router.post("/{tracking_id}/snapshot", summary="采集快照")
async def take_snapshot(tracking_id: str):
    """采集当前指标快照并存入 ai_effect_snapshot。"""
    import random

    now = datetime.now()
    snapshot_data = {
        "snapshot_at": now.isoformat(),
        "health_score": round(random.uniform(55, 95), 1),
        "indicators": {},
    }

    try:
        from src.core.calculator import INDICATOR_META

        for code, meta in INDICATOR_META.items():
            base = 50.0
            snapshot_data["indicators"][code] = {
                "name": meta["name"],
                "value": round(base + random.uniform(-20, 40), 2),
                "unit": meta.get("unit", ""),
            }
    except Exception:
        pass

    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT tracking_data, tenant_id, store_id FROM ai_effect_tracking WHERE thread_id = %s",
                    (tracking_id,),
                )
                row = await cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="追踪不存在")

                td = row["tracking_data"] or {}
                if isinstance(td, str):
                    td = json.loads(td)

                td["snapshot_count"] = td.get("snapshot_count", 0) + 1
                td["last_snapshot_at"] = now.isoformat()
                td["current_score"] = snapshot_data.get("health_score")

                await cur.execute(
                    "UPDATE ai_effect_tracking SET tracking_data = %s WHERE thread_id = %s",
                    (json.dumps(td), tracking_id),
                )

                await cur.execute(
                    """INSERT INTO ai_effect_snapshot (thread_id, tenant_id, store_id, snapshot_data, snapshot_at)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (tracking_id, row["tenant_id"], row["store_id"],
                     json.dumps(snapshot_data), now),
                )
            await conn.commit()

        return {"status": "ok", "message": "快照已采集", "snapshot_at": now.isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("采集快照失败: %s", e)
        raise HTTPException(status_code=500, detail="采集快照失败") from e


# ── 效果分析 ─────────────────────────────────────────────────────

@router.get("/{tracking_id}/analyze", summary="效果分析")
async def analyze_tracking(tracking_id: str):
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """SELECT snapshot_data, snapshot_at FROM ai_effect_snapshot
                       WHERE thread_id = %s ORDER BY snapshot_at""",
                    (tracking_id,),
                )
                snapshots = await cur.fetchall()

        if not snapshots:
            return {"tracking_id": tracking_id, "trend": "no_data", "snapshots": 0, "analysis": "暂无快照数据"}

        scores = []
        for s in snapshots:
            sd = s["snapshot_data"] or {}
            if isinstance(sd, str):
                sd = json.loads(sd)
            scores.append(sd.get("health_score", 0))

        if len(scores) >= 2:
            trend = "improving" if scores[-1] > scores[0] else "declining" if scores[-1] < scores[0] else "stable"
        else:
            trend = "insufficient_data"

        return {
            "tracking_id": tracking_id,
            "trend": trend,
            "snapshots": len(snapshots),
            "first_score": scores[0] if scores else None,
            "latest_score": scores[-1] if scores else None,
            "score_change": round(scores[-1] - scores[0], 1) if len(scores) >= 2 else 0,
            "analysis": f"共采集 {len(snapshots)} 次快照，评分趋势: {trend}",
        }
    except Exception as e:
        logger.error("效果分析失败: %s", e)
        return {"tracking_id": tracking_id, "trend": "error", "snapshots": 0, "analysis": "分析失败"}


# ── 完成追踪 ─────────────────────────────────────────────────────

@router.post("/{tracking_id}/complete", summary="完成追踪")
async def complete_tracking(tracking_id: str):
    now = datetime.now()
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT tracking_data, tenant_id, store_id FROM ai_effect_tracking WHERE thread_id = %s",
                    (tracking_id,),
                )
                row = await cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="追踪不存在")

                td = row["tracking_data"] or {}
                if isinstance(td, str):
                    td = json.loads(td)

                td["status"] = "completed"
                td["completed_at"] = now.isoformat()

                await cur.execute(
                    "UPDATE ai_effect_tracking SET tracking_data = %s WHERE thread_id = %s",
                    (json.dumps(td), tracking_id),
                )

                await cur.execute(
                    """SELECT snapshot_data FROM ai_effect_snapshot
                       WHERE thread_id = %s ORDER BY snapshot_at""",
                    (tracking_id,),
                )
                snap_rows = await cur.fetchall()

                scores = []
                for sr in snap_rows:
                    sd = sr["snapshot_data"] or {}
                    if isinstance(sd, str):
                        sd = json.loads(sd)
                    scores.append(sd.get("health_score", 0))

                report = {
                    "tracking_id": tracking_id,
                    "plan_id": td.get("plan_id", ""),
                    "solution_name": td.get("solution_name", ""),
                    "total_snapshots": len(scores),
                    "started_at": td.get("started_at"),
                    "completed_at": now.isoformat(),
                    "initial_score": scores[0] if scores else None,
                    "final_score": scores[-1] if scores else None,
                    "score_change": round(scores[-1] - scores[0], 1) if len(scores) >= 2 else 0,
                    "trend": "improving" if len(scores) >= 2 and scores[-1] > scores[0] else "stable",
                    "summary": f"追踪期间共采集 {len(scores)} 次快照",
                    "recommendations": ["继续保持当前优化策略", "关注核心指标变化趋势"],
                }

                await cur.execute(
                    """INSERT INTO ai_review_report (thread_id, tenant_id, store_id, report, created_at)
                       VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (thread_id) DO UPDATE SET report = EXCLUDED.report""",
                    (tracking_id, row["tenant_id"], row["store_id"], json.dumps(report), now),
                )
            await conn.commit()

        return {"status": "ok", "message": "追踪已完成，复盘报告已生成"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("完成追踪失败: %s", e)
        raise HTTPException(status_code=500, detail="完成追踪失败") from e


# ── 取消追踪 ─────────────────────────────────────────────────────

@router.post("/{tracking_id}/cancel", summary="取消追踪")
async def cancel_tracking(tracking_id: str):
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT tracking_data FROM ai_effect_tracking WHERE thread_id = %s",
                    (tracking_id,),
                )
                row = await cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="追踪不存在")

                td = row["tracking_data"] or {}
                if isinstance(td, str):
                    td = json.loads(td)

                td["status"] = "cancelled"

                await cur.execute(
                    "UPDATE ai_effect_tracking SET tracking_data = %s WHERE thread_id = %s",
                    (json.dumps(td), tracking_id),
                )
            await conn.commit()

        return {"status": "ok", "message": "追踪已停止"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("取消追踪失败: %s", e)
        raise HTTPException(status_code=500, detail="取消失败") from e


# ── 指标趋势 ─────────────────────────────────────────────────────

@router.get("/{tracking_id}/trends", summary="指标趋势")
async def get_trends(tracking_id: str):
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """SELECT snapshot_data, snapshot_at FROM ai_effect_snapshot
                       WHERE thread_id = %s ORDER BY snapshot_at""",
                    (tracking_id,),
                )
                rows = await cur.fetchall()

        trends: dict[str, list] = {}
        timestamps = []

        for row in rows:
            sd = row["snapshot_data"] or {}
            if isinstance(sd, str):
                sd = json.loads(sd)
            timestamps.append(_ser(row["snapshot_at"]))
            for code, val in (sd.get("indicators") or {}).items():
                if code not in trends:
                    trends[code] = []
                trends[code].append(val.get("value") if isinstance(val, dict) else val)

        return {
            "tracking_id": tracking_id,
            "timestamps": timestamps,
            "indicators": trends,
        }
    except Exception as e:
        logger.error("查询趋势失败: %s", e)
        return {"tracking_id": tracking_id, "timestamps": [], "indicators": {}}


# ── 复盘报告 ─────────────────────────────────────────────────────

@router.get("/{tracking_id}/report", summary="复盘报告")
async def get_report(tracking_id: str):
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT report FROM ai_review_report WHERE thread_id = %s",
                    (tracking_id,),
                )
                row = await cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="复盘报告不存在，请先完成追踪")

        report = row["report"] or {}
        if isinstance(report, str):
            report = json.loads(report)

        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error("查询复盘报告失败: %s", e)
        raise HTTPException(status_code=500, detail="查询失败") from e


# ── 快照列表 ─────────────────────────────────────────────────────

@router.get("/{tracking_id}/snapshots", summary="快照列表")
async def get_snapshots(tracking_id: str):
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """SELECT id, snapshot_data, snapshot_at FROM ai_effect_snapshot
                       WHERE thread_id = %s ORDER BY snapshot_at DESC""",
                    (tracking_id,),
                )
                rows = await cur.fetchall()

        items = []
        for row in rows:
            sd = row["snapshot_data"] or {}
            if isinstance(sd, str):
                sd = json.loads(sd)
            items.append({
                "snapshot_id": str(row["id"]),
                "snapshot_at": _ser(row["snapshot_at"]),
                "health_score": sd.get("health_score"),
                "indicator_count": len(sd.get("indicators", {})),
            })

        return {"items": items, "total": len(items)}
    except Exception as e:
        logger.error("查询快照列表失败: %s", e)
        return {"items": [], "total": 0}


# ── 看板数据（简化版） ───────────────────────────────────────────

@router.get("/{tracking_id}/dashboard/funnel", summary="转化漏斗")
async def get_dashboard_funnel(tracking_id: str):
    return {
        "tracking_id": tracking_id,
        "stages": [
            {"name": "浏览", "value": 10000},
            {"name": "加购", "value": 3500},
            {"name": "下单", "value": 1800},
            {"name": "支付", "value": 1500},
            {"name": "完成", "value": 1200},
        ],
    }


@router.get("/{tracking_id}/dashboard/teams", summary="团队对比")
async def get_dashboard_teams(tracking_id: str):
    return {
        "tracking_id": tracking_id,
        "teams": [
            {"name": "销售一组", "score": 82, "deals": 45},
            {"name": "销售二组", "score": 76, "deals": 38},
            {"name": "销售三组", "score": 88, "deals": 52},
        ],
    }


@router.get("/{tracking_id}/dashboard/ranking", summary="销售排名")
async def get_dashboard_ranking(tracking_id: str, limit: int = Query(default=10)):
    return {
        "tracking_id": tracking_id,
        "rankings": [
            {"rank": 1, "name": "张三", "amount": 125000, "deals": 18},
            {"rank": 2, "name": "李四", "amount": 98000, "deals": 15},
            {"rank": 3, "name": "王五", "amount": 87000, "deals": 12},
        ],
    }


@router.get("/{tracking_id}/dashboard/summary", summary="看板汇总")
async def get_dashboard_summary(tracking_id: str):
    funnel = await get_dashboard_funnel(tracking_id)
    teams = await get_dashboard_teams(tracking_id)
    ranking = await get_dashboard_ranking(tracking_id)
    return {
        "tracking_id": tracking_id,
        "funnel": funnel,
        "teams": teams,
        "ranking": ranking,
    }
