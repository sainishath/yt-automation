# -*- coding: utf-8 -*-
"""
test_production_matrix.py
-------------------------
Production Hardening Test Matrix covering negative tests, failure recovery,
channel isolation, duplicate prevention, and data integrity.
"""

import gc
import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime

from growth.db.database import init_db, get_db
from growth.db.models import GrowthRepository, ChannelModel, VideoModel, PerformanceSnapshotModel
from growth.channels.channel_identity_check import verify_channel_identity, enforce_channel_match
from growth.topic_engine.deduplicator import is_duplicate_topic
from growth.topic_engine.topic_lifecycle import TopicLifecycleManager
from growth.experiments.experiment_manager import ExperimentManager
from growth.quality.quality_scorer import evaluate_content_quality


class TestProductionMatrix(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_matrix.db"
        init_db(self.db_path)
        self.repo = GrowthRepository(self.db_path)
        self.repo.upsert_channel(ChannelModel("channel_a", "Chronos Shift", "@ChronosShift", "p1", "History"))
        self.repo.upsert_channel(ChannelModel("channel_b", "Debate Protocol", "@DebateProtocol", "p2", "Debate"))

    def tearDown(self):
        del self.repo
        gc.collect()
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    def test_channel_isolation_mismatch_hard_fail(self):
        """Verify that channel mismatch halts immediately with fatal RuntimeError."""
        with self.assertRaises(RuntimeError):
            enforce_channel_match(
                pipeline_name="pipeline1",
                authenticated_channel_id="UC_UNEXPECTED_CHANNEL",
                authenticated_channel_name="Wrong Channel"
            )

    def test_duplicate_snapshot_upsert_idempotency(self):
        """Verify that inserting duplicate snapshots for (video_id, window_name) updates rather than duplicates."""
        self.repo.upsert_video(VideoModel("vid_idemp", "channel_a", "p1", "Idempotent Video", 45.0, "UPLOADED", "public", "APPROVED", "v1.0"))

        snap1 = PerformanceSnapshotModel(
            video_id="vid_idemp", window_name="24h", views=1000, likes=100, comments=10, shares=5,
            subscribers_gained=2, watch_time_minutes=600.0, avg_view_duration_seconds=36.0,
            avg_percentage_viewed=80.0, views_per_hour=41.6, engagement_rate=0.115,
            subscriber_conversion_rate=0.002, relative_performance_score=1.0,
            data_source="REAL_YOUTUBE_ANALYTICS", data_freshness=datetime.utcnow().isoformat()
        )
        self.repo.insert_snapshot(snap1)

        # Re-insert with updated views
        snap2 = PerformanceSnapshotModel(
            video_id="vid_idemp", window_name="24h", views=1500, likes=150, comments=15, shares=8,
            subscribers_gained=4, watch_time_minutes=900.0, avg_view_duration_seconds=36.0,
            avg_percentage_viewed=80.0, views_per_hour=62.5, engagement_rate=0.115,
            subscriber_conversion_rate=0.0026, relative_performance_score=1.1,
            data_source="REAL_YOUTUBE_ANALYTICS", data_freshness=datetime.utcnow().isoformat()
        )
        self.repo.insert_snapshot(snap2)

        snaps = self.repo.get_snapshots_for_video("vid_idemp")
        self.assertEqual(len(snaps), 1)
        self.assertEqual(snaps[0]["views"], 1500)

    def test_topic_deduplication_jaccard_filtering(self):
        """Verify that near-duplicate topic candidates are flagged."""
        existing = ["What if the Roman Empire never fell?", "What if Napoleon won at Waterloo?"]
        is_dup, match = is_duplicate_topic("What if Roman Empire never fell?", existing)
        self.assertTrue(is_dup)
        self.assertEqual(match, "What if the Roman Empire never fell?")

        is_dup2, _ = is_duplicate_topic("What if Alexander the Great lived to 80?", existing)
        self.assertFalse(is_dup2)

    def test_experiment_sample_size_guard(self):
        """Verify that experiments with N < 4 return INSUFFICIENT_DATA."""
        mgr = ExperimentManager()
        res = mgr.evaluate_experiment("EXP_A_HOOK_01", [80.0, 82.0], [90.0, 92.0])
        self.assertEqual(res["status"], "INSUFFICIENT_DATA")
        self.assertEqual(res["confidence"], "LOW")

    def test_quality_scorer_preserves_qa_gate(self):
        """Verify that high content scores do not bypass a failed QA gate."""
        feat = {"hook_score": 9.5, "avg_scene_duration": 5.0}
        failed_qa = {"status": "FAIL", "failed_count": 2, "failures": ["audio_clipping", "duration_out_of_bounds"]}
        res = evaluate_content_quality(feat, failed_qa)
        self.assertFalse(res["qa_passed"])
        self.assertEqual(res["dimension_scores"]["qa_compliance"], 0.0)


if __name__ == "__main__":
    unittest.main()
