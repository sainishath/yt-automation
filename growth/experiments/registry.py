# -*- coding: utf-8 -*-
"""
registry.py
-----------
Predefined hypotheses and experiment definitions for Channel A and Channel B.
"""

from typing import Dict, Any, List

PREDEFINED_EXPERIMENTS: List[Dict[str, Any]] = [
    {
        "experiment_id": "EXP_A_HOOK_01",
        "channel_id": "channel_a",
        "name": "Question Hook vs Active Counterfactual Statement",
        "hypothesis": "Opening with an active counterfactual statement yields >= 5% higher 24h retention than a question hook.",
        "variable_tested": "hook_opening_structure",
        "control_definition": "Polar Question (e.g., 'What if the Roman Empire never fell?')",
        "variant_definition": "Active Counterfactual Claim (e.g., 'If Rome had never fallen, humanity would be 500 years ahead.')",
        "primary_metric": "avg_percentage_viewed",
        "min_sample_size": 4,
        "status": "ACTIVE"
    },
    {
        "experiment_id": "EXP_B_HOOK_01",
        "channel_id": "channel_b",
        "name": "Direct Provocation vs Relatable Habit Question",
        "hypothesis": "Opening with a direct accusation ('You are destroying your morning focus') produces higher comment engagement than a neutral question.",
        "variable_tested": "hook_emotional_tone",
        "control_definition": "Neutral Habit Question",
        "variant_definition": "Direct Second-Person Provocation",
        "primary_metric": "engagement_rate",
        "min_sample_size": 4,
        "status": "ACTIVE"
    }
]
