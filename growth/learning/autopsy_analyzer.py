# -*- coding: utf-8 -*-
"""
autopsy_analyzer.py
-------------------
Generates structured, evidence-based postmortems (autopsies) for published videos.
Labels hypotheses clearly as hypotheses.
"""

from typing import Dict, Any, List


def generate_video_autopsy(
    video_id: str,
    features: Dict[str, Any],
    normalized_summary: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Analyzes a video's features against normalized performance to generate an autopsy.
    """
    raw_24h = normalized_summary.get("raw_24h", {})
    norm = normalized_summary.get("normalized", {})
    score = norm.get("composite_performance_score", 1.0)
    ret_mult = norm.get("retention_multiplier", 1.0)
    view_mult = norm.get("view_multiplier", 1.0)

    strong_signals = []
    weak_signals = []

    if ret_mult >= 1.10:
        strong_signals.append(f"High Audience Retention (APV: {raw_24h.get('avg_percentage_viewed', 0)}%, {ret_mult}x baseline)")
    elif ret_mult <= 0.85:
        weak_signals.append(f"Early Drop-off Detected (APV: {raw_24h.get('avg_percentage_viewed', 0)}%, {ret_mult}x baseline)")

    if view_mult >= 1.20:
        strong_signals.append(f"Strong Initial Velocity ({raw_24h.get('views_per_hour', 0)} views/hr)")
    elif view_mult <= 0.80:
        weak_signals.append(f"Sluggish View Velocity ({raw_24h.get('views_per_hour', 0)} views/hr)")

    # Formulate evidence-based hypothesis
    if score >= 1.15:
        hypothesis = (
            f"Topic '{features.get('topic_category', 'General')}' combined with "
            f"'{features.get('hook_type', 'Hook')}' strongly resonates with audience curiosity."
        )
        recommendation = "Maintain this topic cluster and test minor narrative pacing variations."
    elif score <= 0.85:
        hypothesis = (
            f"Premise in '{features.get('topic_category', 'General')}' failed to sustain mid-video momentum "
            f"(Scene count: {features.get('scene_count', 0)})."
        )
        recommendation = "Shorten introduction by 1.5s and increase visual change rate in first 10s."
    else:
        hypothesis = "Performance is in line with historical channel median baseline."
        recommendation = "Continue active experiment cohort to establish statistical divergence."

    return {
        "video_id": video_id,
        "performance_verdict": "ABOVE_MEDIAN" if score >= 1.15 else ("BELOW_MEDIAN" if score <= 0.85 else "ON_MEDIAN"),
        "composite_score": score,
        "strongest_signals": strong_signals or ["Stable baseline engagement"],
        "weakest_signals": weak_signals or ["No critical failure detected"],
        "hypothesis": hypothesis,
        "recommendation": recommendation
    }
