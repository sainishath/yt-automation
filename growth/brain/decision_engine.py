# -*- coding: utf-8 -*-
"""
decision_engine.py
------------------
Synthesizes memory, opportunities, hypotheses, and portfolio allocations
to generate explainable BrainDecision recommendations.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from growth.brain.schemas import (
    BrainDecision,
    DecisionType,
    ConfidenceLevel,
    ContentOpportunity,
    Hypothesis
)
from growth.brain.memory import BrainMemory
from growth.brain.evidence import EvidenceEvaluator
from growth.brain.opportunity_engine import OpportunityEngine
from growth.brain.hypothesis_engine import HypothesisEngine
from growth.brain.explanation_engine import ExplanationEngine


class DecisionEngine:
    """
    Core strategic decision synthesizer for Content Brain.
    Ensures experimental balance, portfolio distribution, and safety guards.
    """

    def __init__(
        self,
        memory: BrainMemory,
        evaluator: Optional[EvidenceEvaluator] = None,
        opp_engine: Optional[OpportunityEngine] = None,
        hyp_engine: Optional[HypothesisEngine] = None,
        expl_engine: Optional[ExplanationEngine] = None
    ):
        self.memory = memory
        self.evaluator = evaluator or EvidenceEvaluator(memory)
        self.opp_engine = opp_engine or OpportunityEngine(memory, self.evaluator)
        self.hyp_engine = hyp_engine or HypothesisEngine(memory, self.evaluator)
        self.expl_engine = expl_engine or ExplanationEngine()

    def recommend_next_decision(self, channel_id: str) -> BrainDecision:
        """
        Generates the next strategic decision for a channel.
        Prioritizes active experiment cohort balancing, then portfolio allocation.
        """
        strat = self.memory.get_active_strategy(channel_id)
        strategy_version = strat.get("strategy_version", "v1.0")

        # 1. Inspect Active Experiments
        exps = self.memory.get_experiments(channel_id)["active"]
        ranked_opps = self.opp_engine.rank_opportunities(channel_id, limit=5)
        top_opp = ranked_opps[0] if ranked_opps else ContentOpportunity(
            opportunity_id="opp_default",
            channel_id=channel_id,
            topic="What if the Library of Alexandria survived?",
            topic_cluster="Ancient Turning Points",
            content_angle="Alternate History",
            proposed_hook="What if Alexandria never burned?",
            audience_reason="Core niche fit",
            overall_score=0.8
        )

        if exps:
            active_exp = exps[0]
            exp_id = active_exp["experiment_id"]
            var_tested = active_exp.get("variable_tested", "HOOK_STRUCTURE")
            arms = active_exp.get("arms", [])

            # Count published samples per arm
            sample_counts = {}
            ctrl_arm = None
            treat_arm = None

            for arm in arms:
                arm_type = arm.get("arm_type", "").upper()
                arm_id = arm.get("arm_id")
                cnt = arm.get("sample_count", 0)
                sample_counts[arm_type] = cnt
                if arm_type == "CONTROL":
                    ctrl_arm = arm
                elif arm_type == "TREATMENT":
                    treat_arm = arm

            n_ctrl = sample_counts.get("CONTROL", 0)
            n_treat = sample_counts.get("TREATMENT", 0)

            # Check if experiment is fully saturated (both arms >= 4)
            if n_ctrl >= 4 and n_treat >= 4:
                return BrainDecision(
                    decision_id=f"dec_{channel_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    channel_id=channel_id,
                    decision_type=DecisionType.DO_NOT_RUN_SATURATED,
                    opportunity=top_opp,
                    experiment_id=exp_id,
                    variable_under_test=var_tested,
                    confidence=ConfidenceLevel.HIGH,
                    reasoning=f"Experiment '{exp_id}' has reached target sample size (Control: {n_ctrl}, Treatment: {n_treat}). Ready for evaluation.",
                    explanation_breakdown={
                        "why_this_decision": "Experiment sample target satisfied. Do not run further samples until outcome is evaluated.",
                        "next_step": "Run experiment outcome evaluation."
                    },
                    portfolio_tier="proven",
                    strategy_version=strategy_version
                )

            # Dynamic Cohort Balancing: Prioritize lagging arm
            if n_ctrl < n_treat:
                target_arm_type = "CONTROL"
                target_arm_id = ctrl_arm["arm_id"] if ctrl_arm else f"{exp_id}_control"
            elif n_treat < n_ctrl:
                target_arm_type = "TREATMENT"
                target_arm_id = treat_arm["arm_id"] if treat_arm else f"{exp_id}_treatment"
            else:
                # Tied: default to CONTROL first
                target_arm_type = "CONTROL"
                target_arm_id = ctrl_arm["arm_id"] if ctrl_arm else f"{exp_id}_control"

            # Formulate hypothesis
            hyp = self.hyp_engine.generate_hypothesis(channel_id, var_tested, top_opp.topic_cluster)

            # Generate full 10-point explanation
            explanation = self.expl_engine.generate_explanation(
                opportunity=top_opp,
                hypothesis=hyp,
                arm_type=target_arm_type,
                sample_counts=sample_counts,
                confidence=hyp.confidence
            )

            reasoning = (
                f"Active experiment '{exp_id}' tests '{var_tested}'. "
                f"Cohort balance: TREATMENT={n_treat}, CONTROL={n_ctrl}. "
                f"Assigning {target_arm_type} arm to balance empirical sample distribution."
            )

            return BrainDecision(
                decision_id=f"dec_{channel_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                channel_id=channel_id,
                decision_type=DecisionType.RUN_EXPERIMENT,
                opportunity=top_opp,
                hypothesis=hyp,
                experiment_id=exp_id,
                arm_id=target_arm_id,
                arm_type=target_arm_type,
                variable_under_test=var_tested,
                invariants=hyp.invariants,
                confidence=hyp.confidence,
                reasoning=reasoning,
                explanation_breakdown=explanation,
                portfolio_tier="adjacent",
                strategy_version=strategy_version
            )

        # 2. No active experiments: Propose Proven baseline or Adjacent exploration
        hyp = self.hyp_engine.generate_hypothesis(channel_id, "HOOK_STRUCTURE", top_opp.topic_cluster)
        explanation = self.expl_engine.generate_explanation(
            opportunity=top_opp,
            hypothesis=None,
            arm_type=None,
            sample_counts={},
            confidence=ConfidenceLevel.LOW
        )

        return BrainDecision(
            decision_id=f"dec_{channel_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            channel_id=channel_id,
            decision_type=DecisionType.PRODUCE_PROVEN,
            opportunity=top_opp,
            hypothesis=hyp,
            invariants=hyp.invariants,
            confidence=ConfidenceLevel.LOW,
            reasoning=f"No active experiments. Recommending top-ranked opportunity '{top_opp.topic}' in cluster '{top_opp.topic_cluster}'.",
            explanation_breakdown=explanation,
            portfolio_tier="proven",
            strategy_version=strategy_version
        )
