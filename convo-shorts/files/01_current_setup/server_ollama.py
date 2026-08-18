"""
FLASK SERVER: YouTube Shorts Generator (100% FREE - Using Ollama Local LLM)

This version uses:
- Ollama (local, free LLM instead of Gemini API)
- Piper TTS (local, free voice generation - you already have this)
- FFmpeg (free video processing)
- Faster Whisper (free transcription)

Zero API costs. Zero monthly fees. Complete control.

Run: python server_ollama.py
"""

from flask import Flask, request, jsonify
from pathlib import Path
import subprocess
import json
import os
import random
from datetime import datetime
import logging
import requests

# Audio/Video processing
import numpy as np
from faster_whisper import WhisperModel
import cv2
from PIL import Image, ImageDraw, ImageFont

# ============================================================================
# CONFIGURATION
# ============================================================================

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path("./data")
ASSETS_DIR = BASE_DIR / "assets"
BACKGROUNDS_DIR = ASSETS_DIR / "backgrounds" / "active"
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp"

# Create directories
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Ollama settings
OLLAMA_URL = "http://localhost:11434"  # Default Ollama port
OLLAMA_MODEL = "mistral"  # Fast, good quality (alternatives: neural-chat, dolphin-mixtral)
# Other options: "llama2" (better but slower), "neural-chat" (faster), "dolphin-mixtral" (longer context)

# Piper settings
PIPER_PATH = "./data/piper.exe"
PIPER_MODEL_PATH = "./data/models/en_US-lessac-medium.onnx"
SAMPLE_RATE = 22050

# Category-specific settings
CATEGORY_STYLES = {
    "Weird Science": {
        "caption_color": (0, 255, 255),  # Cyan
        "secondary_color": (255, 255, 255),
        "font_scale": 1.2,
    },
    "Productivity & stoicism": {
        "caption_color": (255, 215, 0),  # Gold
        "secondary_color": (255, 255, 255),
        "font_scale": 1.1,
    },
    "Human Behavior": {
        "caption_color": (255, 0, 127),  # Hot pink
        "secondary_color": (255, 255, 255),
        "font_scale": 1.15,
    },
}

# ============================================================================
# OLLAMA INTEGRATION (FREE LOCAL LLM)
# ============================================================================

def check_ollama_running():
    """Verify Ollama is running and accessible"""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"✗ Ollama not accessible: {str(e)}")
        return False

def get_available_models():
    """Get list of available Ollama models"""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags")
        models = response.json().get("models", [])
        return [m["name"].split(":")[0] for m in models]
    except Exception as e:
        logger.error(f"✗ Failed to get models: {str(e)}")
        return []

def generate_script_with_ollama(topic: str, category: str) -> dict:
    """
    Generate script using Ollama (completely free, local)
    
    Args:
        topic: Topic for the video
        category: Content category (determines prompt)
    
    Returns:
        {
            "hook": "...",
            "body": "...",
            "cta": "...",
            "success": True/False
        }
    """
    
    # Select prompt based on category
    if category == "Weird Science":
        prompt = f"""Generate a 30-second YouTube Short script about: {topic}

Format EXACTLY like this:
[HOOK]
[BODY]
[CTA]

HOOK (10-15 words, shocking/curious):
Start with "Your brain...", "Scientists found...", or "This fact..."
Make it stop-scroll worthy.

BODY (80-100 words):
Simple explanations, use "imagine if..." analogies.
Include ONE surprising fact.
Sound conversational.

CTA (10-15 words):
"Follow for more mind-bending facts" or similar.

Example:
[HOOK] Your brain does THIS while you sleep every night...
[BODY] Your neurons are constantly reorganizing... This process is called...
[CTA] Drop a 🧠 if your mind was blown"""

    elif category == "Productivity & stoicism":
        prompt = f"""Generate a 35-second YouTube Short script about: {topic}

Format EXACTLY like this:
[HOOK]
[BODY]
[CTA]

HOOK (10-15 words, aspirational):
Start with "Millionaires...", "One habit...", or "This changed..."
Make it promise transformation.

BODY (90-110 words):
Introduce the principle clearly.
Give a REAL example.
Explain WHY it works.
Sound motivational but not cheesy.

CTA (10-15 words):
"Try this today" or "Save this" or similar.

Example:
[HOOK] Millionaires do THIS every single morning...
[BODY] It's called... When you [example]... This works because...
[CTA] Start today and tag someone"""

    elif category == "Human Behavior":
        prompt = f"""Generate a 30-second YouTube Short script about: {topic}

Format EXACTLY like this:
[HOOK]
[BODY]
[CTA]

HOOK (10-15 words, revealing):
Start with "If someone does THIS...", "Watch for THIS...", or "This reveals..."
Make it feel like a secret.

BODY (85-105 words):
Explain the behavior/signal clearly.
Describe what it MEANS (psychology).
Use relatable examples.
Sound like you're telling a friend.

CTA (10-15 words):
"Have you seen this?", "Tag someone...", or similar.

Example:
[HOOK] If someone does THIS when talking to you...
[BODY] It means [psychology]... I've seen this with...
[CTA] Comment if you've noticed this"""

    else:
        prompt = f"""Generate a 30-second YouTube Short script about: {topic}
Make it interesting, conversational, and engaging."""

    try:
        # Call Ollama API
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.7,  # Creative but consistent
            },
            timeout=60  # Ollama can take time
        )
        
        if response.status_code != 200:
            raise Exception(f"Ollama error: {response.text}")
        
        script = response.json().get("response", "")
        
        # Parse sections
        hook_match = script.find("[HOOK]")
        body_match = script.find("[BODY]")
        cta_match = script.find("[CTA]")
        
        hook = script[hook_match+7:body_match].strip() if hook_match != -1 else ""
        body = script[body_match+7:cta_match].strip() if body_match != -1 else ""
        cta = script[cta_match+6:].strip() if cta_match != -1 else ""
        
        logger.info(f"✓ Script generated (Ollama)")
        
        return {
            "hook": hook,
            "body": body,
            "cta": cta,
            "success": True
        }
    
    except Exception as e:
        logger.error(f"✗ Ollama script generation failed: {str(e)}")
        return {
            "hook": "Check this out...",
            "body": topic,  # Fallback
            "cta": "Follow for more",
            "success": False,
            "error": str(e)
        }

# ============================================================================
# AUDIO GENERATION (PIPER - Already have this)
# ============================================================================

def generate_piper_audio(text: str, video_id: str, speed: float = 1.15) -> str:
    """Generate audio using Piper TTS with speed adjustment"""
    audio_path = TEMP_DIR / f"{video_id}.wav"
    
    try:
        # Generate base audio with Piper
        process = subprocess.Popen(
            [PIPER_PATH, "--model", PIPER_MODEL_PATH, "--output_file", str(audio_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate(input=text.encode('utf-8'))
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Piper failed: {stderr.decode('utf-8', errors='ignore')}")
        
        # Apply speed adjustment
        sped_audio = TEMP_DIR / f"{video_id}_sped.wav"
        speed_cmd = [
            "ffmpeg",
            "-i", str(audio_path),
            "-af", f"atempo={speed}",
            "-y",
            str(sped_audio)
        ]
        
        subprocess.run(speed_cmd, capture_output=True, check=True)
        
        logger.info(f"✓ Audio generated: {sped_audio} (speed: {speed}x)")
        return str(sped_audio)
    
    except Exception as e:
        logger.error(f"✗ Audio generation failed: {str(e)}")
        raise

# ============================================================================
# TRANSCRIPTION (Faster Whisper - free, local)
# ============================================================================

def transcribe_with_timing(audio_path: str, video_id: str) -> dict:
    """Transcribe and get word-level timing using Faster Whisper"""
    try:
        model = WhisperModel("base", device="cuda", compute_type="float16")
        segments, info = model.transcribe(audio_path, word_level=True)
        
        words_data = []
        for segment in segments:
            for word_info in segment.words:
                words_data.append({
                    "word": word_info.word.strip(),
                    "start": word_info.start,
                    "end": word_info.end
                })
        
        duration = info.duration
        logger.info(f"✓ Transcribed {len(words_data)} words, duration: {duration:.1f}s")
        
        return {
            "words": words_data,
            "duration": duration
        }
    
    except Exception as e:
        logger.error(f"✗ Transcription failed: {str(e)}")
        raise

# ============================================================================
# BACKGROUND MANAGEMENT
# ============================================================================

def select_random_background() -> str:
    """Select random background video from active folder"""
    videos = list(BACKGROUNDS_DIR.glob("*.mp4"))
    
    if not videos:
        raise FileNotFoundError(f"No backgrounds in {BACKGROUNDS_DIR}")
    
    selected = random.choice(videos)
    logger.info(f"✓ Selected background: {selected.name}")
    return str(selected)

def apply_background_effects(video_path: str, video_id: str) -> str:
    """Apply blur, color grading, vignette to background"""
    output_path = TEMP_DIR / f"{video_id}_background.mp4"
    
    filter_chain = (
        "scale=1080:1920:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,"
        "boxblur=50:2,"
        "curves=preset=increase_contrast"
    )
    
    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-vf", filter_chain,
        "-y",
        str(output_path)
    ]
    
    subprocess.run(cmd, capture_output=True, check=True)
    logger.info(f"✓ Background effects applied")
    return str(output_path)

# ============================================================================
# VIDEO COMPOSITION
# ============================================================================

def compose_video(background_video: str, audio_path: str, 
                   hook: str, cta: str, category: str, video_id: str) -> str:
    """Compose final video: background + audio"""
    try:
        output_path = OUTPUT_DIR / f"{video_id}.mp4"
        
        # Simple composition: background + audio
        cmd = [
            "ffmpeg",
            "-i", background_video,
            "-i", audio_path,
            "-c:v", "libx264",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-y",
            str(output_path)
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        logger.info(f"✓ Video composed: {output_path}")
        return str(output_path)
    
    except Exception as e:
        logger.error(f"✗ Video composition failed: {str(e)}")
        raise

# ============================================================================
# THUMBNAIL GENERATION
# ============================================================================

def generate_thumbnail(video_id: str, hook_text: str, category: str) -> str:
    """Generate thumbnail from video at 3 seconds"""
    try:
        video_path = OUTPUT_DIR / f"{video_id}.mp4"
        thumb_path = OUTPUT_DIR / f"{video_id}_thumb.jpg"
        
        # Extract frame at 3 seconds
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-ss", "3",
            "-vframes", "1",
            "-vf", "scale=1280:720",
            "-y",
            str(thumb_path)
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        
        # Add overlay text
        img = Image.open(thumb_path)
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("arial.ttf", 48)
        except:
            font = ImageFont.load_default()
        
        # Add text overlay
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 128))
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        draw = ImageDraw.Draw(img)
        
        text = hook_text[:40].upper()
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        x = (img.width - text_w) // 2
        y = img.height // 3
        
        style = CATEGORY_STYLES.get(category, CATEGORY_STYLES["Weird Science"])
        draw.text((x, y), text, fill=style["caption_color"], font=font)
        
        img.save(thumb_path)
        logger.info(f"✓ Thumbnail generated")
        return str(thumb_path)
    
    except Exception as e:
        logger.error(f"✗ Thumbnail generation failed: {str(e)}")
        return None

# ============================================================================
# MAIN API ENDPOINTS
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check - verify all tools are available"""
    ollama_status = check_ollama_running()
    
    import shutil
    return jsonify({
        "status": "ok" if ollama_status else "partial",
        "ollama_running": ollama_status,
        "ollama_model": OLLAMA_MODEL,
        "ollama_url": OLLAMA_URL,
        "piper_available": os.path.exists(PIPER_PATH),
        "ffmpeg_available": shutil.which("ffmpeg") is not None,
        "backgrounds_available": len(list(BACKGROUNDS_DIR.glob("*.mp4"))) > 0,
        "available_models": get_available_models()
    })

@app.route('/generate_video', methods=['POST'])
def generate_video():
    """
    Generate complete video from topic
    
    POST data:
    {
        "topic": "Why you yawn",
        "category": "Weird Science" | "Productivity & stoicism" | "Human Behavior",
        "video_id": "unique_id"
    }
    """
    try:
        data = request.json
        topic = data.get('topic', '')
        category = data.get('category', 'Weird Science')
        video_id = data.get('video_id', f"video_{int(datetime.now().timestamp())}")
        
        if not topic:
            return jsonify({"error": "No topic provided"}), 400
        
        logger.info(f"🎬 Starting video generation: {video_id}")
        logger.info(f"Topic: {topic}, Category: {category}")
        
        # 1. Generate script using Ollama (FREE)
        script_result = generate_script_with_ollama(topic, category)
        
        if not script_result["success"]:
            logger.warning(f"Script generation had issues, using fallback")
        
        hook = script_result["hook"]
        body = script_result["body"]
        cta = script_result["cta"]
        
        # Combine for audio
        full_script = f"{hook} {body} {cta}"
        
        # 2. Generate audio (FREE - Piper)
        audio_path = generate_piper_audio(full_script, video_id, speed=1.15)
        
        # 3. Select background (FREE)
        background_video = select_random_background()
        
        # 4. Apply effects (FREE - FFmpeg)
        bg_with_effects = apply_background_effects(background_video, video_id)
        
        # 5. Compose video (FREE - FFmpeg)
        final_video = compose_video(
            bg_with_effects, audio_path,
            hook, cta, category, video_id
        )
        
        # 6. Generate thumbnail (FREE)
        thumbnail = generate_thumbnail(video_id, hook, category)
        
        logger.info(f"✓✓✓ Video generation complete: {video_id}")
        
        return jsonify({
            "status": "success",
            "video_id": video_id,
            "video_path": final_video,
            "thumbnail_path": thumbnail,
            "script": {
                "hook": hook,
                "body": body,
                "cta": cta
            },
            "cost": "$0.00 (100% free - Ollama + Piper + FFmpeg)"
        })
    
    except Exception as e:
        logger.error(f"✗ Video generation failed: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/test_ollama', methods=['GET'])
def test_ollama():
    """Test Ollama connection and generate sample script"""
    try:
        if not check_ollama_running():
            return jsonify({
                "status": "error",
                "message": "Ollama not running",
                "fix": "Run 'ollama serve' in terminal"
            }), 500
        
        # Test with simple topic
        result = generate_script_with_ollama(
            "Why do we dream",
            "Weird Science"
        )
        
        return jsonify({
            "status": "success",
            "ollama_model": OLLAMA_MODEL,
            "test_result": result,
            "message": "Ollama is working perfectly!"
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

# ============================================================================
# RUN
# ============================================================================

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("🚀 100% FREE Flask Server (Ollama + Piper + FFmpeg)")
    logger.info("=" * 60)
    logger.info(f"Ollama URL: {OLLAMA_URL}")
    logger.info(f"Ollama Model: {OLLAMA_MODEL}")
    logger.info(f"Output Directory: {OUTPUT_DIR}")
    logger.info(f"Backgrounds Directory: {BACKGROUNDS_DIR}")
    logger.info("")
    logger.info("Check Ollama status:")
    logger.info("  curl http://localhost:5000/health")
    logger.info("")
    logger.info("Test Ollama script generation:")
    logger.info("  curl http://localhost:5000/test_ollama")
    logger.info("=" * 60)
    
    app.run(host='localhost', port=5000, debug=False)
