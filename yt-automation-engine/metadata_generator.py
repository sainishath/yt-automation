# -*- coding: utf-8 -*-
"""
metadata_generator.py
---------------------
Generates YouTube metadata for convo-shorts:
- Title (<= 60 chars, front-loaded hook using debate question)
- Description (starts with question, 3-5 hashtags including #Shorts)
- Tags (mix of broad and specific)
Uses Ollama (llama3.2) to polish the title and select optimized hashtags.
"""

import sys
import json
import logging
import requests
from pathlib import Path

OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "llama3.2:latest"

def generate_metadata(question: str, category: str) -> dict:
    """
    Generates YouTube metadata (title, description, tags) for the debate question.
    """
    prompt = f"""You are a professional YouTube growth analyst.
Generate video metadata for a short debate about the topic: "{question}" in the category: "{category}".

The output must be a valid JSON object matching this schema:
{{
  "title": "A highly-clickable, viral YouTube Short title under 60 characters. Must be hooky and contain a front-loaded hook based on the question.",
  "description": "Short video description starting with the debate question, followed by a 1-sentence curiosity hook, and 3-5 relevant hashtags (one of which MUST be #Shorts and one MUST be #debate).",
  "tags": ["tag1", "tag2", "tag3", ...]
}}

Ensure that "title" is strictly <= 60 characters.
Output ONLY the raw JSON object, no formatting.
"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 500
        }
    }
    
    for attempt in range(1, 4):
        try:
            print(f"[Metadata] Generating metadata via Ollama (Attempt {attempt}/3)...")
            response = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=60)
            response.raise_for_status()
            
            raw_text = response.json().get("response", "").strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()
            
            data = json.loads(raw_text)
            title = data.get("title", "").strip()
            desc = data.get("description", "").strip()
            tags = data.get("tags", [])
            
            # Post validation
            if title and desc and tags:
                # Truncate title if it exceeds 60 chars
                if len(title) > 60:
                    title = title[:57] + "..."
                # Enforce #Shorts in description
                if "#Shorts" not in desc and "#shorts" not in desc:
                    desc += " #Shorts"
                # Enforce #debate
                if "#debate" not in desc.lower():
                    desc += " #debate"
                    
                return {
                    "title": title,
                    "description": desc,
                    "tags": tags
                }
        except Exception as e:
            print(f"[Metadata] Attempt {attempt} failed: {e}")
            
    # Fallback metadata
    fallback_title = f"{question[:45]}? #Shorts"
    fallback_desc = f"{question}. Who is right? Comment below! #Shorts #debate #vs"
    return {
        "title": fallback_title[:60],
        "description": fallback_desc,
        "tags": [category.lower(), "debate", "versus", "argument", "comparison"]
    }
