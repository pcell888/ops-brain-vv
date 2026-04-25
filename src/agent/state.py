"""DiagnosisState — 诊断流程全局状态定义。"""

from __future__ import annotations

from typing import Literal, TypedDict


def _merge_messages(existing: list[dict] | None, new: list[dict] | None) -> list[dict]:
    if existing is None:
        existing = []
    if new is None:
        new = []
    return existing + new


class DiagnosisState(TypedDict):
    """诊断流程全局状态"""

    thread_id: str | None
    tenant_id: str
    store_id: str
    trigger_type: Literal["manual", "scheduled"]
    triggered_by: str | None
    selected_dimensions: list[str] | None
    selected_indicators: list[str] | None
    auth_token: str | None

    store_profile: dict | None
    crm_indicators: dict | None
    marketing_indicators: dict | None
    retention_indicators: dict | None
    efficiency_indicators: dict | None
    benchmarks: dict | None

    health_score: float | None
    dimension_scores: dict | None
    anomalies: list[dict] | None
    root_causes: list[dict] | None
    diagnosis_report: dict | None

    solution_plans: list[dict] | None
    pending_adopt_plan_id: str | None
    adopted_plan_ids: list[str] | None

    exec_tasks: list[dict] | None

    tracking_data: dict | None
    review_report: dict | None

    progress_messages: list[dict]
