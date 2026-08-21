# -*- coding: utf-8 -*-
"""
test_brain_production_recommendation.py
---------------------------------------
Unit and integration tests for ProductionRecommendationEngine.
Validates packaging specs, single-variable discipline, and JSON plan file generation.
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
from growth.brain.brain import ContentBrain
from growth.brain.schemas import (
    BrainDecision,
    DecisionType,
    ConfidenceLevel,
    ContentOpportunity,
    Hypothesis
)
from growth.brain.production_recommendation import (
    ProductionRecommendationEngine,
    ProductionRecommendation
)


class TestBrainProductionRecommendation(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_rec.db"
        init_db(self.db_path)
        self.brain = ContentBrain(self.db_path)
        self.engine = ProductionRecommendationEngine(output_dir=Path(self.tmp_dir.name))

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_01_generate_channel_a_production_recommendation(self):
        """1. Generates complete Channel A production recommendation with alternate history packaging."""
        opp = ContentOpportunity(
            opportunity_id="opp_alexandria", channel_id="channel_a",
            topic="What if the Library of Alexandria survived?", topic_cluster="Classical",
            content_angle="Knowledge", proposed_hook="What if the Library of Alexandria survived?",
            audience_reason="Target classical history buffs", evidence_items=[], novelty_score=0.9,
            experiment_value=0.85, production_feasibility=1.0, first_party_support=0.5,
            external_support=0.8, uncertainty_penalty=0.0, repetition_penalty=0.0,
            overall_score=0.82, portfolio_tier="adjacent", knowledge_state="UNTESTED", explanation="Test"
        )
        hyp = Hypothesis(
            hypothesis_id="hyp_01", channel_id="channel_a",
            statement="Question hooks achieve higher early APV.",
            variable_under_test="HOOK_STRUCTURE",
            control_spec="Declarative statement",
            treatment_spec="Direct question hook",
            invariants=["Voice Actor", "Visual Style", "Ken Burns Motion", "17/17 QA"],
            expected_learning="Measures APV delta between question and statement openings."
        )
        decision = BrainDecision(
            decision_id="dec_01", channel_id="channel_a", decision_type=DecisionType.RUN_EXPERIMENT,
            opportunity=opp, hypothesis=hyp, arm_type="CONTROL", variable_under_test="HOOK_STRUCTURE",
            confidence=ConfidenceLevel.LOW, reasoning="Testing control arm.", explanation_breakdown={},
            invariants=hyp.invariants
        )

        rec = self.engine.generate_recommendation(decision, save_plan_file=True)
        self.assertEqual(rec.channel_id, "channel_a")
        self.assertEqual(rec.experiment_variable, "HOOK_STRUCTURE")
        self.assertEqual(rec.target_duration, "42s - 50s")
        self.assertTrue(len(rec.script_structure) >= 5)
        self.assertIn("ChristopherNeural", rec.voice_recommendation)
        self.assertIn("SDXL", rec.visual_strategy)
        self.assertEqual(rec.confidence, "LOW")

        # Verify JSON file on disk
        plan_file = Path(self.tmp_dir.name) / "brain_production_plan_channel_a.json"
        self.assertTrue(plan_file.exists())
        with open(plan_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["channel_id"], "channel_a")
            self.assertEqual(data["experiment_variable"], "HOOK_STRUCTURE")

    def test_02_generate_channel_b_production_recommendation(self):
        """2. Generates complete Channel B recommendation with dual-host debate packaging."""
        opp = ContentOpportunity(
            opportunity_id="opp_brain_names", channel_id="channel_b",
            topic="Why your brain forgets names in three seconds", topic_cluster="Memory",
            content_angle="Cognitive Psychology", proposed_hook="Why your brain forgets names in three seconds",
            audience_reason="Curiosity target", evidence_items=[], novelty_score=0.95,
            experiment_value=0.85, production_feasibility=1.0, first_party_support=0.5,
            external_support=0.85, uncertainty_penalty=0.0, repetition_penalty=0.0,
            overall_score=0.85, portfolio_tier="adjacent", knowledge_state="UNTESTED", explanation="Test"
        )
        hyp = Hypothesis(
            hypothesis_id="hyp_b_01", channel_id="channel_b",
            statement="Provocative openings drive higher comment debate.",
            variable_under_test="HOOK_STRUCTURE",
            control_spec="Standard inquiry",
            treatment_spec="Direct provocative paradox",
            invariants=["Dual Piper Voices", "Motion Background", "16/16 QA"],
            expected_learning="Measures comments per 1k views."
        )
        decision = BrainDecision(
            decision_id="dec_b_01", channel_id="channel_b", decision_type=DecisionType.RUN_EXPERIMENT,
            opportunity=opp, hypothesis=hyp, arm_type="CONTROL", variable_under_test="HOOK_STRUCTURE",
            confidence=ConfidenceLevel.LOW, reasoning="Testing control arm.", explanation_breakdown={},
            invariants=hyp.invariants
        )

        rec = self.engine.generate_recommendation(decision, save_plan_file=True)
        self.assertEqual(rec.channel_id, "channel_b")
        self.assertIn("Piper", rec.voice_recommendation)
        self.assertIn("Turn 1 (Host A)", rec.script_structure[0])
        self.assertEqual(rec.target_duration, "42s - 50s")

    def test_03_single_variable_invariant_protection(self):
        """3. Enforces single-variable discipline and rejects plans with undefined variables."""
        opp = ContentOpportunity(
            opportunity_id="opp_bad", channel_id="channel_a", topic="Bad Op",
            topic_cluster="Test", content_angle="Test", proposed_hook="Hook",
            audience_reason="Test", evidence_items=[], novelty_score=0.5,
            experiment_value=0.5, production_feasibility=1.0, first_party_support=0.5,
            external_support=0.5, uncertainty_penalty=0.0, repetition_penalty=0.0,
            overall_score=0.5, portfolio_tier="adjacent", knowledge_state="UNTESTED", explanation="Test"
        )
        # Invalid hypothesis with undefined variable
        hyp_bad = Hypothesis(
            hypothesis_id="hyp_bad", channel_id="channel_a", statement="Bad",
            variable_under_test="", control_spec="c", treatment_spec="t", invariants=[]
        )
        decision_bad = BrainDecision(
            decision_id="dec_bad", channel_id="channel_a", decision_type=DecisionType.RUN_EXPERIMENT,
            opportunity=opp, hypothesis=hyp_bad, arm_type="CONTROL", variable_under_test="",
            confidence=ConfidenceLevel.LOW, reasoning="Bad.", explanation_breakdown={}, invariants=[]
        )

        with self.assertRaises(ValueError):
            self.engine.generate_recommendation(decision_bad)


if __name__ == "__main__":
    unittest.main()
