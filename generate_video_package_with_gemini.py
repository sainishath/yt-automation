#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_video_package_with_gemini.py
-------------------------------------
Automates Gemini (via Google Generative AI API) to research any historical topic
and generate a production-ready, 100% causal-synced video package:

Outputs:
1. 16:9 Long-Form Master JSON (80 distinct shots, each with 1-to-1 spoken narration & Fooocus prompt)
2. 9:16 Viral Short JSON (15 fast-paced 3-4s cuts, each with 1-to-1 spoken narration & Fooocus prompt)
3. YouTube Metadata (Clickable titles, SEO description, chapter timestamps, tags, and schedule slots)

Usage:
  export GEMINI_API_KEY="your_api_key_here"
  python generate_video_package_with_gemini.py --topic "The Fall of Constantinople 1453"
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Anti-Hallucination Negative Prompt Lock enforced across all visual prompts
FOOOCUS_NEGATIVE_LOCK = (
    "modern, 20th century, 21st century, modern boats, modern ships, cruise ship, "
    "ferry boat, motorboat, steamship, yacht, modern buildings, skyscrapers, asphalt roads, "
    "streetlights, cars, electricity, power lines, contemporary clothing, wristwatch, "
    "eyeglasses, cartoon, anime, 3d render plastic, watermark, text, signature, "
    "lowres, blurry, deformed hands, extra fingers, distorted anatomy, split screen, "
    "multi-panel grid, comic strip panels, collage"
)

SYSTEM_PROMPT = """You are an elite YouTube documentary director, forensic historian, and cinematic AI prompt engineer.
Your job is to take a historical topic and output a complete, production-ready JSON package.

CRITICAL RULES:
1. CAUSAL STORYTELLING ("Because -> Therefore -> But -> So -> The End"):
   - Every script must open with a 2-sentence setup: "This is the story of [WHO] trying to do [WHAT], why [X armies/superpowers] failed before him, and the one crazy move that changed everything."
   - Write at a 12-year-old listening level. Every single sentence must be a direct cause or effect of the previous sentence. Zero academic filler.
   - Pacing must be punchy, rhythmic, and written strictly for spoken narration.

2. 1-TO-1 AUDIO-VISUAL BINDING (FRAME-ACCURATE SYNC):
   - Every single shot MUST have its own 1-2 sentence "narration" and its own exact matching "prompt".
   - The visual MUST depict the exact physical subject mentioned in the spoken narration (e.g. if the voice says "dragging seventy warships over a mountain", the image prompt MUST describe the wooden warship on greased logs on a dirt hill with oxen, NOT an empty scaffold or modern city).

3. ZERO-HALLUCINATION FOOOCUS SDXL PROMPT SPECIFICATION:
   - Every prompt MUST follow this exact structure:
     [Aspect Ratio 9:16 or 16:9] + [Camera Angle & Lens] + [Historical Subject & Physical Action] + [Era Lock: exact century/year AD/BC] + [Environment & Weather Details] + [Cinematic Lighting & Material Texture] + "photorealistic 8k, 35mm film still, historical authenticity, octane render"
   - Explicitly forbid modern leaks in historical settings (e.g. specify "15th-century wooden oared galley with red cloth sails on blue water, medieval stone sea walls, NO modern boats, NO cruise ships").

4. OUTPUT FORMAT:
   - Output PURE JSON ONLY. No markdown fences, no conversational preamble.
"""

SCHEMA_EXAMPLE = {
    "channel": "Chronos Shift (@ChronosShiftHistory)",
    "topic": "Topic Name",
    "era": "Year / Century",
    "youtube_metadata": {
        "title_option_a": "High CTR Curiosity Title",
        "title_option_b": "Alternative A/B Title",
        "description": "SEO Description with primary source citations and chapter timestamps.",
        "tags": ["history", "documentary", "shorts"],
        "recommended_schedule": "Friday 18:00 IST for Longform, Mon-Fri 13:00 IST for Shorts"
    },
    "short_15_cuts": [
        {
            "cut_id": "cut_01",
            "duration_est_sec": 3.5,
            "narration": "Exact spoken sentence for this 3-second cut.",
            "prompt": "9:16 vertical ... photorealistic 8k, historical authenticity [Era]",
            "negative_prompt": FOOOCUS_NEGATIVE_LOCK
        }
    ],
    "longform_80_shots": [
        {
            "act_number": 1,
            "act_title": "Act Name",
            "shots": [
                {
                    "shot_id": "act01_shot01",
                    "shot_type": "Wide Establishing",
                    "motion": "push_in",
                    "narration": "Exact 1-2 spoken sentences for this shot.",
                    "prompt": "16:9 cinematic ... photorealistic 8k, historical authenticity [Era]",
                    "negative_prompt": FOOOCUS_NEGATIVE_LOCK
                }
            ]
        }
    ]
}


def generate_package_with_gemini(topic: str, api_key: str, out_file: Path) -> dict:
    """Invokes Gemini 1.5 Pro to generate the full JSON package."""
    try:
        import google.generativeai as genai
    except ImportError:
        print("[ERROR] google-generativeai package not found. Run: pip install google-generativeai")
        sys.exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro",
        system_instruction=SYSTEM_PROMPT,
        generation_config={
            "temperature": 0.3,
            "response_mime_type": "application/json",
        }
    )

    prompt = f"""Generate the complete, production-ready video package for this topic:
Topic: "{topic}"

Requirements:
1. Provide 15 rapid, causal 3-4s cuts for the 9:16 vertical Short ("short_15_cuts").
2. Provide 7 acts with a total of 80 shots for the 16:9 Longform Documentary ("longform_80_shots").
3. Ensure every prompt specifies historical authenticity, material textures, and historical anchors with zero modern elements.
4. Conform strictly to this JSON schema:
{json.dumps(SCHEMA_EXAMPLE, indent=2)}
"""

    print(f"--> Querying Gemini for topic: '{topic}'...")
    response = model.generate_content(prompt)
    data = json.loads(response.text)

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[SUCCESS] Saved production package to: {out_file}")
    return data


def main():
    parser = argparse.ArgumentParser(description="Automate Gemini Video Package Generation")
    parser.add_argument("--topic", required=True, help="Historical topic to generate")
    parser.add_argument("--out", default="longform_engine/drafts/gemini_generated_package.json", help="Output JSON path")
    args = parser.parse_args()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY environment variable not set.")
        print("Run: export GEMINI_API_KEY='your_key' (Linux/Mac) or $env:GEMINI_API_KEY='your_key' (PowerShell)")
        sys.exit(1)

    generate_package_with_gemini(args.topic, api_key, Path(args.out))


if __name__ == "__main__":
    main()