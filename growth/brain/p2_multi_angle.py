# -*- coding: utf-8 -*-
"""
p2_multi_angle.py
----------------
Content Brain v1 Multi-Angle Generation for Pipeline 2 (Beginner Coding & Mentorship).
Persona: Friendly, expert coding mentor explaining to an absolute beginner using the ELI5 rule.
"""

import json
import logging
import urllib.request
from typing import Dict, Any, Optional

OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "llama3.2:latest"


def generate_p2_multi_angle_concept(topic: str, category: str, active_strategy: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates 3 distinct beginner-friendly ELI5 angles for a programming concept and selects the best candidate.
    """
    prompt = f"""You are a warm, encouraging coding mentor teaching absolute beginners who have never coded before.
Generate 3 distinct beginner-friendly 'Explain Like I'm 5' (ELI5) strategic angles for a high-retention 40-second YouTube Short on '{topic}'.
Category: {category}

### CORE PERSONA & TEACHING RULES:
1. EXPLAIN LIKE I'M 5 (ELI5): Use everyday physical metaphors (e.g. variables are labeled storage boxes, booleans are light switches, functions are recipes).
2. NO ADVANCED JARGON: Never mention memory buses, compiler ASTs, bytecodes, or distributed architectures. Keep it fun, simple, and crystal clear.
3. CLEAR CALL TO ACTION: Tease the next part in the sequence so viewers subscribe/follow.

### THE 3 STRATEGIC ANGLES TO CREATE:
1. REAL_WORLD_METAPHOR: Ground the concept in a physical object everyone understands (boxes, recipes, light switches).
2. BEGINNER_AH_HA_MOMENT: Clarify a common point of confusion for new coders (e.g. why we need quotes around words but not numbers).
3. MINI_SUPERPOWER: Show how this single concept lets them build something cool (like games or calculators).

### REQUIRED JSON OUTPUT:
{{
  "angles": [
    {{
      "angle_id": "angle_1",
      "type": "REAL_WORLD_METAPHOR",
      "hook_text": "A punchy real-world physical metaphor specifically about {topic}.",
      "core_conflict": "The core problem solved by {topic}.",
      "senior_takeaway": "The fundamental insight beginners need to remember about {topic}.",
      "curiosity_score": 9.5
    }},
    {{
      "angle_id": "angle_2",
      "type": "BEGINNER_AH_HA_MOMENT",
      "hook_text": "A common mistake or curiosity question specifically about {topic}.",
      "core_conflict": "Why beginners struggle with {topic} without this insight.",
      "senior_takeaway": "The clean mental model for {topic}.",
      "curiosity_score": 9.0
    }},
    {{
      "angle_id": "angle_3",
      "type": "MINI_SUPERPOWER",
      "hook_text": "How {topic} gives coders a superpower to build games or apps.",
      "core_conflict": "What programs cannot do without {topic}.",
      "senior_takeaway": "How mastering {topic} unlocks practical programming.",
      "curiosity_score": 8.5
    }}
  ],
  "selected_angle_id": "angle_1",
  "selection_reasoning": "Real-world metaphor produces the highest comprehension and beginner retention."
}}
"""

    try:
        req_data = json.dumps({
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }).encode("utf-8")

        req = urllib.request.Request(f"{OLLAMA_URL}/api/generate", data=req_data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            raw = res_json.get("response", "{}")
            return json.loads(raw)
    except Exception as e:
        logging.warning(f"[MultiAngle] Angle generation fallback: {e}")

    return {
        "selected_angle_id": "angle_1",
        "angles": [{
            "angle_id": "angle_1",
            "type": "REAL_WORLD_METAPHOR",
            "hook_text": f"Think of {topic} as a simple real-world tool.",
            "core_conflict": "Understanding how code stores and uses data.",
            "senior_takeaway": "Master the simple mental model to write great code."
        }],
        "selection_reasoning": "Fallback ELI5 angle selection."
    }

