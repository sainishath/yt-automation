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
import json
import requests
import logging
import shutil
import threading
from pathlib import Path
from flask import Flask, request, jsonify, send_file

# Ensure we can import from current directory and workspace root
_DIR = Path(__file__).parent.resolve()
sys.path.append(str(_DIR))
sys.path.append(str(_DIR.parent.parent))

from media_engine import (
    generate_script,
    generate_fooocus_image,
    generate_voiceover,
    generate_subtitles,
    pick_background,
    assemble_video,
    compile_long_form,
    CFG
)

from thumbnail_generator import generate_debate_thumbnail
from metadata_generator import generate_metadata
from shared.discord_review import post_for_review, parse_discord_reply

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Paths
TEMP_DIR = Path(CFG["temp_dir"])
OUTPUT_DIR = Path(CFG["output_dir"])
FINAL_VIDEO_PATH = OUTPUT_DIR / "final.mp4"

# Task tracker database with JSON file persistence
import json
TASKS_DB_PATH = TEMP_DIR / "tasks_db.json"
tasks_lock = threading.Lock()

def _load_tasks():
    if TASKS_DB_PATH.exists():
        try:
            with open(TASKS_DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_tasks(tasks_dict):
    try:
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        with open(TASKS_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(tasks_dict, f, indent=4)
    except Exception as e:
        logger.warning(f"Could not save tasks DB: {e}")

tasks = _load_tasks()

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

def run_pipeline_task(task_id, timeline_or_text, title, category, voice):
    """Executes the media compilation pipeline as a background thread task."""
    audio_raw = str(TEMP_DIR / f"{task_id}_voice_raw.wav")
    task_output_path = OUTPUT_DIR / f"{task_id}.mp4"
    sped_audio_path = audio_raw  # Default fallback path

    try:
        # 1. Generate voiceover
        logger.info(f"[{task_id}] Generating voiceover...")
        voice_res = generate_voiceover(timeline_or_text, audio_raw, voice=voice)
        
        if isinstance(voice_res, tuple):
            sped_audio_path, timings = voice_res
        else:
            sped_audio_path = voice_res
            timings = None

        # 1.5 Generate segment images if this is a debate run
        visual_proofs = []
        is_debate_run = timings is not None and len(timings) > 0
        if is_debate_run and isinstance(timeline_or_text, list):
            logger.info(f"[{task_id}] Generating Fooocus images for segments...")
            generated_paths = {}
            for idx, turn in enumerate(timeline_or_text):
                seg_id = turn.get("segment_id", f"seg_{idx}")
                prompt = turn.get("visual_topic_prompt") or turn.get("image_prompt")
                if prompt:
                    target_path = TEMP_DIR / f"{task_id}_{seg_id}.png"
                    if seg_id not in generated_paths:
                        try:
                            img_path = generate_fooocus_image(prompt, str(target_path))
                            generated_paths[seg_id] = img_path
                        except Exception as img_err:
                            logger.warning(f"Failed to generate image for segment {seg_id}: {img_err}")
                            generated_paths[seg_id] = None
                    visual_proofs.append(generated_paths[seg_id])
                else:
                    visual_proofs.append(None)
        else:
            visual_proofs = None

        # 2. Transcribe voiceover to get timing and duration
        logger.info(f"[{task_id}] Transcribing voiceover...")
        subtitle_data = generate_subtitles(sped_audio_path, timings=timings)

        # 3. Select background video clip
        logger.info(f"[{task_id}] Selecting background clip...")
        is_debate_run = timings is not None and len(timings) > 0
        bg_path = pick_background(required_duration=subtitle_data["duration"], is_debate=is_debate_run)

        # 4. Assemble final video with sidechain compression and bouncing subtitles
        logger.info(f"[{task_id}] Rendering final video...")
        assemble_video(
            bg_path, 
            sped_audio_path, 
            subtitle_data, 
            str(task_output_path), 
            category,
            visual_proofs=visual_proofs,
            timings=timings
        )

        # 5. Overwrite the main final.mp4 for legacy / sync download requests
        shutil.copy2(task_output_path, FINAL_VIDEO_PATH)

        with tasks_lock:
            tasks[task_id] = {
                "status": "success",
                "video_path": str(task_output_path).replace("\\", "/"),
                "duration": subtitle_data["duration"],
                "error": None
            }
            _save_tasks(tasks)
        logger.info(f"OK: [{task_id}] Task completed successfully!")

    except Exception as e:
        logger.error(f"FAIL: [{task_id}] Task failed: {str(e)}", exc_info=True)
        with tasks_lock:
            tasks[task_id] = {
                "status": "error",
                "video_path": None,
                "duration": 0,
                "error": str(e)
            }
            _save_tasks(tasks)
    finally:
        # Strict lifecycle management of temporary audio and subtitle assets
        _clean_temp_files(audio_raw, sped_audio_path)


@app.route('/generate-factual-discussion', methods=['POST'])
@app.route('/tts', methods=['POST'])
def tts():
    """
    Generate video from script and title.
    Expected payload:
    - Array format:
      [{"speaker": "character_name", "text": "dialogue string", "visual_proof_prompt": "descriptive prompt or null"}]
    - OR Legacy format:
      {
          "text": "full script text or stringified JSON array",
          "title": "on screen title",
          "category": "Weird Science" | "Productivity & stoicism" | "Human Behavior" | "Tech",
          "voice": "en-US-BrianNeural",
          "sync": true/false
      }
    """
    try:
        data = request.json or {}
        if isinstance(data, list):
            timeline_or_text = data
            title = 'MIND HACK'
            category = 'Tech'
            voice = 'en-US-BrianNeural'
            sync = True
        else:
            text_val = data.get('text', '')
            title = data.get('title', 'MIND HACK')
            category = data.get('category', 'Tech')
            voice = data.get('voice', 'en-US-BrianNeural')
            sync = data.get('sync', True)

            if not text_val and title:
                logger.info(f"[VIDEO] No pre-generated script text provided. Triggering Ollama generate_script for topic: '{title}'...")
                script_data = generate_script(title, category)
                timeline_or_text = script_data.get("lines", [])
            else:
                timeline_or_text = text_val
                if isinstance(text_val, str) and text_val.strip().startswith('['):
                    try:
                        timeline_or_text = json.loads(text_val)
                    except Exception:
                        pass

        if not timeline_or_text:
            return jsonify({"status": "error", "error": "No script timeline or text provided"}), 400

        task_id = str(uuid.uuid4())
        logger.info(f"[VIDEO] Received video request: '{title}' (sync={sync}, task_id={task_id})")

        if sync:
            # Synchronous rendering
            with tasks_lock:
                tasks[task_id] = {"status": "processing", "video_path": None, "error": None}
                _save_tasks(tasks)
            
            # Execute directly in request thread
            run_pipeline_task(task_id, timeline_or_text, title, category, voice)
            
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
                _save_tasks(tasks)
            
            thread = threading.Thread(
                target=run_pipeline_task,
                args=(task_id, timeline_or_text, title, category, voice),
                daemon=True
            )
            thread.start()
            
            return jsonify({
                "status": "accepted",
                "task_id": task_id,
                "message": "Video compilation running in background."
            }), 202

    except Exception as e:
        logger.error(f"FAIL: Video generation failed: {str(e)}", exc_info=True)
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
        logger.error(f"FAIL: Video file not found: {video_to_serve}")
        return jsonify({"status": "error", "error": "Video file not found"}), 404

    return send_file(video_to_serve, mimetype='video/mp4', as_attachment=True, download_name="final.mp4")



@app.route('/auth-youtube', methods=['GET'])
def auth_youtube():
    """
    One-time YouTube OAuth setup.
    Visit http://localhost:5001/auth-youtube in your browser.
    This opens a Google consent screen in a new browser tab/window (port 8090).
    After you approve access, the token is saved automatically.
    Only needs to be done ONCE — auto-refreshes forever after.
    """
    try:
        from uploader import is_authorized, run_auth_flow
        if is_authorized():
            return "<h2>✅ YouTube already authorized!</h2><p>Your pipeline is ready to upload videos automatically.</p>", 200

        # Run auth in background thread so Flask doesn't block
        import threading
        auth_thread = threading.Thread(target=run_auth_flow, daemon=True)
        auth_thread.start()

        return (
            "<h2>YouTube Authorization Started</h2>"
            "<p>A browser window should open automatically asking you to sign in with Google.</p>"
            "<p>If no window opens, check your taskbar or visit "
            "<a href='http://localhost:8090'>http://localhost:8090</a></p>"
            "<p>After approving, refresh <a href='/auth-status'>/auth-status</a> to confirm.</p>"
        ), 200
    except Exception as e:
        logger.error(f"FAIL: Auth flow failed: {e}")
        return f"<h2>Error</h2><pre>{e}</pre>", 500


@app.route('/auth-status', methods=['GET'])
def auth_status():
    """Check if YouTube OAuth is set up."""
    try:
        from uploader import is_authorized
        authorized = is_authorized()
        return jsonify({"youtube_authorized": authorized,
                        "message": "Ready to upload" if authorized else "Visit /auth-youtube to authorize"})
    except Exception as e:
        return jsonify({"youtube_authorized": False, "error": str(e)}), 500


@app.route('/upload_youtube', methods=['POST'])
def upload_youtube():
    """Trigger a YouTube upload for a rendered video."""
    try:
        data = request.json or {}
        video_path = data.get('video_path', str(FINAL_VIDEO_PATH))
        topic = data.get('title', 'New Short')
        category = data.get('category', 'Human Behavior')
        category_id = data.get('category_id', '27')

        from metadata_generator import generate_metadata
        logger.info(f"[YOUTUBE] Generating AI content-appropriate metadata for topic: '{topic}'...")
        meta = generate_metadata(topic, category)

        title = meta.get("title", topic)
        description = meta.get("description", topic)
        tags = meta.get("tags", ["#shorts", "#facts"])

        from uploader import upload_to_youtube, is_authorized
        if not is_authorized():
            return jsonify({
                "status": "error",
                "error": "YouTube not authorized. Visit http://localhost:5001/auth-youtube to authorize."
            }), 401

        result = upload_to_youtube(video_path, title, description, tags, category_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"FAIL: YouTube upload failed: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500


DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1528609697089982494/fv9TUyDcJOxxZn1PxKqw-ac3nBBstahSV2CpFEJi0b9sged8hWikgY6uwV8eViqw9nag"

@app.route('/post-discord-review', methods=['POST'])
def route_post_discord_review():
    """
    Posts the rendered video file directly to Discord Webhook as a playable attachment,
    along with n8n interactive approval/rejection links for mobile review.
    Handles proxy scaling and fallback gracefully.
    """
    try:
        data = request.json or {}
        task_id = data.get('task_id')
        topic = data.get('topic', 'YouTube Short')
        resume_url = data.get('resume_url', '')

        if resume_url and ("localhost" in resume_url or "127.0.0.1" in resume_url):
            import socket
            try:
                local_ip = socket.gethostbyname(socket.gethostname())
                resume_url = resume_url.replace("localhost", local_ip).replace("127.0.0.1", local_ip)
            except Exception:
                pass

        video_path = None
        if task_id:
            with tasks_lock:
                task = tasks.get(task_id)
            if task and task.get("video_path"):
                video_path = Path(task["video_path"])

        if not video_path or not video_path.exists():
            video_path = FINAL_VIDEO_PATH

        if not video_path or not video_path.exists():
            mp4_files = sorted(OUTPUT_DIR.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
            if mp4_files:
                video_path = mp4_files[0]

        if not video_path or not video_path.exists():
            return jsonify({"status": "error", "error": "Video file not found"}), 404

        # Generate a small 540x960 proxy (~3-5MB) so it uploads fast & stays under Discord's 10MB limit
        from shared.discord_review import generate_review_proxy
        temp_proxy = Path(video_path).parent / f"discord_review_{task_id or 'latest'}.mp4"
        target_video = Path(generate_review_proxy(str(video_path), str(temp_proxy)))

        # Format message content with interactive approval links
        message_text = (
            f"🎥 **[CONVO-SHORTS REVIEW REQUIRED]**\n"
            f"Topic: **{topic}**\n\n"
            f"Watch the video attached above & tap an option below to proceed:\n"
            f"🟢 [Approve and Upload to YouTube]({resume_url}?action=approve)\n"
            f"🔴 [Reject and Re-generate]({resume_url}?action=reject)"
        )

        payload = {"content": message_text}

        try:
            with open(target_video, 'rb') as f:
                files = {'file': (target_video.name, f, 'video/mp4')}
                resp = requests.post(DISCORD_WEBHOOK_URL, data={'payload_json': json.dumps(payload)}, files=files)

            if not resp.ok:
                logger.warning(f"[DISCORD] Attachment upload failed ({resp.status_code}): {resp.text}. Falling back to text review message...")
                resp = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        except Exception as upload_err:
            logger.warning(f"[DISCORD] Direct upload failed: {upload_err}. Falling back to text review message...")
            resp = requests.post(DISCORD_WEBHOOK_URL, json=payload)

        if temp_proxy and temp_proxy.exists():
            try:
                temp_proxy.unlink()
            except Exception:
                pass

        if resp.ok:
            logger.info(f"OK: Posted video review for topic '{topic}' to Discord!")
            return jsonify({"status": "success", "message": "Video review posted to Discord."})
        else:
            logger.error(f"FAIL: Discord webhook error ({resp.status_code}): {resp.text}")
            return jsonify({"status": "error", "error": f"Discord response {resp.status_code}: {resp.text}"}), 500

    except Exception as e:
        logger.error(f"FAIL: Direct Discord review posting failed: {e}", exc_info=True)
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/compile-long-form', methods=['POST'])
def route_compile_long_form():
    """
    Endpoint to stitch completed mp4 shorts losslessly into 1 long-form video.
    Expected payload:
    {
        "short_paths": ["/path/to/short1.mp4", "/path/to/short2.mp4", ...],
        "output_name": "compilation_weekly.mp4" (optional)
    }
    """
    try:
        data = request.json or {}
        short_paths = data.get('short_paths', [])
        output_name = data.get('output_name', CFG.get("compilation_output_name", "compilation_weekly.mp4"))
        
        if not short_paths:
            return jsonify({"status": "error", "error": "No short_paths provided"}), 400
            
        output_path = OUTPUT_DIR / output_name
        logger.info(f"Stitching {len(short_paths)} shorts into long-form compilation: {output_path.name}")
        
        compile_long_form(short_paths, str(output_path))
        
        return jsonify({
            "status": "success",
            "output_path": str(output_path),
            "output_name": output_path.name
        })
    except Exception as e:
        logger.error(f"FAIL: Long-form compilation failed: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500



import csv

CSV_PATH = Path(__file__).parent.parent / "files" / "02_resources_and_data" / "Topics_Queue.csv"

@app.route('/get-next-topic', methods=['GET'])
def get_next_topic():
    """Reads the local CSV queue and returns all rows to n8n."""
    try:
        if not CSV_PATH.exists():
            return jsonify({"status": "error", "error": f"CSV queue not found at {CSV_PATH}"}), 404
            
        rows = []
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                row["row_number"] = idx + 2
                rows.append(row)
                
        return jsonify(rows)
    except Exception as e:
        logger.error(f"FAIL: Failed to read CSV queue: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/mark-done', methods=['POST'])
def mark_done():
    """Updates the status column for a given topic in the local CSV queue."""
    try:
        data = request.json or {}
        topic = data.get('topic', '')
        status = data.get('status', 'DONE')
        youtube_url = data.get('youtube_url', '')
        
        if not topic:
            return jsonify({"status": "error", "error": "No topic provided"}), 400
            
        if not CSV_PATH.exists():
            return jsonify({"status": "error", "error": "CSV queue file not found"}), 404
            
        rows = []
        headers = []
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
            f.seek(0)
            dict_reader = csv.DictReader(f)
            rows = list(dict_reader)
            
        updated = False
        for row in rows:
            if row.get("Topic") == topic:
                row["Video Status"] = status
                if youtube_url:
                    row["YouTube URL"] = youtube_url
                updated = True
                
        if not updated:
            for row in rows:
                if topic in row.get("Topic", "") or row.get("Topic", "") in topic:
                    row["Video Status"] = status
                    if youtube_url:
                        row["YouTube URL"] = youtube_url
                    updated = True
                    break
                    
        if updated:
            with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)
            logger.info(f"OK: Marked topic as done: '{topic}'")
            return jsonify({"status": "success", "message": f"Topic '{topic}' updated successfully."})
        else:
            return jsonify({"status": "error", "error": f"Topic '{topic}' not found in CSV"}), 404
            
    except Exception as e:
        logger.error(f"FAIL: Failed to update CSV status: {e}")
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

@app.route('/create-job', methods=['POST'])
def route_create_job():
    """Stage 1: Create Job and Generate Script."""
    try:
        data = request.json or {}
        topic = data.get("topic")
        category = data.get("category", "Tech")
        if not topic:
            return jsonify({"status": "error", "error": "No topic provided"}), 400
            
        job_id = str(uuid.uuid4())
        script_data = generate_script(topic, category)
        
        # Save script.json in job folder
        job_folder = OUTPUT_DIR / job_id
        job_folder.mkdir(parents=True, exist_ok=True)
        script_path = job_folder / "script.json"
        with open(script_path, "w", encoding="utf-8") as f:
            json.dump(script_data, f, indent=2, ensure_ascii=False)
            
        return jsonify({
            "status": "success",
            "job_id": job_id,
            "script": script_data
        })
    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/generate-audio', methods=['POST'])
def route_generate_audio():
    """Stage 2: Piper TTS Voice Generation with duration logging."""
    try:
        data = request.json or {}
        job_id = data.get("job_id")
        voice = data.get("voice", "en-US-BrianNeural")
        
        if not job_id:
            return jsonify({"status": "error", "error": "No job_id provided"}), 400
            
        job_folder = OUTPUT_DIR / job_id
        script_path = job_folder / "script.json"
        if not script_path.exists():
            return jsonify({"status": "error", "error": "Job not found"}), 404
            
        with open(script_path, "r", encoding="utf-8") as f:
            script_data = json.load(f)
            
        # Run audio generation and timings alignment
        audio_output = str(job_folder / "audio.wav")
        sped_audio, timings = generate_voiceover(script_data.get("lines", []), audio_output, voice=voice)
        
        # Save updated script with durations
        with open(script_path, "w", encoding="utf-8") as f:
            json.dump(script_data, f, indent=2, ensure_ascii=False)
            
        # Cache timings to a separate json file for easier reference
        timings_path = job_folder / "timings.json"
        with open(timings_path, "w", encoding="utf-8") as f:
            json.dump(timings, f, indent=2)
            
        return jsonify({
            "status": "success",
            "sped_audio_path": sped_audio,
            "timings": timings,
            "script": script_data
        })
    except Exception as e:
        logger.error(f"Failed to generate audio for job {job_id}: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/generate-images', methods=['POST'])
def route_generate_images():
    """Stage 3: Fooocus Image Generation for each segment."""
    try:
        data = request.json or {}
        job_id = data.get("job_id")
        
        if not job_id:
            return jsonify({"status": "error", "error": "No job_id provided"}), 400
            
        job_folder = OUTPUT_DIR / job_id
        script_path = job_folder / "script.json"
        if not script_path.exists():
            return jsonify({"status": "error", "error": "Job not found"}), 404
            
        with open(script_path, "r", encoding="utf-8") as f:
            script_data = json.load(f)
            
        segments = script_data.get("segments", [])
        images_dir = job_folder / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        generated_paths = {}
        for seg in segments:
            seg_id = seg.get("segment_id")
            prompt = seg.get("visual_topic_prompt")
            target_path = images_dir / f"{seg_id}.png"
            
            img_path = generate_fooocus_image(prompt, str(target_path))
            seg["image_path"] = img_path
            generated_paths[seg_id] = img_path
            
        # Update lines with image path too for ease of assembly overlay mapping
        for line in script_data.get("lines", []):
            seg_id = line.get("segment_id")
            line["image_path"] = generated_paths.get(seg_id)
            
        # Save updated script
        with open(script_path, "w", encoding="utf-8") as f:
            json.dump(script_data, f, indent=2, ensure_ascii=False)
            
        return jsonify({
            "status": "success",
            "images": generated_paths,
            "script": script_data
        })
    except Exception as e:
        logger.error(f"Failed to generate images for job {job_id}: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/assemble-video', methods=['POST'])
def route_assemble_video():
    """Stage 4: Video assembly with split-screen, captions, sidechain ducking."""
    try:
        data = request.json or {}
        job_id = data.get("job_id")
        category = data.get("category", "Tech")
        
        if not job_id:
            return jsonify({"status": "error", "error": "No job_id provided"}), 400
            
        job_folder = OUTPUT_DIR / job_id
        script_path = job_folder / "script.json"
        if not script_path.exists():
            return jsonify({"status": "error", "error": "Job not found"}), 404
            
        with open(script_path, "r", encoding="utf-8") as f:
            script_data = json.load(f)
            
        timings_path = job_folder / "timings.json"
        if not timings_path.exists():
            return jsonify({"status": "error", "error": "Timings not found. Generate audio first."}), 400
        with open(timings_path, "r", encoding="utf-8") as f:
            timings = json.load(f)
            
        audio_path = str(job_folder / "audio_sped.wav")
        video_out = str(job_folder / f"{job_id}_final.mp4")
        
        # Build subtitle data structures expected by assemble_video
        # We need Whisper word-level timestamps. Let's transcribe the generated audio track.
        logger.info(f"[{job_id}] Running Whisper word alignment...")
        subtitle_data = generate_subtitles(audio_path, timings=timings)
        
        # Build visual proofs (images) mapped to their segments
        visual_proofs = []
        for line in script_data.get("lines", []):
            visual_proofs.append(line.get("image_path"))
            
        # Select background gameplay footage clip
        bg_path = pick_background(required_duration=subtitle_data["duration"], is_debate=True)
        
        logger.info(f"[{job_id}] Assembling split-screen short...")
        assemble_video(
            video_bg_path=bg_path,
            audio_path=audio_path,
            subtitle_data=subtitle_data,
            final_output_path=video_out,
            category=category,
            visual_proofs=visual_proofs,
            timings=timings
        )
        
        # Cache final video info
        with tasks_lock:
            tasks[job_id] = {
                "status": "success",
                "video_path": video_out,
                "duration": subtitle_data["duration"],
                "error": None
            }
            _save_tasks(tasks)
            
        return jsonify({
            "status": "success",
            "video_path": video_out,
            "duration": subtitle_data["duration"]
        })
    except Exception as e:
        logger.error(f"Failed to assemble video for job {job_id}: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/generate-metadata', methods=['POST'])
def route_generate_metadata():
    """Stage 5: Generate Title, Description, Tags, and Pillow Title Card."""
    try:
        data = request.json or {}
        job_id = data.get("job_id")
        category = data.get("category", "Tech")
        
        if not job_id:
            return jsonify({"status": "error", "error": "No job_id provided"}), 400
            
        job_folder = OUTPUT_DIR / job_id
        script_path = job_folder / "script.json"
        if not script_path.exists():
            return jsonify({"status": "error", "error": "Job not found"}), 404
            
        with open(script_path, "r", encoding="utf-8") as f:
            script_data = json.load(f)
            
        debate_question = script_data.get("title", "Debate Topic")
        
        # Generate Pillow title card thumbnail
        thumbnail_out = str(job_folder / "thumbnail.jpg")
        generate_debate_thumbnail(debate_question, thumbnail_out)
        
        # Generate YouTube metadata
        meta = generate_metadata(debate_question, category)
        meta["thumbnail_path"] = thumbnail_out
        
        # Save metadata to JSON
        meta_path = job_folder / "metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
            
        return jsonify({
            "status": "success",
            "metadata": meta
        })
    except Exception as e:
        logger.error(f"Failed to generate metadata for job {job_id}: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/discord-post-review', methods=['POST'])
def route_discord_post_review():
    """Post image list or video to Discord webhook for review."""
    try:
        data = request.json or {}
        job_id = data.get("job_id")
        media_type = data.get("media_type") # "image" or "video"
        webhook_url = data.get("webhook_url")
        
        if not job_id or not media_type or not webhook_url:
            return jsonify({"status": "error", "error": "Missing parameters (job_id, media_type, webhook_url)"}), 400
            
        job_folder = OUTPUT_DIR / job_id
        
        if media_type == "video":
            video_path = str(job_folder / f"{job_id}_final.mp4")
            success = post_for_review("convo-shorts", job_id, [video_path], "video", webhook_url)
        elif media_type == "image":
            script_path = job_folder / "script.json"
            with open(script_path, "r", encoding="utf-8") as f:
                script_data = json.load(f)
            segments = script_data.get("segments", [])
            media_paths = [(seg.get("segment_id"), seg.get("image_path")) for seg in segments]
            success = post_for_review("convo-shorts", job_id, media_paths, "image", webhook_url)
        else:
            return jsonify({"status": "error", "error": "Invalid media_type"}), 400
            
        return jsonify({"status": "success" if success else "error"})
    except Exception as e:
        logger.error(f"Discord post review failed: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/discord-parse-reply', methods=['POST'])
def route_discord_parse_reply():
    """Parses raw text reply message into structured JSON actions."""
    try:
        data = request.json or {}
        message_text = data.get("message_text", "")
        parsed = parse_discord_reply(message_text)
        return jsonify(parsed)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/regenerate-asset', methods=['POST'])
def route_regenerate_asset():
    """Regenerates a single segment image using Fooocus."""
    try:
        data = request.json or {}
        job_id = data.get("job_id")
        segment_id = data.get("segment_id")
        prompt = data.get("prompt")
        
        if not job_id or not segment_id:
            return jsonify({"status": "error", "error": "Missing job_id or segment_id"}), 400
            
        # We invoke regenerate_segment_image directly from regenerate_asset module
        from regenerate_asset import regenerate_segment_image
        success = regenerate_segment_image(job_id, segment_id, prompt)
        return jsonify({"status": "success" if success else "error"})
    except Exception as e:
        logger.error(f"Asset regeneration failed: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    logger.info(f"[START] Flask Server starting on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)
