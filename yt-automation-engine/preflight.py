# -*- coding: utf-8 -*-
"""
preflight.py
------------
Pre-flight infrastructure verification for Pipeline 2.
Verifies all external dependencies, servers, voice models, assets,
and directory permissions BEFORE starting expensive AI generation.
"""

import os
import sys
import json
import shutil
import subprocess
import requests
from pathlib import Path

def run_preflight_check(cfg: dict, require_youtube_auth: bool = False) -> tuple:
    """
    Run preflight checks for required infrastructure.

    Returns:
        (is_valid: bool, failed_stage: str, error_message: str)
    """
    # 1. FFmpeg availability
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        return False, "PREFLIGHT", "FFmpeg executable not found on system PATH."
    try:
        res = subprocess.run([ffmpeg_bin, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        if res.returncode != 0:
            return False, "PREFLIGHT", f"FFmpeg health check failed with exit code {res.returncode}."
    except Exception as e:
        return False, "PREFLIGHT", f"FFmpeg check failed: {e}"

    # 2. Ollama server and model availability
    ollama_url = cfg.get("ollama_url", "http://127.0.0.1:11434").rstrip("/")
    required_ollama_model = cfg.get("ollama_model", "llama3.1:latest")
    try:
        r = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if r.status_code != 200:
            return False, "PREFLIGHT", f"Ollama server returned status code {r.status_code} at {ollama_url}."
        
        models_data = r.json().get("models", [])
        available_models = [m.get("name") for m in models_data]
        if not any(required_ollama_model in m for m in available_models):
            return False, "PREFLIGHT", f"Required Ollama model '{required_ollama_model}' not loaded in Ollama server. Available: {available_models}"
    except Exception as e:
        return False, "PREFLIGHT", f"Ollama server unreachable at {ollama_url}: {e}"

    # 3. Fooocus endpoint availability
    fooocus_url = cfg.get("fooocus_url", "http://127.0.0.1:7865").rstrip("/")
    try:
        rf = requests.get(fooocus_url, timeout=5)
        if rf.status_code not in [200, 302, 401, 403]:
            return False, "PREFLIGHT", f"Fooocus server returned status code {rf.status_code} at {fooocus_url}."
    except Exception as e:
        return False, "PREFLIGHT", f"Fooocus server unreachable at {fooocus_url}: {e}"

    # 4. Piper executable and voice models
    models_dir = Path(__file__).parent.parent / "models"
    ryan_voice = models_dir / "voices" / "en_US-ryan-medium.onnx"
    libri_voice = models_dir / "en_US-libritts_r-medium.onnx"

    if not ryan_voice.exists():
        return False, "PREFLIGHT", f"Speaker A voice model not found at {ryan_voice}."
    if not libri_voice.exists():
        return False, "PREFLIGHT", f"Speaker B voice model not found at {libri_voice}."

    # 5. Background assets (video and BGM)
    bg_dir = Path(__file__).parent.parent / "assets" / "backgrounds" / "active"
    if not bg_dir.exists():
        return False, "PREFLIGHT", f"Background directory not found at {bg_dir}."

    bg_files = list(bg_dir.glob("*.mp4")) + list(bg_dir.glob("*.webm"))
    if not bg_files:
        return False, "PREFLIGHT", f"No background video files (.mp4/.webm) found in {bg_dir}."

    bgm_dir = Path(__file__).parent.parent / "assets" / "bgm"
    if not bgm_dir.exists() or not list(bgm_dir.glob("*.mp3")):
        return False, "PREFLIGHT", f"No background music files (.mp3) found in {bgm_dir}."

    # 6. Directory permissions
    output_dir = Path(__file__).parent.parent / "data" / "yt-automation-engine" / "videos"
    temp_dir = Path(__file__).parent.parent / "data" / "yt-automation-engine" / "temp"
    for d in [output_dir, temp_dir]:
        d.mkdir(parents=True, exist_ok=True)
        test_file = d / ".preflight_write_test"
        try:
            test_file.write_text("test", encoding="utf-8")
            test_file.unlink()
        except Exception as e:
            return False, "PREFLIGHT", f"Directory {d} is not writable: {e}"

    # 7. Optional YouTube OAuth check
    if require_youtube_auth:
        try:
            from uploader import is_authorized
            if not is_authorized():
                return False, "PREFLIGHT", "YouTube OAuth credentials missing or invalid. Visit http://localhost:5001/auth-youtube to authorize."
        except Exception as ye:
            return False, "PREFLIGHT", f"YouTube authorization check failed: {ye}"

    return True, "", ""
