"""
Backup Manager - Atomic file operations and versioning

Handles backup and versioning of report files with collision detection.
Uses atomic rename operations for thread-safe file operations.
Implements ISO 8601 timestamp-based versioning (YYYY-MM-DD_HH-MM-SS).
"""

import os
import logging
import shutil
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from threading import Lock

logger = logging.getLogger(__name__)


class FileVersioner:
    """Handles collision detection and filename versioning."""

    @staticmethod
    def get_versioned_filename(
        base_path: Path, existing_filename: str
    ) -> Path:
        """
        Get a versioned filename that doesn't collide with existing files.

        Args:
            base_path: Directory to check for collisions
            existing_filename: The filename to version

        Returns:
            Path object with collision-free filename
        """
        if not base_path.exists():
            return base_path / existing_filename

        # Check if file already exists
        full_path = base_path / existing_filename
        if not full_path.exists():
            return full_path

        # File exists, need to add numeric suffix
        stem = Path(existing_filename).stem
        suffix = Path(existing_filename).suffix
        counter = 1

        while True:
            versioned_name = f"{stem}_{counter}{suffix}"
            versioned_path = base_path / versioned_name
            if not versioned_path.exists():
                return versioned_path
            counter += 1


class AtomicWriter:
    """Safely writes files atomically using temp-then-rename pattern."""

    @staticmethod
    def write_atomic(temp_path: Path, final_path: Path) -> None:
        """
        Atomically move temp file to final destination.

        Uses atomic rename operation to prevent partial writes.
        Should only be called after file is fully written to temp location.

        Args:
            temp_path: Path to temporary file (must exist)
            final_path: Desired final path
        """
        if not temp_path.exists():
            raise FileNotFoundError(f"Temp file not found: {temp_path}")

        # Ensure parent directory exists
        final_path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic rename operation (os.rename on Windows/Unix)
        try:
            # On Windows, os.rename will fail if destination exists, so remove it first
            if final_path.exists():
                final_path.unlink()
            os.rename(str(temp_path), str(final_path))
            logger.debug(f"Atomic rename: {temp_path} -> {final_path}")
        except OSError as e:
            logger.error(f"Atomic write failed: {e}")
            # Clean up temp file on failure
            if temp_path.exists():
                temp_path.unlink()
            raise


class BackupManager:
    """
    Manages atomic backup and versioning of report files.

    Features:
    - ISO 8601 timestamp-based backup folders (YYYY-MM-DD_HH-MM-SS)
    - Collision handling with numeric suffixes (_1, _2, etc.)
    - Atomic file operations to prevent data loss
    - Thread-safe via internal locking
    - Comprehensive logging of all backup operations
    """

    def __init__(self, backup_dir: Path):
        """
        Initialize BackupManager.

        Args:
            backup_dir: Root directory for backups
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def backup_and_version(
        self,
        file_paths: Dict[str, Path],
        extensions: Optional[List[str]] = None
    ) -> Dict[str, Optional[Path]]:
        """
        Backup existing files before versioning.

        Only backs up files that exist. Returns mapping of original paths
        to backup paths.

        Args:
            file_paths: Dict of {file_type: Path} for files to backup
            extensions: List of extensions to backup (e.g., ['.pdf', '.pptx'])
                       If None, backs up all files in file_paths

        Returns:
            Dict mapping file_type to backup path (or None if not backed up)
        """
        backup_results = {}

        with self._lock:
            for file_type, file_path in file_paths.items():
                path = Path(file_path)

                # Check if we should process this file
                if extensions and path.suffix not in extensions:
                    backup_results[file_type] = None
                    continue

                # Only backup if file exists
                if not path.exists():
                    backup_results[file_type] = None
                    continue

                try:
                    backup_path = self._backup_single_file(path)
                    backup_results[file_type] = backup_path
                    logger.info(
                        f"Backed up {file_type}: {path} -> {backup_path}"
                    )
                except Exception as e:
                    logger.error(f"Failed to backup {file_type}: {e}")
                    backup_results[file_type] = None

        return backup_results

    def _backup_single_file(self, file_path: Path) -> Path:
        """
        Backup a single file to versioned backup directory.

        Args:
            file_path: Path to file to backup

        Returns:
            Path to backup location
        """
        # Create timestamp-based backup folder
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_folder = self.backup_dir / timestamp

        # Get collision-free filename
        backup_path = FileVersioner.get_versioned_filename(
            backup_folder, file_path.name
        )

        # Ensure backup folder exists
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy file to backup location
        shutil.copy2(str(file_path), str(backup_path))

        logger.debug(f"Created backup: {file_path} -> {backup_path}")
        return backup_path

    def get_temp_file_path(self, output_dir: Path, extension: str) -> Path:
        """
        Get a safe temporary file path for generation.

        Args:
            output_dir: Directory where output will go
            extension: File extension (e.g., '.pdf', '.mp3')

        Returns:
            Path to temporary file
        """
        temp_filename = f".tmp.{uuid.uuid4()}{extension}"
        temp_path = output_dir / temp_filename
        return temp_path

    def finalize_file(
        self,
        temp_path: Path,
        final_path: Path,
        backup_dir: Optional[Path] = None
    ) -> Path:
        """
        Finalize file by atomically renaming temp to final.

        Optionally backs up existing file first.

        Args:
            temp_path: Path to temporary file
            final_path: Desired final path
            backup_dir: If provided, backup existing final_path before rename

        Returns:
            Final path where file was moved
        """
        with self._lock:
            # Backup existing file if requested
            if backup_dir and final_path.exists():
                backup_path = self._backup_single_file(final_path)
                logger.info(f"Backed up before finalization: {final_path} -> {backup_path}")

            # Atomically move temp to final
            AtomicWriter.write_atomic(temp_path, final_path)

        return final_path

    def cleanup_temp_file(self, temp_path: Path) -> None:
        """
        Clean up temporary file if it exists.

        Args:
            temp_path: Path to temporary file to delete
        """
        try:
            if temp_path.exists():
                temp_path.unlink()
                logger.debug(f"Cleaned up temp file: {temp_path}")
        except OSError as e:
            logger.warning(f"Failed to clean up temp file {temp_path}: {e}")

    def get_backup_info(self) -> Dict:
        """
        Get information about current backups.

        Returns:
            Dict with backup statistics
        """
        if not self.backup_dir.exists():
            return {"total_backups": 0, "backup_folders": []}

        backup_folders = [
            d.name for d in self.backup_dir.iterdir()
            if d.is_dir()
        ]
        backup_folders.sort(reverse=True)  # Latest first

        backup_files = {}
        for folder in backup_folders[:5]:  # Show last 5 backups
            folder_path = self.backup_dir / folder
            files = [f.name for f in folder_path.iterdir() if f.is_file()]
            backup_files[folder] = files

        return {
            "total_backups": len(backup_folders),
            "backup_folders": backup_folders[:10],
            "recent_backups": backup_files,
        }
