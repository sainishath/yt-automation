# -*- coding: utf-8 -*-
"""
test_brain_closed_loop.py
-------------------------
Comprehensive test suite for Closed-Loop Content Intelligence (Phases 12 - 26).
Validates Multi-Arm Evaluation, Outlier Protection, Learning Engine, First-Party Overrides,
Strategy Evolution Immutability, Memory V2 Knowledge States, and Idempotent Daily Cycle.
"""

import unittest
import tempfile
import json
import sys
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from growth.db.database import init_db
from growth.db.models import (
    GrowthRepository,
    ChannelModel,
    VideoModel,
    ExperimentModel,
    ExperimentArmModel,
    PerformanceSnapshotModel,
    LearningEventModel
)
from growth.external_intelligence.repository import ExternalIntelligenceRepository
from growth.external_intelligence.schemas import (
    ExternalPriorModel,
    PriorStatus,
    TransferabilityClassification
)
from growth.brain.evaluator import MultiArmExperimentEvaluator, ExperimentDecision
from growth.brain.learning_engine import LearningEngine
from growth.brain.strategy_evolution import StrategyEvolutionEngine
from growth.brain.brain import ContentBrain
from growth.brain.cycle import DailyBrainCycle


class TestBrainClosedLoop(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_closed_loop.db"
        init_db(self.db_path)

        self.repo = GrowthRepository(self.db_path)
        self.ext_repo = ExternalIntelligenceRepository(self.db_path)

        # Seed test channels
        self.repo.upsert_channel(ChannelModel(
            channel_id="channel_a",
            name="Chronos Shift",
            handle="@ChronosShift",
            pipeline_id="alternate-history-shorts",
            content_category="Alternate History"
        ))
        self.repo.upsert_channel(ChannelModel(
            channel_id="channel_b",
            name="Debate Protocol",
            handle="@DebateProtocol",
            pipeline_id="convo-shorts",
            content_category="Debates & Philosophy"
        ))

        self.evaluator = MultiArmExperimentEvaluator(self.repo)
        self.learning_engine = LearningEngine(self.repo, self.ext_repo, self.evaluator)
        self.strat_dir = Path(self.tmp_dir.name) / "strategies"
        self.strat_dir.mkdir(parents=True, exist_ok=True)

        # Seed initial strategy files
        for ch in ["channel_a", "channel_b"]:
            strat_json = {
                "channel_id": ch,
                "strategy_version": "v1.0",
                "name": f"{ch} Baseline",
                "winning_patterns": {"topics": ["General"], "hooks": ["Standard"]},
                "portfolio_allocation": {"proven": 0.70, "adjacent": 0.20, "exploratory": 0.10}
            }
            with open(self.strat_dir / f"{ch}_strategy_v1.0.json", "w", encoding="utf-8") as f:
                json.dump(strat_json, f, indent=2)

        self.strategy_evolution = StrategyEvolutionEngine(self.repo, self.strat_dir)
        self.brain = ContentBrain(self.db_path)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_01_evaluator_blocks_on_n_less_than_4(self):
        """1. Evaluator returns CONTINUE_COLLECTION when N < 4."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_partial",
            channel_id="channel_a",
            name="Partial Exp",
            hypothesis="Hypothesis",
            variable_tested="HOOK_STRUCTURE",
            control_definition="Ctrl",
            variant_definition="Treat",
            primary_metric="avg_percentage_viewed",
            status="RUNNING"
        ))
        # Insert 2 control videos and 1 treatment video
        for i in range(2):
            vid_id = f"vid_ctrl_{i}"
            self.repo.upsert_video(VideoModel(
                video_id=vid_id, channel_id="channel_a", pipeline_id="alternate-history-shorts",
                title=f"Ctrl {i}", duration=45.0, upload_status="UPLOADED_PUBLIC",
                experiment_id="exp_partial", variant_id="CONTROL"
            ))
            self.repo.insert_snapshot(PerformanceSnapshotModel(video_id=vid_id, window_name="24h", avg_percentage_viewed=70.0))

        vid_id = "vid_treat_0"
        self.repo.upsert_video(VideoModel(
            video_id=vid_id, channel_id="channel_a", pipeline_id="alternate-history-shorts",
            title="Treat 0", duration=45.0, upload_status="UPLOADED_PUBLIC",
            experiment_id="exp_partial", variant_id="TREATMENT"
        ))
        self.repo.insert_snapshot(PerformanceSnapshotModel(video_id=vid_id, window_name="24h", avg_percentage_viewed=80.0))

        report = self.evaluator.evaluate_experiment("exp_partial")
        self.assertEqual(report.decision, ExperimentDecision.CONTINUE_COLLECTION)
        self.assertIn("Insufficient real published samples", report.decision_reason)

    def test_02_evaluator_evaluates_on_n_ge_4_win(self):
        """2. When Control N=4 and Treatment N=4, evaluator calculates delta and returns WIN on +5% APV."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_full_win",
            channel_id="channel_a",
            name="Full Win Exp",
            hypothesis="Hypothesis",
            variable_tested="HOOK_STRUCTURE",
            control_definition="Standard Hook",
            variant_definition="Question Hook",
            primary_metric="avg_percentage_viewed",
            status="RUNNING"
        ))
        # Insert 4 control videos (median 70%)
        for i in range(4):
            vid_id = f"vid_ctrl_w_{i}"
            self.repo.upsert_video(VideoModel(
                video_id=vid_id, channel_id="channel_a", pipeline_id="alternate-history-shorts",
                title=f"Ctrl {i}", duration=45.0, upload_status="UPLOADED_PUBLIC",
                experiment_id="exp_full_win", variant_id="CONTROL"
            ))
            self.repo.insert_snapshot(PerformanceSnapshotModel(video_id=vid_id, window_name="24h", avg_percentage_viewed=70.0 + i))

        # Insert 4 treatment videos (median 80%)
        for i in range(4):
            vid_id = f"vid_treat_w_{i}"
            self.repo.upsert_video(VideoModel(
                video_id=vid_id, channel_id="channel_a", pipeline_id="alternate-history-shorts",
                title=f"Treat {i}", duration=45.0, upload_status="UPLOADED_PUBLIC",
                experiment_id="exp_full_win", variant_id="TREATMENT"
            ))
            self.repo.insert_snapshot(PerformanceSnapshotModel(video_id=vid_id, window_name="24h", avg_percentage_viewed=80.0 + i))

        report = self.evaluator.evaluate_experiment("exp_full_win")
        self.assertEqual(report.decision, ExperimentDecision.WIN)
        self.assertTrue(report.is_statistically_significant)
        self.assertTrue(report.delta_percentage > 5.0)

    def test_03_evaluator_outlier_protection(self):
        """3. Extreme statistical outliers are filtered out from calculation."""
        raw = [70.0, 71.0, 70.5, 72.0, 1500.0]  # 1500 is extreme outlier
        filtered, outliers_count = self.evaluator._filter_outliers(raw)
        self.assertEqual(outliers_count, 1)
        self.assertNotIn(1500.0, filtered)

    def test_04_evaluator_idempotency(self):
        """4. Evaluating multiple times produces identical results."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_idem", channel_id="channel_a", name="Idem Exp", hypothesis="H",
            variable_tested="HOOK_STRUCTURE", control_definition="C", variant_definition="T",
            primary_metric="avg_percentage_viewed", status="RUNNING"
        ))
        for i in range(4):
            vid_c = f"vid_ic_{i}"
            vid_t = f"vid_it_{i}"
            self.repo.upsert_video(VideoModel(video_id=vid_c, channel_id="channel_a", pipeline_id="p1", title="C", duration=45.0, upload_status="UPLOADED_PUBLIC", experiment_id="exp_idem", variant_id="CONTROL"))
            self.repo.upsert_video(VideoModel(video_id=vid_t, channel_id="channel_a", pipeline_id="p1", title="T", duration=45.0, upload_status="UPLOADED_PUBLIC", experiment_id="exp_idem", variant_id="TREATMENT"))
            self.repo.insert_snapshot(PerformanceSnapshotModel(video_id=vid_c, window_name="24h", avg_percentage_viewed=70.0))
            self.repo.insert_snapshot(PerformanceSnapshotModel(video_id=vid_t, window_name="24h", avg_percentage_viewed=80.0))

        r1 = self.evaluator.evaluate_experiment("exp_idem")
        r2 = self.evaluator.evaluate_experiment("exp_idem")
        self.assertEqual(r1.decision, r2.decision)
        self.assertEqual(r1.delta_percentage, r2.delta_percentage)

    def test_05_learning_engine_records_completed_event(self):
        """5. LearningEngine creates EXPERIMENT_COMPLETED and STRATEGY_PROPOSAL on win."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_learn_win", channel_id="channel_a", name="Learn Win", hypothesis="H",
            variable_tested="HOOK_STRUCTURE", control_definition="C", variant_definition="T",
            primary_metric="avg_percentage_viewed", status="RUNNING"
        ))
        for i in range(4):
            vid_c = f"vid_lc_{i}"
            vid_t = f"vid_lt_{i}"
            self.repo.upsert_video(VideoModel(video_id=vid_c, channel_id="channel_a", pipeline_id="p1", title="C", duration=45.0, upload_status="UPLOADED_PUBLIC", experiment_id="exp_learn_win", variant_id="CONTROL"))
            self.repo.upsert_video(VideoModel(video_id=vid_t, channel_id="channel_a", pipeline_id="p1", title="T", duration=45.0, upload_status="UPLOADED_PUBLIC", experiment_id="exp_learn_win", variant_id="TREATMENT"))
            self.repo.insert_snapshot(PerformanceSnapshotModel(video_id=vid_c, window_name="24h", avg_percentage_viewed=65.0))
            self.repo.insert_snapshot(PerformanceSnapshotModel(video_id=vid_t, window_name="24h", avg_percentage_viewed=82.0))

        res = self.learning_engine.process_experiment_outcome("exp_learn_win")
        self.assertEqual(res["action"], "LEARNING_PROCESSED")
        self.assertIn("EXPERIMENT_COMPLETED", res["events_generated"])
        self.assertIn("STRATEGY_PROPOSAL", res["events_generated"])

        events = self.repo.list_learning_events(channel_id="channel_a")
        event_types = [e["event_type"] for e in events]
        self.assertIn("EXPERIMENT_COMPLETED", event_types)
        self.assertIn("STRATEGY_PROPOSAL", event_types)

    def test_06_learning_engine_first_party_override(self):
        """6. Failed treatment demotes external prior to REJECTED and creates FIRST_PARTY_OVERRIDE."""
        self.ext_repo.upsert_external_prior(ExternalPriorModel(
            prior_id="prior_overrated", target_channel_id="channel_a", pattern_id="pat_ov",
            hypothesis="Overrated Pattern", transferability_classification=TransferabilityClassification.HIGH,
            prior_weight=0.25, status=PriorStatus.HYPOTHESIS
        ))
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_override_loss", channel_id="channel_a", name="Override Loss", hypothesis="H",
            variable_tested="HOOK_STRUCTURE", control_definition="C", variant_definition="T",
            primary_metric="avg_percentage_viewed", status="RUNNING", external_prior_id="prior_overrated"
        ))
        for i in range(4):
            vid_c = f"vid_oc_{i}"
            vid_t = f"vid_ot_{i}"
            self.repo.upsert_video(VideoModel(video_id=vid_c, channel_id="channel_a", pipeline_id="p1", title="C", duration=45.0, upload_status="UPLOADED_PUBLIC", experiment_id="exp_override_loss", variant_id="CONTROL"))
            self.repo.upsert_video(VideoModel(video_id=vid_t, channel_id="channel_a", pipeline_id="p1", title="T", duration=45.0, upload_status="UPLOADED_PUBLIC", experiment_id="exp_override_loss", variant_id="TREATMENT"))
            self.repo.insert_snapshot(PerformanceSnapshotModel(video_id=vid_c, window_name="24h", avg_percentage_viewed=80.0))
            self.repo.insert_snapshot(PerformanceSnapshotModel(video_id=vid_t, window_name="24h", avg_percentage_viewed=65.0))

        res = self.learning_engine.process_experiment_outcome("exp_override_loss")
        self.assertIn("FIRST_PARTY_OVERRIDE", res["events_generated"])

        prior = self.ext_repo.get_external_prior("prior_overrated")
        self.assertEqual(prior["status"], "REJECTED")
        self.assertEqual(prior["prior_weight"], 0.0)

    def test_07_strategy_evolution_creates_immutable_v1_1(self):
        """7. Winning N=4 experiment proposes immutable v1.1 and preserves v1.0."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_for_mutation", channel_id="channel_a", name="Mut Exp", hypothesis="H",
            variable_tested="HOOK_STRUCTURE", control_definition="C", variant_definition="Question Hook V2",
            primary_metric="avg_percentage_viewed", status="EVALUATED", decision="ACCEPT_VARIANT",
            control_count=4, treatment_count=4, delta_percentage=12.0
        ))

        res = self.strategy_evolution.evaluate_strategy_mutation("channel_a")
        self.assertEqual(res["action"], "STRATEGY_VERSION_CREATED")
        self.assertEqual(res["new_version"], "v1.1")
        self.assertEqual(res["parent_version"], "v1.0")

        # Verify both v1.0 and v1.1 exist on disk
        v1_path = self.strat_dir / "channel_a_strategy_v1.0.json"
        v1_1_path = self.strat_dir / "channel_a_strategy_v1.1.json"
        self.assertTrue(v1_path.exists())
        self.assertTrue(v1_1_path.exists())

        # Verify v1.0 was untouched
        with open(v1_path, "r", encoding="utf-8") as f:
            v1_data = json.load(f)
        self.assertEqual(v1_data["strategy_version"], "v1.0")

    def test_08_strategy_evolution_refuses_mutation_without_n4_win(self):
        """8. No mutation is proposed when no N >= 4 winning experiment exists."""
        res = self.strategy_evolution.evaluate_strategy_mutation("channel_b")
        self.assertEqual(res["action"], "NO_MUTATION_WARRANTED")

    def test_09_memory_v2_knowledge_state_and_summary(self):
        """9. BrainMemory reports explicit knowledge states and institutional knowledge summary."""
        # Insert completed win
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_mem_k", channel_id="channel_a", name="K", hypothesis="H",
            variable_tested="HOOK_STRUCTURE", control_definition="C", variant_definition="Question",
            primary_metric="avg_percentage_viewed", status="EVALUATED", decision="ACCEPT_VARIANT",
            control_count=4, treatment_count=4, delta_percentage=10.0
        ))

        state = self.brain.memory.get_knowledge_state("channel_a", "HOOK_STRUCTURE", "Question")
        self.assertEqual(state, "SUPPORTED")

        summary = self.brain.memory.get_knowledge_summary("channel_a")
        self.assertTrue(len(summary["supported_patterns"]) > 0)

    def test_10_daily_cycle_idempotency_and_discord_gate(self):
        """10. DailyBrainCycle runs cleanly, preserves Discord gate, and is idempotent."""
        cycle = DailyBrainCycle(self.db_path)
        r1 = cycle.run_cycle("channel_a")
        r2 = cycle.run_cycle("channel_a")

        self.assertTrue(r1["human_approval_required"])
        self.assertFalse(r1["auto_upload_enabled"])
        self.assertEqual(r1["sample_counts"], r2["sample_counts"])

    def test_11_channel_a_channel_b_isolation(self):
        """11. Channel A and Channel B memories and learnings remain completely isolated."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_chan_a_only", channel_id="channel_a", name="A Exp", hypothesis="H",
            variable_tested="HOOK_STRUCTURE", control_definition="C", variant_definition="T",
            primary_metric="avg_percentage_viewed", status="RUNNING"
        ))
        for i in range(4):
            vid_c = f"vid_iso_c_{i}"
            vid_t = f"vid_iso_t_{i}"
            self.repo.upsert_video(VideoModel(video_id=vid_c, channel_id="channel_a", pipeline_id="p1", title="C", duration=45.0, upload_status="UPLOADED_PUBLIC", experiment_id="exp_chan_a_only", variant_id="CONTROL"))
            self.repo.upsert_video(VideoModel(video_id=vid_t, channel_id="channel_a", pipeline_id="p1", title="T", duration=45.0, upload_status="UPLOADED_PUBLIC", experiment_id="exp_chan_a_only", variant_id="TREATMENT"))
            self.repo.insert_snapshot(PerformanceSnapshotModel(video_id=vid_c, window_name="24h", avg_percentage_viewed=65.0))
            self.repo.insert_snapshot(PerformanceSnapshotModel(video_id=vid_t, window_name="24h", avg_percentage_viewed=82.0))

        self.learning_engine.process_experiment_outcome("exp_chan_a_only")

        evts_a = self.repo.list_learning_events(channel_id="channel_a")
        evts_b = self.repo.list_learning_events(channel_id="channel_b")

        self.assertTrue(len(evts_a) > 0)
        self.assertEqual(len(evts_b), 0)


if __name__ == "__main__":
    unittest.main()
