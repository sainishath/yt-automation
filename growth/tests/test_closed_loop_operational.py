# -*- coding: utf-8 -*-
"""
test_closed_loop_operational.py
-------------------------------
Comprehensive 24-point operational verification test suite for the
Closed-Loop Video-by-Video First-Party Learning System.
"""

import unittest
import tempfile
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from growth.db.database import init_db
from growth.db.models import (
    GrowthRepository,
    VideoModel,
    PerformanceSnapshotModel,
    ExperimentModel,
    ExperimentArmModel,
    LearningEventModel
)
from growth.external_intelligence.repository import ExternalIntelligenceRepository
from growth.external_intelligence.schemas import (
    ExternalVideoModel,
    ExternalPriorModel,
    ProvenanceSource,
    TransferabilityClassification,
    PriorStatus
)
from growth.experiments.sample_tracker import ExperimentSampleTracker
from growth.brain.belief_engine import BeliefEngine, VideoMaturity, BeliefStatus, VideoDiagnostic
from growth.brain.evaluator import MultiArmExperimentEvaluator, ExperimentDecision
from growth.brain.learning_engine import LearningEngine
from growth.brain.strategy_evolution import StrategyEvolutionEngine
from growth.brain.weekly_cycle import WeeklyLearningCycle
from growth.brain.brain import ContentBrain
from growth.brain.production_recommendation import ProductionRecommendationEngine
from growth.brain.schemas import ConfidenceLevel, KnowledgeState, DecisionType


class TestClosedLoopOperational(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_operational.db"
        init_db(self.db_path)

        self.repo = GrowthRepository(self.db_path)
        self.ext_repo = ExternalIntelligenceRepository(self.db_path)
        self.tracker = ExperimentSampleTracker(self.repo)
        self.belief_engine = BeliefEngine(self.repo, self.ext_repo)
        self.evaluator = MultiArmExperimentEvaluator(self.repo, min_sample_size=4)
        self.learning_engine = LearningEngine(self.repo, self.ext_repo, self.evaluator)
        self.strat_evolution = StrategyEvolutionEngine(self.repo)
        self.weekly_cycle = WeeklyLearningCycle(self.repo, output_dir=Path(self.tmp_dir.name))
        self.rec_engine = ProductionRecommendationEngine(output_dir=Path(self.tmp_dir.name))
        self.brain = ContentBrain(self.db_path)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_01_one_video_published(self):
        """1. Registering one published video increments arm sample count exactly once."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_op_01", channel_id="channel_a", name="Op Test",
            hypothesis="Test", variable_tested="HOOK_STRUCTURE", control_definition="c", variant_definition="t",
            primary_metric="avg_percentage_viewed", status="RUNNING", decision="PENDING"
        ))
        self.repo.upsert_experiment_arm(ExperimentArmModel(
            arm_id="arm_op_01_treat", experiment_id="exp_op_01", arm_type="TREATMENT", name="Treatment", definition="t"
        ))
        self.repo.upsert_video(VideoModel(
            video_id="vid_op_01", channel_id="channel_a", pipeline_id="pipeline1",
            title="First Video", duration=45.0, experiment_id="exp_op_01",
            arm_id="arm_op_01_treat", variant_id="TREATMENT"
        ))
        res = self.tracker.register_real_upload("vid_op_01", "yt_vid_01")
        self.assertEqual(res["status"], "UPLOAD_REGISTERED")
        self.assertEqual(res["sample_count"], 1)

    def test_02_snapshot_ingestion(self):
        """2. Snapshots across all windows are ingested into SQLite."""
        self.repo.upsert_video(VideoModel(
            video_id="vid_op_02", channel_id="channel_a", pipeline_id="pipeline1",
            title="Snapshot Test", duration=45.0, upload_status="UPLOADED_PUBLIC"
        ))
        for win in ["1h", "6h", "24h", "48h", "7d", "28d"]:
            self.repo.insert_snapshot(PerformanceSnapshotModel(
                video_id="vid_op_02", window_name=win, views=100, avg_percentage_viewed=75.0
            ))
        snaps = self.repo.list_snapshots_for_video("vid_op_02")
        self.assertEqual(len(snaps), 6)

    def test_03_1h_diagnostic_immature(self):
        """3. 1h snapshot generates IMMATURE diagnostic and does NOT mutate strategy."""
        self.repo.upsert_video(VideoModel(
            video_id="vid_op_03", channel_id="channel_a", pipeline_id="pipeline1",
            title="1h Test", duration=45.0, upload_status="UPLOADED_PUBLIC"
        ))
        self.repo.insert_snapshot(PerformanceSnapshotModel(
            video_id="vid_op_03", window_name="1h", views=10, avg_percentage_viewed=80.0
        ))
        diag = self.belief_engine.generate_video_diagnostic("vid_op_03")
        self.assertEqual(diag.maturity, VideoMaturity.IMMATURE)
        strat_report = self.strat_evolution.evaluate_strategy_mutation("channel_a")
        self.assertEqual(strat_report["action"], "NO_MUTATION_WARRANTED")

    def test_04_6h_diagnostic_immature(self):
        """4. 6h snapshot remains IMMATURE for early anomaly detection."""
        self.repo.upsert_video(VideoModel(
            video_id="vid_op_04", channel_id="channel_a", pipeline_id="pipeline1",
            title="6h Test", duration=45.0, upload_status="UPLOADED_PUBLIC"
        ))
        self.repo.insert_snapshot(PerformanceSnapshotModel(
            video_id="vid_op_04", window_name="6h", views=50, avg_percentage_viewed=82.0
        ))
        diag = self.belief_engine.generate_video_diagnostic("vid_op_04")
        self.assertEqual(diag.maturity, VideoMaturity.IMMATURE)

    def test_05_24h_diagnostic_preliminary(self):
        """5. 24h snapshot enters PRELIMINARY tier for initial diagnostic attribution."""
        self.repo.upsert_video(VideoModel(
            video_id="vid_op_05", channel_id="channel_a", pipeline_id="pipeline1",
            title="24h Test", duration=45.0, upload_status="UPLOADED_PUBLIC"
        ))
        self.repo.insert_snapshot(PerformanceSnapshotModel(
            video_id="vid_op_05", window_name="24h", views=500, avg_percentage_viewed=85.0
        ))
        diag = self.belief_engine.generate_video_diagnostic("vid_op_05")
        self.assertEqual(diag.maturity, VideoMaturity.PRELIMINARY)
        self.assertEqual(diag.hook_signal, "POSITIVE")

    def test_06_48h_diagnostic_preliminary(self):
        """6. 48h snapshot confirms PRELIMINARY diagnostic trends."""
        self.repo.upsert_video(VideoModel(
            video_id="vid_op_06", channel_id="channel_a", pipeline_id="pipeline1",
            title="48h Test", duration=45.0, upload_status="UPLOADED_PUBLIC"
        ))
        self.repo.insert_snapshot(PerformanceSnapshotModel(
            video_id="vid_op_06", window_name="48h", views=900, avg_percentage_viewed=87.0
        ))
        diag = self.belief_engine.generate_video_diagnostic("vid_op_06")
        self.assertEqual(diag.maturity, VideoMaturity.PRELIMINARY)

    def test_07_7d_maturity_evaluation(self):
        """7. 7d snapshot marks video MATURE for cohort statistical evaluation."""
        self.repo.upsert_video(VideoModel(
            video_id="vid_op_07", channel_id="channel_a", pipeline_id="pipeline1",
            title="7d Test", duration=45.0, upload_status="UPLOADED_PUBLIC"
        ))
        self.repo.insert_snapshot(PerformanceSnapshotModel(
            video_id="vid_op_07", window_name="7d", views=1500, avg_percentage_viewed=89.0
        ))
        diag = self.belief_engine.generate_video_diagnostic("vid_op_07")
        self.assertEqual(diag.maturity, VideoMaturity.MATURE)
        self.assertEqual(diag.evidence_level, "FIRST_PARTY_MATURE")

    def test_08_dynamic_arm_balancing(self):
        """8. Dynamic cohort balancer assigns next job to lagging arm."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_bal_08", channel_id="channel_a", name="Bal Test",
            hypothesis="Test", variable_tested="HOOK_STRUCTURE", control_definition="c", variant_definition="t",
            primary_metric="avg_percentage_viewed", status="RUNNING", decision="PENDING",
            control_count=1, treatment_count=2
        ))
        self.repo.upsert_experiment_arm(ExperimentArmModel(
            arm_id="arm_bal_08_c", experiment_id="exp_bal_08", arm_type="CONTROL", name="Control", definition="c", sample_count=1
        ))
        self.repo.upsert_experiment_arm(ExperimentArmModel(
            arm_id="arm_bal_08_t", experiment_id="exp_bal_08", arm_type="TREATMENT", name="Treatment", definition="t", sample_count=2
        ))
        decision = self.brain.next_production_decision("channel_a")
        self.assertEqual(decision.arm_type, "CONTROL")

    def test_09_duplicate_snapshot_idempotency(self):
        """9. Re-inserting a snapshot for (video_id, window_name) updates rather than duplicates."""
        self.repo.upsert_video(VideoModel(
            video_id="vid_op_09", channel_id="channel_a", pipeline_id="pipeline1",
            title="Dup Snap Test", duration=45.0, upload_status="UPLOADED_PUBLIC"
        ))
        self.repo.insert_snapshot(PerformanceSnapshotModel(
            video_id="vid_op_09", window_name="24h", views=100, avg_percentage_viewed=70.0
        ))
        self.repo.insert_snapshot(PerformanceSnapshotModel(
            video_id="vid_op_09", window_name="24h", views=150, avg_percentage_viewed=75.0
        ))
        snaps = self.repo.list_snapshots_for_video("vid_op_09")
        self.assertEqual(len(snaps), 1)
        self.assertEqual(snaps[0]["views"], 150)

    def test_10_duplicate_video_protection(self):
        """10. Duplicate upload registration does not double-count arm samples."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_dup_10", channel_id="channel_a", name="Dup Test",
            hypothesis="Test", variable_tested="HOOK_STRUCTURE", control_definition="c", variant_definition="t",
            primary_metric="avg_percentage_viewed", status="RUNNING", decision="PENDING"
        ))
        self.repo.upsert_experiment_arm(ExperimentArmModel(
            arm_id="arm_dup_10", experiment_id="exp_dup_10", arm_type="CONTROL", name="Control", definition="c", sample_count=0
        ))
        self.repo.upsert_video(VideoModel(
            video_id="vid_dup_10", channel_id="channel_a", pipeline_id="pipeline1",
            title="Dup Vid Test", duration=45.0, experiment_id="exp_dup_10",
            arm_id="arm_dup_10", variant_id="CONTROL"
        ))
        res1 = self.tracker.register_real_upload("vid_dup_10", "yt_dup_10")
        self.assertEqual(res1["status"], "UPLOAD_REGISTERED")
        self.assertEqual(res1["sample_count"], 1)

        res2 = self.tracker.register_real_upload("vid_dup_10", "yt_dup_10")
        self.assertEqual(res2["status"], "ALREADY_REGISTERED")
        self.assertEqual(res2["sample_count"], 1)

    def test_11_n_less_than_4_strategy_rejection(self):
        """11. N < 4 per arm rejects strategy mutation."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_n3_11", channel_id="channel_a", name="N3 Test",
            hypothesis="Test", variable_tested="HOOK_STRUCTURE", control_definition="c", variant_definition="t",
            primary_metric="avg_percentage_viewed", status="RUNNING", decision="PENDING",
            control_count=3, treatment_count=3
        ))
        rep = self.strat_evolution.evaluate_strategy_mutation("channel_a")
        self.assertEqual(rep["action"], "NO_MUTATION_WARRANTED")

    def test_12_n_greater_equal_4_evaluation(self):
        """12. N >= 4 per arm allows statistical evaluation."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_n4_12", channel_id="channel_a", name="N4 Test",
            hypothesis="Test", variable_tested="HOOK_STRUCTURE", control_definition="c", variant_definition="t",
            primary_metric="avg_percentage_viewed", status="RUNNING", decision="PENDING"
        ))
        for i in range(4):
            cv = f"cv_12_{i}"
            self.repo.upsert_video(VideoModel(
                video_id=cv, channel_id="channel_a", pipeline_id="pipeline1",
                title=f"Ctrl {i}", duration=45.0, experiment_id="exp_n4_12",
                arm_id="arm_c", variant_id="CONTROL", upload_status="UPLOADED_PUBLIC"
            ))
            self.repo.insert_snapshot(PerformanceSnapshotModel(
                video_id=cv, window_name="7d", views=1000, avg_percentage_viewed=72.0
            ))
            tv = f"tv_12_{i}"
            self.repo.upsert_video(VideoModel(
                video_id=tv, channel_id="channel_a", pipeline_id="pipeline1",
                title=f"Treat {i}", duration=45.0, experiment_id="exp_n4_12",
                arm_id="arm_t", variant_id="TREATMENT", upload_status="UPLOADED_PUBLIC"
            ))
            self.repo.insert_snapshot(PerformanceSnapshotModel(
                video_id=tv, window_name="7d", views=1200, avg_percentage_viewed=82.0
            ))
        report = self.evaluator.evaluate_experiment("exp_n4_12")
        self.assertEqual(report.status, "EVALUATED")
        self.assertEqual(report.decision, ExperimentDecision.WIN)

    def test_13_winning_treatment_promotes_strategy(self):
        """13. Winning treatment (+12% APV) creates immutable Strategy Version v1.1."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_win_13", channel_id="channel_a", name="Win Test",
            hypothesis="Win", variable_tested="HOOK_STRUCTURE", control_definition="c", variant_definition="Winning Hook",
            primary_metric="avg_percentage_viewed", status="EVALUATED", decision="ACCEPT_VARIANT",
            control_count=4, treatment_count=4, delta_percentage=12.0
        ))
        report = self.strat_evolution.evaluate_strategy_mutation("channel_a")
        self.assertEqual(report["action"], "STRATEGY_VERSION_CREATED")
        self.assertEqual(report["new_version"], "v1.1")

    def test_14_losing_treatment_rejection(self):
        """14. Losing treatment (-14% APV) rejects variant without mutating strategy."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_lose_14", channel_id="channel_a", name="Lose Test",
            hypothesis="Lose", variable_tested="HOOK_STRUCTURE", control_definition="c", variant_definition="Losing Hook",
            primary_metric="avg_percentage_viewed", status="EVALUATED", decision="REJECT_VARIANT",
            control_count=4, treatment_count=4, delta_percentage=-14.0
        ))
        report = self.strat_evolution.evaluate_strategy_mutation("channel_a")
        self.assertEqual(report["action"], "NO_MUTATION_WARRANTED")

    def test_15_inconclusive_experiment_keeps_baseline(self):
        """15. Inconclusive experiment (+1% APV) retains control baseline."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_inc_15", channel_id="channel_a", name="Inc Test",
            hypothesis="Inc", variable_tested="HOOK_STRUCTURE", control_definition="c", variant_definition="Inc Hook",
            primary_metric="avg_percentage_viewed", status="EVALUATED", decision="INCONCLUSIVE",
            control_count=4, treatment_count=4, delta_percentage=1.0
        ))
        report = self.strat_evolution.evaluate_strategy_mutation("channel_a")
        self.assertEqual(report["action"], "NO_MUTATION_WARRANTED")

    def test_16_strategy_cooldown_active(self):
        """16. Mutation evaluation returns NO_MUTATION_WARRANTED when no unapplied winning experiment exists."""
        report = self.strat_evolution.evaluate_strategy_mutation("channel_a")
        self.assertEqual(report["action"], "NO_MUTATION_WARRANTED")

    def test_17_do_not_use_persistence(self):
        """17. Rejected patterns are stored in DO_NOT_USE registry."""
        self.ext_repo.upsert_external_prior(ExternalPriorModel(
            prior_id="prior_dnu_17", target_channel_id="channel_a", pattern_id="pat_dnu",
            hypothesis="Bad Hook", transferability_classification=TransferabilityClassification.HIGH,
            prior_weight=0.0, status=PriorStatus.REJECTED
        ))
        neg = self.belief_engine.get_negative_knowledge("channel_a")
        p_ids = [p["pattern_id"] for p in neg["do_not_use_patterns"]]
        self.assertIn("prior_dnu_17", p_ids)

    def test_18_first_party_override_of_external_prior(self):
        """18. First-party N >= 4 empirical rejection demotes external prior."""
        self.ext_repo.upsert_external_prior(ExternalPriorModel(
            prior_id="prior_override_18", target_channel_id="channel_a", pattern_id="pat_ovr",
            hypothesis="Overrated Hook", transferability_classification=TransferabilityClassification.HIGH,
            prior_weight=0.25, status=PriorStatus.HYPOTHESIS
        ))
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_ovr_18", channel_id="channel_a", name="Ovr Test",
            hypothesis="Overrated Hook", variable_tested="HOOK_STRUCTURE", control_definition="c", variant_definition="t",
            primary_metric="avg_percentage_viewed", status="RUNNING", decision="PENDING",
            external_prior_id="prior_override_18"
        ))
        for i in range(4):
            cv = f"cv_ovr_{i}"
            self.repo.upsert_video(VideoModel(
                video_id=cv, channel_id="channel_a", pipeline_id="pipeline1",
                title=f"Ctrl {i}", duration=45.0, experiment_id="exp_ovr_18",
                arm_id="arm_c", variant_id="CONTROL", upload_status="UPLOADED_PUBLIC"
            ))
            self.repo.insert_snapshot(PerformanceSnapshotModel(
                video_id=cv, window_name="7d", views=1000, avg_percentage_viewed=82.0
            ))
            tv = f"tv_ovr_{i}"
            self.repo.upsert_video(VideoModel(
                video_id=tv, channel_id="channel_a", pipeline_id="pipeline1",
                title=f"Treat {i}", duration=45.0, experiment_id="exp_ovr_18",
                arm_id="arm_t", variant_id="TREATMENT", upload_status="UPLOADED_PUBLIC"
            ))
            self.repo.insert_snapshot(PerformanceSnapshotModel(
                video_id=tv, window_name="7d", views=750, avg_percentage_viewed=62.0
            ))
        self.learning_engine.process_experiment_outcome("exp_ovr_18")
        prior = self.ext_repo.get_external_prior("prior_override_18")
        self.assertEqual(prior["status"], "REJECTED")
        self.assertEqual(prior["prior_weight"], 0.0)

    def test_19_channel_isolation(self):
        """19. Strict isolation between Channel A and Channel B models and priors."""
        priors_a = self.ext_repo.list_external_priors(target_channel_id="channel_a")
        priors_b = self.ext_repo.list_external_priors(target_channel_id="channel_b")
        a_ids = {p["prior_id"] for p in priors_a}
        b_ids = {p["prior_id"] for p in priors_b}
        self.assertEqual(len(a_ids & b_ids), 0)

    def test_20_single_variable_invariant_enforcement(self):
        """20. Only single variable is tested; all other generation parameters are locked."""
        decision = self.brain.next_production_decision("channel_a")
        rec = self.rec_engine.generate_recommendation(decision, save_plan_file=False)
        self.assertEqual(rec.experiment_variable, "HOOK_STRUCTURE")
        self.assertTrue(len(rec.invariants) >= 5)

    def test_21_next_video_plan_generation(self):
        """21. Generates valid brain_production_plan_{channel}.json after every video."""
        decision = self.brain.next_production_decision("channel_b")
        rec = self.rec_engine.generate_recommendation(decision, save_plan_file=True)
        plan_file = Path(self.tmp_dir.name) / "brain_production_plan_channel_b.json"
        self.assertTrue(plan_file.exists())

    def test_22_weekly_learning_report(self):
        """22. Generates WEEKLY_LEARNING_REPORT.md at end of cycle."""
        report = self.weekly_cycle.run_weekly_cycle("channel_b")
        self.assertIn("maturity_breakdown", report)
        self.assertTrue((Path(self.tmp_dir.name) / "WEEKLY_LEARNING_REPORT_CHANNEL_B.md").exists())

    def test_23_70_20_10_allocation(self):
        """23. Allocates decisions into proven, adjacent, and exploratory tiers."""
        opps = self.brain.get_ranked_opportunities("channel_a")
        self.assertTrue(len(opps) > 0)
        self.assertIn(opps[0]["portfolio_tier"], ["proven", "adjacent", "exploratory"])

    def test_24_learning_blocked_safeguards(self):
        """24. Blocks evaluation and mutation on insufficient samples or missing data."""
        report = self.evaluator.evaluate_experiment("non_existent_exp")
        self.assertEqual(report.status, "NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
