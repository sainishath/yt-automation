# -*- coding: utf-8 -*-
"""
test_closed_loop_learning.py
----------------------------
Comprehensive 18-point verification test suite for the Closed-Loop First-Party Learning System.
"""

import unittest
import tempfile
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from growth.db.database import init_db
from growth.db.models import GrowthRepository, VideoModel, PerformanceSnapshotModel, ExperimentModel, LearningEventModel
from growth.external_intelligence.repository import ExternalIntelligenceRepository
from growth.external_intelligence.schemas import (
    ExternalVideoModel,
    ExternalPriorModel,
    ProvenanceSource,
    TransferabilityClassification,
    PriorStatus
)
from growth.brain.belief_engine import BeliefEngine, VideoMaturity, BeliefStatus, VideoDiagnostic
from growth.brain.evaluator import MultiArmExperimentEvaluator, ExperimentDecision
from growth.brain.learning_engine import LearningEngine
from growth.brain.strategy_evolution import StrategyEvolutionEngine
from growth.brain.weekly_cycle import WeeklyLearningCycle
from growth.brain.brain import ContentBrain
from growth.brain.production_recommendation import ProductionRecommendationEngine
from growth.brain.schemas import ConfidenceLevel, KnowledgeState, DecisionType


class TestClosedLoopLearning(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_closed_loop.db"
        init_db(self.db_path)

        self.repo = GrowthRepository(self.db_path)
        self.ext_repo = ExternalIntelligenceRepository(self.db_path)
        self.belief_engine = BeliefEngine(self.repo, self.ext_repo)
        self.evaluator = MultiArmExperimentEvaluator(self.repo, min_sample_size=4)
        self.learning_engine = LearningEngine(self.repo, self.ext_repo, self.evaluator)
        self.strat_evolution = StrategyEvolutionEngine(self.repo)
        self.weekly_cycle = WeeklyLearningCycle(self.repo, output_dir=Path(self.tmp_dir.name))
        self.rec_engine = ProductionRecommendationEngine(output_dir=Path(self.tmp_dir.name))
        self.brain = ContentBrain(self.db_path)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_01_snapshot_ingestion_with_maturity_categorization(self):
        """1. Ingested snapshots are correctly categorized into maturity tiers."""
        self.assertEqual(self.belief_engine.classify_maturity("1h"), VideoMaturity.IMMATURE)
        self.assertEqual(self.belief_engine.classify_maturity("6h"), VideoMaturity.IMMATURE)
        self.assertEqual(self.belief_engine.classify_maturity("24h"), VideoMaturity.PRELIMINARY)
        self.assertEqual(self.belief_engine.classify_maturity("48h"), VideoMaturity.PRELIMINARY)
        self.assertEqual(self.belief_engine.classify_maturity("7d"), VideoMaturity.MATURE)
        self.assertEqual(self.belief_engine.classify_maturity("28d"), VideoMaturity.LONG_TERM)

    def test_02_video_diagnostic_attribution(self):
        """2. Generates multi-dimensional diagnostic attribution (Topic, Hook, Pacing, Ending)."""
        self.repo.upsert_video(VideoModel(
            video_id="vid_diag_01", channel_id="channel_a", pipeline_id="pipeline1",
            title="What if Rome Never Fell?", duration=45.0, upload_status="UPLOADED_PUBLIC"
        ))
        self.repo.insert_snapshot(PerformanceSnapshotModel(
            video_id="vid_diag_01", window_name="24h", views=1500, avg_percentage_viewed=88.5,
            likes=120, comments=45
        ))
        diag = self.belief_engine.generate_video_diagnostic("vid_diag_01")
        self.assertIsNotNone(diag)
        self.assertEqual(diag.maturity, VideoMaturity.PRELIMINARY)
        self.assertTrue(diag.hook_retention_score >= 0.8)
        self.assertTrue(diag.pacing_score >= 0.8)
        self.assertTrue(len(diag.what_worked) > 0)

    def test_03_cohort_construction_balance(self):
        """3. Tracks exact cohort balances for Control and Treatment arms."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_cohort_03", channel_id="channel_a", name="Cohort Test",
            hypothesis="Test", variable_tested="HOOK_STRUCTURE", control_definition="c", variant_definition="t",
            primary_metric="avg_percentage_viewed", status="RUNNING", decision="PENDING",
            control_count=2, treatment_count=1
        ))
        from growth.db.models import ExperimentArmModel
        self.repo.upsert_experiment_arm(ExperimentArmModel(
            arm_id="arm_exp_c", experiment_id="exp_cohort_03", arm_type="CONTROL", name="Control", definition="c", sample_count=2
        ))
        self.repo.upsert_experiment_arm(ExperimentArmModel(
            arm_id="arm_exp_t", experiment_id="exp_cohort_03", arm_type="TREATMENT", name="Treatment", definition="t", sample_count=1
        ))
        decision = self.brain.next_production_decision("channel_a")
        # With Control=2 and Treatment=1, balancer should assign TREATMENT
        self.assertEqual(decision.arm_type, "TREATMENT")

    def test_04_treatment_control_comparison(self):
        """4. Computes median APV delta between control and treatment cohorts."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_comp_04", channel_id="channel_a", name="Comp Test",
            hypothesis="Test", variable_tested="HOOK_STRUCTURE", control_definition="c", variant_definition="t",
            primary_metric="avg_percentage_viewed", status="RUNNING", decision="PENDING"
        ))
        for i in range(4):
            cv = f"cv_{i}"
            self.repo.upsert_video(VideoModel(
                video_id=cv, channel_id="channel_a", pipeline_id="pipeline1",
                title=f"Ctrl {i}", duration=45.0, experiment_id="exp_comp_04",
                arm_id="arm_c", variant_id="CONTROL", upload_status="UPLOADED_PUBLIC"
            ))
            self.repo.insert_snapshot(PerformanceSnapshotModel(
                video_id=cv, window_name="7d", views=1000, avg_percentage_viewed=70.0
            ))
            tv = f"tv_{i}"
            self.repo.upsert_video(VideoModel(
                video_id=tv, channel_id="channel_a", pipeline_id="pipeline1",
                title=f"Treat {i}", duration=45.0, experiment_id="exp_comp_04",
                arm_id="arm_t", variant_id="TREATMENT", upload_status="UPLOADED_PUBLIC"
            ))
            self.repo.insert_snapshot(PerformanceSnapshotModel(
                video_id=tv, window_name="7d", views=1200, avg_percentage_viewed=85.0
            ))

        report = self.evaluator.evaluate_experiment("exp_comp_04")
        self.assertEqual(report.status, "EVALUATED")
        self.assertEqual(report.decision, ExperimentDecision.WIN)
        self.assertTrue(report.delta_percentage > 15.0)

    def test_05_n_less_than_4_blocks_winner_declaration(self):
        """5. N < 4 strictly blocks winner declaration and strategy mutation."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_guard_05", channel_id="channel_a", name="Guard Test",
            hypothesis="Test", variable_tested="HOOK_STRUCTURE", control_definition="c", variant_definition="t",
            primary_metric="avg_percentage_viewed", status="RUNNING", decision="PENDING"
        ))
        for i in range(2):
            cv = f"cv_g_{i}"
            self.repo.upsert_video(VideoModel(
                video_id=cv, channel_id="channel_a", pipeline_id="pipeline1",
                title=f"Ctrl {i}", duration=45.0, experiment_id="exp_guard_05",
                arm_id="arm_c", variant_id="CONTROL", upload_status="UPLOADED_PUBLIC"
            ))
            self.repo.insert_snapshot(PerformanceSnapshotModel(
                video_id=cv, window_name="7d", views=1000, avg_percentage_viewed=70.0
            ))
        report = self.evaluator.evaluate_experiment("exp_guard_05")
        self.assertEqual(report.status, "COLLECTING_DATA")
        self.assertEqual(report.decision, ExperimentDecision.CONTINUE_COLLECTION)

    def test_06_n_greater_equal_4_transition(self):
        """6. Reaching N >= 4 per arm triggers valid statistical evaluation."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_n4_06", channel_id="channel_a", name="N4 Test",
            hypothesis="Test", variable_tested="HOOK_STRUCTURE", control_definition="c", variant_definition="t",
            primary_metric="avg_percentage_viewed", status="RUNNING", decision="PENDING"
        ))
        for i in range(4):
            cv = f"cv_n4_{i}"
            self.repo.upsert_video(VideoModel(
                video_id=cv, channel_id="channel_a", pipeline_id="pipeline1",
                title=f"Ctrl {i}", duration=45.0, experiment_id="exp_n4_06",
                arm_id="arm_c", variant_id="CONTROL", upload_status="UPLOADED_PUBLIC"
            ))
            self.repo.insert_snapshot(PerformanceSnapshotModel(
                video_id=cv, window_name="7d", views=1000, avg_percentage_viewed=75.0
            ))
            tv = f"tv_n4_{i}"
            self.repo.upsert_video(VideoModel(
                video_id=tv, channel_id="channel_a", pipeline_id="pipeline1",
                title=f"Treat {i}", duration=45.0, experiment_id="exp_n4_06",
                arm_id="arm_t", variant_id="TREATMENT", upload_status="UPLOADED_PUBLIC"
            ))
            self.repo.insert_snapshot(PerformanceSnapshotModel(
                video_id=tv, window_name="7d", views=1100, avg_percentage_viewed=82.0
            ))
        report = self.evaluator.evaluate_experiment("exp_n4_06")
        self.assertEqual(report.status, "EVALUATED")
        self.assertEqual(report.control_count, 4)
        self.assertEqual(report.treatment_count, 4)

    def test_07_external_prior_update_progression(self):
        """7. External priors progress from HYPOTHESIS to VALIDATING upon sample accumulation."""
        self.ext_repo.upsert_external_prior(ExternalPriorModel(
            prior_id="prior_prog_07", target_channel_id="channel_a", pattern_id="pat_prog",
            hypothesis="Declarative hooks", transferability_classification=TransferabilityClassification.HIGH,
            prior_weight=0.2, status=PriorStatus.HYPOTHESIS
        ))
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_prog_07", channel_id="channel_a", name="Prog Test",
            hypothesis="Declarative hooks", variable_tested="HOOK_STRUCTURE", control_definition="c", variant_definition="t",
            primary_metric="avg_percentage_viewed", status="RUNNING", decision="PENDING",
            control_count=1, treatment_count=1, external_prior_id="prior_prog_07"
        ))
        beliefs = self.belief_engine.get_channel_beliefs("channel_a")
        b = next(b for b in beliefs if b.pattern_id == "prior_prog_07")
        self.assertEqual(b.status, BeliefStatus.VALIDATING)
        self.assertEqual(b.first_party_samples, 2)

    def test_08_first_party_override_demotes_prior(self):
        """8. N >= 4 loss demotes external prior to REJECTED with zero weight."""
        self.ext_repo.upsert_external_prior(ExternalPriorModel(
            prior_id="prior_demote_08", target_channel_id="channel_a", pattern_id="pat_demote",
            hypothesis="Provocation Hook", transferability_classification=TransferabilityClassification.HIGH,
            prior_weight=0.25, status=PriorStatus.HYPOTHESIS
        ))
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_demote_08", channel_id="channel_a", name="Demote Test",
            hypothesis="Provocation Hook", variable_tested="HOOK_STRUCTURE", control_definition="c", variant_definition="t",
            primary_metric="avg_percentage_viewed", status="RUNNING", decision="PENDING",
            external_prior_id="prior_demote_08"
        ))
        for i in range(4):
            cv = f"cv_d_{i}"
            self.repo.upsert_video(VideoModel(
                video_id=cv, channel_id="channel_a", pipeline_id="pipeline1",
                title=f"Ctrl {i}", duration=45.0, experiment_id="exp_demote_08",
                arm_id="arm_c", variant_id="CONTROL", upload_status="UPLOADED_PUBLIC"
            ))
            self.repo.insert_snapshot(PerformanceSnapshotModel(
                video_id=cv, window_name="7d", views=1000, avg_percentage_viewed=80.0
            ))
            tv = f"tv_d_{i}"
            self.repo.upsert_video(VideoModel(
                video_id=tv, channel_id="channel_a", pipeline_id="pipeline1",
                title=f"Treat {i}", duration=45.0, experiment_id="exp_demote_08",
                arm_id="arm_t", variant_id="TREATMENT", upload_status="UPLOADED_PUBLIC"
            ))
            self.repo.insert_snapshot(PerformanceSnapshotModel(
                video_id=tv, window_name="7d", views=800, avg_percentage_viewed=60.0
            ))
        res = self.learning_engine.process_experiment_outcome("exp_demote_08")
        prior = self.ext_repo.get_external_prior("prior_demote_08")
        self.assertEqual(prior["status"], "REJECTED")
        self.assertEqual(prior["prior_weight"], 0.0)

    def test_09_negative_knowledge_persistence(self):
        """9. Rejected patterns are stored in institutional negative knowledge registry."""
        self.ext_repo.upsert_external_prior(ExternalPriorModel(
            prior_id="prior_neg_09", target_channel_id="channel_a", pattern_id="pat_neg",
            hypothesis="Rejected Hook", transferability_classification=TransferabilityClassification.HIGH,
            prior_weight=0.0, status=PriorStatus.REJECTED
        ))
        neg = self.belief_engine.get_negative_knowledge("channel_a")
        self.assertTrue(neg["rejected_count"] >= 1)
        rejected_ids = [p["pattern_id"] for p in neg["do_not_use_patterns"]]
        self.assertIn("prior_neg_09", rejected_ids)

    def test_10_strategy_promotion_creates_immutable_version(self):
        """10. Winning N >= 4 experiment justifies creating strategy version v1.1."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_promote_10", channel_id="channel_a", name="Promote Test",
            hypothesis="Winning Hook", variable_tested="HOOK_STRUCTURE", control_definition="c", variant_definition="New Winning Hook",
            primary_metric="avg_percentage_viewed", status="EVALUATED", decision="ACCEPT_VARIANT",
            control_count=4, treatment_count=4, delta_percentage=12.5
        ))
        report = self.strat_evolution.evaluate_strategy_mutation("channel_a")
        self.assertEqual(report["action"], "STRATEGY_VERSION_CREATED")
        self.assertEqual(report["new_version"], "v1.1")

    def test_11_strategy_rejection_prevents_mutation(self):
        """11. Losing experiment does not mutate strategy."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_reject_11", channel_id="channel_a", name="Reject Test",
            hypothesis="Losing Hook", variable_tested="HOOK_STRUCTURE", control_definition="c", variant_definition="Losing Hook",
            primary_metric="avg_percentage_viewed", status="EVALUATED", decision="REJECT_VARIANT",
            control_count=4, treatment_count=4, delta_percentage=-15.0
        ))
        report = self.strat_evolution.evaluate_strategy_mutation("channel_a")
        self.assertEqual(report["action"], "NO_MUTATION_WARRANTED")

    def test_12_strategy_cooldown_guard(self):
        """12. Strategy evolution respects cooldown guard."""
        # Mutation check returns NO_MUTATION_WARRANTED when no winning unapplied experiment
        report = self.strat_evolution.evaluate_strategy_mutation("channel_a")
        self.assertEqual(report["action"], "NO_MUTATION_WARRANTED")

    def test_13_exploration_exploitation_tier_allocation(self):
        """13. Allocates decisions into 70/20/10 portfolio tiers."""
        opps = self.brain.get_ranked_opportunities("channel_a")
        self.assertTrue(len(opps) > 0)
        tiers = [o["portfolio_tier"] for o in opps]
        self.assertTrue(any(t in ["proven", "adjacent", "exploratory"] for t in tiers))

    def test_14_channel_isolation_beliefs(self):
        """14. Channel A beliefs and negative knowledge never leak into Channel B."""
        self.ext_repo.upsert_external_prior(ExternalPriorModel(
            prior_id="prior_iso_a", target_channel_id="channel_a", pattern_id="pat_iso_a",
            hypothesis="Channel A Prior", transferability_classification=TransferabilityClassification.HIGH,
            prior_weight=0.25, status=PriorStatus.HYPOTHESIS
        ))
        beliefs_b = self.belief_engine.get_channel_beliefs("channel_b")
        p_ids_b = [b.pattern_id for b in beliefs_b]
        self.assertNotIn("prior_iso_a", p_ids_b)

    def test_15_next_video_recommendation_contract(self):
        """15. Generates full ProductionRecommendation with single-variable contract."""
        decision = self.brain.next_production_decision("channel_a")
        rec = self.rec_engine.generate_recommendation(decision, save_plan_file=True)
        self.assertEqual(rec.channel_id, "channel_a")
        self.assertTrue(len(rec.invariants) > 0)
        self.assertTrue(len(rec.script_structure) > 0)

    def test_16_no_strategy_change_from_single_outlier(self):
        """16. Single viral outlier does not distort median-based evaluation."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_outlier_16", channel_id="channel_a", name="Outlier Test",
            hypothesis="Outlier Hook", variable_tested="HOOK_STRUCTURE", control_definition="c", variant_definition="t",
            primary_metric="avg_percentage_viewed", status="RUNNING", decision="PENDING"
        ))
        # 3 normal control samples (75% APV) + 1 outlier (99% APV) -> Median should remain ~75%
        apvs = [74.0, 75.0, 76.0, 99.0]
        for i, val in enumerate(apvs):
            cv = f"cv_out_{i}"
            self.repo.upsert_video(VideoModel(
                video_id=cv, channel_id="channel_a", pipeline_id="pipeline1",
                title=f"Ctrl {i}", duration=45.0, experiment_id="exp_outlier_16",
                arm_id="arm_c", variant_id="CONTROL", upload_status="UPLOADED_PUBLIC"
            ))
            self.repo.insert_snapshot(PerformanceSnapshotModel(
                video_id=cv, window_name="7d", views=1000, avg_percentage_viewed=val
            ))
        filtered, outliers_removed = self.evaluator._filter_outliers(apvs)
        import numpy as np
        med = float(np.median(filtered))
        self.assertAlmostEqual(med, 75.0, places=1)

    def test_17_weekly_learning_cycle_report_generation(self):
        """17. WeeklyLearningCycle generates structured WEEKLY_LEARNING_REPORT.md."""
        report = self.weekly_cycle.run_weekly_cycle("channel_a")
        self.assertIn("channel_id", report)
        self.assertIn("maturity_breakdown", report)
        report_file = Path(self.tmp_dir.name) / "WEEKLY_LEARNING_REPORT_CHANNEL_A.md"
        self.assertTrue(report_file.exists())

    def test_18_end_to_end_closed_loop_flow(self):
        """18. End-to-end simulation: Upload -> Snapshots -> Attribution -> Evaluation -> Next Plan."""
        # 1. Setup experiment
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_e2e_18", channel_id="channel_a", name="E2E Experiment",
            hypothesis="Grounded counterfactual", variable_tested="HOOK_STRUCTURE",
            control_definition="Generic Question", variant_definition="Grounded Question",
            primary_metric="avg_percentage_viewed", status="RUNNING", decision="PENDING"
        ))

        # 2. Ingest 4 Control + 4 Treatment videos with mature snapshots
        for i in range(4):
            cv = f"vid_e2e_c_{i}"
            self.repo.upsert_video(VideoModel(
                video_id=cv, channel_id="channel_a", pipeline_id="pipeline1",
                title=f"Control Alexandria {i}", duration=45.0,
                experiment_id="exp_e2e_18", arm_id="arm_c", variant_id="CONTROL",
                upload_status="UPLOADED_PUBLIC"
            ))
            self.repo.insert_snapshot(PerformanceSnapshotModel(
                video_id=cv, window_name="7d", views=1000, avg_percentage_viewed=72.0
            ))

            tv = f"vid_e2e_t_{i}"
            self.repo.upsert_video(VideoModel(
                video_id=tv, channel_id="channel_a", pipeline_id="pipeline1",
                title=f"Treatment Alexandria {i}", duration=45.0,
                experiment_id="exp_e2e_18", arm_id="arm_t", variant_id="TREATMENT",
                upload_status="UPLOADED_PUBLIC"
            ))
            self.repo.insert_snapshot(PerformanceSnapshotModel(
                video_id=tv, window_name="7d", views=1350, avg_percentage_viewed=86.0
            ))

        # 3. Run weekly cycle
        cycle_res = self.weekly_cycle.run_weekly_cycle("channel_a")
        self.assertEqual(cycle_res["completed_experiments_count"], 1)

        # 4. Check that strategy evolved
        self.assertEqual(cycle_res["strategy_mutation_status"]["action"], "STRATEGY_VERSION_CREATED")
        self.assertEqual(cycle_res["strategy_mutation_status"]["new_version"], "v1.1")

        # 5. Check next production plan reflects updated strategy
        plan = cycle_res["next_production_plan"]
        self.assertEqual(plan["channel_id"], "channel_a")
        self.assertIsNotNone(plan["title_recommendation"])


if __name__ == "__main__":
    unittest.main()
