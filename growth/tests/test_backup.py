# -*- coding: utf-8 -*-
"""
test_backup.py
--------------
Unit tests for the SQLite online hot backup and restoration module.
"""

import gc
import tempfile
import unittest
from pathlib import Path

from growth.db.database import init_db, get_db
from growth.db.backup import create_database_backup, list_backups, restore_database, BACKUP_DIR


class TestDatabaseBackup(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "source_test.db"
        init_db(self.db_path)
        with get_db(self.db_path) as conn:
            conn.execute("INSERT INTO channels (channel_id, name, handle, pipeline_id, content_category) VALUES ('ch_bk', 'Backup Ch', '@Backup', 'p1', 'History')")

    def tearDown(self):
        gc.collect()
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    def test_create_and_restore_backup(self):
        backup_file = create_database_backup(self.db_path, max_backups_to_keep=3)
        self.assertTrue(backup_file.exists())

        restored_db = Path(self.tmp_dir.name) / "restored_test.db"
        success = restore_database(backup_file, target_db_path=restored_db)
        self.assertTrue(success)

        # Verify data restored accurately
        with get_db(restored_db) as conn:
            row = conn.execute("SELECT name FROM channels WHERE channel_id = 'ch_bk'").fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["name"], "Backup Ch")

        # Cleanup created backup file
        try:
            backup_file.unlink()
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main()
