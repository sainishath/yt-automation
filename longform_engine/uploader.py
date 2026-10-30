# -*- coding: utf-8 -*-
"""
longform_engine/uploader.py
----------------------------
YouTube Data API v3 Uploader & Automated Scheduling Engine for Longform Documentaries & Derived Shorts.
Enforces:
- Category 27 (Education)
- Mandatory synthetic media disclosure (status.containsSyntheticMedia = True)
- Primary source citations & chapter timestamps
- Resumable chunked upload with progress display
- Scheduled publishAt support for daily Shorts queues (e.g. 13:00 IST / 07:30 UTC)
- Quota tracking & manifest export (week_1_schedule_manifest.json)
"""

from __future__ import annotations

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pipeline.upload_guard import (
    build_youtube_insert_body,
    append_rag_citations_to_description,
)
from pipeline.primary_sources import extract_primary_sources

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Constants & Paths
CONFIG_DIR = _ROOT / "alternate-history-shorts" / "config"
TOKEN_FILE = Path(os.getenv("P1_YOUTUBE_TOKEN", str(CONFIG_DIR / "token.json")))
CLIENT_SECRETS_FILE = Path(os.getenv("P1_YOUTUBE_CLIENT_SECRETS", str(CONFIG_DIR / "client_secrets.json")))
QUOTA_TRACKER_FILE = CONFIG_DIR / "quota_tracker.json"

QUOTA_UNITS_PER_UPLOAD = 1600
QUOTA_DAILY_LIMIT = 10000
CATEGORY_EDUCATION = "27"

YOUTUBE_UPLOAD_SCOPE = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def load_quota_tracker() -> Dict[str, Any]:
    """Loads today's quota usage from quota_tracker.json."""
    today = time.strftime("%Y-%m-%d")
    if QUOTA_TRACKER_FILE.exists():
        try:
            with open(QUOTA_TRACKER_FILE, "r", encoding="utf-8") as f:
                tracker = json.load(f)
            if tracker.get("date") == today:
                return tracker
        except Exception as e:
            logging.warning(f"Failed to read quota tracker: {e}")
    return {"date": today, "units_used": 0, "uploads": []}


def save_quota_tracker(tracker: Dict[str, Any]) -> None:
    """Saves updated quota usage to quota_tracker.json."""
    QUOTA_TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(QUOTA_TRACKER_FILE, "w", encoding="utf-8") as f:
        json.dump(tracker, f, indent=2)


def get_authenticated_service():
    """Authenticates with YouTube Data API v3 using the stored OAuth token."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    if not TOKEN_FILE.exists():
        raise FileNotFoundError(
            f"YouTube OAuth token not found at {TOKEN_FILE}.\n"
            "Please ensure alternate-history-shorts/config/token.json exists."
        )

    credentials = Credentials.from_authorized_user_file(
        str(TOKEN_FILE), YOUTUBE_UPLOAD_SCOPE
    )

    if credentials.expired and credentials.refresh_token:
        logging.info("Refreshing expired YouTube OAuth token...")
        credentials.refresh(Request())
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(credentials.to_json())
        logging.info("Token refreshed and saved successfully.")

    if not credentials.valid:
        raise RuntimeError("OAuth credentials invalid even after refresh attempt.")

    return build("youtube", "v3", credentials=credentials)


def upload_single_video(
    video_path: Path,
    title: str,
    description: str,
    tags: List[str],
    privacy: str = "public",
    publish_at_iso: Optional[str] = None,
    is_short: bool = False,
    force: bool = False,
) -> Dict[str, Any]:
    """Uploads a video to YouTube with resumable chunking and quota protection."""
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError

    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Check daily quota
    tracker = load_quota_tracker()
    units_remaining = QUOTA_DAILY_LIMIT - tracker["units_used"]
    if units_remaining < QUOTA_UNITS_PER_UPLOAD:
        raise RuntimeError(
            f"YouTube daily API quota limit reached! "
            f"Used: {tracker['units_used']}/{QUOTA_DAILY_LIMIT}. "
            f"Need {QUOTA_UNITS_PER_UPLOAD} units per upload."
        )

    # Format description
    desc = description.strip()
    if is_short and "#Shorts" not in desc and "#shorts" not in desc:
        desc += "\n\n#Shorts"

    synthetic_note = "[Altered or Synthetic Content: This video contains AI-generated visual and audio content.]"
    if synthetic_note not in desc:
        desc = f"{desc}\n\n{synthetic_note}"

    # Build insert body
    body = build_youtube_insert_body(
        title=title,
        description=desc,
        tags=tags,
        category_id=CATEGORY_EDUCATION,
        publish_at_iso=publish_at_iso,
    )
    if not publish_at_iso:
        body["status"]["privacyStatus"] = privacy

    youtube = get_authenticated_service()

    file_size_mb = video_path.stat().st_size / (1024 * 1024)
    target_privacy = body["status"]["privacyStatus"]
    logging.info(
        f"Uploading {video_path.name} ({file_size_mb:.1f} MB) | "
        f"Title: {title[:60]}... | Privacy: {target_privacy}"
        + (f" | Scheduled: {publish_at_iso}" if publish_at_iso else "")
    )

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        chunksize=5 * 1024 * 1024,
        resumable=True
    )

    start_time = time.time()
    try:
        insert_request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = insert_request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                elapsed = time.time() - start_time
                print(f"\r  Upload progress: {pct}% ({elapsed:.0f}s elapsed)", end="", flush=True)
        print()

    except HttpError as e:
        error_content = json.loads(e.content.decode()) if e.content else {}
        error_msg = error_content.get("error", {}).get("message", str(e))
        if privacy == "public" and not publish_at_iso:
            logging.warning(f"Public upload rejected ({error_msg}). Retrying as 'private'...")
            body["status"]["privacyStatus"] = "private"
            media = MediaFileUpload(
                str(video_path),
                mimetype="video/mp4",
                chunksize=5 * 1024 * 1024,
                resumable=True
            )
            insert_request = youtube.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media
            )
            response = None
            start_time = time.time()
            while response is None:
                status, response = insert_request.next_chunk()
                if status:
                    pct = int(status.progress() * 100)
                    elapsed = time.time() - start_time
                    print(f"\r  Upload progress (private retry): {pct}% ({elapsed:.0f}s elapsed)", end="", flush=True)
            print()
            target_privacy = "private"
        else:
            logging.error(f"YouTube upload failed: {error_msg}")
            raise RuntimeError(f"YouTube upload failed: {error_msg}") from e

    upload_time = time.time() - start_time
    yt_video_id = response.get("id", "")
    public_url = f"https://youtu.be/{yt_video_id}"
    studio_url = f"https://studio.youtube.com/video/{yt_video_id}/edit"

    # Update quota tracker
    tracker["units_used"] += QUOTA_UNITS_PER_UPLOAD
    tracker["uploads"].append({
        "file_name": video_path.name,
        "youtube_id": yt_video_id,
        "privacy": target_privacy,
        "scheduled_publish": publish_at_iso,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "upload_time_seconds": round(upload_time, 1)
    })
    save_quota_tracker(tracker)

    return {
        "youtube_video_id": yt_video_id,
        "public_url": public_url,
        "studio_url": studio_url,
        "privacy": target_privacy,
        "publish_at_iso": publish_at_iso,
        "upload_time_seconds": round(upload_time, 1),
    }


def build_week_1_manifest() -> Dict[str, Any]:
    """Builds the comprehensive scheduling manifest structure for Week 1."""
    output_dir = _ROOT / "longform_engine" / "output" / "history_10min"
    master_path = output_dir / "constantinople_1453_10min_master.mp4"
    desc_path = output_dir / "youtube_description.txt"

    master_desc = ""
    if desc_path.exists():
        master_desc = desc_path.read_text(encoding="utf-8").replace("Mehmed IIs", "Mehmed II's")

    # Add verified primary source citations
    sources = extract_primary_sources("constantinople_1453")
    citations_text = "\n\nPRIMARY HISTORICAL SOURCES & CITATIONS (EYEWITNESS):\n"
    for s in sources[:5]:
        citations_text += f"- {s['author']} ({s['date']}): {s['original_work']}\n"
    master_desc += citations_text

    master_title = "The 53 Days That Shattered Rome: The Fall of Constantinople (1453)"
    master_tags = [
        "Fall of Constantinople", "Constantinople 1453", "Byzantine Empire",
        "Ottoman Empire", "Mehmed II", "Constantine XI", "Theodosian Walls",
        "Urban the Engineer", "Basilic Cannon", "Golden Horn",
        "Military History", "Historical Documentary", "Chronos Shift"
    ]

    shorts_dir = output_dir / "shorts"
    shorts_queue = []
    short_ids = ["w1_short_01", "w1_short_02", "w1_short_03", "w1_short_04", "w1_short_05"]

    for sid in short_ids:
        meta_file = shorts_dir / f"{sid}_meta.json"
        short_mp4 = shorts_dir / f"{sid}.mp4"
        if not meta_file.exists():
            continue

        with open(meta_file, "r", encoding="utf-8") as f:
            smeta = json.load(f)

        # Ensure accurate master video CTA
        sdesc = smeta.get("description", "")
        sdesc = sdesc.replace("Constantinople 1453 10Min Master", master_title)
        pinned_comment = (
            f"🚨 Watch the complete 10-minute master documentary:\n"
            f"\"{master_title}\" on Chronos Shift!\n"
            f"Full siege breakdown with Theodosian wall defenses, overland fleet transit, and primary sources."
        )

        shorts_queue.append({
            "short_id": sid,
            "title": smeta.get("title", f"Constantinople 1453 Short ({sid})"),
            "file_path": str(short_mp4.relative_to(_ROOT)).replace("\\", "/"),
            "meta_path": str(meta_file.relative_to(_ROOT)).replace("\\", "/"),
            "source_act": smeta.get("source_act"),
            "duration_sec": smeta.get("duration_sec", 45.0),
            "privacy_target": "private",
            "publish_at_iso": smeta.get("publish_at_iso"),
            "scheduled_slot_ist": f"{smeta.get('publish_at_iso', '')[:10]} 13:00 IST",
            "description": sdesc,
            "tags": smeta.get("tags", ["History", "Shorts", "Documentary"]),
            "pinned_comment": pinned_comment,
            "youtube_video_id": smeta.get("youtube_video_id"),
            "public_url": smeta.get("youtube_url"),
            "studio_url": smeta.get("studio_url"),
            "status": "SCHEDULED" if smeta.get("youtube_video_id") else "READY"
        })

    manifest = {
        "production_cycle": "Week 1",
        "theme": "The Fall of Constantinople (1453)",
        "channel_identity": {
            "name": "sai nishath",
            "handle": "@sainishath4220",
            "channel_id": "UCoR40hR599Fu66KoWCXgjnw",
            "brand": "Chronos Shift"
        },
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "master_documentary": {
            "title": master_title,
            "file_path": str(master_path.relative_to(_ROOT)).replace("\\", "/"),
            "duration_sec": 533.6,
            "category_id": CATEGORY_EDUCATION,
            "privacy_target": "public",
            "upload_slot": "Day 1 (Today / Immediate)",
            "description": master_desc,
            "tags": master_tags,
            "contains_synthetic_media": True,
            "youtube_video_id": None,
            "public_url": None,
            "studio_url": None,
            "status": "READY"
        },
        "shorts_queue": shorts_queue,
        "execution_summary": {
            "total_items": 1 + len(shorts_queue),
            "master_uploaded": False,
            "shorts_scheduled": 0,
            "daily_quota_budget": f"{QUOTA_UNITS_PER_UPLOAD * (1 + len(shorts_queue))} / {QUOTA_DAILY_LIMIT} units"
        }
    }
    return manifest


def execute_week_1_upload_queue(dry_run: bool = False) -> Dict[str, Any]:
    """Executes the Week 1 master upload and schedules the 5 derived Shorts."""
    manifest = build_week_1_manifest()
    manifest_out = _ROOT / "longform_engine" / "output" / "week_1_schedule_manifest.json"

    # If manifest already exists, preserve existing IDs
    if manifest_out.exists():
        try:
            with open(manifest_out, "r", encoding="utf-8") as f:
                old_m = json.load(f)
            if old_m.get("master_documentary", {}).get("youtube_video_id"):
                manifest["master_documentary"]["youtube_video_id"] = old_m["master_documentary"]["youtube_video_id"]
                manifest["master_documentary"]["public_url"] = old_m["master_documentary"]["public_url"]
                manifest["master_documentary"]["studio_url"] = old_m["master_documentary"]["studio_url"]
                manifest["master_documentary"]["status"] = "UPLOADED"
                manifest["execution_summary"]["master_uploaded"] = True

            for short in manifest["shorts_queue"]:
                for old_short in old_m.get("shorts_queue", []):
                    if old_short["short_id"] == short["short_id"] and old_short.get("youtube_video_id"):
                        short["youtube_video_id"] = old_short["youtube_video_id"]
                        short["public_url"] = old_short["public_url"]
                        short["studio_url"] = old_short["studio_url"]
                        short["status"] = "SCHEDULED"
        except Exception as e:
            logging.warning(f"Error reading existing manifest: {e}")

    if dry_run:
        logging.info("=== DRY RUN MODE: Validating files and schedule ===")
        print(json.dumps(manifest, indent=2))
        with open(manifest_out, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        print(f"\nManifest written to: {manifest_out}")
        return manifest

    # 1. Upload Master Documentary
    master = manifest["master_documentary"]
    master_path = _ROOT / master["file_path"]

    if master.get("youtube_video_id"):
        logging.info(f"[IDEMPOTENCY] Master documentary already uploaded: {master['youtube_video_id']} ({master['public_url']})")
    else:
        logging.info("==================================================")
        logging.info("STEP 1: Uploading Master Longform Documentary...")
        logging.info("==================================================")
        res = upload_single_video(
            video_path=master_path,
            title=master["title"],
            description=master["description"],
            tags=master["tags"],
            privacy=master["privacy_target"],
            publish_at_iso=None,
            is_short=False
        )
        master["youtube_video_id"] = res["youtube_video_id"]
        master["public_url"] = res["public_url"]
        master["studio_url"] = res["studio_url"]
        master["privacy_status"] = res["privacy"]
        master["status"] = "UPLOADED"
        manifest["execution_summary"]["master_uploaded"] = True

        # Save manifest checkpoint
        with open(manifest_out, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    # 2. Upload and Schedule Derived Shorts
    logging.info("==================================================")
    logging.info("STEP 2: Uploading & Scheduling 5 Derived Shorts...")
    logging.info("==================================================")
    scheduled_count = 0

    for idx, short in enumerate(manifest["shorts_queue"], 1):
        sid = short["short_id"]
        if short.get("youtube_video_id"):
            logging.info(f"[IDEMPOTENCY] Short {sid} already uploaded: {short['youtube_video_id']}")
            scheduled_count += 1
            continue

        short_path = _ROOT / short["file_path"]
        meta_path = _ROOT / short["meta_path"]

        logging.info(f"\nUploading Short {idx}/5: {short['title']} (Slot: {short['scheduled_slot_ist']})")
        res = upload_single_video(
            video_path=short_path,
            title=short["title"],
            description=short["description"],
            tags=short["tags"],
            privacy="private",
            publish_at_iso=short["publish_at_iso"],
            is_short=True
        )

        short["youtube_video_id"] = res["youtube_video_id"]
        short["public_url"] = res["public_url"]
        short["studio_url"] = res["studio_url"]
        short["status"] = "SCHEDULED"
        scheduled_count += 1

        # Also update the per-short meta JSON
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                smeta = json.load(f)
            smeta["youtube_video_id"] = res["youtube_video_id"]
            smeta["youtube_url"] = res["public_url"]
            smeta["studio_url"] = res["studio_url"]
            smeta["upload_status"] = "SCHEDULED"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(smeta, f, indent=2)

        # Save manifest checkpoint
        manifest["execution_summary"]["shorts_scheduled"] = scheduled_count
        with open(manifest_out, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    manifest["execution_summary"]["shorts_scheduled"] = scheduled_count
    with open(manifest_out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload & Schedule Week 1 Master + Shorts")
    parser.add_argument("--dry-run", action="store_true", help="Generate manifest without uploading")
    parser.add_argument("--manifest-only", action="store_true", help="Generate manifest file only")
    args = parser.parse_args()

    if args.manifest_only:
        m = build_week_1_manifest()
        out_file = _ROOT / "longform_engine" / "output" / "week_1_schedule_manifest.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(m, f, indent=2)
        print(f"Manifest written to {out_file}")
    else:
        execute_week_1_upload_queue(dry_run=args.dry_run)
