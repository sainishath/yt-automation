# -*- coding: utf-8 -*-
"""
fetch_analytics.py
------------------
Automated periodic YouTube Analytics and Data API ingestion script for growth.db.
Checks published videos across Channel A and Channel B, determines due snapshot windows
(1h, 6h, 24h, 48h, 7d, 28d) based on publish age, and idempotently records performance metrics.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from growth.db.database import DEFAULT_DB_PATH
from growth.db.models import GrowthRepository, PerformanceSnapshotModel
from growth.analytics.youtube_api_collector import YouTubeApiCollector

# Standard snapshot windows and their elapsed age triggers
SNAPSHOT_WINDOWS = [
    ("1h", timedelta(hours=1)),
    ("6h", timedelta(hours=6)),
    ("24h", timedelta(hours=24)),
    ("48h", timedelta(hours=48)),
    ("7d", timedelta(days=7)),
    ("28d", timedelta(days=28)),
]

def fetch_due_snapshots(
    repo: Optional[GrowthRepository] = None,
    dry_run: bool = False,
    token_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Scans all published videos in growth.db, calculates their elapsed age (t - t_publish),
    and queries the YouTube Data API v3 and Analytics API v2 for missing window snapshots.
    """
    if repo is None:
        repo = GrowthRepository(DEFAULT_DB_PATH)

    collector = YouTubeApiCollector(repo=repo, token_path=token_path, dry_run=dry_run)
    now = datetime.utcnow()

    all_videos = []
    for ch in ["channel_a", "channel_b"]:
        all_videos.extend(repo.list_videos_by_channel(ch))

    collected = []
    skipped = []
    errors = []

    for vid in all_videos:
        vid_id = vid.get("video_id")
        yt_id = vid.get("youtube_video_id")
        ch_id = vid.get("channel_id")
        duration = float(vid.get("duration", 45.0))
        status = vid.get("upload_status", "")

        # Only process videos that have been uploaded or in simulation mode
        if not dry_run and status not in ["UPLOADED", "UPLOADED_PUBLIC", "PUBLISHED"]:
            continue

        # If dry run and no youtube_video_id, use a mock id
        if not yt_id:
            if dry_run:
                yt_id = f"sim_{vid_id}"
            else:
                continue

        # Determine video age
        ts_str = vid.get("publish_timestamp") or vid.get("generation_timestamp") or now.isoformat()
        try:
            if "T" in str(ts_str):
                pub_time = datetime.fromisoformat(str(ts_str).replace("Z", ""))
            else:
                pub_time = datetime.strptime(str(ts_str), "%Y-%m-%d %H:%M:%S")
        except Exception:
            pub_time = now - timedelta(hours=25)

        elapsed = now - pub_time

        # Check existing snapshots for this video
        existing_snaps = repo.get_snapshots_for_video(vid_id)
        existing_windows = {s["window_name"] for s in existing_snaps}

        for win_name, win_delta in SNAPSHOT_WINDOWS:
            # Check if video has reached the required age for this window
            if elapsed >= win_delta:
                if win_name not in existing_windows:
                    try:
                        snap = collector.fetch_and_record_snapshot(
                            video_id=vid_id,
                            youtube_video_id=yt_id,
                            window_name=win_name,
                            duration=duration,
                            channel_id=ch_id
                        )
                        collected.append({
                            "video_id": vid_id,
                            "window_name": win_name,
                            "views": snap.views,
                            "apv": snap.avg_percentage_viewed,
                            "data_source": snap.data_source
                        })
                        logging.info(
                            f"[fetch_analytics] Ingested {win_name} snapshot for {vid_id} "
                            f"(APV: {snap.avg_percentage_viewed:.1f}%, Source: {snap.data_source})"
                        )
                    except Exception as e:
                        logging.error(f"[fetch_analytics] Error pulling {win_name} for {vid_id}: {e}")
                        errors.append({"video_id": vid_id, "window": win_name, "error": str(e)})
                else:
                    skipped.append(f"{vid_id}:{win_name}")

    return {
        "status": "success",
        "collected_count": len(collected),
        "skipped_count": len(skipped),
        "errors_count": len(errors),
        "collected": collected,
        "errors": errors,
        "timestamp": now.isoformat()
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="YouTube Analytics Periodic Ingestion Runner")
    parser.add_argument("--dry-run", action="store_true", help="Run with simulation data without calling live APIs")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    res = fetch_due_snapshots(dry_run=args.dry_run)
    print("\n=======================================================")
    print("  ANALYTICS INGESTION COMPLETE")
    print(f"  Collected : {res['collected_count']} snapshots")
    print(f"  Skipped   : {res['skipped_count']} already present")
    print(f"  Errors    : {res['errors_count']}")
    print("=======================================================\n")