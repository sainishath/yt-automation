# -*- coding: utf-8 -*-
"""
mock_data_generator.py
----------------------
Generates realistic, statistically consistent mock performance snapshots
for development, testing, and dry-run simulation across multiple time windows.
"""

import math
import random
from typing import Dict, Any, List
from growth.db.models import PerformanceSnapshotModel


SNAPSHOT_WINDOWS = ["1h", "6h", "24h", "48h", "7d", "28d"]
WINDOW_HOURS = {
    "1h": 1.0,
    "6h": 6.0,
    "24h": 24.0,
    "48h": 48.0,
    "7d": 168.0,
    "28d": 672.0
}


def generate_mock_snapshots_for_video(
    video_id: str,
    duration: float = 45.0,
    base_velocity: float = 85.0,
    retention_factor: float = 0.88
) -> List[PerformanceSnapshotModel]:
    """
    Generates realistic performance snapshots evolving over time windows.
    """
    snapshots = []
    total_views = 0

    for window in SNAPSHOT_WINDOWS:
        hours = WINDOW_HOURS[window]
        # Diminishing growth curve
        growth_multiplier = math.log(hours + 1.0, 2.0)
        current_views = int(base_velocity * growth_multiplier * (1.0 + (random.random() * 0.1 - 0.05)))
        current_views = max(current_views, total_views + 5)
        total_views = current_views

        likes = int(total_views * 0.09)
        comments = int(total_views * 0.015)
        shares = int(total_views * 0.008)
        subs = int(total_views * 0.006)

        avg_pct_viewed = round(min(retention_factor * 100.0, 120.0), 2)
        avg_view_duration = round((avg_pct_viewed / 100.0) * duration, 2)
        watch_time_mins = round((total_views * avg_view_duration) / 60.0, 2)
        vph = round(total_views / max(hours, 1.0), 2)
        eng_rate = round((likes + comments + shares) / max(total_views, 1), 4)
        sub_conv = round(subs / max(total_views, 1), 5)
        rel_score = round(1.0 + (retention_factor - 0.80) * 2.0, 2)

        snap = PerformanceSnapshotModel(
            video_id=video_id,
            window_name=window,
            views=total_views,
            likes=likes,
            comments=comments,
            shares=shares,
            subscribers_gained=subs,
            watch_time_minutes=watch_time_mins,
            avg_view_duration_seconds=avg_view_duration,
            avg_percentage_viewed=avg_pct_viewed,
            views_per_hour=vph,
            engagement_rate=eng_rate,
            subscriber_conversion_rate=sub_conv,
            relative_performance_score=rel_score,
            data_source="MOCK_ENGINE",
            data_freshness="SYNTHETIC_SIMULATION"
        )
        snapshots.append(snap)

    return snapshots
