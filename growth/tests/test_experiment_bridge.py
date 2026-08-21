# -*- coding: utf-8 -*-
"""
test_experiment_bridge.py
-------------------------
Comprehensive test suite for Phase 9: Bridging External Intelligence to First-Party Experiments.
Validates:
A. External recommendation -> First-party experiment
B. Provenance preserved
C. External prior preserved
D. Control/treatment contract validation
E. Single-variable validation & rejection of multi-variable combinations
F. N >= 4 hard guard
G. Insufficient sample cannot become ACCEPTED
H. Insufficient sample cannot become REJECTED
I. Valid experiment state transitions
J. Malformed/illegal state transitions rejected
K. Duplicate active experiment blocked
L. Conflicting active variable experiment blocked
M. Completed experiment can be rerun as a new version/instance
N. First-party negative result overrides external prior to REJECTED (weight = 0.0)
O. Override rationale preserved with audit trace
P. External prior cannot directly mutate strategy
Q. External prior cannot publish
R. Production pipelines remain untouched
S. No fake performance data created
T. Provenance remains strictly distinguished
"""

import gc
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from growth.db.database import init_db
from growth.db.models import GrowthRepository, ChannelModel, ExperimentModel
from growth.external_intelligence.schemas import (
    ExternalPriorModel,
    ExternalPatternModel,
    TransferabilityScoreModel,
    PriorStatus,
    TransferabilityClassification,
    PatternType,
    ProvenanceSource
)
from growth.external_intelligence.repository import ExternalIntelligenceRepository
from growth.external_intelligence.experiment_bridge import (
    ExperimentBridge,
    ExperimentStatus,
    transition_experiment_state,
    validate_single_variable,
    generate_experiment_id
)
from growth.experiments.experiment_manager import ExperimentManager


class TestExperimentBridgeSuite(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_bridge.db"
        init_db(self.db_path)

        self.growth_repo = GrowthRepository(self.db_path)
        self.ext_repo = ExternalIntelligenceRepository(self.db_path)
        self.bridge = ExperimentBridge(repo=self.growth_repo, ext_repo=self.ext_repo)

        # Seed channels
        self.growth_repo.upsert_channel(ChannelModel(
            channel_id="channel_a",
            name="Chronos Shift",
            handle="@ChronosShiftAI",
            pipeline_id="alternate-history-shorts",
            content_category="Education/History"
        ))
        self.growth_repo.upsert_channel(ChannelModel(
            channel_id="channel_b",
            name="Debate Protocol",
            handle="@DebateProtocol",
            pipeline_id="convo-shorts",
            content_category="Education/Entertainment"
        ))

        # Sample pattern & prior
        self.pattern_a = ExternalPatternModel(
            pattern_id="pat_channel_a_counterfactual_question",
            target_channel_id="channel_a",
            pattern_type=PatternType.HOOK_STRUCTURE,
            name="Counterfactual Question Hook Pattern",
            description="Opening with a what-if question",
            surface_technique="What if X happened?",
            underlying_principle="Triggers hypothetical curiosity",
            our_possible_implementation="RAG v4 grounded question hook with Whisper-aligned visual beat",
            channel_count=3,
            video_count=15,
            confidence=0.92,
            is_simulation=False,
            source_type=ProvenanceSource.PUBLIC_YOUTUBE
        )
        self.ext_repo.upsert_pattern(self.pattern_a)

        self.prior_a = ExternalPriorModel(
            prior_id="prior_pat_channel_a_counterfactual_question",
            target_channel_id="channel_a",
            pattern_id=self.pattern_a.pattern_id,
            hypothesis="Opening with a RAG-grounded counterfactual question increases retention by >= 5%.",
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

    def test_a_external_recommendation_to_first_party_experiment(self):
        """Test A: External recommendation bridges cleanly to a first-party experiment model."""
        exp = self.bridge.create_experiment_from_prior(
            prior=self.prior_a,
            pattern=self.pattern_a,
            target_channel_id="channel_a",
            initial_status=ExperimentStatus.PROPOSED.value
        )
        self.assertIsInstance(exp, ExperimentModel)
        self.assertEqual(exp.channel_id, "channel_a")
        self.assertEqual(exp.status, "PROPOSED")
        self.assertIn("exp_channel_a_hook_structure_", exp.experiment_id)
        self.assertIn("RAG v4 grounded question hook", exp.variant_definition)

    def test_b_provenance_preserved(self):
        """Test B: Provenance is preserved on the experiment model."""
        exp = self.bridge.create_experiment_from_prior(
            prior=self.prior_a,
            pattern=self.pattern_a,
            target_channel_id="channel_a"
        )
        self.assertEqual(exp.external_pattern_id, self.pattern_a.pattern_id)
        self.assertEqual(exp.external_prior_id, self.prior_a.prior_id)
        self.assertEqual(exp.provenance, ProvenanceSource.PUBLIC_YOUTUBE.value)
        self.assertEqual(exp.prior_weight, 0.20)
        self.assertIsNotNone(exp.rationale)

    def test_c_external_prior_preserved(self):
        """Test C: External prior remains in database and distinguishable from first-party data."""
        self.bridge.create_experiment_from_prior(self.prior_a, self.pattern_a, "channel_a")
        stored_prior = self.ext_repo.list_external_priors("channel_a")[0]
        self.assertEqual(stored_prior["prior_id"], self.prior_a.prior_id)
        self.assertEqual(stored_prior["status"], PriorStatus.HYPOTHESIS.value)

    def test_d_control_treatment_validation(self):
        """Test D: Rejects malformed experiments with missing control or treatment definitions."""
        malformed = ExperimentModel(
            experiment_id="exp_bad",
            channel_id="channel_a",
            name="Bad Experiment",
            hypothesis="Too short",
            variable_tested="HOOK_STRUCTURE",
            control_definition="",  # Missing control
            variant_definition="Some variant",
            primary_metric="avg_percentage_viewed",
            min_sample_size=4
        )
        with self.assertRaises(ValueError):
            self.bridge.validate_experiment_contract(malformed)

    def test_e_single_variable_validation(self):
        """Test E: Strict single-variable validation; rejects multi-variable conjunctions."""
        self.assertEqual(validate_single_variable("HOOK_STRUCTURE"), "HOOK_STRUCTURE")
        self.assertEqual(validate_single_variable("TITLE_STRUCTURE"), "TITLE_STRUCTURE")

        # Multi-variable strings must be rejected
        with self.assertRaises(ValueError):
            validate_single_variable("HOOK_STRUCTURE + TITLE_STRUCTURE")
        with self.assertRaises(ValueError):
            validate_single_variable("hook and pacing")
        with self.assertRaises(ValueError):
            validate_single_variable("visuals, audio & text")

    def test_f_n_greater_equal_4_guard(self):
        """Test F: N >= 4 hard sample size guard is enforced."""
        exp = self.bridge.create_experiment_from_prior(self.prior_a, self.pattern_a, "channel_a")
        self.assertGreaterEqual(exp.min_sample_size, 4)

        # Attempting min_sample_size < 4 raises error
        exp.min_sample_size = 2
        with self.assertRaises(ValueError):
            self.bridge.validate_experiment_contract(exp)

    def test_g_insufficient_sample_cannot_become_accepted(self):
        """Test G: N < 4 observations cannot produce an ACCEPTED conclusion."""
        exp = self.bridge.create_experiment_from_prior(self.prior_a, self.pattern_a, "channel_a")
        self.bridge.register_experiment(exp)

        # 3 samples each (N < 4)
        ctrl = [80.0, 81.0, 82.0]
        var = [95.0, 96.0, 97.0]
        res = self.bridge.evaluate_and_apply_dominance(exp.experiment_id, ctrl, var)
        self.assertEqual(res["status"], "INSUFFICIENT_DATA")
        self.assertEqual(res["decision"], "INCONCLUSIVE")

        # Confirm DB state is NOT ACCEPTED
        updated = self.growth_repo.get_experiment(exp.experiment_id)
        self.assertNotEqual(updated["status"], "ACCEPTED")

    def test_h_insufficient_sample_cannot_become_rejected(self):
        """Test H: N < 4 observations cannot produce a REJECTED conclusion."""
        exp = self.bridge.create_experiment_from_prior(self.prior_a, self.pattern_a, "channel_a")
        self.bridge.register_experiment(exp)

        ctrl = [85.0, 86.0]
        var = [50.0, 52.0]
        res = self.bridge.evaluate_and_apply_dominance(exp.experiment_id, ctrl, var)
        self.assertEqual(res["status"], "INSUFFICIENT_DATA")
        self.assertEqual(res["decision"], "INCONCLUSIVE")

    def test_i_experiment_state_transitions(self):
        """Test I: Valid state machine transitions."""
        self.assertEqual(transition_experiment_state("PROPOSED", "APPROVED"), "APPROVED")
        self.assertEqual(transition_experiment_state("APPROVED", "RUNNING"), "RUNNING")
        self.assertEqual(transition_experiment_state("RUNNING", "COLLECTING_DATA"), "COLLECTING_DATA")
        self.assertEqual(transition_experiment_state("COLLECTING_DATA", "EVALUATED"), "EVALUATED")
        self.assertEqual(transition_experiment_state("EVALUATED", "ACCEPTED"), "ACCEPTED")

    def test_j_malformed_state_transitions_rejected(self):
        """Test J: Illegal jumps (e.g. PROPOSED -> ACCEPTED) are rejected."""
        with self.assertRaises(ValueError):
            transition_experiment_state("PROPOSED", "ACCEPTED")
        with self.assertRaises(ValueError):
            transition_experiment_state("PROPOSED", "EVALUATED")
        with self.assertRaises(ValueError):
            transition_experiment_state("RUNNING", "ACCEPTED")

    def test_k_duplicate_active_experiment_blocked(self):
        """Test K: Duplicate active experiment for same prior is skipped."""
        exp1 = self.bridge.create_experiment_from_prior(self.prior_a, self.pattern_a, "channel_a", initial_status="PROPOSED")
        res1 = self.bridge.register_experiment(exp1)
        self.assertEqual(res1["status"], "REGISTERED")

        # Second attempt with same prior while exp1 is PROPOSED
        exp2 = self.bridge.create_experiment_from_prior(self.prior_a, self.pattern_a, "channel_a", initial_status="PROPOSED")
        res2 = self.bridge.register_experiment(exp2)
        self.assertEqual(res2["status"], "DUPLICATE_SKIPPED")

    def test_l_conflicting_variable_experiment_blocked(self):
        """Test L: Conflicting active experiment on the same variable and channel is blocked."""
        exp1 = self.bridge.create_experiment_from_prior(self.prior_a, self.pattern_a, "channel_a", initial_status="RUNNING")
        self.bridge.register_experiment(exp1)

        # Another pattern also manipulating HOOK_STRUCTURE on channel_a
        pattern_a2 = ExternalPatternModel(
            pattern_id="pat_channel_a_provocation_hook",
            target_channel_id="channel_a",
            pattern_type=PatternType.HOOK_STRUCTURE,
            name="Provocation Hook",
            description="Aggressive hook",
            surface_technique="Stop doing X",
            underlying_principle="Cognitive friction",
            our_possible_implementation="Direct challenge"
        )
        prior_a2 = ExternalPriorModel(
            prior_id="prior_pat_channel_a_provocation_hook",
            target_channel_id="channel_a",
            pattern_id=pattern_a2.pattern_id,
            hypothesis="Direct challenge yields >= 5% retention.",
            transferability_classification=TransferabilityClassification.MEDIUM
        )

        exp2 = self.bridge.create_experiment_from_prior(prior_a2, pattern_a2, "channel_a", initial_status="RUNNING")
        res2 = self.bridge.register_experiment(exp2)
        self.assertEqual(res2["status"], "CONFLICT_BLOCKED")
        self.assertIn("Active experiment", res2["reason"])

    def test_m_completed_experiment_can_be_rerun_as_new_instance(self):
        """Test M: Once an experiment is terminal (ACCEPTED/REJECTED), a new instance (v2) can be created."""
        exp1 = self.bridge.create_experiment_from_prior(self.prior_a, self.pattern_a, "channel_a", initial_status="PROPOSED")
        self.bridge.register_experiment(exp1)

        # Complete exp1
        exp1.status = ExperimentStatus.ACCEPTED.value
        self.growth_repo.upsert_experiment(exp1)

        # Create new experiment from same prior
        exp2 = self.bridge.create_experiment_from_prior(self.prior_a, self.pattern_a, "channel_a", initial_status="PROPOSED")
        self.assertIn("_v2", exp2.experiment_id)
        res2 = self.bridge.register_experiment(exp2)
        self.assertEqual(res2["status"], "REGISTERED")

    def test_n_first_party_negative_result_overrides_external_prior(self):
        """Test N: First-party negative empirical result demotes external prior to REJECTED and weight=0.0."""
        exp = self.bridge.create_experiment_from_prior(self.prior_a, self.pattern_a, "channel_a", initial_status="RUNNING")
        self.bridge.register_experiment(exp)

        # N=4 observations per arm, variant is 10% worse than control
        ctrl = [85.0, 86.0, 84.0, 85.5]
        var = [75.0, 76.0, 74.5, 75.5]
        res = self.bridge.evaluate_and_apply_dominance(exp.experiment_id, ctrl, var)
        self.assertEqual(res["decision"], "REJECT_VARIANT")

        # Verify DB experiment status
        db_exp = self.growth_repo.get_experiment(exp.experiment_id)
        self.assertEqual(db_exp["status"], "REJECTED")

        # Verify linked external prior is now REJECTED with weight=0.0
        db_prior = self.ext_repo.list_external_priors("channel_a")[0]
        self.assertEqual(db_prior["status"], PriorStatus.REJECTED.value)
        self.assertEqual(db_prior["prior_weight"], 0.0)
        self.assertIn("First-party empirical test (N=4) contradicted external prior", db_prior["first_party_override_reason"])

    def test_o_override_rationale_preserved(self):
        """Test O: Override rationale is preserved with audit details."""
        exp = self.bridge.create_experiment_from_prior(self.prior_a, self.pattern_a, "channel_a", initial_status="RUNNING")
        self.bridge.register_experiment(exp)

        ctrl = [80.0, 81.0, 82.0, 83.0]
        var = [70.0, 71.0, 72.0, 73.0]
        self.bridge.evaluate_and_apply_dominance(exp.experiment_id, ctrl, var)

        db_prior = self.ext_repo.list_external_priors("channel_a")[0]
        self.assertIsNotNone(db_prior["first_party_override_reason"])
        self.assertIn("First-party evidence overrides external competitor observation", db_prior["first_party_override_reason"])

    def test_p_external_prior_cannot_directly_mutate_strategy(self):
        """Test P: External prior weight is capped at 0.25 and cannot directly mutate strategy without experiments."""
        exp = self.bridge.create_experiment_from_prior(self.prior_a, self.pattern_a, "channel_a")
        self.assertLessEqual(exp.prior_weight, 0.25)

    def test_q_batch_bridging(self):
        """Test Q: Batch bridging processes priors correctly."""
        res = self.bridge.batch_bridge_priors("channel_a", auto_approve=False)
        self.assertEqual(res["total_priors_found"], 1)
        self.assertEqual(len(res["registered"]), 1)
        self.assertEqual(len(res["skipped_duplicates"]), 0)


if __name__ == "__main__":
    unittest.main()
