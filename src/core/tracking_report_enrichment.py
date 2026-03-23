from __future__ import annotations


def needs_llm_enrichment(report: dict | None) -> bool:
    data = report or {}
    if not isinstance(data, dict):
        return True

    indicator_analysis = data.get("indicator_analysis")
    if isinstance(indicator_analysis, list) and indicator_analysis:
        return False

    recs = data.get("recommendations")
    rec_count = len(recs) if isinstance(recs, list) else 0
    sections = data.get("sections")
    sec_count = len(sections) if isinstance(sections, list) else 0
    summary = str(data.get("summary") or "").strip()

    looks_like_template_summary = summary.startswith("追踪期间共采集")
    looks_like_template_recs = rec_count <= 2
    looks_like_template_sections = sec_count <= 1
    return looks_like_template_summary and looks_like_template_recs and looks_like_template_sections

