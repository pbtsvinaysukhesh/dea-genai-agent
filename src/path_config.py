"""
Path Configuration Management

Centralizes configuration for report, backup, and podcast output directories.
Loads from environment variables with sensible defaults and ensures directories exist.
Uses singleton pattern for consistent access throughout the application.
"""

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class PathConfig:
    """Singleton configuration class for managing output paths."""

    _instance: Optional["PathConfig"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Only initialize once
        if PathConfig._initialized:
            return

        # Load paths from environment variables with defaults
        self.report_dir = self._resolve_path(
            os.getenv("REPORT_OUTPUT_DIR", "results/reports")
        )
        self.backup_dir = self._resolve_path(
            os.getenv("BACKUP_DIR", "results/backup")
        )
        self.podcast_dir = self._resolve_path(
            os.getenv("PODCAST_DIR", "results/podcasts")
        )

        # Podcast configuration
        self.podcast_greeting = os.getenv(
            "PODCAST_GREETING",
            "Hello Every One Good Evening & Good morning Welcome to Vinay DEA podcast"
        )
        self.podcast_intro_music = os.getenv("PODCAST_INTRO_MUSIC_PATH")
        self.podcast_outro_music = os.getenv("PODCAST_OUTRO_MUSIC_PATH")

        # Ensure all directories exist
        self._ensure_directories_exist()

        # Log configuration
        self._log_configuration()

        PathConfig._initialized = True

    def _resolve_path(self, path_str: str) -> Path:
        """
        Resolve path string to absolute Path object.
        Handles both relative and absolute paths.
        """
        path = Path(path_str)
        if not path.is_absolute():
            # Make relative to project root (where main.py is)
            project_root = Path(__file__).parent.parent
            path = project_root / path
        return path.resolve()

    def _ensure_directories_exist(self) -> None:
        """Create all required directories if they don't exist."""
        for directory in [self.report_dir, self.backup_dir, self.podcast_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")

    def _log_configuration(self) -> None:
        """Log the current configuration at startup."""
        logger.info("=" * 70)
        logger.info("PATH CONFIGURATION INITIALIZED")
        logger.info("=" * 70)
        logger.info(f"Report Output Directory:  {self.report_dir}")
        logger.info(f"Backup Directory:         {self.backup_dir}")
        logger.info(f"Podcast Output Directory: {self.podcast_dir}")
        logger.info(f"Podcast Greeting:         {self.podcast_greeting[:50]}...")
        if self.podcast_intro_music:
            logger.info(f"Podcast Intro Music:      {self.podcast_intro_music}")
        if self.podcast_outro_music:
            logger.info(f"Podcast Outro Music:      {self.podcast_outro_music}")
        logger.info("=" * 70)

    @classmethod
    def get_instance(cls) -> "PathConfig":
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton instance (mainly for testing)."""
        cls._instance = None
        cls._initialized = False

    def get_report_dir(self) -> Path:
        """Get report output directory."""
        return self.report_dir

    def get_backup_dir(self) -> Path:
        """Get backup directory."""
        return self.backup_dir

    def get_podcast_dir(self) -> Path:
        """Get podcast output directory."""
        return self.podcast_dir

    def get_podcast_greeting(self) -> str:
        """Get podcast greeting phrase."""
        return self.podcast_greeting

    def get_podcast_intro_music(self) -> Optional[Path]:
        """Get podcast intro music path if configured."""
        if self.podcast_intro_music:
            return Path(self.podcast_intro_music)
        return None

    def get_podcast_outro_music(self) -> Optional[Path]:
        """Get podcast outro music path if configured."""
        if self.podcast_outro_music:
            return Path(self.podcast_outro_music)
        return None
