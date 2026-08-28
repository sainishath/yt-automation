# -*- coding: utf-8 -*-
"""
collector.py
------------
Ingests YouTube video performance metrics across multiple evaluation windows.
Integrates YouTubeApiCollector for live metrics and MockDataGenerator for deterministic testing.
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from growth.db.models import GrowthRepository, PerformanceSnapshotModel
from growth.analytics.mock_data_generator import generate_mock_snapshots_for_video
from growth.analytics.youtube_api_collector import YouTubeApiCollector
from growth.analytics.normalizer import calculate_channel_baseline, normalize_video_metrics


class AnalyticsCollector:
    def __init__(self, repo: GrowthRepository, use_mock_engine: bool = True, token_path: Optional[Path] = None):
        self.repo = repo
        self.use_mock_engine = use_mock_engine
        self.api_collector = YouTubeApiCollector(repo, token_path=token_path, dry_run=use_mock_engine)

    def collect_snapshots_for_video(
        self,
        video_id: str,
        youtube_video_id: Optional[str] = None,
        duration: float = 45.0,
        retention_factor: float = 0.88
    ) -> List[int]:
        """
        Collects or simulates performance snapshots for a video and saves them to the repository.
        Returns list of inserted snapshot IDs.
        """
        if self.use_mock_engine or not youtube_video_id:
            snapshots = generate_mock_snapshots_for_video(video_id, duration=duration, retention_factor=retention_factor)
            inserted_ids = []
            for snap in snapshots:
                snap_id = self.repo.insert_snapshot(snap)
                inserted_ids.append(snap_id)
        else:
            # Real YouTube API ingestion across standard evaluation windows
            inserted_ids = []
            windows = ["1h", "6h", "24h", "48h", "7d", "28d"]
            for w in windows:
                snap = self.api_collector.fetch_and_record_snapshot(
                    video_id=video_id,
                    youtube_video_id=youtube_video_id,
                    window_name=w,
                    duration=duration
                )
                if snap.snapshot_id:
                    inserted_ids.append(snap.snapshot_id)

        logging.info(f"[Analytics] Ingested {len(inserted_ids)} snapshots for video '{video_id}'")
        return inserted_ids

    def get_video_normalized_summary(self, video_id: str, channel_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves mature performance snapshot (preferring 7d, falling back to 24h)
        and computes normalized scores against channel baseline.
        """
        snaps = self.repo.get_snapshots_for_video(video_id)
        # Select best evaluation snapshot: 7d window preferred, fallback to 24h
        eval_snap = next((s for s in snaps if s.get("window_name") == "7d"), None)
        if not eval_snap:
            eval_snap = next((s for s in snaps if s.get("window_name") == "24h"), None)
        if not eval_snap:
            return None

        # Fetch recent baseline snapshots for channel
        channel_videos = self.repo.list_videos_by_channel(channel_id)
        recent_snaps = []
        for v in channel_videos[:15]:
            v_snaps = self.repo.get_snapshots_for_video(v["video_id"])
            s = next((x for x in v_snaps if x.get("window_name") == eval_snap.get("window_name")), None)
            if not s:
                s = next((x for x in v_snaps if x.get("window_name") == "24h"), None)
            if s:
                recent_snaps.append(s)

        baseline = calculate_channel_baseline(recent_snaps)
        norm = normalize_video_metrics(eval_snap, baseline)
        return {
            "video_id": video_id,
            "window_name": eval_snap.get("window_name", "24h"),
            "raw_24h": eval_snap,
            "raw_snapshot": eval_snap,
            "baseline": baseline,
            "normalized": norm
        }
