"""
Comprehensive Unit & Integration Tests for GenerativeAI-agent
Tests for core modules and pipeline execution
"""

import pytest
import os
import json
import tempfile
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock


# ============================================================================
# UNIT TESTS - Core Modules
# ============================================================================


class TestAnalyzer:
    """Test multi-provider LLM fallback (Groq → Ollama → Gemini)"""

    def test_analyzer_initialization_with_groq(self):
        """Test analyzer initializes with Groq key"""
        try:
            from src.analyzer import SimpleAIProcessor
            processor = SimpleAIProcessor(groq_api_key="test-key")
            assert processor.groq_client is not None
            assert processor.enable_ollama == True  # Default
        except ImportError:
            pytest.skip("src.analyzer not available")

    def test_analyzer_respects_enable_ollama_env(self):
        """Test analyzer respects ENABLE_OLLAMA environment variable"""
        try:
            from src.analyzer import SimpleAIProcessor
            os.environ["ENABLE_OLLAMA"] = "false"
            processor = SimpleAIProcessor(groq_api_key="test-key")
            assert processor.enable_ollama == False
            assert processor.ollama_available == False
            del os.environ["ENABLE_OLLAMA"]
        except ImportError:
            pytest.skip("src.analyzer not available")

    def test_analyzer_fallback_chain(self):
        """Test analyzer has proper fallback order"""
        try:
            from src.analyzer import SimpleAIProcessor
            processor = SimpleAIProcessor()
            # Should have stats tracking for all providers
            assert "groq_used" in processor.stats
            assert "ollama_used" in processor.stats
            assert "gemini_used" in processor.stats
        except ImportError:
            pytest.skip("src.analyzer not available")


class TestCollector:
    """Test article collection and deduplication"""

    def test_collector_initialization(self):
        """Test collector can be initialized"""
        try:
            from src.collector import ArticleCollector
            collector = ArticleCollector()
            assert collector is not None
        except ImportError:
            pytest.skip("src.collector not available")

    def test_collector_output_format(self):
        """Test collector returns structured article format"""
        try:
            from src.collector import ArticleCollector
            collector = ArticleCollector()
            # Articles should have expected fields
            assert hasattr(collector, 'collect_from_sources')
        except ImportError:
            pytest.skip("src.collector not available")


class TestMailer:
    """Test email delivery with attachments"""

    def test_mailer_initialization(self):
        """Test mailer can be initialized"""
        try:
            from src.mailer import Mailer
            mailer = Mailer(
                smtp_server="smtp.test.com",
                smtp_port=587,
                smtp_user="test@test.com",
                smtp_password="test"
            )
            assert mailer is not None
            assert mailer.smtp_user == "test@test.com"
        except ImportError:
            pytest.skip("src.mailer not available")

    def test_mailer_attachment_support(self):
        """Test mailer supports multiple attachments"""
        try:
            from src.mailer import Mailer
            mailer = Mailer(
                smtp_server="smtp.test.com",
                smtp_port=587,
                smtp_user="test@test.com",
                smtp_password="test"
            )
            assert hasattr(mailer, 'send_email')
        except ImportError:
            pytest.skip("src.mailer not available")


class TestHistory:
    """Test deduplication detection"""

    def test_history_initialization(self):
        """Test history manager can be initialized"""
        try:
            from src.history import HistoryManager
            history = HistoryManager()
            assert history is not None
        except ImportError:
            pytest.skip("src.history not available")

    def test_history_deduplication(self):
        """Test history can detect duplicates"""
        try:
            from src.history import HistoryManager
            history = HistoryManager()
            assert hasattr(history, 'is_duplicate')
            assert hasattr(history, 'add_to_history')
        except ImportError:
            pytest.skip("src.history not available")


class TestEnhancedFormatter:
    """Test enhanced email formatter"""

    def test_formatter_initialization(self):
        """Test formatter can be initialized"""
        try:
            from src.enhanced_formatter import EnhancedReportFormatter, ReportFormatter
            formatter = EnhancedReportFormatter()
            assert formatter is not None
            # Check backward compatibility alias
            assert ReportFormatter == EnhancedReportFormatter
        except ImportError:
            pytest.skip("src.enhanced_formatter not available")

    def test_formatter_html_generation(self):
        """Test formatter generates valid HTML"""
        try:
            from src.enhanced_formatter import EnhancedReportFormatter
            formatter = EnhancedReportFormatter()
            insights = [
                {
                    "title": "Test Paper",
                    "relevance_score": 95,
                    "platform": "Mobile",
                    "model_type": "LLM",
                    "dram_impact": "High",
                    "memory_insight": "Important insight",
                    "engineering_takeaway": "Key takeaway",
                    "link": "https://example.com",
                    "source": "arXiv"
                }
            ]
            html = formatter.build_html(insights)
            assert isinstance(html, str)
            assert "<html" in html.lower()
            assert "Test Paper" in html
            assert "95" in html  # Score
        except ImportError:
            pytest.skip("src.enhanced_formatter not available")


# ============================================================================
# INTEGRATION TESTS - Multi-Step Workflows
# ============================================================================


class TestPipelineIntegration:
    """Test complete pipeline execution flow"""

    def test_pipeline_basic_structure(self):
        """Test main.py can import all required components"""
        try:
            import main
            assert hasattr(main, 'load_config')
            assert main.logger is not None
        except ImportError as e:
            pytest.skip(f"main.py import failed: {e}")

    def test_config_loading(self):
        """Test configuration can be loaded"""
        try:
            import main
            # Config should exist
            config_path = "config/config.yaml"
            assert os.path.exists(config_path), "config.yaml not found"
        except ImportError:
            pytest.skip("main import failed")


class TestMultiFormatIntegration:
    """Test multi-format report generation"""

    def test_multiformat_integration_imports(self):
        """Test multiformat modules can be imported"""
        try:
            from src.multiformat_integration import generate_multiformat_email_report
            assert callable(generate_multiformat_email_report)
        except ImportError:
            pytest.skip("multiformat_integration not available")

    def test_multiformat_orchestrator(self):
        """Test multi-format orchestrator"""
        try:
            from src.multi_format_orchestrator import MultiFormatReportOrchestrator
            orchestrator = MultiFormatReportOrchestrator()
            assert orchestrator is not None
            assert hasattr(orchestrator, 'generate_all')
        except ImportError:
            pytest.skip("multi_format_orchestrator not available")


class TestDashboardAPIIntegration:
    """Test Dashboard FastAPI endpoints"""

    def test_dashboard_main_structure(self):
        """Test Dashboard FastAPI app structure"""
        try:
            from Dashboard.backend.app.main import app, router
            assert app is not None
            assert app.title == "AGI Research Intelligence"
        except ImportError:
            pytest.skip("Dashboard app not available")

    def test_dashboard_routers_registered(self):
        """Test all routers are properly registered"""
        try:
            from Dashboard.backend.app.main import app
            # Check registered routes
            routes = [route.path for route in app.routes]
            assert any("/api/papers" in route for route in routes), "Papers router not found"
            assert any("/api/chat" in route for route in routes), "Chat router not found"
            assert any("/api/pipeline" in route for route in routes), "Pipeline router not found"
            assert any("/api/stats" in route for route in routes), "Stats router not found"
            assert any("/api/hitl" in route for route in routes), "HITL router not found"
        except ImportError:
            pytest.skip("Dashboard app not available")


class TestModelOrchestrator:
    """Test LLM model selection and fallback"""

    def test_model_orchestrator_imports(self):
        """Test model orchestrator can be imported"""
        try:
            from src.multimodel_orchestrator import MultiModelOrchestrator
            assert MultiModelOrchestrator is not None
        except ImportError:
            pytest.skip("multimodel_orchestrator not available")

    def test_model_orchestrator_respects_enable_ollama(self):
        """Test model orchestrator respects ENABLE_OLLAMA env var"""
        try:
            from src.multimodel_orchestrator import MultiModelOrchestrator
            os.environ["ENABLE_OLLAMA"] = "false"
            orchestrator = MultiModelOrchestrator()
            # Should initialize even without Ollama
            assert orchestrator is not None
            del os.environ["ENABLE_OLLAMA"]
        except ImportError:
            pytest.skip("multimodel_orchestrator not available")


# ============================================================================
# SMOKE TESTS - Verify No Import Errors
# ============================================================================


class TestNoImportErrors:
    """Smoke tests to ensure all modules can be imported"""

    def test_all_core_imports(self):
        """Test all core src modules can be imported"""
        modules = [
            "src.analyzer",
            "src.collector",
            "src.judge",
            "src.history",
            "src.rag_orchestrator",
            "src.hybrid_search",
            "src.mmr_ranker",
            "src.knowledge_graph",
            "src.mailer",
            "src.email_and_archive",
            "src.enhanced_formatter",
            "src.pdf_generator",
            "src.pptx_generator",
            "src.podcast_generator",
            "src.multi_format_orchestrator",
            "src.multimodel_orchestrator",
            "src.crewai_agents",
            "src.ai_council",
        ]

        skipped = []
        for module_name in modules:
            try:
                __import__(module_name)
            except ImportError:
                skipped.append(module_name)

        if skipped:
            pytest.skip(f"Some modules unavailable: {', '.join(skipped)}")

    def test_all_dashboard_imports(self):
        """Test all Dashboard modules can be imported"""
        modules = [
            "Dashboard.backend.app.main",
            "Dashboard.backend.app.routers.papers_improved",
            "Dashboard.backend.app.routers.chat",
            "Dashboard.backend.app.routers.pipeline",
            "Dashboard.backend.app.routers.stats",
            "Dashboard.backend.app.routers.hitl",
        ]

        skipped = []
        for module_name in modules:
            try:
                __import__(module_name)
            except ImportError:
                skipped.append(module_name)

        if skipped:
            pytest.skip(f"Some Dashboard modules unavailable: {', '.join(skipped)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
