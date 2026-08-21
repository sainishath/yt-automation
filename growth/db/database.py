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

        cursor = conn.cursor()

        # 1. Experiments table migrations
        cursor.execute("PRAGMA table_info(experiments)")
        existing_exp_cols = {row[1] for row in cursor.fetchall()}

        exp_col_defs = [
            ("secondary_metrics", "TEXT"),
            ("target_sample_size", "INTEGER DEFAULT 4"),
            ("source_type", "TEXT DEFAULT 'FIRST_PARTY_DISCOVERY'"),
            ("underlying_principle", "TEXT"),
            ("external_pattern_id", "TEXT"),
            ("external_prior_id", "TEXT"),
            ("source_channels", "TEXT"),
            ("transferability_score", "REAL"),
            ("transferability_classification", "TEXT"),
            ("prior_weight", "REAL"),
            ("provenance", "TEXT DEFAULT 'FIRST_PARTY'"),
            ("rationale", "TEXT"),
            ("decision", "TEXT"),
            ("decision_reason", "TEXT"),
            ("delta_percentage", "REAL"),
            ("control_count", "INTEGER DEFAULT 0"),
            ("treatment_count", "INTEGER DEFAULT 0"),
            ("control_median", "REAL"),
            ("treatment_median", "REAL"),
            ("started_at", "TIMESTAMP"),
            ("completed_at", "TIMESTAMP"),
            ("evaluated_at", "TIMESTAMP"),
            ("first_party_override_status", "TEXT"),
            ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        ]

        for col_name, col_type in exp_col_defs:
            if col_name not in existing_exp_cols:
                try:
                    cursor.execute(f"ALTER TABLE experiments ADD COLUMN {col_name} {col_type}")
                except Exception:
                    pass

        # 2. Jobs table migrations
        cursor.execute("PRAGMA table_info(jobs)")
        existing_job_cols = {row[1] for row in cursor.fetchall()}
        for col_name, col_type in [("topic_id", "TEXT"), ("arm_id", "TEXT")]:
            if col_name not in existing_job_cols:
                try:
                    cursor.execute(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_type}")
                except Exception:
                    pass

        # 3. Videos table migrations
        cursor.execute("PRAGMA table_info(videos)")
        existing_vid_cols = {row[1] for row in cursor.fetchall()}
        for col_name, col_type in [("arm_id", "TEXT"), ("topic_id", "TEXT")]:
            if col_name not in existing_vid_cols:
                try:
                    cursor.execute(f"ALTER TABLE videos ADD COLUMN {col_name} {col_type}")
                except Exception:
                    pass

        # 4. Create experiment_arms table if missing
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiment_arms (
                arm_id TEXT PRIMARY KEY,
                experiment_id TEXT NOT NULL,
                arm_type TEXT NOT NULL,
                name TEXT NOT NULL,
                definition TEXT NOT NULL,
                sample_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'ACTIVE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(experiment_id) REFERENCES experiments(experiment_id)
            )
        """)

        # 5. Ensure performance_snapshots has unique index for upserts
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_snapshots_video_window
            ON performance_snapshots(video_id, window_name)
        """)

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
