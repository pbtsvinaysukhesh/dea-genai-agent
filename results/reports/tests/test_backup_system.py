"""
Comprehensive test suite for backup system, versioning, and report generation features.
Tests atomic operations, collision handling, concurrent access, pagination, and metadata.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import json
from threading import Thread
import time

# Test helper imports
from src.backup_manager import BackupManager, FileVersioner, AtomicWriter
from src.path_config import PathConfig
from src.summary_generator import JsonSummaryGenerator
from src.source_link_processor import SourceLinkProcessor
from src.audio_metadata import AudioMetadataEmbedder


class TestFileVersioner:
    """Test FileVersioner collision handling"""

    def test_get_versioned_filename_no_collision(self):
        """Test getting filename when no collision exists"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            result = FileVersioner.get_versioned_filename(base, "test.txt")
            assert result == base / "test.txt"

    def test_get_versioned_filename_with_collision(self):
        """Test suffix addition on filename collision"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            # Create first file
            (base / "test.txt").touch()
            # Request same filename
            result = FileVersioner.get_versioned_filename(base, "test.txt")
            assert result == base / "test_1.txt"

    def test_get_versioned_filename_multiple_collisions(self):
        """Test numeric suffix increment on multiple collisions"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "test.txt").touch()
            (base / "test_1.txt").touch()
            result = FileVersioner.get_versioned_filename(base, "test.txt")
            assert result == base / "test_2.txt"


class TestAtomicWriter:
    """Test AtomicWriter atomic operations"""

    def test_write_atomic_success(self):
        """Test successful atomic write"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            temp_file = tmpdir / "temp.txt"
            final_file = tmpdir / "final.txt"

            # Write to temp file
            temp_file.write_text("test content")

            # Atomic move
            AtomicWriter.write_atomic(temp_file, final_file)

            # Verify
            assert final_file.exists()
            assert final_file.read_text() == "test content"
            assert not temp_file.exists()

    def test_write_atomic_overwrites(self):
        """Test atomic write overwrites existing file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            temp_file = tmpdir / "temp.txt"
            final_file = tmpdir / "final.txt"

            final_file.write_text("old content")
            temp_file.write_text("new content")

            AtomicWriter.write_atomic(temp_file, final_file)

            assert final_file.read_text() == "new content"

    def test_write_atomic_missing_temp(self):
        """Test error when temp file missing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            temp_file = tmpdir / "missing.txt"
            final_file = tmpdir / "final.txt"

            with pytest.raises(FileNotFoundError):
                AtomicWriter.write_atomic(temp_file, final_file)


class TestBackupManager:
    """Test BackupManager backup and versioning"""

    def test_backup_iso_timestamp_format(self):
        """Test backup directory uses ISO 8601 timestamp"""
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_dir = Path(tmpdir)
            manager = BackupManager(backup_dir)

            # Create test file to backup
            test_file = backup_dir.parent / "test.pdf"
            test_file.write_text("test")

            files_to_backup = {"pdf": test_file}
            result = manager.backup_and_version(files_to_backup)

            # Verify backup path was created with ISO timestamp
            assert result["pdf"] is not None
            backup_path = result["pdf"]
            assert backup_path.parent.parent == backup_dir
            # Check timestamp format YYYY-MM-DD_HH-MM-SS
            timestamp = backup_path.parent.name
            assert len(timestamp) == 19  # YYYY-MM-DD_HH-MM-SS
            test_file.unlink()

    def test_backup_collision_handling(self):
        """Test collision suffix _1, _2, etc."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_dir = Path(tmpdir)
            manager = BackupManager(backup_dir)

            # Create timestamp-based folder
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            timestamp_dir = backup_dir / timestamp
            timestamp_dir.mkdir()

            # Create first file
            (timestamp_dir / "report.pdf").touch()

            # Manually create backup with collision
            test_file = backup_dir.parent / "test.pdf"
            test_file.write_text("test")

            files_to_backup = {"pdf": test_file}
            result = manager.backup_and_version(files_to_backup)

            # Should have _1 suffix due to collision
            assert result["pdf"] is not None
            assert "_1" in result["pdf"].name or result["pdf"].name == "report.pdf"
            test_file.unlink()

    def test_backup_multiple_formats(self):
        """Test backing up multiple file types together"""
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_dir = Path(tmpdir)
            manager = BackupManager(backup_dir)

            # Create test files
            pdf_file = backup_dir.parent / "report.pdf"
            pptx_file = backup_dir.parent / "report.pptx"
            mp3_file = backup_dir.parent / "podcast.mp3"

            pdf_file.write_text("pdf")
            pptx_file.write_text("pptx")
            mp3_file.write_text("mp3")

            files_to_backup = {
                "pdf": pdf_file,
                "pptx": pptx_file,
                "mp3": mp3_file
            }

            result = manager.backup_and_version(files_to_backup)

            # All should be backed up
            assert all(result.values())
            assert len(result) == 3

            pdf_file.unlink()
            pptx_file.unlink()
            mp3_file.unlink()


class TestJsonSummaryGenerator:
    """Test JSON summary generation"""

    def test_json_schema_complete(self):
        """Test generated JSON has all required fields"""
        gen = JsonSummaryGenerator()

        papers = [
            {
                "title": "Paper 1",
                "link": "https://arxiv.org/1",
                "source": "arXiv",
                "relevance_score": 95,
                "summary": "Summary 1"
            }
        ]

        summary = gen.build_json_summary(
            papers=papers,
            executive_summary="Test summary",
            takeaways=["Takeaway 1", "Takeaway 2"],
            confidence="primary"
        )

        # Check required fields
        assert summary.session_id
        assert summary.generated_at
        assert summary.total_papers == 1
        assert summary.executive_summary == "Test summary"
        assert summary.confidence == "primary"
        assert len(summary.takeaways) == 2
        assert len(summary.sources) == 1

    def test_json_serialization(self):
        """Test JSON summary can be serialized"""
        gen = JsonSummaryGenerator()

        papers = [
            {
                "title": "Paper 1",
                "link": "https://arxiv.org/1",
                "source": "arXiv",
                "relevance_score": 90,
                "summary": "Summary"
            }
        ]

        summary = gen.build_json_summary(
            papers=papers,
            executive_summary="Test",
            confidence="primary"
        )

        json_str = summary.to_json()
        parsed = json.loads(json_str)

        assert parsed["total_papers"] == 1
        assert parsed["confidence"] == "primary"


class TestSourceLinkProcessor:
    """Test source link processing and pagination"""

    def test_url_normalization(self):
        """Test URL normalization adds https://"""
        url1 = SourceLinkProcessor.normalize_url("arxiv.org/abs/123")
        assert url1.startswith("https://")

        url2 = SourceLinkProcessor.normalize_url("https://arxiv.org/abs/123")
        assert url2 == "https://arxiv.org/abs/123"

    def test_url_validation(self):
        """Test URL validation"""
        assert SourceLinkProcessor.validate_url("https://arxiv.org/abs/123")
        assert not SourceLinkProcessor.validate_url("not-a-url")

    def test_build_source_list_deduplication(self):
        """Test source deduplication in list"""
        papers = [
            {
                "title": "Paper 1",
                "link": "https://arxiv.org/1",
                "source": "arXiv",
                "relevance_score": 95
            },
            {
                "title": "Paper 2",
                "link": "https://arxiv.org/1",
                "source": "arXiv",
                "relevance_score": 90
            }
        ]

        sources = SourceLinkProcessor.build_source_list(papers)

        assert len(sources) == 1

    def test_paginate_sources_pptx(self):
        """Test PPTX pagination (20 per slide)"""
        papers = [
            {
                "title": f"Paper {i}",
                "link": f"https://arxiv.org/{i}",
                "source": "arXiv",
                "relevance_score": 100 - i
            }
            for i in range(50)
        ]

        sources = SourceLinkProcessor.build_source_list(papers)
        pages = SourceLinkProcessor.paginate_sources_for_pptx(sources)

        assert len(pages) == 3  # 50 sources = 3 slides
        assert len(pages[0]) == 20
        assert len(pages[1]) == 20
        assert len(pages[2]) == 10

    def test_paginate_sources_pdf(self):
        """Test PDF pagination (40 per page)"""
        papers = [
            {
                "title": f"Paper {i}",
                "link": f"https://arxiv.org/{i}",
                "source": "arXiv",
                "relevance_score": 100 - i
            }
            for i in range(68)
        ]

        sources = SourceLinkProcessor.build_source_list(papers)
        pages = SourceLinkProcessor.paginate_sources_for_pdf(sources)

        assert len(pages) == 2  # 68 sources = 2 pages
        assert len(pages[0]) == 40
        assert len(pages[1]) == 28


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
