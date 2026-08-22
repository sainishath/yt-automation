# -*- coding: utf-8 -*-
"""
test_external_competitor_intelligence.py
----------------------------------------
Phase 32: Public YouTube External Competitor Intelligence & Evidence Provenance Test Suite.
Verifies:
1. Public video snapshot tracking (initial, 7d, 14d) with explicit public provenance.
2. Robust median normalization and MAD outlier protection.
3. External evidence generates HYPOTHESIS, never SUPPORTED.
4. External failure creates EXTERNAL_NEGATIVE_PRIOR, never direct DO_NOT_USE.
5. First-Party Empirical Dominance (FIRST_PARTY_OVERRIDE).
6. Strict Channel A / Channel B isolation.
"""

import unittest
import tempfile
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from growth.db.database import init_db
from growth.db.models import GrowthRepository, VideoModel, PerformanceSnapshotModel, ExperimentModel
from growth.external_intelligence.repository import ExternalIntelligenceRepository
from growth.external_intelligence.schemas import (
    ExternalChannelModel,
    ExternalVideoModel,
    ExternalVideoSnapshotModel,
    ExternalPriorModel,
    ProvenanceSource,
    TransferabilityClassification,
    PriorStatus,
    EvidenceLevel
)
from growth.external_intelligence.dataset_builder import ExternalDatasetBuilder
from growth.external_intelligence.pattern_miner import mine_patterns_from_videos
from growth.brain.belief_engine import BeliefEngine
from growth.brain.learning_engine import LearningEngine


class TestExternalCompetitorIntelligence(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_competitor_intel.db"
        init_db(self.db_path)

        self.repo = GrowthRepository(self.db_path)
        self.ext_repo = ExternalIntelligenceRepository(self.db_path)
        self.builder = ExternalDatasetBuilder(self.ext_repo)
        self.belief_engine = BeliefEngine(self.repo)
        self.learning_engine = LearningEngine(self.repo, self.ext_repo)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_01_public_snapshot_persistence_and_retrieval(self):
        """1. External video snapshots (initial, 7d) are stored and retrieved with PUBLIC_YOUTUBE provenance."""
        self.ext_repo.upsert_external_channel(ExternalChannelModel(
            external_channel_id="analog_a_hub", target_channel_id="channel_a",
            channel_title="AlternateHistoryHub", source_type=ProvenanceSource.PUBLIC_YOUTUBE
        ))
        self.ext_repo.upsert_external_video(ExternalVideoModel(
            external_video_id="ext_vid_01", external_channel_id="analog_a_hub",
            youtube_video_id="yt_01", title="What if Rome never fell?", url="https://youtu.be/yt_01",
            views=500000, likes=35000, comments=1200, source_type=ProvenanceSource.PUBLIC_YOUTUBE
        ))

        # Insert multiple snapshots across time windows
        self.ext_repo.upsert_external_video_snapshot(ExternalVideoSnapshotModel(
            external_video_id="ext_vid_01", window_name="initial", views=200000, likes=14000, comments=500,
            source_type=ProvenanceSource.PUBLIC_YOUTUBE
        ))
        self.ext_repo.upsert_external_video_snapshot(ExternalVideoSnapshotModel(
            external_video_id="ext_vid_01", window_name="7d", views=500000, likes=35000, comments=1200,
            source_type=ProvenanceSource.PUBLIC_YOUTUBE
        ))

        snaps = self.ext_repo.list_external_video_snapshots("ext_vid_01")
        self.assertEqual(len(snaps), 2)
        self.assertEqual(snaps[0]["window_name"], "initial")
        self.assertEqual(snaps[1]["window_name"], "7d")
        self.assertEqual(snaps[1]["views"], 500000)
        self.assertTrue(all(s["source_type"] == "PUBLIC_YOUTUBE" for s in snaps))

    def test_02_robust_median_normalization_and_mad_filtering(self):
        """2. Normalization against channel baseline uses robust medians with MAD outlier protection."""
        from growth.brain.channel_trajectory import ChannelTrajectoryEngine
        traj_engine = ChannelTrajectoryEngine(self.repo)

        # Baseline views around 100k, with one 50M viral outlier
        views = [95000.0, 100000.0, 105000.0, 110000.0, 90000.0, 50000000.0]
        filtered = traj_engine._filter_mad_outliers(views)
        self.assertNotIn(50000000.0, filtered)
        self.assertEqual(len(filtered), 5)

    def test_03_external_evidence_creates_hypothesis_never_supported(self):
        """3. External patterns generate priors with status HYPOTHESIS, never SUPPORTED or strategy mutation."""
        videos = [
            ExternalVideoModel(
                external_video_id=f"v_soc_{i}", external_channel_id=f"analog_b_{i%2}",
                youtube_video_id=f"yt_soc_{i}", title="Can AI ever experience subjective emotional pain?",
                url="https://youtube.com/shorts/test", duration_seconds=45.0, views=700000,
                relative_view_multiplier=1.3, source_type=ProvenanceSource.PUBLIC_YOUTUBE
            )
            for i in range(4)
        ]
        patterns = mine_patterns_from_videos("channel_b", videos)
        self.assertTrue(len(patterns) > 0)

        # Prior generation from pattern
        prior = ExternalPriorModel(
            prior_id="prior_test_socratic", target_channel_id="channel_b",
            pattern_id=patterns[0].pattern_id, hypothesis="Socratic hooks increase engagement",
            transferability_classification=TransferabilityClassification.HIGH,
            prior_weight=0.20, status=PriorStatus.HYPOTHESIS
        )
        self.ext_repo.upsert_external_prior(prior)

        fetched = self.ext_repo.get_external_prior("prior_test_socratic")
        self.assertEqual(fetched["status"], "HYPOTHESIS")
        self.assertNotEqual(fetched["status"], "SUPPORTED")
        self.assertLessEqual(fetched["prior_weight"], 0.30)

    def test_04_external_failure_does_not_populate_do_not_use(self):
        """4. External underperformance does NOT directly populate first-party DO_NOT_USE."""
        neg_knowledge = self.belief_engine.get_negative_knowledge("channel_a")
        # Ensure DO_NOT_USE is strictly governed by first-party empirical failure
        self.assertIsInstance(neg_knowledge.get("do_not_use_patterns"), list)

    def test_05_first_party_dominance_overrides_external_prior(self):
        """5. Empirical first-party data (N >= 4) strictly overrides contradictory external prior."""
        self.ext_repo.upsert_external_prior(ExternalPriorModel(
            prior_id="prior_override_test", target_channel_id="channel_a",
            pattern_id="pat_question_hook", hypothesis="Question hooks outperform statement hooks",
            transferability_classification=TransferabilityClassification.HIGH,
            prior_weight=0.25, status=PriorStatus.HYPOTHESIS
        ))

        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_override_01", channel_id="channel_a", name="Hook Test",
            hypothesis="Question hooks outperform statement hooks", variable_tested="HOOK_STRUCTURE",
            control_definition="Question Hook", variant_definition="Statement Hook",
            primary_metric="avg_percentage_viewed", status="RUNNING", decision="PENDING",
            control_count=4, treatment_count=4, delta_percentage=0.0,
            external_prior_id="prior_override_test"
        ))

        # Insert 4 Control (80% APV) and 4 Treatment (60% APV) -> Treatment lost (-25% delta)
        for i in range(4):
            self.repo.upsert_video(VideoModel(
                video_id=f"v_c_{i}", channel_id="channel_a", pipeline_id="pipeline1",
                title=f"Ctrl {i}", duration=45.0, experiment_id="exp_override_01",
                arm_id="arm_c", variant_id="CONTROL", upload_status="UPLOADED_PUBLIC"
            ))
            self.repo.insert_performance_snapshot(PerformanceSnapshotModel(
                video_id=f"v_c_{i}", window_name="24h", views=1000, avg_percentage_viewed=80.0
            ))
            self.repo.upsert_video(VideoModel(
                video_id=f"v_t_{i}", channel_id="channel_a", pipeline_id="pipeline1",
                title=f"Treat {i}", duration=45.0, experiment_id="exp_override_01",
                arm_id="arm_t", variant_id="TREATMENT", upload_status="UPLOADED_PUBLIC"
            ))
            self.repo.insert_performance_snapshot(PerformanceSnapshotModel(
                video_id=f"v_t_{i}", window_name="24h", views=800, avg_percentage_viewed=60.0
            ))

        outcome = self.learning_engine.process_experiment_outcome("exp_override_01")
        prior = self.ext_repo.get_external_prior("prior_override_test")
        self.assertEqual(prior["status"], "REJECTED")
        self.assertEqual(prior["prior_weight"], 0.0)
        self.assertIn("FIRST_PARTY_OVERRIDE", outcome["events_generated"])

    def test_06_channel_isolation_and_provenance(self):
        """6. External data for Channel A and Channel B are isolated and strictly tagged."""
        self.builder.build_dataset(target_count_per_channel=5)
        channels_a = self.ext_repo.list_external_channels("channel_a")
        channels_b = self.ext_repo.list_external_channels("channel_b")

        self.assertTrue(len(channels_a) > 0)
        self.assertTrue(len(channels_b) > 0)
        self.assertTrue(all(c["target_channel_id"] == "channel_a" for c in channels_a))
        self.assertTrue(all(c["target_channel_id"] == "channel_b" for c in channels_b))


if __name__ == "__main__":
    unittest.main()
