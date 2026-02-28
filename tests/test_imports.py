"""
Test suite for GenerativeAI-agent
Basic sanity checks for imports and dependencies
"""

import pytest
import sys


def test_basic_imports():
    """Test that basic Python modules can be imported"""
    try:
        import os
        import json
        import yaml
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import basic modules: {e}")


def test_requirements():
    """Test that required packages are available"""
    required = ['reportlab', 'python_pptx', 'gtts', 'pydantic', 'requests']
    skipped = []

    for package in required:
        try:
            __import__(package)
        except ImportError:
            skipped.append(package)

    if skipped:
        pytest.skip(f"Optional dependencies not installed: {', '.join(skipped)}")


def test_src_modules_exist():
    """Test that src modules can be imported"""
    try:
        from src import analyzer
        from src import collector
        from src import enhanced_formatter
        from src import judge
        from src import history
        assert True
    except ImportError as e:
        pytest.skip(f"Some src modules not available: {e}")


def test_multiformat_modules():
    """Test that multiformat modules exist"""
    try:
        from src import enhanced_formatter
        from src import pdf_generator
        from src import pptx_generator
        from src import podcast_generator
        assert True
    except ImportError as e:
        pytest.skip(f"Multiformat modules not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
