# -*- coding: utf-8 -*-
"""
p2_multi_angle.py
----------------
Content Brain v1 Multi-Angle Generation for Pipeline 2 (Coding & Tech).
"""

import json
import logging
import urllib.request
from typing import Dict, Any, Optional

OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "llama3.2:latest"


def generate_p2_multi_angle_concept(topic: str, category: str, active_strategy: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates 3 distinct strategic angles for a technical concept and selects the highest-scoring candidate.
    """
    prompt = f"""You are a principal software engineer and senior coding educator.
Generate 3 distinct strategic angles for a high-retention 40-second YouTube Short on '{topic}'.
Category: {category}

### THE 3 STRATEGIC ANGLES TO CREATE:
1. CODE_SMELL_TRAP: Focus on a common junior coding pitfall that silently fails or causes bugs in production.
2. ARCHITECTURE_BOTTLENECK: Focus on high-load, scalability failure, or catastrophic system outages.
3. SENIOR_MENTAL_MODEL: Focus on a counter-intuitive principle about memory, data structures, or performance.

### REQUIRED JSON OUTPUT:
{{
  "angles": [
    {{
      "angle_id": "angle_1",
      "type": "CODE_SMELL_TRAP",
      "hook_text": "Why 90% of devs misuse this pattern.",
      "core_conflict": "Unbounded writes overwhelm the server memory.",
      "senior_takeaway": "Always enforce chunked backpressure batching.",
      "curiosity_score": 9.0
    }},
    {{
      "angle_id": "angle_2",
      "type": "ARCHITECTURE_BOTTLENECK",
      "hook_text": "The single query that crashed GitHub.",
      "core_conflict": "Lack of read replicas caused primary lock starvation.",
      "senior_takeaway": "Separate read and write connection pools.",
      "curiosity_score": 8.5
    }},
    {{
      "angle_id": "angle_3",
      "type": "SENIOR_MENTAL_MODEL",
      "hook_text": "Stop using bigger servers for read traffic.",
      "core_conflict": "Vertical scaling hits memory bus limits.",
      "senior_takeaway": "Read replicas offer linear read throughput.",
      "curiosity_score": 8.0
    }}
  ],
  "selected_angle_id": "angle_1",
  "selection_reasoning": "Code smell with clear junior vs senior code cards produces highest completion rate."
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
            "type": "CODE_SMELL_TRAP",
            "hook_text": f"Why junior devs struggle with {topic}.",
            "core_conflict": "Performance bottleneck under production load.",
            "senior_takeaway": "Use idiomatic clean design patterns."
        }],
        "selection_reasoning": "Fallback angle selection."
    }
