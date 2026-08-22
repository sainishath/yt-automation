# -*- coding: utf-8 -*-
"""
schemas.py
----------
Data schemas and contracts for Brain V1.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime


class EvidenceSource(Enum):
    FIRST_PARTY_CONTROLLED = "FIRST_PARTY_CONTROLLED"
    FIRST_PARTY_OBSERVATIONAL = "FIRST_PARTY_OBSERVATIONAL"
    EXTERNAL_PUBLIC = "EXTERNAL_PUBLIC"
    EXTERNAL_RESEARCH = "EXTERNAL_RESEARCH"
    FIRST_PARTY_SNAPSHOT = "FIRST_PARTY_SNAPSHOT"
    FIRST_PARTY_EXPERIMENT = "FIRST_PARTY_EXPERIMENT"
    FIRST_PARTY_PATTERN = "FIRST_PARTY_PATTERN"
    EXTERNAL_PRIOR = "EXTERNAL_PRIOR"
    EXTERNAL_PATTERN = "EXTERNAL_PATTERN"
    HEURISTIC = "HEURISTIC"


class ConfidenceLevel(Enum):
    LOW = "LOW"        # Hypothesis only, external evidence only, N < 4, or insufficient samples
    MEDIUM = "MEDIUM"  # Multiple observations, partial first-party support, emerging pattern
    HIGH = "HIGH"      # Completed experiment with N >= 4, consistent first-party evidence


class KnowledgeLevel(Enum):
    CHANNEL = "CHANNEL"
    TOPIC_CLUSTER = "TOPIC_CLUSTER"
    TOPIC = "TOPIC"
    HOOK_STRUCTURE = "HOOK_STRUCTURE"
    FORMAT = "FORMAT"
    EXPERIMENT_VARIABLE = "EXPERIMENT_VARIABLE"
    SPECIFIC_COMBINATION = "SPECIFIC_COMBINATION"


@dataclass
class EvidenceItem:
    source: EvidenceSource
    metric_name: str
    metric_value: float
    sample_size: int
    description: str
    provenance: str
    confidence: ConfidenceLevel = ConfidenceLevel.LOW

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source.value,
            "metric_name": self.metric_name,
            "metric_value": round(self.metric_value, 4),
            "sample_size": self.sample_size,
            "description": self.description,
            "provenance": self.provenance,
            "confidence": self.confidence.value
        }


class KnowledgeState(Enum):
    SUPPORTED = "SUPPORTED"      # Validated by completed experiment N >= 4
    PROMISING = "PROMISING"      # Positive emerging trend or valid external prior
    UNCERTAIN = "UNCERTAIN"      # Untested gap or neutral outcome
    REJECTED = "REJECTED"        # Empirically failed first-party experiment
    CONTRADICTED = "CONTRADICTED"# Contradicted by FIRST_PARTY_OVERRIDE
    UNTESTED = "UNTESTED"        # No empirical data yet


@dataclass
class ContentOpportunity:
    opportunity_id: str
    channel_id: str
    topic: str
    topic_cluster: str
    content_angle: str
    proposed_hook: str
    audience_reason: str
    evidence_items: List[EvidenceItem] = field(default_factory=list)
    novelty_score: float = 0.5
    experiment_value: float = 0.5
    production_feasibility: float = 1.0
    first_party_support: float = 0.0
    external_support: float = 0.0
    uncertainty_penalty: float = 0.0
    repetition_penalty: float = 0.0
    overall_score: float = 0.5
    portfolio_tier: str = "proven"  # 'proven', 'adjacent', 'exploratory'
    knowledge_state: str = "UNTESTED"
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "channel_id": self.channel_id,
            "topic": self.topic,
            "topic_cluster": self.topic_cluster,
            "content_angle": self.content_angle,
            "proposed_hook": self.proposed_hook,
            "audience_reason": self.audience_reason,
            "evidence_items": [e.to_dict() for e in self.evidence_items],
            "novelty_score": round(self.novelty_score, 3),
            "experiment_value": round(self.experiment_value, 3),
            "production_feasibility": round(self.production_feasibility, 3),
            "first_party_support": round(self.first_party_support, 3),
            "external_support": round(self.external_support, 3),
            "uncertainty_penalty": round(self.uncertainty_penalty, 3),
            "repetition_penalty": round(self.repetition_penalty, 3),
            "overall_score": round(self.overall_score, 3),
            "portfolio_tier": self.portfolio_tier,
            "knowledge_state": self.knowledge_state,
            "explanation": self.explanation
        }


@dataclass
class Hypothesis:
    hypothesis_id: str
    channel_id: str
    statement: str
    variable_under_test: str
    control_spec: str
    treatment_spec: str
    invariants: List[str] = field(default_factory=list)
    expected_learning: str = ""
    uncertainty_addressed: str = ""
    supported_by: List[EvidenceItem] = field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.LOW

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "channel_id": self.channel_id,
            "statement": self.statement,
            "variable_under_test": self.variable_under_test,
            "control_spec": self.control_spec,
            "treatment_spec": self.treatment_spec,
            "invariants": self.invariants,
            "expected_learning": self.expected_learning,
            "uncertainty_addressed": self.uncertainty_addressed,
            "supported_by": [e.to_dict() for e in self.supported_by],
            "confidence": self.confidence.value
        }


class DecisionType(Enum):
    RUN_EXPERIMENT = "RUN_EXPERIMENT"
    PRODUCE_PROVEN = "PRODUCE_PROVEN"
    EXPLORE_ADJACENT = "EXPLORE_ADJACENT"
    AWAIT_EVIDENCE = "AWAIT_EVIDENCE"
    DO_NOT_RUN_SATURATED = "DO_NOT_RUN_SATURATED"


@dataclass
class BrainDecision:
    decision_id: str
    channel_id: str
    decision_type: DecisionType
    opportunity: Optional[ContentOpportunity] = None
    hypothesis: Optional[Hypothesis] = None
    experiment_id: Optional[str] = None
    arm_id: Optional[str] = None
    arm_type: Optional[str] = None  # 'CONTROL' or 'TREATMENT'
    variable_under_test: Optional[str] = None
    invariants: List[str] = field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    reasoning: str = ""
    explanation_breakdown: Dict[str, str] = field(default_factory=dict)
    portfolio_tier: str = "proven"
    strategy_version: str = "v1.0"
    created_at: str = field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "channel_id": self.channel_id,
            "decision_type": self.decision_type.value,
            "opportunity": self.opportunity.to_dict() if self.opportunity else None,
            "hypothesis": self.hypothesis.to_dict() if self.hypothesis else None,
            "experiment_id": self.experiment_id,
            "arm_id": self.arm_id,
            "arm_type": self.arm_type,
            "variable_under_test": self.variable_under_test,
            "invariants": self.invariants,
            "confidence": self.confidence.value,
            "reasoning": self.reasoning,
            "explanation_breakdown": self.explanation_breakdown,
            "portfolio_tier": self.portfolio_tier,
            "strategy_version": self.strategy_version,
            "created_at": self.created_at
        }


@dataclass
class BrainMemorySnapshot:
    channel_id: str
    strategy_version: str
    active_strategy: Dict[str, Any]
    published_videos_count: int
    active_experiments: List[Dict[str, Any]]
    completed_experiments: List[Dict[str, Any]]
    first_party_samples_by_arm: Dict[str, int]
    learning_events: List[Dict[str, Any]]
    external_priors: List[Dict[str, Any]]
    cluster_performance: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    hook_performance: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "strategy_version": self.strategy_version,
            "active_strategy": self.active_strategy,
            "published_videos_count": self.published_videos_count,
            "active_experiments": self.active_experiments,
            "completed_experiments": self.completed_experiments,
            "first_party_samples_by_arm": self.first_party_samples_by_arm,
            "learning_events": self.learning_events,
            "external_priors": self.external_priors,
            "cluster_performance": self.cluster_performance,
            "hook_performance": self.hook_performance
        }
