# -*- coding: utf-8 -*-
"""
server.py
---------
API Backend server bridging n8n automation requests to the upgraded media_engine pipeline.
Supports asynchronous background tasks with threading, status checks, and strict cleanup.
"""

import os
import sys
import uuid
import logging
import shutil
import threading
from pathlib import Path
from flask import Flask, request, jsonify, send_file

# Ensure we can import from current directory
_DIR = Path(__file__).parent.resolve()
sys.path.append(str(_DIR))

from media_engine import (
    generate_voiceover,
    generate_subtitles,
    pick_background,
    assemble_video,
    CFG
)

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Paths
TEMP_DIR = Path(CFG["temp_dir"])
OUTPUT_DIR = Path(CFG["output_dir"])
FINAL_VIDEO_PATH = OUTPUT_DIR / "final.mp4"

# Task tracker database
tasks = {}
tasks_lock = threading.Lock()

def _clean_temp_files(audio_raw, audio_path):
    """Safely remove intermediate audio and subtitle files."""
    try:
        raw_p = Path(audio_raw)
        path_p = Path(audio_path)
        ass_p = path_p.with_suffix(".ass")
        for p in [raw_p, path_p, ass_p]:
            if p.exists():
                p.unlink()
                logger.info(f"Cleaned up temp file: {p.name}")
    except Exception as e:
        logger.warning(f"Could not perform temp file cleanup: {e}")

def run_pipeline_task(task_id, text, title, category, voice):
    """Executes the media compilation pipeline as a background thread task."""
    audio_raw = str(TEMP_DIR / f"{task_id}_voice_raw.wav")
    audio_path = str(TEMP_DIR / f"{task_id}_voice_sped.wav")
    task_output_path = OUTPUT_DIR / f"{task_id}.mp4"

    try:
        # 1. Generate voiceover
        logger.info(f"[{task_id}] Generating voiceover...")
        generate_voiceover(text, audio_raw, voice=voice)

        # Sped file is returned by media_engine voiceover pipeline, let's verify path
        # Note: generate_voiceover returns the path of the sped audio
        sped_audio_path = str(TEMP_DIR / f"{task_id}_voice_raw_sped.wav")
        if not Path(sped_audio_path).exists():
            sped_audio_path = audio_raw

        # 2. Transcribe voiceover to get timing and duration
        logger.info(f"[{task_id}] Transcribing voiceover...")
        subtitle_data = generate_subtitles(sped_audio_path)

        # 3. Select background video clip
        logger.info(f"[{task_id}] Selecting background clip...")
        bg_path = pick_background(required_duration=subtitle_data["duration"])

        # 4. Assemble final video with sidechain compression and bouncing subtitles
        logger.info(f"[{task_id}] Rendering final video...")
        assemble_video(bg_path, sped_audio_path, subtitle_data, str(task_output_path), category)

        # 5. Overwrite the main final.mp4 for legacy / sync download requests
        shutil.copy2(task_output_path, FINAL_VIDEO_PATH)

        with tasks_lock:
            tasks[task_id] = {
                "status": "success",
                "video_path": str(task_output_path),
                "duration": subtitle_data["duration"],
                "error": None
            }
        logger.info(f"✓ [{task_id}] Task completed successfully!")

    except Exception as e:
        logger.error(f"✗ [{task_id}] Task failed: {str(e)}", exc_info=True)
        with tasks_lock:
            tasks[task_id] = {
                "status": "error",
                "video_path": None,
                "duration": 0,
                "error": str(e)
            }
    finally:
        # Strict lifecycle management of temporary audio and subtitle assets
        _clean_temp_files(audio_raw, sped_audio_path)


@app.route('/tts', methods=['POST'])
def tts():
    """
    Generate video from script and title.
    Expected payload:
    {
        "text": "full script text",
        "title": "on screen title",
        "category": "Weird Science" | "Productivity & stoicism" | "Human Behavior" | "Tech",
        "voice": "en-US-BrianNeural",
        "sync": true/false (defaults to true for legacy workflow compatibility)
    }
    """
    try:
        data = request.json or {}
        text = data.get('text', '')
        title = data.get('title', 'MIND HACK')
        category = data.get('category', 'Tech')
        voice = data.get('voice', 'en-US-BrianNeural')
        sync = data.get('sync', True)

        if not text:
            return jsonify({"status": "error", "error": "No script text provided"}), 400

        task_id = str(uuid.uuid4())
        logger.info(f"🎬 Received video request: '{title}' (sync={sync}, task_id={task_id})")

        if sync:
            # Synchronous rendering
            with tasks_lock:
                tasks[task_id] = {"status": "processing", "video_path": None, "error": None}
            
            # Execute directly in request thread
            run_pipeline_task(task_id, text, title, category, voice)
            
            task_result = tasks[task_id]
            if task_result["status"] == "success":
                return jsonify({
                    "status": "success",
                    "task_id": task_id,
                    "video_path": task_result["video_path"],
                    "duration": task_result["duration"]
                })
            else:
                return jsonify({
                    "status": "error",
                    "task_id": task_id,
                    "error": task_result["error"]
                }), 500
        else:
            # Asynchronous rendering - fire and forget background thread
            with tasks_lock:
                tasks[task_id] = {"status": "processing", "video_path": None, "error": None}
            
            thread = threading.Thread(
                target=run_pipeline_task,
                args=(task_id, text, title, category, voice),
                daemon=True
            )
            thread.start()
            
            return jsonify({
                "status": "accepted",
                "task_id": task_id,
                "message": "Video compilation running in background."
            }), 202

    except Exception as e:
        logger.error(f"✗ Video generation failed: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/status/<task_id>', methods=['GET'])
def get_status(task_id):
    """Query the status of an asynchronous background rendering task."""
    with tasks_lock:
        task = tasks.get(task_id)

    if not task:
        return jsonify({"status": "error", "error": "Task not found"}), 404

    return jsonify(task)


@app.route('/get-video', methods=['GET'])
@app.route('/get-video/<task_id>', methods=['GET'])
def get_video(task_id=None):
    """Serves the generated video file as binary download to n8n."""
    video_to_serve = FINAL_VIDEO_PATH

    if task_id:
        with tasks_lock:
            task = tasks.get(task_id)
        if not task:
            return jsonify({"status": "error", "error": "Task not found"}), 404
        if task["status"] == "processing":
            return jsonify({"status": "error", "error": "Video is still processing"}), 202
        if task["status"] == "error":
            return jsonify({"status": "error", "error": f"Video generation failed: {task['error']}"}), 500
        
        video_to_serve = Path(task["video_path"])

    if not video_to_serve.exists():
        logger.error(f"✗ Video file not found: {video_to_serve}")
        return jsonify({"status": "error", "error": "Video file not found"}), 404

    return send_file(video_to_serve, mimetype='video/mp4', as_attachment=True, download_name="final.mp4")


@app.route('/upload_youtube', methods=['POST'])
def upload_youtube():
    """Exposes YouTube upload functionality."""
    try:
        data = request.json or {}
        video_path = data.get('video_path', str(FINAL_VIDEO_PATH))
        title = data.get('title', 'New Short')
        description = data.get('description', '#shorts')
        tags = data.get('tags', [])
        category_id = data.get('category_id', '27')

        from uploader import upload_to_youtube
        result = upload_to_youtube(video_path, title, description, tags, category_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"✗ YouTube upload failed: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """System health check endpoint."""
    return jsonify({
        "status": "ok",
        "ffmpeg_available": True,
        "backgrounds_dir_exists": Path(CFG["backgrounds_dir"]).exists(),
        "final_video_exists": FINAL_VIDEO_PATH.exists()
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    logger.info(f"🚀 Flask Server starting on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)
