# -*- coding: utf-8 -*-
"""
discord_review.py
-----------------
Pipeline 1 (Chronos Shift / alternate-history-shorts) Discord review integration.
Generates < 8MB video proxies, enforces human-gated review posting via environment variables
(DISCORD_REVIEW_WEBHOOK_URL / DISCORD_ERROR_WEBHOOK_URL), and raises explicit HTTP errors on delivery failure.
"""

import os
import sys
import re
import logging
import subprocess
import requests
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

_ROOT_REPO = Path(__file__).resolve().parent.parent.parent
if str(_ROOT_REPO) not in sys.path:
    sys.path.insert(0, str(_ROOT_REPO))

try:
    from dotenv import load_dotenv
    _root_env = _ROOT_REPO / ".env"
    if _root_env.exists():
        load_dotenv(_root_env)
    load_dotenv()
except ImportError:
    pass

from pipeline.upload_guard import send_discord_alert

logger = logging.getLogger("DiscordReview")

MAX_DISCORD_PAYLOAD_BYTES = 7900000  # 7.9 MB (strictly within 8MB non-nitro limit)


def generate_review_proxy(input_video_path: str, output_proxy_path: str, max_size_bytes: int = MAX_DISCORD_PAYLOAD_BYTES) -> str:
    """
    Generates a compact 540x960 proxy video from a full-quality Short.
    Enforces a strict < 8MB size limit for Discord webhook delivery via adaptive multi-pass compression.
    """
    input_path = Path(input_video_path)
    proxy_path = Path(output_proxy_path)
    proxy_path.parent.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise FileNotFoundError(f"Input video for proxy generation does not exist: {input_path}")

    print(f"[Proxy] Generating compact 540x960 review proxy for {input_path.name}...")

    cmd_pass1 = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", "scale=540:960",
        "-c:v", "libx264", "-crf", "30", "-preset", "veryfast",
        "-maxrate", "1200k", "-bufsize", "2400k",
        "-c:a", "aac", "-b:a", "64k",
        str(proxy_path)
    ]

    try:
        subprocess.run(cmd_pass1, capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        err_out = e.stderr.decode("utf-8", errors="ignore") if e.stderr else str(e)
        raise RuntimeError(f"FFmpeg Pass 1 proxy encoding failed: {err_out}")

    size_bytes = proxy_path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    print(f"[Proxy] Pass 1 complete: {proxy_path.name} ({size_mb:.2f} MB)")

    if size_bytes > max_size_bytes:
        print(f"[Proxy] Warning: Proxy size ({size_mb:.2f} MB) exceeds limit ({max_size_bytes / (1024*1024):.2f} MB). Running Pass 2 (CRF 36)...")
        cmd_pass2 = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-vf", "scale=540:960",
            "-c:v", "libx264", "-crf", "36", "-preset", "veryfast",
            "-maxrate", "800k", "-bufsize", "1600k",
            "-c:a", "aac", "-b:a", "48k",
            str(proxy_path)
        ]
        try:
            subprocess.run(cmd_pass2, capture_output=True, check=True)
            size_bytes = proxy_path.stat().st_size
            size_mb = size_bytes / (1024 * 1024)
            print(f"[Proxy] Pass 2 complete: {proxy_path.name} ({size_mb:.2f} MB)")
        except subprocess.CalledProcessError as e:
            err_out = e.stderr.decode("utf-8", errors="ignore") if e.stderr else str(e)
            raise RuntimeError(f"FFmpeg Pass 2 proxy encoding failed: {err_out}")

    if size_bytes > max_size_bytes:
        raise ValueError(f"Proxy video size ({size_mb:.2f} MB) strictly exceeds Discord limit ({max_size_bytes / (1024*1024):.2f} MB).")

    return str(proxy_path)


def post_for_review(pipeline_name: str, job_id: str, media_paths: list, media_type: str, webhook_url: Optional[str] = None) -> bool:
    """
    Posts a review notification and proxy media to the Discord review webhook configured in .env.
    - If media_type is "video", compresses it to a < 8MB review proxy and uploads it.
    - If media_type is "image", uploads segment images labeled with their segment_ids.
    Raises RuntimeError if delivery fails.
    """
    target_url = (
        webhook_url
        or os.getenv("DISCORD_REVIEW_WEBHOOK_URL")
        or os.getenv("DISCORD_WEBHOOK_URL_P1")
        or os.getenv("DISCORD_WEBHOOK_CHANNEL_A")
    )

    if not target_url:
        raise RuntimeError(
            "Missing required environment variable: DISCORD_REVIEW_WEBHOOK_URL (or DISCORD_WEBHOOK_URL_P1 / DISCORD_WEBHOOK_CHANNEL_A)."
        )

    files = {}
    temp_files_to_cleanup = []
    message_text = "**[CHRONOS SHIFT (PIPELINE 1) - HUMAN REVIEW GATE]**\n"
    message_text += f"Job ID: `{job_id}`\n"
    message_text += "Status: `AWAITING_REVIEW`\n"

    try:
        if media_type == "video":
            video_path = media_paths[0]
            proxy_output = Path(video_path).parent / f"review_proxy_{job_id}.mp4"
            proxy_file = generate_review_proxy(video_path, str(proxy_output))
            temp_files_to_cleanup.append(proxy_file)

            message_text += "📹 **540x960 Review Proxy Generated**\n"
            message_text += "Please inspect the video formatting, narration sync, and subtitle alignment.\n\n"
            message_text += f"👉 **To Approve Upload:** `approve {job_id}`\n"
            message_text += f"👉 **To Reject:** `reject {job_id}`"

            files["file"] = (os.path.basename(proxy_file), open(proxy_file, "rb"), "video/mp4")

        elif media_type == "image":
            message_text += "🖼️ **Review Generated Scene Overlays:**\n"
            instructions = []
            for idx, item in enumerate(media_paths):
                seg_id, img_path = item if isinstance(item, (tuple, list)) else (f"seg_{idx+1}", item)
                if img_path and os.path.exists(img_path):
                    file_key = f"file_{idx}"
                    files[file_key] = (os.path.basename(img_path), open(img_path, "rb"), "image/png")
                    instructions.append(f"`{seg_id}`")

            message_text += f"Segments: {', '.join(instructions)}\n\n"
            message_text += f"👉 **To Approve:** `approve {job_id}`\n"
            message_text += f"👉 **To Regenerate Segment:** `regen {job_id} <segment_id>:<new visual prompt>`"

        else:
            raise ValueError(f"Unsupported media type: {media_type}")

        payload = {"content": message_text}
        print(f"[Discord Review] Dispatching review payload to Discord webhook (Job: {job_id})...")

        resp = requests.post(target_url, data=payload, files=files, timeout=30)
        
        if resp.status_code not in (200, 204):
            err_msg = f"Discord webhook returned HTTP {resp.status_code}: {resp.text}"
            print(f"[Discord Review Error] {err_msg}")
            raise RuntimeError(err_msg)

        print(f"[Discord Review SUCCESS] Review request for job {job_id} successfully posted to Discord.")
        return True

    finally:
        for key in list(files.keys()):
            try:
                files[key][1].close()
            except Exception:
                pass
        for temp_f in temp_files_to_cleanup:
            try:
                if os.path.exists(temp_f) and "review_proxy_" in temp_f:
                    os.remove(temp_f)
            except Exception:
                pass


def parse_discord_reply(message_text: str) -> dict:
    """
    Parses a Discord reply message into a structured workflow action dictionary.
    """
    text = message_text.strip()

    approve_match = re.match(r"^approve\s+([a-zA-Z0-9_\-]+)$", text, re.IGNORECASE)
    if approve_match:
        return {"job_id": approve_match.group(1), "action": "approve", "segment_id": None, "override_prompt": None}

    reject_match = re.match(r"^reject\s+([a-zA-Z0-9_\-]+)$", text, re.IGNORECASE)
    if reject_match:
        return {"job_id": reject_match.group(1), "action": "reject", "segment_id": None, "override_prompt": None}

    regen_match = re.match(r"^regen\s+([a-zA-Z0-9_\-]+)\s+([a-zA-Z0-9_]+):(.+)$", text, re.IGNORECASE)
    if regen_match:
        return {
            "job_id": regen_match.group(1),
            "action": "regenerate",
            "segment_id": regen_match.group(2),
            "override_prompt": regen_match.group(3).strip()
        }

    return {"job_id": None, "action": None, "segment_id": None, "override_prompt": None, "error": "Failed to parse reply command."}
