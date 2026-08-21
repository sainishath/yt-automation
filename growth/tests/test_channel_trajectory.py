# -*- coding: utf-8 -*-
"""
test_channel_trajectory.py
--------------------------
Phase 32: Channel Trajectory, Longitudinal Health & Scorecard Test Suite.
Verifies robust rolling medians, baseline capture, MAD outlier filtering,
deterministic scorecards, milestone comparisons, and causal evidence classification.
"""

import unittest
import tempfile
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from growth.db.database import init_db
from growth.db.models import (
    GrowthRepository,
    VideoModel,
    PerformanceSnapshotModel,
    ExperimentModel,
    ExperimentArmModel
)
from growth.brain.channel_trajectory import (
    ChannelTrajectoryEngine,
    ChannelHealthSnapshot,
    ChannelImprovementScorecard
)
from growth.brain.weekly_cycle import WeeklyLearningCycle
from growth.brain.brain import ContentBrain


class TestChannelTrajectory(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_trajectory.db"
        init_db(self.db_path)

        self.repo = GrowthRepository(self.db_path)
        self.trajectory_engine = ChannelTrajectoryEngine(self.repo)
        self.brain = ContentBrain(self.db_path)
        self.weekly_cycle = WeeklyLearningCycle(self.repo, output_dir=Path(self.tmp_dir.name))

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_01_baseline_capture_and_persistence(self):
        """1. Captures and persists pre-trial baseline snapshot in SQLite."""
        self.repo.upsert_video(VideoModel(
            video_id="vid_base_01", channel_id="channel_a", pipeline_id="pipeline1",
            title="Base Video", duration=45.0, upload_status="UPLOADED_PUBLIC"
        ))
        self.repo.insert_snapshot(PerformanceSnapshotModel(
            video_id="vid_base_01", window_name="7d", views=100, avg_percentage_viewed=70.0,
            likes=10, comments=2
        ))

        snapshot = self.trajectory_engine.capture_and_record_baseline("channel_a", tag="PRE_TRIAL_BASELINE")
        self.assertEqual(snapshot.channel_id, "channel_a")
        self.assertEqual(snapshot.tag, "PRE_TRIAL_BASELINE")
        self.assertEqual(snapshot.total_videos_published, 1)
        self.assertEqual(snapshot.mature_videos_count, 1)
        self.assertEqual(snapshot.median_views_per_video, 100.0)
        self.assertEqual(snapshot.median_mature_apv, 70.0)

        # Verify event was recorded in DB
        events = self.repo.list_learning_events(channel_id="channel_a")
        self.assertTrue(any(e.get("event_type") == "MILESTONE_PRE_TRIAL_BASELINE" for e in events))

    def test_02_mad_outlier_filtering(self):
        """2. MAD outlier filtering prevents single viral video from distorting mature median."""
        # Baseline normal views: 100, 105, 110, 95, 100. One massive viral outlier: 10,000
        views = [100.0, 105.0, 110.0, 95.0, 100.0, 10000.0]
        filtered = self.trajectory_engine._filter_mad_outliers(views)
        self.assertNotIn(10000.0, filtered)
        self.assertEqual(len(filtered), 5)

    def test_03_rolling_window_medians(self):
        """3. Calculates rolling 7d, 14d, and 28d views using robust medians."""
        for i in range(1, 15):
            vid_id = f"vid_roll_{i:02d}"
            self.repo.upsert_video(VideoModel(
                video_id=vid_id, channel_id="channel_a", pipeline_id="pipeline1",
                title=f"Rolling Vid {i}", duration=45.0, upload_status="UPLOADED_PUBLIC"
            ))
            self.repo.insert_snapshot(PerformanceSnapshotModel(
                video_id=vid_id, window_name="24h", views=100 + i * 10, avg_percentage_viewed=70.0
            ))

        health = self.trajectory_engine.compute_channel_health("channel_a")
        self.assertEqual(health.total_videos_published, 14)
        self.assertIsNotNone(health.rolling_7d_median_views)
        self.assertIsNotNone(health.rolling_14d_median_views)

    def test_04_scorecard_delta_and_evidence_classification(self):
        """4. Generates deterministic scorecard with OBSERVED vs SUPPORTED evidence tags."""
        base_snap = ChannelHealthSnapshot(
            channel_id="channel_a", tag="PRE_TRIAL_BASELINE", strategy_version="v1.0",
            total_videos_published=4, mature_videos_count=4, total_views=400,
            median_views_per_video=100.0, mean_views_per_video=100.0, median_mature_views=100.0,
            median_apv=70.0, mean_apv=70.0, median_mature_apv=70.0, likes_total=40, comments_total=4,
            comment_rate=0.01, subscriber_gain="NOT_AVAILABLE", best_video_id="v1", worst_video_id="v2",
            rolling_7d_median_views=100.0, rolling_14d_median_views=100.0, rolling_28d_median_views=100.0,
            active_experiments_count=1, completed_experiments_count=0, promoted_patterns_count=0,
            rejected_patterns_count=0, do_not_use_count=0
        )

        curr_snap = ChannelHealthSnapshot(
            channel_id="channel_a", tag="DAY_14", strategy_version="v1.1",
            total_videos_published=14, mature_videos_count=8, total_views=1600,
            median_views_per_video=120.0, mean_views_per_video=120.0, median_mature_views=120.0,
            median_apv=78.0, mean_apv=78.0, median_mature_apv=78.0, likes_total=160, comments_total=24,
            comment_rate=0.015, subscriber_gain="NOT_AVAILABLE", best_video_id="v5", worst_video_id="v1",
            rolling_7d_median_views=120.0, rolling_14d_median_views=110.0, rolling_28d_median_views=100.0,
            active_experiments_count=1, completed_experiments_count=1, promoted_patterns_count=1,
            rejected_patterns_count=0, do_not_use_count=0
        )

        scorecard = self.trajectory_engine.generate_scorecard("channel_a", baseline_snapshot=base_snap, current_snapshot=curr_snap)
        self.assertEqual(scorecard.channel_trajectory_status, "IMPROVED")
        self.assertEqual(scorecard.experiment_wins_count, 1)

        # Check metrics deltas
        metric_map = {m.name: m for m in scorecard.metrics}
        self.assertEqual(metric_map["median_mature_views"].delta_percentage, 20.0)
        self.assertEqual(metric_map["median_mature_views"].evidence_classification, "OBSERVED")
        self.assertAlmostEqual(metric_map["median_mature_apv"].delta_percentage, 11.4, places=1)
        self.assertEqual(metric_map["comment_rate"].delta_percentage, 50.0)
        self.assertIn("SUPPORTED", scorecard.causal_attribution_statement)

    def test_05_milestone_progression(self):
        """5. Verifies milestone capture across Day 0, 7, 14, 21, 30."""
        for tag in ["DAY_0", "DAY_7", "DAY_14", "DAY_21", "DAY_30"]:
            res = self.brain.record_channel_milestone("channel_a", tag=tag)
            self.assertEqual(res["tag"], tag)

        events = self.repo.list_learning_events(channel_id="channel_a")
        milestone_events = [e for e in events if "MILESTONE_" in e.get("event_type", "")]
        self.assertEqual(len(milestone_events), 5)

    def test_06_two_section_weekly_learning_report(self):
        """6. Generates weekly report containing distinct Section A (Experiments) and Section B (Trajectory)."""
        self.repo.upsert_video(VideoModel(
            video_id="vid_rep_06", channel_id="channel_a", pipeline_id="pipeline1",
            title="Weekly Report Test", duration=45.0, upload_status="UPLOADED_PUBLIC"
        ))
        self.repo.insert_snapshot(PerformanceSnapshotModel(
            video_id="vid_rep_06", window_name="7d", views=500, avg_percentage_viewed=75.0
        ))

        report = self.weekly_cycle.run_weekly_cycle("channel_a")
        self.assertIn("channel_health", report)
        self.assertIn("channel_scorecard", report)

        # Verify file output
        report_file = Path(self.tmp_dir.name) / "WEEKLY_LEARNING_REPORT_CHANNEL_A.md"
        self.assertTrue(report_file.exists())
        content = report_file.read_text(encoding="utf-8")
        self.assertIn("SECTION A — EXPERIMENTAL LEARNING", content)
        self.assertIn("SECTION B — CHANNEL TRAJECTORY", content)
        self.assertIn("Robust Channel Scorecard", content)


if __name__ == "__main__":
    unittest.main()
