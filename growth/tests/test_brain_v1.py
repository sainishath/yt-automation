# -*- coding: utf-8 -*-
"""
test_brain_v1.py
----------------
Comprehensive test suite for Phase 11: Content Brain V1.
Validates memory aggregation, evidence hierarchy, knowledge gap discovery,
single-variable discipline, multi-variable rejection, 10-point explanations,
first-party dominance, and dynamic cohort recommendations.
"""

import unittest
import tempfile
import sqlite3
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
    ExternalPatternModel,
    PriorStatus,
    PatternType,
    ProvenanceSource,
    TransferabilityClassification
)
from growth.brain.schemas import (
    EvidenceSource,
    ConfidenceLevel,
    DecisionType,
    BrainDecision,
    ContentOpportunity,
    Hypothesis
)
from growth.brain.memory import BrainMemory
from growth.brain.evidence import EvidenceEvaluator
from growth.brain.opportunity_engine import OpportunityEngine
from growth.brain.hypothesis_engine import HypothesisEngine
from growth.brain.decision_engine import DecisionEngine
from growth.brain.explanation_engine import ExplanationEngine
from growth.brain.brain import ContentBrain


class TestBrainV1(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_brain.db"
        init_db(self.db_path)

        self.repo = GrowthRepository(self.db_path)
        self.ext_repo = ExternalIntelligenceRepository(self.db_path)

        # Seed test channel
        self.repo.upsert_channel(ChannelModel(
            channel_id="channel_a",
            name="Chronos Shift",
            handle="@ChronosShift",
            pipeline_id="alternate-history-shorts",
            content_category="Alternate History"
        ))

        self.brain = ContentBrain(self.db_path)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_01_brain_initialization(self):
        """1. Brain initializes with all component engines."""
        self.assertIsNotNone(self.brain.memory)
        self.assertIsNotNone(self.brain.evaluator)
        self.assertIsNotNone(self.brain.opp_engine)
        self.assertIsNotNone(self.brain.hyp_engine)
        self.assertIsNotNone(self.brain.decision_engine)
        self.assertIsNotNone(self.brain.expl_engine)

    def test_02_brain_reads_current_strategy(self):
        """2. Brain reads active immutable strategy version for channel."""
        strat = self.brain.memory.get_active_strategy("channel_a")
        self.assertIn("strategy_version", strat)
        self.assertTrue(strat["strategy_version"].startswith("v"))
        self.assertIn("portfolio_allocation", strat)

    def test_03_brain_reads_first_party_performance(self):
        """3. Brain retrieves published videos and snapshots without fabricating missing values."""
        # Insert video and snapshot
        self.repo.upsert_video(VideoModel(
            video_id="vid_test_01",
            channel_id="channel_a",
            pipeline_id="alternate-history-shorts",
            title="What If Rome Fell Early?",
            duration=45.0,
            upload_status="UPLOADED_PUBLIC",
            youtube_video_id="YT_TEST_01"
        ))
        self.repo.insert_snapshot(PerformanceSnapshotModel(
            video_id="vid_test_01",
            window_name="24h",
            views=1500,
            avg_percentage_viewed=78.5,
            data_source="YOUTUBE_API",
            data_freshness="2026-08-21"
        ))

        vids = self.brain.memory.get_published_videos("channel_a")
        self.assertEqual(len(vids), 1)
        perf_map = self.brain.memory.get_video_performance_map("channel_a")
        self.assertIn("vid_test_01", perf_map)
        self.assertEqual(perf_map["vid_test_01"]["snapshots"]["24h"]["views"], 1500)

    def test_04_brain_reads_experiment_history(self):
        """4. Brain reads experiment history and arm sample counts."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_test_hook",
            channel_id="channel_a",
            name="Hook Test",
            hypothesis="Question hook increases APV",
            variable_tested="HOOK_STRUCTURE",
            control_definition="Standard",
            variant_definition="Question",
            primary_metric="avg_percentage_viewed",
            status="RUNNING"
        ))
        self.repo.upsert_experiment_arm(ExperimentArmModel(
            arm_id="arm_ctrl",
            experiment_id="exp_test_hook",
            arm_type="CONTROL",
            name="Control Arm",
            definition="Standard",
            sample_count=2
        ))
        self.repo.upsert_experiment_arm(ExperimentArmModel(
            arm_id="arm_treat",
            experiment_id="exp_test_hook",
            arm_type="TREATMENT",
            name="Treatment Arm",
            definition="Question",
            sample_count=3
        ))

        counts = self.brain.memory.get_arm_sample_counts("channel_a")
        self.assertEqual(counts.get("arm_ctrl"), 2)
        self.assertEqual(counts.get("arm_treat"), 3)

    def test_05_brain_reads_external_evidence(self):
        """5. Brain reads external priors and patterns."""
        self.ext_repo.upsert_external_prior(ExternalPriorModel(
            prior_id="prior_test_01",
            target_channel_id="channel_a",
            pattern_id="pat_test_01",
            hypothesis="Question hooks boost views",
            transferability_classification=TransferabilityClassification.HIGH,
            prior_weight=0.22,
            status=PriorStatus.HYPOTHESIS
        ))

        priors = self.brain.memory.get_external_priors("channel_a")
        self.assertEqual(len(priors), 1)
        self.assertEqual(priors[0]["prior_id"], "prior_test_01")

    def test_06_first_party_evidence_outranks_external(self):
        """6. Evaluator places First-Party Experiment/Snapshot above External Priors in evidence list."""
        self.ext_repo.upsert_external_prior(ExternalPriorModel(
            prior_id="prior_test_02",
            target_channel_id="channel_a",
            pattern_id="pat_test_02",
            hypothesis="HOOK_STRUCTURE question hooks",
            transferability_classification=TransferabilityClassification.HIGH,
            prior_weight=0.20,
            status=PriorStatus.HYPOTHESIS
        ))
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_completed_01",
            channel_id="channel_a",
            name="Completed Hook Test",
            hypothesis="Question hook increases APV",
            variable_tested="HOOK_STRUCTURE",
            control_definition="Standard",
            variant_definition="Question",
            primary_metric="avg_percentage_viewed",
            status="EVALUATED",
            decision="ACCEPT_VARIANT",
            delta_percentage=8.5,
            control_count=4,
            treatment_count=4
        ))

        ev_items, conf = self.brain.evaluator.evaluate_hypothesis_evidence(
            channel_id="channel_a",
            variable="HOOK_STRUCTURE",
            variant_value="treatment"
        )
        self.assertTrue(len(ev_items) >= 2)
        # First item must be FIRST_PARTY_EXPERIMENT
        self.assertEqual(ev_items[0].source, EvidenceSource.FIRST_PARTY_EXPERIMENT)
        self.assertEqual(ev_items[0].confidence, ConfidenceLevel.HIGH)
        # Later item is EXTERNAL_PRIOR with LOW confidence
        ext_item = next(e for e in ev_items if e.source == EvidenceSource.EXTERNAL_PRIOR)
        self.assertEqual(ext_item.confidence, ConfidenceLevel.LOW)

    def test_07_n_less_than_4_cannot_produce_high_confidence(self):
        """7. Experiments with N < 4 produce LOW confidence."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_small_01",
            channel_id="channel_a",
            name="Small Hook Test",
            hypothesis="Question hook",
            variable_tested="HOOK_STRUCTURE",
            control_definition="Standard",
            variant_definition="Question",
            primary_metric="avg_percentage_viewed",
            status="EVALUATED",
            decision="INCONCLUSIVE",
            delta_percentage=2.0,
            control_count=1,
            treatment_count=1
        ))

        ev_items, conf = self.brain.evaluator.evaluate_hypothesis_evidence(
            channel_id="channel_a",
            variable="HOOK_STRUCTURE",
            variant_value="treatment"
        )
        exp_item = next(e for e in ev_items if e.provenance == "experiment:exp_small_01")
        self.assertEqual(exp_item.confidence, ConfidenceLevel.LOW)

    def test_08_brain_identifies_knowledge_gap(self):
        """8. Brain scans memory and identifies untested variables."""
        gaps = self.brain.hyp_engine.identify_knowledge_gaps("channel_a")
        self.assertTrue(len(gaps) > 0)
        gap_vars = {g["variable"] for g in gaps}
        self.assertIn("KEN_BURNS_MOTION", gap_vars)

    def test_09_brain_produces_valid_hypothesis(self):
        """9. Brain generates structured single-variable hypothesis."""
        hyp = self.brain.hyp_engine.generate_hypothesis("channel_a", "HOOK_STRUCTURE", "Classical")
        self.assertEqual(hyp.variable_under_test, "HOOK_STRUCTURE")
        self.assertTrue(len(hyp.invariants) >= 5)
        self.assertIn("Voice Actor Profile", hyp.invariants[0])

    def test_10_brain_produces_single_variable_experiment(self):
        """10. Hypothesis engine validates single-variable proposal."""
        hyp = self.brain.hyp_engine.generate_hypothesis("channel_a", "HOOK_STRUCTURE")
        valid, msg = self.brain.hyp_engine.validate_single_variable(hyp, ["HOOK_STRUCTURE"])
        self.assertTrue(valid)

    def test_11_brain_rejects_multivariable_experiment(self):
        """11. Hypothesis engine rejects multi-variable proposal."""
        hyp = self.brain.hyp_engine.generate_hypothesis("channel_a", "HOOK_STRUCTURE")
        valid, msg = self.brain.hyp_engine.validate_single_variable(hyp, ["HOOK_STRUCTURE", "VOICE_PACING", "VISUAL_STYLE"])
        self.assertFalse(valid)
        self.assertIn("Multi-variable experiment rejected", msg)

    def test_12_brain_produces_explainable_decisions(self):
        """12. DecisionEngine produces 10-point structured explanation."""
        dec = self.brain.recommend_next("channel_a")
        self.assertIsNotNone(dec.explanation_breakdown)
        self.assertIn("why_this_topic", dec.explanation_breakdown)
        self.assertIn("why_this_angle", dec.explanation_breakdown)
        self.assertIn("why_this_hook", dec.explanation_breakdown)
        self.assertIn("what_variable_is_being_tested", dec.explanation_breakdown)
        self.assertIn("what_remains_constant", dec.explanation_breakdown)
        self.assertIn("what_will_we_learn_win_vs_lose", dec.explanation_breakdown)

    def test_13_brain_does_not_fabricate_missing_analytics(self):
        """13. Unpopulated snapshot windows remain missing without fabricated zeros."""
        self.repo.upsert_video(VideoModel(
            video_id="vid_no_analytics",
            channel_id="channel_a",
            pipeline_id="alternate-history-shorts",
            title="What If Constantinople Survived?",
            duration=50.0,
            upload_status="UPLOADED_PUBLIC"
        ))
        perf_map = self.brain.memory.get_video_performance_map("channel_a")
        self.assertEqual(len(perf_map["vid_no_analytics"]["snapshots"]), 0)
        self.assertIsNone(perf_map["vid_no_analytics"]["latest_snapshot"])

    def test_14_brain_respects_portfolio_allocation(self):
        """14. OpportunityEngine assigns portfolio tiers."""
        opps = self.brain.opp_engine.rank_opportunities("channel_a", limit=10)
        self.assertTrue(len(opps) > 0)
        tiers = {o.portfolio_tier for o in opps}
        self.assertTrue(any(t in ["proven", "adjacent", "exploratory"] for t in tiers))

    def test_15_brain_does_not_upload_videos(self):
        """15. Recommending a decision returns a structured object and does not upload."""
        dec = self.brain.recommend_next("channel_a")
        self.assertIsInstance(dec, BrainDecision)
        # Database video status must remain untouched
        vids = self.repo.list_videos_by_channel("channel_a")
        self.assertTrue(all(v.get("upload_status") != "UPLOADING_IN_PROGRESS" for v in vids))

    def test_16_brain_does_not_bypass_discord(self):
        """16. Brain decisions specify invariants including mandatory Discord human gate."""
        dec = self.brain.recommend_next("channel_a")
        self.assertTrue(any("Discord" in inv for inv in dec.invariants))

    def test_17_brain_preserves_immutable_strategy_versions(self):
        """17. Strategy versions retrieved by memory are versioned strings."""
        strat = self.brain.memory.get_active_strategy("channel_a")
        self.assertRegex(strat["strategy_version"], r"^v\d+\.\d+$")

    def test_18_brain_integrates_with_experiment_queue(self):
        """18. Brain decision incorporates active experiment ID."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_active_q",
            channel_id="channel_a",
            name="Active Queue Test",
            hypothesis="Hyp",
            variable_tested="HOOK_STRUCTURE",
            control_definition="Ctrl",
            variant_definition="Treat",
            primary_metric="avg_percentage_viewed",
            status="RUNNING"
        ))
        self.repo.upsert_experiment_arm(ExperimentArmModel(
            arm_id="arm_active_ctrl",
            experiment_id="exp_active_q",
            arm_type="CONTROL",
            name="Control",
            definition="Ctrl",
            sample_count=0
        ))
        self.repo.upsert_experiment_arm(ExperimentArmModel(
            arm_id="arm_active_treat",
            experiment_id="exp_active_q",
            arm_type="TREATMENT",
            name="Treatment",
            definition="Treat",
            sample_count=0
        ))

        dec = self.brain.recommend_next("channel_a")
        self.assertEqual(dec.experiment_id, "exp_active_q")
        self.assertEqual(dec.arm_type, "CONTROL")

    def test_19_brain_recommends_control_for_channel_a_current_state(self):
        """19. When Treatment = 1 and Control = 0, Brain dynamically recommends CONTROL arm."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_channel_a_hook_structure_counterfactual_question_v1",
            channel_id="channel_a",
            name="Counterfactual Question Hook Test",
            hypothesis="Counterfactual question improves APV",
            variable_tested="HOOK_STRUCTURE",
            control_definition="Standard Question Hook",
            variant_definition="RAG Grounded Question Hook",
            primary_metric="avg_percentage_viewed",
            status="RUNNING"
        ))
        self.repo.upsert_experiment_arm(ExperimentArmModel(
            arm_id="arm_exp_channel_a_hook_structure_counterfactual_question_v1_control",
            experiment_id="exp_channel_a_hook_structure_counterfactual_question_v1",
            arm_type="CONTROL",
            name="Control Arm",
            definition="Standard Question",
            sample_count=0
        ))
        self.repo.upsert_experiment_arm(ExperimentArmModel(
            arm_id="arm_exp_channel_a_hook_structure_counterfactual_question_v1_treatment",
            experiment_id="exp_channel_a_hook_structure_counterfactual_question_v1",
            arm_type="TREATMENT",
            name="Treatment Arm",
            definition="RAG Grounded Question",
            sample_count=1
        ))

        dec = self.brain.recommend_next("channel_a")
        self.assertEqual(dec.decision_type, DecisionType.RUN_EXPERIMENT)
        self.assertEqual(dec.arm_type, "CONTROL")
        self.assertEqual(dec.arm_id, "arm_exp_channel_a_hook_structure_counterfactual_question_v1_control")
        self.assertIn("TREATMENT=1, CONTROL=0", dec.reasoning)

    def test_20_first_party_override_demotes_external_prior(self):
        """20. Completed experiment with N >= 4 rejecting variant demotes external prior."""
        self.ext_repo.upsert_external_prior(ExternalPriorModel(
            prior_id="prior_to_override",
            target_channel_id="channel_a",
            pattern_id="pat_to_override",
            hypothesis="Overrated hook pattern",
            transferability_classification=TransferabilityClassification.HIGH,
            prior_weight=0.25,
            status=PriorStatus.HYPOTHESIS
        ))
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_override_test",
            channel_id="channel_a",
            name="Override Test",
            hypothesis="Overrated hook pattern",
            variable_tested="HOOK_STRUCTURE",
            control_definition="Ctrl",
            variant_definition="Treat",
            primary_metric="avg_percentage_viewed",
            status="EVALUATED",
            decision="REJECT_VARIANT",
            delta_percentage=-6.0,
            control_count=4,
            treatment_count=4,
            external_prior_id="prior_to_override"
        ))

        res = self.brain.evaluator.check_first_party_override("channel_a", "exp_override_test")
        self.assertIsNotNone(res)
        self.assertEqual(res["action"], "FIRST_PARTY_OVERRIDE_APPLIED")

        # Verify prior updated in repository
        updated_prior = self.ext_repo.get_external_prior("prior_to_override")
        self.assertEqual(updated_prior["status"], "REJECTED")
        self.assertEqual(updated_prior["prior_weight"], 0.0)


if __name__ == "__main__":
    unittest.main()
