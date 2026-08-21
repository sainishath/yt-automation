# -*- coding: utf-8 -*-
"""
transferability.py
------------------
Evaluates whether an externally successful technique or pattern is transferable to our channels.
Distinguishes surface competitor techniques from underlying principles and assigns bounded transferability classifications.
"""

from typing import Dict, Any, List, Optional
from growth.external_intelligence.schemas import (
    ExternalPatternModel,
    TransferabilityScoreModel,
    TransferabilityClassification
)


def evaluate_pattern_transferability(
    pattern: Any,
    target_channel_id: Any,
    target_channel_profile: Optional[Dict[str, Any]] = None
) -> TransferabilityScoreModel:
    """
    Evaluates transferability across 6 core dimensions:
      1. Topic Similarity (0.25)
      2. Audience Similarity (0.20)
      3. Format Similarity (0.20)
      4. Production Model Compatibility (0.15)
      5. Evidence Strength (0.10)
      6. Repeatability (0.10)
    """
    if isinstance(pattern, str) and not isinstance(target_channel_id, str):
        # Swap inverted arguments
        pattern, target_channel_id = target_channel_id, pattern

    # Baseline dimension estimations based on target channel & pattern type
    if str(target_channel_id) == "channel_a":
        # Channel A = Chronos Shift (Cinematic Alternate History, Fooocus SDXL, Ken Burns Candidate A)
        if "ANCIENT" in pattern.name.upper() or "COUNTERFACTUAL" in pattern.name.upper() or "WARFARE" in pattern.name.upper():
            topic_sim = 0.95
            aud_sim = 0.90
            format_sim = 0.95
            prod_sim = 0.90
        elif "TALKING_HEAD" in pattern.surface_technique.upper() or "LIVE_ACTION" in pattern.surface_technique.upper():
            topic_sim = 0.85
            aud_sim = 0.85
            format_sim = 0.80
            prod_sim = 0.20  # Incompatible with our AI image generation model
        else:
            topic_sim = 0.75
            aud_sim = 0.75
            format_sim = 0.85
            prod_sim = 0.80

    else:
        # Channel B = Debate Protocol (Two-host Socratic debates, Piper TTS, Gameplay canvas)
        if "PROVOCATION" in pattern.name.upper() or "SOCRATIC" in pattern.name.upper() or "AI" in pattern.name.upper() or "BIAS" in pattern.name.upper():
            topic_sim = 0.95
            aud_sim = 0.92
            format_sim = 0.95
            prod_sim = 0.92
        elif "FULL_CINEMATIC_RECREATION" in pattern.surface_technique.upper():
            topic_sim = 0.80
            aud_sim = 0.80
            format_sim = 0.80
            prod_sim = 0.30  # Channel B uses split-screen dialogue format
        else:
            topic_sim = 0.75
            aud_sim = 0.80
            format_sim = 0.85
            prod_sim = 0.85

    evidence_strength = min(max(pattern.confidence, 0.0), 1.0)
    repeatability = min(max(pattern.consistency_score, 0.0), 1.0)

    # Bounded weighted score
    overall_score = round(
        (0.25 * topic_sim) +
        (0.20 * aud_sim) +
        (0.20 * format_sim) +
        (0.15 * prod_sim) +
        (0.10 * evidence_strength) +
        (0.10 * repeatability),
        3
    )

    if prod_sim <= 0.25:
        classification = TransferabilityClassification.DO_NOT_TRANSFER if overall_score < 0.50 else TransferabilityClassification.LOW
        reason = (
            f"Production model incompatible ({round(prod_sim * 100)}%). Technique relies on assets/workflows "
            "(e.g., live presenter, manual studio footage) incompatible with our frozen generation standard."
        )
    elif overall_score >= 0.80:
        classification = TransferabilityClassification.HIGH
        reason = (
            f"Strong alignment ({round(overall_score * 100)}%) across topic ({round(topic_sim * 100)}%), "
            f"format ({round(format_sim * 100)}%), and our automated production architecture ({round(prod_sim * 100)}%). "
            f"Underlying principle '{pattern.underlying_principle}' directly translates into our pipeline."
        )
    elif overall_score >= 0.60:
        classification = TransferabilityClassification.MEDIUM
        reason = (
            f"Moderate alignment ({round(overall_score * 100)}%). Surface technique may differ, but the underlying "
            f"principle ('{pattern.underlying_principle}') is adaptable via '{pattern.our_possible_implementation}'."
        )
    elif overall_score >= 0.40:
        classification = TransferabilityClassification.LOW
        reason = (
            f"Low alignment ({round(overall_score * 100)}%). Significant disparity in production model or audience expectations. "
            "Adopt only as an isolated exploratory experiment."
        )
    else:
        classification = TransferabilityClassification.DO_NOT_TRANSFER
        reason = (
            f"Incompatible format or production model ({round(overall_score * 100)}%). Technique relies on assets or "
            "workflows incompatible with our frozen generation standard."
        )

    return TransferabilityScoreModel(
        transferability_id=f"ts_{pattern.pattern_id}",
        pattern_id=pattern.pattern_id,
        target_channel_id=target_channel_id,
        topic_similarity=topic_sim,
        audience_similarity=aud_sim,
        format_similarity=format_sim,
        production_similarity=prod_sim,
        evidence_strength=evidence_strength,
        repeatability=repeatability,
        overall_transferability_score=overall_score,
        classification=classification,
        reason=reason
    )
