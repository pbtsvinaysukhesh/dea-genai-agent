#!/usr/bin/env python3
"""
Legacy File Migration Script

Migrates existing reports from results/reports/ directory into the new backup
structure using ISO 8601 timestamps. Creates dated backup folders and moves
existing files safely.

This script is idempotent - safe to run multiple times without duplicating
migrations or losing data.

Usage:
    python scripts/migrate_existing_reports.py
"""

import os
import shutil
import logging
from pathlib import Path
from datetime import datetime
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def migrate_existing_reports(
    reports_dir: str = "results/reports",
    backup_dir: str = "results/backup"
):
    """
    Migrate existing reports from reports/ to backup/ using ISO 8601 timestamps.

    Args:
        reports_dir: Directory containing existing reports
        backup_dir: Root backup directory
    """
    reports_path = Path(reports_dir)
    backup_path = Path(backup_dir)

    logger.info("=" * 70)
    logger.info("LEGACY FILE MIGRATION - Initializing...")
    logger.info("=" * 70)

    # Check if reports directory exists
    if not reports_path.exists():
        logger.info(f"Reports directory does not exist: {reports_path}")
        logger.info("No migration needed.")
        return

    # List existing files
    existing_files = list(reports_path.glob("*"))
    existing_files = [f for f in existing_files if f.is_file()]

    if not existing_files:
        logger.info(f"No existing files found in {reports_path}")
        logger.info("No migration needed.")
        return

    logger.info(f"Found {len(existing_files)} file(s) to migrate:")
    for file in existing_files:
        logger.info(f"  - {file.name} ({file.stat().st_size} bytes)")

    # Create migration timestamp (use current time for initial migration)
    migration_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    migration_backup_dir = backup_path / migration_timestamp

    # Ensure backup directory exists
    migration_backup_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"\nCreating backup directory: {migration_backup_dir}")

    # Track migration
    migration_log = {
        "migration_timestamp": migration_timestamp,
        "migration_date": datetime.now().isoformat(),
        "files_migrated": [],
        "files_skipped": [],
        "errors": []
    }

    migrated_count = 0
    skipped_count = 0

    # Migrate each file
    for file in existing_files:
        try:
            dest_path = migration_backup_dir / file.name

            # Skip if destination already exists
            if dest_path.exists():
                logger.warning(f"Skipping {file.name} - destination exists")
                migration_log["files_skipped"].append({
                    "file": file.name,
                    "reason": "destination_exists"
                })
                skipped_count += 1
                continue

            # Move file
            shutil.move(str(file), str(dest_path))
            logger.info(f"✓ Migrated: {file.name} -> {migration_backup_dir.name}/")

            migration_log["files_migrated"].append({
                "file": file.name,
                "size": file.stat().st_size,
                "destination": str(dest_path)
            })
            migrated_count += 1

        except Exception as e:
            logger.error(f"✗ Migration failed for {file.name}: {e}")
            migration_log["errors"].append({
                "file": file.name,
                "error": str(e)
            })

    # Save migration log
    log_path = backup_path / "migration_log.json"
    try:
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(migration_log, f, indent=2)
        logger.info(f"\nMigration log saved: {log_path}")
    except Exception as e:
        logger.error(f"Failed to save migration log: {e}")

    # Summary
    logger.info("=" * 70)
    logger.info("MIGRATION SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Files migrated:  {migrated_count}")
    logger.info(f"Files skipped:   {skipped_count}")
    logger.info(f"Errors:          {len(migration_log['errors'])}")
    logger.info(f"Backup location: {migration_backup_dir}")
    logger.info("=" * 70)

    if migrated_count > 0:
        logger.info("✓ Migration completed successfully!")
    elif skipped_count > 0:
        logger.info("ℹ No new files to migrate (already migrated)")
    else:
        logger.warning("⚠ No files were migrated")

    return migration_log


def check_migration_status(backup_dir: str = "results/backup"):
    """
    Check the status of previous migrations.

    Args:
        backup_dir: Root backup directory
    """
    backup_path = Path(backup_dir)
    log_path = backup_path / "migration_log.json"

    if not log_path.exists():
        logger.info("No migration log found")
        return

    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            log = json.load(f)

        logger.info("\nPrevious Migration Status:")
        logger.info(f"  Migration date: {log.get('migration_date', 'Unknown')}")
        logger.info(f"  Files migrated: {len(log.get('files_migrated', []))}")
        logger.info(f"  Files skipped:  {len(log.get('files_skipped', []))}")
        logger.info(f"  Errors:         {len(log.get('errors', []))}")

    except Exception as e:
        logger.error(f"Failed to read migration log: {e}")


if __name__ == "__main__":
    import sys

    # Check for --status flag
    if "--status" in sys.argv:
        check_migration_status()
    else:
        # Perform migration
        migrate_existing_reports()
        # Show status
        check_migration_status()
