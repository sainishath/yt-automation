# -*- coding: utf-8 -*-
"""
discord_review.py
-----------------
Pipeline-1 localized Discord review integration module.
Enables posting review requests to Discord channels (generating low-bitrate video proxies if needed)
and parsing user responses.
"""

import os
import re
import subprocess
import requests
from pathlib import Path

def generate_review_proxy(input_video_path: str, output_proxy_path: str) -> str:
    """
    Generates a compact 540x960 proxy video from a full-quality Short
    to guarantee it fits well under Discord's 10 MB webhook upload limit.
    """
    input_path = Path(input_video_path)
    proxy_path = Path(output_proxy_path)
    proxy_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"[Proxy] Generating compact 540x960 video review proxy for {input_path.name}...")
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", "scale=540:960",
        "-c:v", "libx264", "-crf", "30", "-preset", "veryfast",
        "-c:a", "aac", "-b:a", "64k",
        str(proxy_path)
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        size_mb = proxy_path.stat().st_size / (1024 * 1024)
        print(f"[Proxy] Proxy generated: {proxy_path.name} ({size_mb:.2f} MB)")
        return str(proxy_path)
    except Exception as e:
        print(f"[Proxy] Warning: Proxy generation failed: {e}. Falling back to original video.")
        return str(input_path)

def post_for_review(pipeline_name: str, job_id: str, media_paths: list, media_type: str, webhook_url: str) -> bool:
    """
    Posts a review notification to the pipeline's Discord webhook.
    - If media_type is "video", compresses it to a review proxy and uploads it.
    - If media_type is "image", uploads all segment images labeled with their segment_ids.
    """
    if not webhook_url:
        print("[Discord Review] Error: No webhook URL provided.")
        return False
        
    files = {}
    message_text = f"**[{pipeline_name.upper()} PIPELINE - REVIEW GATED]**\n"
    message_text += f"Job ID: `{job_id}`\n"
    
    temp_files_to_cleanup = []
    
    try:
        if media_type == "video":
            # Post compiled video for review
            video_path = media_paths[0]
            proxy_output = Path(video_path).parent / f"review_proxy_{job_id}.mp4"
            proxy_file = generate_review_proxy(video_path, str(proxy_output))
            temp_files_to_cleanup.append(proxy_file)
            
            message_text += "Please review the final compiled video.\n"
            message_text += f"👉 Reply with: `approve {job_id}` or `reject {job_id}`"
            
            files["file"] = (os.path.basename(proxy_file), open(proxy_file, "rb"), "video/mp4")
            
        elif media_type == "image":
            # Post segment images for review (expects a list of (segment_id, image_path) tuples)
            message_text += "Please review the generated segment images.\n"
            instructions = []
            
            for idx, (seg_id, img_path) in enumerate(media_paths):
                if img_path and os.path.exists(img_path):
                    file_key = f"file_{idx}"
                    files[file_key] = (os.path.basename(img_path), open(img_path, "rb"), "image/png")
                    instructions.append(f"`{seg_id}`")
                    
            message_text += f"Segments: {', '.join(instructions)}\n"
            message_text += f"👉 Reply with: `approve {job_id}` or `regen {job_id} <segment_id>:<new visual prompt>`"
            
        else:
            print(f"[Discord Review] Unsupported media type: {media_type}")
            return False
            
        payload = {
            "content": message_text
        }
        
        response = requests.post(webhook_url, data=payload, files=files)
        response.raise_for_status()
        print(f"[Discord Review] Successfully posted review request for job {job_id} to Discord.")
        return True
        
    except Exception as e:
        print(f"[Discord Review] Failed to post to Discord webhook: {e}")
        return False
        
    finally:
        # Close open file handles
        for key in list(files.keys()):
            try:
                files[key][1].close()
            except Exception:
                pass
        # Clean up temporary proxy files
        for temp_f in temp_files_to_cleanup:
            try:
                if os.path.exists(temp_f) and "review_proxy_" in temp_f:
                    os.remove(temp_f)
            except Exception:
                pass

def parse_discord_reply(message_text: str) -> dict:
    """
    Parses a Discord reply message into a structured workflow action dictionary.
    Supports actions:
    - approve <job_id>
    - reject <job_id>
    - regen <job_id> <segment_id>:<override_prompt>
    """
    text = message_text.strip()
    
    # 1. Parse approve command
    approve_match = re.match(r"^approve\s+([a-zA-Z0-9_\-]+)$", text, re.IGNORECASE)
    if approve_match:
        return {
            "job_id": approve_match.group(1),
            "action": "approve",
            "segment_id": None,
            "override_prompt": None
        }
        
    # 2. Parse reject command
    reject_match = re.match(r"^reject\s+([a-zA-Z0-9_\-]+)$", text, re.IGNORECASE)
    if reject_match:
        return {
            "job_id": reject_match.group(1),
            "action": "reject",
            "segment_id": None,
            "override_prompt": None
        }
        
    # 3. Parse regen command
    # Syntax: regen <job_id> <segment_id>:<override_prompt>
    regen_match = re.match(r"^regen\s+([a-zA-Z0-9_\-]+)\s+([a-zA-Z0-9_]+):(.+)$", text, re.IGNORECASE)
    if regen_match:
        return {
            "job_id": regen_match.group(1),
            "action": "regenerate",
            "segment_id": regen_match.group(2),
            "override_prompt": regen_match.group(3).strip()
        }
        
    return {
        "job_id": None,
        "action": None,
        "segment_id": None,
        "override_prompt": None,
        "error": "Failed to parse reply command. Does not match syntax."
    }
