# -*- coding: utf-8 -*-
"""
hypothesis_engine.py
--------------------
Identifies knowledge gaps, designs single-variable hypotheses,
and enforces invariant requirements for Content Brain V1.
"""

from typing import List, Dict, Optional, Any, Tuple
from growth.brain.schemas import (
    Hypothesis,
    ConfidenceLevel,
    EvidenceItem,
    EvidenceSource
)
from growth.brain.memory import BrainMemory
from growth.brain.evidence import EvidenceEvaluator


VALID_ISOLATED_VARIABLES = {
    "HOOK_STRUCTURE",
    "TOPIC_CLUSTER",
    "VISUAL_STYLE",
    "KEN_BURNS_MOTION",
    "VOICE_PACING",
    "TITLE_FORMAT"
}

STANDARD_INVARIANTS = [
    "Voice Actor Profile (e.g. ChristopherNeural)",
    "Visual Art Architecture (SDXL / Fooocus Prompts)",
    "Motion Profile (8% Linear Ken Burns Motion)",
    "Video Duration Target (40s - 55s)",
    "Subtitles & Captioning Architecture (Whisper ASS Dynamic)",
    "Audio Loudness & Music Ducking Mix (-22dB bg)",
    "17/17 QA Gate Verification",
    "Mandatory Discord Human Approval Gate"
]


class HypothesisEngine:
    """
    Formulates scientific, single-variable hypotheses and validates experiment invariants.
    """

    def __init__(self, memory: BrainMemory, evaluator: Optional[EvidenceEvaluator] = None):
        self.memory = memory
        self.evaluator = evaluator or EvidenceEvaluator(memory)

    def identify_knowledge_gaps(self, channel_id: str) -> List[Dict[str, Any]]:
        """
        Scans first-party memory to identify high-uncertainty areas and knowledge gaps.
        """
        exps = self.memory.get_experiments(channel_id)
        active_vars = {e.get("variable_tested") for e in exps["active"]}
        completed_vars = {e.get("variable_tested") for e in exps["completed"]}

        gaps = []

        # Check unaddressed external priors
        priors = self.memory.get_external_priors(channel_id)
        for p in priors:
            if p.get("status") == "HYPOTHESIS":
                gaps.append({
                    "gap_id": f"gap_prior_{p['prior_id']}",
                    "variable": "HOOK_STRUCTURE" if "hook" in p.get("hypothesis", "").lower() else "TOPIC_CLUSTER",
                    "description": f"External prior '{p['prior_id']}' remains unvalidated by first-party empirical data.",
                    "source_prior": p["prior_id"]
                })

        # Check variable coverage
        for var in VALID_ISOLATED_VARIABLES:
            if var not in active_vars and var not in completed_vars:
                gaps.append({
                    "gap_id": f"gap_var_{var.lower()}",
                    "variable": var,
                    "description": f"No first-party experiments recorded for variable '{var}'.",
                    "source_prior": None
                })

        return gaps

    def generate_hypothesis(
        self,
        channel_id: str,
        variable: str,
        topic_cluster: Optional[str] = None
    ) -> Hypothesis:
        """
        Constructs a structured single-variable hypothesis.
        """
        if variable not in VALID_ISOLATED_VARIABLES:
            raise ValueError(f"Invalid variable '{variable}'. Must be one of: {VALID_ISOLATED_VARIABLES}")

        evidence_items, conf = self.evaluator.evaluate_hypothesis_evidence(
            channel_id=channel_id,
            variable=variable,
            variant_value="treatment",
            topic_cluster=topic_cluster
        )

        if variable == "HOOK_STRUCTURE":
            stmt = "Implementing a RAG v4 grounded counterfactual question hook will improve average percentage viewed (APV) relative to the standard question hook."
            ctrl = "Standard Chronos Shift Question Hook (e.g. 'What if X happened?')"
            treat = "RAG v4 grounded question hook with Whisper-aligned visual beat"
            expected_learning = "Determines whether grounding the opening question in specific historical evidence increases early viewer retention."
            uncertainty = "Whether explicit evidence grounding in the hook increases retention without alienating casual viewers."
        elif variable == "TOPIC_CLUSTER":
            stmt = f"Videos in topic cluster '{topic_cluster or 'Modern Warfare'}' achieve higher average views than the baseline historical cluster."
            ctrl = "Standard Ancient / Classical Turning Points"
            treat = f"Cluster: {topic_cluster or 'Modern Warfare'}"
            expected_learning = f"Measures audience interest elasticity for {topic_cluster or 'Modern Warfare'} content."
            uncertainty = f"Audience appetite for {topic_cluster or 'Modern Warfare'} on Channel A."
        else:
            stmt = f"Optimizing {variable} will improve first-party viewer retention."
            ctrl = f"Standard {variable} configuration"
            treat = f"Optimized {variable} variant"
            expected_learning = f"Quantifies impact of {variable} on video performance."
            uncertainty = f"Baseline sensitivity to {variable}."

        return Hypothesis(
            hypothesis_id=f"hyp_{channel_id}_{variable.lower()}_v1",
            channel_id=channel_id,
            statement=stmt,
            variable_under_test=variable,
            control_spec=ctrl,
            treatment_spec=treat,
            invariants=STANDARD_INVARIANTS.copy(),
            expected_learning=expected_learning,
            uncertainty_addressed=uncertainty,
            supported_by=evidence_items,
            confidence=conf
        )

    def validate_single_variable(self, hypothesis: Hypothesis, proposed_changes: List[str]) -> Tuple[bool, str]:
        """
        Enforces strict single-variable experimental discipline.
        Rejects proposals modifying multiple variables.
        """
        if len(proposed_changes) > 1:
            return False, f"Multi-variable experiment rejected! Proposed changes modify {len(proposed_changes)} variables ({proposed_changes}). Experiments must isolate exactly ONE variable."

        if not hypothesis.variable_under_test or hypothesis.variable_under_test not in VALID_ISOLATED_VARIABLES:
            return False, f"Invalid variable under test: '{hypothesis.variable_under_test}'"

        if not hypothesis.invariants or len(hypothesis.invariants) < 3:
            return False, "Hypothesis lacks explicit invariants. Must specify what remains constant."

        return True, "Valid single-variable experiment proposal."
