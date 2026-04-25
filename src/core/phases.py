"""阶段定义与进度计算 — 全流程单一信源。"""

from __future__ import annotations

PHASE_DIAGNOSIS = "diagnosis"
PHASE_ADOPTION = "adoption"
PHASE_EXECUTION = "execution"
PHASE_TRACKING = "tracking"
PHASE_COMPLETED = "completed"

_PHASE_NAME = {
    PHASE_DIAGNOSIS: "诊断",
    PHASE_ADOPTION: "采纳",
    PHASE_EXECUTION: "执行",
    PHASE_TRACKING: "追踪",
    PHASE_COMPLETED: "已完成",
}

_PHASE_OVERALL_RANGE = {
    PHASE_DIAGNOSIS: (0, 60),
    PHASE_ADOPTION: (60, 75),
    PHASE_EXECUTION: (75, 90),
    PHASE_TRACKING: (90, 99),
    PHASE_COMPLETED: (100, 100),
}

WORKFLOW_NODES = frozenset({
    "collect_data", "diagnose", "generate_solutions",
    "wait_adoption", "execute_plans", "track_effects",
})


def calc_overall_progress(phase: str, phase_progress: int) -> int:
    p = max(0, min(100, int(phase_progress)))
    lo, hi = _PHASE_OVERALL_RANGE.get(phase, (0, 100))
    if lo == hi:
        return lo
    return int(round(lo + (hi - lo) * (p / 100.0)))


def phase_name(phase: str) -> str:
    return _PHASE_NAME.get(phase, phase)


def infer_next_phase(phase: str, status: str) -> str | None:
    if status in ("failed", "not_found"):
        return None
    order = [PHASE_DIAGNOSIS, PHASE_ADOPTION, PHASE_EXECUTION, PHASE_TRACKING, PHASE_COMPLETED]
    try:
        idx = order.index(phase)
        return order[idx + 1] if idx + 1 < len(order) else None
    except ValueError:
        return None
