"""Pydantic data models for API request/response and internal data transfer."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


# ── API Request / Response ──────────────────────────────────────


class DiagnosisRequest(BaseModel):
    tenant_id: str
    store_id: str = Field(default="", description="店铺ID，为空则诊断全企业")
    trigger_type: Literal["manual", "scheduled"] = "manual"
    triggered_by: str | None = None
    selected_dimensions: list[str] | None = Field(
        default=None,
        description="参与诊断的维度列表，如 ['crm','marketing']；为空则全量",
    )
    selected_indicators: list[str] | None = Field(
        default=None,
        description="参与诊断的指标代码列表，如 ['lead_conversion_rate']；为空则按维度全量",
    )
    auth_token: str | None = Field(
        default=None,
        description="前端透传的鉴权 token，用于访问业务侧 API",
    )

    @model_validator(mode="after")
    def normalize_store_id_vs_tenant(self):
        """勿将 tenant_id 与店铺 ID 混用：相等时视为未选店（全企业）。"""
        if self.store_id and self.store_id == self.tenant_id:
            return self.model_copy(update={"store_id": ""})
        return self


class DiagnosisStartResponse(BaseModel):
    thread_id: str
    ws_url: str
    already_running: bool = Field(
        default=False,
        description="为 True 时表示未新建任务，仅返回当前正在执行的诊断 thread_id",
    )


class AdoptPlanRequest(BaseModel):
    plan_id: str


# ── Indicator Models ────────────────────────────────────────────


class IndicatorValue(BaseModel):
    value: float
    unit: str = "%"
    direction: Literal["higher_is_better", "lower_is_better"] = "higher_is_better"
    raw_data: dict = Field(default_factory=dict)


class DimensionIndicators(BaseModel):
    tenant_id: str
    dimension: str
    period: str
    indicators: dict[str, IndicatorValue]


# ── Benchmark Models ────────────────────────────────────────────


class BenchmarkValue(BaseModel):
    avg_value: float
    median_value: float
    excellent_value: float  # P90


# ── Anomaly & Diagnosis ────────────────────────────────────────


class RootCauseBrief(BaseModel):
    """挂载在异常上的根因摘要"""

    cause: str
    evidence: str
    confidence: float = Field(ge=0, le=1)
    recommendations: list[str] = Field(default_factory=list)


class Anomaly(BaseModel):
    indicator_code: str
    indicator_name: str
    dimension: str
    current_value: float
    benchmark_avg: float
    benchmark_excellent: float
    deviation_pct: float
    severity: Literal["high", "medium", "low"]
    description: str
    root_cause: RootCauseBrief | None = None


class RootCause(BaseModel):
    anomaly_indicator: str
    cause: str
    evidence: str
    confidence: float = Field(ge=0, le=1)
    recommendations: list[str] = Field(default_factory=list)


class DimensionScore(BaseModel):
    score: float
    weight: float


class DimensionIndicatorScore(BaseModel):
    """单指标得分，用于报告「各维度指标得分」"""

    indicator_code: str
    indicator_name: str
    score: float
    current_value: float
    unit: str = "%"
    deviation_pct: float | None = None


class DimensionBenchmark(BaseModel):
    """该次诊断使用的单指标行业基准"""

    indicator_code: str
    indicator_name: str
    unit: str = "%"
    avg_value: float | None = None
    median_value: float | None = None
    excellent_value: float | None = None


class DiagnosisReport(BaseModel):
    tenant_id: str
    store_id: str
    generated_at: datetime
    health_score: float
    dimension_scores: dict[str, DimensionScore]
    dimension_indicator_scores: dict[str, list[DimensionIndicatorScore]] = Field(default_factory=dict)
    dimension_benchmarks: dict[str, list[DimensionBenchmark]] = Field(default_factory=dict)
    dimension_benchmarks_scores: dict[str, float] = Field(default_factory=dict)
    anomalies: list[Anomaly]
    root_causes: list[RootCause]
    summary: str


# ── Solution Plan Models ────────────────────────────────────────


class AutoAction(BaseModel):
    type: str
    config: dict


class SolutionPlan(BaseModel):
    plan_id: str
    plan_name: str
    description: str
    target_indicators: list[str]
    expected_improvement: dict[str, float]
    expected_roi: float = 0
    difficulty_score: float = Field(ge=1, le=10, default=5)
    urgency_score: float = Field(ge=1, le=10, default=5)
    priority_score: float = 0
    priority_level: Literal["high", "medium", "low"] = "medium"
    steps: list[dict] = Field(default_factory=list)
    auto_actions: list[AutoAction] = Field(default_factory=list)


# ── Execution Task Models ───────────────────────────────────────


class ExecTask(BaseModel):
    task_id: str = ""
    task_name: str
    description: str
    assignee_user_id: str | None = None
    assignee_dept_id: str | None = None
    assignee_user_name: str | None = None
    deadline: str | None = None
    deadline_at: str | None = None
    priority: Literal["high", "medium", "low"] = "medium"
    related_resources: dict = Field(default_factory=dict)
    status: str = "pending"


# ── Tracking & Review ──────────────────────────────────────────


class IndicatorChange(BaseModel):
    indicator_code: str
    before_value: float
    after_value: float
    change_pct: float
    improved: bool


class ReviewReport(BaseModel):
    overall_achievement_rate: float
    improved_indicator_count: int
    total_tracked_indicators: int
    indicator_changes: list[IndicatorChange]
    summary: str
    lessons_learned: list[str] = Field(default_factory=list)


# ── WebSocket Messages ─────────────────────────────────────────


class WSProgressMessage(BaseModel):
    type: str
    node: str | None = None
    message: str | None = None
    timestamp: str | None = None
    health_score: float | None = None
    anomaly_count: int | None = None
    dimension_scores: dict | None = None
    plans: list | None = None
