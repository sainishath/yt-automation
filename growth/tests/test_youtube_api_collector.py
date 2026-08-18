# -*- coding: utf-8 -*-
"""
test_youtube_api_collector.py
-----------------------------
Unit tests for the real YouTube API collector with mocked API responses.
"""

import gc
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from growth.db.database import init_db
from growth.db.models import GrowthRepository, ChannelModel, VideoModel
from growth.analytics.youtube_api_collector import YouTubeApiCollector


class TestYouTubeApiCollector(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_yt_api.db"
        init_db(self.db_path)
        self.repo = GrowthRepository(self.db_path)
        self.repo.upsert_channel(ChannelModel("channel_a", "Chronos Shift", "@ChronosShift", "p1", "History"))
        self.repo.upsert_video(VideoModel("vid_test", "channel_a", "p1", "Test", 45.0, "UPLOADED", "public", "APPROVED", "v1.0"))

        self.collector = YouTubeApiCollector(self.repo, dry_run=True)

    def tearDown(self):
        del self.collector
        del self.repo
        gc.collect()
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    def test_dry_run_statistics_fetch(self):
        stats = self.collector.fetch_video_statistics("fake_yt_id_123")
        self.assertEqual(stats["data_source"], "SIMULATION_FALLBACK")
        self.assertGreater(stats["views"], 0)

    def test_fetch_and_record_snapshot(self):
        snap = self.collector.fetch_and_record_snapshot("vid_test", "fake_yt_id_123", "24h", duration=45.0)
        self.assertEqual(snap.video_id, "vid_test")
        self.assertEqual(snap.window_name, "24h")

        snaps_in_db = self.repo.get_snapshots_for_video("vid_test")
        self.assertEqual(len(snaps_in_db), 1)
        self.assertEqual(snaps_in_db[0]["window_name"], "24h")


if __name__ == "__main__":
    unittest.main()
