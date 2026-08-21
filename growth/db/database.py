# -*- coding: utf-8 -*-
"""
database.py
-----------
SQLite connection manager and schema initializer for Content Intelligence.
"""

import sqlite3
from pathlib import Path
from contextlib import contextmanager

DEFAULT_DB_PATH = Path(__file__).parent.parent / "growth.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def init_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    """Initializes the database schema if tables do not exist and applies migrations."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())

        # Safe schema migration for existing experiments table
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(experiments)")
        existing_cols = {row[1] for row in cursor.fetchall()}

        col_defs = [
            ("secondary_metrics", "TEXT"),
            ("external_pattern_id", "TEXT"),
            ("external_prior_id", "TEXT"),
            ("source_channels", "TEXT"),
            ("transferability_score", "REAL"),
            ("transferability_classification", "TEXT"),
            ("prior_weight", "REAL"),
            ("provenance", "TEXT DEFAULT 'FIRST_PARTY'"),
            ("rationale", "TEXT"),
            ("decision", "TEXT"),
            ("delta_percentage", "REAL"),
            ("control_count", "INTEGER DEFAULT 0"),
            ("treatment_count", "INTEGER DEFAULT 0"),
            ("control_median", "REAL"),
            ("treatment_median", "REAL"),
            ("evaluated_at", "TIMESTAMP"),
            ("first_party_override_status", "TEXT"),
            ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        ]

        for col_name, col_type in col_defs:
            if col_name not in existing_cols:
                try:
                    cursor.execute(f"ALTER TABLE experiments ADD COLUMN {col_name} {col_type}")
                except Exception:
                    pass

        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_db(db_path: Path = DEFAULT_DB_PATH):
    """Context manager for obtaining a database connection with dictionary row access."""
    if not db_path.exists():
        init_db(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
