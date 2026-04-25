"""案例与趋势分析。"""

from __future__ import annotations

import json
import logging

from src.repositories.tracking import (
    get_diagnosis_health_score,
    get_solution_case,
    list_similar_solution_cases,
    list_snapshots,
    search_solution_cases,
)

from src.services.tracking_error_service import TrackingServiceError
from src.services.tracking_helper import _ser

logger = logging.getLogger(__name__)


async def search_tracking_cases(plan_name: str | None, skip: int, limit: int) -> dict:
    try:
        rows, total = await search_solution_cases(plan_name=plan_name, skip=skip, limit=limit)
        items = [
            {
                "case_id": str(row["id"]),
                "plan_name": row["plan_name"],
                "industry": row.get("industry_code", ""),
                "target_indicators": row.get("target_indicators", []),
                "achievement_rate": row.get("achievement_rate", 0),
                "indicator_changes": row.get("indicator_changes", []),
                "created_at": _ser(row["created_at"]),
            }
            for row in rows
        ]
        return {"items": items, "total": total}
    except Exception:
        logger.exception("搜索案例失败")
        return {"items": [], "total": 0}


async def list_similar_tracking_cases(indicators_csv: str, industry: str | None, limit: int) -> dict:
    indicator_list = [i.strip() for i in indicators_csv.split(",") if i.strip()]
    try:
        rows = await list_similar_solution_cases(
            indicator_list=indicator_list,
            industry=industry,
            limit=limit,
        )
        items = [
            {
                "case_id": str(row["id"]),
                "plan_name": row["plan_name"],
                "industry": row.get("industry_code", ""),
                "target_indicators": row.get("target_indicators", []),
                "achievement_rate": row.get("achievement_rate", 0),
                "indicator_changes": row.get("indicator_changes", []),
                "created_at": _ser(row["created_at"]),
            }
            for row in rows
        ]
        return {"items": items, "total": len(items)}
    except Exception:
        logger.exception("查询相似案例失败")
        return {"items": [], "total": 0}


async def get_tracking_case_detail(case_id: str) -> dict:
    try:
        row = await get_solution_case(int(case_id))
        if not row:
            raise TrackingServiceError(404, "案例不存在")
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
    except TrackingServiceError:
        raise
    except ValueError:
        raise TrackingServiceError(400, "无效的案例ID")
    except Exception as e:
        logger.exception("查询案例详情失败")
        raise TrackingServiceError(500, "查询失败，请稍后重试") from e


async def analyze_tracking_payload(tracking_id: str) -> dict:
    try:
        snapshots = await list_snapshots(tracking_id)
        if not snapshots:
            diagnosis_score = await get_diagnosis_health_score(tracking_id)
            return {
                "tracking_id": tracking_id,
                "trend": "no_data",
                "snapshots": 0,
                "analysis": "暂无快照数据",
                "latest_score": diagnosis_score,
                "first_score": diagnosis_score,
                "score_change": 0,
                "recommendations": ["建议先完成基线快照采集，再进行趋势分析", "建议提高采集频次，至少形成 2-3 个时间点的数据"],
                "risk_hint": "⚠ 数据采集不足，无法准确评估风险",
            }

        scores: list[float] = []
        for s in snapshots:
            sd = s["snapshot_data"] or {}
            if isinstance(sd, str):
                sd = json.loads(sd)
            try:
                scores.append(float(sd.get("health_score", 0)))
            except (TypeError, ValueError):
                scores.append(0.0)

        trend = (
            ("improving" if scores[-1] > scores[0] else "declining" if scores[-1] < scores[0] else "stable")
            if len(scores) >= 2
            else "insufficient_data"
        )
        score_change = round(scores[-1] - scores[0], 1) if len(scores) >= 2 else 0.0
        latest_score = round(scores[-1], 1) if scores else None
        first_score = round(scores[0], 1) if scores else None
        snapshot_count = len(snapshots)

        recent_change = round(scores[-1] - scores[-2], 1) if len(scores) >= 2 else 0.0
        recent3 = scores[-3:] if len(scores) >= 3 else scores
        recent_diffs = [recent3[i] - recent3[i - 1] for i in range(1, len(recent3))]
        rising_steps = sum(1 for d in recent_diffs if d > 0)
        falling_steps = sum(1 for d in recent_diffs if d < 0)

        avg_score = (sum(scores) / len(scores)) if scores else 0.0
        volatility = (sum((x - avg_score) ** 2 for x in scores) / len(scores)) ** 0.5 if len(scores) >= 2 else 0.0

        recommendations: list[str] = []
        if snapshot_count <= 1:
            recommendations.append("当前为基线阶段，建议尽快补充第 2-3 次快照，形成可比趋势")
        elif snapshot_count == 2:
            recommendations.append("已形成初步对比，建议保持固定周期采集，避免判断受偶然波动影响")
        elif 3 <= snapshot_count <= 4:
            recommendations.append("趋势进入成形期，建议按周复盘关键动作并记录干预前后变化")
        else:
            recommendations.append("样本已较充分，建议按月沉淀有效策略并复用到相似场景")

        if score_change <= -15:
            recommendations.append("整体评分显著下滑（>=15分），建议立即排查执行偏差并启动纠偏")
        elif score_change <= -5:
            recommendations.append("整体评分持续回落，建议优先处理负向变化最大的核心指标")
        elif score_change < 5:
            recommendations.append("总体变化不明显，建议聚焦 1-2 个高价值指标做针对性优化")
        elif score_change < 15:
            recommendations.append("整体评分稳步提升，建议固化当前有效动作并扩大覆盖范围")
        else:
            recommendations.append("整体评分显著提升（>=15分），建议沉淀为标准化执行模板")

        if snapshot_count >= 3:
            if rising_steps >= 2:
                recommendations.append("近 3 次快照连续向好，可适度提高目标阈值以释放增长空间")
            elif falling_steps >= 2:
                recommendations.append("近 3 次快照连续下行，建议缩小优化面并优先止损关键环节")
            elif recent_change > 0:
                recommendations.append("最近一次快照出现回升，建议继续观察 1-2 个周期确认趋势反转")
            elif recent_change < 0:
                recommendations.append("最近一次快照出现回落，建议复查近期新增动作对结果的影响")

        if snapshot_count >= 3:
            if volatility >= 8:
                recommendations.append("评分波动较大，建议统一采集口径并拆分活动/非活动时段观察")
            elif volatility <= 3:
                recommendations.append("评分波动较小，建议逐步提高优化目标，避免进入平台期")

        deduped: list[str] = []
        for item in recommendations:
            if item not in deduped:
                deduped.append(item)
        recommendations = deduped[:4] if deduped else ["继续保持当前优化策略", "关注核心指标变化趋势"]

        if snapshot_count < 2:
            risk_level, risk_hint = "low_confidence", "⚠ 数据采集不足，分析置信度低，请先补齐快照样本"
        elif score_change <= -15 or (snapshot_count >= 3 and falling_steps >= 2):
            risk_level, risk_hint = "high", "⚠ 高风险：评分持续下行，建议立即进行专项排查与纠偏"
        elif score_change < -5 or recent_change < 0:
            risk_level, risk_hint = "medium", "⚠ 中风险：近期存在下行信号，建议优先处理负向指标"
        elif volatility >= 8:
            risk_level, risk_hint = "medium", "⚠ 中风险：结果波动较大，建议稳定采集口径并分场景复盘"
        else:
            risk_level, risk_hint = "low", "✅ 当前风险整体可控，请继续保持稳定采集与复盘"

        return {
            "tracking_id": tracking_id,
            "trend": trend,
            "snapshots": snapshot_count,
            "first_score": first_score,
            "latest_score": latest_score,
            "score_change": score_change,
            "recent_change": recent_change,
            "volatility": round(volatility, 2),
            "risk_level": risk_level,
            "analysis": f"共采集 {snapshot_count} 次快照，评分趋势: {trend}",
            "recommendations": recommendations[:4],
            "risk_hint": risk_hint,
        }
    except Exception:
        logger.exception("效果分析失败")
        diag_score = await get_diagnosis_health_score(tracking_id)
        return {
            "tracking_id": tracking_id,
            "trend": "error",
            "snapshots": 0,
            "score_change": 0,
            "analysis": "分析失败",
            "latest_score": diag_score,
            "first_score": diag_score,
            "recommendations": ["分析服务暂不可用，请稍后重试", "建议先检查快照采集是否正常"],
            "risk_hint": "⚠ 分析服务异常，当前结果仅供参考",
        }


async def get_tracking_trends_payload(tracking_id: str) -> dict:
    try:
        rows = await list_snapshots(tracking_id)
        trends: dict[str, list] = {}
        timestamps: list = []
        for row in rows:
            sd = row["snapshot_data"] or {}
            if isinstance(sd, str):
                sd = json.loads(sd)
            timestamps.append(_ser(row["snapshot_at"]))
            for code, val in (sd.get("indicators") or {}).items():
                if code not in trends:
                    trends[code] = []
                trends[code].append(val.get("value") if isinstance(val, dict) else val)
        return {"tracking_id": tracking_id, "timestamps": timestamps, "indicators": trends}
    except Exception:
        logger.exception("查询趋势失败 tracking_id=%s", tracking_id)
        return {"tracking_id": tracking_id, "timestamps": [], "indicators": {}}
