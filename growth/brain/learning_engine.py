# -*- coding: utf-8 -*-
"""
learning_engine.py
------------------
Phase 13: Closed-Loop Learning Engine for Content Brain.
Translates completed first-party experiment outcomes into multi-level knowledge,
emits structured learning events, and triggers FIRST_PARTY_OVERRIDE.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from growth.db.models import GrowthRepository, LearningEventModel
from growth.external_intelligence.repository import ExternalIntelligenceRepository
from growth.external_intelligence.schemas import ExternalPriorModel
from growth.brain.evaluator import MultiArmExperimentEvaluator, EvaluationReport, ExperimentDecision
from growth.brain.schemas import ConfidenceLevel, KnowledgeLevel


class LearningEngine:
    """
    Core learning loop of the Content Brain.
    Extracts multi-level lessons from empirical results and updates institutional memory.
    """

    def __init__(
        self,
        repo: GrowthRepository,
        ext_repo: Optional[ExternalIntelligenceRepository] = None,
        evaluator: Optional[MultiArmExperimentEvaluator] = None
    ):
        self.repo = repo
        self.ext_repo = ext_repo or ExternalIntelligenceRepository(repo.db_path)
        self.evaluator = evaluator or MultiArmExperimentEvaluator(repo)

    def process_experiment_outcome(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """
        Evaluates an experiment and converts the empirical outcome into structured learning events.
        Idempotently processes results and applies First-Party Dominance.
        """
        report = self.evaluator.evaluate_experiment(experiment_id)
        if report.status != "EVALUATED":
            return {
                "experiment_id": experiment_id,
                "action": "SKIPPED_INSUFFICIENT_DATA",
                "reason": report.decision_reason
            }

        exp_data = self.repo.get_experiment(experiment_id)
        if not exp_data:
            return None

        channel_id = report.channel_id
        var_tested = report.variable_tested
        delta = report.delta_percentage or 0.0
        n_total = report.control_count + report.treatment_count
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        events_generated = []

        # 1. Generate Primary Experiment Completion Learning Event
        summary_text = (
            f"Experiment '{experiment_id}' ({var_tested}) concluded with outcome '{report.decision}' "
            f"(Delta: {delta:+.1f}%, Control N={report.control_count}, Treatment N={report.treatment_count})."
        )
        payload = {
            "experiment_id": experiment_id,
            "variable_tested": var_tested,
            "decision": report.decision,
            "delta_percentage": delta,
            "control_count": report.control_count,
            "treatment_count": report.treatment_count,
            "control_median_apv": report.control_median_apv,
            "treatment_median_apv": report.treatment_median_apv,
            "is_significant": report.is_statistically_significant
        }

        exp_evt = LearningEventModel(
            channel_id=channel_id,
            event_type="EXPERIMENT_COMPLETED",
            summary=summary_text,
            details=json.dumps(payload),
            confidence=report.confidence.value
        )
        self.repo.insert_learning_event(exp_evt)
        events_generated.append("EXPERIMENT_COMPLETED")

        # 2. Check for FIRST_PARTY_OVERRIDE on External Priors
        prior_id = exp_data.get("external_prior_id")
        if report.decision == ExperimentDecision.LOSE and prior_id:
            override_evt = LearningEventModel(
                channel_id=channel_id,
                event_type="FIRST_PARTY_OVERRIDE",
                summary=(
                    f"First-party empirical evidence (N={n_total}) rejected treatment for variable '{var_tested}'. "
                    f"External prior '{prior_id}' is demoted to REJECTED."
                ),
                details=json.dumps({"prior_id": prior_id, "experiment_id": experiment_id, "delta": delta}),
                confidence="HIGH"
            )
            self.repo.insert_learning_event(override_evt)
            events_generated.append("FIRST_PARTY_OVERRIDE")

            # Update external prior status in DB
            prior_row = self.ext_repo.get_external_prior(prior_id)
            if prior_row:
                prior_row["status"] = "REJECTED"
                prior_row["prior_weight"] = 0.0
                prior_row["first_party_override_reason"] = f"Empirically rejected in experiment {experiment_id} (Delta: {delta:+.1f}%)"
                self.ext_repo.upsert_external_prior(ExternalPriorModel(**prior_row))

        # 3. Check for Strategy Proposal Generation on Clear Wins
        if report.decision == ExperimentDecision.WIN and report.is_statistically_significant:
            proposal_evt = LearningEventModel(
                channel_id=channel_id,
                event_type="STRATEGY_PROPOSAL",
                summary=(
                    f"Statistically significant win for '{var_tested}' (+{delta:.1f}% APV across N={n_total}). "
                    f"Recommending evolution of active strategy."
                ),
                details=json.dumps({
                    "experiment_id": experiment_id,
                    "variable_tested": var_tested,
                    "winning_arm_definition": exp_data.get("variant_definition"),
                    "delta_percentage": delta
                }),
                confidence="HIGH"
            )
            self.repo.insert_learning_event(proposal_evt)
            events_generated.append("STRATEGY_PROPOSAL")

        return {
            "experiment_id": experiment_id,
            "action": "LEARNING_PROCESSED",
            "decision": report.decision,
            "events_generated": events_generated,
            "confidence": report.confidence.value
        }

    def run_channel_learning_cycle(self, channel_id: str) -> List[Dict[str, Any]]:
        """
        Scans all active/pending experiments for a channel and processes any that meet evaluation criteria.
        """
        exps = self.repo.list_experiments(channel_id=channel_id)
        results = []

        for exp in exps:
            exp_id = exp["experiment_id"]
            status = exp.get("status", "").upper()
            if status in ["RUNNING", "COLLECTING_DATA", "APPROVED", "SCHEDULED"]:
                outcome = self.process_experiment_outcome(exp_id)
                if outcome:
                    results.append(outcome)

        return results
