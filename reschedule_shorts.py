#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reschedule_shorts.py
--------------------
Uploads and reschedules re-rendered, 100% synced Shorts to YouTube for the exact same scheduled slot.
Updates week_1_schedule_manifest.json with new video IDs, status, and direct Studio URLs.
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("reschedule_shorts")

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from longform_engine.uploader import upload_single_video, get_authenticated_service

MANIFEST_PATH = ROOT_DIR / "longform_engine" / "output" / "week_1_schedule_manifest.json"
SHORTS_DIR = ROOT_DIR / "longform_engine" / "output" / "history_10min" / "shorts"


def reschedule_short(short_id: str) -> dict:
    mp4_file = SHORTS_DIR / f"{short_id}.mp4"
    meta_file = SHORTS_DIR / f"{short_id}_meta.json"

    if not mp4_file.exists():
        raise FileNotFoundError(f"Video file not found: {mp4_file}")
    if not meta_file.exists():
        raise FileNotFoundError(f"Meta file not found: {meta_file}")

    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    title = meta["title"]
    desc = meta["description"]
    tags = meta["tags"]
    publish_at_iso = meta.get("publish_at_iso") or meta.get("scheduled_publish_slot")
    scheduled_slot_ist = meta.get("scheduled_slot_ist", "Unknown")
    old_video_id = meta.get("old_video_id")

    logger.info(f"Uploading & Rescheduling {short_id}: '{title}' for {publish_at_iso} ({scheduled_slot_ist})")

    # Upload video with publish_at_iso
    result = upload_single_video(
        video_path=mp4_file,
        title=title,
        description=desc,
        tags=tags,
        publish_at_iso=publish_at_iso,
        is_short=True,
    )

    new_video_id = result.get("youtube_video_id") or result.get("video_id")
    public_url = result["public_url"]
    studio_url = f"https://studio.youtube.com/video/{new_video_id}/edit"

    meta["youtube_video_id"] = new_video_id
    meta["youtube_url"] = public_url
    meta["studio_url"] = studio_url
    meta["upload_status"] = "SCHEDULED"
    meta["replaced_video_id"] = old_video_id
    meta_file.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    # Update week_1_schedule_manifest.json
    if MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        for s in manifest.get("shorts_queue", []):
            if s.get("short_id") == short_id:
                s["youtube_video_id"] = new_video_id
                s["public_url"] = public_url
                s["studio_url"] = studio_url
                s["status"] = "SCHEDULED"
                s["publish_at_iso"] = publish_at_iso
                s["scheduled_slot_ist"] = scheduled_slot_ist
                s["replaced_video_id"] = old_video_id
                s["file_path"] = str(mp4_file.relative_to(ROOT_DIR)).replace("\\", "/")
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info(f"✅ Successfully rescheduled {short_id}!")
    logger.info(f"   New Video ID: {new_video_id}")
    logger.info(f"   Scheduled Slot: {scheduled_slot_ist} ({publish_at_iso})")
    logger.info(f"   Public URL: {public_url}")
    logger.info(f"   Studio URL: {studio_url}")
    if old_video_id:
        logger.info(f"   Replaces Old Video: {old_video_id} (Studio: https://studio.youtube.com/video/{old_video_id}/edit)")

    return {
        "short_id": short_id,
        "new_video_id": new_video_id,
        "old_video_id": old_video_id,
        "publish_at_iso": publish_at_iso,
        "scheduled_slot_ist": scheduled_slot_ist,
        "public_url": public_url,
        "studio_url": studio_url
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python reschedule_shorts.py <short_id>")
        sys.exit(1)
    short_id = sys.argv[1]
    res = reschedule_short(short_id)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
