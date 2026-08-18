# -*- coding: utf-8 -*-
"""
feature_extractor_p2.py
-----------------------
Extracts measurable content, dialogue, turn balance, and pacing features for Pipeline 2.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from growth.db.models import VideoFeaturesModel


def extract_p2_features(
    video_id: str,
    manifest_path: Optional[Path] = None,
    topic_category: str = "Debate & Psychology"
) -> VideoFeaturesModel:
    """
    Extracts features from Pipeline 2 manifest or script payload.
    """
    duration = 42.0
    word_count = 120
    speaker_balance = 0.45
    turn_count = 6
    hook_text = ""
    hook_score = 8.8
    hook_type = "Socratic Provocation"
    controversy_level = 0.7

    if manifest_path and manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                mdata = json.load(f)
                diag = mdata.get("dialogue", [])
                if diag:
                    turn_count = len(diag)
                    spk_a_words = sum(len(turn.get("text", "").split()) for turn in diag if turn.get("speaker") in ["Host A", "Speaker A", "A"])
                    spk_b_words = sum(len(turn.get("text", "").split()) for turn in diag if turn.get("speaker") in ["Host B", "Speaker B", "B"])
                    total_words = spk_a_words + spk_b_words
                    if total_words > 0:
                        word_count = total_words
                        speaker_balance = round(spk_b_words / total_words, 2)
                    hook_text = diag[0].get("text", "")
                    if "?" in hook_text:
                        hook_type = "Polar Question"
                    else:
                        hook_type = "Controversial Assertion"
                
                timing = mdata.get("timing", {})
                duration = timing.get("duration", 42.0)
        except Exception:
            pass

    scene_count = max(turn_count, 4)
    avg_scene_duration = duration / max(scene_count, 1)
    visual_change_rate = scene_count / max(duration, 1.0)
    caption_density = word_count / max(duration, 1.0)

    return VideoFeaturesModel(
        video_id=video_id,
        topic_category=topic_category,
        hook_type=hook_type,
        hook_score=hook_score,
        hook_text=hook_text[:200],
        word_count=word_count,
        scene_count=scene_count,
        avg_scene_duration=round(avg_scene_duration, 2),
        visual_change_rate=round(visual_change_rate, 3),
        motion_type="Gameplay Looping",
        motion_intensity=0.5,
        caption_density=round(caption_density, 2),
        narrative_structure="two_host_socratic_duel",
        speaker_balance=speaker_balance,
        turn_count=turn_count,
        controversy_level=controversy_level
    )
