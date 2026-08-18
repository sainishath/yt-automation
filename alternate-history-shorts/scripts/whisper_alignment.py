# -*- coding: utf-8 -*-
"""
whisper_alignment.py
--------------------
Standalone Pipeline-1 module for deterministic TTS audio transcription,
word-level alignment, and persistent alignment cache generation.

Serves as the authoritative word-timeline provider for downstream visual scene planning.
"""

import os
import sys
import json
import time
import hashlib
import logging
import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Setup logging
LOG_FILE = Path("pipeline.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

_WHISPER_MODEL_CACHE: Dict[str, Any] = {}

def get_whisper_model(model_name: str = "base.en"):
    """Loads and caches the Whisper model instance to avoid redundant reloads."""
    global _WHISPER_MODEL_CACHE
    if model_name not in _WHISPER_MODEL_CACHE:
        logging.info(f"[Whisper Alignment] Loading Whisper model '{model_name}'...")
        import whisper
        _WHISPER_MODEL_CACHE[model_name] = whisper.load_model(model_name)
    return _WHISPER_MODEL_CACHE[model_name]

def normalize_word(text: str) -> str:
    """
    Normalizes a word string for fuzzy matching without altering text structure.
    Strips leading/trailing punctuation and converts to lowercase.
    """
    if not text:
        return ""
    # Strip standard and typographer punctuation
    cleaned = re.sub(r'^[^\w]+|[^\w]+$', '', text.strip().lower(), flags=re.UNICODE)
    return cleaned

def compute_file_hash(file_path: Path) -> str:
    """Computes quick MD5 hash of a file for cache identity validation."""
    if not file_path.exists():
        return ""
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        # Read first 64KB for speed
        chunk = f.read(65536)
        hasher.update(chunk)
    return hasher.hexdigest()

def validate_word_timestamps(words: List[Dict[str, Any]], audio_duration: float) -> List[Dict[str, Any]]:
    """
    Validates and cleans word timestamps:
    - Ensures start >= 0 and end > start.
    - Clamps end timestamps to audio_duration.
    - Ensures strict chronological ordering.
    """
    valid_words = []
    prev_end = 0.0

    for idx, w in enumerate(words):
        start = float(w.get("start", 0.0))
        end = float(w.get("end", start + 0.1))

        # Fix start time if earlier than previous end
        if start < prev_end:
            start = prev_end

        # Ensure end is strictly after start
        if end <= start:
            end = round(start + 0.15, 3)

        # Clamp to audio duration
        if audio_duration > 0 and start > audio_duration:
            logging.warning(f"[Whisper Alignment Warning] Word '{w.get('word')}' start ({start:.2f}s) exceeds audio duration ({audio_duration:.2f}s). Skipping.")
            continue
        if audio_duration > 0 and end > audio_duration:
            end = round(audio_duration, 3)

        cleaned_word = {
            "index": idx,
            "word": str(w.get("word", "")),
            "normalized": normalize_word(str(w.get("word", ""))),
            "start": round(start, 3),
            "end": round(end, 3),
            "probability": round(float(w.get("probability", 1.0)), 3)
        }
        valid_words.append(cleaned_word)
        prev_end = cleaned_word["end"]

    return valid_words

def align_audio_file(
    audio_path: Path,
    narration_text: str,
    model_name: str = "base.en",
    whisper_model=None
) -> Dict[str, Any]:
    """
    Transcribes a single audio file using Whisper with word timestamps.
    Returns structured alignment data for the file.
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    if whisper_model is None:
        whisper_model = get_whisper_model(model_name)

    logging.info(f"[Whisper Alignment] Transcribing {audio_path.name}...")
    result = whisper_model.transcribe(
        str(audio_path),
        word_timestamps=True,
        initial_prompt=narration_text,
        language="en"
    )

    # Extract raw word items
    raw_words = []
    raw_segments = []
    for seg_idx, segment in enumerate(result.get("segments", [])):
        raw_segments.append({
            "segment_id": seg_idx,
            "text": segment.get("text", "").strip(),
            "start": round(float(segment.get("start", 0.0)), 3),
            "end": round(float(segment.get("end", 0.0)), 3)
        })
        for w in segment.get("words", []):
            raw_words.append({
                "word": w.get("word", ""),
                "start": w.get("start", 0.0),
                "end": w.get("end", 0.0),
                "probability": w.get("probability", 1.0)
            })

    # Audio duration from last segment or word
    audio_duration = raw_segments[-1]["end"] if raw_segments else (raw_words[-1]["end"] if raw_words else 0.0)

    # Fallback to segment-level if word timestamps are missing
    if not raw_words and raw_segments:
        logging.warning(f"[Whisper Alignment] No word timestamps returned for {audio_path.name}. Falling back to segment words.")
        for seg in raw_segments:
            seg_words = seg["text"].split()
            seg_dur = max(0.1, seg["end"] - seg["start"])
            word_dur = seg_dur / max(1, len(seg_words))
            for w_i, w_str in enumerate(seg_words):
                w_start = seg["start"] + (w_i * word_dur)
                raw_words.append({
                    "word": w_str,
                    "start": w_start,
                    "end": w_start + word_dur,
                    "probability": 0.8
                })

    validated_words = validate_word_timestamps(raw_words, audio_duration)

    return {
        "file_name": audio_path.name,
        "file_hash": compute_file_hash(audio_path),
        "narration_text": narration_text,
        "duration": round(audio_duration, 3),
        "words": validated_words,
        "segments": raw_segments
    }

def align_video_job(
    video_id: str,
    output_dir: str = "output",
    model_name: str = "base.en",
    force_rebuild: bool = False
) -> Dict[str, Any]:
    """
    Performs full job audio alignment across all scenes, generating global timeline offsets
    and persisting output to output/{video_id}/audio/alignment_cache.json.
    """
    video_path = Path(output_dir) / video_id
    script_path = video_path / "script.json"
    audio_dir = video_path / "audio"
    cache_path = audio_dir / "alignment_cache.json"

    if not script_path.exists():
        raise FileNotFoundError(f"script.json not found for {video_id} at {script_path}")

    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    scenes = script.get("scenes", [])
    if not scenes:
        raise ValueError(f"script.json for {video_id} contains no scenes.")

    # Check cache validity
    if cache_path.exists() and not force_rebuild:
        try:
            with open(cache_path, "r", encoding="utf-8") as cf:
                cache_data = json.load(cf)
            
            # Verify cache metadata matches current files
            cache_valid = True
            if cache_data.get("model") != model_name or len(cache_data.get("scenes", [])) != len(scenes):
                cache_valid = False
            else:
                for idx, scene_cache in enumerate(cache_data.get("scenes", [])):
                    audio_file = audio_dir / f"scene_{idx:03d}.mp3"
                    if not audio_file.exists() or compute_file_hash(audio_file) != scene_cache.get("file_hash"):
                        cache_valid = False
                        break

            if cache_valid:
                logging.info(f"[Whisper Alignment] Reusing valid alignment cache from {cache_path.name}")
                return cache_data
            else:
                logging.info(f"[Whisper Alignment] Cache invalid or stale. Rebuilding alignment cache...")
        except Exception as ce:
            logging.warning(f"[Whisper Alignment] Could not read cache file ({ce}). Rebuilding...")

    # Build fresh alignment
    whisper_model = get_whisper_model(model_name)
    scene_alignments = []
    global_words = []
    global_offset = 0.0

    print("\n==============================================")
    print(f"  Whisper Audio Alignment: {video_id} ")
    print("==============================================\n")
    print(f"{'Scene':<6} | {'Words':<5} | {'Duration (s)':<12} | {'Global Offset (s)':<18}")
    print("-" * 55)

    for idx, scene in enumerate(scenes):
        narration = scene.get("narration", "").strip()
        audio_file = audio_dir / f"scene_{idx:03d}.mp3"
        if not audio_file.exists():
            raise FileNotFoundError(f"Missing audio file for scene {idx}: {audio_file}")

        scene_data = align_audio_file(audio_file, narration, model_name, whisper_model)
        scene_duration = scene_data["duration"]
        scene_data["scene_index"] = idx
        scene_data["global_start"] = round(global_offset, 3)
        scene_data["global_end"] = round(global_offset + scene_duration, 3)

        # Construct global word timeline entries
        for w in scene_data["words"]:
            g_word = dict(w)
            g_word["scene_index"] = idx
            g_word["global_start"] = round(global_offset + w["start"], 3)
            g_word["global_end"] = round(global_offset + w["end"], 3)
            global_words.append(g_word)

        print(f"#{idx:<4} | {len(scene_data['words']):<5} | {scene_duration:<12.2f} | {global_offset:<18.2f}")
        scene_alignments.append(scene_data)
        global_offset += scene_duration

    print("-" * 55)
    print(f"Total  | {len(global_words):<5} | {global_offset:<12.2f} | End Time: {global_offset:.2f}s")
    print("==============================================\n")

    alignment_cache = {
        "video_id": video_id,
        "model": model_name,
        "total_duration": round(global_offset, 3),
        "total_words": len(global_words),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scenes": scene_alignments,
        "global_timeline": global_words
    }

    # Save cache JSON
    audio_dir.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(alignment_cache, f, indent=2, ensure_ascii=False)

    logging.info(f"[Whisper Alignment] Alignment cache successfully saved to {cache_path}")
    return alignment_cache

def get_global_word_timeline(alignment_cache: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Returns the flattened global word timeline from an alignment cache dict."""
    return alignment_cache.get("global_timeline", [])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standalone Whisper Alignment Module for Pipeline 1")
    parser.add_argument("--video_id", required=True, help="Video folder ID to process")
    parser.add_argument("--output_dir", default="output", help="Base output directory")
    parser.add_argument("--force", action="store_true", help="Force rebuild alignment cache")
    args = parser.parse_args()

    try:
        res = align_video_job(args.video_id, args.output_dir, force_rebuild=args.force)
        print(f"OK Alignment complete for {args.video_id}. Total words: {res['total_words']}, Duration: {res['total_duration']}s")
    except Exception as e:
        logging.error(f"Alignment failed: {e}")
        sys.exit(1)
