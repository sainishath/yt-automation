# -*- coding: utf-8 -*-
"""
longform_engine/dispatch_discord_review.py
-------------------------------------------
Dispatches all 5 modular Shorts for a target job to the Discord Review Webhook for creator approval.
"""

import os
import sys
import json
import time
import argparse
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

parser = argparse.ArgumentParser(description="Dispatch review proxies to Discord webhook")
parser.add_argument("--job", type=str, default="siege_of_vienna_1683", help="Target job ID in pending_review")
args = parser.parse_args()

webhook_url = (
    os.getenv("DISCORD_REVIEW_WEBHOOK_URL")
    or os.getenv("DISCORD_WEBHOOK_CHANNEL_A")
    or os.getenv("DISCORD_WEBHOOK_URL_P1")
)

if not webhook_url:
    print("ERROR: Discord webhook URL not found in environment.")
    sys.exit(1)

shorts_dir = _ROOT / "longform_engine" / "output" / "pending_review" / args.job / "shorts"
if not shorts_dir.exists():
    print(f"ERROR: Shorts directory not found: {shorts_dir}")
    sys.exit(1)

meta_files = sorted(shorts_dir.glob("*_meta.json"))
print(f"--> Found {len(meta_files)} Shorts to dispatch from {shorts_dir.name}")

dispatched = []
for mf in meta_files:
    with open(mf, "r", encoding="utf-8") as f:
        meta = json.load(f)

    sid = meta.get("short_id", mf.stem.replace("_meta", ""))
    title = meta.get("title", sid)
    slot = meta.get("scheduled_publish_slot") or meta.get("scheduled_slot") or "Upcoming Slot"
    hook = meta.get("hook_script") or meta.get("description", "").split("\n")[0]
    dur = meta.get("duration_sec", 35.0)

    mp4_path = shorts_dir / f"{sid}.mp4"
    proxy_path = shorts_dir / f"{sid}_proxy.mp4"

    message_content = (
        f"🚨 **[CHRONOS SHIFT (PIPELINE 1) - SHORT REVIEW GATE]**\n"
        f"**Job**: `{args.job}`\n"
        f"**Short ID**: `{sid}`\n"
        f"**Title**: **{title}**\n"
        f"**Target Release Slot**: `{slot}`\n"
        f"**Hook**: *\"{hook[:130]}...\"*\n"
        f"**Specs**: 9:16 Vertical (1080x1920) | Duration: {dur:.1f}s | Subtitles: `MarginV=620`\n"
        f"**Status**: `AWAITING_REVIEW`\n\n"
        f"**Review Checklist:**\n"
        f"  [ ] Visuals: No modern artifacts or deformed anatomy?\n"
        f"  [ ] Voice: Clear pacing and pronunciation?\n"
        f"  [ ] Subtitles: Centered in safe-zone (MarginV=620) with no typos?\n"
        f"  [ ] Packaging: Hook and thumbnail verified?\n\n"
        f"🔘 **To Approve:** `approve {sid}`\n"
        f"🔘 **To Reject/Reroll:** `reroll {sid} <notes>`"
    )

    if not proxy_path.exists() or (mp4_path.exists() and proxy_path.stat().st_mtime < mp4_path.stat().st_mtime):
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

print(f"\n--> All {len(dispatched)}/{len(meta_files)} Shorts successfully posted to Discord.")
