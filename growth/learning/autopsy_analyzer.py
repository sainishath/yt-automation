# -*- coding: utf-8 -*-
"""
autopsy_analyzer.py
-------------------
Generates structured, evidence-based postmortems (autopsies) for published videos.
Labels hypotheses clearly as hypotheses.
"""

from typing import Dict, Any, List, Optional


def generate_video_autopsy(
    video_id: str,
    features: Dict[str, Any],
    normalized_summary: Dict[str, Any],
    experiment_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Analyzes a video's features against normalized performance to generate a structured autopsy.
    Maintains complete causal attribution:
    VIDEO -> STRATEGY -> EXPERIMENT -> VARIABLE -> ARM -> OUTCOME -> LEARNED_RULE
    """
    raw_24h = normalized_summary.get("raw_24h", {})
    norm = normalized_summary.get("normalized", {})
    score = norm.get("composite_performance_score", 1.0)
    ret_mult = norm.get("retention_multiplier", 1.0)
    view_mult = norm.get("view_multiplier", 1.0)

    strong_signals = []
    weak_signals = []

    apv = raw_24h.get("avg_percentage_viewed", 0.0)
    vph = raw_24h.get("views_per_hour", 0.0)

    if ret_mult >= 1.10:
        strong_signals.append(f"High Audience Retention (APV: {apv}%, {ret_mult}x baseline)")
    elif ret_mult <= 0.85:
        weak_signals.append(f"Early Drop-off Detected (APV: {apv}%, {ret_mult}x baseline)")

    if view_mult >= 1.20:
        strong_signals.append(f"Strong Initial Velocity ({vph} views/hr, {view_mult}x baseline)")
    elif view_mult <= 0.80:
        weak_signals.append(f"Sluggish View Velocity ({vph} views/hr, {view_mult}x baseline)")

    # Structured Causal Attribution
    exp = experiment_data or {}
    exp_id = exp.get("experiment_id", "BASELINE_OBSERVATION")
    tested_var = exp.get("variable_tested", "GENERAL_CONTENT_STRUCTURE")
    arm_id = exp.get("arm_id", "control")
    hook_type = features.get("hook_type", "Standard Hook")
    topic_cat = features.get("topic_category", "General")

    if score >= 1.15:
        verdict = "ABOVE_MEDIAN"
        hypothesis = f"Tested {tested_var} in arm '{arm_id}' strongly resonates with audience curiosity."
        learned_rule = f"Pattern '{hook_type}' in category '{topic_cat}' outperforms baseline (APV multiplier: {ret_mult}x)."
        recommendation = f"Promote arm '{arm_id}' for variable '{tested_var}' in next strategy iteration."
    elif score <= 0.85:
        verdict = "BELOW_MEDIAN"
        hypothesis = f"Tested {tested_var} in arm '{arm_id}' experienced mid-video retention degradation."
        learned_rule = f"Pattern '{hook_type}' in category '{topic_cat}' underperformed baseline (APV multiplier: {ret_mult}x)."
        recommendation = f"Adjust pacing or refine opening hook for variable '{tested_var}'."
    else:
        verdict = "ON_MEDIAN"
        hypothesis = f"Tested {tested_var} in arm '{arm_id}' performed in line with historical channel baseline."
        learned_rule = f"No significant divergence detected for arm '{arm_id}' (Score: {score})."
        recommendation = "Continue cohort sampling until mature N >= 4 samples accumulate."

    return {
        "video_id": video_id,
        "performance_verdict": verdict,
        "composite_score": score,
        "causal_attribution": {
            "experiment_id": exp_id,
            "tested_variable": tested_var,
            "arm_id": arm_id,
            "hook_type": hook_type,
            "topic_category": topic_cat
        },
        "strongest_signals": strong_signals or ["Stable baseline engagement"],
        "weakest_signals": weak_signals or ["No critical failure detected"],
        "hypothesis": hypothesis,
        "learned_rule": learned_rule,
        "recommendation": recommendation
    }
