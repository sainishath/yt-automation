# -*- coding: utf-8 -*-
"""
schemas.py
----------
Core dataclasses, enums, and schema definitions for the External Intelligence Layer.
Strictly enforces data provenance and the 5-level evidence hierarchy.
"""

from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from datetime import datetime


class ProvenanceSource(str, Enum):
    REAL_EXTERNAL_DATA = "REAL_EXTERNAL_DATA"
    PUBLIC_YOUTUBE = "PUBLIC_YOUTUBE"
    SIMULATION = "SIMULATION"


class EvidenceLevel(str, Enum):
    LEVEL_1_OBSERVATION = "OBSERVATION"                 # Directly observable fact
    LEVEL_2_EXTERNAL_EVIDENCE = "EXTERNAL_EVIDENCE"     # Corroborated external pattern / relative performance
    LEVEL_3_HYPOTHESIS = "HYPOTHESIS"                   # External Prior / hypothesis to test
    LEVEL_4_FIRST_PARTY_EVIDENCE = "FIRST_PARTY_EVIDENCE" # Our own empirical experimental data
    LEVEL_5_CONFIRMED_LEARNING = "CONFIRMED_LEARNING"   # Statistically validated strategy promotion


class ObservationType(str, Enum):
    OBJECTIVE_FACT = "OBJECTIVE_FACT"
    INTERPRETATION = "INTERPRETATION"


class TransferabilityClassification(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    DO_NOT_TRANSFER = "DO_NOT_TRANSFER"


class PriorStatus(str, Enum):
    HYPOTHESIS = "HYPOTHESIS"
    TESTING = "TESTING"
    SUPPORTED = "SUPPORTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class PatternType(str, Enum):
    HOOK_STRUCTURE = "HOOK_STRUCTURE"
    TOPIC_CLUSTER = "TOPIC_CLUSTER"
    NARRATIVE_FLOW = "NARRATIVE_FLOW"
    CTA_FORMAT = "CTA_FORMAT"


class ResearchStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


@dataclass
class ExternalChannelModel:
    external_channel_id: str
    target_channel_id: str  # 'channel_a' or 'channel_b'
    channel_title: str
    handle: Optional[str] = None
    youtube_channel_id: Optional[str] = None
    subscriber_count: int = 0
    video_count: int = 0
    content_niche: str = ""
    similarity_score: float = 0.0
    similarity_reasons: List[str] = field(default_factory=list)
    confidence: str = "HIGH"
    is_simulation: bool = False
    source_type: ProvenanceSource = ProvenanceSource.PUBLIC_YOUTUBE
    discovered_at: Optional[str] = None
    last_researched_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExternalVideoModel:
    external_video_id: str
    external_channel_id: str
    youtube_video_id: str
    title: str
    url: str
    published_at: Optional[str] = None
    duration_seconds: float = 0.0
    is_short: bool = True
    views: int = 0
    likes: int = 0
    comments: int = 0
    relative_view_multiplier: float = 1.0
    collected_at: Optional[str] = None
    is_simulation: bool = False
    source_type: ProvenanceSource = ProvenanceSource.PUBLIC_YOUTUBE

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExternalObservationModel:
    observation_id: str
    external_video_id: str
    observation_type: ObservationType
    field_name: str
    observed_value: str
    interpretation: Optional[str] = None
    evidence_level: EvidenceLevel = EvidenceLevel.LEVEL_1_OBSERVATION
    confidence: float = 1.0
    is_simulation: bool = False
    source_type: ProvenanceSource = ProvenanceSource.PUBLIC_YOUTUBE
    recorded_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["observation_type"] = self.observation_type.value if isinstance(self.observation_type, ObservationType) else self.observation_type
        d["evidence_level"] = self.evidence_level.value if isinstance(self.evidence_level, EvidenceLevel) else self.evidence_level
        d["source_type"] = self.source_type.value if isinstance(self.source_type, ProvenanceSource) else self.source_type
        return d


@dataclass
class ExternalEvidenceModel:
    evidence_id: str
    target_channel_id: str
    pattern_type: PatternType
    claim_summary: str
    supporting_channel_count: int = 0
    supporting_video_count: int = 0
    performance_evidence: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    is_simulation: bool = False
    source_type: ProvenanceSource = ProvenanceSource.PUBLIC_YOUTUBE
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["pattern_type"] = self.pattern_type.value if isinstance(self.pattern_type, PatternType) else self.pattern_type
        d["source_type"] = self.source_type.value if isinstance(self.source_type, ProvenanceSource) else self.source_type
        return d


@dataclass
class ExternalPatternModel:
    pattern_id: str
    target_channel_id: str
    pattern_type: PatternType
    name: str
    description: str
    surface_technique: str
    underlying_principle: str
    our_possible_implementation: str
    frequency: float = 0.0
    channel_count: int = 0
    video_count: int = 0
    supporting_observations: List[str] = field(default_factory=list)
    consistency_score: float = 0.0
    confidence: float = 0.0
    is_simulation: bool = False
    source_type: ProvenanceSource = ProvenanceSource.PUBLIC_YOUTUBE
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["pattern_type"] = self.pattern_type.value if isinstance(self.pattern_type, PatternType) else self.pattern_type
        d["source_type"] = self.source_type.value if isinstance(self.source_type, ProvenanceSource) else self.source_type
        return d


@dataclass
class TransferabilityScoreModel:
    transferability_id: str
    pattern_id: str
    target_channel_id: str
    topic_similarity: float
    audience_similarity: float
    format_similarity: float
    production_similarity: float
    evidence_strength: float
    repeatability: float
    overall_transferability_score: float
    classification: TransferabilityClassification
    reason: str
    evaluated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["classification"] = self.classification.value if isinstance(self.classification, TransferabilityClassification) else self.classification
        return d


@dataclass
class ExternalPriorModel:
    prior_id: str
    target_channel_id: str
    pattern_id: str
    hypothesis: str
    transferability_classification: TransferabilityClassification
    prior_weight: float = 0.20
    status: PriorStatus = PriorStatus.HYPOTHESIS
    first_party_override_reason: Optional[str] = None
    created_at: Optional[str] = None
    review_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["transferability_classification"] = (
            self.transferability_classification.value
            if isinstance(self.transferability_classification, TransferabilityClassification)
            else self.transferability_classification
        )
        d["status"] = self.status.value if isinstance(self.status, PriorStatus) else self.status
        return d


@dataclass
class ResearchRunModel:
    run_id: str
    target_channel_id: str
    channels_scanned: int = 0
    videos_analyzed: int = 0
    patterns_discovered: int = 0
    priors_generated: int = 0
    status: ResearchStatus = ResearchStatus.IN_PROGRESS
    error_message: Optional[str] = None
    is_simulation: bool = False
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value if isinstance(self.status, ResearchStatus) else self.status
        return d
