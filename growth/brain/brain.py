# -*- coding: utf-8 -*-
"""
brain.py
--------
Content Brain V1 Facade.
Unified interface for memory retrieval, opportunity discovery, hypothesis formation,
multi-factor scoring, and explainable decision generation.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any

from growth.db.database import DEFAULT_DB_PATH
from growth.brain.schemas import BrainDecision, ContentOpportunity, Hypothesis
from growth.brain.memory import BrainMemory
from growth.brain.evidence import EvidenceEvaluator
from growth.brain.opportunity_engine import OpportunityEngine
from growth.brain.hypothesis_engine import HypothesisEngine
from growth.brain.decision_engine import DecisionEngine
from growth.brain.explanation_engine import ExplanationEngine


class ContentBrain:
    """
    Unified Content Brain V1 Facade.
    Acts as a strategic decision engine without direct publishing authority.
    """

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.memory = BrainMemory(self.db_path)
        self.evaluator = EvidenceEvaluator(self.memory)
        self.opp_engine = OpportunityEngine(self.memory, self.evaluator)
        self.hyp_engine = HypothesisEngine(self.memory, self.evaluator)
        self.expl_engine = ExplanationEngine()
        self.decision_engine = DecisionEngine(
            memory=self.memory,
            evaluator=self.evaluator,
            opp_engine=self.opp_engine,
            hyp_engine=self.hyp_engine,
            expl_engine=self.expl_engine
        )

    def get_status(self, channel_id: str) -> Dict[str, Any]:
        """
        Provides a comprehensive overview of active strategy, experiments,
        portfolio allocations, and pending decisions for a channel.
        """
        snapshot = self.memory.get_snapshot(channel_id)
        decision = self.decision_engine.recommend_next_decision(channel_id)

        strat = snapshot.active_strategy
        alloc = strat.get("portfolio_allocation", {"proven": 0.70, "adjacent": 0.20, "exploratory": 0.10})

        return {
            "channel_id": channel_id,
            "strategy_version": snapshot.strategy_version,
            "published_videos_count": snapshot.published_videos_count,
            "active_experiments_count": len(snapshot.active_experiments),
            "completed_experiments_count": len(snapshot.completed_experiments),
            "active_arms_sample_counts": snapshot.first_party_samples_by_arm,
            "learning_events_count": len(snapshot.learning_events),
            "external_priors_count": len(snapshot.external_priors),
            "portfolio_allocation": alloc,
            "next_recommended_decision": {
                "decision_type": decision.decision_type.value,
                "arm_type": decision.arm_type,
                "variable_under_test": decision.variable_under_test,
                "topic": decision.opportunity.topic if decision.opportunity else None,
                "confidence": decision.confidence.value,
                "reasoning": decision.reasoning
            }
        }

    def get_memory_view(self, channel_id: str) -> Dict[str, Any]:
        """
        Returns structured view of everything the Brain currently 'knows' about a channel.
        """
        snapshot = self.memory.get_snapshot(channel_id)
        return snapshot.to_dict()

    def get_ranked_opportunities(self, channel_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Returns scored and ranked content opportunities with factor breakdown.
        """
        opps = self.opp_engine.rank_opportunities(channel_id, limit=limit)
        return [o.to_dict() for o in opps]

    def recommend_next(self, channel_id: str) -> BrainDecision:
        """
        Generates the next strategic decision.
        """
        return self.decision_engine.recommend_next_decision(channel_id)

    def next_production_decision(self, channel_id: str) -> BrainDecision:
        """
        Operational endpoint for determining the next production decision.
        Inspects active experiments, cohort balances, 70/20/10 portfolio,
        and returns a fully traceable BrainDecision.
        """
        return self.decision_engine.recommend_next_decision(channel_id)

    def explain_recommendation(self, channel_id: str) -> Dict[str, Any]:
        """
        Returns deep 10-point explanation for the current recommendation.
        """
        decision = self.recommend_next(channel_id)
        return {
            "decision_id": decision.decision_id,
            "channel_id": decision.channel_id,
            "decision_type": decision.decision_type.value,
            "arm_type": decision.arm_type,
            "variable_under_test": decision.variable_under_test,
            "confidence": decision.confidence.value,
            "reasoning": decision.reasoning,
            "explanation": decision.explanation_breakdown,
            "invariants": decision.invariants
        }

    def get_belief_state(self, channel_id: str) -> List[Dict[str, Any]]:
        """
        Returns current empirical belief states for the channel.
        """
        from growth.brain.belief_engine import BeliefEngine
        engine = BeliefEngine(self.repo, self.ext_repo)
        return [b.to_dict() for b in engine.get_channel_beliefs(channel_id)]

    def get_negative_knowledge(self, channel_id: str) -> Dict[str, Any]:
        """
        Returns institutional negative knowledge (DO_NOT_USE registry).
        """
        from growth.brain.belief_engine import BeliefEngine
        engine = BeliefEngine(self.repo, self.ext_repo)
        return engine.get_negative_knowledge(channel_id)

    def run_weekly_learning_cycle(self, channel_id: str) -> Dict[str, Any]:
        """
        Executes complete weekly learning cycle and writes WEEKLY_LEARNING_REPORT.md.
        """
        from growth.brain.weekly_cycle import WeeklyLearningCycle
        cycle = WeeklyLearningCycle(self.repo)
        return cycle.run_weekly_cycle(channel_id)
