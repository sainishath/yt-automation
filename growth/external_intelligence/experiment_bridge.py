# -*- coding: utf-8 -*-
"""
experiment_bridge.py
--------------------
Integration Bridge between External Intelligence hypotheses and First-Party A/B Experiment Management.
Enforces strict single-variable constraints, hard N>=4 sample size guards, collision-resistant
experiment versioning, conflict protection, and First-Party Evidence Dominance.
"""

import re
import json
import logging
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from growth.db.models import GrowthRepository, ExperimentModel
from growth.external_intelligence.schemas import (
    ExternalPriorModel,
    ExternalPatternModel,
    TransferabilityScoreModel,
    PriorStatus,
    TransferabilityClassification,
    PatternType,
    ProvenanceSource
)
from growth.external_intelligence.repository import ExternalIntelligenceRepository
from growth.external_intelligence.prior_engine import apply_first_party_override


class ExperimentStatus(str, Enum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    SCHEDULED = "SCHEDULED"
    RUNNING = "RUNNING"
    COLLECTING_DATA = "COLLECTING_DATA"
    EVALUATED = "EVALUATED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    INCONCLUSIVE = "INCONCLUSIVE"
    CANCELLED = "CANCELLED"
    # Legacy aliases
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


# Allowed state transitions in the experiment lifecycle
VALID_TRANSITIONS: Dict[str, List[str]] = {
    ExperimentStatus.PROPOSED.value: [ExperimentStatus.APPROVED.value, ExperimentStatus.CANCELLED.value],
    ExperimentStatus.APPROVED.value: [ExperimentStatus.SCHEDULED.value, ExperimentStatus.RUNNING.value, ExperimentStatus.CANCELLED.value],
    ExperimentStatus.SCHEDULED.value: [ExperimentStatus.RUNNING.value, ExperimentStatus.CANCELLED.value],
    ExperimentStatus.RUNNING.value: [ExperimentStatus.COLLECTING_DATA.value, ExperimentStatus.EVALUATED.value, ExperimentStatus.CANCELLED.value, ExperimentStatus.COMPLETED.value],
    ExperimentStatus.COLLECTING_DATA.value: [ExperimentStatus.EVALUATED.value, ExperimentStatus.CANCELLED.value, ExperimentStatus.COMPLETED.value],
    ExperimentStatus.EVALUATED.value: [ExperimentStatus.ACCEPTED.value, ExperimentStatus.REJECTED.value, ExperimentStatus.INCONCLUSIVE.value, ExperimentStatus.CANCELLED.value],
    ExperimentStatus.ACTIVE.value: [ExperimentStatus.EVALUATED.value, ExperimentStatus.ACCEPTED.value, ExperimentStatus.REJECTED.value, ExperimentStatus.INCONCLUSIVE.value, ExperimentStatus.CANCELLED.value, ExperimentStatus.COMPLETED.value],
    ExperimentStatus.COMPLETED.value: [],
    ExperimentStatus.ACCEPTED.value: [],
    ExperimentStatus.REJECTED.value: [],
    ExperimentStatus.INCONCLUSIVE.value: [ExperimentStatus.RUNNING.value, ExperimentStatus.COLLECTING_DATA.value, ExperimentStatus.CANCELLED.value],
    ExperimentStatus.CANCELLED.value: []
}

ACTIVE_STATES = {
    ExperimentStatus.PROPOSED.value,
    ExperimentStatus.APPROVED.value,
    ExperimentStatus.SCHEDULED.value,
    ExperimentStatus.RUNNING.value,
    ExperimentStatus.COLLECTING_DATA.value,
    ExperimentStatus.ACTIVE.value
}

TERMINAL_STATES = {
    ExperimentStatus.ACCEPTED.value,
    ExperimentStatus.REJECTED.value,
    ExperimentStatus.CANCELLED.value,
    ExperimentStatus.COMPLETED.value
}

# Standard single-variable categories
RECOGNIZED_VARIABLES = {
    "HOOK_STRUCTURE",
    "TITLE_STRUCTURE",
    "TOPIC_ANGLE",
    "SCRIPT_OPENING",
    "VISUAL_DENSITY",
    "PACING",
    "CTA_STRUCTURE",
    "DIALOGUE_STRUCTURE",
    "IMAGE_STYLE",
    "TOPIC_CLUSTER",
    "hook_opening_structure",
    "hook_emotional_tone"
}


def transition_experiment_state(current_state: str, new_state: str) -> str:
    """
    Validates that a state transition adheres to the experiment lifecycle.
    Prevents unvalidated jumps (e.g., PROPOSED -> ACCEPTED).
    """
    curr = current_state.upper()
    nxt = new_state.upper()

    if curr == nxt:
        return curr

    allowed = VALID_TRANSITIONS.get(curr, [])
    if nxt not in allowed:
        raise ValueError(
            f"Invalid experiment state transition: '{curr}' -> '{nxt}'. "
            f"Allowed transitions from '{curr}': {allowed}. "
            "Experiments require empirical first-party data collection (N >= 4) before evaluation."
        )
    return nxt


def validate_single_variable(variable_tested: str) -> str:
    """
    Enforces the single-variable constraint.
    Rejects multi-variable combinations (e.g. 'hook + title + pacing').
    """
    if not variable_tested or not variable_tested.strip():
        raise ValueError("variable_tested cannot be empty.")

    clean_var = variable_tested.strip()
    # Reject multi-variable conjunctions
    if any(sep in clean_var for sep in ["+", " & ", " and ", ",", "/"]):
        raise ValueError(
            f"Multi-variable experiments are strictly forbidden: '{clean_var}'. "
            "Every experiment must isolate and test exactly ONE variable."
        )

    return clean_var


def generate_experiment_id(
    channel_id: str,
    variable_tested: str,
    pattern_slug: str,
    instance_version: int = 1
) -> str:
    """
    Generates a deterministic, descriptive, collision-resistant experiment ID.
    Example: exp_channel_a_hook_structure_counterfactual_question_v1
    """
    clean_channel = channel_id.lower().replace("-", "_")
    clean_var = re.sub(r"[^a-zA-Z0-9_]", "", variable_tested.lower().replace("-", "_"))
    clean_slug = re.sub(r"[^a-zA-Z0-9_]", "", pattern_slug.lower().replace("-", "_"))

    # Remove duplicate prefixes
    clean_slug = clean_slug.replace(f"pat_{clean_channel}_", "").replace("pat_", "")

    return f"exp_{clean_channel}_{clean_var}_{clean_slug}_v{instance_version}"


class ExperimentBridge:
    """
    Integration layer linking External Intelligence hypotheses with First-Party A/B Experiments.
    """
    def __init__(self, repo: Optional[GrowthRepository] = None, ext_repo: Optional[ExternalIntelligenceRepository] = None):
        self.repo = repo or GrowthRepository()
        self.ext_repo = ext_repo or ExternalIntelligenceRepository(self.repo.db_path)

    def validate_experiment_contract(self, exp: ExperimentModel) -> None:
        """
        Validates the strict control/treatment single-variable experiment contract.
        """
        if not exp.experiment_id or not exp.experiment_id.strip():
            raise ValueError("Experiment contract violation: experiment_id cannot be empty.")

        if not exp.channel_id or not exp.channel_id.strip():
            raise ValueError("Experiment contract violation: channel_id cannot be empty.")

        if not exp.hypothesis or len(exp.hypothesis.strip()) < 10:
            raise ValueError("Experiment contract violation: hypothesis must be a clear, testable explanation (>= 10 chars).")

        validate_single_variable(exp.variable_tested)

        if not exp.control_definition or len(exp.control_definition.strip()) < 5:
            raise ValueError("Experiment contract violation: control_definition must explicitly define the current baseline.")

        if not exp.variant_definition or len(exp.variant_definition.strip()) < 5:
            raise ValueError("Experiment contract violation: variant_definition must explicitly define the treatment modification.")

        if not exp.primary_metric or not exp.primary_metric.strip():
            raise ValueError("Experiment contract violation: primary_metric must be specified.")

        if exp.min_sample_size < 4:
            raise ValueError(f"Experiment contract violation: min_sample_size must be >= 4 (received {exp.min_sample_size}).")

    def check_experiment_conflicts(self, channel_id: str, variable_tested: str, new_exp_id: str) -> Optional[str]:
        """
        Enforces conflict protection: One Variable, One Active Experiment per Variable per Channel.
        Returns conflicting experiment_id if an active experiment exists, else None.
        """
        clean_var = validate_single_variable(variable_tested)
        existing_experiments = self.repo.list_experiments(channel_id=channel_id)

        for exp in existing_experiments:
            if exp["experiment_id"] != new_exp_id and exp["status"] in ACTIVE_STATES:
                if exp["variable_tested"].upper() == clean_var.upper():
                    return exp["experiment_id"]
        return None

    def find_duplicate_active_experiment(self, channel_id: str, external_prior_id: str) -> Optional[str]:
        """
        Checks if an identical prior already has an active experiment on the channel.
        """
        if not external_prior_id:
            return None

        existing_experiments = self.repo.list_experiments(channel_id=channel_id)
        for exp in existing_experiments:
            if exp.get("external_prior_id") == external_prior_id and exp["status"] in ACTIVE_STATES:
                return exp["experiment_id"]
        return None

    def create_experiment_from_prior(
        self,
        prior: ExternalPriorModel,
        pattern: ExternalPatternModel,
        target_channel_id: str,
        transferability: Optional[TransferabilityScoreModel] = None,
        initial_status: str = ExperimentStatus.PROPOSED.value
    ) -> ExperimentModel:
        """
        Converts an External Prior hypothesis into a First-Party A/B ExperimentModel.
        Preserves complete external provenance without conflating it with first-party evidence.
        """
        # Determine variable tested
        var_tested = pattern.pattern_type.value if hasattr(pattern.pattern_type, "value") else str(pattern.pattern_type)
        var_tested = validate_single_variable(var_tested)

        # Determine instance version if previous versions exist
        existing_experiments = self.repo.list_experiments(channel_id=target_channel_id)
        matching_count = sum(
            1 for e in existing_experiments
            if e.get("external_prior_id") == prior.prior_id or pattern.pattern_id in e["experiment_id"]
        )
        instance_version = matching_count + 1

        exp_id = generate_experiment_id(
            channel_id=target_channel_id,
            variable_tested=var_tested,
            pattern_slug=pattern.pattern_id,
            instance_version=instance_version
        )

        # Baseline control definitions
        if target_channel_id == "channel_a":
            control_def = "Standard Chronos Shift Question Hook (e.g. 'What if Rome never fell?')"
            primary_metric = "avg_percentage_viewed"
            secondary_metrics = ["retention_at_3s", "engagement_rate", "views_24h"]
        else:
            control_def = "Standard Debate Protocol Neutral Opening"
            primary_metric = "engagement_rate"
            secondary_metrics = ["comment_rate", "avg_percentage_viewed", "views_24h"]

        variant_def = pattern.our_possible_implementation or f"Implement {pattern.name} in production pipeline"

        transfer_score = transferability.overall_transferability_score if transferability else 0.85
        transfer_class = (
            prior.transferability_classification.value
            if hasattr(prior.transferability_classification, "value")
            else str(prior.transferability_classification)
        )

        exp = ExperimentModel(
            experiment_id=exp_id,
            channel_id=target_channel_id,
            name=f"External Prior Test: {pattern.name}",
            hypothesis=prior.hypothesis,
            variable_tested=var_tested,
            control_definition=control_def,
            variant_definition=variant_def,
            primary_metric=primary_metric,
            secondary_metrics=secondary_metrics,
            min_sample_size=4,
            target_sample_size=4,
            source_type="EXTERNAL_PRIOR",
            underlying_principle=pattern.underlying_principle,
            status=initial_status,
            external_pattern_id=pattern.pattern_id,
            external_prior_id=prior.prior_id,
            source_channels=[f"analog_{target_channel_id}"],
            transferability_score=transfer_score,
            transferability_classification=transfer_class,
            prior_weight=min(prior.prior_weight, 0.25),
            provenance=ProvenanceSource.PUBLIC_YOUTUBE.value if not pattern.is_simulation else ProvenanceSource.SIMULATION.value,
            rationale=pattern.underlying_principle
        )

        self.validate_experiment_contract(exp)
        return exp

    def register_experiment(self, experiment: ExperimentModel) -> Dict[str, Any]:
        """
        Validates, checks conflicts/duplicates, and saves the experiment and its explicit arms to the Growth Database.
        """
        self.validate_experiment_contract(experiment)

        # 1. Deduplication check
        dup_id = self.find_duplicate_active_experiment(experiment.channel_id, experiment.external_prior_id or "")
        if dup_id:
            logging.info(f"[Experiment Bridge] Duplicate active experiment found for prior '{experiment.external_prior_id}': '{dup_id}'. Skipping.")
            return {
                "status": "DUPLICATE_SKIPPED",
                "experiment_id": dup_id,
                "reason": f"Active experiment '{dup_id}' is already testing prior '{experiment.external_prior_id}'."
            }

        # 2. Conflict check (one active experiment per variable per channel)
        if experiment.status in ACTIVE_STATES:
            conflicting_id = self.check_experiment_conflicts(
                experiment.channel_id,
                experiment.variable_tested,
                experiment.experiment_id
            )
            if conflicting_id:
                logging.warning(f"[Experiment Bridge] Conflict: Channel '{experiment.channel_id}' already has active experiment '{conflicting_id}' testing variable '{experiment.variable_tested}'.")
                return {
                    "status": "CONFLICT_BLOCKED",
                    "experiment_id": experiment.experiment_id,
                    "conflicting_experiment_id": conflicting_id,
                    "reason": f"Active experiment '{conflicting_id}' is already manipulating variable '{experiment.variable_tested}' on {experiment.channel_id}."
                }

        self.repo.upsert_experiment(experiment)

        # 3. Create and register explicit experiment arms
        from growth.db.models import ExperimentArmModel
        arm_control = ExperimentArmModel(
            arm_id=f"arm_{experiment.experiment_id}_control",
            experiment_id=experiment.experiment_id,
            arm_type="CONTROL",
            name=f"{experiment.name} (Control)",
            definition=experiment.control_definition,
            sample_count=experiment.control_count,
            status="ACTIVE"
        )
        arm_treatment = ExperimentArmModel(
            arm_id=f"arm_{experiment.experiment_id}_treatment",
            experiment_id=experiment.experiment_id,
            arm_type="TREATMENT",
            name=f"{experiment.name} (Treatment)",
            definition=experiment.variant_definition,
            sample_count=experiment.treatment_count,
            status="ACTIVE"
        )
        self.repo.upsert_experiment_arm(arm_control)
        self.repo.upsert_experiment_arm(arm_treatment)

        logging.info(f"[Experiment Bridge] Successfully registered experiment '{experiment.experiment_id}' and arms in state '{experiment.status}'.")

        return {
            "status": "REGISTERED",
            "experiment_id": experiment.experiment_id,
            "channel_id": experiment.channel_id,
            "variable_tested": experiment.variable_tested,
            "control_arm_id": arm_control.arm_id,
            "treatment_arm_id": arm_treatment.arm_id,
            "state": experiment.status
        }

    def batch_bridge_priors(self, channel_id: str, auto_approve: bool = False) -> Dict[str, Any]:
        """
        Scans all active external priors for a channel and bridges them into registered First-Party Experiments.
        """
        priors_raw = self.ext_repo.list_external_priors(channel_id)
        patterns_raw = {p["pattern_id"]: p for p in self.ext_repo.list_patterns(channel_id)}

        results = {
            "channel_id": channel_id,
            "total_priors_found": len(priors_raw),
            "registered": [],
            "skipped_duplicates": [],
            "blocked_conflicts": [],
            "errors": []
        }

        for pr in priors_raw:
            prior_id = pr["prior_id"]
            pat_id = pr["pattern_id"]
            pattern_data = patterns_raw.get(pat_id)

            if not pattern_data:
                continue

            prior_model = ExternalPriorModel(
                prior_id=pr["prior_id"],
                target_channel_id=pr["target_channel_id"],
                pattern_id=pr["pattern_id"],
                hypothesis=pr["hypothesis"],
                transferability_classification=TransferabilityClassification(pr["transferability_classification"]),
                prior_weight=pr["prior_weight"],
                status=PriorStatus(pr["status"])
            )

            pattern_model = ExternalPatternModel(
                pattern_id=pattern_data["pattern_id"],
                target_channel_id=pattern_data["target_channel_id"],
                pattern_type=PatternType(pattern_data["pattern_type"]),
                name=pattern_data["name"],
                description=pattern_data["description"],
                surface_technique=pattern_data["surface_technique"],
                underlying_principle=pattern_data["underlying_principle"],
                our_possible_implementation=pattern_data["our_possible_implementation"],
                channel_count=pattern_data["channel_count"],
                video_count=pattern_data["video_count"],
                confidence=pattern_data["confidence"],
                is_simulation=bool(pattern_data["is_simulation"])
            )

            try:
                initial_status = ExperimentStatus.APPROVED.value if auto_approve else ExperimentStatus.PROPOSED.value
                exp_model = self.create_experiment_from_prior(
                    prior=prior_model,
                    pattern=pattern_model,
                    target_channel_id=channel_id,
                    initial_status=initial_status
                )
                res = self.register_experiment(exp_model)

                if res["status"] == "REGISTERED":
                    results["registered"].append(res)
                elif res["status"] == "DUPLICATE_SKIPPED":
                    results["skipped_duplicates"].append(res)
                elif res["status"] == "CONFLICT_BLOCKED":
                    results["blocked_conflicts"].append(res)
            except Exception as e:
                results["errors"].append({"prior_id": prior_id, "error": str(e)})

        return results

    def evaluate_and_apply_dominance(
        self,
        experiment_id: str,
        control_observations: List[float],
        variant_observations: List[float]
    ) -> Dict[str, Any]:
        """
        Evaluates first-party experiment results and applies First-Party Evidence Dominance:
        - If N >= 4 and negative result: Demotes linked external prior to REJECTED and sets weight = 0.0.
        - If N >= 4 and positive result: Promotes linked external prior to SUPPORTED.
        - If N < 4: Inconclusive / insufficient data. Prior remains unmutated.
        """
        import statistics

        exp_data = self.repo.get_experiment(experiment_id)
        if not exp_data:
            raise ValueError(f"Experiment '{experiment_id}' not found in database.")

        min_sample = exp_data.get("min_sample_size", 4)
        n_ctrl = len(control_observations)
        n_var = len(variant_observations)

        if n_ctrl < min_sample or n_var < min_sample:
            # Insufficient samples: Hard guard prevents premature conclusion
            eval_result = {
                "experiment_id": experiment_id,
                "status": "INSUFFICIENT_DATA",
                "control_count": n_ctrl,
                "variant_count": n_var,
                "min_sample_required": min_sample,
                "decision": "INCONCLUSIVE",
                "verdict": "COLLECTING_MORE_SAMPLES",
                "confidence": "LOW"
            }
            return eval_result

        median_ctrl = float(statistics.median(control_observations))
        median_var = float(statistics.median(variant_observations))
        delta_pct = round(((median_var - median_ctrl) / max(median_ctrl, 0.001)) * 100.0, 2)

        if delta_pct >= 5.0:
            verdict = "VARIANT_OUTPERFORMS_CONTROL"
            decision = "ACCEPT_VARIANT"
            exp_status = ExperimentStatus.ACCEPTED.value
            confidence = "HIGH"
        elif delta_pct <= -5.0:
            verdict = "CONTROL_OUTPERFORMS_VARIANT"
            decision = "REJECT_VARIANT"
            exp_status = ExperimentStatus.REJECTED.value
            confidence = "HIGH"
        else:
            verdict = "NO_STATISTICALLY_SIGNIFICANT_DIFFERENCE"
            decision = "INCONCLUSIVE"
            exp_status = ExperimentStatus.INCONCLUSIVE.value
            confidence = "MEDIUM"

        eval_result = {
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
            "hypothesis": exp_data["hypothesis"]
        }

        # Update experiment in database
        exp_model = ExperimentModel(
            experiment_id=exp_data["experiment_id"],
            channel_id=exp_data["channel_id"],
            name=exp_data["name"],
            hypothesis=exp_data["hypothesis"],
            variable_tested=exp_data["variable_tested"],
            control_definition=exp_data["control_definition"],
            variant_definition=exp_data["variant_definition"],
            primary_metric=exp_data["primary_metric"],
            secondary_metrics=exp_data.get("secondary_metrics"),
            min_sample_size=min_sample,
            status=exp_status,
            result=json.dumps(eval_result),
            confidence=confidence,
            external_pattern_id=exp_data.get("external_pattern_id"),
            external_prior_id=exp_data.get("external_prior_id"),
            source_channels=exp_data.get("source_channels"),
            transferability_score=exp_data.get("transferability_score"),
            transferability_classification=exp_data.get("transferability_classification"),
            prior_weight=exp_data.get("prior_weight"),
            provenance=exp_data.get("provenance", "FIRST_PARTY"),
            rationale=exp_data.get("rationale"),
            decision=decision,
            delta_percentage=delta_pct,
            control_count=n_ctrl,
            treatment_count=n_var,
            control_median=median_ctrl,
            treatment_median=median_var,
            evaluated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        )
        self.repo.upsert_experiment(exp_model)

        # Apply First-Party Dominance to linked External Prior
        ext_prior_id = exp_data.get("external_prior_id")
        if ext_prior_id:
            try:
                priors_list = self.ext_repo.list_external_priors(exp_data["channel_id"])
                for pr in priors_list:
                    if pr["prior_id"] == ext_prior_id:
                        prior_model = ExternalPriorModel(
                            prior_id=pr["prior_id"],
                            target_channel_id=pr["target_channel_id"],
                            pattern_id=pr["pattern_id"],
                            hypothesis=pr["hypothesis"],
                            transferability_classification=TransferabilityClassification(pr["transferability_classification"]),
                            prior_weight=pr["prior_weight"],
                            status=PriorStatus(pr["status"]),
                            review_by=pr.get("review_by")
                        )
                        updated_prior = apply_first_party_override(prior_model, eval_result)
                        self.ext_repo.upsert_external_prior(updated_prior)
                        eval_result["linked_prior_override"] = {
                            "prior_id": ext_prior_id,
                            "prior_status": updated_prior.status.value,
                            "prior_weight": updated_prior.prior_weight,
                            "override_reason": updated_prior.first_party_override_reason
                        }
                        break
            except Exception as e:
                logging.error(f"[Experiment Bridge] Failed to update linked prior '{ext_prior_id}': {e}")

        return eval_result
