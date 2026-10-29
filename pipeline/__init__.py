# -*- coding: utf-8 -*-
"""
pipeline package
----------------
Drop-in upgrade modules for yt-automations (v2 — Calibrated to @sainishath4220 Audit):
- verify_claims: Anti-Repetition, Anti-Hedging & Two-Phase Counterfactual RAG Verifier
- compositor / visuals: Fooocus SDXL Negative Prompt Lock, Split-Panel Detector & Safe Subtitles
- upload_guard / upload: Compliant YouTube Upload, Synthetic Disclosure, RAG Attribution & Env-Var Alerting
- tts: Multi-Language Audio Track Dubbing (Spanish, Portuguese, German, Hindi via Edge-TTS)
"""

from pipeline.verify_claims import (
    BANNED_HEDGING_AND_FILLER_PATTERNS,
    BANNED_HEDGING_PATTERNS,
    BeatVerification,
    CounterfactualScriptAudit,
    audit_script_quality,
    verify_counterfactual_beats_deterministic,
    verify_counterfactual_script_with_cloud_llm,
)
from pipeline.compositor import (
    FOOOCUS_NEGATIVE_PROMPT_LOCK,
    MOTION_TRAJECTORIES,
    SAFE_SHORTS_ASS_HEADER,
    SAFE_SHORTS_ASS_STYLE,
    build_fooocus_scene_prompt,
    detect_split_panel_collage,
    render_dynamic_short_scene,
)
from pipeline.upload_guard import (
    append_rag_citations_to_description,
    build_youtube_insert_body,
    format_rag_citations_footer,
    send_discord_alert,
)

__all__ = [
    "BANNED_HEDGING_AND_FILLER_PATTERNS",
    "BANNED_HEDGING_PATTERNS",
    "BeatVerification",
    "CounterfactualScriptAudit",
    "audit_script_quality",
    "verify_counterfactual_beats_deterministic",
    "verify_counterfactual_script_with_cloud_llm",
    "FOOOCUS_NEGATIVE_PROMPT_LOCK",
    "MOTION_TRAJECTORIES",
    "SAFE_SHORTS_ASS_HEADER",
    "SAFE_SHORTS_ASS_STYLE",
    "build_fooocus_scene_prompt",
    "detect_split_panel_collage",
    "render_dynamic_short_scene",
    "append_rag_citations_to_description",
    "build_youtube_insert_body",
    "format_rag_citations_footer",
    "send_discord_alert",
]
