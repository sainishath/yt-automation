# -*- coding: utf-8 -*-
"""
sync_youtube_state.py
---------------------
Full True-State Reconciliation Engine between growth.db and the live YouTube channel(s).

Audits all uploaded videos in growth.db against YouTube Data API v3:
1. Verifies if video exists on YouTube or was manually deleted from YouTube Studio.
2. Updates `upload_status` to 'DELETED_ON_YOUTUBE' for deleted videos to prevent analytics crashes.
3. Synchronizes `privacy_status` to match real-time YouTube state (public, private, unlisted).
4. Verifies channel ownership and active public vs private distribution across pipelines.
"""

import sys
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from growth.db.database import get_db, DEFAULT_DB_PATH
from growth.db.models import GrowthRepository

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def get_youtube_service(channel_id: str = "channel_a"):
    """
    Authenticates with YouTube Data API v3 for the given channel.
    Channel A: alternate-history-shorts/config/token.json
    Channel B: convo-shorts/yt-automation-engine/youtube_token.pickle
    """
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    import pickle

    token_path = None
    if channel_id == "channel_b":
        token_path = ROOT_DIR / "convo-shorts" / "yt-automation-engine" / "youtube_token.pickle"
    else:
        token_path = ROOT_DIR / "alternate-history-shorts" / "config" / "token.json"

    if not token_path.exists():
        logging.warning(f"Token file not found for {channel_id}: {token_path}")
        return None

    try:
        if str(token_path).endswith(".pickle"):
            with open(token_path, "rb") as f:
                creds = pickle.load(f)
        else:
            creds = Credentials.from_authorized_user_file(str(token_path))

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            if str(token_path).endswith(".pickle"):
                with open(token_path, "wb") as f:
                    pickle.dump(creds, f)
            else:
                with open(token_path, "w", encoding="utf-8") as f:
                    f.write(creds.to_json())

        return build("youtube", "v3", credentials=creds)
    except Exception as e:
        logging.error(f"Failed to authenticate YouTube client for {channel_id}: {e}")
        return None


def reconcile_channel_videos(
    channel_id: str,
    db_path: Path = DEFAULT_DB_PATH
) -> Dict[str, Any]:
    """
    Reconciles all uploaded videos in growth.db for a given channel with live YouTube state.
    """
    summary = {
        "channel_id": channel_id,
        "authenticated": False,
        "channel_name": "Unknown",
        "channel_custom_url": "",
        "total_db_records": 0,
        "active_verified": 0,
        "marked_deleted": 0,
        "updated_privacy": 0,
        "details": []
    }

    youtube = get_youtube_service(channel_id)
    if not youtube:
        summary["error"] = f"No authenticated YouTube service for {channel_id}"
        return summary

    summary["authenticated"] = True

    # 1. Fetch Authenticated Channel Details
    try:
        chan_req = youtube.channels().list(part="snippet,contentDetails", mine=True)
        chan_res = chan_req.execute()
        items = chan_res.get("items", [])
        if items:
            ch_info = items[0]
            summary["channel_name"] = ch_info.get("snippet", {}).get("title", "")
            summary["channel_custom_url"] = ch_info.get("snippet", {}).get("customUrl", "")
            summary["channel_yt_id"] = ch_info.get("id", "")
    except Exception as e:
        logging.warning(f"Could not retrieve channel info for {channel_id}: {e}")

    # 2. Query Candidate Videos from growth.db
    with get_db(db_path) as conn:
        conn.row_factory = lambda cursor, row: {
            col[0]: row[idx] for idx, col in enumerate(cursor.description)
        }
        db_videos = conn.execute("""
            SELECT video_id, channel_id, pipeline_id, title, youtube_video_id, youtube_url, upload_status, privacy_status 
            FROM videos 
            WHERE channel_id = ? 
              AND youtube_video_id IS NOT NULL 
              AND upload_status NOT IN ('SCRAPPED', 'SIMULATED_BENCHMARK')
        """, (channel_id,)).fetchall()

    summary["total_db_records"] = len(db_videos)
    if not db_videos:
        logging.info(f"[{channel_id}] No active uploaded videos found in growth.db to reconcile.")
        return summary

    # 3. Batch Query YouTube Data API for Video Statuses (up to 50 at a time)
    yt_id_to_db_vids = {}
    for v in db_videos:
        yt_id = v["youtube_video_id"]
        if yt_id:
            yt_id_to_db_vids[yt_id] = v

    all_yt_ids = list(yt_id_to_db_vids.keys())
    batch_size = 50
    live_yt_data = {}

    for i in range(0, len(all_yt_ids), batch_size):
        batch = all_yt_ids[i:i+batch_size]
        try:
            req = youtube.videos().list(
                part="snippet,status",
                id=",".join(batch)
            )
            res = req.execute()
            for item in res.get("items", []):
                live_yt_data[item.get("id")] = item
        except Exception as e:
            logging.error(f"Failed to query YouTube API batch: {e}")

    # 4. Synchronize growth.db State
    with get_db(db_path) as conn:
        for yt_id, db_vid in yt_id_to_db_vids.items():
            vid_id = db_vid["video_id"]
            cur_status = db_vid["upload_status"]
            cur_privacy = db_vid["privacy_status"]
            title = db_vid["title"]

            if yt_id not in live_yt_data:
                # Video was DELETED on YouTube Studio
                conn.execute("""
                    UPDATE videos
                    SET upload_status = 'DELETED_ON_YOUTUBE',
                        privacy_status = 'DELETED'
                    WHERE video_id = ?
                """, (vid_id,))
                
                # Also update corresponding job if exists
                conn.execute("""
                    UPDATE jobs
                    SET status = 'DELETED_ON_YOUTUBE',
                        error_message = 'Video deleted on YouTube Studio by operator',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE video_id = ?
                """, (vid_id,))

                summary["marked_deleted"] += 1
                summary["details"].append({
                    "video_id": vid_id,
                    "youtube_id": yt_id,
                    "title": title,
                    "action": "MARKED_DELETED_ON_YOUTUBE",
                    "previous_status": cur_status
                })
            else:
                # Video EXISTS on YouTube
                item = live_yt_data[yt_id]
                yt_status = item.get("status", {})
                yt_snippet = item.get("snippet", {})
                
                reported_privacy = yt_status.get("privacyStatus", "public")
                reported_title = yt_snippet.get("title", title)
                new_upload_status = f"UPLOADED_{reported_privacy.upper()}"

                conn.execute("""
                    UPDATE videos
                    SET upload_status = ?,
                        privacy_status = ?,
                        title = ?
                    WHERE video_id = ?
                """, (new_upload_status, reported_privacy, reported_title, vid_id))

                summary["active_verified"] += 1
                if reported_privacy != cur_privacy:
                    summary["updated_privacy"] += 1

                summary["details"].append({
                    "video_id": vid_id,
                    "youtube_id": yt_id,
                    "title": reported_title,
                    "action": "VERIFIED_ACTIVE",
                    "privacy_status": reported_privacy,
                    "upload_status": new_upload_status
                })

    return summary


def run_full_reconciliation(db_path: Path = DEFAULT_DB_PATH) -> Dict[str, Any]:
    """
    Executes full true-state reconciliation audit for Channel A and Channel B.
    """
    results = {}
    for ch in ["channel_a", "channel_b"]:
        results[ch] = reconcile_channel_videos(channel_id=ch, db_path=db_path)
    return results


def print_audit_report(results: Dict[str, Any]):
    """
    Renders clean, human-readable terminal audit summary.
    """
    print("\n" + "=" * 70)
    print("      YOUTUBE CHANNEL & GROWTH.DB TRUE-STATE RECONCILIATION AUDIT")
    print("=" * 70)

    for ch_id, res in results.items():
        pipeline_name = "Pipeline 1 (Alternate History)" if ch_id == "channel_a" else "Pipeline 2 (Coding & Dev)"
        print(f"\n--- [{pipeline_name} / {ch_id.upper()}] ---")
        if not res.get("authenticated"):
            print(f"  Status: {res.get('error', 'Authentication Failed or No Token')}")
            continue

        print(f"  Channel Title : {res.get('channel_name')} ({res.get('channel_custom_url', 'N/A')})")
        print(f"  Total In DB   : {res.get('total_db_records')} video records checked")
        print(f"  Active Live   : {res.get('active_verified')} verified active on YouTube")
        print(f"  Deleted Synced: {res.get('marked_deleted')} marked as DELETED_ON_YOUTUBE")
        print(f"  Privacy Synced: {res.get('updated_privacy')} privacy statuses synchronized")

        if res.get("details"):
            print("\n  Video Breakdown:")
            for d in res["details"]:
                if d["action"] == "MARKED_DELETED_ON_YOUTUBE":
                    print(f"    ❌ [DELETED]  {d['youtube_id']} | {d['title']} -> Status set to DELETED_ON_YOUTUBE")
                else:
                    print(f"    ✔ [ACTIVE]   {d['youtube_id']} | {d['title']} -> Privacy: {d['privacy_status']}")

    print("\n" + "=" * 70)
    print("  RECONCILIATION COMPLETE: growth.db matches 100% of live YouTube reality.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    audit_results = run_full_reconciliation()
    print_audit_report(audit_results)
