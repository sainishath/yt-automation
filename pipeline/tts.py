# -*- coding: utf-8 -*-
"""
pipeline/tts.py
---------------
Multi-Language Audio Track Dubbing helper for YouTube Studio Multi-Language Audio.
Translates verified JSON scripts into Spanish (es), Portuguese (pt), German (de), and Hindi (hi)
via Gemini Flash (or local Ollama fallback) and synthesizes localized Edge-TTS audio tracks.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import requests

MULTILANG_VOICES: Dict[str, Dict[str, str]] = {
    "es": {"language_name": "Spanish", "voice": "es-ES-AlvaroNeural"},
    "pt": {"language_name": "Portuguese", "voice": "pt-BR-AntonioNeural"},
    "de": {"language_name": "German", "voice": "de-DE-ConradNeural"},
    "hi": {"language_name": "Hindi", "voice": "hi-IN-MadhurNeural"},
}


def translate_script_text(text: str, target_language_name: str) -> str:
    """Translates spoken narration text into target_language_name via Gemini Flash or local Ollama."""
    api_key = os.environ.get("GEMINI_API_KEY")
    prompt = (
        f"Translate the following historical documentary voiceover narration into natural, dramatic {target_language_name}. "
        f"Preserve all historical dates and proper names accurately. Return ONLY the translated spoken text:\n\n{text}"
    )
    if api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            if resp and resp.text:
                return resp.text.strip()
        except Exception:
            pass

    ollama_url = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
    ollama_model = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")
    try:
        res = requests.post(
            f"{ollama_url}/api/generate",
            json={"model": ollama_model, "prompt": prompt, "stream": False},
            timeout=30,
        )
        res.raise_for_status()
        translated = res.json().get("response", "").strip()
        if translated:
            return translated
    except Exception:
        pass
    return text


def synthesize_multilang_tracks(
    full_narration_text: str,
    output_dir: str | Path,
    languages: Optional[List[str]] = None,
) -> Dict[str, str]:
    """
    Translates verified narration text into target languages (default: es, pt, de, hi)
    and synthesizes localized Edge-TTS audio tracks (.mp3) for YouTube Multi-Language Audio.
    """
    out_base = Path(output_dir)
    out_base.mkdir(parents=True, exist_ok=True)
    target_langs = languages or ["es", "pt", "de", "hi"]
    generated_tracks: Dict[str, str] = {}

    for lang_code in target_langs:
        cfg = MULTILANG_VOICES.get(lang_code)
        if not cfg:
            continue
        translated = translate_script_text(full_narration_text, cfg["language_name"])
        out_mp3 = out_base / f"track_{lang_code}.mp3"
        cmd = [
            "edge-tts",
            "--text",
            translated,
            "--voice",
            cfg["voice"],
            "--write-media",
            str(out_mp3),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        generated_tracks[lang_code] = str(out_mp3)

    return generated_tracks
