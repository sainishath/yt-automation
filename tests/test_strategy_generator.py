# -*- coding: utf-8 -*-
"""
test_strategy_generator.py
--------------------------
Unit tests for the schema-validated Gemini Strategy Generator.
"""

import pytest
from growth.brain.strategy_generator import (
    validate_gemini_strategy,
    generate_strategy_with_gemini,
    StrategyMutation
)

def test_valid_strategy_mutation():
    valid_payload = {
        "channel_id": "channel_a",
        "strategy_version": "v1.2",
        "parent_version": "v1.1",
        "target_duration": [35.0, 48.0],
        "tts_speed": 1.05,
        "allowed_hook_types": ["COUNTERFACTUAL", "SOCRATIC_QUESTION"],
        "pacing_rules": {"max_words_per_scene": 22, "target_word_count": 92},
        "visual_rules": {"code_card_theme": "tokyo_night", "zoom_pct": 0.03},
        "hypothesized_apv_impact": 5.2,
        "rationale": "Empirical evidence from last 10 shorts shows higher APV with socratic questions."
    }
    
    mutation = validate_gemini_strategy(valid_payload)
    assert isinstance(mutation, StrategyMutation)
    assert mutation.channel_id == "channel_a"
    assert mutation.strategy_version == "v1.2"
    assert mutation.tts_speed == 1.05
    assert "COUNTERFACTUAL" in mutation.allowed_hook_types

def test_markdown_wrapped_json():
    raw_str = """```json
    {
      "channel_id": "channel_b",
      "strategy_version": "v2.1",
      "parent_version": "v2.0",
      "target_duration": [30.0, 45.0],
      "tts_speed": 1.10,
      "allowed_hook_types": ["REAL_WORLD_METAPHOR", "MISTAKE_FIRST"],
      "pacing_rules": {"max_words_per_scene": 24, "target_word_count": 95},
      "visual_rules": {"code_card_theme": "dracula"},
      "hypothesized_apv_impact": 3.0,
      "rationale": "Beginners retain code concepts 15% better with physical real-world metaphors."
    }
    ```"""
    mutation = validate_gemini_strategy(raw_str)
    assert mutation.strategy_version == "v2.1"
    assert mutation.channel_id == "channel_b"

def test_missing_fields_raises_error():
    invalid = {
        "channel_id": "channel_a",
        "strategy_version": "v1.2"
        # missing other fields
    }
    with pytest.raises(ValueError, match=r"Missing required fields"):
        validate_gemini_strategy(invalid)

def test_out_of_bounds_duration_raises_error():
    invalid = {
        "channel_id": "channel_a",
        "strategy_version": "v1.2",
        "parent_version": "v1.1",
        "target_duration": [10.0, 95.0],  # out of 20-60 range
        "tts_speed": 1.05,
        "allowed_hook_types": ["COUNTERFACTUAL"],
        "pacing_rules": {"max_words_per_scene": 22, "target_word_count": 92},
        "visual_rules": {"code_card_theme": "tokyo_night"},
        "hypothesized_apv_impact": 5.2,
        "rationale": "Valid test explanation text here."
    }
    with pytest.raises(ValueError, match=r"STRATEGY_BOUNDS_ERROR"):
        validate_gemini_strategy(invalid)

def test_invalid_hook_type_raises_error():
    invalid = {
        "channel_id": "channel_a",
        "strategy_version": "v1.2",
        "parent_version": "v1.1",
        "target_duration": [30.0, 45.0],
        "tts_speed": 1.05,
        "allowed_hook_types": ["UNAUTHORIZED_SCREAMER_HOOK"],
        "pacing_rules": {"max_words_per_scene": 22, "target_word_count": 92},
        "visual_rules": {"code_card_theme": "tokyo_night"},
        "hypothesized_apv_impact": 5.2,
        "rationale": "Valid test explanation text here."
    }
    with pytest.raises(ValueError, match=r"STRATEGY_ENUM_ERROR"):
        validate_gemini_strategy(invalid)

def test_safe_fallback_without_api_key():
    fallback = {"strategy_version": "v1.0_baseline", "channel_id": "channel_a"}
    res = generate_strategy_with_gemini("channel_a", {}, fallback_strategy=fallback)
    assert res == fallback
