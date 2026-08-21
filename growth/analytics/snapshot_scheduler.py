# -*- coding: utf-8 -*-
"""
snapshot_scheduler.py
---------------------
Orchestrates periodic collection of analytics snapshots across:
1h, 6h, 24h, 48h, 7d, 28d.
Checks eligibility, prevents duplicate snapshots, and records collection status.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

from growth.db.models import GrowthRepository
from growth.analytics.youtube_api_collector import YouTubeApiCollector

SNAPSHOT_WINDOWS = [
    ("1h", timedelta(hours=1)),
    ("6h", timedelta(hours=6)),
    ("24h", timedelta(hours=24)),
    ("48h", timedelta(hours=48)),
    ("7d", timedelta(days=7)),
    ("28d", timedelta(days=28)),
]


class SnapshotScheduler:
    def __init__(self, repo: GrowthRepository, token_path: Optional[Path] = None, dry_run: bool = False):
        self.repo = repo
        self.collector = YouTubeApiCollector(repo, token_path=token_path, dry_run=dry_run)

    def run_pending_snapshot_checks(self) -> Dict[str, Any]:
        """
        Scans all published videos across channels, determines which snapshot windows are due,
        and collects missing snapshots idempotently.
        """
        all_videos = []
        for ch in ["channel_a", "channel_b"]:
            all_videos.extend(self.repo.list_videos_by_channel(ch))

        collected_count = 0
        skipped_count = 0
        errors = []

        now = datetime.utcnow()

        for vid in all_videos:
            vid_id = vid["video_id"]
            yt_id = vid.get("youtube_video_id") or "simulated_yt_id"
            duration = float(vid.get("duration", 45.0))

            existing_snaps = self.repo.get_snapshots_for_video(vid_id)
            existing_windows = {s["window_name"] for s in existing_snaps}

            # Parse creation/publish timestamp
            ts_str = vid.get("publish_timestamp") or vid.get("generation_timestamp") or now.isoformat()
            try:
                if "T" in str(ts_str):
                    pub_time = datetime.fromisoformat(str(ts_str).replace("Z", ""))
                else:
                    pub_time = datetime.strptime(str(ts_str), "%Y-%m-%d %H:%M:%S")
            except Exception:
                pub_time = now - timedelta(hours=25)

            elapsed = now - pub_time

            for win_name, win_delta in SNAPSHOT_WINDOWS:
                if elapsed >= win_delta:
                    if win_name not in existing_windows:
                        try:
                            self.collector.fetch_and_record_snapshot(
                                video_id=vid_id,
                                youtube_video_id=yt_id,
                                window_name=win_name,
                                duration=duration,
                                channel_id=vid.get("channel_id")
                            )
                            collected_count += 1
                        except Exception as e:
                            logging.error(f"[Scheduler] Failed collecting {win_name} snapshot for {vid_id}: {e}")
                            errors.append(f"{vid_id}:{win_name} -> {e}")
                    else:
                        skipped_count += 1

        return {
            "status": "success",
            "collected_count": collected_count,
            "already_present_count": skipped_count,
            "errors": errors
        }
