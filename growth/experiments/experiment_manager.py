import json
import logging
import statistics
from datetime import datetime
from typing import Dict, Any, List, Optional
from growth.experiments.registry import PREDEFINED_EXPERIMENTS


class ExperimentManager:
    def __init__(
        self,
        experiments: Optional[List[Dict[str, Any]]] = None,
        repo: Optional[Any] = None
    ):
        self.experiments = {e["experiment_id"]: e for e in (experiments or PREDEFINED_EXPERIMENTS)}
        self.repo = repo

    def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        if experiment_id in self.experiments:
            return self.experiments[experiment_id]
        if self.repo:
            db_exp = self.repo.get_experiment(experiment_id)
            if db_exp:
                return db_exp
        return None

    def evaluate_experiment(
        self,
        experiment_id: str,
        control_observations: List[float],
        variant_observations: List[float]
    ) -> Dict[str, Any]:
        """
        Evaluates experiment results across control and treatment observations.
        Requires N >= min_sample_size per arm before making any conclusion.
        Emits learning events and applies First-Party Evidence Dominance when repo is present.
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
                "outcome_type": "INSUFFICIENT_SAMPLE",
                "control_count": n_ctrl,
                "variant_count": n_var,
                "min_sample_required": min_sample,
                "verdict": "COLLECTING_MORE_SAMPLES",
                "decision": "INCONCLUSIVE",
                "confidence": "LOW"
            }

        median_ctrl = float(statistics.median(control_observations))
        median_var = float(statistics.median(variant_observations))
        delta_pct = round(((median_var - median_ctrl) / max(median_ctrl, 0.001)) * 100.0, 2)

        if delta_pct >= 5.0:
            verdict = "VARIANT_OUTPERFORMS_CONTROL"
            outcome_type = "TREATMENT_WIN"
            decision = "ACCEPT_VARIANT"
            exp_status = "ACCEPTED"
            confidence = "HIGH"
        elif delta_pct <= -5.0:
            verdict = "CONTROL_OUTPERFORMS_VARIANT"
            outcome_type = "CONTROL_WIN"
            decision = "REJECT_VARIANT"
            exp_status = "REJECTED"
            confidence = "HIGH"
        else:
            verdict = "NO_STATISTICALLY_SIGNIFICANT_DIFFERENCE"
            outcome_type = "NO_MEANINGFUL_DIFFERENCE"
            decision = "INCONCLUSIVE"
            exp_status = "INCONCLUSIVE"
            confidence = "MEDIUM"

        res = {
            "experiment_id": experiment_id,
            "status": "EVALUATED",
            "outcome_type": outcome_type,
            "control_count": n_ctrl,
            "variant_count": n_var,
            "control_median": median_ctrl,
            "variant_median": median_var,
            "delta_percentage": delta_pct,
            "verdict": verdict,
            "decision": decision,
            "confidence": confidence,
            "hypothesis": exp.get("hypothesis", "")
        }

        # If repo is available, persist outcome and trigger learning/dominance
        if self.repo:
            try:
                from growth.external_intelligence.experiment_bridge import ExperimentBridge
                bridge = ExperimentBridge(repo=self.repo)
                bridge_res = bridge.evaluate_and_apply_dominance(experiment_id, control_observations, variant_observations)
                res.update(bridge_res)

                # Record structured learning event
                from growth.db.database import get_db
                event_type = "FIRST_PARTY_OVERRIDE" if decision == "REJECT_VARIANT" else ("STRATEGY_PROPOSAL" if decision == "ACCEPT_VARIANT" else "EXPERIMENT_COMPLETED")
                summary = f"Experiment '{experiment_id}' evaluated: {verdict} ({delta_pct:+.1f}% delta, N={n_ctrl}+{n_var})"
                with get_db(self.repo.db_path) as conn:
                    conn.execute("""
                        INSERT INTO learning_events (channel_id, event_type, summary, details, confidence)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        exp.get("channel_id", "channel_a"),
                        event_type,
                        summary,
                        json.dumps(res),
                        confidence
                    ))
            except Exception as e:
                logging.error(f"[ExperimentManager] Failed to apply dominance/learning event: {e}")

        return res

    def evaluate_experiment_from_db(self, experiment_id: str) -> Dict[str, Any]:
        """
        Gathers real YouTube performance metrics from the database for the experiment's
        control and treatment arms, then executes evaluation.
        """
        if not self.repo:
            raise RuntimeError("Repository required to evaluate from database.")

        exp = self.repo.get_experiment(experiment_id)
        if not exp:
            raise ValueError(f"Experiment '{experiment_id}' not found in database.")

        primary_metric = exp.get("primary_metric", "avg_percentage_viewed")
        videos = self.repo.list_videos_by_experiment(experiment_id)

        ctrl_obs = []
        var_obs = []

        for v in videos:
            arm_type = "CONTROL" if v.get("variant_id") == "CONTROL" else "TREATMENT"
            if v.get("arm_id") and "treatment" in v["arm_id"]:
                arm_type = "TREATMENT"

            snaps = self.repo.get_snapshots_for_video(v["video_id"])
            if snaps:
                # Use latest snapshot for the primary metric
                latest_snap = snaps[-1]
                val = latest_snap.get(primary_metric, 0.0)
                if arm_type == "CONTROL":
                    ctrl_obs.append(float(val))
                else:
                    var_obs.append(float(val))

        return self.evaluate_experiment(experiment_id, ctrl_obs, var_obs)

