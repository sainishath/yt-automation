# -*- coding: utf-8 -*-
"""
outlier_analyzer.py
-------------------
Analyzes extreme performance outliers (>3x median) and isolates repeatable signals
from external trend spikes, preventing premature over-mutation of core strategy.
"""

from typing import Dict, Any, List


def analyze_performance_outlier(
    video_snapshot: Dict[str, Any],
    channel_baseline: Dict[str, Any],
    outlier_threshold_multiplier: float = 3.0
) -> Dict[str, Any]:
    """
    Evaluates whether a video is an extreme outlier and analyzes whether the performance
    is a repeatable format signal or an isolated distribution spike.
    """
    median_views = float(channel_baseline.get("median_views_24h", 1000.0))
    median_apv = float(channel_baseline.get("median_avg_percentage_viewed", 85.0))

    views = float(video_snapshot.get("views", 0))
    apv = float(video_snapshot.get("avg_percentage_viewed", 0.0))

    view_multiplier = round(views / max(median_views, 1.0), 2)
    is_outlier = view_multiplier >= outlier_threshold_multiplier

    if not is_outlier:
        return {
            "is_outlier": False,
            "view_multiplier": view_multiplier,
            "signal_type": "NORMAL_DISTRIBUTION",
            "learning_action": "STANDARD_INCORPORATION",
            "explanation": f"Performance ({view_multiplier}x median) within normal baseline distribution."
        }

    # If it is an outlier, inspect retention
    has_high_retention = apv >= median_apv

    if has_high_retention:
        signal_type = "REPEATABLE_FORMAT_AND_TOPIC_SIGNAL"
        learning_action = "EXPAND_TOPIC_CLUSTER_AND_PRESERVE_HOOK"
        explanation = (
            f"Video achieved {view_multiplier}x views WITH strong retention ({apv}% vs {median_apv}% median). "
            "Indicates genuine product-market fit. Recommended: Produce adjacent topics in this cluster."
        )
    else:
        signal_type = "ISOLATED_ALGORITHMIC_OR_CLICK_SPIKE"
        learning_action = "CAP_MULTIPLIER_AND_EXPLORE_CAUTIOUSLY"
        explanation = (
            f"Video achieved {view_multiplier}x views but below-average retention ({apv}% vs {median_apv}% median). "
            "Indicates high initial curiosity/clickthrough but lower satisfaction. Do NOT blindly adopt as sole strategy."
        )

    return {
        "is_outlier": True,
        "view_multiplier": view_multiplier,
        "capped_view_multiplier": min(view_multiplier, 3.0),
        "signal_type": signal_type,
        "learning_action": learning_action,
        "explanation": explanation
    }
