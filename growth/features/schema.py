# -*- coding: utf-8 -*-
"""
schema.py
---------
Feature schema definitions and normalization boundaries for Video Features.
"""

from typing import Dict, Any, List


P1_FEATURE_KEYS = [
    "video_id", "topic_category", "historical_period", "hook_type",
    "hook_score", "hook_text", "question_vs_statement", "stakes_level",
    "word_count", "duration", "scene_count", "avg_scene_duration",
    "visual_change_rate", "motion_type", "motion_intensity",
    "caption_density", "narrative_structure", "evidence_source_count",
    "historical_confidence", "curiosity_score"
]

P2_FEATURE_KEYS = [
    "video_id", "topic_category", "psychology_category", "hook_type",
    "hook_score", "hook_text", "question_vs_statement", "controversy_level",
    "speaker_balance", "turn_count", "avg_turn_length", "word_count",
    "duration", "caption_density", "visual_change_rate", "outro_word_count",
    "curiosity_score"
]
