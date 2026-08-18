# -*- coding: utf-8 -*-
"""
feature_extractor_p1.py
-----------------------
Extracts measurable content, visual, audio, and narrative features for Pipeline 1.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from growth.db.models import VideoFeaturesModel


def extract_p1_features(
    video_id: str,
    output_dir: Path,
    topic_category: str = "History"
) -> VideoFeaturesModel:
    """
    Extracts features from Pipeline 1 run artifacts:
    - metadata.json
    - script.json (or run_manifest.json)
    - evidence_packet.json
    - scene_plan.json
    - qa_report.json
    """
    v_dir = output_dir / video_id
    manifest_file = v_dir / "run_manifest.json"
    metadata_file = v_dir / "metadata.json"
    scene_plan_file = v_dir / "scene_plan.json"
    evidence_file = v_dir / "evidence_packet.json"

    duration = 45.0
    word_count = 100
    hook_text = ""
    hook_score = 8.5
    hook_type = "Counterfactual Divergence"
    scene_count = 8
    historical_period = "Ancient/Classical"

    if metadata_file.exists():
        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                mdata = json.load(f)
                title = mdata.get("title", "")
                if "Roman" in title or "Alexandria" in title or "Egypt" in title:
                    historical_period = "Classical Antiquity"
                elif "19" in title or "Cold War" in title or "War" in title:
                    historical_period = "Modern"
        except Exception:
            pass

    if scene_plan_file.exists():
        try:
            with open(scene_plan_file, "r", encoding="utf-8") as f:
                splan = json.load(f)
                scenes = splan if isinstance(splan, list) else splan.get("scenes", [])
                scene_count = len(scenes) if scenes else 8
                if scenes and len(scenes) > 0:
                    hook_text = scenes[0].get("narration_text", "")
                    if "?" in hook_text:
                        hook_type = "Question/Provocation"
                    else:
                        hook_type = "Active Premise"
        except Exception:
            pass

    if manifest_file.exists():
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest = json.load(f)
                metrics = manifest.get("metrics", {})
                duration = metrics.get("duration", 45.0)
                word_count = metrics.get("word_count", 100)
                if not hook_text:
                    script_text = manifest.get("script", "")
                    if script_text:
                        lines = script_text.split(".")
                        hook_text = lines[0] if lines else ""
        except Exception:
            pass

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
        motion_type="Candidate A Linear Ken Burns",
        motion_intensity=0.08,
        caption_density=round(caption_density, 2),
        narrative_structure="8_beat_counterfactual",
        speaker_balance=1.0,
        turn_count=1,
        controversy_level=0.4
    )
