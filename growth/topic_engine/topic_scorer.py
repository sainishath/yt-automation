# -*- coding: utf-8 -*-
"""
topic_scorer.py
---------------
Multi-factor explainable scoring model for topic candidates (topic_score_v1.2).
Answers: "Why did we choose this topic?"
"""

from typing import Dict, Any
from growth.scorer import check_counterfactual_divergence, evaluate_6step_outlier_title_rubric


def score_topic(
    topic_text: str,
    channel_id: str,
    category: str,
    historical_cluster_avg: float = 0.80,
    novelty: float = 0.75,
    fact_check_difficulty: float = 0.30,
    external_prior_boost: float = 0.0
) -> Dict[str, Any]:
    """
    Computes an explainable topic score (v1.2 — with Counterfactual Divergence Pre-Check & 6-Step Outlier Rubric).
    Factors:
      - audience_fit (0.30 weight)
      - historical_performance (0.25 weight)
      - novelty (0.20 weight)
      - expected_retention (0.15 weight)
      - fact_check_penalty (0.10 weight)
      - bounded external prior boost (max +0.05)
      - counterfactual_divergence_gate (rejects non-counterfactual real-history tautologies on channel_a)
    """
    # Baseline audience fit heuristic based on keywords
    audience_fit = 0.85
    expected_retention = 0.82
    divergence_check = {"is_valid_counterfactual": True, "issues": []}
    outlier_rubric = None

    if channel_id == "channel_a":
        # History / Alternate History checks + Counterfactual Divergence Pre-Check
        keywords = ["rome", "alexandria", "empire", "war", "what if", "history", "invented", "conquered", "stalingrad", "constantinople", "napoleon"]
        match_count = sum(1 for kw in keywords if kw in topic_text.lower())
        audience_fit = min(0.70 + (match_count * 0.08), 0.98)
        divergence_check = check_counterfactual_divergence(topic_text)
        outlier_rubric = evaluate_6step_outlier_title_rubric(topic_text)
    else:
        # Debate / Psychology checks
        keywords = ["brain", "ai", "why", "psychology", "debate", "argue", "mind", "sleep", "deja vu"]
        match_count = sum(1 for kw in keywords if kw in topic_text.lower())
        audience_fit = min(0.70 + (match_count * 0.08), 0.98)

    historical_perf = max(min(historical_cluster_avg, 1.0), 0.1)
    ease_of_production = max(1.0 - fact_check_difficulty, 0.1)
    bounded_ext_boost = min(max(external_prior_boost, 0.0), 0.05)

    # Weighted composite score
    base_score = (
        (0.30 * audience_fit) +
        (0.25 * historical_perf) +
        (0.20 * novelty) +
        (0.15 * expected_retention) +
        (0.10 * ease_of_production)
    )
    final_score = round(min(base_score + bounded_ext_boost, 1.0), 3)

    # Enforce Counterfactual Divergence Pre-Check: penalize non-counterfactual "What If" titles
    if not divergence_check["is_valid_counterfactual"]:
        final_score = round(min(final_score, 0.25), 3)

    breakdown = {
        "audience_fit": round(audience_fit, 2),
        "historical_cluster_performance": round(historical_perf, 2),
        "novelty": round(novelty, 2),
        "expected_retention": round(expected_retention, 2),
        "production_ease": round(ease_of_production, 2),
        "external_prior_boost": round(bounded_ext_boost, 3),
        "is_valid_counterfactual": divergence_check["is_valid_counterfactual"],
    }
    if outlier_rubric is not None:
        breakdown["outlier_rubric_score"] = outlier_rubric["rubric_score"]

    reason_str = (
        f"Audience fit: {audience_fit:.2f}, Historical cluster: {historical_perf:.2f}, "
        f"Novelty: {novelty:.2f}, Ext boost: {bounded_ext_boost:.2f}"
    )
    if divergence_check["issues"]:
        reason_str += f" | BLOCKED: {'; '.join(divergence_check['issues'])}"

    return {
        "final_score": final_score,
        "is_valid_counterfactual": divergence_check["is_valid_counterfactual"],
        "formula_version": "topic_score_v1.2",
        "breakdown": breakdown,
        "reason": reason_str
    }
