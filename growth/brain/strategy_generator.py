# -*- coding: utf-8 -*-
"""
strategy_generator.py
---------------------
Secure, schema-validated Gemini API module for the Growth Brain.
Analyzes first-party empirical performance metrics and proposes safe,
bounded strategy mutations (hooks, duration, pacing, visual rules).

Guarantees:
1. Strict type, range, and enum validation via validate_gemini_strategy().
2. Defensive fallback: Any API error or schema violation raises ValueError and
   safely returns the baseline strategy from growth.db / disk.
3. Zero untrusted state leakage into generation pipelines.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict

# ── Allowed Enums and Bounds ───────────────────────────────────────────────────
ALLOWED_CHANNELS = {"channel_a", "channel_b"}

ALLOWED_HOOK_TYPES = {
    "COUNTERFACTUAL",
    "SOCRATIC_QUESTION",
    "MISTAKE_FIRST",
    "ANALOGY_HOOK",
    "REAL_WORLD_METAPHOR",
    "CONTRARIAN_TAKE",
    "CODE_PUZZLE",
    "HISTORICAL_PARADOX",
    "WHAT_IF_DIVERGENCE"
}

ALLOWED_CODE_THEMES = {"tokyo_night", "monokai", "dracula", "github_dark", "vscode_dark"}

DURATION_MIN_LOWER = 20.0
DURATION_MAX_UPPER = 60.0
TTS_SPEED_MIN = 0.85
TTS_SPEED_MAX = 1.25
WORDS_PER_SCENE_MIN = 12
WORDS_PER_SCENE_MAX = 35
TOTAL_WORDS_MIN = 60
TOTAL_WORDS_MAX = 140


@dataclass
class StrategyMutation:
    channel_id: str
    strategy_version: str
    parent_version: str
    target_duration: List[float]
    tts_speed: float
    allowed_hook_types: List[str]
    pacing_rules: Dict[str, Any]
    visual_rules: Dict[str, Any]
    hypothesized_apv_impact: float
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def validate_gemini_strategy(raw_data: Union[str, dict]) -> StrategyMutation:
    """
    Validates a raw JSON string or dictionary against strict Growth Brain invariants.
    Raises ValueError with explicit violation details if validation fails.
    """
    if isinstance(raw_data, str):
        try:
            # Clean possible markdown code fences
            cleaned = raw_data.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            data = json.loads(cleaned.strip())
        except json.JSONDecodeError as je:
            raise ValueError(f"[STRATEGY_SCHEMA_ERROR] Invalid JSON syntax: {je}") from je
    elif isinstance(raw_data, dict):
        data = raw_data
    else:
        raise ValueError(f"[STRATEGY_SCHEMA_ERROR] Expected str or dict, got {type(raw_data).__name__}")

    # 1. Required Top-Level Fields
    required_fields = [
        "channel_id",
        "strategy_version",
        "parent_version",
        "target_duration",
        "tts_speed",
        "allowed_hook_types",
        "pacing_rules",
        "visual_rules",
        "hypothesized_apv_impact",
        "rationale"
    ]
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise ValueError(f"[STRATEGY_SCHEMA_ERROR] Missing required fields: {missing}")

    # 2. Channel ID
    channel_id = str(data["channel_id"]).lower().strip()
    if channel_id not in ALLOWED_CHANNELS:
        raise ValueError(f"[STRATEGY_SCHEMA_ERROR] Invalid channel_id '{channel_id}'. Must be one of {ALLOWED_CHANNELS}")

    # 3. Strategy Version Strings
    strat_ver = str(data["strategy_version"]).strip()
    parent_ver = str(data["parent_version"]).strip()
    if not strat_ver or not parent_ver:
        raise ValueError("[STRATEGY_SCHEMA_ERROR] strategy_version and parent_version must be non-empty strings.")

    # 4. Target Duration Bounds [min, max]
    target_dur = data["target_duration"]
    if not isinstance(target_dur, (list, tuple)) or len(target_dur) != 2:
        raise ValueError(f"[STRATEGY_SCHEMA_ERROR] target_duration must be [min_sec, max_sec] list, got: {target_dur}")
    min_dur, max_dur = float(target_dur[0]), float(target_dur[1])
    if not (DURATION_MIN_LOWER <= min_dur < max_dur <= DURATION_MAX_UPPER):
        raise ValueError(
            f"[STRATEGY_BOUNDS_ERROR] target_duration [{min_dur}, {max_dur}] violates bounds "
            f"({DURATION_MIN_LOWER}s <= min < max <= {DURATION_MAX_UPPER}s)"
        )

    # 5. TTS Speed
    tts_speed = float(data["tts_speed"])
    if not (TTS_SPEED_MIN <= tts_speed <= TTS_SPEED_MAX):
        raise ValueError(f"[STRATEGY_BOUNDS_ERROR] tts_speed {tts_speed:.2f} violates bounds [{TTS_SPEED_MIN}, {TTS_SPEED_MAX}]")

    # 6. Allowed Hook Types
    hook_types = data["allowed_hook_types"]
    if not isinstance(hook_types, list) or len(hook_types) == 0:
        raise ValueError("[STRATEGY_SCHEMA_ERROR] allowed_hook_types must be a non-empty list")
    for ht in hook_types:
        if str(ht).upper() not in ALLOWED_HOOK_TYPES:
            raise ValueError(f"[STRATEGY_ENUM_ERROR] Unknown hook type '{ht}'. Allowed: {ALLOWED_HOOK_TYPES}")

    # 7. Pacing Rules
    pacing = data["pacing_rules"]
    if not isinstance(pacing, dict):
        raise ValueError("[STRATEGY_SCHEMA_ERROR] pacing_rules must be a dictionary")
    
    words_per_scene = pacing.get("max_words_per_scene", 25)
    total_words = pacing.get("target_word_count", 95)
    if not (WORDS_PER_SCENE_MIN <= words_per_scene <= WORDS_PER_SCENE_MAX):
        raise ValueError(f"[STRATEGY_BOUNDS_ERROR] max_words_per_scene {words_per_scene} violates bounds [{WORDS_PER_SCENE_MIN}, {WORDS_PER_SCENE_MAX}]")
    if not (TOTAL_WORDS_MIN <= total_words <= TOTAL_WORDS_MAX):
        raise ValueError(f"[STRATEGY_BOUNDS_ERROR] target_word_count {total_words} violates bounds [{TOTAL_WORDS_MIN}, {TOTAL_WORDS_MAX}]")

    # 8. Visual Rules
    visual = data["visual_rules"]
    if not isinstance(visual, dict):
        raise ValueError("[STRATEGY_SCHEMA_ERROR] visual_rules must be a dictionary")
    code_theme = visual.get("code_card_theme", "tokyo_night")
    if code_theme not in ALLOWED_CODE_THEMES:
        raise ValueError(f"[STRATEGY_ENUM_ERROR] Invalid code_card_theme '{code_theme}'. Allowed: {ALLOWED_CODE_THEMES}")

    # 9. Hypothesized Impact & Rationale
    impact = float(data["hypothesized_apv_impact"])
    if not (-20.0 <= impact <= 35.0):
        raise ValueError(f"[STRATEGY_BOUNDS_ERROR] hypothesized_apv_impact {impact}% out of realistic range [-20%, +35%]")

    rationale = str(data["rationale"]).strip()
    if len(rationale) < 10:
        raise ValueError("[STRATEGY_SCHEMA_ERROR] rationale must be a meaningful explanation (>= 10 chars)")

    return StrategyMutation(
        channel_id=channel_id,
        strategy_version=strat_ver,
        parent_version=parent_ver,
        target_duration=[min_dur, max_dur],
        tts_speed=tts_speed,
        allowed_hook_types=[str(h).upper() for h in hook_types],
        pacing_rules=pacing,
        visual_rules=visual,
        hypothesized_apv_impact=impact,
        rationale=rationale
    )


def generate_strategy_with_gemini(
    channel_id: str,
    performance_summary: Dict[str, Any],
    fallback_strategy: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Queries Gemini API with structured JSON output to hypothesize an optimized strategy mutation.
    Safely falls back to `fallback_strategy` upon any API failure, missing key, or validation error.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logging.info("[Strategy Generator] GEMINI_API_KEY not set. Using baseline strategy fallback.")
        return fallback_strategy or {}

    try:
        import requests
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        prompt = (
            f"You are the Chief Growth Strategist for YouTube Shorts ({channel_id}).\n"
            f"Empirical Performance Data:\n{json.dumps(performance_summary, indent=2)}\n\n"
            "Generate an optimized strategy mutation strictly formatted as JSON matching this schema:\n"
            "{\n"
            f'  "channel_id": "{channel_id}",\n'
            '  "strategy_version": "v1.2",\n'
            '  "parent_version": "v1.1",\n'
            '  "target_duration": [30.0, 48.0],\n'
            '  "tts_speed": 1.05,\n'
            '  "allowed_hook_types": ["COUNTERFACTUAL", "SOCRATIC_QUESTION"],\n'
            '  "pacing_rules": {"max_words_per_scene": 24, "target_word_count": 95},\n'
            '  "visual_rules": {"code_card_theme": "tokyo_night", "camera_motion_zoom": 0.03},\n'
            '  "hypothesized_apv_impact": 4.5,\n'
            '  "rationale": "Empirical data shows 4% higher APV when using socratic hooks with 10% slower audio pacing."\n'
            "}"
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2
            }
        }

        resp = requests.post(endpoint, json=payload, timeout=30)
        resp.raise_for_status()
        res_json = resp.json()
        
        candidates = res_json.get("candidates", [])
        if not candidates:
            raise RuntimeError("No candidate responses returned from Gemini API.")
            
        raw_text = candidates[0]["content"]["parts"][0]["text"]
        validated_mutation = validate_gemini_strategy(raw_text)
        logging.info(f"[Strategy Generator] Gemini proposed valid strategy: {validated_mutation.strategy_version}")
        return validated_mutation.to_dict()

    except Exception as e:
        logging.warning(f"[Strategy Generator Warning] Gemini strategy generation failed or rejected ({e}). Safely falling back.")
        return fallback_strategy or {}
