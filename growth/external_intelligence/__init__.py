# -*- coding: utf-8 -*-
"""
External Intelligence Subsystem
-------------------------------
Studies legitimate publicly observable data from analogous YouTube channels
and converts evidence into structured priors, hypothesis candidates, and transferability models.
"""

from growth.external_intelligence.schemas import (
    ProvenanceSource,
    EvidenceLevel,
    ObservationType,
    TransferabilityClassification,
    PriorStatus,
    PatternType,
    ResearchStatus,
    ExternalChannelModel,
    ExternalVideoModel,
    ExternalObservationModel,
    ExternalEvidenceModel,
    ExternalPatternModel,
    TransferabilityScoreModel,
    ExternalPriorModel,
    ResearchRunModel,
)
from growth.external_intelligence.repository import ExternalIntelligenceRepository

__all__ = [
    "ProvenanceSource",
    "EvidenceLevel",
    "ObservationType",
    "TransferabilityClassification",
    "PriorStatus",
    "PatternType",
    "ResearchStatus",
    "ExternalChannelModel",
    "ExternalVideoModel",
    "ExternalObservationModel",
    "ExternalEvidenceModel",
    "ExternalPatternModel",
    "TransferabilityScoreModel",
    "ExternalPriorModel",
    "ResearchRunModel",
    "ExternalIntelligenceRepository",
]
