"""DiagnosisState — LangGraph 全局状态定义。"""

from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from langgraph.graph import add_messages


class DiagnosisState(TypedDict):
    """诊断流程全局状态"""

    # ── 输入参数 ──
    tenant_id: str
    store_id: str
    trigger_type: Literal["manual", "scheduled"]
    triggered_by: str | None
    selected_dimensions: list[str] | None
    selected_indicators: list[str] | None

    # ── 采集阶段产出 ──
    store_profile: dict | None
    crm_indicators: dict | None
    marketing_indicators: dict | None
    retention_indicators: dict | None
    efficiency_indicators: dict | None
    benchmarks: dict | None

    # ── 诊断阶段产出 ──
    health_score: float | None
    dimension_scores: dict | None
    anomalies: list[dict] | None
    root_causes: list[dict] | None
    diagnosis_report: dict | None

    # ── 方案阶段产出 ──
    solution_plans: list[dict] | None
    adopted_plan_ids: list[str] | None

    # ── 执行阶段产出 ──
    exec_tasks: list[dict] | None

    # ── 追踪阶段产出 ──
    tracking_data: dict | None
    review_report: dict | None

    # ── 进度推送 ──
    progress_messages: Annotated[list[dict], add_messages]
