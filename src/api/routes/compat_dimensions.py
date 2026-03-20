"""前端兼容层 — /custom-dimensions 系列接口。

基于 INDICATOR_META / DEFAULT_DIMENSION_WEIGHTS 生成系统内置维度配置，
供前端 useDimensionConfig hook 使用。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from src.core.calculator import (
    INDICATOR_META,
    DEFAULT_DIMENSION_WEIGHTS,
    DEFAULT_BENCHMARKS,
    ALL_DIMENSIONS,
)

router = APIRouter(prefix="/custom-dimensions", tags=["维度配置(兼容层)"])

_DIMENSION_DISPLAY_NAMES: dict[str, str] = {
    "crm": "CRM共享",
    "marketing": "营销效果",
    "retention": "客户留存",
    "efficiency": "运营效率",
}

_DIMENSION_ICONS: dict[str, str] = {
    "crm": "🤝",
    "marketing": "📣",
    "retention": "👥",
    "efficiency": "⚙️",
}

_DIMENSION_COLORS: dict[str, str] = {
    "crm": "#3b82f6",
    "marketing": "#f59e0b",
    "retention": "#10b981",
    "efficiency": "#8b5cf6",
}


def _build_system_dimensions() -> list[dict]:
    """从 INDICATOR_META 构建系统维度配置列表。"""
    dim_metrics: dict[str, list[dict]] = {}
    for code, meta in INDICATOR_META.items():
        dim = meta["dimension"]
        bench = DEFAULT_BENCHMARKS.get(code, {})
        avg = bench.get("avg_value", 0) if isinstance(bench, dict) else 0
        excellent = bench.get("excellent_value", 0) if isinstance(bench, dict) else 0
        median = bench.get("median_value", avg) if isinstance(bench, dict) else avg

        dim_metrics.setdefault(dim, []).append({
            "name": code,
            "display_name": meta["name"],
            "unit": meta["unit"],
            "description": meta.get("drill_desc", ""),
            "data_source": "api",
            "direction": meta.get("direction", "higher_is_better"),
            "benchmark": {
                "avg": avg,
                "excellent": excellent,
                "median": median,
            },
        })

    dimensions = []
    for dim in ALL_DIMENSIONS:
        weight = DEFAULT_DIMENSION_WEIGHTS.get(dim, 0.25)
        metrics = dim_metrics.get(dim, [])
        dimensions.append({
            "id": f"sys_{dim}",
            "name": dim,
            "display_name": _DIMENSION_DISPLAY_NAMES.get(dim, dim),
            "description": f"{_DIMENSION_DISPLAY_NAMES.get(dim, dim)}维度",
            "icon": _DIMENSION_ICONS.get(dim, "📊"),
            "color": _DIMENSION_COLORS.get(dim, "#6b7280"),
            "weight": weight,
            "is_system": True,
            "enabled": True,
            "metrics_config": {"metrics": metrics},
            "rules_config": {"rules": []},
            "tasks_config": {"tasks": []},
            "created_at": None,
            "updated_at": None,
        })
    return dimensions


_SYSTEM_DIMENSIONS = _build_system_dimensions()


@router.get("/all-dimensions", summary="获取所有可用维度")
async def get_all_dimensions(
    enterprise_id: str | None = Query(default=None),
):
    """兼容前端 GET /custom-dimensions/all-dimensions?enterprise_id=。

    返回系统内置维度 + 自定义维度（当前仅系统维度）。
    """
    return {
        "system_dimensions": _SYSTEM_DIMENSIONS,
        "custom_dimensions": [],
        "all_dimensions": _SYSTEM_DIMENSIONS,
    }
