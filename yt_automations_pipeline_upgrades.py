"""
yt-automations Monorepo Upgrade Suite (v2 — Calibrated to @sainishath4220 Audit)
Author: Prepared for Gujjari Sai Nishath (@sainishath)
Target Repository: https://github.com/sainishath/yt-automation (Private yt-automations monorepo)
Audited Channel: https://www.youtube.com/@sainishath4220 (5 Published Shorts, 122 Total Views)

Fixes the 6 exact root causes discovered across your 5 published Shorts on @sainishath4220:
1. RAG Counterfactual Suppression Fix (fixes Stalingrad & Berlin Wall Shorts telling real history instead of 'What If')
2. Anti-Repetition & Anti-Hedging Script Gate (fixes Egypt verbatim sentence loop & Rome/Alexandria vague hedging)
3. Fooocus SDXL Negative Prompt & Split-Panel QA Gate (fixes 'TIP PROGAPNINTA' text, 2-panel grids, and Mandalorian helmets)
4. Mobile-Safe Shorts Subtitle Positioning & Compliant YouTube API Upload (moves captions out of YT bottom UI zone)
"""

from __future__ import annotations

import json
import os
import random
import re
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import cv2
import numpy as np
import requests

try:
    from pydantic import BaseModel, Field  # type: ignore
    _HAS_PYDANTIC = True
except ImportError:
    _HAS_PYDANTIC = False


# ==============================================================================
# 1. ANTI-REPETITION, ANTI-HEDGING & COUNTERFACTUAL SCRIPT GATE
#    Fixes:
#    - Short 2 (Egypt, 2FJHdTGpRpc): Verbatim repetition of "commissioned by Pharaoh Khufu during the fourth dynasty"
#    - Short 4 (Alexandria, SEjKTQpHOOU): Ending at 0:37 with "Join us as we explore..." & zero concrete facts
#    - Short 5 (Rome, zNzOWnYZheA): Repeating "Roman Empire" 6x and hedging ("might have", "could have potentially")
# ==============================================================================

BANNED_HEDGING_AND_FILLER_PATTERNS = [
    r"\bmight have\b",
    r"\bcould have potentially\b",
    r"\bit is possible that\b",
    r"\bjoin us as we explore\b",
    r"\bwatch to find out\b",
    r"\btestament to what might have been\b",
]


def audit_script_quality(beats: List[str], title_entity: str) -> Dict[str, object]:
    """
    Deterministic QA gate for 6-to-8 beat Shorts scripts before TTS synthesis:
    1. Rejects duplicate/near-duplicate beats (fixes the Egypt Khufu 4th Dynasty loop).
    2. Rejects weak hedging phrases and trailing "Join us as we explore" intros at the end of a Short.
    3. Flags excessive repetition of the main entity noun (>3 times across 40 seconds).
    """
    issues: List[str] = []
    full_text = " ".join(beats)

    # Check 1: Cross-beat n-gram overlap (catches Egypt beat 1 vs beat 3 repetition)
    normalized_beats = [re.sub(r"[^a-z0-9\s]", "", b.lower()).split() for b in beats]
    for i in range(len(normalized_beats)):
        for j in range(i + 1, len(normalized_beats)):
            set_i, set_j = set(normalized_beats[i]), set(normalized_beats[j])
            if set_i and set_j:
                jaccard = len(set_i & set_j) / len(set_i | set_j)
                if jaccard > 0.55:
                    issues.append(f"Beat {i+1} and Beat {j+1} have {jaccard:.0%} word overlap (duplicate fact loop).")

    # Check 2: Banned hedging & filler phrases (catches Rome & Alexandria filler)
    for pat in BANNED_HEDGING_AND_FILLER_PATTERNS:
        if re.search(pat, full_text, flags=re.IGNORECASE):
            issues.append(f"Contains weak hedging/filler phrase matching '{pat}'. Rewrite in bold present-tense.")

    # Check 3: Main entity repetition cap (catches "Roman Empire" repeated 6x in 40s)
    entity_count = len(re.findall(re.escape(title_entity), full_text, flags=re.IGNORECASE))
    if entity_count > 3:
        issues.append(f"Entity '{title_entity}' repeated {entity_count}x (max 3x in a 45s Short). Use pronouns/epithets.")

    return {"passed": len(issues) == 0, "issues": issues}


# ==============================================================================
# 2. TWO-PHASE RAG VERIFIER: REAL PIVOT (BEATS 1-2) + COUNTERFACTUAL (BEATS 3-6)
#    Fixes:
#    - Short 1 (Berlin Wall, 3acz-TlpYx0) & Short 3 (Stalingrad, fqClEqxTJBE):
#      RAG forced the script to recite real history ("In the end, the Soviet Union emerged victorious")
#      instead of answering the "What If" question in the title!
# ==============================================================================

if _HAS_PYDANTIC:
    class BeatVerification(BaseModel):  # type: ignore[no-redef]
        beat_index: int
        beat_role: str = Field(description="'HISTORICAL_ANCHOR' (Beats 1-2) or 'COUNTERFACTUAL_DOMINO' (Beats 3-6)")
        is_valid: bool
        source_or_causality_note: str
        rewritten_beat_if_invalid: str = ""

    class CounterfactualScriptAudit(BaseModel):  # type: ignore[no-redef]
        answers_title_what_if_premise: bool
        avoids_real_history_ending_contradiction: bool
        has_concrete_historical_nouns_in_every_beat: bool
        beat_audits: List[BeatVerification]
else:
    @dataclass
    class BeatVerification:  # type: ignore[no-redef]
        beat_index: int
        beat_role: str
        is_valid: bool
        source_or_causality_note: str
        rewritten_beat_if_invalid: str = ""

        def model_dump(self) -> Dict[str, Any]:
            return {
                "beat_index": self.beat_index,
                "beat_role": self.beat_role,
                "is_valid": self.is_valid,
                "source_or_causality_note": self.source_or_causality_note,
                "rewritten_beat_if_invalid": self.rewritten_beat_if_invalid,
            }

    @dataclass
    class CounterfactualScriptAudit:  # type: ignore[no-redef]
        answers_title_what_if_premise: bool
        avoids_real_history_ending_contradiction: bool
        has_concrete_historical_nouns_in_every_beat: bool
        beat_audits: List[BeatVerification] = field(default_factory=list)

        @classmethod
        def model_validate_json(cls, raw_json: str) -> "CounterfactualScriptAudit":
            data = json.loads(raw_json)
            audits = [BeatVerification(**b) for b in data.get("beat_audits", [])]
            return cls(
                answers_title_what_if_premise=bool(data.get("answers_title_what_if_premise", False)),
                avoids_real_history_ending_contradiction=bool(
                    data.get("avoids_real_history_ending_contradiction", False)
                ),
                has_concrete_historical_nouns_in_every_beat=bool(
                    data.get("has_concrete_historical_nouns_in_every_beat", False)
                ),
                beat_audits=audits,
            )


def verify_counterfactual_script_with_cloud_llm(
    title: str, beats: List[str], rag_evidence_packet: str, model_name: str = "gemini-2.5-flash"
) -> CounterfactualScriptAudit:
    """
    Separates RAG fact-checking from Counterfactual Domino validation using Gemini 2.5 Flash:
    - Beats 1-2 (0-12s) MUST be grounded in the RAG evidence packet (the real historical point of divergence).
    - Beats 3-6 (12-45s) MUST diverge from real history to answer the 'What If' title with specific,
      plausible geopolitical/scientific domino effects (never reverting to 'In the end, real history happened').
    """
    from google import genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY environment variable.")

    client = genai.Client(api_key=api_key)
    numbered_beats = "\n".join(f"Beat {i+1}: {b}" for i, b in enumerate(beats))
    prompt = (
        f"VIDEO TITLE: {title}\n\n"
        "You are auditing an Alternate History Short script.\n"
        "CRITICAL RULES:\n"
        "1. Beats 1-2 must establish the real historical point of divergence using the RAG EVIDENCE.\n"
        "2. Beats 3-6 MUST explore the counterfactual 'What If' timeline promised by the title. "
        "If the title asks 'What If Nazi Germany Captured Stalingrad?', the ending MUST NOT say "
        "'In the end, the Soviet Union emerged victorious.' It must show the alternate timeline (e.g. cutoff of Volga, "
        "fall of Caucasus oil fields, prolonged Eastern Front stalemate).\n"
        "3. Every beat must name a specific historical person, place, technology, or date—no vague platitudes.\n\n"
        f"RAG EVIDENCE PACKET:\n{rag_evidence_packet}\n\n"
        f"SCRIPT BEATS:\n{numbered_beats}"
    )
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": CounterfactualScriptAudit,
        },
    )
    return CounterfactualScriptAudit.model_validate_json(response.text)


# ==============================================================================
# 3. FOOOCUS SDXL NEGATIVE PROMPT LOCK & SPLIT-PANEL QA GATE
#    Fixes:
#    - Short 3 (Stalingrad, fqClEqxTJBE @ 0:29): 3-panel collage with AI gibberish text "TIP PROGAPNINTA"
#    - Short 5 (Rome, zNzOWnYZheA @ 0:16, 0:23, 0:34): 2-panel split grid & Star Wars Mandalorian helmet
#    - Short 1 (Berlin Wall, 3acz-TlpYx0 @ 0:08, 0:24): Clocks on guard tower & medieval castle in open farmland
#    - Short 4 (Alexandria, SEjKTQpHOOU @ 0:15): Modern ballpoint pen & hardcover book in ancient Egypt
# ==============================================================================

FOOOCUS_NEGATIVE_PROMPT_LOCK = (
    "text, letters, typography, watermark, signature, gibberish text, poster text, signage, "
    "split screen, multi-panel, collage, comic strip, 2-panel grid, 3-panel grid, horizontal divider, "
    "frame border, sci-fi armor, mandalorian helmet, T-visor helmet, modern ballpoint pen, modern hardhats, "
    "wall clocks on exterior tower, medieval castle in 20th century city, blurry, deformed hands, extra limbs"
)


def build_fooocus_scene_prompt(scene_description: str, era_context: str) -> Dict[str, str]:
    """Enforces single-frame vertical composition and period-accurate visual constraints for Fooocus SDXL."""
    positive = (
        f"Single full-bleed vertical 9:16 cinematic photograph, {era_context}, {scene_description}, "
        "dramatic volumetric lighting, historically authentic wardrobe and architecture, 35mm archival film grain, "
        "no text, no split screen"
    )
    return {"prompt": positive, "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK}


def detect_split_panel_collage(image_path: str) -> bool:
    """
    17-Point QA Gate addition: Detects horizontal split-screen divider bars (like Rome @ 0:23 and Stalingrad @ 0:29)
    by scanning the middle 60% of the image for uniform horizontal separator lines.
    Returns True if a defective multi-panel grid is detected so Fooocus regenerates the keyframe.
    """
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return False
    h, w = img.shape
    mid_band = img[int(h * 0.25) : int(h * 0.75), :]
    row_std = np.std(mid_band, axis=1)
    # A solid white/black/gray horizontal divider bar across the full width has near-zero row std
    return bool(np.any(row_std < 3.5))


# ==============================================================================
# 4. MOBILE-SAFE SHORTS SUBTITLES & DYNAMIC CAMERA COMPOSITOR
#    Fixes:
#    - All 5 Shorts on @sainishath4220 place small white subtitles at the bottom edge (y > 1700),
#      where the YouTube Shorts mobile UI (@sainishath4220 handle, title, audio bar) covers them!
# ==============================================================================

MOTION_TRAJECTORIES = [
    "zoompan=z='min(zoom+0.0010,1.18)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps=30",
    "zoompan=z='if(eq(on,1),1.18,max(zoom-0.0010,1.0))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps=30",
    "zoompan=z='1.12':x='(iw-iw/zoom)*(on/{frames})':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps=30",
    "zoompan=z='1.12':x='(iw-iw/zoom)*(1-on/{frames})':y='(ih-ih/zoom)*(on/{frames})':d={frames}:s=1080x1920:fps=30",
]

# Places bold, high-contrast captions in the upper-lower-third safe zone (MarginV=620 on 1920px height)
# so they NEVER collide with the YouTube Shorts title/channel overlay at the bottom of the screen.
SAFE_SHORTS_ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,72,&H0000FFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,5,2,2,80,80,620,1
"""


def render_dynamic_short_scene(image_path: str, duration_sec: float, output_clip_path: str) -> None:
    """Renders a 9:16 keyframe with randomized camera motion instead of frozen Candidate A Ken Burns."""
    frames = max(1, int(duration_sec * 30))
    motion_expr = random.choice(MOTION_TRAJECTORIES).format(frames=frames)
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", image_path,
        "-vf", f"{motion_expr},format=yuv420p",
        "-t", f"{duration_sec:.2f}", "-c:v", "libx264", "-preset", "fast", "-crf", "20", output_clip_path,
    ]
    subprocess.run(cmd, check=True)


# ==============================================================================
# 5. COMPLIANT YOUTUBE API UPLOAD & ENV-VAR DISCORD ALERTING
#    Fixes:
#    - Section 4.3 of yt_automations_monetization_and_view_growth_plan.pdf
# ==============================================================================

def send_discord_alert(message: str, is_error: bool = False) -> None:
    """Reads webhook strictly from environment variables (never hardcoded in source)."""
    env_key = "DISCORD_ERROR_WEBHOOK_URL" if is_error else "DISCORD_REVIEW_WEBHOOK_URL"
    webhook_url = os.environ.get(env_key)
    if not webhook_url:
        raise RuntimeError(f"Missing required environment variable: {env_key}")
    resp = requests.post(webhook_url, json={"content": message}, timeout=10)
    resp.raise_for_status()


def build_youtube_insert_body(
    title: str,
    description: str,
    tags: List[str],
    rag_sources: List[str],
    privacy_status: str = "private",
    publish_at_iso: Optional[str] = None,
) -> Dict[str, object]:
    """
    Constructs a fully compliant YouTube Data API v3 videos.insert payload:
    - Sets categoryId='27' (Education)
    - Declares containsSyntheticMedia=True for AI visuals/voice compliance
    - Appends verified RAG historical citations to description for YPP originality review
    """
    citation_block = "\n\nHistorical Sources & References:\n" + "\n".join(f"- {s}" for s in rag_sources[:4])
    full_description = f"{description.strip()}{citation_block}\n\n#AlternateHistory #HistoryShorts #WhatIf"

    status_block: Dict[str, object] = {
        "privacyStatus": privacy_status,
        "selfDeclaredMadeForKids": False,
        "containsSyntheticMedia": True,
    }
    if publish_at_iso and privacy_status == "private":
        status_block["publishAt"] = publish_at_iso

    return {
        "snippet": {
            "title": title[:100],
            "description": full_description[:5000],
            "tags": tags[:15],
            "categoryId": "27",
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": status_block,
    }
