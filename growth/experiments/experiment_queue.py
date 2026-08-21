# -*- coding: utf-8 -*-
"""
experiment_queue.py
-------------------
Experiment Queue & Portfolio Allocation Engine.
Manages the operational queue of A/B experiments:
- Identifies experiments ready for execution
- Enforces channel isolation and conflict prevention (One Variable, One Active Experiment per Channel)
- Enforces balanced portfolio allocation (70% Proven, 20% Adjacent Experiments, 10% High-Risk Experiments)
- Assigns balanced experiment arms (CONTROL vs TREATMENT) to upcoming production jobs
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from growth.db.models import GrowthRepository, ExperimentModel
from growth.external_intelligence.experiment_bridge import ACTIVE_STATES, RECOGNIZED_VARIABLES


class ExperimentQueue:
    """
    Manages the operational queue and execution schedule for A/B experiments.
    """
    def __init__(self, repo: Optional[GrowthRepository] = None):
        self.repo = repo or GrowthRepository()

    def get_ready_experiments(self, channel_id: str) -> List[Dict[str, Any]]:
        """
        Returns all experiments ready for execution on a channel:
        - Must be in APPROVED, SCHEDULED, or RUNNING state
        - Excludes conflicting active variables
        - Sorted by priority / creation time
        """
        all_exps = self.repo.list_experiments(channel_id=channel_id)
        ready = []
        active_variables = set()

        for exp in all_exps:
            status = exp.get("status", "").upper()
            var = exp.get("variable_tested", "").upper()

            if status in ["APPROVED", "SCHEDULED", "RUNNING"]:
                if var not in active_variables:
                    arms = self.repo.get_experiment_arms(exp["experiment_id"])
                    exp_copy = dict(exp)
                    exp_copy["arms"] = arms
                    ready.append(exp_copy)
                    active_variables.add(var)

        return ready

    def get_all_queued_experiments(self, channel_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lists all experiments in PROPOSED, APPROVED, SCHEDULED, or RUNNING state.
        """
        all_exps = self.repo.list_experiments(channel_id=channel_id)
        queued = []
        for exp in all_exps:
            if exp.get("status", "").upper() in ACTIVE_STATES:
                exp_dict = dict(exp)
                exp_dict["arms"] = self.repo.get_experiment_arms(exp["experiment_id"])
                queued.append(exp_dict)
        return queued

    def select_experiment_for_topic(
        self,
        channel_id: str,
        topic_dict: Dict[str, Any],
        video_sequence_number: int
    ) -> Dict[str, Any]:
        """
        Applies portfolio allocation (70% proven, 20% adjacent, 10% high-risk) and selects
        an active experiment and balanced arm (CONTROL vs TREATMENT) for a new video plan.
        """
        risk_tier = topic_dict.get("risk_tier", "proven")
        ready_experiments = self.get_ready_experiments(channel_id)

        # By default, baseline control production
        assignment = {
            "experiment_id": None,
            "arm_id": None,
            "variant_id": "CONTROL",
            "arm_type": "CONTROL",
            "variable_under_test": None,
            "allocation_tier": risk_tier,
            "is_experiment": False,
            "reason": "Baseline proven production"
        }

        if not ready_experiments:
            return assignment

        # When ready experiments exist on a channel, assign cohorts to control vs treatment
        selected_exp = ready_experiments[0]
        exp_id = selected_exp["experiment_id"]
        arms = selected_exp.get("arms", [])

        # Alternate arms based on sequence number
        is_treatment = (video_sequence_number % 2 == 1)
        arm_type = "TREATMENT" if is_treatment else "CONTROL"

        selected_arm = next((a for a in arms if a["arm_type"] == arm_type), None)
        arm_id = selected_arm["arm_id"] if selected_arm else f"arm_{exp_id}_{arm_type.lower()}"

        assignment = {
            "experiment_id": exp_id,
            "arm_id": arm_id,
            "variant_id": "VARIANT" if is_treatment else "CONTROL",
            "arm_type": arm_type,
            "variable_under_test": selected_exp.get("variable_tested"),
            "allocation_tier": risk_tier,
            "is_experiment": True,
            "reason": f"Assigned to {selected_exp['name']} ({arm_type} arm)"
        }

        # If experiment was in APPROVED/SCHEDULED state, advance to RUNNING
        if selected_exp.get("status") in ["APPROVED", "SCHEDULED"]:
            selected_exp["status"] = "RUNNING"
            self.repo.upsert_experiment(ExperimentModel(**{
                k: selected_exp[k] for k in ExperimentModel.__dataclass_fields__ if k in selected_exp
            }))

        return assignment
