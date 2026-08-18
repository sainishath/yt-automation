# -*- coding: utf-8 -*-
"""
test_learning_engine.py
-----------------------
Unit tests for the Learning Engine, Autopsy Analyzer, and Weekly Report generation.
"""

import gc
import tempfile
import unittest
from pathlib import Path
from growth.db.database import init_db
from growth.db.models import GrowthRepository, ChannelModel, VideoModel, VideoFeaturesModel
from growth.analytics.collector import AnalyticsCollector
from growth.learning.learning_engine import LearningEngine


class TestLearningEngine(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_learning.db"
        init_db(self.db_path)
        self.repo = GrowthRepository(self.db_path)
        self.collector = AnalyticsCollector(self.repo, use_mock_engine=True)
        self.engine = LearningEngine(self.repo, self.collector)

        self.repo.upsert_channel(ChannelModel("channel_a", "Chronos Shift", "@ChronosShift", "p1", "History"))
        
        # Populate 2 sample videos with features & snapshots
        for i in range(1, 3):
            vid_id = f"vid_00{i}"
            self.repo.upsert_video(VideoModel(vid_id, "channel_a", "p1", f"Test Title {i}", 45.0, "UPLOADED", "public", "APPROVED", "v1.0"))
            self.repo.upsert_features(VideoFeaturesModel(vid_id, "History", "Hook", 9.0, "Hook text", 100, 8, 5.5, 0.18, "Motion", 0.08, 2.2, "8_beat"))
            self.collector.collect_snapshots_for_video(vid_id, duration=45.0, retention_factor=0.88 + (i * 0.02))

    def tearDown(self):
        del self.engine
        del self.collector
        del self.repo
        gc.collect()
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    def test_run_channel_learning_cycle(self):
        res = self.engine.run_channel_learning_cycle("channel_a")
        self.assertEqual(res["channel_id"], "channel_a")
        self.assertEqual(res["videos_count"], 2)
        self.assertEqual(len(res["autopsies"]), 2)
        self.assertGreater(len(res["recommended_topics"]), 0)
        self.assertIn("# 📊 Weekly Channel Growth Report", res["report_markdown"])


if __name__ == "__main__":
    unittest.main()
