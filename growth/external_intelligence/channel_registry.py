# -*- coding: utf-8 -*-
"""
channel_registry.py
-------------------
Curated and dynamic analog channel profiles for Channel A (Chronos Shift) and Channel B (Debate Protocol).
Calculates multi-factor similarity scoring across topic, audience, format, duration, storytelling, and production style.
"""

from typing import Dict, Any, List, Optional
from growth.external_intelligence.schemas import ExternalChannelModel, ProvenanceSource


# Curated catalog of benchmark analog archetypes in target niches
ANALOG_CATALOG: Dict[str, List[Dict[str, Any]]] = {
    "channel_a": [
        {
            "external_channel_id": "analog_a_althist_hub",
            "channel_title": "AlternateHistoryHub",
            "handle": "@AlternateHistoryHub",
            "youtube_channel_id": "UClfEht64_NrzHf8Y0dtW49w",
            "content_niche": "Alternate History & Historical Turning Points",
            "topic_similarity": 0.95,
            "audience_similarity": 0.90,
            "format_similarity": 0.85,
            "duration_similarity": 0.80,
            "storytelling_similarity": 0.95,
            "production_similarity": 0.80,
            "notes": "Pioneer in counterfactual history and geopolitical turning point narratives."
        },
        {
            "external_channel_id": "analog_a_whatif_hist",
            "channel_title": "What If History Shorts",
            "handle": "@WhatIfHistoryShorts",
            "youtube_channel_id": "UC_ANALOG_WHATIF_HIST",
            "content_niche": "Bite-Sized Counterfactuals & Divergence Scenarios",
            "topic_similarity": 0.98,
            "audience_similarity": 0.92,
            "format_similarity": 0.98,
            "duration_similarity": 0.95,
            "storytelling_similarity": 0.90,
            "production_similarity": 0.85,
            "notes": "Direct competitor format: 40-50s historical what-if scenarios with visual narration."
        },
        {
            "external_channel_id": "analog_a_armchair_hist",
            "channel_title": "The Armchair Historian",
            "handle": "@TheArmchairHistorian",
            "youtube_channel_id": "UC3sznuOTq28nqmB04NDJU5Q",
            "content_niche": "Animated & Visual Military/Civilization History",
            "topic_similarity": 0.85,
            "audience_similarity": 0.88,
            "format_similarity": 0.75,
            "duration_similarity": 0.70,
            "storytelling_similarity": 0.90,
            "production_similarity": 0.88,
            "notes": "High visual accuracy and historical grounding in ancient/modern warfare."
        },
        {
            "external_channel_id": "analog_a_timeline_doc",
            "channel_title": "Timeline - World History Documentaries",
            "handle": "@TimelineWorldHistory",
            "youtube_channel_id": "UC88lvyJe7aHZmcvzvubDFRg",
            "content_niche": "Documentary History & Turning Points of Civilization",
            "topic_similarity": 0.88,
            "audience_similarity": 0.85,
            "format_similarity": 0.70,
            "duration_similarity": 0.65,
            "storytelling_similarity": 0.92,
            "production_similarity": 0.90,
            "notes": "Authoritative documentary tone and cinematic archival imagery."
        },
        {
            "external_channel_id": "analog_a_history_legends",
            "channel_title": "History Legends",
            "handle": "@HistoryLegends",
            "youtube_channel_id": "UC_ANALOG_HIST_LEGENDS",
            "content_niche": "Battle Breakdowns & Tactical Decision Analysis",
            "topic_similarity": 0.80,
            "audience_similarity": 0.82,
            "format_similarity": 0.85,
            "duration_similarity": 0.80,
            "storytelling_similarity": 0.85,
            "production_similarity": 0.78,
            "notes": "Analysis of pivotal tactical turning points in famous battles."
        }
    ],
    "channel_b": [
        {
            "external_channel_id": "analog_b_psych_insights",
            "channel_title": "Psychology & Human Behavior Shorts",
            "handle": "@PsychInsightsAI",
            "youtube_channel_id": "UC_ANALOG_PSYCH_INSIGHTS",
            "content_niche": "Cognitive Biases, Paradoxes & Psychological Dilemmas",
            "topic_similarity": 0.95,
            "audience_similarity": 0.92,
            "format_similarity": 0.95,
            "duration_similarity": 0.95,
            "storytelling_similarity": 0.90,
            "production_similarity": 0.85,
            "notes": "Short-form paradox and behavioral contradiction explainers."
        },
        {
            "external_channel_id": "analog_b_ai_dilemmas",
            "channel_title": "Future Tech & AI Dilemmas",
            "handle": "@AIDilemmas",
            "youtube_channel_id": "UC_ANALOG_AI_DILEMMAS",
            "content_niche": "AI Ethics, Autonomous Systems & Philosophical Paradoxes",
            "topic_similarity": 0.92,
            "audience_similarity": 0.90,
            "format_similarity": 0.92,
            "duration_similarity": 0.90,
            "storytelling_similarity": 0.92,
            "production_similarity": 0.88,
            "notes": "Provocative ethical dilemmas in artificial intelligence and automation."
        },
        {
            "external_channel_id": "analog_b_debate_lab",
            "channel_title": "Socratic Debate Protocol",
            "handle": "@SocraticDebateLab",
            "youtube_channel_id": "UC_ANALOG_DEBATE_LAB",
            "content_niche": "Two-Sided Debates, Socratic Dialogues & Counter-Arguments",
            "topic_similarity": 0.98,
            "audience_similarity": 0.95,
            "format_similarity": 0.98,
            "duration_similarity": 0.95,
            "storytelling_similarity": 0.95,
            "production_similarity": 0.92,
            "notes": "Dual-speaker dialogue structure debating controversial psychology/tech questions."
        },
        {
            "external_channel_id": "analog_b_mind_field_clips",
            "channel_title": "Curiosity & Science Explainers",
            "handle": "@CuriosityScienceShorts",
            "youtube_channel_id": "UC_ANALOG_CURIOSITY_SCIENCE",
            "content_niche": "Behavioral Experiments, Thought Experiments & Mind Puzzles",
            "topic_similarity": 0.85,
            "audience_similarity": 0.88,
            "format_similarity": 0.85,
            "duration_similarity": 0.85,
            "storytelling_similarity": 0.90,
            "production_similarity": 0.82,
            "notes": "Engaging thought experiments that challenge common human assumptions."
        }
    ]
}


def calculate_channel_similarity(metrics: Dict[str, float]) -> Dict[str, Any]:
    """
    Computes explainable weighted similarity score between an analog channel and our target channel.
    Weights:
      - Topic Similarity: 25%
      - Audience Similarity: 20%
      - Format (Shorts) Similarity: 20%
      - Duration/Pacing Similarity: 15%
      - Storytelling/Narrative Style: 10%
      - Production Model: 10%
    """
    topic_sim = float(metrics.get("topic_similarity", 0.5))
    aud_sim = float(metrics.get("audience_similarity", 0.5))
    format_sim = float(metrics.get("format_similarity", 0.5))
    dur_sim = float(metrics.get("duration_similarity", 0.5))
    story_sim = float(metrics.get("storytelling_similarity", 0.5))
    prod_sim = float(metrics.get("production_similarity", 0.5))

    weighted_score = (
        0.25 * topic_sim +
        0.20 * aud_sim +
        0.20 * format_sim +
        0.15 * dur_sim +
        0.10 * story_sim +
        0.10 * prod_sim
    )
    final_score = round(min(max(weighted_score, 0.0), 1.0), 3)

    reasons = []
    if topic_sim >= 0.85:
        reasons.append(f"High topic niche alignment ({round(topic_sim * 100)}%)")
    if format_sim >= 0.85:
        reasons.append(f"Direct short-form video match ({round(format_sim * 100)}%)")
    if aud_sim >= 0.85:
        reasons.append(f"Strong demographic/psychographic audience overlap ({round(aud_sim * 100)}%)")
    if story_sim >= 0.85:
        reasons.append("Comparable hook and narrative storytelling cadence")

    confidence = "HIGH" if final_score >= 0.80 else "MEDIUM" if final_score >= 0.60 else "LOW"

    return {
        "similarity_score": final_score,
        "similarity_reasons": reasons,
        "confidence": confidence,
        "breakdown": {
            "topic": topic_sim,
            "audience": aud_sim,
            "format": format_sim,
            "duration": dur_sim,
            "storytelling": story_sim,
            "production": prod_sim
        }
    }


def get_analog_channels_for_target(target_channel_id: str) -> List[ExternalChannelModel]:
    """Retrieves standard analog channel models for a target channel."""
    catalog = ANALOG_CATALOG.get(target_channel_id, [])
    res = []
    for item in catalog:
        sim_eval = calculate_channel_similarity(item)
        ch = ExternalChannelModel(
            external_channel_id=item["external_channel_id"],
            target_channel_id=target_channel_id,
            channel_title=item["channel_title"],
            handle=item.get("handle"),
            youtube_channel_id=item.get("youtube_channel_id"),
            subscriber_count=0,
            video_count=0,
            content_niche=item["content_niche"],
            similarity_score=sim_eval["similarity_score"],
            similarity_reasons=sim_eval["similarity_reasons"],
            confidence=sim_eval["confidence"],
            is_simulation=False,
            source_type=ProvenanceSource.PUBLIC_YOUTUBE
        )
        res.append(ch)
    return res
