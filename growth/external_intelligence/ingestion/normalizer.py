# -*- coding: utf-8 -*-
"""
normalizer.py
-------------
Computes robust relative performance metrics (views / channel median) and MAD outlier protection
across validated records within an external research dataset.
Assigns computed_classification and flags classification disagreements without discarding researcher claims.
"""

import math
from typing import List, Dict, Any, Optional
from collections import defaultdict
from growth.external_intelligence.ingestion.ingestion_schemas import (
    ValidatedExternalVideoRecord,
    PerformanceClass
)


def _compute_median(values: List[float]) -> float:
    """Computes sample median."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 1:
        return float(sorted_vals[mid])
    else:
        return float((sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0)


def _compute_mad(values: List[float], median: float) -> float:
    """Computes Median Absolute Deviation (MAD)."""
    if not values:
        return 0.0
    deviations = [abs(x - median) for x in values]
    return _compute_median(deviations)


def normalize_dataset_records(
    records: List[ValidatedExternalVideoRecord]
) -> List[ValidatedExternalVideoRecord]:
    """
    Groups validated records by channel to compute channel-relative medians and multipliers.
    Preserves researcher claims while calculating computed_classification and computed_relative_views.
    """
    valid_records = [r for r in records if r.is_valid]
    if not valid_records:
        return records

    # 1. Group views by channel
    channel_views: Dict[str, List[float]] = defaultdict(list)
    for r in valid_records:
        if r.views > 0:
            channel_views[r.channel_name].append(float(r.views))

    # 2. Compute channel medians and MADs
    channel_stats: Dict[str, Dict[str, float]] = {}
    for ch_name, views_list in channel_views.items():
        if len(views_list) >= 2:
            med = _compute_median(views_list)
            mad = _compute_mad(views_list, med)
            channel_stats[ch_name] = {"median": med, "mad": mad, "count": len(views_list)}
        else:
            # Insufficient samples for robust channel-level median
            med = views_list[0] if views_list else 100000.0
            channel_stats[ch_name] = {"median": med, "mad": 0.0, "count": len(views_list)}

    # Overall dataset median for cross-channel relative context if channel count is 1
    all_views = [float(r.views) for r in valid_records if r.views > 0]
    global_median = _compute_median(all_views) if all_views else 100000.0

    # 3. Apply normalization and computed classification
    for r in records:
        if not r.is_valid:
            continue

        stats = channel_stats.get(r.channel_name)
        if stats and stats["count"] >= 2 and stats["median"] > 0:
            rel_views = round(float(r.views) / stats["median"], 2)
        elif global_median > 0:
            rel_views = round(float(r.views) / global_median, 2)
        else:
            rel_views = 1.0

        r.computed_relative_views = rel_views

        # Determine computed classification thresholds:
        # HIGH: >= 1.5x median
        # LOW: <= 0.65x median
        # NORMAL: between 0.65x and 1.5x
        if rel_views >= 1.5:
            r.computed_classification = PerformanceClass.HIGH_PERFORMER
        elif rel_views <= 0.65:
            r.computed_classification = PerformanceClass.LOW_PERFORMER
        else:
            r.computed_classification = PerformanceClass.NORMAL_PERFORMER

    return records
