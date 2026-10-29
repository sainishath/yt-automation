# -*- coding: utf-8 -*-
"""
growth/scorer.py
----------------
Growth Engine Topic Scorer with Counterfactual Divergence Pre-Check and 6-Step Outlier Title Rubric.

Fixes:
- Short 5 (Berlin Wall, 3acz-TlpYx0): Allowed a non-counterfactual title
  ("What If a Single Wall Divided East and West Berlin?"—which is real history) to pass into production.
- Short 2 (Egypt, 2FJHdTGpRpc): Allowed a non-counterfactual vague title
  ("What If Ancient Egypt Built a Pyramid Like This?") without a concrete divergence point.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


# Known literal real-history tautologies disguised as "What If" questions
REAL_HISTORY_TAUTOLOGY_PATTERNS = [
    r"what if a single wall divided east and west berlin",
    r"what if the berlin wall divided east and west berlin",
    r"what if ancient egypt built a pyramid like this",
    r"what if ancient egypt built the great pyramid",
    r"what if the soviet union won the battle of stalingrad",
    r"what if the allies won world war ii",
    r"what if the roman empire fell",
    r"what if the library of alexandria burned",
    r"what if the titanic sank",
]

# Counterfactual divergence operators indicating a genuine historical reversal or alternate branch
COUNTERFACTUAL_DIVERGENCE_MARKERS = [
    r"\bnever\b",
    r"\bsurvived\b",
    r"\bcaptured\b",
    r"\bwon\b",
    r"\blost\b",
    r"\bfailed\b",
    r"\bavoided\b",
    r"\bspared\b",
    r"\bprevented\b",
    r"\bconquered\b",
    r"\binvented\b",
    r"\bindustrialized\b",
    r"\badopted\b",
    r"\bdefeated\b",
    r"\bheld\b",
    r"\bescaped\b",
    r"\blived\b",
    r"\bno\s+\w+\b",
    r"\binstead of\b",
    r"\bearlier\b",
    r"\bwithout\b",
]

HIGH_VELOCITY_HISTORICAL_ENTITIES = [
    "roman empire",
    "rome",
    "library of alexandria",
    "alexandria",
    "stalingrad",
    "constantinople",
    "napoleon",
    "julius caesar",
    "caesar",
    "genghis khan",
    "mongol",
    "berlin wall",
    "cold war",
    "titanic",
    "spanish armada",
    "byzantine",
    "ottoman",
    "nikola tesla",
    "printing press",
    "black death",
    "carthage",
    "alexander the great",
    "han dynasty",
    "aztec",
]


def check_counterfactual_divergence(title: str, is_factual_mode: bool = False) -> Dict[str, Any]:
    """
    Pre-Check Gate: Verifies that a 'What If' title actually diverges from real history
    rather than asking a question whose premise is literal textbook history
    (e.g., 'What If a Single Wall Divided East and West Berlin?').
    """
    clean_title = (title or "").strip()
    lower_title = clean_title.lower()

    if is_factual_mode:
        return {
            "is_valid_counterfactual": True,
            "mode": "FACTUAL_DOCUMENTARY",
            "issues": [],
        }

    issues: List[str] = []

    # 1. Reject known real-history tautologies disguised as What-Ifs
    for pat in REAL_HISTORY_TAUTOLOGY_PATTERNS:
        if re.search(pat, lower_title, flags=re.IGNORECASE):
            issues.append(
                f"Title '{clean_title}' describes literal real history or vague clickbait ('{pat}') instead of a counterfactual divergence."
            )

    # 2. Reject dangling demonstratives without a concrete historical mechanism ("Like This?", "Did This?")
    if re.search(r"\b(like this|did this|happened like this)\??$", lower_title):
        issues.append(
            f"Title '{clean_title}' uses vague placeholder ('like this') instead of a concrete counterfactual divergence."
        )

    # 3. Verify presence of a counterfactual divergence operator if framed as a "What If" question
    is_what_if = lower_title.startswith(("what if", "imagine if", "suppose", "had "))
    has_divergence_marker = any(
        re.search(pat, lower_title, flags=re.IGNORECASE) for pat in COUNTERFACTUAL_DIVERGENCE_MARKERS
    )
    if is_what_if and not has_divergence_marker:
        issues.append(
            f"Title '{clean_title}' lacks an explicit counterfactual divergence operator (e.g., 'never fell', 'captured', 'survived', 'won')."
        )

    return {
        "is_valid_counterfactual": len(issues) == 0,
        "mode": "COUNTERFACTUAL",
        "issues": issues,
    }


def evaluate_6step_outlier_title_rubric(title: str) -> Dict[str, Any]:
    """
    Evaluates a candidate title against the 6-Step Outlier Title Rubric from the Grow Channels Playbook:
    Step 1: Counterfactual Divergence Validity (true historical reversal, not real history)
    Step 2: Iconic Entity Recognition (high-search global historical anchor)
    Step 3: High-Stakes Conflict / Domino Tension
    Step 4: Curiosity Gap & Mobile Length (< 60 chars, no truncation in Shorts shelf)
    Step 5: Visualizable 0:00 Hook Frame
    Step 6: Search & Trend Velocity Alignment
    """
    clean_title = (title or "").strip()
    lower_title = clean_title.lower()

    div_check = check_counterfactual_divergence(clean_title)
    step1_divergence = 1.0 if div_check["is_valid_counterfactual"] else 0.0

    matched_entities = [ent for ent in HIGH_VELOCITY_HISTORICAL_ENTITIES if ent in lower_title]
    step2_entity = 1.0 if matched_entities else 0.5

    stakes_terms = [
        "fell", "burned", "captured", "survived", "won", "conquered", "destroyed",
        "collapsed", "war", "empire", "nuclear", "invaded", "assassinated", "failed", "split"
    ]
    step3_conflict = 1.0 if any(t in lower_title for t in stakes_terms) else 0.4

    char_len = len(clean_title)
    step4_mobile_len = 1.0 if (15 <= char_len <= 60) else (0.7 if char_len <= 75 else 0.3)

    visual_nouns = [
        "wall", "pyramid", "library", "empire", "rome", "stalingrad", "fleet", "armada",
        "cannon", "gate", "tower", "city", "legion", "tanks", "scrolls", "constantinople", "napoleon"
    ]
    step5_visual = 1.0 if any(vn in lower_title for vn in visual_nouns) else 0.6

    step6_search = 1.0 if (lower_title.startswith("what if ") and "?" in clean_title) else 0.7

    steps = {
        "step1_counterfactual_divergence": step1_divergence,
        "step2_iconic_entity": step2_entity,
        "step3_conflict_stakes": step3_conflict,
        "step4_mobile_length": step4_mobile_len,
        "step5_visual_hook": step5_visual,
        "step6_search_velocity": step6_search,
    }

    # If Step 1 fails (non-counterfactual tautology like the Berlin Wall upload), hard-cap score
    raw_avg = sum(steps.values()) / len(steps)
    rubric_score = round(raw_avg if step1_divergence > 0 else min(raw_avg, 0.25), 3)

    return {
        "passed": step1_divergence > 0 and rubric_score >= 0.70,
        "rubric_score": rubric_score,
        "steps": steps,
        "issues": div_check["issues"],
    }
