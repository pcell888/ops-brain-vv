"""诊断进度构建逻辑 — 从 diagnosis.py 提取。"""

from __future__ import annotations

_DIAGNOSIS_STEPS = [
    ("collect_data", "数据采集"),
    ("diagnose", "诊断分析"),
    ("generate_solutions", "方案生成"),
]

_STEP_PERCENT_RANGE = {
    "collect_data": (0, 35),
    "diagnose": (35, 70),
    "generate_solutions": (70, 100),
}


def build_steps(messages: list[dict]) -> list[dict]:
    """将 progress_messages 按节点聚合成 steps 列表。"""
    steps: dict[str, dict] = {}
    for node, label in _DIAGNOSIS_STEPS:
        steps[node] = {
            "node": node,
            "label": label,
            "status": "pending",
            "percent_range": list(_STEP_PERCENT_RANGE[node]),
            "messages": [],
            "started_at": None,
            "completed_at": None,
        }

    current_node: str | None = None
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        content = str(msg.get("content", "")).strip()
        ts = msg.get("timestamp")
        pct = msg.get("percent")

        matched_node = None
        if pct is not None:
            try:
                pct_val = float(pct)
            except (TypeError, ValueError):
                pct_val = None
            if pct_val is not None:
                for node, (lo, hi) in _STEP_PERCENT_RANGE.items():
                    if lo <= pct_val <= hi:
                        matched_node = node
                        break
        if matched_node is None:
            matched_node = current_node

        if matched_node and matched_node in steps:
            current_node = matched_node
            step = steps[matched_node]
            if step["status"] == "pending":
                step["status"] = "running"
                step["started_at"] = ts
            if content:
                step["messages"].append({"text": content, "percent": pct, "timestamp": ts})

    for node, _ in _DIAGNOSIS_STEPS:
        step = steps[node]
        if step["messages"]:
            last_pct = step["messages"][-1].get("percent")
            if last_pct is not None:
                try:
                    _, hi = _STEP_PERCENT_RANGE[node]
                    if float(last_pct) >= hi:
                        step["status"] = "completed"
                        step["completed_at"] = step["messages"][-1].get("timestamp")
                except (TypeError, ValueError):
                    pass

    return [steps[node] for node, _ in _DIAGNOSIS_STEPS]
