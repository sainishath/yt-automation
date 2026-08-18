# -*- coding: utf-8 -*-
"""
normalizer.py
-------------
Normalizes performance metrics against channel baselines and recent medians.
Avoids raw-views distortion and protects against single viral outliers.
"""

import statistics
from typing import List, Dict, Any, Optional


def calculate_channel_baseline(snapshots_24h: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calculates median baseline performance from 24h snapshots across recent videos.
    """
    if not snapshots_24h:
        return {
            "median_views_24h": 500.0,
            "median_apv": 80.0,
            "median_engagement_rate": 0.08,
            "median_sub_conversion": 0.005,
            "sample_size": 0
        }

    views = [s.get("views", 0) for s in snapshots_24h]
    apvs = [s.get("avg_percentage_viewed", 0.0) for s in snapshots_24h]
    engs = [s.get("engagement_rate", 0.0) for s in snapshots_24h]
    subs = [s.get("subscriber_conversion_rate", 0.0) for s in snapshots_24h]

    return {
        "median_views_24h": float(statistics.median(views)),
        "median_apv": float(statistics.median(apvs)),
        "median_engagement_rate": float(statistics.median(engs)),
        "median_sub_conversion": float(statistics.median(subs)),
        "sample_size": len(snapshots_24h)
    }


def normalize_video_metrics(
    raw_snapshot: Dict[str, Any],
    baseline: Dict[str, float]
) -> Dict[str, float]:
    """
    Computes normalized relative performance multipliers against channel baseline.
    """
    median_views = max(baseline.get("median_views_24h", 500.0), 1.0)
    median_apv = max(baseline.get("median_apv", 80.0), 1.0)
    median_eng = max(baseline.get("median_engagement_rate", 0.08), 0.001)

    views = raw_snapshot.get("views", 0)
    apv = raw_snapshot.get("avg_percentage_viewed", 0.0)
    eng = raw_snapshot.get("engagement_rate", 0.0)

    view_multiplier = round(views / median_views, 2)
    retention_multiplier = round(apv / median_apv, 2)
    engagement_multiplier = round(eng / median_eng, 2)

    # Composite Normalized Performance Score (v1.0)
    # 40% Retention + 35% Views + 25% Engagement
    composite_score = round(
        (0.40 * retention_multiplier) +
        (0.35 * min(view_multiplier, 3.0)) + # Cap outlier at 3.0x to avoid skew
        (0.25 * engagement_multiplier),
        2
    )

    return {
        "view_multiplier": view_multiplier,
        "retention_multiplier": retention_multiplier,
        "engagement_multiplier": engagement_multiplier,
        "composite_performance_score": composite_score
    }
