# -*- coding: utf-8 -*-
"""
recommendation_engine.py
------------------------
Converts external evidence and priors into explainable recommendations and controlled A/B experiment proposals.
Guarantees full transparency across evidence, transferability, confidence, and test parameters.
"""

from typing import Dict, Any, List, Optional
from growth.external_intelligence.schemas import (
    ExternalPriorModel,
    ExternalPatternModel,
    TransferabilityScoreModel,
    TransferabilityClassification,
    PriorStatus
)


def generate_experiment_proposal_from_prior(
    prior: ExternalPriorModel,
    pattern: ExternalPatternModel,
    target_channel_id: str
) -> Dict[str, Any]:
    """
    Creates a production-ready single-variable A/B experiment definition compatible with ExperimentManager.
    Enforces minimum sample size N >= 4 per cohort.
    """
    exp_suffix = "HOOK_02" if "hook" in pattern.pattern_id else "TOPIC_02"
    channel_letter = "A" if target_channel_id == "channel_a" else "B"
    exp_id = f"EXP_{channel_letter}_EXT_{exp_suffix}"

    if target_channel_id == "channel_a":
        control_def = "Standard Chronos Shift Question Hook (e.g., 'What if Rome never fell?')"
        variant_def = pattern.our_possible_implementation
        primary_metric = "avg_percentage_viewed"
    else:
        control_def = "Standard Debate Protocol Neutral Opening"
        variant_def = pattern.our_possible_implementation
        primary_metric = "engagement_rate"

    return {
        "experiment_id": exp_id,
        "channel_id": target_channel_id,
        "name": f"External Prior Test: {pattern.name}",
        "hypothesis": prior.hypothesis,
        "variable_tested": pattern.pattern_type.value if hasattr(pattern.pattern_type, 'value') else str(pattern.pattern_type),
        "control_definition": control_def,
        "variant_definition": variant_def,
        "primary_metric": primary_metric,
        "min_sample_size": 4,
        "status": "PROPOSED",
        "evidence_source": f"Observed across {pattern.channel_count} analog channels ({pattern.video_count} videos)",
        "confidence": pattern.confidence,
        "transferability": prior.transferability_classification
    }


def build_explainable_recommendation(
    prior: ExternalPriorModel,
    pattern: ExternalPatternModel,
    transferability: TransferabilityScoreModel
) -> Dict[str, Any]:
    """Constructs a fully explainable recommendation card."""
    return {
        "what": f"Test {pattern.name}",
        "why": pattern.underlying_principle,
        "evidence": f"Corroborated across {pattern.channel_count} analog channels ({pattern.video_count} public videos)",
        "transferability": transferability.classification.value if hasattr(transferability.classification, 'value') else transferability.classification,
        "transferability_reason": transferability.reason,
        "confidence": pattern.confidence,
        "action": f"Launch controlled A/B experiment comparing control baseline vs '{pattern.our_possible_implementation}'",
        "status": prior.status.value if hasattr(prior.status, 'value') else prior.status,
        "prior_weight": prior.prior_weight
    }
