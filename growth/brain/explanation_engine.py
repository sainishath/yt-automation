# -*- coding: utf-8 -*-
"""
explanation_engine.py
---------------------
Generates structured, explainable rationales for Content Brain decisions.
Answers the 10 core strategic questions for every recommendation.
"""

from typing import Dict, Any, Optional
from growth.brain.schemas import ContentOpportunity, Hypothesis, ConfidenceLevel


class ExplanationEngine:
    """
    Produces transparent, multi-dimensional explanations for Brain decisions.
    """

    def generate_explanation(
        self,
        opportunity: ContentOpportunity,
        hypothesis: Optional[Hypothesis],
        arm_type: Optional[str],
        sample_counts: Dict[str, int],
        confidence: ConfidenceLevel
    ) -> Dict[str, str]:
        """
        Generates full 10-point explanation mapping for the decision.
        """
        topic = opportunity.topic
        cluster = opportunity.topic_cluster
        hook = opportunity.proposed_hook
        fp_support = opportunity.first_party_support
        ext_support = opportunity.external_support

        ctrl_count = sample_counts.get("CONTROL", 0)
        treat_count = sample_counts.get("TREATMENT", 0)

        # 1. Why this topic?
        why_topic = (
            f"Topic '{topic}' in cluster '{cluster}' achieved an opportunity score of {opportunity.overall_score:.2f} "
            f"(First-Party Support: {fp_support:.2f}, Novelty: {opportunity.novelty_score:.2f}, Audience Fit: {opportunity.audience_reason})."
        )

        # 2. Why this angle?
        why_angle = (
            f"Angle '{opportunity.content_angle}' explores a high-leverage counterfactual turning point "
            f"without saturated repetition (Novelty: {opportunity.novelty_score:.2f})."
        )

        # 3. Why this hook?
        why_hook = (
            f"Proposed hook '{hook}' implements the structured question format to maximize early retention "
            f"and curiosity before the first visual transition."
        )

        # 4. Why this experiment / arm?
        if hypothesis and arm_type:
            why_exp = (
                f"Active experiment tests '{hypothesis.variable_under_test}'. Recommending arm '{arm_type}' "
                f"because current cohort counts are TREATMENT: {treat_count}, CONTROL: {ctrl_count}. "
                f"Assigning {arm_type} balances cohorts toward the N >= 4 decision threshold."
            )
        else:
            why_exp = "No active experiment required; producing proven baseline content."

        # 5. What evidence supports it?
        evidence_summary = (
            f"Supported by {len(opportunity.evidence_items)} evidence items. "
            f"First-Party Support: {fp_support:.2f}, External Intelligence Boost: {ext_support:.2f}. "
            f"Calibrated Confidence: {confidence.value}."
        )

        # 6. What do we not know?
        unknown = (
            hypothesis.uncertainty_addressed if hypothesis else
            "Remaining uncertainty around long-term viewer fatigue in this specific sub-topic."
        )

        # 7. What variable is being tested?
        var_tested = hypothesis.variable_under_test if hypothesis else "NONE (Proven Production)"

        # 8. What remains constant?
        invariants = (
            ", ".join(hypothesis.invariants[:4]) + "..." if hypothesis and hypothesis.invariants else
            "Standard production baseline, voice actor, SDXL style, 8% Ken Burns motion, 17/17 QA."
        )

        # 9. What would change our mind?
        change_mind = (
            "If subsequent first-party samples demonstrate lower average percentage viewed (< 60% APV) "
            "or higher swipe-away rates across N >= 4 samples."
        )

        # 10. What will we learn if it wins vs loses?
        if hypothesis:
            learn_win_lose = (
                f"IF WIN: Validates that {hypothesis.variable_under_test} ({hypothesis.treatment_spec}) "
                f"causes higher viewer retention and justifies updating the strategy version. "
                f"IF LOSE: Rejects the hypothesis, triggers FIRST_PARTY_OVERRIDE on external priors, "
                f"and retains the proven control configuration."
            )
        else:
            learn_win_lose = "Provides incremental baseline performance data for the proven topic cluster."

        return {
            "why_this_topic": why_topic,
            "why_this_angle": why_angle,
            "why_this_hook": why_hook,
            "why_this_experiment": why_exp,
            "what_evidence_supports_it": evidence_summary,
            "what_do_we_not_know": unknown,
            "what_variable_is_being_tested": var_tested,
            "what_remains_constant": invariants,
            "what_would_change_our_mind": change_mind,
            "what_will_we_learn_win_vs_lose": learn_win_lose
        }
