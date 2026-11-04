# -*- coding: utf-8 -*-
"""
longform_engine/dispatch_discord_review.py
-------------------------------------------
Dispatches all 5 Week 2 modular Shorts to the Discord Review Webhook for creator approval.
"""

import os
import sys
import json
import time
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

webhook_url = (
    os.getenv("DISCORD_REVIEW_WEBHOOK_URL")
    or os.getenv("DISCORD_WEBHOOK_CHANNEL_A")
    or os.getenv("DISCORD_WEBHOOK_URL_P1")
)

if not webhook_url:
    print("ERROR: Discord webhook URL not found in environment.")
    sys.exit(1)

shorts_dir = _ROOT / "longform_engine" / "output" / "pending_review" / "bronze_age_collapse_1177bc" / "shorts"
short_items = [
    ("w2_short_01", "Part 1: The Unsent Clay Letter Baked by a Burning Empire (1177 BC)", "Monday 13:00 IST"),
    ("w2_short_02", "Part 2: Why 8 Ancient Superpowers Depended on One Single Ship", "Tuesday 13:00 IST"),
    ("w2_short_03", "Part 3: The 300-Year Drought That Toppled Bronze Age Fortresses", "Wednesday 13:00 IST"),
    ("w2_short_04", "Part 4: Who Were the Mysterious Sea Peoples of 1177 BC?", "Thursday 13:00 IST"),
    ("w2_short_05", "Part 5: How Egypt Trapped the Sea Peoples and Ignited the Iron Age", "Friday 13:00 IST"),
]

print(f"--> Found {len(short_items)} Shorts to dispatch from {shorts_dir.name}")

dispatched = []
for sid, title, slot in short_items:
    mp4_path = shorts_dir / f"{sid}.mp4"
    meta_path = shorts_dir / f"{sid}_meta.json"
    meta = {}
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as mf:
            meta = json.load(mf)

    desc = meta.get("description", "")
    first_line = desc.split("\n")[0] if desc else title

    message_content = (
        f"🎬 **[CHRONOS SHIFT (PIPELINE 1) - SHORT REVIEW GATE]**\n"
        f"**Short ID**: `{sid}`\n"
        f"**Title**: **{title}**\n"
        f"**Target Release Slot**: `{slot}`\n"
        f"**Hook**: *\"{first_line[:130]}...\"*\n"
        f"**Specs**: 9:16 Vertical (1080x1920) | Duration: {meta.get('duration_sec', 56.0):.1f}s | Subtitles: `MarginV=620`\n"
        f"**Status**: `AWAITING_REVIEW`\n\n"
        f"**Review Checklist:**\n"
        f"  [ ] Visuals: No modern artifacts or deformed anatomy?\n"
        f"  [ ] Voice: Clear pacing and pronunciation?\n"
        f"  [ ] Subtitles: Centered in safe-zone (MarginV=620) with no typos?\n"
        f"  [ ] Packaging: Hook and thumbnail verified?\n\n"
        f"👉 **To Approve:** `approve {sid}`\n"
        f"👉 **To Reject/Reroll:** `reroll {sid} <notes>`"
    )

    proxy_path = shorts_dir / f"{sid}_proxy.mp4"
    if not proxy_path.exists() or proxy_path.stat().st_mtime < mp4_path.stat().st_mtime:
        print(f"Generating 540x960 review proxy for {sid}...")
        cmd_proxy = [
            "ffmpeg", "-y",
            "-i", str(mp4_path),
            "-vf", "scale=540:960",
            "-c:v", "libx264",
            "-preset", "faster",
            "-crf", "24",
            "-c:a", "aac",
            "-b:a", "128k",
            str(proxy_path)
        ]
        subprocess.run(cmd_proxy, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    upload_file = proxy_path if proxy_path.exists() else mp4_path
    size_mb = upload_file.stat().st_size / (1024 * 1024)
    print(f"Dispatching {sid} ({upload_file.name}, {size_mb:.2f} MB)...")

    with open(upload_file, "rb") as vf:
        payload = {"content": message_content}
        files = {"file": (f"{sid}.mp4", vf, "video/mp4")}
        resp = requests.post(webhook_url, data=payload, files=files, timeout=60)

    if resp.status_code in (200, 204):
        print(f"  [SUCCESS] {sid} dispatched to Discord successfully (HTTP {resp.status_code})")
        dispatched.append(sid)
    else:
        print(f"  [FAILED] {sid} failed: {resp.status_code} {resp.text}")

    time.sleep(1.5)

print(f"\n--> All {len(dispatched)}/{len(short_items)} Shorts successfully posted to Discord.")
