# -*- coding: utf-8 -*-
"""
strategy_manager.py
-------------------
Manages immutable versioned strategy memory for Channel A and Channel B.
Ensures history is never silently overwritten.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

STRATEGY_DIR = Path(__file__).parent


class StrategyManager:
    def __init__(self, strategy_dir: Path = STRATEGY_DIR):
        self.strategy_dir = strategy_dir

    def get_active_strategy(self, channel_id: str) -> Dict[str, Any]:
        """Loads the active (highest version) strategy for a channel."""
        files = list(self.strategy_dir.glob(f"{channel_id}_strategy_*.json"))
        if not files:
            filename = "channel_a_strategy_v1.json" if channel_id == "channel_a" else "channel_b_strategy_v1.json"
            strat_path = self.strategy_dir / filename
            if not strat_path.exists():
                raise FileNotFoundError(f"Strategy file not found: {strat_path}")
            with open(strat_path, "r", encoding="utf-8") as f:
                return json.load(f)

        files.sort(key=lambda p: p.name, reverse=True)
        with open(files[0], "r", encoding="utf-8") as f:
            return json.load(f)

    def validate_strategy_compatibility(self, video_plan: Dict[str, Any], strategy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Advises whether the video plan complies with the active strategy recommendations.
        Note: Strategy is advisory and never overrides hard factual or safety gates.
        """
        duration = video_plan.get("duration", 45.0)
        opt_duration = strategy.get("winning_patterns", {}).get("optimal_duration_seconds", [30, 60])

        duration_fit = opt_duration[0] <= duration <= opt_duration[1]
        return {
            "strategy_version": strategy.get("strategy_version", "v1.0"),
            "duration_fit": duration_fit,
            "optimal_duration_range": opt_duration,
            "status": "COMPLIANT" if duration_fit else "ADVISORY_DEVIATION"
        }
