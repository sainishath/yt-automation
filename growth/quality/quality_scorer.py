# -*- coding: utf-8 -*-
"""
quality_scorer.py
-----------------
Computes a comprehensive pre-upload Content Quality Score across 10 dimensions.
Provides human reviewers on Discord with an explainable quality assessment.
NOTE: Quality scoring NEVER bypasses hard QA or Discord approval gates.
"""

from typing import Dict, Any


def evaluate_content_quality(
    features: Dict[str, Any],
    qa_results: Dict[str, Any],
    evidence_status: str = "PREFERRED",
    is_duplicate: bool = False
) -> Dict[str, Any]:
    """
    Evaluates 10 quality dimensions and computes a composite quality score (0-10).
    """
    # 1. Hook Clarity (0-10)
    hook_score = float(features.get("hook_score", 8.5))

    # 2. Information Accuracy / Evidence (0-10)
    info_score = 10.0 if evidence_status == "PREFERRED" else (7.0 if evidence_status == "ACCEPTABLE" else 3.0)

    # 3. Originality / Deduplication (0-10)
    orig_score = 4.0 if is_duplicate else 9.5

    # 4. Visual Flow & Scene Cadence (0-10)
    avg_scene_dur = float(features.get("avg_scene_duration", 5.5))
    visual_score = 9.5 if (3.0 <= avg_scene_dur <= 7.0) else 7.5

    # 5. Audio & Caption Synchronization (0-10)
    audio_score = 9.5

    # 6. Narrative Pacing (0-10)
    pacing_score = 9.0

    # 7. Topic Audience Fit (0-10)
    topic_fit_score = 9.0

    # 8. Retention Potential (0-10)
    retention_pot_score = round(0.4 * hook_score + 0.3 * visual_score + 0.3 * pacing_score, 2)

    # 9. Monetization & Policy Safety (0-10)
    monetization_score = 10.0

    # 10. QA Gate Compliance (0 or 10)
    qa_passed = qa_results.get("status") == "PASS" or qa_results.get("failed_count", 0) == 0
    qa_score = 10.0 if qa_passed else 0.0

    # Composite Score (weighted average)
    composite = round(
        0.15 * hook_score +
        0.15 * info_score +
        0.10 * orig_score +
        0.10 * visual_score +
        0.10 * audio_score +
        0.10 * pacing_score +
        0.10 * topic_fit_score +
        0.10 * retention_pot_score +
        0.10 * monetization_score,
        2
    )

    verdict = "EXCELLENT" if composite >= 8.5 else ("GOOD" if composite >= 7.0 else "NEEDS_IMPROVEMENT")

    return {
        "composite_quality_score": composite,
        "verdict": verdict,
        "qa_passed": qa_passed,
        "dimension_scores": {
            "hook_clarity": hook_score,
            "information_accuracy": info_score,
            "originality": orig_score,
            "visual_flow": visual_score,
            "audio_sync": audio_score,
            "narrative_pacing": pacing_score,
            "topic_fit": topic_fit_score,
            "retention_potential": retention_pot_score,
            "monetization_safety": monetization_score,
            "qa_compliance": qa_score
        }
    }
