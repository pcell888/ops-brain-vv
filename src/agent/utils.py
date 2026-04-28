"""agent 各节点共享的工具函数。"""

from __future__ import annotations

from src.core.exceptions import AppError
from src.repositories.tenant_registry import get_tenant_row


async def get_admin_accounts(
    profile: dict | None = None,
    *,
    tenant_id: str | None = None,
) -> list[str]:

    row = await get_tenant_row(tenant_id)
    if not row:
        raise AppError("租户未注册或已停用", tenant_id=tenant_id)

    uid = row.get("user_id")
    v = str(uid).strip() if uid is not None else ""
    if not v:
        raise AppError("tenant_registries.user_id 未配置，无法推送", tenant_id=tenant_id)
    return [v]


def slim_anomalies(anomalies: list[dict]) -> list[dict]:
    """精简异常列表，仅保留 LLM prompt 所需字段以降低 token 消耗。"""
    return [
        {
            "indicator_code": a.get("indicator_code"),
            "indicator_name": a.get("indicator_name"),
            "dimension": a.get("dimension"),
            "current_value": a.get("current_value"),
            "benchmark_avg": a.get("benchmark_avg"),
            "deviation_pct": a.get("deviation_pct"),
            "severity": a.get("severity"),
        }
        for a in anomalies
    ]


def slim_indicators(all_indicators: dict, anomalies: list[dict]) -> dict:
    """精简指标数据，仅保留异常相关维度和指标。"""
    anomaly_codes = {a["indicator_code"] for a in anomalies if a.get("indicator_code")}
    anomaly_dims = {a.get("dimension") for a in anomalies if a.get("dimension")}
    slim: dict = {}
    for dim, data in all_indicators.items():
        if dim not in anomaly_dims:
            continue
        indicators = data.get("indicators", {})
        if not isinstance(indicators, dict):
            continue
        slim_inds = {}
        for code, ind_data in indicators.items():
            if code in anomaly_codes:
                slim_inds[code] = {
                    "value": ind_data.get("value"),
                    "unit": ind_data.get("unit"),
                }
        if slim_inds:
            slim[dim] = {"indicators": slim_inds}
    return slim


def slim_store_profile(profile: dict) -> dict:
    """精简企业画像，仅保留 LLM prompt 所需字段。"""
    return {
        "store_name": profile.get("store_name"),
        "industry_code": profile.get("industry_code"),
        "customer_count": profile.get("customer_count"),
        "monthly_gmv": profile.get("monthly_gmv"),
        "employee_count": profile.get("employee_count"),
    }


def slim_benchmarks(benchmarks: dict, anomalies: list[dict]) -> dict:
    """精简基准数据，仅保留异常指标对应的基准，且只取 avg_value 以降低 token。"""
    anomaly_codes = {a["indicator_code"] for a in anomalies if a.get("indicator_code")}
    slim: dict = {}
    for code, bench in benchmarks.items():
        if code not in anomaly_codes:
            continue
        if isinstance(bench, dict):
            slim[code] = {"avg_value": bench.get("avg_value")}
        elif bench is not None:
            slim[code] = {"avg_value": bench}
    return slim


def slim_root_causes(root_causes: list[dict]) -> list[dict]:
    """精简根因列表，仅保留方案生成所需字段以降低 token。"""
    return [
        {
            "anomaly_indicator": rc.get("anomaly_indicator"),
            "cause": rc.get("cause"),
            "confidence": rc.get("confidence"),
            "recommendations": rc.get("recommendations"),
        }
        for rc in root_causes
    ]


def message_text(resp) -> str:
    """从 LangChain LLM 响应中提取纯文本 content。"""
    c = getattr(resp, "content", "")
    if isinstance(c, str):
        return c.strip()
    if isinstance(c, list):
        parts: list[str] = []
        for block in c:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "".join(parts).strip()
    return str(c).strip()
