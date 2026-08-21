# -*- coding: utf-8 -*-
"""
growth/brain/__init__.py
-----------------------
Content Brain V1 Subsystem.
Closed-loop learning, hypothesis formation, opportunity scoring, and decision engine.
"""

from growth.brain.schemas import (
    EvidenceSource,
    ConfidenceLevel,
    EvidenceItem,
    KnowledgeLevel,
    KnowledgeState,
    ContentOpportunity,
    Hypothesis,
    DecisionType,
    BrainDecision,
    BrainMemorySnapshot
)
from growth.brain.memory import BrainMemory
from growth.brain.evidence import EvidenceEvaluator
from growth.brain.evaluator import MultiArmExperimentEvaluator, EvaluationReport, ExperimentDecision
from growth.brain.learning_engine import LearningEngine
from growth.brain.strategy_evolution import StrategyEvolutionEngine
from growth.brain.opportunity_engine import OpportunityEngine
from growth.brain.hypothesis_engine import HypothesisEngine
from growth.brain.decision_engine import DecisionEngine
from growth.brain.explanation_engine import ExplanationEngine
from growth.brain.brain import ContentBrain
from growth.brain.cycle import DailyBrainCycle
from growth.brain.production_recommendation import ProductionRecommendation, ProductionRecommendationEngine
from growth.brain.backtester import BacktestReport, BrainBacktester
from growth.brain.belief_engine import (
    BeliefEngine,
    VideoMaturity,
    BeliefStatus,
    VideoDiagnostic,
    PatternBelief
)
from growth.brain.weekly_cycle import WeeklyLearningCycle
from growth.brain.learning_trace import VideoLearningTrace, LearningTraceEngine
from growth.brain.channel_trajectory import (
    ChannelHealthSnapshot,
    ScorecardMetric,
    ChannelImprovementScorecard,
    ChannelTrajectoryEngine
)

__all__ = [
    "EvidenceSource",
    "ConfidenceLevel",
    "EvidenceItem",
    "KnowledgeLevel",
    "KnowledgeState",
    "ContentOpportunity",
    "Hypothesis",
    "DecisionType",
    "BrainDecision",
    "BrainMemorySnapshot",
    "BrainMemory",
    "EvidenceEvaluator",
    "MultiArmExperimentEvaluator",
    "EvaluationReport",
    "ExperimentDecision",
    "LearningEngine",
    "StrategyEvolutionEngine",
    "OpportunityEngine",
    "HypothesisEngine",
    "DecisionEngine",
    "ExplanationEngine",
    "ContentBrain",
    "DailyBrainCycle",
    "ProductionRecommendation",
    "ProductionRecommendationEngine",
    "BacktestReport",
    "BrainBacktester",
    "BeliefEngine",
    "VideoMaturity",
    "BeliefStatus",
    "VideoDiagnostic",
    "PatternBelief",
    "WeeklyLearningCycle",
    "VideoLearningTrace",
    "LearningTraceEngine",
    "ChannelHealthSnapshot",
    "ScorecardMetric",
    "ChannelImprovementScorecard",
    "ChannelTrajectoryEngine",
]
