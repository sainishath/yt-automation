# -*- coding: utf-8 -*-
"""
server_alt_history.py
---------------------
Flask API Backend server on Port 8000 serving n8n requests for Alternate History Shorts.
"""

import os
import sys
import json
import logging
from pathlib import Path
from flask import Flask, request, jsonify, send_file

_DIR = Path(__file__).parent.resolve()
sys.path.append(str(_DIR / "scripts"))

from pipeline_runner import run_pipeline1

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

STYLE_CFG_PATH = _DIR / "config" / "style.json"

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "alternate-history-server", "port": 8000})

@app.route('/generate-alternate-history', methods=['POST'])
def generate_alternate_history():
    try:
        data = request.get_json() or {}
        topic = data.get("topic", "What if the Library of Alexandria survived?")
        video_id = data.get("video_id", f"video_{os.urandom(4).hex()}")
        
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
        discord_webhook_url = "https://discord.com/api/webhooks/1528622690980724807/0LU5dDQwTA3bd2nbnx4DIUix_DJq3tYH0KykuMYqu67XVWupfrS_7KB5hK5uZWdUkQv0"
        try:
            from discord_review import post_for_review
            post_for_review("alternate-history", video_id, [str(final_mp4)], "video", discord_webhook_url)
            logger.info(f"[ALT-HISTORY] Posted video review for {video_id} to Discord webhook")
        except Exception as de:
            logger.warning(f"[ALT-HISTORY] Discord review posting failed: {de}")
            
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

@app.route('/get-video', methods=['GET'])
def get_video():
    video_id = request.args.get('id')
    if not video_id:
        return jsonify({"status": "error", "error": "Missing video id parameter"}), 400
        
    out_dir = _DIR / "output" / video_id
    mp4_files = list((out_dir / "final").glob("*.mp4")) + list(out_dir.glob("*.mp4"))
    if not mp4_files:
        return jsonify({"status": "error", "error": f"No compiled video found for {video_id}"}), 404
        
    return send_file(str(mp4_files[0]), mimetype='video/mp4', as_attachment=True, download_name=f"{video_id}.mp4")

@app.route('/get-status', methods=['GET'])
def get_status():
    video_id = request.args.get('id')
    if not video_id:
        return jsonify({"status": "error", "error": "Missing video id parameter"}), 400
    
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
    try:
        data = request.get_json() or {}
        video_id = data.get("video_id")
        privacy = data.get("privacy", "public")
        
        if not video_id:
            return jsonify({"status": "error", "error": "Missing video_id parameter"}), 400
            
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
    app.run(host='0.0.0.0', port=8000, debug=False)
