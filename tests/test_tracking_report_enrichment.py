from src.core.tracking_report_enrichment import needs_llm_enrichment


def test_needs_llm_enrichment_for_template_like_report():
    report = {
        "summary": "追踪期间共采集 21 次快照",
        "recommendations": ["继续保持当前优化策略", "关注核心指标变化趋势"],
        "sections": [{"title": "复盘总结", "content": "追踪期间共采集 21 次快照"}],
    }
    assert needs_llm_enrichment(report) is True


def test_no_enrichment_when_indicator_analysis_exists():
    report = {
        "summary": "总体达成率较好",
        "recommendations": ["建议A", "建议B", "建议C"],
        "indicator_analysis": [
            {"indicator_code": "lead_conversion_rate", "trend": "持续改善", "analysis": "转化稳定提升"}
        ],
    }
    assert needs_llm_enrichment(report) is False

