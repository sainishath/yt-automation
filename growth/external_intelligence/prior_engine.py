# -*- coding: utf-8 -*-
"""
prior_engine.py
---------------
Converts high-transferability external patterns into bounded external priors.
Strictly enforces First-Party Evidence Dominance: empirical first-party test results
always override external competitor observations.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from growth.external_intelligence.schemas import (
    ExternalPatternModel,
    TransferabilityScoreModel,
    ExternalPriorModel,
    TransferabilityClassification,
    PriorStatus
)


def generate_prior_from_transferability(
    pattern: ExternalPatternModel,
    transferability: TransferabilityScoreModel,
    max_prior_weight: float = 0.25
) -> Optional[ExternalPriorModel]:
    """
    Generates a bounded external prior if transferability is HIGH or MEDIUM.
    LOW or DO_NOT_TRANSFER patterns are rejected from prior generation.
    """
    if transferability.classification in [TransferabilityClassification.LOW, TransferabilityClassification.DO_NOT_TRANSFER]:
        return None

    # Bounded prior weight scaling with transferability and pattern confidence
    raw_weight = transferability.overall_transferability_score * pattern.confidence * 0.25
    bounded_weight = round(min(max(raw_weight, 0.05), max_prior_weight), 2)

    prior_id = f"prior_{pattern.pattern_id}"
    hypothesis = (
        f"Implementing '{pattern.our_possible_implementation}' (derived from external pattern '{pattern.name}') "
        f"will improve channel relative performance by >= 5% in target niche."
    )

    review_date = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")

    return ExternalPriorModel(
        prior_id=prior_id,
        target_channel_id=pattern.target_channel_id,
        pattern_id=pattern.pattern_id,
        hypothesis=hypothesis,
        transferability_classification=transferability.classification,
        prior_weight=bounded_weight,
        status=PriorStatus.HYPOTHESIS,
        review_by=review_date
    )


def apply_first_party_override(
    prior: ExternalPriorModel,
    first_party_experiment_result: Dict[str, Any]
) -> ExternalPriorModel:
    """
    ARCHITECTURAL INVARIANT: FIRST_PARTY_EVIDENCE > EXTERNAL_ANALOG_EVIDENCE.
    
    If our own empirical experiment demonstrates that a hypothesis failed (e.g., REJECT_VARIANT or negative delta),
    the external prior is immediately demoted or marked REJECTED, overriding external observations.
    """
    verdict = first_party_experiment_result.get("verdict", "")
    decision = first_party_experiment_result.get("decision", "")
    delta_pct = float(first_party_experiment_result.get("delta_percentage", 0.0))
    sample_count = int(first_party_experiment_result.get("control_count", 0))

    if sample_count >= 4:
        if decision == "REJECT_VARIANT" or delta_pct <= -5.0:
            prior.status = PriorStatus.REJECTED
            prior.prior_weight = 0.0
            prior.first_party_override_reason = (
                f"First-party empirical test (N={sample_count}) contradicted external prior with {delta_pct}% delta. "
                "First-party evidence overrides external competitor observation."
            )
        elif decision == "ACCEPT_VARIANT" and delta_pct >= 5.0:
            prior.status = PriorStatus.SUPPORTED
            prior.first_party_override_reason = (
                f"First-party empirical test (N={sample_count}) confirmed external hypothesis with +{delta_pct}% delta."
            )
        else:
            prior.status = PriorStatus.TESTING
            prior.first_party_override_reason = f"First-party empirical test inconclusive ({delta_pct}% delta). Continuing testing."

    return prior
