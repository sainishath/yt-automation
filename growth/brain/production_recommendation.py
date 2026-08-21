# -*- coding: utf-8 -*-
"""
production_recommendation.py
----------------------------
Phase 29: Production Recommendation & Packaging Engine.
Generates complete video production plans (topic, angle, packaging, script structure,
visual strategy, pacing, voice, subtitles, invariants) and saves brain_production_plan.json.
Enforces single-variable experiment discipline.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
from pathlib import Path

from growth.brain.schemas import BrainDecision, ConfidenceLevel


@dataclass
class ProductionRecommendation:
    recommendation_id: str
    channel_id: str
    topic: str
    angle: str
    title_recommendation: str
    hook_recommendation: str
    script_structure: List[str]
    target_duration: str
    pacing_recommendation: str
    visual_strategy: str
    visual_change_triggers: str
    voice_recommendation: str
    subtitle_recommendation: str
    CTA_recommendation: str
    ending_recommendation: str
    experiment_variable: str
    control_spec: str
    treatment_spec: str
    invariants: List[str]
    rationale: str
    supporting_evidence: List[Dict[str, Any]]
    confidence: str
    expected_learning: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProductionRecommendationEngine:
    """
    Generates comprehensive, packaging-aware production plans from Content Brain decisions.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = Path(output_dir) if output_dir else Path(__file__).parent.parent.parent

    def generate_recommendation(
        self,
        decision: BrainDecision,
        save_plan_file: bool = True
    ) -> ProductionRecommendation:
        """
        Synthesizes a BrainDecision into a detailed, executable ProductionRecommendation.
        """
        ch = decision.channel_id
        opp = decision.opportunity
        hyp = decision.hypothesis
        var = decision.variable_under_test or "HOOK_STRUCTURE"

        # 1. Single-Variable Validation Gate
        if hyp:
            # Verify only 1 variable under test
            if not hyp.variable_under_test or hyp.variable_under_test == "UNKNOWN":
                raise ValueError("Cannot generate production plan: Undefined variable under test.")

        # Packaging recommendations tailored to channel archetype
        if ch == "channel_a":
            # Channel A: Chronos Shift / Alternate History
            topic_str = opp.topic if opp else "What if the Library of Alexandria survived?"
            title_str = f"What If {topic_str.replace('What if ', '').replace('?', '')}?"
            hook_str = opp.proposed_hook if opp else topic_str
            script_struct = [
                "Beat 0 (0-4s): High-Stakes Counterfactual Hook Statement",
                "Beat 1 (4-10s): The Historical Divergence Point & Context",
                "Beat 2 (10-18s): Immediate Cascade & Technological / Military Shift",
                "Beat 3 (18-28s): Global Geopolitical Realignment",
                "Beat 4 (28-38s): Modern Era Consequences & Societal Contrast",
                "Beat 5 (38-45s): Climax & Provocative Closing Reflection"
            ]
            visual_strat = "SDXL Photorealistic oil/cinematic digital art with 8% linear Ken Burns camera motion."
            voice_rec = "ChristopherNeural (Deep authoritative documentary narration) - Pitch: +0Hz, Rate: +0%"
            sub_rec = "Whisper-aligned dynamic ASS subtitles, yellow keyword emphasis, center-bottom safe zone."
            cta_rec = "Pinned Comment Question: 'Which civilization would dominate today? Tell us below.'"
            ending_rec = "Echo consequence closing with prompt to subscribe for daily turning points."
            pacing_rec = "Fast 3.2s average visual beat duration with zero static freeze."

        else:
            # Channel B: Debate Protocol / Conversational Shorts
            topic_str = opp.topic if opp else "Why your brain forgets names in three seconds"
            title_str = f"The Truth About {topic_str.replace('Why ', '')}"
            hook_str = opp.proposed_hook if opp else topic_str
            script_struct = [
                "Turn 1 (Host A): Provocative Question / Paradox Hook",
                "Turn 2 (Host B): Common Myth / Intuitive Explanation",
                "Turn 3 (Host A): Empirical Counter-Evidence & Cognitive Reality",
                "Turn 4 (Host B): Philosophical & Psychological Implication",
                "Turn 5 (Host A): Practical Daily Takeaway",
                "Turn 6 (Host B): Closing Challenge / Moral Paradox"
            ]
            visual_strat = "Fast-paced dynamic split-host avatar framing over engaging motion background."
            voice_rec = "Dual Piper Voices: Host A (Ryan - Analytical), Host B (Samantha - Inquisitive)."
            sub_rec = "Speaker-colored kinetic subtitles (Host A: Cyan, Host B: Yellow) with word-by-word pop."
            cta_rec = "Which side are you on? Drop your argument in the comments."
            ending_rec = "Sharp abrupt paradox punchline leaving audience thinking."
            pacing_rec = "Conversational cadence (165 words per minute) with instant speaker transitions."

        rec_id = f"rec_{ch}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        rec = ProductionRecommendation(
            recommendation_id=rec_id,
            channel_id=ch,
            topic=topic_str,
            angle=opp.content_angle if opp else "Historical Divergence",
            title_recommendation=title_str,
            hook_recommendation=hook_str,
            script_structure=script_struct,
            target_duration="42s - 50s",
            pacing_recommendation=pacing_rec,
            visual_strategy=visual_strat,
            visual_change_triggers="Whisper phonetic word boundary transition",
            voice_recommendation=voice_rec,
            subtitle_recommendation=sub_rec,
            CTA_recommendation=cta_rec,
            ending_recommendation=ending_rec,
            experiment_variable=var,
            control_spec=hyp.control_spec if hyp else "Standard baseline structure",
            treatment_spec=hyp.treatment_spec if hyp else "Experimental treatment structure",
            invariants=decision.invariants or [
                "Voice Actor Profiles",
                "Visual Art Style Architecture",
                "Motion Profile (8% Ken Burns)",
                "Audio Mix (-22dB background ducking)",
                "17/17 QA Gate Verification",
                "Discord Human Review Gate"
            ],
            rationale=decision.reasoning,
            supporting_evidence=[e.to_dict() for e in (opp.evidence_items if opp else [])],
            confidence=decision.confidence.value,
            expected_learning=hyp.expected_learning if hyp else "Evaluates impact of single isolated variable on APV.",
            created_at=now_str
        )

        # 2. Save brain_production_plan.json if requested
        if save_plan_file:
            plan_path = self.output_dir / f"brain_production_plan_{ch}.json"
            with open(plan_path, "w", encoding="utf-8") as f:
                json.dump(rec.to_dict(), f, indent=2, ensure_ascii=False)

        return rec
