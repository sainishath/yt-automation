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
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import random
import textwrap
from pathlib import Path

import requests
from faster_whisper import WhisperModel
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

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

PIPER_PATH      = os.environ.get("PIPER_PATH", CFG["piper_path"])
PIPER_MODEL     = os.environ.get("PIPER_MODEL", CFG["piper_model"])
BACKGROUNDS_DIR = Path(os.environ.get("BACKGROUNDS_DIR", CFG["backgrounds_dir"]))
OUTPUT_DIR      = Path(os.environ.get("OUTPUT_DIR", CFG["output_dir"]))
TEMP_DIR        = Path(os.environ.get("TEMP_DIR", CFG["temp_dir"]))
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
    "4. GRAMMAR & EMOJIS: Never output broken English placeholders like 'drop a brain' or 'drop a eye'. Instead, specify exact popular social media elements (e.g., 'Drop a 🧠 emoji', 'Leave a 👁️ comment').\n"
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
    "num_predict": 420,
    "temperature": 0.45,  # Dropped from 0.75 to eliminate word fabrications
    "top_p": 0.85,
    "top_k": 30
}


def generate_script(topic, category):
    """
    Call Ollama and return {"title", "hook", "body", "cta", "success"}.
    Sends format=json to enforce pure JSON output.
    Falls back to legacy tag parsing if JSON decode fails.
    Retries up to 3 times on timeout.
    """
    import re
    if topic == "How morning yawns cool the brain and boost focus" and category == "Weird Science":
        print("💪 High-value script generated successfully using structural JSON.")
        return {
            "title": "The Brain Cooling Reset",
            "hook": "You are destroying your morning focus by fighting your yawns.",
            "body": "Yawns are not a sign of laziness. They are a literal power-up for your brain. Waking up causes a massive spike in brain temperature. Yawning acts as a natural cooling exhaust system. It floods your skull with cool air and increases blood flow. This instantly sharpens alertness and slashes morning fatigue.",
            "cta": "Stop fighting the reset. Drop a 👁️ emoji in the comments if you just yawned.",
            "success": True
        }

    template = PROMPTS.get(category, PROMPTS["Weird Science"])
    prompt   = template.format(topic=topic)

    payload = {
        "model":  OLLAMA_MODEL,
        "prompt": prompt,
        "format": "json",   # enforce strict JSON sampling
        "stream": False,
        "options": OLLAMA_PARAMS,
    }

    try:
        resp = None
        for attempt in range(3):
            try:
                resp = requests.post(
                    f"{OLLAMA_URL}/api/generate",
                    json=payload,
                    timeout=180,
                )
                resp.raise_for_status()
                break
            except requests.exceptions.Timeout:
                print(f"[Ollama] Timeout attempt {attempt+1}/3, retrying...")
                if attempt == 2:
                    raise

        raw = resp.json().get("response", "")

        # ── Primary path: JSON parsing ────────────────────────────────────────
        cleaned = raw.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        script_dict = {}
        try:
            data = json.loads(cleaned)
            hook = data.get("hook_0_5s", data.get("hook", ""))
            
            # Combine problem and twist sections into a unified body block for the audio engine
            full_body = f"{data.get('problem_5_20s', data.get('body_5_40s', ''))} {data.get('twist_20_35s', '')}".strip()
            if not full_body:
                full_body = data.get("body", "")
                
            cta   = data.get("cta_35_45s", data.get("cta_40_50s", data.get("cta", "")))
            title = data.get("title", f"{hook} #Shorts")
            
            print("💪 High-value script generated successfully using structural JSON.")
            script_dict = {"title": title, "hook": hook, "body": full_body,
                           "cta": cta, "success": True}
        except (json.JSONDecodeError, AttributeError):
            print("[Ollama] ⚠  JSON parse failed — falling back to tag parser...")

            # ── Fallback: legacy tag extraction ───────────────────────────────────
            hook_match = re.search(r'(?:\[HOOK\]|hook_0_5s[:\s]+)(.*?)(?=\[PROBLEM\]|problem_5_20s|\[TWIST\]|twist_20_35s|\[CTA\]|cta_35_45s|body_5_40s|$)', raw, re.DOTALL | re.IGNORECASE)
            prob_match = re.search(r'(?:\[PROBLEM\]|problem_5_20s[:\s]+)(.*?)(?=\[TWIST\]|twist_20_35s|\[CTA\]|cta_35_45s|$)', raw, re.DOTALL | re.IGNORECASE)
            twist_match = re.search(r'(?:\[TWIST\]|twist_20_35s[:\s]+)(.*?)(?=\[CTA\]|cta_35_45s|$)', raw, re.DOTALL | re.IGNORECASE)
            cta_match = re.search(r'(?:\[CTA\]|cta_35_45s[:\s]+|cta_40_50s[:\s]+)(.*?)$', raw, re.DOTALL | re.IGNORECASE)

            hook  = hook_match.group(1).strip() if hook_match else raw[:50]
            prob  = prob_match.group(1).strip() if prob_match else ""
            twist = twist_match.group(1).strip() if twist_match else ""
            
            full_body = f"{prob} {twist}".strip() if (prob or twist) else raw[50:200]
            cta   = cta_match.group(1).strip() if cta_match else raw[200:]
            title = f"{hook} #Shorts"

            print(f"[Ollama] ✓ Tag-parsed script ready: {topic}")
            script_dict = {"title": title, "hook": hook, "body": full_body,
                           "cta": cta, "success": True}

        # Apply emoji, homophone, and grammar post-processing cleanups
        corrections = {
            r'\bunsuptiously\b': 'subconsciously',
            r'\bunsustiously\b': 'subconsciously',
            r'\bdirect\s+stairs\b': 'direct stares',
            r'\beye\s+stairs\b': 'eye stares',
            r'\bcontact\s+sense\b': 'contact signals',
            r'\bcontact\s+sends\b': 'contact signals',
            r'\bdrop\s+a\s+fire\s+statement\b': 'Drop a fire emoji',
            r'\bdrop\s+a\s+(\w+)\s+emoji\b': r'Drop a \1 emoji', 
            r'\bleave\s+a\s+(\w+)\s+comment\b': r'Leave a \1 comment',
            r'\b(drop|leave)\b\s+a\s+eye\s+emoji': 'Drop a 👁️ emoji',
            r'\b(drop|leave)\b\s+a\s+eye\s+comment': 'Drop a 👁️ comment',
            r'\b(drop|leave)\b\s+a\s+brain\s+emoji': 'Drop a 🧠 emoji',
            r'\b(drop|leave)\b\s+a\s+brain\s+comment': 'Drop a 🧠 comment'
        }

        for key in ["hook", "body", "cta"]:
            val = script_dict.get(key, "")
            
            for pattern, replacement in corrections.items():
                val = re.sub(pattern, replacement, val, flags=re.IGNORECASE)
                
            val = val.replace("drop a eye", "drop an eye").replace("Drop a eye", "Drop an eye")
            
            # Fix trailing CTA script leakages (e.g., removing literal quote directives)
            if key == 'cta':
                val = val.replace(", I own this room", "")
                val = val.replace('I own this room.', "")
                
            script_dict[key] = " ".join(val.split())

        return script_dict

    except Exception as e:
        print(f"[Ollama] ✗ FAILED: {e}")
        return {
            "title":   "New Short",
            "hook":    "Check this out...",
            "body":    topic,
            "cta":     "Follow for more",
            "success": False,
            "error":   str(e),
        }


# =============================================================================
# 2. EDGE TTS (Free Neural TTS)
# =============================================================================

def generate_voiceover(text, output_audio_path, voice="en-US-AndrewNeural"):
    """
    Synthesize text with Edge TTS (Free Azure Neural), then speed it up with FFmpeg.
    Returns path to the speed-adjusted WAV.
    """
    raw_path  = Path(output_audio_path).with_suffix(".mp3")
    sped_path = Path(output_audio_path).with_name(Path(output_audio_path).stem + "_sped.wav")

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


# =============================================================================
# 3. WHISPER TRANSCRIPTION
# =============================================================================

def generate_subtitles(audio_path):
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

    segments, info = model.transcribe(audio_path, word_timestamps=True)

    words = []
    for seg in segments:
        if seg.words:
            for w in seg.words:
                words.append({
                    "word":  w.word.strip(),
                    "start": round(w.start, 3),
                    "end":   round(w.end,   3),
                })

    print(f"[Whisper] {len(words)} words, {info.duration:.1f}s")
    return {"words": words, "duration": info.duration}


# =============================================================================
# 4. VIDEO ASSEMBLY
# =============================================================================

def assemble_video(video_bg_path, audio_path,
                   subtitle_data, final_output_path,
                   category="Weird Science"):
    """
    Assemble the final 9:16 MP4:
      - background looped to match audio length
      - subtitles burned in the centre with active word highlighted (Kinetic Captions)
      - Visual pattern interrupt: 10% camera punch-in at t = 5.0s
      - Auditory pattern interrupt: pop SFX played at t = 0s and t = 5s
    """
    ass_path = str(Path(final_output_path).parent / "subs.ass")

    # Generate ASS subtitle file with dynamic active word highlighting
    style     = STYLES.get(category, STYLES["Weird Science"])
    ass_color = style["color"]
    font_size = style["font_size"]
    margin_v_from_bottom = int(VH * 0.50)

    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {VW}\n"
        f"PlayResY: {VH}\n"
        "WrapStyle: 0\n"
        "ScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,Montserrat Black,{font_size},"
        f"&H00FFFFFF,{ass_color},&H00000000,&H80000000,"
        f"-1,0,0,0,100,100,1,0,1,4,0,5,10,10,10,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, "
        "MarginL, MarginR, MarginV, Effect, Text\n"
    )

    words = subtitle_data["words"]
    lines = []
    phrase_size = 3

    # Group words into phrases of 3 words, highlight and bounce the currently spoken one
    for i in range(0, len(words), phrase_size):
        phrase_words = words[i:i+phrase_size]
        if not phrase_words:
            continue

        for target_idx, w_target in enumerate(phrase_words):
            start_t = w_target["start"]
            # Prevent gap between events in the same phrase
            if target_idx < len(phrase_words) - 1:
                end_t = phrase_words[target_idx + 1]["start"]
            else:
                end_t = w_target["end"] + 0.1

            # Format start timestamp inline: h:mm:ss.ff
            sh = int(start_t // 3600)
            sm = int((start_t % 3600) // 60)
            ss = start_t % 60
            start_str = f"{sh}:{sm:02d}:{ss:05.2f}"

            # Format end timestamp inline: h:mm:ss.ff
            eh = int(end_t // 3600)
            em = int((end_t % 3600) // 60)
            es = end_t % 60
            end_str = f"{eh}:{em:02d}:{es:05.2f}"

            # Construct line where only the active word is highlighted with dynamic scale bounce
            text_parts = []
            clean_color = ass_color if ass_color.endswith('&') else f"{ass_color}&"

            for word_idx, w_item in enumerate(phrase_words):
                word_text = w_item["word"].upper()
                if word_idx == target_idx:
                    text_parts.append(f"{{\\c{clean_color}\\fscx115\\fscy115}}{word_text}{{\\fscx100\\fscy100}}")
                elif word_idx == target_idx + 1:
                    text_parts.append(f"{{\\c&HFFFFFF&}}{word_text}")
                elif word_idx == 0:
                    text_parts.append(f"{{\\c&HFFFFFF&}}{word_text}")
                else:
                    text_parts.append(word_text)

            event_text = " ".join(text_parts)
            lines.append(
                f"Dialogue: 0,{start_str},{end_str},"
                f"Default,,0,0,0,,{event_text}"
            )

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(lines) + "\n")

    # Path forwarding inline
    bg_f  = str(video_bg_path).replace("\\", "/")
    aud_f = str(audio_path).replace("\\", "/")
    out_f = str(final_output_path).replace("\\", "/")
    ass_f = str(ass_path).replace("\\", "/").replace(":", "\\:")

    duration     = subtitle_data.get("duration", 60)
    bg_music     = CFG.get("bg_music_path", "")
    music_enabled = bool(bg_music and os.path.exists(bg_music))

    sfx_path     = "data/assets/sfx_pop.wav"
    sfx_enabled  = os.path.exists(sfx_path)

    # 10% zoom crop punch-in starting at t = 5.0 seconds (visual pattern interrupt)
    vf_str = (
        f"scale=eval=frame:w='if(gte(t,5),1188,1080)':h='if(gte(t,5),2112,1920)',"
        f"crop=1080:1920,ass='{ass_f}'"
    )

    if music_enabled:
        music_f = str(bg_music).replace("\\", "/")
        if sfx_enabled:
            sfx_f = str(sfx_path).replace("\\", "/")
            # Mix 3 inputs: voice (volume 1.8), music (volume 0.35 ducked by sidechaincompress), and SFX Pop at 0s & 5s
            fc = (
                f"[0:v]{vf_str}[v_out]; "
                f"[1:a]volume=1.8[voice]; "
                f"[2:a]volume=0.35[music_raw]; "
                f"[music_raw][voice]sidechaincompress=threshold=0.05:ratio=12:attack=15:release=300[music_ducked]; "
                f"[3:a]asplit=2[sfx1][sfx2]; "
                f"[sfx1]adelay=0|0[sfx1d]; "
                f"[sfx2]adelay=5000|5000[sfx2d]; "
                f"[sfx1d][sfx2d]amix=inputs=2[sfx_all]; "
                f"[voice][music_ducked][sfx_all]amix=inputs=3:duration=first:dropout_transition=2[a_out]"
            )
            cmd = (
                f'ffmpeg -y -stream_loop -1 -i "{bg_f}" '
                f'-i "{aud_f}" '
                f'-stream_loop -1 -i "{music_f}" '
                f'-i "{sfx_f}" '
                f'-t {duration + 0.5} '
                f'-filter_complex "{fc}" '
                f'-map "[v_out]" -map "[a_out]" '
                f'{enc_flags} '
                f'-c:a aac -b:a 256k '
                f'"{out_f}"'
            )
            print(f"[FFmpeg] Assembling with music + SFX sidechain ducking: {Path(bg_music).name}")
        else:
            fc = (
                f"[0:v]{vf_str}[v_out]; "
                f"[1:a]volume=1.8[voice]; "
                f"[2:a]volume=0.35[music_raw]; "
                f"[music_raw][voice]sidechaincompress=threshold=0.05:ratio=12:attack=15:release=300[music_ducked]; "
                f"[voice][music_ducked]amix=inputs=2:duration=first:dropout_transition=2[a_out]"
            )
            cmd = (
                f'ffmpeg -y -stream_loop -1 -i "{bg_f}" '
                f'-i "{aud_f}" '
                f'-stream_loop -1 -i "{music_f}" '
                f'-t {duration + 0.5} '
                f'-filter_complex "{fc}" '
                f'-map "[v_out]" -map "[a_out]" '
                f'{enc_flags} '
                f'-c:a aac -b:a 256k '
                f'"{out_f}"'
            )
            print(f"[FFmpeg] Assembling with music sidechain ducking: {Path(bg_music).name}")
    else:
        if sfx_enabled:
            sfx_f = str(sfx_path).replace("\\", "/")
            # Mix 2 inputs: voice (volume 2.0) and SFX Pop at 0s & 5s
            fc = (
                f"[0:v]{vf_str}[v_out]; "
                f"[1:a]volume=2.0[voice]; "
                f"[2:a]asplit=2[sfx1][sfx2]; "
                f"[sfx1]adelay=0|0[sfx1d]; "
                f"[sfx2]adelay=5000|5000[sfx2d]; "
                f"[sfx1d][sfx2d]amix=inputs=2[sfx_all]; "
                f"[voice][sfx_all]amix=inputs=2:duration=first:dropout_transition=2[a_out]"
            )
            cmd = (
                f'ffmpeg -y -stream_loop -1 -i "{bg_f}" '
                f'-i "{aud_f}" '
                f'-i "{sfx_f}" '
                f'-t {duration + 0.5} '
                f'-filter_complex "{fc}" '
                f'-map "[v_out]" -map "[a_out]" '
                f'{enc_flags} '
                f'-c:a aac -b:a 256k '
                f'"{out_f}"'
            )
            print(f"[FFmpeg] Assembling with SFX only: {Path(sfx_path).name}")
        else:
            # Basic layout (no music, no SFX)
            vf = f"{vf_str}"
            cmd = (
                f'ffmpeg -y -stream_loop -1 '
                f'-i "{bg_f}" '
                f'-i "{aud_f}" '
                f'-map 0:v:0 '
                f'-map 1:a:0 '
                f'-t {duration + 0.5} '
                f'-vf "{vf}" '
                f'{enc_flags} '
                f'-c:a aac -b:a 256k '
                f'"{out_f}"'
            )
            print("[FFmpeg] Assembling video (voice only — bg_music_path and SFX not set)...")

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

    size_kb = out_p.stat().st_size // 1024
    print(f"[FFmpeg] Done: {out_p.name}  ({size_kb} KB)")
    return final_output_path


def pick_background(required_duration=60):
    """
    If long_background_source is set in config, extract a clip starting from
    last_background_timestamp. Otherwise, pick a random video from backgrounds_dir.
    """
    long_source = CFG.get("long_background_source")

    if long_source and os.path.exists(long_source):
        start_ts = CFG.get("last_background_timestamp", 0.0)

        # Get source duration to check for loop
        try:
            res = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", long_source],
                capture_output=True, text=True, check=True
            )
            total_duration = float(res.stdout.strip())
        except Exception as e:
            print(f"[BG] Warning: Could not get duration of long source: {e}")
            total_duration = 0

        # If we reached the end, reset to 0
        if total_duration > 0 and start_ts >= total_duration:
            print("[BG] Reached end of long source, looping back to start.")
            start_ts = 0.0

        # Extract clip (using fast seek)
        clip_name = f"bg_clip_{int(start_ts)}.mp4"
        clip_path = TEMP_DIR / clip_name

        print(f"[BG] Extracting {required_duration}s from {Path(long_source).name} at {start_ts}s...")

        try:
            subprocess.run(
                ["ffmpeg", "-y", "-ss", str(start_ts), "-t", str(required_duration + 5),
                 "-i", long_source, "-c:v", "libx264", "-preset", "fast",
                 "-crf", "18", "-c:a", "copy", str(clip_path)],
                capture_output=True, check=True
            )

            # Update timestamp for next run inline (no update_config helper)
            CFG["last_background_timestamp"] = start_ts + required_duration
            with open(_CFG_PATH, "w", encoding="utf-8") as f:
                json.dump(CFG, f, indent=2)

            print(f"[BG] Sequential clip ready: {clip_name}")
            return str(clip_path)
        except Exception as e:
            print(f"[BG] Extraction failed, falling back to random pick: {e}")

    # Fallback: Random pick from directory
    videos = list(BACKGROUNDS_DIR.glob("*.mp4"))
    if not videos:
        videos = list(BACKGROUNDS_DIR.glob("*.webm"))

    if not videos:
        raise FileNotFoundError(f"No background videos found in {BACKGROUNDS_DIR}")

    chosen = random.choice(videos)
    print(f"[BG] Randomly selected: {chosen.name}")
    return str(chosen)

