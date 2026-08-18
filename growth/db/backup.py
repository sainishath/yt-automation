# -*- coding: utf-8 -*-
"""
backup.py
---------
Automated Hot Backup and Disaster Recovery for the Growth SQLite Database.
Uses SQLite's online backup API for safe, non-blocking backups in WAL mode.
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from growth.db.database import DEFAULT_DB_PATH

BACKUP_DIR = Path(__file__).parent.parent / "backups"


def create_database_backup(db_path: Path = DEFAULT_DB_PATH, max_backups_to_keep: int = 10) -> Path:
    """
    Creates a hot, online backup of the SQLite database without locking active transactions.
    Prunes old backups beyond max_backups_to_keep.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at {db_path}")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"growth_backup_{ts}.db"

    source_conn = sqlite3.connect(str(db_path))
    dest_conn = sqlite3.connect(str(backup_file))

    try:
        with dest_conn:
            source_conn.backup(dest_conn, pages=100, progress=None)
        logging.info(f"[DB Backup] Successfully created hot backup: {backup_file.name}")
    finally:
        dest_conn.close()
        source_conn.close()

    # Prune older backups
    all_backups = sorted(BACKUP_DIR.glob("growth_backup_*.db"))
    if len(all_backups) > max_backups_to_keep:
        to_prune = all_backups[:-max_backups_to_keep]
        for p in to_prune:
            try:
                p.unlink()
                logging.info(f"[DB Backup] Pruned old backup: {p.name}")
            except Exception as e:
                logging.warning(f"Could not prune backup {p.name}: {e}")

    return backup_file


def list_backups() -> List[Path]:
    """Returns list of available backup files sorted by creation time."""
    if not BACKUP_DIR.exists():
        return []
    return sorted(BACKUP_DIR.glob("growth_backup_*.db"), reverse=True)


def restore_database(backup_file: Path, target_db_path: Path = DEFAULT_DB_PATH) -> bool:
    """
    Restores the database from a backup file.
    """
    if not backup_file.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_file}")

    source_conn = sqlite3.connect(str(backup_file))
    dest_conn = sqlite3.connect(str(target_db_path))

    try:
        with dest_conn:
            source_conn.backup(dest_conn)
        logging.info(f"[DB Restore] Successfully restored database from {backup_file.name}")
        return True
    finally:
        dest_conn.close()
        source_conn.close()
