# -*- coding: utf-8 -*-
"""
test_analytics.py
-----------------
Unit tests for analytics collection, mock generation, and metric normalization.
"""

import gc
import tempfile
import unittest
from pathlib import Path
from growth.db.database import init_db
from growth.db.models import GrowthRepository, ChannelModel, VideoModel
from growth.analytics.collector import AnalyticsCollector
from growth.analytics.normalizer import calculate_channel_baseline, normalize_video_metrics


class TestAnalytics(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_analytics.db"
        init_db(self.db_path)
        self.repo = GrowthRepository(self.db_path)
        self.collector = AnalyticsCollector(self.repo, use_mock_engine=True)

        self.repo.upsert_channel(ChannelModel("channel_a", "Chronos Shift", "@ChronosShift", "p1", "History"))
        self.repo.upsert_video(VideoModel("vid_001", "channel_a", "p1", "Test Title", 45.0, "UPLOADED", "public", "APPROVED", "v1.0"))

    def tearDown(self):
        del self.collector
        del self.repo
        gc.collect()
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    def test_collect_snapshots(self):
        ids = self.collector.collect_snapshots_for_video("vid_001", duration=45.0, retention_factor=0.90)
        self.assertEqual(len(ids), 6) # 1h, 6h, 24h, 48h, 7d, 28d

        snaps = self.repo.get_snapshots_for_video("vid_001")
        self.assertEqual(len(snaps), 6)
        windows = [s["window_name"] for s in snaps]
        self.assertIn("1h", windows)
        self.assertIn("24h", windows)
        self.assertIn("28d", windows)

    def test_normalizer_and_summary(self):
        self.collector.collect_snapshots_for_video("vid_001", duration=45.0, retention_factor=0.92)
        summary = self.collector.get_video_normalized_summary("vid_001", "channel_a")
        self.assertIsNotNone(summary)
        self.assertIn("composite_performance_score", summary["normalized"])
        self.assertGreater(summary["normalized"]["composite_performance_score"], 0.0)


if __name__ == "__main__":
    unittest.main()
