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
    """Initializes the database schema if tables do not exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
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
