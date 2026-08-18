# -*- coding: utf-8 -*-
"""
generate_metadata.py
--------------------
Pipeline 1 Stage 5: Generates YouTube Shorts metadata (title, description, tags).
Loads script.json, generates title/description/tags via Ollama, validates constraints,
and saves to output/{video_id}/metadata.json.
"""

import os
import sys
import json
import time
import argparse
import logging
import requests
from pathlib import Path
from typing import Any, Tuple

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

OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "llama3.2:latest"
MAX_RETRIES = 3
MAX_TITLE_LENGTH = 60
MIN_TAGS = 10
MAX_TAGS = 15


def parse_llm_json(raw_text: str, default: Any = None) -> Any:
    """Safely extracts and parses JSON content from LLM output, stripping markdown code fences."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        return default


def call_ollama_json(prompt: str, max_retries: int = MAX_RETRIES) -> dict:
    """Calls Ollama with the given prompt and returns parsed JSON with retries."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.6,
            "num_predict": 600
        }
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=90)
            response.raise_for_status()
            raw_text = response.json().get("response", "").strip()
            result = parse_llm_json(raw_text)
            if result and isinstance(result, dict):
                return result
            logging.warning(f"JSON decode failed (attempt {attempt}/{max_retries})")
        except Exception as e:
            logging.error(f"Ollama call error (attempt {attempt}/{max_retries}): {e}")

    raise RuntimeError(f"Failed to get valid JSON from Ollama after {max_retries} attempts.")


def validate_metadata(metadata: dict) -> Tuple[bool, Any]:
    """Validates generated metadata fields against YouTube requirements."""
    title = metadata.get("title", "")
    description = metadata.get("description", "")
    tags = metadata.get("tags", [])

    if not title or not isinstance(title, str):
        return False, "Missing or invalid 'title' field"

    metadata["title"] = title.strip()
    title = metadata["title"]
    if len(title) > MAX_TITLE_LENGTH:
        return False, f"Title is {len(title)} chars, must be <= {MAX_TITLE_LENGTH}"

    if not description or not isinstance(description, str):
        return False, "Missing or invalid 'description' field"

    if "#Shorts" not in description and "#shorts" not in description:
        return False, "Description must include #Shorts"

    if not isinstance(tags, list) or len(tags) < MIN_TAGS:
        return False, f"tags must be a list with at least {MIN_TAGS} items (got {len(tags)})"

    if len(tags) > MAX_TAGS:
        metadata["tags"] = tags[:MAX_TAGS]
        logging.info(f"Tags trimmed from {len(tags)} to {MAX_TAGS}")

    return True, metadata


def generate_video_metadata(video_id: str, output_dir: str = "output") -> dict:
    """
    Main Stage 5 metadata generation function.
    Loads script.json for a video, generates title/description/tags via Ollama,
    validates them, and saves to metadata.json.
    """
    video_path = Path(output_dir) / video_id
    script_path = video_path / "script.json"

    if not script_path.exists():
        raise FileNotFoundError(f"script.json not found for {video_id}")

    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    topic = script.get("topic", video_id.replace("_", " "))
    hook = script.get("hook", "")
    scenes = script.get("scenes", [])

    narrations = [s.get("narration", "") for s in scenes[:3]]
    synopsis = " ".join(narrations)

    prompt = f"""Generate YouTube Shorts metadata for a historical "what if" video.

Topic: "{topic}"
Hook: "{hook}"
Synopsis: "{synopsis}"

Requirements:
- title: Under {MAX_TITLE_LENGTH} characters. MUST be directly about the topic "{topic}". Front-load the hook, curiosity-driven, starts with or includes "What If". Keep it short so it is not truncated on mobile screens.
- description: A compelling description that starts immediately with the hook line. Follow with 1-2 sentences summarizing the premise and a call to action. (Do not write any hashtags here — they will be appended automatically).
- tags: A list of exactly {MIN_TAGS}-{MAX_TAGS} strings. Mix broad terms ("history", "alternate history", "what if", "history shorts") with specific entity names strictly from the topic "{topic}". Do not include unrelated historical entities.

Return ONLY valid JSON with no other text:
{{
  "title": "...",
  "description": "...",
  "tags": ["...", "...", ...]
}}"""

    logging.info(f"Generating metadata for video_id: {video_id}")
    print(f"\nGenerating metadata for: {video_id}")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            metadata = call_ollama_json(prompt)
            metadata["video_id"] = video_id

            desc = metadata.get("description", "").strip()
            topic_tag = "#" + topic.split()[-1].strip("?").capitalize()
            hashtag_suffix = f"\n\n#Shorts #WhatIf #AlternateHistory {topic_tag}"
            
            if "#Shorts" not in desc and "#shorts" not in desc:
                metadata["description"] = f"{desc} {hashtag_suffix}".strip()

            valid, result = validate_metadata(metadata)
            if valid:
                metadata_path = video_path / "metadata.json"
                with open(metadata_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)

                logging.info(f"Metadata saved to {metadata_path}")
                print(f"\n  Title:       {result['title']}")
                print(f"  Description: {result['description'][:120]}...")
                print(f"  Tags ({len(result['tags'])}): {', '.join(result['tags'][:5])}...")
                return result
            else:
                logging.warning(f"Metadata validation failed (attempt {attempt}): {result}")

        except Exception as e:
            logging.error(f"Metadata generation error (attempt {attempt}): {e}")

    raise RuntimeError(f"Failed to generate valid metadata for {video_id} after {MAX_RETRIES} attempts.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 5: Generate YouTube Shorts metadata")
    parser.add_argument("--video_id", required=True, help="Video folder name to process")
    parser.add_argument("--output_dir", default="output", help="Base output directory")
    args = parser.parse_args()

    try:
        generate_video_metadata(args.video_id, args.output_dir)
    except Exception as e:
        logging.error(f"Metadata generation failed: {e}")
        sys.exit(1)
