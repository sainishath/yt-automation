# -*- coding: utf-8 -*-
"""
topic_scorer.py
---------------
Multi-factor explainable scoring model for topic candidates (topic_score_v1).
Answers: "Why did we choose this topic?"
"""

from typing import Dict, Any


def score_topic(
    topic_text: str,
    channel_id: str,
    category: str,
    historical_cluster_avg: float = 0.80,
    novelty: float = 0.75,
    fact_check_difficulty: float = 0.30
) -> Dict[str, Any]:
    """
    Computes an explainable topic score (v1.0).
    Factors:
      - audience_fit (0.30 weight)
      - historical_performance (0.25 weight)
      - novelty (0.20 weight)
      - expected_retention (0.15 weight)
      - fact_check_penalty (0.10 weight)
    """
    # Baseline audience fit heuristic based on keywords
    audience_fit = 0.85
    expected_retention = 0.82

    if channel_id == "channel_a":
        # History / Alternate History checks
        keywords = ["rome", "alexandria", "empire", "war", "what if", "history", "invented", "conquered"]
        match_count = sum(1 for kw in keywords if kw in topic_text.lower())
        audience_fit = min(0.70 + (match_count * 0.08), 0.98)
    else:
        # Debate / Psychology checks
        keywords = ["brain", "ai", "why", "psychology", "debate", "argue", "mind", "sleep", "deja vu"]
        match_count = sum(1 for kw in keywords if kw in topic_text.lower())
        audience_fit = min(0.70 + (match_count * 0.08), 0.98)

    historical_perf = max(min(historical_cluster_avg, 1.0), 0.1)
    ease_of_production = max(1.0 - fact_check_difficulty, 0.1)

    # Weighted composite score
    final_score = (
        (0.30 * audience_fit) +
        (0.25 * historical_perf) +
        (0.20 * novelty) +
        (0.15 * expected_retention) +
        (0.10 * ease_of_production)
    )
    final_score = round(final_score, 3)

    return {
        "final_score": final_score,
        "formula_version": "topic_score_v1",
        "breakdown": {
            "audience_fit": round(audience_fit, 2),
            "historical_cluster_performance": round(historical_perf, 2),
            "novelty": round(novelty, 2),
            "expected_retention": round(expected_retention, 2),
            "production_ease": round(ease_of_production, 2)
        },
        "reason": f"Audience fit: {audience_fit:.2f}, Historical cluster: {historical_perf:.2f}, Novelty: {novelty:.2f}"
    }
