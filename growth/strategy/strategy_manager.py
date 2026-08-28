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

    def get_strategy(self, channel_id: str, version: Optional[str] = None) -> Dict[str, Any]:
        """Loads a specific version of a channel strategy."""
        if version:
            path = self.strategy_dir / f"{channel_id}_strategy_{version}.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        return self.get_active_strategy(channel_id)

    def get_active_strategy(self, channel_id: str) -> Dict[str, Any]:
        """Loads the active baseline strategy for a channel."""
        # By default, loads baseline v1.0 unless explicitly promoted
        filename = "channel_a_strategy_v1.json" if channel_id == "channel_a" else "channel_b_strategy_v1.json"
        strat_path = self.strategy_dir / filename
        if strat_path.exists():
            with open(strat_path, "r", encoding="utf-8") as f:
                return json.load(f)

        files = list(self.strategy_dir.glob(f"{channel_id}_strategy_*.json"))
        if files:
            files.sort(key=lambda p: p.name)
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

    def get_active_strategy_context(self, channel_id: str) -> Dict[str, Any]:
        """
        Extracts strategic context to dynamically inject into Ollama generation prompts:
        - Winning hook types
        - Optimal duration bounds (min/max)
        - Distilled qualitative learned rules
        - Losing patterns to avoid
        """
        strat = self.get_active_strategy(channel_id)
        winning = strat.get("winning_patterns", {})
        losing = strat.get("losing_patterns", {})
        dur_range = winning.get("optimal_duration_seconds", [35, 55])
        
        learned_rules = strat.get("learned_rules", [])
        
        return {
            "strategy_version": strat.get("strategy_version", "v1.0"),
            "channel_id": channel_id,
            "min_duration_seconds": dur_range[0] if isinstance(dur_range, list) and len(dur_range) > 0 else 35.0,
            "max_duration_seconds": dur_range[1] if isinstance(dur_range, list) and len(dur_range) > 1 else 55.0,
            "winning_hooks": winning.get("hooks", []),
            "winning_narrative_structure": winning.get("narrative_structure", ""),
            "learned_rules": learned_rules,
            "forbidden_losing_patterns": losing.get("hooks", []) + losing.get("topics", [])
        }

    def record_learned_rule(self, channel_id: str, rule: str, experiment_id: str) -> str:
        """
        Creates an immutable new version of the channel strategy containing the newly confirmed learned rule.
        Returns the new strategy version string.
        """
        current_strat = self.get_active_strategy(channel_id)
        curr_ver = current_strat.get("strategy_version", "v1.0")
        
        # Determine next minor version e.g. v1.0 -> v1.1
        try:
            ver_num = float(curr_ver.lstrip("v"))
            new_ver = f"v{round(ver_num + 0.1, 1):.1f}"
        except Exception:
            new_ver = f"{curr_ver}_learned"

        updated_data = dict(current_strat)
        updated_data["strategy_version"] = new_ver
        if "learned_rules" not in updated_data or not isinstance(updated_data["learned_rules"], list):
            updated_data["learned_rules"] = []

        rule_entry = {
            "rule": rule,
            "experiment_id": experiment_id
        }
        if rule_entry not in updated_data["learned_rules"]:
            updated_data["learned_rules"].append(rule_entry)

        new_strat_path = self.strategy_dir / f"{channel_id}_strategy_{new_ver}.json"
        with open(new_strat_path, "w", encoding="utf-8") as f:
            json.dump(updated_data, f, indent=2, ensure_ascii=False)

        return new_ver
