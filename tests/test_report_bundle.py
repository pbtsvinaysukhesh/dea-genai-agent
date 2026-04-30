import sys
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _sample_sources():
    return [
        {
            "title": "Source One",
            "link": "https://example.com/one",
            "summary": "Short summary one",
            "full_text": "Full fetched content for source one with enough detail to form an excerpt.",
            "source": "Example Blog",
            "source_type": "blog",
            "scraped_at": "2026-03-26T10:00:00",
            "crawl_confidence": 0.9,
        },
        {
            "title": "Source Two",
            "link": "https://example.com/two",
            "summary": "Short summary two",
            "source": "Example Feed",
            "source_type": "rss",
            "collected_at": "2026-03-26T10:05:00",
        },
    ]


def _sample_insights():
    return [
        {
            "title": "Ranked Insight",
            "link": "https://example.com/one",
            "summary": "Insight summary",
            "relevance_score": 92,
            "platform": "Mobile",
            "model_type": "LLM",
            "dram_impact": "High",
            "memory_insight": "Cache reuse improves memory efficiency.",
            "engineering_takeaway": "Use cache-aware batching.",
            "source": "Example Blog",
        }
    ]


def test_report_bundle_preserves_source_appendix():
    from src.report_bundle import build_report_bundle

    bundle = build_report_bundle(_sample_insights(), all_sources=_sample_sources()).to_dict()

    assert bundle["metadata"]["total_sources"] == 2
    assert bundle["source_appendix"][0]["url"] == "https://example.com/one"
    assert "content_excerpt" in bundle["source_appendix"][0]


def test_email_formatter_includes_source_appendix_and_excerpt():
    from src.enhanced_formatter import EnhancedReportFormatter
    from src.report_bundle import build_report_bundle

    bundle = build_report_bundle(_sample_insights(), all_sources=_sample_sources()).to_dict()
    formatter = EnhancedReportFormatter()

    html = formatter.build_html(
        _sample_insights(),
        all_sources=_sample_sources(),
        report_bundle=bundle,
    )

    assert "Captured Source Appendix" in html
    assert "Fetched Content Excerpt" in html
    assert "https://example.com/one" in html


def test_multiformat_integration_attachment_list_includes_source_index():
    from src.multiformat_integration import MultiFormatReportIntegration

    output_dir = str(ROOT / "results" / "reports")
    expected = {
        str(Path(output_dir) / "report.pdf"),
        str(Path(output_dir) / "source_index.json"),
    }

    def fake_exists(path):
        return path in expected

    integration = MultiFormatReportIntegration(output_dir=output_dir)
    with patch("src.multiformat_integration.os.path.exists", side_effect=fake_exists):
        attachments = integration.get_attachment_paths()

    assert str(Path(output_dir) / "report.pdf") in attachments
    assert str(Path(output_dir) / "source_index.json") in attachments


def test_enhanced_formatter_uses_dea_news_heading():
    from src.enhanced_formatter import EnhancedReportFormatter
    from src.report_bundle import build_report_bundle

    bundle = build_report_bundle(_sample_insights(), all_sources=_sample_sources()).to_dict()
    formatter = EnhancedReportFormatter()

    html = formatter.build_html(
        _sample_insights(),
        all_sources=_sample_sources(),
        report_bundle=bundle,
    )

    assert "<title>DEA News</title>" in html
    assert "<h1>DEA News</h1>" in html
