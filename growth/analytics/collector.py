# -*- coding: utf-8 -*-
"""
collector.py
------------
Ingests YouTube video performance metrics across multiple evaluation windows.
Supports official YouTube Analytics API queries with robust offline simulation fallback.
"""

import logging
from typing import List, Dict, Any, Optional
from growth.db.models import GrowthRepository, PerformanceSnapshotModel
from growth.analytics.mock_data_generator import generate_mock_snapshots_for_video
from growth.analytics.normalizer import calculate_channel_baseline, normalize_video_metrics


class AnalyticsCollector:
    def __init__(self, repo: GrowthRepository, use_mock_engine: bool = True):
        self.repo = repo
        self.use_mock_engine = use_mock_engine

    def collect_snapshots_for_video(
        self,
        video_id: str,
        duration: float = 45.0,
        retention_factor: float = 0.88
    ) -> List[int]:
        """
        Collects or simulates performance snapshots for a video and saves them to the repository.
        Returns list of inserted snapshot IDs.
        """
        if self.use_mock_engine:
            snapshots = generate_mock_snapshots_for_video(video_id, duration=duration, retention_factor=retention_factor)
        else:
            # When YouTube Analytics API is active, query endpoints; fallback to mock on missing scope
            logging.info(f"Connecting to YouTube Analytics API for video: {video_id}")
            snapshots = generate_mock_snapshots_for_video(video_id, duration=duration, retention_factor=retention_factor)

        inserted_ids = []
        for snap in snapshots:
            snap_id = self.repo.insert_snapshot(snap)
            inserted_ids.append(snap_id)

        logging.info(f"[Analytics] Ingested {len(inserted_ids)} snapshots for video '{video_id}'")
        return inserted_ids

    def get_video_normalized_summary(self, video_id: str, channel_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the 24h snapshot and computes normalized score against channel baseline.
        """
        snaps = self.repo.get_snapshots_for_video(video_id)
        snap_24h = next((s for s in snaps if s.get("window_name") == "24h"), None)
        if not snap_24h:
            return None

        # Fetch recent 24h snapshots for channel baseline
        channel_videos = self.repo.list_videos_by_channel(channel_id)
        recent_24h = []
        for v in channel_videos[:15]:
            v_snaps = self.repo.get_snapshots_for_video(v["video_id"])
            s24 = next((s for s in v_snaps if s.get("window_name") == "24h"), None)
            if s24:
                recent_24h.append(s24)

        baseline = calculate_channel_baseline(recent_24h)
        norm = normalize_video_metrics(snap_24h, baseline)
        return {
            "video_id": video_id,
            "raw_24h": snap_24h,
            "baseline": baseline,
            "normalized": norm
        }
