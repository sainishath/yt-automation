# -*- coding: utf-8 -*-
"""
server_alt_history.py
---------------------
Flask API Backend server on Port 8000 serving n8n requests for Alternate History Shorts.
Includes:
- Host binding configuration (default 127.0.0.1 for local isolation)
- Optional API key authentication (SERVER_API_KEY)
- Concurrency control (pipeline_lock to prevent concurrent GPU VRAM exhaustion)
- Strict path traversal protection on video_id parameters
"""

import os
import sys
import re
import json
import logging
import threading
from pathlib import Path
from flask import Flask, request, jsonify, send_file

_DIR = Path(__file__).parent.resolve()
sys.path.append(str(_DIR / "scripts"))

from pipeline_runner import run_pipeline1

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

STYLE_CFG_PATH = _DIR / "config" / "style.json"
pipeline_lock = threading.Lock()


def _require_api_key():
    """Validates X-API-Key or Authorization header if SERVER_API_KEY is set in environment."""
    expected_key = os.getenv("SERVER_API_KEY", "").strip()
    if not expected_key:
        return None  # Pass-through when no API key is configured

    provided_key = (
        request.headers.get("X-API-Key", "").strip()
        or request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    )
    if provided_key != expected_key:
        return jsonify({"status": "error", "error": "Unauthorized: Invalid or missing API key"}), 401
    return None


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "service": "alternate-history-server",
        "port": 8000,
        "pipeline_busy": pipeline_lock.locked()
    })


@app.route('/generate-alternate-history', methods=['POST'])
def generate_alternate_history():
    auth_err = _require_api_key()
    if auth_err:
        return auth_err

    # Concurrency control: prevent simultaneous GPU generation runs from exhausting VRAM
    if not pipeline_lock.acquire(blocking=False):
        return jsonify({
            "status": "error",
            "error": "Pipeline busy with another render"
        }), 429

    try:
        data = request.get_json() or {}
        topic = data.get("topic", "What if the Library of Alexandria survived?")
        video_id = data.get("video_id", f"video_{os.urandom(4).hex()}")

        # Sanitize video_id
        if not re.match(r"^[a-zA-Z0-9_\-]+$", video_id):
            return jsonify({"status": "error", "error": "Invalid video_id parameter format"}), 400
        
        logger.info(f"[ALT-HISTORY] Request received for topic: '{topic}' (video_id={video_id})")
        
        # Execute unified production pipeline runner
        result = run_pipeline1(topic, video_id=video_id, output_dir=str(_DIR / "output"))
        if result.get("status") not in ("READY", "SUCCESS"):
            return jsonify({
                "status": "error",
                "reason": result.get("reason", "PIPELINE_BLOCKED"),
                "manifest": result.get("manifest", {})
            }), 400

        final_mp4 = result.get("video_path")
        meta_file = _DIR / "output" / video_id / "metadata.json"
        title = f"What If: {topic}"
        description = "Alternate History Short #shorts #whatif #history"
        if meta_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as mf:
                    meta = json.load(mf)
                    title = meta.get("title", title)
                    description = meta.get("description", description)
            except Exception:
                pass

        # Post for Discord Review Approval
        discord_webhook_url = (
            os.getenv("DISCORD_WEBHOOK_URL_P1")
            or os.getenv("DISCORD_REVIEW_WEBHOOK_URL")
            or os.getenv("DISCORD_WEBHOOK_URL", "")
        )
        if discord_webhook_url:
            try:
                from discord_review import post_for_review
                post_for_review("alternate-history", video_id, [str(final_mp4)], "video", discord_webhook_url)
                logger.info(f"[ALT-HISTORY] Posted video review for {video_id} to Discord webhook")
            except Exception as de:
                logger.warning(f"[ALT-HISTORY] Discord review posting failed: {de}")
        else:
            logger.warning("[ALT-HISTORY] DISCORD_WEBHOOK_URL_P1 not set; skipping Discord review post.")
            
        return jsonify({
          "status": "success",
          "video_id": video_id,
          "video_path": str(final_mp4),
          "video_url": f"http://127.0.0.1:8000/get-video?id={video_id}",
          "title": title,
          "description": description,
          "qa_status": "PASS"
        })
    except Exception as e:
        logger.error(f"[ALT-HISTORY FAIL] {e}", exc_info=True)
        return jsonify({"status": "error", "error": str(e)}), 500
    finally:
        pipeline_lock.release()


@app.route('/get-video', methods=['GET'])
def get_video():
    video_id = request.args.get('id', '').strip()
    if not video_id or not re.match(r"^[a-zA-Z0-9_\-]+$", video_id):
        return jsonify({"status": "error", "error": "Invalid or missing video id"}), 400
        
    out_dir = _DIR / "output" / video_id
    mp4_files = list((out_dir / "final").glob("*.mp4")) + list(out_dir.glob("*.mp4"))
    if not mp4_files:
        return jsonify({"status": "error", "error": f"No compiled video found for {video_id}"}), 404
        
    return send_file(str(mp4_files[0]), mimetype='video/mp4', as_attachment=True, download_name=f"{video_id}.mp4")


@app.route('/get-status', methods=['GET'])
def get_status():
    video_id = request.args.get('id', '').strip()
    if not video_id or not re.match(r"^[a-zA-Z0-9_\-]+$", video_id):
        return jsonify({"status": "error", "error": "Invalid or missing video id"}), 400
    
    man_file = _DIR / "output" / video_id / "run_manifest.json"
    if not man_file.exists():
        return jsonify({"status": "error", "error": f"No manifest found for {video_id}"}), 404
    
    try:
        with open(man_file, "r", encoding="utf-8") as mf:
            manifest = json.load(mf)
        return jsonify({"status": "success", "manifest": manifest})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/upload-youtube', methods=['POST'])
def upload_youtube_endpoint():
    auth_err = _require_api_key()
    if auth_err:
        return auth_err

    try:
        data = request.get_json() or {}
        video_id = data.get("video_id", "").strip()
        privacy = data.get("privacy", "public")
        
        if not video_id or not re.match(r"^[a-zA-Z0-9_\-]+$", video_id):
            return jsonify({"status": "error", "error": "Invalid or missing video_id parameter"}), 400
            
        from upload_video import upload_video
        upload_result = upload_video(video_id, output_dir=str(_DIR / "output"), privacy=privacy)
        
        return jsonify({
            "status": "success",
            "video_id": video_id,
            "youtube_id": upload_result.get("youtube_video_id"),
            "url": upload_result.get("public_url"),
            "studio_url": upload_result.get("studio_url"),
            "upload_status": upload_result.get("status", "UPLOADED")
        })
    except Exception as e:
        logger.error(f"[UPLOAD FAIL] {e}", exc_info=True)
        return jsonify({"status": "error", "error": str(e)}), 500


if __name__ == '__main__':
    host = os.getenv("SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("SERVER_PORT", "8000"))
    app.run(host=host, port=port, debug=False)
