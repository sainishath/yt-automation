# -*- coding: utf-8 -*-
"""
test_db.py
----------
Unit tests for the SQLite growth database and models.
"""

import gc
import tempfile
import unittest
from pathlib import Path
from growth.db.database import init_db
from growth.db.models import (
    GrowthRepository, ChannelModel, VideoModel,
    VideoFeaturesModel, PerformanceSnapshotModel
)


class TestGrowthDatabase(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_growth.db"
        init_db(self.db_path)
        self.repo = GrowthRepository(self.db_path)

    def tearDown(self):
        del self.repo
        gc.collect()
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    def test_channel_upsert_and_retrieval(self):
        ch = ChannelModel(
            channel_id="channel_a",
            name="Chronos Shift",
            handle="@ChronosShiftAI",
            pipeline_id="alternate-history-shorts",
            content_category="Education/History",
            audience_definition="History & Speculative fiction fans",
            posting_frequency="3_shorts_per_week"
        )
        self.repo.upsert_channel(ch)
        res = self.repo.get_channel("channel_a")
        self.assertIsNotNone(res)
        self.assertEqual(res["name"], "Chronos Shift")
        self.assertEqual(res["handle"], "@ChronosShiftAI")

    def test_video_and_features_lifecycle(self):
        ch = ChannelModel("channel_a", "Chronos Shift", "@ChronosShift", "p1", "History")
        self.repo.upsert_channel(ch)

        vid = VideoModel(
            video_id="test_vid_001",
            channel_id="channel_a",
            pipeline_id="alternate-history-shorts",
            title="What If Alexandria Never Burned?",
            duration=47.5,
            upload_status="UPLOADED",
            privacy_status="public",
            review_status="APPROVED",
            strategy_version="v1.0",
            youtube_video_id="MBz1UuEKnmQ",
            youtube_url="https://youtu.be/MBz1UuEKnmQ",
            qa_score=17.0
        )
        self.repo.upsert_video(vid)
        v_res = self.repo.get_video("test_vid_001")
        self.assertIsNotNone(v_res)
        self.assertEqual(v_res["title"], "What If Alexandria Never Burned?")

        feat = VideoFeaturesModel(
            video_id="test_vid_001",
            topic_category="Ancient History",
            hook_type="Counterfactual Active Framing",
            hook_score=9.2,
            hook_text="If Ptolemy XIII hadn't burned the Library of Alexandria...",
            word_count=105,
            scene_count=8,
            avg_scene_duration=5.9,
            visual_change_rate=0.17,
            motion_type="Candidate A Linear Zoom",
            motion_intensity=0.08,
            caption_density=2.2,
            narrative_structure="8_beat_divergence"
        )
        self.repo.upsert_features(feat)
        f_res = self.repo.get_features("test_vid_001")
        self.assertIsNotNone(f_res)
        self.assertEqual(f_res["hook_score"], 9.2)

    def test_snapshots_insertion(self):
        ch = ChannelModel("channel_b", "Debate Protocol", "@DebateProtocol", "p2", "Debate")
        self.repo.upsert_channel(ch)
        vid = VideoModel("test_vid_002", "channel_b", "convo-shorts", "Can AI Feel Pain?", 42.0, "UPLOADED", "public", "APPROVED", "v1.0")
        self.repo.upsert_video(vid)

        snap = PerformanceSnapshotModel(
            video_id="test_vid_002",
            window_name="24h",
            views=1250,
            likes=145,
            comments=32,
            shares=18,
            subscribers_gained=8,
            watch_time_minutes=850.0,
            avg_view_duration_seconds=38.2,
            avg_percentage_viewed=90.9,
            views_per_hour=52.1,
            engagement_rate=0.156,
            subscriber_conversion_rate=0.0064,
            relative_performance_score=1.42,
            data_source="MOCK_ENGINE",
            data_freshness="FRESH"
        )
        snap_id = self.repo.insert_snapshot(snap)
        self.assertGreater(snap_id, 0)
        snaps = self.repo.get_snapshots_for_video("test_vid_002")
        self.assertEqual(len(snaps), 1)
        self.assertEqual(snaps[0]["views"], 1250)


if __name__ == "__main__":
    unittest.main()
