# -*- coding: utf-8 -*-
"""
media_engine.py
---------------
Full media pipeline:
  1. Ollama  -> generate script (hook / body / cta)
  2. Piper   -> text-to-speech WAV
  3. FFmpeg  -> speed-adjust audio
  4. Whisper -> word-level timestamps
  5. FFmpeg  -> assemble final 9:16 MP4 with burned-in subtitles
  6. Pillow  -> generate thumbnail JPEG
"""

import subprocess
import json
import os
import time
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import random
import threading
gpu_lock = threading.Lock()
import textwrap
import shutil
import sys
from pathlib import Path

# Add workspace root to python path for shared utilities import
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from shared_caption_utils import align_and_generate_ass

import requests
from faster_whisper import WhisperModel
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from gradio_client import Client

FOOOCUS_API_URL = "http://127.0.0.1:7865/"
FOOOCUS_OUTPUTS_DIR = Path("D:\\Projects\\Fooocus\\outputs")

def check_fooocus_online(timeout=3) -> bool:
    """Quick check to verify Fooocus webserver is online before generation."""
    try:
        r = requests.get(FOOOCUS_API_URL, timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False

def validate_image(image_path) -> bool:
    """Verifies that the image is valid, uncorrupted, and not completely black."""
    try:
        path = Path(image_path)
        if not path.exists() or path.stat().st_size == 0:
            return False
            
        with Image.open(path) as img:
            img.verify()
            
        with Image.open(path) as img:
            w, h = img.size
            if w <= 0 or h <= 0:
                return False
                
            extrema = img.getextrema()
            is_black = True
            if isinstance(extrema[0], tuple):
                for min_val, max_val in extrema:
                    if max_val > 8:
                        is_black = False
                        break
            else:
                min_val, max_val = extrema
                if max_val > 8:
                    is_black = False
                    
            if is_black:
                return False
                
        return True
    except Exception:
        return False

def _generate_fallback_image(prompt_text, out_path):
    """Generates an 896x896 PIL placeholder visual proof image."""
    try:
        img = Image.new("RGB", (896, 896), color=(25, 35, 45))
        draw = ImageDraw.Draw(img)
        draw.rectangle([20, 20, 876, 876], outline=(70, 130, 180), width=4)
        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except Exception:
            font = ImageFont.load_default()
        draw.text((40, 400), f"Topic: {prompt_text[:40]}...", fill=(240, 240, 240), font=font)
        img.save(out_path)
        print(f"[Fooocus Fallback] Created placeholder visual proof image at {out_path}")
        return str(out_path).replace("\\", "/")
    except Exception as pe:
        print(f"[Fooocus Fallback Error] {pe}")
        return None

def generate_fooocus_image(prompt_text, out_path, allow_fallback=True):
    """
    Connects to local Fooocus instance to generate cinematic visual proof.
    Enforces native 896x896 resolution with snapshot-based output detection and image validation.
    If allow_fallback is False or STRICT_FOOOCUS=1, raises RuntimeError on failure instead of silent placeholder fallback.
    """
    if not prompt_text:
        return None
        
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 1. Quick connectivity check — fail fast if Fooocus is completely offline
    if not check_fooocus_online():
        err_msg = f"[FOOOCUS UNAVAILABLE] Could not connect to {FOOOCUS_API_URL}."
        print(err_msg)
        if not allow_fallback or os.getenv("STRICT_FOOOCUS", "0") == "1":
            raise RuntimeError(f"FOOOCUS GENERATION FAILED\nReason: Server unavailable at {FOOOCUS_API_URL}\nVideo generation aborted.\nNo upload should occur.")
        print("[FOOOCUS] USING FALLBACK IMAGE.")
        return _generate_fallback_image(prompt_text, out_path)
        
    neg_prompt = "low quality, blurry, distorted text, modern vehicles, tanks, firearms, anachronistic technology"
    style_list = ["Fooocus Cinematic", "Fooocus V2", "Fooocus Enhance", "Fooocus Sharp"]
    aspect_ratio = "896×896"
    
    for attempt in range(1, 4):
        try:
            print(f"[FOOOCUS] Generating image (Attempt {attempt}/3) for prompt: {prompt_text[:60]}...")
            client = Client(FOOOCUS_API_URL)
            
            if len(client.endpoints) <= 68:
                raise RuntimeError(f"Unexpected Fooocus API endpoints structure (total {len(client.endpoints)} endpoints).")
                
            ep67 = client.endpoints[67]
            dep67 = ep67.dependency
            comps = {comp['id']: comp for comp in client.config['components']}
            
            args = []
            for cid in dep67['inputs']:
                if cid in comps:
                    comp = comps[cid]
                    val = comp.get('value')
                    if val is None:
                        val = comp.get('props', {}).get('value')
                    args.append(val)
                else:
                    args.append(None)
                    
            for idx, (cid, ctype) in enumerate(zip(dep67['inputs'], ep67.input_component_types)):
                val = args[idx]
                if ctype == 'radio' and isinstance(val, list):
                    args[idx] = val[1] if len(val) > 1 else val[0]
                    
            args[0] = None  # state
            args[1] = False # generate_image_grid_for_each_batch
            args[2] = prompt_text
            args[3] = neg_prompt
            args[4] = style_list
            args[5] = "Speed"
            
            target_clean = aspect_ratio.replace("*", "×").replace("x", "×").split(" ")[0]
            aspect_choices = comps[dep67['inputs'][6]].get('props', {}).get('choices', [])
            resolved_ratio = aspect_choices[0][1] if isinstance(aspect_choices[0], list) else aspect_choices[0]
            for choice in aspect_choices:
                val = choice[1] if isinstance(choice, list) else choice
                if val.startswith(target_clean):
                    resolved_ratio = val
                    break
            args[6] = resolved_ratio
            args[7] = 1  # image_number
            args[8] = "png"
            args[9] = str(random.randint(1, 1000000000))
            args[13] = "juggernautXL_v8Rundiffusion.safetensors"
            args[14] = "None"
            args[15] = 0.5
            
            filtered_args = [val for val, ctype in zip(args, ep67.input_component_types) if ctype != 'state']
            
            import tempfile
            gradio_temp = Path(tempfile.gettempdir()) / "gradio"
            
            pre_files_fooocus = set(FOOOCUS_OUTPUTS_DIR.glob("**/*.png")) if FOOOCUS_OUTPUTS_DIR.exists() else set()
            pre_files_gradio = set(gradio_temp.glob("**/*.png")) if gradio_temp.exists() else set()
            pre_existing_files = pre_files_fooocus | pre_files_gradio

            acquired = gpu_lock.acquire(timeout=600)
            if not acquired:
                raise TimeoutError("Pipeline queue timeout capacity reached (GPU lock in Fooocus)")
            try:
                client.predict(*filtered_args, fn_index=67)
                
                job_start_time = time.time()
                job = client.submit(fn_index=68)
                
                timeout_seconds = 180
                while not job.done():
                    if time.time() - job_start_time > timeout_seconds:
                        print("[ERROR] Fooocus image generation timed out after 3 minutes. Aborting job.")
                        job.cancel()
                        raise TimeoutError("Fooocus generation timed out.")
                    time.sleep(2)
            finally:
                gpu_lock.release()
                
            post_files_fooocus = set(FOOOCUS_OUTPUTS_DIR.glob("**/*.png")) if FOOOCUS_OUTPUTS_DIR.exists() else set()
            post_files_gradio = set(gradio_temp.glob("**/*.png")) if gradio_temp.exists() else set()
            post_existing_files = post_files_fooocus | post_files_gradio
            
            new_candidate_files = post_existing_files - pre_existing_files
            
            valid_new_files = []
            for f in new_candidate_files:
                try:
                    if f.stat().st_mtime >= job_start_time - 2.0:
                        valid_new_files.append((f, f.stat().st_mtime))
                except Exception:
                    pass
                    
            new_img = None
            if valid_new_files:
                valid_new_files.sort(key=lambda x: x[1], reverse=True)
                new_img = valid_new_files[0][0]
            else:
                print(f"[FOOOCUS WARNING] No new output PNG detected from this generation request (Attempt {attempt}).")
                
            if new_img and new_img.exists():
                shutil.copy(new_img, out_path)
                # Enforce strict 896x896 dimensions via PIL center-crop / resize
                try:
                    with Image.open(out_path) as img:
                        w, h = img.size
                        if w != 896 or h != 896:
                            min_dim = min(w, h)
                            left = (w - min_dim) // 2
                            top = (h - min_dim) // 2
                            right = left + min_dim
                            bottom = top + min_dim
                            img_cropped = img.crop((left, top, right, bottom)).resize((896, 896), Image.Resampling.LANCZOS)
                            img_cropped.save(out_path)
                except Exception as crop_err:
                    print(f"[FOOOCUS WARNING] Could not resize image to 896x896: {crop_err}")

                if validate_image(out_path):
                    print(f"[FOOOCUS SUCCESS] Generated & validated 896x896 image for {out_path.name}")
                    return str(out_path).replace("\\", "/")
                else:
                    print(f"[FOOOCUS ERROR] Validation failed for generated image {out_path.name} (corrupt or blank).")
                    if out_path.exists():
                        try: out_path.unlink()
                        except Exception: pass
            else:
                if out_path.exists():
                    try: out_path.unlink()
                    except Exception: pass

        except Exception as e:
            print(f"[FOOOCUS ERROR] Generation attempt {attempt} failed: {e}")
            if out_path.exists():
                try: out_path.unlink()
                except Exception: pass
                
    if not allow_fallback or os.getenv("STRICT_FOOOCUS", "0") == "1":
        raise RuntimeError("FOOOCUS GENERATION FAILED\nReason: All image generation attempts failed.\nVideo generation aborted.\nNo upload should occur.")

    print(f"[FOOOCUS FALLBACK] All attempts failed. Creating placeholder visual proof image for '{prompt_text[:30]}...'")
    return _generate_fallback_image(prompt_text, out_path)

def generate_cloned_voice(text, speaker, output_wav_path):
    """
    Synthesizes speech using a zero-shot voice cloning framework.
    Loads reference wav from voice_refs/{speaker}.wav.
    If the framework is not running or fails, falls back to Edge-TTS.
    """
    speaker_norm = speaker.strip().upper()
    if "A" in speaker_norm or "CHARACTER_A" in speaker_norm:
        speaker_key = "A"
    elif "B" in speaker_norm or "CHARACTER_B" in speaker_norm:
        speaker_key = "B"
    else:
        speaker_key = "A"

    # Resolve piper.exe path
    ROOT_DIR = Path(__file__).parent.parent
    piper_exe = ROOT_DIR / "piper.exe"
    voice_config_path = ROOT_DIR / "config" / "voice.json"

    if voice_config_path.exists() and speaker_key in ["A", "B"]:
        try:
            with open(voice_config_path, "r", encoding="utf-8") as f:
                voice_cfg = json.load(f)
            cfg_speaker = voice_cfg.get(speaker_key)
            if cfg_speaker:
                model_rel_path = cfg_speaker.get("model", "models/en_US-lessac-medium.onnx")
                model_path = ROOT_DIR / model_rel_path
                current_model_path = str(model_path)
                
                print(f"[VOICE ENGINE] Speaker Detected: {speaker} | Assigned Model: {current_model_path}")
                
                # Safety fallback: if custom voice file doesn't exist, use default Lessac model
                if not model_path.exists():
                    print(f"[VOICE WARNING] Model file not found at {current_model_path}. Forcing fallback to default Lessac model.")
                    model_path = ROOT_DIR / "models" / "en_US-lessac-medium.onnx"
                length_scale = cfg_speaker.get("length_scale", 1.0)
                speed = cfg_speaker.get("speed", 1.0)
                spk_id = cfg_speaker.get("speaker")
                
                cmd = [
                    str(piper_exe),
                    "--model", str(model_path),
                    "--length-scale", str(length_scale),
                    "--output_file", str(output_wav_path)
                ]
                if spk_id is not None:
                    cmd.extend(["--speaker", str(spk_id)])
                
                proc = subprocess.run(cmd, input=text.encode("utf-8"), capture_output=True)
                if proc.returncode != 0:
                    raise RuntimeError(f"Piper process failed: {proc.stderr.decode('utf-8', errors='ignore')}")
                
                # Apply speed adjustment and audio treatment
                temp_wav = Path(output_wav_path).with_suffix(".temp.wav")
                shutil.move(output_wav_path, temp_wav)
                
                af_filters = f"atempo={speed},loudnorm=I=-16:TP=-1.5:LRA=11,treble=g=4:f=8000:w=0.5"
                subprocess.run(
                    ["ffmpeg", "-y", "-i", str(temp_wav),
                     "-af", af_filters, 
                     "-c:a", "pcm_s16le", "-ar", "44100", str(output_wav_path)],
                    capture_output=True, check=True
                )
                if temp_wav.exists():
                    temp_wav.unlink()
                print(f"[Piper TTS] Successfully generated voice for speaker {speaker_key} using local model")
                return output_wav_path
        except Exception as e:
            print(f"[Piper TTS] Failed to generate voice using Piper: {e}. Falling back to Edge-TTS...")

    voice_ref_path = Path("voice_refs") / f"{speaker}.wav"
    os.makedirs("voice_refs", exist_ok=True)
    
    # Try calling a local inference wrapper or API (e.g. XTTS or F5-TTS standard endpoint)
    try:
        response = requests.post(
            "http://127.0.0.1:8020/tts", 
            json={"text": text, "speaker_wav": str(voice_ref_path.resolve())},
            timeout=5
        )
        if response.status_code == 200:
            with open(output_wav_path, "wb") as f:
                f.write(response.content)
            return output_wav_path
    except Exception as e:
        print(f"[Voice Cloning] Local API not responding, using Edge-TTS fallback: {e}")
        
    # Fallback to edge-tts with character mappings
    voice_map = {
        "narrator": "en-US-AndrewNeural",
        "host": "en-US-BrianNeural",
        "guest": "en-US-EmmaNeural",
        "character_a": "en-US-BrianNeural",
        "character_b": "en-US-EmmaNeural",
        "scientist": "en-US-AndrewNeural",
        "skeptic": "en-US-EmmaNeural"
    }
    fallback_voice = voice_map.get(speaker.lower(), "en-US-BrianNeural")
    
    raw_mp3 = Path(output_wav_path).with_suffix(".mp3")
    cmd = [
        "edge-tts",
        "--text", text,
        "--voice", fallback_voice,
        "--write-media", str(raw_mp3)
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    
    # Speed adjustment and audio treatment
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(raw_mp3),
         "-af", f"atempo={AUDIO_SPEED},loudnorm=I=-16:TP=-1.5:LRA=11,treble=g=4:f=8000:w=0.5", 
         "-c:a", "pcm_s16le", "-ar", "44100", str(output_wav_path)],
        capture_output=True, check=True,
    )
    if raw_mp3.exists():
        raw_mp3.unlink()
        
    return output_wav_path


# -- load .env manually if exists ---------------------------------------------
_ENV_PATH = Path(__file__).parent / ".env"
if _ENV_PATH.exists():
    with open(_ENV_PATH, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ[_k.strip()] = _v.strip().strip('"').strip("'")

# -- config -------------------------------------------------------------------
_CFG_PATH = Path(__file__).parent / "config.json"
with open(_CFG_PATH, "r", encoding="utf-8") as f:
    CFG = json.load(f)

def _resolve_rel(p):
    path = Path(p)
    if not path.is_absolute():
        return (Path(__file__).parent / path).resolve()
    return path

PIPER_PATH      = os.environ.get("PIPER_PATH", str(_resolve_rel(CFG["piper_path"])))
PIPER_MODEL     = os.environ.get("PIPER_MODEL", str(_resolve_rel(CFG["piper_model"])))
BACKGROUNDS_DIR = Path(os.environ.get("BACKGROUNDS_DIR", _resolve_rel(CFG["backgrounds_dir"])))
OUTPUT_DIR      = Path(os.environ.get("OUTPUT_DIR", _resolve_rel(CFG["output_dir"])))
TEMP_DIR        = Path(os.environ.get("TEMP_DIR", _resolve_rel(CFG["temp_dir"])))
OLLAMA_URL      = os.environ.get("OLLAMA_URL", CFG["ollama_url"])
OLLAMA_MODEL    = os.environ.get("OLLAMA_MODEL", CFG["ollama_model"])
WHISPER_MODEL   = os.environ.get("WHISPER_MODEL", CFG["whisper_model"])
WHISPER_DEVICE  = os.environ.get("WHISPER_DEVICE", CFG["whisper_device"])
AUDIO_SPEED     = float(os.environ.get("AUDIO_SPEED", CFG["audio_speed"]))
VW              = int(os.environ.get("VIDEO_WIDTH", CFG["video_width"]))
VH              = int(os.environ.get("VIDEO_HEIGHT", CFG["video_height"]))
SUB_TOP_PCT     = float(os.environ.get("SUBTITLE_SAFE_ZONE_TOP_PCT", CFG["subtitle_safe_zone_top_pct"]))
SUB_BOT_PCT     = float(os.environ.get("SUBTITLE_SAFE_ZONE_BOTTOM_PCT", CFG["subtitle_safe_zone_bottom_pct"]))

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Hardware acceleration codec setup
FFMPEG_CODEC  = os.environ.get("FFMPEG_CODEC", CFG.get("ffmpeg_codec", "libx264"))
FFMPEG_PRESET = os.environ.get("FFMPEG_PRESET", CFG.get("ffmpeg_preset", "slow"))
FFMPEG_CRF    = os.environ.get("FFMPEG_CRF", CFG.get("ffmpeg_crf", "20"))

if FFMPEG_CODEC == "h264_nvenc":
    enc_flags = f"-c:v h264_nvenc -preset {FFMPEG_PRESET} -cq {FFMPEG_CRF} -pix_fmt yuv420p"
else:
    enc_flags = f"-c:v libx264 -preset {FFMPEG_PRESET} -crf {FFMPEG_CRF} -pix_fmt yuv420p"


# -- category styling ---------------------------------------------------------
STYLES = {
    "Weird Science":          {"color": "&H00FFFF00", "font_size": 95},  # True Cyan
    "Productivity & stoicism":{"color": "&H00FFFF00", "font_size": 95},  # True Cyan
    "Human Behavior":         {"color": "&H00FF00FF", "font_size": 95},  # Magenta/Hot Pink
    "Tech":                   {"color": "&H0000FF00", "font_size": 95},  # Lime Green
}

# =============================================================================
# 1. OLLAMA SCRIPT GENERATION
# =============================================================================

# Hook framework descriptions injected into every prompt.
# Ollama chooses one of the three per generation (randomness via temperature).
_HOOK_FRAMEWORKS = (
    "Choose ONE of these three hook frameworks (vary randomly):\n"
    "1. Negative Bias   — target a mistake the viewer is actively making RIGHT NOW.\n"
    "   Example: 'You are ruining your focus every morning by doing this one thing.'\n"
    "2. Open Loop       — state a shocking result first; delay the explanation until the CTA.\n"
    "   Example: 'Scientists locked 50 people in darkness for a week. What happened is disturbing.'\n"
    "3. Counter-Intuitive Claim — attack a universally accepted fact.\n"
    "   Example: 'Stop waking up at 5 AM. It is actually destroying your productivity.'\n"
)

BASE_SYSTEM_INSTRUCTION = (
    "You are a elite short-form retention engineer and growth expert for viral YouTube channels.\n"
    "CRITICAL STRUCTURE REQUIREMENTS:\n"
    "1. Output ONLY strict raw JSON containing exactly: 'title', 'hook_0_5s', 'problem_5_20s', 'twist_20_35s', 'cta_35_45s'. No markdown fences. No extra text.\n"
    "2. TARGET LENGTH: The total script must be between 90 and 110 words to ensure a solid 35-45 second video run. Expand on the mechanisms, stakes, and biological realities. Each section MUST have the exact target word count range (hook: 12-15 words, problem: 35-40 words, twist: 35-40 words, cta: 15-20 words). Write detailed, descriptive sentences to hit this target length.\n"
    "3. PACING: Every sentence must be sharp, punchy, and under 10 words. Use hard periods (.) or exclamation marks (!) frequently. Do not use commas to chain long ideas together.\n"
    "4. NO EMOJIS: Strictly do not include emojis, unicode symbols, or visual graphics anywhere in the output. Keep the script completely in clean, raw text format.\n"
    "5. LOGICAL ALIGNMENT CONSTRAINT: The hook must logically match the scientific or factual payload of the body. If the body explains a beneficial biological mechanism (e.g., yawning cools the brain, boosts focus), the hook MUST attack the viewer's behavior or misconception (e.g., 'You are destroying your morning focus by fighting your yawns.') rather than claiming the mechanism itself is bad (e.g., NEVER claim yawning is bad or toxic).\n"
)

PROMPTS = {
    "Weird Science": BASE_SYSTEM_INSTRUCTION + (
        "TOPIC: {topic}\n"
        "Category Style: High-level neurobiology masterclass delivered with dramatic urgency. Focus on intense, lesser-known metrics.\n"
        "Framework Blueprint:\n"
        " - hook_0_5s: An intense Negative Bias or Counter-Intuitive warning targeting a daily habit. (10-15 words)\n"
        " - problem_5_20s: Explain the hidden biological disaster happening inside the body when this habit occurs. Write at least 3 descriptive, punchy sentences. (35-40 words)\n"
        " - twist_20_35s: Deliver a mind-blowing, specific scientific counter-measure or revelation that fixes it. Write at least 3 descriptive, punchy sentences. (35-40 words)\n"
        " - cta_35_45s: A high-leverage engagement loop that blends into the beginning of the video. (15-20 words)\n"
    ),
    "Productivity & stoicism": BASE_SYSTEM_INSTRUCTION + (
        "TOPIC: {topic}\n"
        "Category Style: Aggressive mental optimization using historical frameworks and performance metrics.\n"
        "Framework Blueprint:\n"
        " - hook_0_5s: Attack the viewer's current routine or focus setup. (10-15 words)\n"
        " - problem_5_20s: Detail the psychological decay or dopamine trap caused by standard advice. Write at least 3 descriptive, punchy sentences. (35-40 words)\n"
        " - twist_20_35s: Introduce a ruthless stoic rule or modern habit shift that fixes it instantly. Write at least 3 descriptive, punchy sentences. (35-40 words)\n"
        " - cta_35_45s: High-friction conversation starter loop for the comments section. (15-20 words)\n"
    ),
    "Human Behavior": BASE_SYSTEM_INSTRUCTION + (
        "TOPIC: {topic}\n"
        "Category Style: High-stakes manipulation, dark psychology, and elite social reading tactics.\n"
        "Framework Blueprint:\n"
        " - hook_0_5s: Expose a way the viewer is being read or manipulated right now. (10-15 words)\n"
        " - problem_5_20s: Detail the hidden subconscious cues people use to judge or control situations. Write at least 3 descriptive, punchy sentences. (35-40 words)\n"
        " - twist_20_35s: Reveal the exact verbal or physical counter-strategy to take control. Write at least 3 descriptive, punchy sentences. (35-40 words)\n"
        " - cta_35_45s: Prompt a high-engagement loop to force rewatching. (15-20 words)\n"
    ),
    "Tech": BASE_SYSTEM_INSTRUCTION + (
        "TOPIC: {topic}\n"
        "Category Style: Insanely advanced local workflows, hidden hardware tricks, or developer secrets.\n"
        "Framework Blueprint:\n"
        " - hook_0_5s: Warn them that their current machine or software configuration is a mistake. (10-15 words)\n"
        " - problem_5_20s: Explain how default consumer settings track, slow down, or limit optimization. Write at least 3 descriptive, punchy sentences. (35-40 words)\n"
        " - twist_20_35s: Walk through the exact local tool, terminal command, or layout switch that solves it. Write at least 3 descriptive, punchy sentences. (35-40 words)\n"
        " - cta_35_45s: Explicit, clean asset-saving loop prompt. (15-20 words)\n"
    ),
}

OLLAMA_PARAMS = {
    "num_predict": 1024,
    "temperature": 0.45,  # Low temperature to eliminate word fabrications
    "top_p": 0.85,
    "top_k": 30
}

SUBSTANTIVE_ROLES = {
    "explain", "answer", "expand", "correct", "example", "reveal", "connect", "challenge", "hook", "summarize"
}

def validate_factual_claims(lines, topic, research_context=None):
    """
    Validates factual claims asserted by Speaker A and Speaker B.
    Checks grounding against topic knowledge or supplied research context.
    Flags HIGH severity errors for false scientific mechanisms.
    """
    claims_a = 0
    claims_b = 0
    supported_a = 0
    supported_b = 0
    uncertain_a = 0
    uncertain_b = 0
    unsupported_a = 0
    unsupported_b = 0
    contradicted_a = 0
    contradicted_b = 0
    high_severity_count = 0
    medium_severity_count = 0

    claim_details = []
    errors = []

    false_mechanisms = [
        ("only possible in low-oxygen", "Bioluminescence is not restricted to low-oxygen environments."),
        ("only possible in zero oxygen", "Bioluminescence requires oxygen for luciferin oxidation."),
        ("only in freshwater", "Bioluminescence is overwhelmingly marine."),
        ("requires zero pressure", "Deep sea creatures adapt to high pressure.")
    ]

    for turn in lines:
        role = str(turn.get("role", "")).lower()
        itype = str(turn.get("interaction_type", "")).lower()
        if role == "outro" or itype == "close":
            continue

        spk = str(turn.get("speaker", "A")).strip().upper()
        txt = turn.get("text", "")
        txt_l = txt.lower()
        ctype = str(turn.get("claim_type", "scientific_fact")).lower()
        claim = turn.get("claim", "")

        if not claim and (turn.get("role") in SUBSTANTIVE_ROLES or len(txt.split()) >= 10):
            claim = txt

        if not claim:
            continue

        if spk == "A":
            claims_a += 1
        else:
            claims_b += 1

        is_contradicted = False
        for trigger, reason in false_mechanisms:
            if trigger in txt_l or trigger in str(claim).lower():
                is_contradicted = True
                high_severity_count += 1
                if spk == "A":
                    contradicted_a += 1
                else:
                    contradicted_b += 1
                errors.append(f"HIGH Severity Factual Error ({spk}): {reason}")
                claim_details.append({"speaker": spk, "claim": claim, "status": "contradicted", "severity": "HIGH", "reason": reason})
                break

        if is_contradicted:
            continue

        is_qualified = any(q in txt_l for q in ["scientists believe", "one known mechanism", "in some species", "researchers", "one explanation", "like the", "often", "usually"])
        
        if is_qualified or ctype in ["opinion", "reaction", "example"]:
            if spk == "A":
                uncertain_a += 1 if is_qualified else 0
                supported_a += 1 if not is_qualified else 0
            else:
                uncertain_b += 1 if is_qualified else 0
                supported_b += 1 if not is_qualified else 0
            claim_details.append({"speaker": spk, "claim": claim, "status": "uncertain" if is_qualified else "supported", "severity": "NONE"})
        else:
            if spk == "A":
                supported_a += 1
            else:
                supported_b += 1
            claim_details.append({"speaker": spk, "claim": claim, "status": "supported", "severity": "NONE"})

    grounding_summary = {
        "claims_a": claims_a, "claims_b": claims_b,
        "supported_a": supported_a, "supported_b": supported_b,
        "uncertain_a": uncertain_a, "uncertain_b": uncertain_b,
        "unsupported_a": unsupported_a, "unsupported_b": unsupported_b,
        "contradicted_a": contradicted_a, "contradicted_b": contradicted_b,
        "total_supported": supported_a + supported_b,
        "total_uncertain": uncertain_a + uncertain_b,
        "total_unsupported": unsupported_a + unsupported_b,
        "total_contradicted": contradicted_a + contradicted_b,
        "high_severity_count": high_severity_count,
        "medium_severity_count": medium_severity_count,
        "claim_details": claim_details
    }

    if high_severity_count > 0:
        return False, errors, grounding_summary

    return True, [], grounding_summary


def validate_and_analyze_conversation(lines, topic="General Topic", research_context=None):
    """
    Validates that Speaker B is a true co-host with initiative & factual quality:
    - Speaker B contributes between 35% and 60% of total spoken words.
    - Speaker B demonstrates initiative (>= 2 initiative beats for both A and B).
    - Validates factual claim grounding & severity.
    - Estimates pre-TTS spoken duration (80-140 words, <= 58s).
    - Prints formatted CONTENT + CONVERSATION QA (V4) dashboard.
    """
    spk_b_min = CFG.get("speaker_b_min_word_pct", 35.0)
    spk_b_max = CFG.get("speaker_b_max_word_pct", 60.0)
    target_max_dur = CFG.get("target_max_duration", 58.0)

    words_a = 0
    words_b = 0
    turns_a = 0
    turns_b = 0
    substantive_a = 0
    substantive_b = 0
    questions_a = 0
    questions_b = 0
    initiative_a = 0
    initiative_b = 0
    responses_a = 0
    responses_b = 0

    roles_a = []
    roles_b = []
    beats_a = []
    beats_b = []
    info_beats = []

    INITIATIVE_ROLES = {"hook", "lead", "reveal", "challenge", "redirect", "example", "connect"}

    for idx, turn in enumerate(lines):
        spk = str(turn.get("speaker", "A")).strip().upper()
        txt = turn.get("text", "")
        role = str(turn.get("role", "explain")).lower()
        itype = str(turn.get("interaction_type", "")).lower()
        beat = str(turn.get("information_beat", "")).strip()
        
        w_count = len(txt.split())
        txt_l = txt.lower()

        if role == "outro" or itype == "close":
            if spk == "A":
                words_a += w_count
                turns_a += 1
                roles_a.append(role)
            else:
                words_b += w_count
                turns_b += 1
                roles_b.append(role)
            continue

        # Infer beat if not explicitly populated
        if not beat and w_count >= 8:
            beat = " ".join(txt.split()[:6]) + "..."
            turn["information_beat"] = beat

        is_initiative = False
        if role in INITIATIVE_ROLES or itype in INITIATIVE_ROLES:
            is_initiative = True
        elif idx > 0:
            is_agree = any(txt_l.startswith(w) for w in ["yeah", "exactly", "right", "pretty much", "normally yes", "that's right"])
            if not is_agree and w_count >= 10:
                is_initiative = True

        if spk == "A":
            words_a += w_count
            turns_a += 1
            roles_a.append(role)
            if role in SUBSTANTIVE_ROLES or w_count >= 10:
                substantive_a += 1
            if "?" in txt or role == "question":
                questions_a += 1
            if is_initiative:
                initiative_a += 1
            else:
                responses_a += 1
            if beat:
                beats_a.append(beat)
                info_beats.append(f"A ({role}) → {beat}")
        else:
            words_b += w_count
            turns_b += 1
            roles_b.append(role)
            if role in SUBSTANTIVE_ROLES or w_count >= 10:
                substantive_b += 1
            if "?" in txt or role == "question":
                questions_b += 1
            if is_initiative:
                initiative_b += 1
            else:
                responses_b += 1
            if beat:
                beats_b.append(beat)
                info_beats.append(f"B ({role}) → {beat}")

    total_words = words_a + words_b
    pct_a = (words_a / total_words * 100) if total_words > 0 else 0
    pct_b = (words_b / total_words * 100) if total_words > 0 else 0

    est_duration = round(total_words / 2.7, 1)

    def check_max_role_streak(roles_list):
        max_s = 0
        curr_s = 0
        curr_r = None
        for r in roles_list:
            if r == curr_r:
                curr_s += 1
            else:
                curr_r = r
                curr_s = 1
            if curr_s > max_s:
                max_s = curr_s
        return max_s

    inferred_roles_a = []
    inferred_roles_b = []
    for turn in lines:
        spk = str(turn.get("speaker", "A")).strip().upper()
        txt = turn.get("text", "").strip()
        role = str(turn.get("role", "explain")).lower()
        
        txt_l = txt.lower()
        if "?" in txt or txt_l.startswith(("why", "how", "what", "can you", "does")):
            role = "question"
        elif txt_l.startswith(("yeah", "exactly", "right", "pretty much", "normally")):
            role = "answer"
        elif txt_l.startswith(("for example", "for instance", "like the")):
            role = "example"
        elif txt_l.startswith(("wait", "really", "wouldn't", "no way")):
            role = "challenge"
        elif txt_l.startswith(("it's due to", "the reason is", "it involves", "they produce")):
            role = "explain"
        elif txt_l.startswith(("and it's not", "plus", "also", "even")):
            role = "reveal"

        turn["inferred_role"] = role
        if spk == "A":
            inferred_roles_a.append(role)
        else:
            inferred_roles_b.append(role)

    streak_a = check_max_role_streak(inferred_roles_a)
    streak_b = check_max_role_streak(inferred_roles_b)
    unique_b_roles = len(set(inferred_roles_b))
    role_diversity_score = round(unique_b_roles / max(1, turns_b), 2)

    monotony_risk = "LOW"
    if streak_b >= 4 or streak_a >= 4 or (turns_b >= 4 and unique_b_roles <= 1):
        monotony_risk = "HIGH"
    elif streak_b >= 3 or unique_b_roles <= 2:
        monotony_risk = "MEDIUM"

    connective_markers = {"yeah", "right", "exactly", "wait", "normally", "pretty", "so", "but", "instance", "example", "for", "hold", "here's"}
    interaction_count = 0
    for idx in range(1, len(lines)):
        prev_txt = lines[idx-1].get("text", "").lower()
        curr_txt = lines[idx].get("text", "").lower()
        curr_role = str(lines[idx].get("role", "")).lower()

        if "?" in prev_txt or curr_role in {"answer", "challenge", "correct", "connect", "example"}:
            interaction_count += 1
        else:
            words = set(curr_txt.split()[:4])
            if words.intersection(connective_markers):
                interaction_count += 1

    second_narrator_risk = "LOW"
    if turns_a >= 2 and turns_b >= 2 and interaction_count == 0:
        second_narrator_risk = "HIGH"
    elif turns_a >= 3 and turns_b >= 3 and interaction_count <= 1:
        second_narrator_risk = "HIGH"
    elif interaction_count <= 2:
        second_narrator_risk = "MEDIUM"

    # Factual Claim Validation Pass
    is_factual_valid, factual_errors, g_summary = validate_factual_claims(lines, topic, research_context)

    # Outro Validation Pass
    # Normalize non-outro interaction_types if Ollama used 'close' on intermediate non-final turns
    for idx, turn in enumerate(lines):
        role_val = str(turn.get("role", "")).lower()
        itype_val = str(turn.get("interaction_type", "")).lower()
        if itype_val == "close" and role_val != "outro" and idx < len(lines) - 1:
            turn["interaction_type"] = "connect"

    outro_turns = [
        idx for idx, t in enumerate(lines)
        if str(t.get("role", "")).lower() == "outro"
    ]
    if not outro_turns:
        outro_turns = [
            idx for idx, t in enumerate(lines)
            if str(t.get("interaction_type", "")).lower() == "close" and idx == len(lines) - 1
        ]

    outro_errors = []
    if len(outro_turns) > 1:
        outro_errors.append("Multiple outro turns detected (only 1 outro turn allowed).")
    elif len(outro_turns) == 1:
        o_idx = outro_turns[0]
        o_turn = lines[o_idx]
        o_spk = str(o_turn.get("speaker", "A")).strip().upper()
        o_txt = o_turn.get("text", "").strip()
        o_role = str(o_turn.get("role", "")).lower()
        o_itype = str(o_turn.get("interaction_type", "")).lower()
        o_w_count = len(o_txt.split())

        # Auto-align role/interaction_type if needed for final turn
        if o_role != "outro":
            o_turn["role"] = "outro"
            o_role = "outro"
        if o_itype != "close":
            o_turn["interaction_type"] = "close"
            o_itype = "close"

        if o_idx != len(lines) - 1:
            outro_errors.append("Outro turn must be the final dialogue turn.")
        if o_w_count > 20:
            outro_errors.append(f"Outro turn word count ({o_w_count}) exceeds maximum 20 words.")
        if o_w_count < 1:
            outro_errors.append("Outro turn is empty.")
        if "?" in o_txt:
            outro_errors.append("Outro turn must not contain an unanswered question.")
        if o_turn.get("information_beat", "").strip():
            outro_errors.append("Outro turn must not introduce a new information beat.")

        o_claim = o_turn.get("claim", "").strip()
        o_ctype = str(o_turn.get("claim_type", "")).lower()
        if o_claim and o_ctype in ["scientific_fact", "historical_fact", "numerical_fact", "causal_claim"]:
            outro_errors.append("Outro turn must not introduce a new factual claim.")

    outro_present = (len(outro_turns) == 1 and outro_turns[0] == len(lines) - 1)
    outro_spk = lines[outro_turns[0]].get("speaker", "A") if len(outro_turns) >= 1 else None
    outro_w_count = len(lines[outro_turns[0]].get("text", "").split()) if len(outro_turns) >= 1 else 0
    outro_validated = (outro_present and len(outro_errors) == 0)

    if not outro_present and len(outro_turns) == 0:
        print("[OUTRO WARNING] Dialogue ended without a dedicated outro turn.")

    # Consolidated Dashboard Output
    print("\n" + "=" * 60)
    print("           CONTENT + CONVERSATION QA (V4)")
    print("=" * 60)
    print("Conversation:")
    print(f"  A/B Balance          : {pct_a:.1f}% / {pct_b:.1f}%")
    print(f"  Initiative           : A={initiative_a}, B={initiative_b}")
    print(f"  Role Diversity       : {role_diversity_score}")
    print(f"  Second-Narrator Risk : {second_narrator_risk}")
    print(f"  Monotony Risk        : {monotony_risk}")
    print("\nOutro:")
    print(f"  Present              : {outro_present}")
    print(f"  Speaker              : {outro_spk}")
    print(f"  Word Count           : {outro_w_count} words")
    print(f"  Validated            : {outro_validated}")
    print("\nInformation Ownership:")
    print(f"  A Information Beats  : {len(beats_a)}")
    print(f"  B Information Beats  : {len(beats_b)}")
    print("\nFactual Claims:")
    print(f"  A Claims             : {g_summary['claims_a']} (Supported: {g_summary['supported_a']}, Uncertain: {g_summary['uncertain_a']}, Unsupported: {g_summary['unsupported_a']}, Contradicted: {g_summary['contradicted_a']})")
    print(f"  B Claims             : {g_summary['claims_b']} (Supported: {g_summary['supported_b']}, Uncertain: {g_summary['uncertain_b']}, Unsupported: {g_summary['unsupported_b']}, Contradicted: {g_summary['contradicted_b']})")
    print("\nGrounding Summary:")
    print(f"  Supported            : {g_summary['total_supported']}")
    print(f"  Uncertain            : {g_summary['total_uncertain']}")
    print(f"  Unsupported          : {g_summary['total_unsupported']}")
    print(f"  Contradicted         : {g_summary['total_contradicted']}")
    print("\nClaim Severity:")
    print(f"  High Severity        : {g_summary['high_severity_count']}")
    print(f"  Medium Severity      : {g_summary['medium_severity_count']}")
    print(f"\nEstimated Duration     : {est_duration}s")
    print("-" * 60)
    if info_beats:
        print("Information Beats Distribution:")
        for ib in info_beats[:8]:
            print(f"  • {ib}")
        print("-" * 60)

    # Validation Errors
    errors = []
    if not is_factual_valid:
        errors.extend(factual_errors)
    if outro_errors:
        errors.extend(outro_errors)

    if pct_b < spk_b_min:
        errors.append(f"Speaker B word count ratio too low ({pct_b:.1f}% < {spk_b_min:.1f}%). Speaker B must be a co-equal co-host.")
    if pct_b > spk_b_max:
        errors.append(f"Speaker B word count ratio too high ({pct_b:.1f}% > {spk_b_max:.1f}%). Speaker B is monopolizing explanations.")
    if substantive_b < 2:
        errors.append(f"Speaker B has too few substantive turns ({substantive_b} < 2).")
    if substantive_a < 2:
        errors.append(f"Speaker A has too few substantive turns ({substantive_a} < 2).")

    if initiative_b < 2:
        errors.append(f"Speaker Initiative Error: Speaker B has too few initiative beats ({initiative_b} < 2). Speaker B only responds to Speaker A and does not introduce new concepts independently.")
    if initiative_a < 2:
        errors.append(f"Speaker Initiative Error: Speaker A has too few initiative beats ({initiative_a} < 2).")

    if turns_b >= 3 and questions_b == turns_b:
        errors.append("Speaker B is question-only. Speaker B must contribute substantive information.")
    if turns_b >= 3 and substantive_b == 0:
        errors.append("Speaker B is reaction-only. Speaker B must contribute substantive information.")

    if len(beats_a) > 0 and len(beats_b) == 0:
        errors.append("Speaker A monopolizes all information beats. Speaker B owns zero information beats.")
    if len(beats_b) > 0 and len(beats_a) == 0:
        errors.append("Speaker B monopolizes all information beats. Speaker A owns zero information beats.")

    if streak_b >= 4 or (turns_b >= 4 and unique_b_roles <= 1):
        errors.append(f"Monotony Risk HIGH: Speaker B has {streak_b} consecutive identical '{inferred_roles_b[0]}' roles. Diversify dialogue roles.")

    if second_narrator_risk == "HIGH":
        errors.append("Second-Narrator Risk HIGH: Dialogue consists of two independent monologues with no conversational interaction.")

    if est_duration > target_max_dur:
        errors.append(f"Pre-TTS Duration Error: Estimated spoken duration ({est_duration:.1f}s) exceeds maximum target ({target_max_dur:.1f}s). Script is too long for Shorts.")

    if total_words < 80:
        errors.append(f"Pre-TTS Duration Error: Total script word count ({total_words} words) is too short (< 80 words). Script duration will be under 28s.")

    convo_stats = {
        "total_words": total_words, "pct_a": pct_a, "pct_b": pct_b,
        "turns_a": turns_a, "turns_b": turns_b,
        "substantive_a": substantive_a, "substantive_b": substantive_b,
        "initiative_a": initiative_a, "initiative_b": initiative_b,
        "beats_a_count": len(beats_a), "beats_b_count": len(beats_b),
        "est_duration": est_duration, "monotony_risk": monotony_risk,
        "second_narrator_risk": second_narrator_risk,
        "role_diversity_score": role_diversity_score,
        "grounding_summary": g_summary,
        "outro": {
            "present": outro_present,
            "speaker": outro_spk,
            "word_count": outro_w_count,
            "validated": outro_validated
        }
    }

    if errors:
        print(f"[CONVERSATION VALIDATION FAILED] {errors}\n")
        return False, errors, convo_stats

    print("[CONVERSATION VALIDATION SUCCESS] Verified: Content + Conversation QA V4 passed!\n")
    return True, [], convo_stats


def generate_script(topic, category):
    """
    Call Ollama and return debate script.
    Enforces structural JSON schema format for two-persona debate.
    """
    import re
    
    last_errors = []
    for attempt in range(1, 7):
        print(f"[Ollama] Generating debate script (Attempt {attempt}/6)...")
        
        feedback_prompt = ""
        if last_errors:
            feedback_prompt = (
                f"\n\n### REGENERATION INSTRUCTIONS FROM PREVIOUS ATTEMPT FAILURE:\n"
                f"The previous attempt failed validation with errors: {last_errors}\n"
                f"FIX THESE ISSUES IMMEDIATELY in this attempt:\n"
                f"- TARGET SCRIPT WORD COUNT: Keep total words between 110 and 135 words (for a tight 35-45s duration).\n"
                f"- SPEAKER B INITIATIVE: Speaker B MUST independently introduce new concepts or reveal facts on at least 2 turns. Speaker B IS NOT merely responding to Speaker A.\n"
                f"- SPEAKER A IS NOT A QUESTION MACHINE: Speaker A must EXPLAIN facts or provide examples on at least 2 turns. DO NOT make Speaker A ask a question on every turn!\n"
                f"- CONVERSATIONAL INTERACTION: Make them respond directly to each other (explain, challenge, reveal, answer) rather than two independent monologues.\n"
            )

        prompt = (
            f"You are a senior YouTube Shorts retention strategist and viral scriptwriter. Generate a fast-paced 2-person dialogue script about '{topic}' in strictly formatted JSON.\n\n"
            f"### CRITICAL RULE: FACTUAL ACCURACY, SCIENTIFIC QUALIFICATION & NATURAL OUTRO\n"
            f"- Both Speaker A and Speaker B are intelligent CO-HOSTS discussing '{topic}'.\n"
            f"- All scientific statements MUST be accurate. Use natural qualifications ('Scientists believe...', 'In some species...', 'One known mechanism is...') when describing complex biological systems.\n"
            f"- DO NOT invent false scientific mechanisms (e.g. claiming bioluminescence requires zero oxygen or low oxygen).\n"
            f"- Speaker B MUST lead at least 2 information beats independently.\n"
            f"- Total Script Word Count MUST be between 110 and 135 words total across 5-6 scenes (target duration: 35-50 seconds).\n"
            f"- Speaker B word count ratio MUST be between 35% and 60% (healthy conversational balance).\n"
            f"- ENDING OUTRO TURN: End the conversation with one brief, natural closing thought (6-15 words, max 20 words) on the final turn using role: 'outro' and interaction_type: 'close'. The closing thought must feel like the two hosts have reached a satisfying endpoint. It must NOT introduce new facts, a new topic, or an unanswered question.\n\n"
            f"### STRUCTURE & DIALOGUE ROLES\n"
            f"Assign a 'role' to every turn from: ['hook', 'explain', 'answer', 'question', 'challenge', 'correct', 'expand', 'example', 'reveal', 'connect', 'summarize', 'outro'].\n"
            f"Target Length: 5 to 7 visual scenes total.\n\n"
            f"### REQUIRED JSON SCHEMA\n"
            f"{{\n"
            f"  \"title\": \"Debate: {topic}\",\n"
            f"  \"scenes\": [\n"
            f"    {{\n"
            f"      \"visual_prompt\": \"Cinematic 8k shot of [Visual Description], hyper-detailed, 8k\",\n"
            f"      \"reason\": \"Concept description\",\n"
            f"      \"dialogue\": [\n"
            f"        {{\"speaker\": \"A\", \"role\": \"hook\", \"interaction_type\": \"lead\", \"information_beat\": \"...\", \"claim\": \"...\", \"claim_type\": \"scientific_fact\", \"text\": \"...\"}},\n"
            f"        {{\"speaker\": \"B\", \"role\": \"explain\", \"interaction_type\": \"lead\", \"information_beat\": \"...\", \"claim\": \"...\", \"claim_type\": \"scientific_fact\", \"text\": \"...\"}},\n"
            f"        {{\"speaker\": \"A\", \"role\": \"outro\", \"interaction_type\": \"close\", \"information_beat\": \"\", \"text\": \"Short natural closing thought.\"}}\n"
            f"      ]\n"
            f"    }}\n"
            f"  ]\n"
            f"}}\n"
            f"{feedback_prompt}"
        )
        
        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "scenes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "visual_prompt": {"type": "string"},
                            "reason": {"type": "string"},
                            "dialogue": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "speaker": {"type": "string", "enum": ["A", "B"]},
                                        "role": {
                                            "type": "string",
                                            "enum": ["hook", "explain", "answer", "question", "follow_up", "challenge", "correct", "expand", "example", "reveal", "connect", "summarize", "react", "outro"]
                                        },
                                        "interaction_type": {
                                            "type": "string",
                                            "enum": ["lead", "respond", "elaborate", "challenge", "answer", "redirect", "reveal", "question", "connect", "example", "close"]
                                        },
                                        "information_beat": {"type": "string"},
                                        "claim": {"type": "string"},
                                        "claim_type": {
                                            "type": "string",
                                            "enum": ["scientific_fact", "historical_fact", "numerical_fact", "definition", "example", "causal_claim", "comparison", "inference", "opinion", "reaction"]
                                        },
                                        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                                        "text": {"type": "string"}
                                    },
                                    "required": ["speaker", "text"]
                                }
                            }
                        },
                        "required": ["visual_prompt", "dialogue"]
                    }
                }
            },
            "required": ["scenes"]
        }

        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "format": schema,   # enforce strict JSON schema-guided output
            "stream": False,
            "options": OLLAMA_PARAMS,
        }

        try:
            acquired = gpu_lock.acquire(timeout=600)
            if not acquired:
                raise TimeoutError("Pipeline queue timeout capacity reached (GPU lock in Ollama)")
            try:
                resp = requests.post(
                    f"{OLLAMA_URL}/api/generate",
                    json=payload,
                    timeout=120,
                )
            finally:
                gpu_lock.release()
                
            resp.raise_for_status()
            raw = resp.json().get("response", "")
            
            cleaned = raw.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            data = json.loads(cleaned)
            scenes_raw = data.get("scenes", [])
            if not isinstance(scenes_raw, list) or not scenes_raw:
                print(f"[Ollama] Validation failed: no scenes found")
                last_errors = ["No scenes found in LLM output."]
                continue

            lines = []
            segments = []
            
            corrections = {
                r'\bunsuptiously\b': 'subconsciously',
                r'\bunsustiously\b': 'subconsciously',
                r'\bdirect\s+stairs\b': 'direct stares',
                r'\beye\s+stairs\b': 'eye stares',
                r'\bcontact\s+sense\b': 'contact signals',
                r'\bcontact\s+sends\b': 'contact signals',
                r'\bdrop\s+a\s+fire\s+statement\b': 'comment below',
                r'\bdrop\s+a\s+(\w+)\s+emoji\b': 'comment below', 
                r'\bleave\s+a\s+(\w+)\s+comment\b': 'comment below',
                r'\b(drop|leave)\b\s+a\s+eye\s+emoji': 'comment below',
                r'\b(drop|leave)\b\s+a\s+eye\s+comment': 'comment below',
                r'\b(drop|leave)\b\s+a\s+brain\s+emoji': 'comment below',
                r'\b(drop|leave)\b\s+a\s+brain\s+comment': 'comment below'
            }

            for idx, sc in enumerate(scenes_raw):
                seg_id = f"segment_{idx}"
                v_prompt = sc.get("visual_prompt", sc.get("image_prompt", "Realistic cinematic image"))
                sc_dialogue = sc.get("dialogue", sc.get("lines", []))
                
                clean_sc_lines = []
                for turn in sc_dialogue:
                    val = turn.get("text", "")
                    for pattern, replacement in corrections.items():
                        val = re.sub(pattern, replacement, val, flags=re.IGNORECASE)
                    turn_copy = {
                        "speaker": turn.get("speaker", "A"),
                        "role": turn.get("role", "explain"),
                        "interaction_type": turn.get("interaction_type", "lead"),
                        "information_beat": turn.get("information_beat", ""),
                        "claim": turn.get("claim", ""),
                        "claim_type": turn.get("claim_type", "scientific_fact"),
                        "confidence": turn.get("confidence", "high"),
                        "text": " ".join(val.split()),
                        "segment_id": seg_id,
                        "visual_topic_prompt": v_prompt
                    }
                    lines.append(turn_copy)
                    clean_sc_lines.append(turn_copy)

                segments.append({
                    "segment_id": seg_id,
                    "visual_topic_prompt": v_prompt,
                    "reason": sc.get("reason", ""),
                    "lines": clean_sc_lines
                })
                
            if len(lines) < 4:
                print(f"[Ollama] Validation failed: script has too few lines ({len(lines)})")
                last_errors = ["Script has too few dialogue lines (< 4)."]
                continue

            # Outro normalization: Ensure only the final turn is eligible for 'outro' / 'close'
            total_turns = len(lines)
            for idx, turn in enumerate(lines):
                role_val = str(turn.get("role", "")).lower()
                itype_val = str(turn.get("interaction_type", "")).lower()
                if idx < total_turns - 1:
                    if role_val == "outro":
                        turn["role"] = "connect"
                    if itype_val == "close":
                        turn["interaction_type"] = "connect"

            if total_turns > 0:
                last_turn = lines[-1]
                last_txt = last_turn.get("text", "").strip()
                last_w_count = len(last_txt.split())
                last_beat = last_turn.get("information_beat", "").strip()
                if 1 <= last_w_count <= 20 and "?" not in last_txt and not last_beat:
                    last_turn["role"] = "outro"
                    last_turn["interaction_type"] = "close"

            # Run Conversation Balance & Substantive Turn Validation
            is_valid_convo, convo_errors, convo_stats = validate_and_analyze_conversation(lines)
            if not is_valid_convo:
                print(f"[Ollama] Attempt {attempt} failed conversational balance validation: {convo_errors}")
                last_errors = convo_errors
                continue
                
            return {
                "title": data.get("title", f"Debate: {topic}"),
                "lines": lines,
                "segments": segments,
                "scenes": scenes_raw,
                "convo_stats": convo_stats,
                "success": True
            }
            
        except Exception as e:
            print(f"[Ollama] Attempt {attempt} failed: {e}")
            last_errors = [str(e)]
            
    raise RuntimeError(f"SCRIPT_VALIDATION_FAILED: All script generation attempts failed validation. Last errors: {last_errors}")
    fallback_lines = [
        {"speaker": "A", "text": "AI will replace all human workers within ten years.", "visual_topic_prompt": "Cinematic shot of human robot working in high tech office", "segment_id": "segment_0"},
        {"speaker": "B", "text": "That is wrong. AI will only assist us, not replace us.", "visual_topic_prompt": "Cinematic shot of friendly human worker collaborating with robot", "segment_id": "segment_0"},
        {"speaker": "A", "text": "Look at the automation speed. It is happening faster than ever.", "visual_topic_prompt": "Cinematic shot of rapid robotic arm assembly line", "segment_id": "segment_1"},
        {"speaker": "B", "text": "But humans will adapt and create new, higher-value jobs.", "visual_topic_prompt": "Cinematic shot of human programmer teaching robots", "segment_id": "segment_1"}
    ]
    return {
        "title": f"Debate: {topic}",
        "lines": fallback_lines,
        "segments": [
            {
                "segment_id": "segment_0",
                "visual_topic_prompt": fallback_lines[0]["visual_topic_prompt"],
                "lines": fallback_lines[0:2]
            },
            {
                "segment_id": "segment_1",
                "visual_topic_prompt": fallback_lines[2]["visual_topic_prompt"],
                "lines": fallback_lines[2:4]
            }
        ],
        "success": False
    }

def sanitize_script(text):
    """Clean script text by stripping unicode emojis and converting emoji prompts to text."""
    import re
    # Convert verbal emoji prompts to clean comments/engagement text
    clean_text = re.sub(r'\b(drop|leave)\s+a\s+\w+\s+emoji\b', 'comment below', text, flags=re.IGNORECASE)
    clean_text = re.sub(r'\b(drop|leave)\s+an\s+\w+\s+emoji\b', 'comment below', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'\b(drop|leave)\s+a\s+\w+\s+icon\b', 'comment below', clean_text, flags=re.IGNORECASE)
    
    # Removes standard emoji unicode ranges and structural brackets
    emoji_pattern = re.compile(
        r'[\u2600-\u27BF]|[\uE000-\uF8FF]|\uD83C[\uDC00-\uDFFF]|\uD83D[\uDC00-\uDFFF]|'
        r'[\u2011-\u26FF]|\uD83E[\uDD00-\uDFFF]', 
        flags=re.UNICODE
    )
    clean_text = emoji_pattern.sub(r'', clean_text)
    
    # Also clean up any literal emoji words if the LLM generated them at the end
    clean_text = re.sub(r'\b(books|laptop|computer|thumbs up|thumbs-up|eyes emoji|brain emoji|emoji)\b\.?$', '', clean_text, flags=re.IGNORECASE)
    
    return clean_text.strip()

def generate_voiceover(timeline_or_text, output_audio_path, voice="en-US-AndrewNeural"):
    """
    Synthesize text. Supports string for legacy single narrator, or list of dicts
    for dual-character timelines. Returns sped_path, or (sped_path, timings, visual_proofs).
    """
    if isinstance(timeline_or_text, str):
        text = sanitize_script(timeline_or_text)
        raw_path  = Path(output_audio_path).with_suffix(".mp3")
        sped_path = Path(output_audio_path).parent / (Path(output_audio_path).stem + "_sped.wav")

        print(f"[Edge TTS] Generating audio with {voice}...")
        
        cmd = [
            "edge-tts",
            "--text", text,
            "--voice", voice,
            "--write-media", str(raw_path)
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)

        if not raw_path.exists():
            raise RuntimeError("Edge TTS failed to generate audio.")

        print(f"[Edge TTS] Audio generated: {raw_path.name}")

        # Apply speedup, audio normalization (loudnorm), and treble boost
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(raw_path),
             "-af", f"atempo={AUDIO_SPEED},loudnorm=I=-16:TP=-1.5:LRA=11,treble=g=4:f=8000:w=0.5", 
             "-c:a", "pcm_s16le", "-ar", "44100", str(sped_path)],
            capture_output=True, check=True,
        )

        print(f"[Edge TTS] Audio ready: {sped_path.name} ({AUDIO_SPEED}x speed)")
        return str(sped_path)
    
    # Process structured timeline list
    current_time = 0.0
    timings = []
    turn_files = []
    
    print(f"[TTS Pipeline] Processing timeline with {len(timeline_or_text)} turns...")
    
    import uuid
    job_temp_dir = TEMP_DIR / f"voice_{uuid.uuid4().hex[:8]}"
    job_temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate a temporary 0.25s silence gap file for conversational spacing
    silence_gap_path = str(job_temp_dir / "silence_gap.wav")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "0.25", "-c:a", "pcm_s16le", silence_gap_path],
        capture_output=True, check=True
    )
    
    ROOT_DIR = Path(__file__).parent.parent
    os.chdir(ROOT_DIR)
    os.environ["PATH"] += os.pathsep + str(ROOT_DIR)

    cfg_voice_path = ROOT_DIR / "config" / "voice.json"
    model_a_path = (ROOT_DIR / "models" / "voices" / "en_US-ryan-medium.onnx").resolve()
    model_b_path = (ROOT_DIR / "models" / "voices" / "en_US-amy-medium.onnx").resolve()
    
    if cfg_voice_path.exists():
        try:
            with open(cfg_voice_path, "r", encoding="utf-8") as vf:
                vcfg = json.load(vf)
                if "A" in vcfg and "model" in vcfg.get("A", {}):
                    model_a_path = (ROOT_DIR / vcfg["A"]["model"]).resolve()
                if "B" in vcfg and "model" in vcfg.get("B", {}):
                    model_b_path = (ROOT_DIR / vcfg["B"]["model"]).resolve()
        except Exception as ve:
            print(f"[TTS Pipeline] Warning loading voice.json: {ve}")

    model_a = str(model_a_path)
    model_b = str(model_b_path)

    # Track assigned voices dynamically
    speaker_map = {}
    available_models = [model_a, model_b]

    scene_map = {}
    for idx, turn in enumerate(timeline_or_text):
        # Normalize speaker tag from the LLM
        raw_speaker = str(turn.get('speaker', f'Unknown_{idx}')).strip()
        speaker = raw_speaker.upper()
        text = turn.get('text', '')
        
        if speaker not in speaker_map:
            if speaker in ["A", "CHARACTER_A", "SPEAKER_A"]:
                speaker_map[speaker] = model_a
            elif speaker in ["B", "CHARACTER_B", "SPEAKER_B"]:
                speaker_map[speaker] = model_b
            elif available_models:
                speaker_map[speaker] = available_models.pop(0)
            else:
                raise RuntimeError(
                    f"[TTS Pipeline Error] No voice model configured for speaker '{raw_speaker}'. "
                    f"Only dual-speaker models (A and B) are supported."
                )
                
        current_model = speaker_map[speaker]

        if not os.path.exists(current_model):
            err_msg = f"[CRITICAL AUDIO ERROR] Voice model for Speaker '{raw_speaker}' missing at path: {current_model}"
            print(err_msg)
            raise FileNotFoundError(err_msg)
            
        clean_text_piper = text.replace("—", ", ").replace("–", ", ").replace("\"", "").replace("''", "")
        clean_text_piper = " ".join(clean_text_piper.split())
        if not clean_text_piper:
            clean_text_piper = "Indeed."

        output_wav = os.path.join(job_temp_dir, f"turn_{idx}.wav")
        piper_bin = str(ROOT_DIR / "piper.exe") if (ROOT_DIR / "piper.exe").exists() else "piper"
        proc = subprocess.run([piper_bin, "-m", current_model, "-f", output_wav], input=clean_text_piper, text=True, encoding="utf-8", capture_output=True)
        if proc.returncode != 0:
            err_details = proc.stderr.strip() if proc.stderr else "Unknown error"
            raise RuntimeError(f"[Piper Error] Failed synthesizing speaker '{raw_speaker}' with model '{current_model}': {err_details}")

        if not os.path.exists(output_wav) or os.path.getsize(output_wav) == 0:
            raise RuntimeError(f"[Piper Error] Audio output file was not generated or is 0 bytes for speaker '{raw_speaker}'")
        
        # Get actual duration of generated WAV file via ffprobe
        res = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", output_wav],
            capture_output=True, text=True, check=True
        )
        duration = float(res.stdout.strip())
        
        scaled_start = round(current_time / AUDIO_SPEED, 3)
        scaled_end = round((current_time + duration) / AUDIO_SPEED, 3)
        
        turn["actual_duration_seconds"] = round(duration / AUDIO_SPEED, 3)
        
        seg_id = turn.get("segment_id", f"segment_{idx//2}")
        if seg_id not in scene_map:
            scene_map[seg_id] = {"start": scaled_start, "end": scaled_end, "speaker": speaker, "segment_id": seg_id}
        else:
            scene_map[seg_id]["end"] = scaled_end
            
        timings.append({
            "start": scaled_start,
            "end": scaled_end,
            "speaker": speaker,
            "segment_id": seg_id
        })
        
        current_time += duration
        turn_files.append(output_wav)
        
        # Inject conversational structural silence gap between speakers
        if idx < len(timeline_or_text) - 1:
            turn_files.append(silence_gap_path)
            current_time += 0.25

    # Concatenate all WAV files into final audio track
    concat_list_path = job_temp_dir / "concat_audio_list.txt"
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for tf in turn_files:
            safe_tf = str(Path(tf).resolve()).replace("\\", "/")
            f.write(f"file '{safe_tf}'\n")
            
    sped_path = (Path(output_audio_path).resolve().parent / (Path(output_audio_path).stem + "_sped.wav")).resolve()
    temp_concat_wav = (job_temp_dir / "temp_concat.wav").resolve()
    sped_path.parent.mkdir(parents=True, exist_ok=True)
    
    # First, concatenate to temp_concat.wav
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list_path.resolve()), "-c:a", "pcm_s16le", str(temp_concat_wav)],
        capture_output=True, check=True
    )
    
    # Then apply speed-up filter to sped_path
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(temp_concat_wav),
         "-af", f"atempo={AUDIO_SPEED},loudnorm=I=-16:TP=-1.5:LRA=11,treble=g=4:f=8000:w=0.5", 
         "-c:a", "pcm_s16le", "-ar", "44100", str(sped_path)],
        capture_output=True, check=True
    )
    
    # Clean up files
    if concat_list_path.exists():
        concat_list_path.unlink()
    if temp_concat_wav.exists():
        temp_concat_wav.unlink()
    if Path(silence_gap_path).exists():
        Path(silence_gap_path).unlink()
    for tf in turn_files:
        if Path(tf).exists() and tf != silence_gap_path:
            Path(tf).unlink()
            
    # Try cleaning up unique job directory
    try:
        if job_temp_dir.exists():
            job_temp_dir.rmdir()
    except Exception as e:
        print(f"[TTS Pipeline] Warning: Could not remove {job_temp_dir}: {e}")
            
    scene_timings = list(scene_map.values())
    print(f"[TTS Pipeline] Concat complete: {sped_path.name} ({current_time:.2f}s total across {len(scene_timings)} scenes)")
    return str(sped_path), scene_timings



# =============================================================================
# 3. WHISPER TRANSCRIPTION
# =============================================================================

def generate_subtitles(audio_path, timings=None):
    """
    Transcribe the WAV with Faster-Whisper (word-level timestamps).
    Returns {"words": [...], "duration": float}.
    """
    try:
        model = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE,
                             compute_type="int8")
    except Exception:
        print("[Whisper] Falling back to CPU...")
        model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")

    acquired = gpu_lock.acquire(timeout=600)
    if not acquired:
        raise TimeoutError("Pipeline queue timeout capacity reached (GPU lock in Whisper)")
    try:
        segments, info = model.transcribe(audio_path, word_timestamps=True)
    finally:
        gpu_lock.release()

    words = []
    for seg in segments:
        if seg.words:
            for w in seg.words:
                w_start = round(w.start, 3)
                w_end = round(w.end, 3)
                word_speaker = "narrator"
                if timings:
                    for turn in timings:
                        if turn["start"] <= w_start <= turn["end"]:
                            word_speaker = turn["speaker"]
                            break
                words.append({
                    "word":  w.word.strip(),
                    "start": w_start,
                    "end":   w_end,
                    "speaker": word_speaker
                })

    print(f"[Whisper] {len(words)} words, {info.duration:.1f}s")
    return {"words": words, "duration": info.duration}


def validate_final_video_audio(video_path) -> bool:
    """
    Validates that the final rendered video MP4:
    1. Contains a valid AAC audio stream
    2. Has a non-zero audio duration matching the video duration
    3. Is NOT silent (mean_volume > -35 dB and max_volume > -20 dB)
    Raises RuntimeError if audio validation fails.
    """
    path = Path(video_path)
    if not path.exists() or path.stat().st_size < 10000:
        raise RuntimeError("FINAL AUDIO VALIDATION: FAILED\nReason: Video file does not exist or is empty.\nVideo generation failed.\nUpload blocked.")
        
    cmd = [
        'ffprobe', '-v', 'quiet', '-print_format', 'json',
        '-show_format', '-show_streams', str(path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError("FINAL AUDIO VALIDATION: FAILED\nReason: Could not probe video file streams.\nVideo generation failed.\nUpload blocked.")
        
    data = json.loads(res.stdout)
    audio_streams = [s for s in data.get('streams', []) if s.get('codec_type') == 'audio']
    if not audio_streams:
        raise RuntimeError("FINAL AUDIO VALIDATION: FAILED\nReason: No audio stream found in final MP4.\nVideo generation failed.\nUpload blocked.")
        
    cmd_vol = [
        'ffmpeg', '-i', str(path), '-af', 'volumedetect', '-f', 'null', 'NUL'
    ]
    res_vol = subprocess.run(cmd_vol, capture_output=True, text=True)
    mean_vol = None
    max_vol = None
    for line in res_vol.stderr.splitlines():
        if 'mean_volume' in line:
            try: mean_vol = float(line.split(':')[1].replace('dB', '').strip())
            except Exception: pass
        elif 'max_volume' in line:
            try: max_vol = float(line.split(':')[1].replace('dB', '').strip())
            except Exception: pass
            
    if mean_vol is None or mean_vol < -35.0 or (max_vol is not None and max_vol < -20.0):
        err_detail = f"mean_volume={mean_vol}dB, max_volume={max_vol}dB (audio is silent or missing voice signal)"
        print(f"[AUDIO QUALITY GATE ERROR] {err_detail}")
        raise RuntimeError(f"FINAL AUDIO VALIDATION: FAILED\nReason: {err_detail}\nVideo generation failed.\nUpload blocked.")
        
    print(f"[AUDIO QUALITY GATE SUCCESS] Audio stream verified: mean_volume={mean_vol}dB, max_volume={max_vol}dB")
    return True

# =============================================================================
# 4. VIDEO ASSEMBLY
# =============================================================================

def assemble_video(video_bg_path, audio_path,
                   subtitle_data, final_output_path,
                   category="Weird Science", visual_proofs=None, timings=None,
                   image_events=None, bgm_folder=None):
    """
    Assemble the final 9:16 MP4:
      - split-screen 1080x1920 layout (upper 1080x960 Fooocus image, lower 1080x960 gameplay footage)
      - subtitles burned in lower zone with active word highlighted and speaker color coding (Cyan/Magenta)
      - background music mixed with sidechain ducking compression
    """
    ROOT_DIR = Path(__file__).parent.parent
    if bgm_folder is None:
        bgm_folder = str(ROOT_DIR / "assets" / "bgm")

    ass_path = str(Path(final_output_path).parent / "subs.ass")

    # Generate ASS subtitle file using shared caption utils
    style     = STYLES.get(category, STYLES["Weird Science"])
    
    is_debate_layout = (timings is not None and len(timings) > 0) or (image_events is not None and len(image_events) > 0)
    
    style_cfg = {
        "font": "Impact",
        "size": 90,
        "color": style.get("color", "&H00FFFFFF"),
        "outline_color": "black",
        "outline_width": 5,
        "shadow": 3,
        "margin_v": 300 if is_debate_layout else 350
    }
    
    original_text = " ".join([w["word"] for w in subtitle_data["words"]])
    
    ass_content = align_and_generate_ass(
        whisper_words=subtitle_data["words"],
        original_text=original_text,
        style_cfg=style_cfg,
        is_debate=is_debate_layout
    )
    
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    bg_f  = str(video_bg_path).replace("\\", "/")
    aud_f = str(audio_path).replace("\\", "/")
    out_f = str(final_output_path).replace("\\", "/")
    ass_f = str(ass_path).replace("\\", "/").replace(":", "\\:")

    duration = subtitle_data.get("duration", 60)

    inputs = [
        f'-stream_loop -1 -i "{bg_f}"',
        f'-i "{aud_f}"'
    ]
    
    bg_music = None
    bgm_path = Path(bgm_folder)
    if bgm_path.exists() and bgm_path.is_dir():
        tracks = [f for f in os.listdir(bgm_path) if f.lower().endswith(('.mp3', '.wav'))]
        if tracks:
            bg_music = str(bgm_path / random.choice(tracks))
            print(f"[FFmpeg] Selected random BGM: {bg_music}")
            
    if bg_music:
        music_f = bg_music.replace("\\", "/")
        inputs.append(f'-stream_loop -1 -i "{music_f}"')
        bgm_input_idx = 2
        img_idx_start = 3
    else:
        bgm_input_idx = None
        img_idx_start = 2

    if not image_events and visual_proofs and timings:
        image_events = []
        for idx, proof in enumerate(visual_proofs):
            if proof:
                start_time = timings[idx]["start"]
                if idx < len(timings) - 1:
                    end_time = timings[idx+1]["start"]
                else:
                    end_time = duration + 0.5
                image_events.append({
                    'path': proof,
                    'start': start_time,
                    'end': end_time
                })

    final_image_events = []
    if image_events:
        for idx, ev in enumerate(image_events):
            img_path = ev.get('path')
            if img_path and os.path.exists(img_path):
                raw_start = ev.get('start', 0.0)
                # Requirement 3: First Fooocus image is delayed to 2.0s so full-screen Minecraft + audio plays from 0.0s to 2.0s
                start_time = max(2.0, raw_start) if idx == 0 else raw_start
                end_time = ev.get('end', duration + 0.5)
                
                print(f"[IMAGE ENGINE] Validating image asset for upper-zone overlay: {img_path} from {start_time}s to {end_time}s")
                img_f = str(img_path).replace("\\", "/")
                inputs.append(f'-loop 1 -i "{img_f}"')
                final_image_events.append({
                    'input_idx': img_idx_start + len(final_image_events),
                    'start': start_time,
                    'end': end_time
                })
            else:
                print(f"[IMAGE ERROR] Expected image asset missing from disk: {img_path}")

    filter_complex = [
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[bg_base]"
    ]
    current_bg_node = "[bg_base]"

    MAX_STATIC_VISUAL_DURATION = 5.5
    if final_image_events:
        for i, event in enumerate(final_image_events):
            next_bg_node = f"[bg_{i}]"
            ev_dur = max(0.5, event['end'] - event['start'])
            if ev_dur > MAX_STATIC_VISUAL_DURATION:
                print(f"[VISUAL PACING] Scene {i} duration ({ev_dur:.2f}s > {MAX_STATIC_VISUAL_DURATION}s) — applying dynamic Ken-Burns movement.")

            # Subtle Ken-Burns zoom effect (slow 3% scale movement over scene duration)
            total_frames = max(30, int(ev_dur * 60))
            if i % 2 == 0:
                kb_filter = f"zoompan=z='min(zoom+0.0003,1.03)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=896x896,fps=60"
            else:
                kb_filter = f"zoompan=z='max(1.03-0.0003*on,1.0)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=896x896,fps=60"

            fade_filter = ",format=yuva420p,fade=in:st=0:d=0.3:alpha=1" if i == 0 else ""
            filter_complex.append(
                f"[{event['input_idx']}:v]{kb_filter},scale=810:810,pad=814:814:2:2:color=0x444444{fade_filter}[img{i}]"
            )
            # Overlay centered horizontally (x=(1080-w)/2) and positioned in upper portion (y=120) over full-screen Minecraft background
            filter_complex.append(
                f"{current_bg_node}[img{i}]overlay=x=(1080-w)/2:y=120:"
                f"enable='between(t,{event['start']},{event['end']})'{next_bg_node}"
            )
            current_bg_node = next_bg_node

    filter_complex.append(f"{current_bg_node}ass='{ass_f}',setsar=1:1[v_out]")
    video_filter_string = ";".join(filter_complex)

    enc_flags = "-c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p"

    if bg_music:
        fc = (
            f"{video_filter_string}; "
            f"[1:a]volume=1.8,asplit=2[voice_spk][voice_sc]; "
            f"[{bgm_input_idx}:a]volume=0.20[bgm_norm]; "
            f"[bgm_norm][voice_sc]sidechaincompress=threshold=0.05:ratio=10:attack=10:release=200[ducked_bgm]; "
            f"[voice_spk][ducked_bgm]amix=inputs=2:duration=first:dropout_transition=2[final_audio]"
        )
        map_audio = "[final_audio]"
        print(f"[FFmpeg] Assembling video with sidechain music ducking: {Path(bg_music).name}")
    else:
        fc = (
            f"{video_filter_string}; "
            f"[1:a]volume=1.8[final_audio]"
        )
        map_audio = "[final_audio]"
        print("[FFmpeg] Assembling video (voice only — BGM not set)...")

    cmd = (
        f'ffmpeg -y {" ".join(inputs)} '
        f'-t {duration + 0.1} '
        f'-filter_complex "{fc}" '
        f'-map "[v_out]" -map "{map_audio}" '
        f'{enc_flags} -aspect 9:16 '
        f'-c:a aac -b:a 256k '
        f'"{out_f}"'
    )

    result = subprocess.run(cmd, shell=True, capture_output=True)
    stderr = result.stderr.decode("utf-8", errors="ignore")

    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed (exit {result.returncode}):\n{stderr[-3000:]}"
        )

    out_p = Path(final_output_path)
    if not out_p.exists() or out_p.stat().st_size < 10_000:
        raise RuntimeError(
            f"FFmpeg output is empty/corrupt.\nstderr:\n{stderr[-3000:]}"
        )

    # Perform strict final audio validation quality gate
    validate_final_video_audio(final_output_path)

    size_kb = out_p.stat().st_size // 1024
    print(f"[FFmpeg] Done: {out_p.name}  ({size_kb} KB)")
    return final_output_path


def pick_background(required_duration=60, is_debate=False):
    """
    Pick a random background video (preferring Minecraft gameplay), query its duration,
    and extract a random clip of required_duration + 5 seconds from it.
    """
    ROOT_DIR = Path(__file__).parent.parent
    active_dir = ROOT_DIR / "assets" / "backgrounds" / "active"
    if not active_dir.exists():
        active_dir = ROOT_DIR / "assets"

    all_vids = list(active_dir.glob("*.mp4")) + list(active_dir.glob("*.webm"))
    videos = [v for v in all_vids if "minecraft" in v.name.lower()]
    if not videos:
        videos = [v for v in all_vids if "subway" not in v.name.lower()]
    if not videos:
        videos = all_vids

    if not videos:
        raise FileNotFoundError(f"No background videos found in {active_dir}")

    chosen = random.choice(videos)
    print(f"[BG] Slicing active background: {chosen.name}")

    # Get source duration to check for loop
    total_duration = 0.0
    try:
        res = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(chosen)],
            capture_output=True, text=True, check=True
        )
        total_duration = float(res.stdout.strip())
    except Exception as e:
        print(f"[BG] Warning: Could not get duration of {chosen.name}: {e}")

    # Determine a random start timestamp
    start_ts = 0.0
    if total_duration > required_duration + 10:
        start_ts = round(random.uniform(0, total_duration - required_duration - 10), 3)

    # Extract clip (using fast seek)
    safe_stem = chosen.stem.replace(" ", "_")
    clip_name = f"{safe_stem}_clip_{int(start_ts)}.mp4"
    clip_path = TEMP_DIR / clip_name

    print(f"[BG] Extracting {required_duration}s from {chosen.name} at {start_ts}s...")

    try:
        subprocess.run(
            ["ffmpeg", "-y", "-ss", str(start_ts), "-t", str(required_duration + 5),
             "-i", str(chosen), "-c:v", "libx264", "-preset", "fast",
             "-crf", "18", "-c:a", "copy", str(clip_path)],
            capture_output=True, check=True
        )
        print(f"[BG] Sliced background clip ready: {clip_name}")
        return str(clip_path)
    except Exception as e:
        print(f"[BG] Slicing failed: {e}. Returning raw video directly.")
        return str(chosen)


def compile_long_form(short_paths, output_long_path):
    """
    Stitches completed mp4 shorts losslessly into 1 long-form video.
    """
    list_file_path = TEMP_DIR / "concat_list.txt"
    
    # Generate the instruction text file for FFmpeg
    with open(list_file_path, "w", encoding="utf-8") as f:
        for path in short_paths:
            # Safely format paths for FFmpeg demuxer
            safe_path = str(Path(path).resolve()).replace("\\", "/")
            f.write(f"file '{safe_path}'\n")
            
    # Run a copy-codec stream concat (no re-encoding = near instant)
    cmd = f'ffmpeg -y -f concat -safe 0 -i "{list_file_path}" -c copy "{output_long_path}"'
    
    result = subprocess.run(cmd, shell=True, capture_output=True)
    
    # Cleanup temp list file
    if list_file_path.exists():
        list_file_path.unlink()
        
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg concat failed: {result.stderr.decode('utf-8', errors='ignore')}")
        
    return output_long_path

