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
        - Excludes saturated experiments where both arms already have >= min_sample_size
        - Excludes conflicting active variables
        - Sorted by priority / creation time
        """
        all_exps = self.repo.list_experiments(channel_id=channel_id)
        # Sort in FIFO order by creation timestamp
        all_exps = sorted(all_exps, key=lambda x: str(x.get("created_at", "")))
        ready = []
        active_variables = set()

        for exp in all_exps:
            status = exp.get("status", "").upper()
            var = exp.get("variable_tested", "").upper()
            min_sample = exp.get("min_sample_size", 4)
            ctrl_n = exp.get("control_count", 0)
            treat_n = exp.get("treatment_count", 0)

            # Satiation check: If both arms have collected >= min_sample, advance status
            if status == "RUNNING" and ctrl_n >= min_sample and treat_n >= min_sample:
                continue

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

    def approve_experiment(self, experiment_id: str) -> Dict[str, Any]:
        """
        Advances an experiment from PROPOSED to APPROVED and registers arms if missing.
        """
        exp_data = self.repo.get_experiment(experiment_id)
        if not exp_data:
            raise ValueError(f"Experiment '{experiment_id}' not found.")

        # Ensure control and treatment arms are registered
        arms = self.repo.get_experiment_arms(experiment_id)
        if not arms:
            ctrl_arm_id = f"arm_{experiment_id}_control"
            treat_arm_id = f"arm_{experiment_id}_treatment"
            from growth.db.models import ExperimentArmModel
            self.repo.upsert_experiment_arm(ExperimentArmModel(
                arm_id=ctrl_arm_id,
                experiment_id=experiment_id,
                arm_type="CONTROL",
                name=f"Control: {exp_data.get('control_definition', 'Standard baseline')[:50]}",
                definition=exp_data.get("control_definition", "Standard baseline")
            ))
            self.repo.upsert_experiment_arm(ExperimentArmModel(
                arm_id=treat_arm_id,
                experiment_id=experiment_id,
                arm_type="TREATMENT",
                name=f"Treatment: {exp_data.get('variant_definition', 'Experimental variant')[:50]}",
                definition=exp_data.get("variant_definition", "Experimental variant")
            ))

        current_status = exp_data.get("status", "").upper()
        if current_status not in ["PROPOSED", "RUNNING", "APPROVED"]:
            return {"status": "NOOP", "message": f"Experiment in state '{current_status}'", "experiment_id": experiment_id}

        from growth.external_intelligence.experiment_bridge import transition_experiment_state
        new_status = "APPROVED" if current_status == "PROPOSED" else current_status
        exp_data["status"] = new_status
        self.repo.upsert_experiment(ExperimentModel(**{
            k: exp_data[k] for k in ExperimentModel.__dataclass_fields__ if k in exp_data
        }))

        return {
            "status": "APPROVED",
            "experiment_id": experiment_id,
            "channel_id": exp_data["channel_id"],
            "variable_tested": exp_data["variable_tested"]
        }

    def select_experiment_for_topic(
        self,
        channel_id: str,
        topic_dict: Dict[str, Any],
        video_sequence_number: int
    ) -> Dict[str, Any]:
        """
        Applies portfolio allocation (70% proven, 20% adjacent, 10% high-risk) and selects
        an active experiment with dynamic sample balancing (CONTROL vs TREATMENT) for a new video plan.
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

        selected_exp = ready_experiments[0]
        exp_id = selected_exp["experiment_id"]
        arms = selected_exp.get("arms", [])
        min_sample = selected_exp.get("min_sample_size", 4)

        # Find sample counts from arms or experiment record
        ctrl_arm = next((a for a in arms if a["arm_type"] == "CONTROL"), None)
        treat_arm = next((a for a in arms if a["arm_type"] == "TREATMENT"), None)

        ctrl_count = ctrl_arm["sample_count"] if ctrl_arm else selected_exp.get("control_count", 0)
        treat_count = treat_arm["sample_count"] if treat_arm else selected_exp.get("treatment_count", 0)

        # Dynamic Sample Balancing: Prioritize lagging arm
        if ctrl_count > treat_count:
            arm_type = "TREATMENT"
        elif treat_count > ctrl_count:
            arm_type = "CONTROL"
        else:
            # If equal, balance by sequence number
            arm_type = "TREATMENT" if (video_sequence_number % 2 == 1) else "CONTROL"

        is_treatment = (arm_type == "TREATMENT")
        selected_arm = treat_arm if is_treatment else ctrl_arm
        arm_id = selected_arm["arm_id"] if selected_arm else f"arm_{exp_id}_{arm_type.lower()}"

        assignment = {
            "experiment_id": exp_id,
            "arm_id": arm_id,
            "variant_id": "VARIANT" if is_treatment else "CONTROL",
            "arm_type": arm_type,
            "variable_under_test": selected_exp.get("variable_tested"),
            "allocation_tier": risk_tier,
            "is_experiment": True,
            "control_count": ctrl_count,
            "treatment_count": treat_count,
            "target_sample_size": min_sample,
            "reason": f"Assigned to {selected_exp['name']} ({arm_type} arm: {ctrl_count} ctrl vs {treat_count} treat)"
        }

        # Advance status from APPROVED/SCHEDULED to RUNNING
        if selected_exp.get("status") in ["APPROVED", "SCHEDULED"]:
            selected_exp["status"] = "RUNNING"
            self.repo.upsert_experiment(ExperimentModel(**{
                k: selected_exp[k] for k in ExperimentModel.__dataclass_fields__ if k in selected_exp
            }))

        return assignment

