# -*- coding: utf-8 -*-
"""
experiment_manager.py
---------------------
Manages controlled A/B experiments across video cohorts.
Enforces minimum sample sizes and separates observation from causal conclusion.
"""

import statistics
from typing import Dict, Any, List, Optional
from growth.experiments.registry import PREDEFINED_EXPERIMENTS


class ExperimentManager:
    def __init__(self, experiments: Optional[List[Dict[str, Any]]] = None):
        self.experiments = {e["experiment_id"]: e for e in (experiments or PREDEFINED_EXPERIMENTS)}

    def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        return self.experiments.get(experiment_id)

    def evaluate_experiment(
        self,
        experiment_id: str,
        control_observations: List[float],
        variant_observations: List[float]
    ) -> Dict[str, Any]:
        """
        Evaluates experiment results.
        Requires len >= min_sample_size per arm before making conclusion.
        """
        exp = self.get_experiment(experiment_id)
        if not exp:
            raise ValueError(f"Unknown experiment: {experiment_id}")

        min_sample = exp.get("min_sample_size", 4)
        n_ctrl = len(control_observations)
        n_var = len(variant_observations)

        if n_ctrl < min_sample or n_var < min_sample:
            return {
                "experiment_id": experiment_id,
                "status": "INSUFFICIENT_DATA",
                "control_count": n_ctrl,
                "variant_count": n_var,
                "min_sample_required": min_sample,
                "verdict": "COLLECTING_MORE_SAMPLES",
                "confidence": "LOW"
            }

        median_ctrl = float(statistics.median(control_observations))
        median_var = float(statistics.median(variant_observations))
        delta_pct = round(((median_var - median_ctrl) / max(median_ctrl, 0.001)) * 100.0, 2)

        if delta_pct >= 5.0:
            verdict = "VARIANT_OUTPERFORMS_CONTROL"
            decision = "ACCEPT_VARIANT"
            confidence = "HIGH"
        elif delta_pct <= -5.0:
            verdict = "CONTROL_OUTPERFORMS_VARIANT"
            decision = "REJECT_VARIANT"
            confidence = "HIGH"
        else:
            verdict = "NO_STATISTICALLY_SIGNIFICANT_DIFFERENCE"
            decision = "INCONCLUSIVE"
            confidence = "MEDIUM"

        return {
            "experiment_id": experiment_id,
            "status": "EVALUATED",
            "control_count": n_ctrl,
            "variant_count": n_var,
            "control_median": median_ctrl,
            "variant_median": median_var,
            "delta_percentage": delta_pct,
            "verdict": verdict,
            "decision": decision,
            "confidence": confidence,
            "hypothesis": exp["hypothesis"]
        }
