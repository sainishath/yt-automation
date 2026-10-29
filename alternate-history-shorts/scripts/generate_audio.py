# -*- coding: utf-8 -*-
"""
generate_audio.py
-----------------
Pipeline 1 Stage 2 TTS Audio Synthesis (Edge-TTS en-US-ChristopherNeural) +
Optional Multi-Language Dubbing (Spanish, Portuguese, German, Hindi via pipeline/tts.py).
"""

import os
import sys
import json
import re
import argparse
import subprocess
import logging
from pathlib import Path
from typing import Optional, List

_ROOT_REPO = Path(__file__).resolve().parent.parent.parent
if str(_ROOT_REPO) not in sys.path:
    sys.path.insert(0, str(_ROOT_REPO))

from pipeline.tts import synthesize_multilang_tracks

# Setup logging to pipeline.log and stdout
LOG_FILE = Path("pipeline.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

def clean_narration_text(text: str) -> str:
    """
    Sanitizes spoken narration text by aggressively removing LLM word-count metadata,
    bracketed notes, parenthetical annotations, and scene prefixes.
    """
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
        
    text = text.strip()
    text = re.sub(r'[\(\[\{]\s*(?:word\s*count\s*:?\s*)?\d+(?:\s*-\s*\d+)?\s*(?:spoken\s*)?words?\s*(?:total|approx)?[\)\]\}]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'[\(\[\{]\s*(?:word\s*count|words?)\b[^\)\]\}]*[\)\]\}]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'[\s,;—–-]+(?:word\s*count\s*:?\s*)?\d+(?:\s*-\s*\d+)?\s*(?:spoken\s*)?words?\s*(?:total|approx)?[\.\?!]?(?=$|[\s,;—–-])', '', text, flags=re.IGNORECASE)
    text = re.sub(r'[\(\[]?\b\d+\s*words?\b[\)\]]?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(?:scene\s*\d+|hook|narration)\s*:\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'[\(\[]\s*scene\s*\d+[^\]\)]*[\)\]]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'[\(\[\{]\s*[\)\]\}]', '', text)
    text = re.sub(r'\s+([,\.\?!])', r'\1', text)
    text = re.sub(r'\s{2,}', ' ', text)
    text = text.strip(' \t\n\r—–-"\'')
    
    if text and not text.endswith(('.', '!', '?', '."', '!"', '?"')):
        text += '.'
        
    return text.strip()

def get_audio_duration(file_path: Path) -> float:
    """Uses ffprobe to measure the actual duration of the generated audio file."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", str(file_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    metadata = json.loads(result.stdout)
    return float(metadata["format"]["duration"])

def generate_scene_audio(text: str, voice: str, out_path: Path, max_retries: int = 3) -> float:
    """Generates audio for a single scene using edge-tts, verifies it, and returns duration."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    clean_text = clean_narration_text(text)
    
    cmd = [
        "edge-tts",
        "--text", clean_text,
        "--voice", voice,
        "--write-media", str(out_path)
    ]
    
    for attempt in range(1, max_retries + 1):
        try:
            logging.info(f"Generating voice for scene to {out_path.name} (Attempt {attempt}/{max_retries})")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if not out_path.exists() or out_path.stat().st_size == 0:
                raise FileNotFoundError(f"Audio file was not created or is empty: {out_path}")
                
            duration = get_audio_duration(out_path)
            if duration <= 0.0:
                raise ValueError("Measured audio duration is 0 seconds")
                
            logging.info(f"Successfully generated {out_path.name}: {duration:.2f}s")
            return round(duration, 2)
            
        except Exception as e:
            logging.warning(f"Failed attempt {attempt} to generate {out_path.name}: {e}")
            if out_path.exists():
                try:
                    out_path.unlink()
                except Exception:
                    pass
                    
    raise RuntimeError(f"Failed to generate valid audio for scene after {max_retries} attempts.")

def process_video_audio(
    video_id: str,
    output_dir: str = "output",
    multilang: bool = False,
    languages: Optional[List[str]] = None
) -> dict:
    video_path = Path(output_dir) / video_id
    script_path = video_path / "script.json"
    
    if not script_path.exists():
        raise FileNotFoundError(f"script.json not found for {video_id} at {script_path}")
        
    _BASE_DIR = Path(__file__).parent.parent.resolve()
    voice_path = _BASE_DIR / "config" / "voice.json"
    if not voice_path.exists():
        voice_path = Path("config/voice.json")
    voice = "en-US-ChristopherNeural"
    if voice_path.exists():
        with open(voice_path, "r", encoding="utf-8") as f:
            voice = json.load(f).get("voice", voice)
            
    logging.info(f"Using narrator voice: {voice}")
    
    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)
        
    scenes = script.get("scenes", [])
    audio_dir = video_path / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    total_estimated = 0.0
    total_actual = 0.0
    
    print("\n==============================================")
    print(f"  Stage 2 TTS Audio Generation: {video_id} ")
    print("==============================================\n")
    print(f"{'Scene':<6} | {'Words':<5} | {'Est. (s)':<8} | {'Act. (s)':<8} | {'Delta (s)':<9}")
    print("-" * 50)
    
    full_narration_parts = []
    for idx, scene in enumerate(scenes):
        narration = clean_narration_text(scene.get("narration", ""))
        scene["narration"] = narration
        full_narration_parts.append(narration)
        words = len(narration.split())
        est_duration = scene.get("estimated_duration_seconds", 0.0)
        total_estimated += est_duration
        
        out_path = audio_dir / f"scene_{idx:03d}.mp3"
        actual_duration = generate_scene_audio(narration, voice, out_path)
        total_actual += actual_duration
        scene["actual_duration_seconds"] = actual_duration
        
        delta = actual_duration - est_duration
        print(f"#{idx:<4} | {words:<5} | {est_duration:<8.1f} | {actual_duration:<8.2f} | {delta:<+9.2f}")

    multilang_tracks = {}
    if multilang:
        try:
            full_text = " ".join(full_narration_parts)
            multilang_tracks = synthesize_multilang_tracks(full_text, audio_dir / "multilang", languages=languages)
            script["multilang_audio_tracks"] = multilang_tracks
            logging.info(f"Generated multi-language audio tracks: {list(multilang_tracks.keys())}")
        except Exception as mle:
            logging.warning(f"Multi-language track generation warning: {mle}")
        
    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)
        
    total_delta = total_actual - total_estimated
    print("-" * 50)
    print(f"Total  | {'-':<5} | {total_estimated:<8.1f} | {total_actual:<8.2f} | {total_delta:<+9.2f}")
    print("==============================================\n")
    
    return {
        "video_id": video_id,
        "total_estimated": round(total_estimated, 2),
        "total_actual": round(total_actual, 2),
        "total_delta": round(total_delta, 2),
        "multilang_tracks": multilang_tracks
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video_id", required=True, help="Video folder name to process")
    parser.add_argument("--output_dir", default="output", help="Base output directory")
    parser.add_argument("--multilang", action="store_true", help="Synthesize localized ES/PT/DE/HI audio tracks")
    args = parser.parse_args()
    
    try:
        process_video_audio(args.video_id, args.output_dir, multilang=args.multilang)
    except Exception as e:
        logging.error(f"TTS audio generation failed: {e}")
        sys.exit(1)
