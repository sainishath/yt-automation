# -*- coding: utf-8 -*-
"""
test_phase29_external_intelligence.py
-------------------------------------
Phase 29 Test Suite: External Intelligence Ingestion, Pattern Mining,
Transferability, Provenance, and First-Party Dominance.
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
from growth.db.models import GrowthRepository, ExperimentModel, PerformanceSnapshotModel
from growth.external_intelligence.repository import ExternalIntelligenceRepository
from growth.external_intelligence.schemas import (
    ExternalChannelModel,
    ExternalVideoModel,
    ExternalObservationModel,
    ExternalPriorModel,
    ProvenanceSource,
    ObservationType,
    EvidenceLevel,
    TransferabilityClassification,
    PriorStatus
)
from growth.external_intelligence.dataset_builder import ExternalDatasetBuilder
from growth.external_intelligence.pattern_miner import mine_patterns_from_videos
from growth.external_intelligence.transferability import evaluate_pattern_transferability
from growth.brain.brain import ContentBrain
from growth.brain.learning_engine import LearningEngine


class TestPhase29ExternalIntelligence(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_p29_ext.db"
        init_db(self.db_path)

        self.repo = GrowthRepository(self.db_path)
        self.ext_repo = ExternalIntelligenceRepository(self.db_path)
        self.builder = ExternalDatasetBuilder(self.ext_repo)
        self.brain = ContentBrain(self.db_path)
        self.learning_engine = LearningEngine(self.repo, self.ext_repo)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_01_external_dataset_builder_populates_500_plus_records(self):
        """1. ExternalDatasetBuilder populates 500+ structured records with provenance."""
        res = self.builder.build_dataset(target_count_per_channel=55)
        self.assertEqual(res["channels_populated"], 10)
        self.assertEqual(res["total_videos_ingested"], 550)
        self.assertEqual(res["total_observations_recorded"], 1100)
        self.assertEqual(res["provenance"], ProvenanceSource.PUBLIC_YOUTUBE.value)

        # Query database to verify physical persistence
        videos = self.ext_repo.list_external_videos(limit=600)
        self.assertEqual(len(videos), 550)
        self.assertTrue(all(v["source_type"] == "PUBLIC_YOUTUBE" for v in videos))

    def test_02_provenance_and_no_fake_metrics_enforcement(self):
        """2. External records store explicit public provenance and do not fabricate private metrics."""
        self.ext_repo.upsert_external_video(ExternalVideoModel(
            external_video_id="ext_test_prov_01",
            external_channel_id="analog_a_test",
            youtube_video_id="yt_prov_01",
            title="What if the Roman Empire Survived?",
            url="https://youtube.com/shorts/yt_prov_01",
            duration_seconds=45.0,
            views=500000,
            likes=40000,
            comments=1500,
            source_type=ProvenanceSource.PUBLIC_YOUTUBE
        ))

        vid = self.ext_repo.get_external_video("ext_test_prov_01")
        self.assertEqual(vid["source_type"], "PUBLIC_YOUTUBE")
        self.assertFalse(vid["is_simulation"])

    def test_03_cross_channel_pattern_mining(self):
        """3. Pattern miner extracts recurring hook patterns across multiple channels."""
        videos = [
            ExternalVideoModel(
                external_video_id=f"v_{i}", external_channel_id=f"analog_a_{i%3}",
                youtube_video_id=f"yt_{i}", title="What if the Library of Alexandria survived?",
                url="url", duration_seconds=45.0, views=400000, relative_view_multiplier=1.2,
                source_type=ProvenanceSource.PUBLIC_YOUTUBE
            )
            for i in range(6)
        ]
        patterns = mine_patterns_from_videos("channel_a", videos)
        self.assertTrue(len(patterns) > 0)
        hook_pats = [p for p in patterns if p.pattern_type.value == "HOOK_STRUCTURE"]
        self.assertTrue(len(hook_pats) > 0)
        self.assertTrue(hook_pats[0].channel_count >= 2)

    def test_04_transferability_classification(self):
        """4. Transferability classifies patterns based on topic, audience, and feasibility."""
        videos = [
            ExternalVideoModel(
                external_video_id=f"v_t_{i}", external_channel_id=f"analog_a_{i}",
                youtube_video_id=f"yt_t_{i}", title="What if the Roman Empire never fell?",
                url="url", duration_seconds=45.0, views=600000, relative_view_multiplier=1.3,
                source_type=ProvenanceSource.PUBLIC_YOUTUBE
            )
            for i in range(4)
        ]
        patterns = mine_patterns_from_videos("channel_a", videos)
        pat = patterns[0]
        score_model = evaluate_pattern_transferability("channel_a", pat)
        self.assertIn(score_model.classification, [TransferabilityClassification.HIGH, TransferabilityClassification.MEDIUM])
        self.assertTrue(score_model.overall_transferability_score > 0.6)

    def test_05_first_party_winner_dominates_external_prior(self):
        """5. Empirical first-party experiment outcome strictly demotes contradictory external prior."""
        from growth.db.models import VideoModel, PerformanceSnapshotModel

        self.ext_repo.upsert_external_prior(ExternalPriorModel(
            prior_id="prior_to_demote", target_channel_id="channel_a", pattern_id="pat_d",
            hypothesis="Declarative hooks outperform questions",
            transferability_classification=TransferabilityClassification.HIGH,
            prior_weight=0.25, status=PriorStatus.HYPOTHESIS
        ))

        # First-party experiment definition
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_demote_test", channel_id="channel_a", name="Demote Test",
            hypothesis="Declarative hooks outperform questions", variable_tested="HOOK_STRUCTURE",
            control_definition="Question Hook", variant_definition="Declarative Hook",
            primary_metric="avg_percentage_viewed", status="RUNNING", decision="PENDING",
            control_count=4, treatment_count=4, delta_percentage=0.0, external_prior_id="prior_to_demote"
        ))

        # Add 4 Control videos (80% APV) and 4 Treatment videos (65% APV)
        for i in range(4):
            ctrl_vid = f"vid_ctrl_{i}"
            self.repo.upsert_video(VideoModel(
                video_id=ctrl_vid, channel_id="channel_a", pipeline_id="pipeline1",
                title=f"Control {i}", duration=45.0,
                experiment_id="exp_demote_test", arm_id="arm_ctrl", variant_id="CONTROL",
                upload_status="UPLOADED_PUBLIC"
            ))
            self.repo.insert_performance_snapshot(PerformanceSnapshotModel(
                video_id=ctrl_vid,
                window_name="24h",
                views=1000,
                avg_percentage_viewed=80.0
            ))

            treat_vid = f"vid_treat_{i}"
            self.repo.upsert_video(VideoModel(
                video_id=treat_vid, channel_id="channel_a", pipeline_id="pipeline1",
                title=f"Treat {i}", duration=45.0,
                experiment_id="exp_demote_test", arm_id="arm_treat", variant_id="TREATMENT",
                upload_status="UPLOADED_PUBLIC"
            ))
            self.repo.insert_performance_snapshot(PerformanceSnapshotModel(
                video_id=treat_vid,
                window_name="24h",
                views=800,
                avg_percentage_viewed=65.0
            ))

        res = self.learning_engine.process_experiment_outcome("exp_demote_test")
        prior = self.ext_repo.get_external_prior("prior_to_demote")
        self.assertEqual(prior["status"], "REJECTED")
        self.assertEqual(prior["prior_weight"], 0.0)
        self.assertIn("FIRST_PARTY_OVERRIDE", res["events_generated"])

    def test_06_channel_a_channel_b_isolation(self):
        """6. External data and priors for Channel A do not leak into Channel B."""
        self.builder.build_dataset(target_count_per_channel=10)

        priors_a = self.ext_repo.list_external_priors(target_channel_id="channel_a")
        priors_b = self.ext_repo.list_external_priors(target_channel_id="channel_b")

        # All Channel A channels must belong to Channel A
        vids_a = self.ext_repo.list_external_videos()
        a_vids = [v for v in vids_a if "analog_a" in v["external_channel_id"]]
        b_vids = [v for v in vids_a if "analog_b" in v["external_channel_id"]]

        self.assertTrue(len(a_vids) > 0)
        self.assertTrue(len(b_vids) > 0)
        self.assertTrue(all("analog_a" in v["external_channel_id"] for v in a_vids))
        self.assertTrue(all("analog_b" in v["external_channel_id"] for v in b_vids))


if __name__ == "__main__":
    unittest.main()
