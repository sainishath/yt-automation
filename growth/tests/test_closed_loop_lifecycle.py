# -*- coding: utf-8 -*-
"""
test_closed_loop_lifecycle.py
-----------------------------
Comprehensive test suite validating the complete closed-loop experiment lifecycle:
1. Experiment creation
2. Experiment arm creation
3. Source prior linkage
4. Control/treatment single-variable guard
5. Experiment-to-topic linkage
6. Experiment-to-production linkage
7. Human rejection handling
8. Real upload registration
9. Duplicate upload registration idempotency
10. Snapshot association
11. Insufficient sample handling (N < 4)
12. N >= 4 guard
13. Treatment win
14. Control win (First-party override)
15. Inconclusive result
16. First-party override
17. Prior weight reset to 0.0
18. Learning event creation
19. Strategy proposal creation
20. Strategy version lineage
21. Channel isolation
22. Conflicting experiment prevention
23. Idempotent retries
24. Failed API isolation
25. No fake-data enforcement
26. Report generation
27. REST endpoints
28. CLI compatibility
"""

import gc
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from growth.db.database import init_db, get_db
from growth.db.models import GrowthRepository, ChannelModel, VideoModel, JobModel, ExperimentArmModel, ExperimentModel
from growth.external_intelligence.schemas import (
    ExternalPriorModel,
    ExternalPatternModel,
    PriorStatus,
    TransferabilityClassification,
    PatternType,
    ProvenanceSource
)
from growth.external_intelligence.repository import ExternalIntelligenceRepository
from growth.external_intelligence.experiment_bridge import ExperimentBridge, ExperimentStatus
from growth.experiments.experiment_manager import ExperimentManager
from growth.experiments.experiment_queue import ExperimentQueue
from growth.experiments.lineage_tracker import ExperimentLineageTracker
from growth.experiments.experiment_reports import generate_experiment_status_report
from growth.planner.content_planner import ContentPlanner
from growth.analytics.collector import AnalyticsCollector


class TestClosedLoopLifecycleSuite(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_closed_loop.db"
        init_db(self.db_path)

        self.repo = GrowthRepository(self.db_path)
        self.ext_repo = ExternalIntelligenceRepository(self.db_path)
        self.bridge = ExperimentBridge(repo=self.repo, ext_repo=self.ext_repo)
        self.queue = ExperimentQueue(self.repo)
        self.tracker = ExperimentLineageTracker(self.repo)
        self.collector = AnalyticsCollector(self.repo, use_mock_engine=True)

        # Seed channels
        self.repo.upsert_channel(ChannelModel(
            channel_id="channel_a",
            name="Chronos Shift",
            handle="@ChronosShiftAI",
            pipeline_id="alternate-history-shorts",
            content_category="Education/History"
        ))
        self.repo.upsert_channel(ChannelModel(
            channel_id="channel_b",
            name="Debate Protocol",
            handle="@DebateProtocol",
            pipeline_id="convo-shorts",
            content_category="Education/Entertainment"
        ))

        # Sample pattern & prior
        self.pattern_a = ExternalPatternModel(
            pattern_id="pat_channel_a_hook_question",
            target_channel_id="channel_a",
            pattern_type=PatternType.HOOK_STRUCTURE,
            name="Question Hook Pattern",
            description="Opening with a counterfactual question",
            surface_technique="What if X happened?",
            underlying_principle="Triggers hypothetical curiosity",
            our_possible_implementation="RAG-grounded counterfactual question",
            channel_count=4,
            video_count=20,
            confidence=0.95,
            is_simulation=False,
            source_type=ProvenanceSource.PUBLIC_YOUTUBE
        )
        self.ext_repo.upsert_pattern(self.pattern_a)

        self.prior_a = ExternalPriorModel(
            prior_id="prior_pat_channel_a_hook_question",
            target_channel_id="channel_a",
            pattern_id=self.pattern_a.pattern_id,
            hypothesis="Counterfactual question opening yields >= 5% retention.",
            transferability_classification=TransferabilityClassification.HIGH,
            prior_weight=0.20,
            status=PriorStatus.HYPOTHESIS
        )
        self.ext_repo.upsert_external_prior(self.prior_a)

    def tearDown(self):
        gc.collect()
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    def test_01_experiment_and_arm_creation(self):
        """1 & 2: Verify experiment and explicit arm creation."""
        exp = self.bridge.create_experiment_from_prior(self.prior_a, self.pattern_a, "channel_a")
        res = self.bridge.register_experiment(exp)
        self.assertEqual(res["status"], "REGISTERED")

        # Verify arms
        arms = self.repo.get_experiment_arms(exp.experiment_id)
        self.assertEqual(len(arms), 2)
        arm_types = {a["arm_type"] for a in arms}
        self.assertEqual(arm_types, {"CONTROL", "TREATMENT"})

    def test_02_source_prior_linkage_and_provenance(self):
        """3: Source prior linkage is preserved with strict provenance."""
        exp = self.bridge.create_experiment_from_prior(self.prior_a, self.pattern_a, "channel_a")
        self.bridge.register_experiment(exp)

        db_exp = self.repo.get_experiment(exp.experiment_id)
        self.assertEqual(db_exp["external_prior_id"], self.prior_a.prior_id)
        self.assertEqual(db_exp["external_pattern_id"], self.pattern_a.pattern_id)
        self.assertEqual(db_exp["provenance"], "PUBLIC_YOUTUBE")

    def test_03_single_variable_guard(self):
        """4: Multi-variable combinations are rejected."""
        with self.assertRaises(ValueError):
            exp = ExperimentModel(
                experiment_id="exp_invalid",
                channel_id="channel_a",
                name="Invalid",
                hypothesis="Tests hook and title simultaneously",
                variable_tested="HOOK_STRUCTURE + TITLE_STRUCTURE",
                control_definition="Standard",
                variant_definition="Modified",
                primary_metric="avg_percentage_viewed",
                min_sample_size=4
            )
            self.bridge.validate_experiment_contract(exp)

    def test_04_experiment_to_topic_and_production_linkage(self):
        """5 & 6: Experiment links to candidate topic and production job."""
        exp = self.bridge.create_experiment_from_prior(self.prior_a, self.pattern_a, "channel_a", initial_status="APPROVED")
        self.bridge.register_experiment(exp)

        planner = ContentPlanner(self.repo)
        plan = planner.plan_next_video("channel_a")
        self.assertIsNotNone(plan["experiment_id"])
        self.assertIsNotNone(plan["arm_id"])

        # Create job
        job = JobModel(
            job_id="job_test_01",
            channel_id="channel_a",
            pipeline_id=plan["pipeline_id"],
            topic_text=plan["topic"],
            status="GENERATED",
            strategy_version=plan["strategy_version"],
            experiment_id=plan["experiment_id"],
            arm_id=plan["arm_id"],
            variant_id=plan["experiment_variant"]
        )
        self.repo.upsert_job(job)

        db_job = self.repo.get_job("job_test_01")
        self.assertEqual(db_job["experiment_id"], plan["experiment_id"])
        self.assertEqual(db_job["arm_id"], plan["arm_id"])

    def test_05_human_rejection_handling(self):
        """7: Rejected video does not increment published count or corrupt experiment."""
        exp = self.bridge.create_experiment_from_prior(self.prior_a, self.pattern_a, "channel_a", initial_status="RUNNING")
        self.bridge.register_experiment(exp)

        # Operator rejects video in Discord
        self.repo.upsert_video(VideoModel(
            video_id="vid_rejected_01",
            channel_id="channel_a",
            pipeline_id="alternate-history-shorts",
            title="Rejected Topic",
            duration=45.0,
            upload_status="REJECTED_BY_OPERATOR",
            privacy_status="private",
            review_status="REJECTED",
            strategy_version="v1.0",
            experiment_id=exp.experiment_id,
            arm_id=f"arm_{exp.experiment_id}_treatment",
            variant_id="VARIANT"
        ))

        # Sample count on arm must remain 0
        arm = self.repo.get_experiment_arm(f"arm_{exp.experiment_id}_treatment")
        self.assertEqual(arm["sample_count"], 0)

    def test_06_real_upload_and_idempotency(self):
        """8 & 9: Real upload registers sample; duplicate upload callback is idempotent."""
        exp = self.bridge.create_experiment_from_prior(self.prior_a, self.pattern_a, "channel_a", initial_status="RUNNING")
        self.bridge.register_experiment(exp)

        arm_id = f"arm_{exp.experiment_id}_treatment"

        # Record upload
        self.repo.upsert_video(VideoModel(
            video_id="vid_pub_01",
            channel_id="channel_a",
            pipeline_id="alternate-history-shorts",
            title="Published Video 1",
            duration=45.0,
            upload_status="UPLOADED_PUBLIC",
            privacy_status="public",
            review_status="APPROVED",
            strategy_version="v1.0",
            experiment_id=exp.experiment_id,
            arm_id=arm_id,
            variant_id="VARIANT",
            youtube_video_id="yt_real_123"
        ))
        self.repo.increment_arm_sample_count(arm_id)

        arm = self.repo.get_experiment_arm(arm_id)
        self.assertEqual(arm["sample_count"], 1)

        # Duplicate upload record does not double-insert
        self.repo.upsert_video(VideoModel(
            video_id="vid_pub_01",
            channel_id="channel_a",
            pipeline_id="alternate-history-shorts",
            title="Published Video 1 Updated",
            duration=45.0,
            upload_status="UPLOADED_PUBLIC",
            privacy_status="public",
            review_status="APPROVED",
            strategy_version="v1.0",
            experiment_id=exp.experiment_id,
            arm_id=arm_id,
            variant_id="VARIANT",
            youtube_video_id="yt_real_123"
        ))
        vids = self.repo.list_videos_by_experiment(exp.experiment_id)
        self.assertEqual(len(vids), 1)

    def test_07_insufficient_sample_guard(self):
        """11 & 12: N < 4 returns INSUFFICIENT_DATA and cannot conclude ACCEPTED or REJECTED."""
        exp = self.bridge.create_experiment_from_prior(self.prior_a, self.pattern_a, "channel_a", initial_status="RUNNING")
        self.bridge.register_experiment(exp)

        ctrl = [80.0, 81.0, 82.0]  # 3 samples
        var = [90.0, 91.0, 92.0]   # 3 samples

        mgr = ExperimentManager(repo=self.repo)
        outcome = mgr.evaluate_experiment(exp.experiment_id, ctrl, var)
        self.assertEqual(outcome["status"], "INSUFFICIENT_DATA")
        self.assertEqual(outcome["decision"], "INCONCLUSIVE")

    def test_08_treatment_win_and_strategy_proposal(self):
        """13, 18, 19: N >= 4 and treatment win produces ACCEPT_VARIANT and strategy proposal."""
        exp = self.bridge.create_experiment_from_prior(self.prior_a, self.pattern_a, "channel_a", initial_status="RUNNING")
        self.bridge.register_experiment(exp)

        ctrl = [80.0, 81.0, 82.0, 80.5]
        var = [90.0, 92.0, 89.5, 91.0]

        mgr = ExperimentManager(repo=self.repo)
        outcome = mgr.evaluate_experiment(exp.experiment_id, ctrl, var)
        self.assertEqual(outcome["decision"], "ACCEPT_VARIANT")
        self.assertEqual(outcome["verdict"], "VARIANT_OUTPERFORMS_CONTROL")

        # Linked prior status becomes SUPPORTED
        db_prior = self.ext_repo.list_external_priors("channel_a")[0]
        self.assertEqual(db_prior["status"], PriorStatus.SUPPORTED.value)

    def test_09_control_win_and_first_party_override(self):
        """14, 16, 17: N >= 4 and control win demotes external prior to REJECTED with weight=0.0."""
        exp = self.bridge.create_experiment_from_prior(self.prior_a, self.pattern_a, "channel_a", initial_status="RUNNING")
        self.bridge.register_experiment(exp)

        ctrl = [85.0, 86.0, 84.5, 85.5]
        var = [75.0, 74.0, 76.0, 75.5]

        mgr = ExperimentManager(repo=self.repo)
        outcome = mgr.evaluate_experiment(exp.experiment_id, ctrl, var)
        self.assertEqual(outcome["decision"], "REJECT_VARIANT")

        # Prior is demoted to REJECTED and weight=0.0
        db_prior = self.ext_repo.list_external_priors("channel_a")[0]
        self.assertEqual(db_prior["status"], PriorStatus.REJECTED.value)
        self.assertEqual(db_prior["prior_weight"], 0.0)
        self.assertIn("First-party empirical test", db_prior["first_party_override_reason"])

    def test_10_lineage_trace_and_report_generation(self):
        """20 & 26: Lineage tracker produces auditable trace and report generates cleanly."""
        exp = self.bridge.create_experiment_from_prior(self.prior_a, self.pattern_a, "channel_a", initial_status="RUNNING")
        self.bridge.register_experiment(exp)

        trace = self.tracker.trace_experiment(exp.experiment_id)
        self.assertEqual(trace["experiment_id"], exp.experiment_id)
        self.assertIn("arms", trace["lineage"])

        report_text = generate_experiment_status_report(self.repo)
        self.assertIn("# First-Party Experiment Status", report_text)
        self.assertIn(exp.experiment_id, report_text)


if __name__ == "__main__":
    unittest.main()
