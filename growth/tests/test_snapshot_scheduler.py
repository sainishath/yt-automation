# -*- coding: utf-8 -*-
"""
test_snapshot_scheduler.py
--------------------------
Unit tests for the periodic snapshot scheduler.
"""

import gc
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from growth.db.database import init_db
from growth.db.models import GrowthRepository, ChannelModel, VideoModel
from growth.analytics.snapshot_scheduler import SnapshotScheduler


class TestSnapshotScheduler(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_sched.db"
        init_db(self.db_path)
        self.repo = GrowthRepository(self.db_path)
        self.repo.upsert_channel(ChannelModel("channel_a", "Chronos Shift", "@ChronosShift", "p1", "History"))

        # Insert a video published 30 hours ago
        old_time = (datetime.utcnow() - timedelta(hours=30)).strftime("%Y-%m-%d %H:%M:%S")
        self.repo.upsert_video(VideoModel(
            video_id="vid_30h_old",
            channel_id="channel_a",
            pipeline_id="alternate-history-shorts",
            title="Old Video",
            duration=45.0,
            upload_status="UPLOADED",
            privacy_status="public",
            review_status="APPROVED",
            strategy_version="v1.0",
            publish_timestamp=old_time
        ))

        self.scheduler = SnapshotScheduler(self.repo, dry_run=True)

    def tearDown(self):
        del self.scheduler
        del self.repo
        gc.collect()
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    def test_run_pending_snapshot_checks(self):
        res = self.scheduler.run_pending_snapshot_checks()
        self.assertEqual(res["status"], "success")
        self.assertGreater(res["collected_count"], 0)

        # Re-running immediately should skip all since they already exist
        res2 = self.scheduler.run_pending_snapshot_checks()
        self.assertEqual(res2["collected_count"], 0)
        self.assertGreater(res2["already_present_count"], 0)


if __name__ == "__main__":
    unittest.main()
