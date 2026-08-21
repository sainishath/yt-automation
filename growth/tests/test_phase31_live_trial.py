# -*- coding: utf-8 -*-
"""
test_phase31_live_trial.py
--------------------------
Phase 31: Live First-Party Learning Trial & Closed-Loop Validation Test Suite.
Verifies the operational trial invariants, causal learning traces, topic confounding
protection, and simulated 30-day multi-cohort progression.
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
from growth.db.models import (
    GrowthRepository,
    VideoModel,
    PerformanceSnapshotModel,
    ExperimentModel,
    ExperimentArmModel,
    LearningEventModel
)
from growth.external_intelligence.repository import ExternalIntelligenceRepository
from growth.brain.belief_engine import BeliefEngine, VideoMaturity, BeliefStatus
from growth.brain.learning_trace import LearningTraceEngine, VideoLearningTrace
from growth.brain.evaluator import MultiArmExperimentEvaluator, ExperimentDecision
from growth.brain.learning_engine import LearningEngine
from growth.brain.strategy_evolution import StrategyEvolutionEngine
from growth.brain.brain import ContentBrain
from growth.brain.schemas import ConfidenceLevel, DecisionType


class TestPhase31LiveTrial(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_phase31.db"
        init_db(self.db_path)

        self.repo = GrowthRepository(self.db_path)
        self.ext_repo = ExternalIntelligenceRepository(self.db_path)
        self.belief_engine = BeliefEngine(self.repo, self.ext_repo)
        self.trace_engine = LearningTraceEngine(self.repo)
        self.evaluator = MultiArmExperimentEvaluator(self.repo, min_sample_size=4)
        self.learning_engine = LearningEngine(self.repo, self.ext_repo, self.evaluator)
        self.strat_evolution = StrategyEvolutionEngine(self.repo)
        self.brain = ContentBrain(self.db_path)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_01_live_learning_status_schema(self):
        """1. Validates get_live_learning_status returns all required operational monitoring fields."""
        status = self.brain.get_live_learning_status("channel_a")
        self.assertIn("channel_id", status)
        self.assertIn("strategy_version", status)
        self.assertIn("videos_published", status)
        self.assertIn("videos_mature", status)
        self.assertIn("next_video_plan", status)
        self.assertIn("data_quality", status)
        self.assertEqual(status["data_quality"]["status"], "HEALTHY")

    def test_02_video_learning_trace_generation(self):
        """2. Constructs a full 9-point causal learning trace for a published video."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_trace_02", channel_id="channel_a", name="Trace Test",
            hypothesis="Test", variable_tested="HOOK_STRUCTURE", control_definition="Standard Hook",
            variant_definition="Counterfactual Hook", primary_metric="avg_percentage_viewed",
            status="RUNNING", decision="PENDING"
        ))
        self.repo.upsert_video(VideoModel(
            video_id="vid_trace_02", channel_id="channel_a", pipeline_id="pipeline1",
            title="Alexandria Turning Point", duration=45.0, experiment_id="exp_trace_02",
            arm_id="arm_t", variant_id="TREATMENT", upload_status="UPLOADED_PUBLIC",
            youtube_video_id="YT_TR_02"
        ))
        self.repo.insert_snapshot(PerformanceSnapshotModel(
            video_id="vid_trace_02", window_name="1h", views=12, avg_percentage_viewed=72.0
        ))

        trace = self.trace_engine.generate_trace_for_video("vid_trace_02")
        self.assertIsNotNone(trace)
        self.assertEqual(trace.video_id, "vid_trace_02")
        self.assertEqual(trace.arm_type, "TREATMENT")
        self.assertEqual(trace.variable_under_test, "HOOK_STRUCTURE")
        self.assertEqual(trace.maturity_tier, "IMMATURE")
        self.assertTrue(len(trace.locked_invariants) >= 5)
        self.assertIn("Strategy remains locked", trace.subsequent_decisions_impact)

    def test_03_topic_confounding_isolation(self):
        """3. Verifies single-variable invariant locks topic cluster across arms."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_conf_03", channel_id="channel_a", name="Conf Test",
            hypothesis="Hook Test", variable_tested="HOOK_STRUCTURE",
            control_definition="Baseline", variant_definition="Counterfactual",
            primary_metric="avg_percentage_viewed", status="RUNNING", decision="PENDING"
        ))
        decision = self.brain.next_production_decision("channel_a")
        self.assertEqual(decision.variable_under_test, "HOOK_STRUCTURE")
        # Invariants explicitly freeze non-hook attributes
        self.assertTrue(any("Visual Art" in inv for inv in decision.invariants))
        self.assertTrue(any("Voice" in inv for inv in decision.invariants))
        self.assertTrue(any("Duration" in inv for inv in decision.invariants))

    def test_04_continuous_diagnostics_without_strategy_mutation(self):
        """4. Continuous 1h, 6h, 24h, 48h snapshots record diagnostics but never mutate strategy."""
        self.repo.upsert_video(VideoModel(
            video_id="vid_diag_04", channel_id="channel_a", pipeline_id="pipeline1",
            title="Diag Test", duration=45.0, upload_status="UPLOADED_PUBLIC"
        ))
        for win, views, apv in [("1h", 15, 60.0), ("6h", 80, 65.0), ("24h", 400, 70.0), ("48h", 850, 72.0)]:
            self.repo.insert_snapshot(PerformanceSnapshotModel(
                video_id="vid_diag_04", window_name=win, views=views, avg_percentage_viewed=apv
            ))
            diag = self.belief_engine.generate_video_diagnostic("vid_diag_04")
            self.assertIsNotNone(diag)
            # Ensure strategy evolution refuses mutation
            strat_rep = self.strat_evolution.evaluate_strategy_mutation("channel_a")
            self.assertEqual(strat_rep["action"], "NO_MUTATION_WARRANTED")

    def test_05_simulated_30_day_trial_cohort_progression(self):
        """5. Simulates 30-day publishing cadence: Day 1-7 collection, Day 8 evaluation upon N=4 per arm."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_trial_05", channel_id="channel_a", name="Trial Exp",
            hypothesis="Counterfactual Hook Lift", variable_tested="HOOK_STRUCTURE",
            control_definition="Baseline", variant_definition="Counterfactual",
            primary_metric="avg_percentage_viewed", status="RUNNING", decision="PENDING"
        ))
        self.repo.upsert_experiment_arm(ExperimentArmModel(
            arm_id="arm_trial_c", experiment_id="exp_trial_05", arm_type="CONTROL", name="Control", definition="c", sample_count=0
        ))
        self.repo.upsert_experiment_arm(ExperimentArmModel(
            arm_id="arm_trial_t", experiment_id="exp_trial_05", arm_type="TREATMENT", name="Treatment", definition="t", sample_count=0
        ))

        # Days 1 to 8: Alternating Control and Treatment
        for day in range(1, 9):
            is_treat = (day % 2 == 1)
            arm = "TREATMENT" if is_treat else "CONTROL"
            arm_id = "arm_trial_t" if is_treat else "arm_trial_c"
            vid_id = f"vid_day_{day:02d}"

            self.repo.upsert_video(VideoModel(
                video_id=vid_id, channel_id="channel_a", pipeline_id="pipeline1",
                title=f"Video Day {day}", duration=45.0, experiment_id="exp_trial_05",
                arm_id=arm_id, variant_id=arm, upload_status="UPLOADED_PUBLIC"
            ))
            self.repo.increment_arm_sample_count(arm_id)

            # Insert mature 7d snapshots (Treatment: 85% APV, Control: 70% APV)
            apv = 85.0 if is_treat else 70.0
            self.repo.insert_snapshot(PerformanceSnapshotModel(
                video_id=vid_id, window_name="7d", views=1000 + day * 50, avg_percentage_viewed=apv
            ))

        # At Day 8: Both arms have reached N=4 mature samples
        report = self.evaluator.evaluate_experiment("exp_trial_05")
        self.assertEqual(report.status, "EVALUATED")
        self.assertEqual(report.decision, ExperimentDecision.WIN)
        self.assertTrue(report.delta_percentage > 15.0)

        # Trigger Strategy Evolution
        strat_report = self.strat_evolution.evaluate_strategy_mutation("channel_a")
        self.assertEqual(strat_report["action"], "STRATEGY_VERSION_CREATED")
        self.assertEqual(strat_report["new_version"], "v1.1")

    def test_06_missing_metrics_resilience(self):
        """6. Missing metrics in snapshots are marked pending and do not crash diagnostics."""
        self.repo.upsert_video(VideoModel(
            video_id="vid_missing_06", channel_id="channel_a", pipeline_id="pipeline1",
            title="Missing Metrics Video", duration=45.0, upload_status="UPLOADED_PUBLIC"
        ))
        self.repo.insert_snapshot(PerformanceSnapshotModel(
            video_id="vid_missing_06", window_name="1h", views=5, avg_percentage_viewed=None
        ))
        status = self.brain.get_live_learning_status("channel_a")
        self.assertEqual(status["data_quality"]["status"], "DATA_PENDING")
        self.assertEqual(status["data_quality"]["missing_metrics"], 1)


if __name__ == "__main__":
    unittest.main()
