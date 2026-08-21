# -*- coding: utf-8 -*-
"""
strategy_evolution.py
---------------------
Phase 14: Immutable Strategy Evolution Engine for Content Brain.
Proposes and generates incremental, immutable strategy versions (v1.0 -> v1.1 -> v1.2)
backed strictly by empirical N >= 4 experiment outcomes.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
import json

from growth.strategy.strategy_manager import StrategyManager, STRATEGY_DIR
from growth.db.models import GrowthRepository, LearningEventModel


class StrategyEvolutionEngine:
    """
    Manages controlled, evidence-backed strategy mutation.
    Ensures absolute immutability of historical versions.
    """

    def __init__(self, repo: GrowthRepository, strat_dir: Path = STRATEGY_DIR):
        self.repo = repo
        self.strat_dir = Path(strat_dir)
        self.strat_mgr = StrategyManager(self.strat_dir)

    def evaluate_strategy_mutation(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """
        Checks if any unapplied winning experiments with N >= 4 justify proposing
        a new immutable strategy version (e.g. v1.1).
        """
        return self._evaluate_mutation_internal(channel_id)

    def evaluate_and_evolve_strategy(self, channel_id: str) -> Optional[Dict[str, Any]]:
        return self.evaluate_strategy_mutation(channel_id)

    def _evaluate_mutation_internal(self, channel_id: str) -> Optional[Dict[str, Any]]:
        current_strat = self.strat_mgr.get_active_strategy(channel_id)
        current_ver = current_strat.get("strategy_version", "v1.0")

        # Get evaluated winning experiments
        exps = self.repo.list_experiments(channel_id=channel_id, status="EVALUATED")
        winning_exps = [
            e for e in exps
            if e.get("decision") == "ACCEPT_VARIANT"
            and e.get("control_count", 0) >= 4
            and e.get("treatment_count", 0) >= 4
        ]

        if not winning_exps:
            return {
                "channel_id": channel_id,
                "current_version": current_ver,
                "action": "NO_MUTATION_WARRANTED",
                "reason": "No unapplied winning experiments with N >= 4 found."
            }

        # Calculate next version number (e.g. v1.0 -> v1.1)
        major, minor = 1, 0
        if current_ver.startswith("v") and "." in current_ver:
            parts = current_ver[1:].split(".")
            try:
                major = int(parts[0])
                minor = int(parts[1]) + 1
            except ValueError:
                minor = 1
        new_ver = f"v{major}.{minor}"

        # Build modified strategy payload
        new_strat = json.loads(json.dumps(current_strat))  # Deep copy
        new_strat["strategy_version"] = new_ver
        new_strat["parent_version"] = current_ver
        new_strat["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        affected_dimensions = []
        experiment_ids = []
        change_summaries = []

        for exp in winning_exps:
            var_tested = exp.get("variable_tested", "")
            treat_def = exp.get("variant_definition", "")
            exp_id = exp["experiment_id"]
            delta = exp.get("delta_percentage", 0.0)

            experiment_ids.append(exp_id)
            affected_dimensions.append(var_tested)

            # Apply winning pattern to strategy
            if var_tested == "HOOK_STRUCTURE":
                if "winning_patterns" not in new_strat:
                    new_strat["winning_patterns"] = {}
                hooks = new_strat["winning_patterns"].get("hooks", [])
                if treat_def not in hooks:
                    hooks.insert(0, treat_def)
                new_strat["winning_patterns"]["hooks"] = hooks
                change_summaries.append(f"Promoted hook '{treat_def}' based on {exp_id} (+{delta:.1f}% APV)")

            elif var_tested == "TOPIC_CLUSTER":
                if "winning_patterns" not in new_strat:
                    new_strat["winning_patterns"] = {}
                topics = new_strat["winning_patterns"].get("topics", [])
                if treat_def not in topics:
                    topics.insert(0, treat_def)
                new_strat["winning_patterns"]["topics"] = topics
                change_summaries.append(f"Promoted topic cluster '{treat_def}' based on {exp_id} (+{delta:.1f}% APV)")

        # Save new immutable version file (never overwrite parent)
        new_file_path = self.strat_dir / f"{channel_id}_strategy_{new_ver}.json"
        with open(new_file_path, "w", encoding="utf-8") as f:
            json.dump(new_strat, f, indent=2, ensure_ascii=False)

        # Log strategy mutation event
        mutation_evt = LearningEventModel(
            channel_id=channel_id,
            event_type="STRATEGY_MUTATION",
            summary=f"Evolved {channel_id} strategy from {current_ver} to {new_ver}.",
            details=json.dumps({
                "parent_version": current_ver,
                "new_version": new_ver,
                "supporting_experiments": experiment_ids,
                "affected_dimensions": affected_dimensions,
                "changes": change_summaries
            }),
            confidence="HIGH"
        )
        self.repo.insert_learning_event(mutation_evt)

        return {
            "channel_id": channel_id,
            "parent_version": current_ver,
            "new_version": new_ver,
            "file_path": str(new_file_path),
            "supporting_experiments": experiment_ids,
            "affected_dimensions": affected_dimensions,
            "changes": change_summaries,
            "action": "STRATEGY_VERSION_CREATED"
        }
