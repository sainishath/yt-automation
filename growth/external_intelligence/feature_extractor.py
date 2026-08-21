# -*- coding: utf-8 -*-
"""
feature_extractor.py
--------------------
Extracts objective facts and structured model interpretations from external video assets.
Separates factual observations from inferred interpretations and normalizes views against channel medians.
"""

import re
import statistics
from typing import Dict, Any, List, Tuple
from growth.external_intelligence.schemas import (
    ExternalVideoModel,
    ExternalObservationModel,
    ObservationType,
    EvidenceLevel,
    ProvenanceSource
)


def extract_title_facts(title: str) -> Dict[str, Any]:
    """Extracts objective, verifiable factual characteristics from title text."""
    clean_title = title.strip()
    words = re.findall(r"\b\w+\b", clean_title)
    starts_what_if = bool(re.match(r"^what\s+if\b", clean_title, re.IGNORECASE))
    starts_if = bool(re.match(r"^if\b", clean_title, re.IGNORECASE))
    has_question_mark = "?" in clean_title
    has_exclamation = "!" in clean_title

    return {
        "title_length_chars": len(clean_title),
        "title_word_count": len(words),
        "starts_what_if": starts_what_if,
        "starts_if": starts_if,
        "has_question_mark": has_question_mark,
        "has_exclamation": has_exclamation
    }


def infer_title_interpretations(title: str, facts: Dict[str, Any]) -> Dict[str, Any]:
    """Infers structural interpretations with explicit confidence values."""
    title_lower = title.lower()

    # Hook Classification
    if facts["starts_what_if"] or (facts["starts_if"] and facts["has_question_mark"]):
        hook_type = "COUNTERFACTUAL_QUESTION"
        confidence = 0.95
        interpretation = "Explicit counterfactual question provoking hypothetical historical curiosity."
    elif facts["starts_if"] and not facts["has_question_mark"]:
        hook_type = "ACTIVE_COUNTERFACTUAL_CLAIM"
        confidence = 0.88
        interpretation = "Direct counterfactual conditional statement establishing immediate scenario divergence."
    elif any(k in title_lower for k in ["you ", "your ", "never ", "stop ", "why you", "truth about"]):
        hook_type = "DIRECT_PROVOCATION"
        confidence = 0.85
        interpretation = "Second-person direct address designed to challenge viewer baseline beliefs."
    elif facts["has_question_mark"]:
        hook_type = "SOCRATIC_QUESTION"
        confidence = 0.80
        interpretation = "Open inquiry encouraging viewer reflection or debate in comments."
    else:
        hook_type = "DECLARATIVE_STATEMENT"
        confidence = 0.70
        interpretation = "Expository informational title."

    # Topic Cluster Inference
    cluster = "GENERAL_EDUCATIONAL"
    if any(k in title_lower for k in ["rome", "roman", "caesar", "empire", "byzantine", "alexandria", "ancient", "greece", "egypt"]):
        cluster = "ANCIENT_EMPIRES_AND_TURNING_POINTS"
    elif any(k in title_lower for k in ["ww2", "world war", "hitler", "germany", "soviet", "cold war", "nuclear", "allies"]):
        cluster = "MODERN_WARFARE_AND_GEOPOLITICAL_DIVERGENCE"
    elif any(k in title_lower for k in ["ai", "robot", "artificial intelligence", "tech", "quantum", "future", "simulation"]):
        cluster = "AI_ETHICS_AND_FUTURE_DILEMMAS"
    elif any(k in title_lower for k in ["psychology", "brain", "bias", "mind", "paradox", "habit", "behavior", "dopamine"]):
        cluster = "COGNITIVE_BIAS_AND_PSYCHOLOGY_PARADOXES"

    # Curiosity gap score
    curiosity_score = 0.5
    if facts["starts_what_if"]:
        curiosity_score += 0.35
    if facts["has_question_mark"]:
        curiosity_score += 0.10
    curiosity_score = round(min(curiosity_score, 1.0), 2)

    return {
        "hook_type": hook_type,
        "topic_cluster": cluster,
        "curiosity_score": curiosity_score,
        "confidence": confidence,
        "interpretation": interpretation
    }


def normalize_external_video_views(
    videos: List[ExternalVideoModel],
    outlier_cap_multiplier: float = 3.0
) -> List[ExternalVideoModel]:
    """
    Computes channel median view baselines and assigns relative_view_multiplier.
    Caps extreme viral view spikes to prevent distorting pattern mining.
    """
    if not videos:
        return videos

    view_counts = [v.views for v in videos if v.views > 0]
    median_views = float(statistics.median(view_counts)) if view_counts else 1000.0

    for v in videos:
        raw_mult = round(float(v.views) / max(median_views, 1.0), 2)
        v.relative_view_multiplier = min(raw_mult, outlier_cap_multiplier)

    return videos


def build_observations_for_video(
    video: ExternalVideoModel
) -> List[ExternalObservationModel]:
    """Generates discrete Level 1 Fact and Level 2 Interpretation observation records for a video."""
    facts = extract_title_facts(video.title)
    interp = infer_title_interpretations(video.title, facts)
    observations = []

    # 1. Fact Observation: Duration
    observations.append(ExternalObservationModel(
        observation_id=f"obs_fact_dur_{video.youtube_video_id}",
        external_video_id=video.external_video_id,
        observation_type=ObservationType.OBJECTIVE_FACT,
        field_name="duration_seconds",
        observed_value=str(round(video.duration_seconds, 1)),
        interpretation="Short-form vertical video duration under 60 seconds",
        evidence_level=EvidenceLevel.LEVEL_1_OBSERVATION,
        confidence=1.0,
        is_simulation=video.is_simulation,
        source_type=video.source_type
    ))

    # 2. Fact Observation: Title Text
    observations.append(ExternalObservationModel(
        observation_id=f"obs_fact_title_{video.youtube_video_id}",
        external_video_id=video.external_video_id,
        observation_type=ObservationType.OBJECTIVE_FACT,
        field_name="title_text",
        observed_value=video.title,
        interpretation=None,
        evidence_level=EvidenceLevel.LEVEL_1_OBSERVATION,
        confidence=1.0,
        is_simulation=video.is_simulation,
        source_type=video.source_type
    ))

    # 3. Interpretation Observation: Hook Structure
    observations.append(ExternalObservationModel(
        observation_id=f"obs_interp_hook_{video.youtube_video_id}",
        external_video_id=video.external_video_id,
        observation_type=ObservationType.INTERPRETATION,
        field_name="hook_structure",
        observed_value=interp["hook_type"],
        interpretation=interp["interpretation"],
        evidence_level=EvidenceLevel.LEVEL_2_EXTERNAL_EVIDENCE,
        confidence=interp["confidence"],
        is_simulation=video.is_simulation,
        source_type=video.source_type
    ))

    # 4. Interpretation Observation: Topic Cluster
    observations.append(ExternalObservationModel(
        observation_id=f"obs_interp_cluster_{video.youtube_video_id}",
        external_video_id=video.external_video_id,
        observation_type=ObservationType.INTERPRETATION,
        field_name="topic_cluster",
        observed_value=interp["topic_cluster"],
        interpretation=f"Semantic category cluster for audience alignment",
        evidence_level=EvidenceLevel.LEVEL_2_EXTERNAL_EVIDENCE,
        confidence=0.85,
        is_simulation=video.is_simulation,
        source_type=video.source_type
    ))

    return observations
