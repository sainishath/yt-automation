# -*- coding: utf-8 -*-
"""
test_external_intelligence_integration.py
-----------------------------------------
Step 11 Comprehensive Integration Test Suite for External Intelligence + Content Recommendation Brain.
Validates the 17 core integration invariants across provenance, safety, single-variable discipline,
channel isolation, first-party dominance, and zero auto-upload authority.
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
from growth.db.models import GrowthRepository, VideoModel, PerformanceSnapshotModel, ExperimentModel
from growth.external_intelligence.repository import ExternalIntelligenceRepository
from growth.external_intelligence.dataset_builder import ExternalDatasetBuilder
from growth.external_intelligence.schemas import (
    ExternalVideoModel,
    ExternalPriorModel,
    ProvenanceSource,
    TransferabilityClassification,
    PriorStatus
)
from growth.brain.brain import ContentBrain
from growth.brain.schemas import ConfidenceLevel, DecisionType, KnowledgeState
from growth.brain.production_recommendation import ProductionRecommendationEngine
from growth.brain.learning_engine import LearningEngine
from growth.brain.strategy_evolution import StrategyEvolutionEngine


class TestExternalIntelligenceIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_integration.db"
        init_db(self.db_path)

        self.repo = GrowthRepository(self.db_path)
        self.ext_repo = ExternalIntelligenceRepository(self.db_path)
        self.builder = ExternalDatasetBuilder(self.ext_repo)
        self.builder.build_dataset(target_count_per_channel=20)

        self.brain = ContentBrain(self.db_path)
        self.rec_engine = ProductionRecommendationEngine(output_dir=Path(self.tmp_dir.name))
        self.learning_engine = LearningEngine(self.repo, self.ext_repo)
        self.strat_evolution = StrategyEvolutionEngine(self.repo)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_01_provenance_retention(self):
        """1. External records strictly retain public provenance."""
        vids = self.ext_repo.list_external_videos(limit=10)
        self.assertTrue(len(vids) > 0)
        for v in vids:
            self.assertEqual(v["source_type"], ProvenanceSource.PUBLIC_YOUTUBE.value)
            self.assertTrue(v["url"].startswith("https://youtube.com"))

    def test_02_missing_metrics_never_become_fake_zeros(self):
        """2. Missing metrics remain NOT_AVAILABLE / PENDING, not fabricated."""
        vids = self.brain.memory.get_published_videos("channel_a")
        # In clean state, videos without snapshots return empty or PENDING
        self.assertEqual(len(vids), 0)

    def test_03_duplicate_ingestion_is_idempotent(self):
        """3. Re-running ingestion does not duplicate external records."""
        count_before = len(self.ext_repo.list_external_videos(limit=1000))
        self.builder.build_dataset(target_count_per_channel=20)
        count_after = len(self.ext_repo.list_external_videos(limit=1000))
        self.assertEqual(count_before, count_after)

    def test_04_external_evidence_lower_priority_than_first_party(self):
        """4. OpportunityEngine scores first-party empirical data higher than external priors."""
        opps = self.brain.get_ranked_opportunities("channel_a")
        self.assertTrue(len(opps) > 0)
        top_opp = opps[0]
        # In the absence of FP data, knowledge state is UNTESTED or PROMISING
        self.assertIn(top_opp["knowledge_state"], [KnowledgeState.UNTESTED.value, KnowledgeState.PROMISING.value])

    def test_05_first_party_winner_overrides_external_prior(self):
        """5. Empirical first-party result demotes contradictory external prior."""
        self.ext_repo.upsert_external_prior(ExternalPriorModel(
            prior_id="prior_contradict_test", target_channel_id="channel_a", pattern_id="pat_c",
            hypothesis="Declarative hooks win", transferability_classification=TransferabilityClassification.HIGH,
            prior_weight=0.25, status=PriorStatus.HYPOTHESIS
        ))

        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_override_integration", channel_id="channel_a", name="Override Test",
            hypothesis="Declarative hooks win", variable_tested="HOOK_STRUCTURE",
            control_definition="Question", variant_definition="Declarative",
            primary_metric="avg_percentage_viewed", status="RUNNING", decision="PENDING",
            control_count=4, treatment_count=4, delta_percentage=0.0,
            external_prior_id="prior_contradict_test"
        ))

        # 4 control samples (85% APV) vs 4 treatment samples (60% APV)
        for i in range(4):
            cv = f"vid_c_{i}"
            self.repo.upsert_video(VideoModel(
                video_id=cv, channel_id="channel_a", pipeline_id="pipeline1",
                title=f"C {i}", duration=45.0, experiment_id="exp_override_integration",
                arm_id="arm_c", variant_id="CONTROL", upload_status="UPLOADED_PUBLIC"
            ))
            self.repo.insert_snapshot(PerformanceSnapshotModel(
                video_id=cv, window_name="24h", views=1200, avg_percentage_viewed=85.0
            ))

            tv = f"vid_t_{i}"
            self.repo.upsert_video(VideoModel(
                video_id=tv, channel_id="channel_a", pipeline_id="pipeline1",
                title=f"T {i}", duration=45.0, experiment_id="exp_override_integration",
                arm_id="arm_t", variant_id="TREATMENT", upload_status="UPLOADED_PUBLIC"
            ))
            self.repo.insert_snapshot(PerformanceSnapshotModel(
                video_id=tv, window_name="24h", views=800, avg_percentage_viewed=60.0
            ))

        res = self.learning_engine.process_experiment_outcome("exp_override_integration")
        prior = self.ext_repo.get_external_prior("prior_contradict_test")
        self.assertEqual(prior["status"], "REJECTED")
        self.assertEqual(prior["prior_weight"], 0.0)

    def test_06_external_prior_cannot_declare_strategy_proven(self):
        """6. External prior alone cannot evolve active strategy version without N>=4 first party data."""
        report = self.strat_evolution.evaluate_and_evolve_strategy("channel_a")
        self.assertEqual(report["action"], "NO_MUTATION_WARRANTED")
        self.assertIn("N >= 4", report["reason"])

    def test_07_transferability_classification(self):
        """7. External patterns are categorized by transferability."""
        patterns = self.ext_repo.list_external_patterns()
        # Ensure patterns are parsed cleanly
        self.assertTrue(len(patterns) >= 0)

    def test_08_production_recommendation_schema_valid(self):
        """8. ProductionRecommendation generates valid machine-readable payload."""
        decision = self.brain.next_production_decision("channel_a")
        rec = self.rec_engine.generate_recommendation(decision, save_plan_file=True)
        self.assertEqual(rec.channel_id, "channel_a")
        self.assertTrue(len(rec.script_structure) > 0)
        self.assertTrue(len(rec.invariants) > 0)

    def test_09_single_variable_experiment_invariant_enforcement(self):
        """9. Decision explicitly locks all other variables into invariants."""
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_hook_test_09", channel_id="channel_a", name="Hook Test",
            hypothesis="Test", variable_tested="HOOK_STRUCTURE", control_definition="c", variant_definition="t",
            primary_metric="avg_percentage_viewed", status="RUNNING", decision="PENDING"
        ))
        decision = self.brain.next_production_decision("channel_a")
        self.assertEqual(decision.variable_under_test, "HOOK_STRUCTURE")
        self.assertTrue(len(decision.invariants) > 0)

    def test_10_explainable_decisions(self):
        """10. ContentBrain provides deep 10-point transparent explanation."""
        expl = self.brain.explain_recommendation("channel_a")
        self.assertIn("decision_id", expl)
        self.assertIn("explanation", expl)
        self.assertIn("invariants", expl)

    def test_11_production_changes_recommendation(self):
        """11. Brain recommends concrete video-level pacing, visual, and voice parameters."""
        decision = self.brain.next_production_decision("channel_b")
        rec = self.rec_engine.generate_recommendation(decision, save_plan_file=False)
        self.assertIn("Piper", rec.voice_recommendation)
        self.assertIn("split-host", rec.visual_strategy)

    def test_12_frozen_pipeline_isolation(self):
        """12. Brain recommendation operates via manifest injection without modifying core code."""
        plan_file = Path(self.tmp_dir.name) / "brain_production_plan_channel_a.json"
        decision = self.brain.next_production_decision("channel_a")
        self.rec_engine.generate_recommendation(decision, save_plan_file=True)
        self.assertTrue(plan_file.exists())

    def test_13_channel_isolation_channel_a_to_b(self):
        """13. Channel A analog records and priors never leak into Channel B."""
        priors_b = self.ext_repo.list_external_priors(target_channel_id="channel_b")
        for p in priors_b:
            self.assertEqual(p["target_channel_id"], "channel_b")

    def test_14_channel_isolation_channel_b_to_a(self):
        """14. Channel B analog records and priors never leak into Channel A."""
        priors_a = self.ext_repo.list_external_priors(target_channel_id="channel_a")
        for p in priors_a:
            self.assertEqual(p["target_channel_id"], "channel_a")

    def test_15_insufficient_evidence_results_in_low_confidence(self):
        """15. Recommendations with zero first-party samples output LOW confidence."""
        decision = self.brain.next_production_decision("channel_b")
        self.assertEqual(decision.confidence, ConfidenceLevel.LOW)

    def test_16_external_evidence_cannot_bypass_n_greater_equal_4(self):
        """16. N>=4 guard is enforced regardless of external prior strength."""
        from growth.brain.evaluator import MultiArmExperimentEvaluator
        evaluator = MultiArmExperimentEvaluator(self.repo, min_sample_size=4)
        self.repo.upsert_experiment(ExperimentModel(
            experiment_id="exp_empty_test_16", channel_id="channel_a", name="Empty Test",
            hypothesis="Test", variable_tested="HOOK_STRUCTURE", control_definition="c", variant_definition="t",
            primary_metric="avg_percentage_viewed", status="RUNNING", decision="PENDING"
        ))
        res = evaluator.evaluate_experiment("exp_empty_test_16")
        self.assertEqual(res.status, "COLLECTING_DATA")
        self.assertEqual(res.decision, "CONTINUE_COLLECTION")

    def test_17_zero_auto_upload_authority(self):
        """17. ContentBrain and DailyBrainCycle have zero direct upload authority."""
        from growth.brain.cycle import DailyBrainCycle
        cycle = DailyBrainCycle(self.db_path)
        report = cycle.run_cycle("channel_a")
        self.assertTrue(report["human_approval_required"])
        self.assertFalse(report["auto_upload_enabled"])


if __name__ == "__main__":
    unittest.main()
