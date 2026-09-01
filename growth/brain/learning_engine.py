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

        # 3. Check for Strategy Proposal & Mutation Generation on Clear Wins (Delta >= +15%)
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

            # Evolve immutable strategy version (e.g. v1.0 -> v1.1)
            try:
                from growth.brain.strategy_evolution import StrategyEvolutionEngine
                strat_evo = StrategyEvolutionEngine(self.repo)
                evo_res = strat_evo.evaluate_strategy_mutation(channel_id)
                if evo_res and evo_res.get("action") == "STRATEGY_VERSION_CREATED":
                    events_generated.append("STRATEGY_MUTATION")
            except Exception as evo_err:
                pass

        return {
            "experiment_id": experiment_id,
            "action": "LEARNING_PROCESSED",
            "decision": report.decision,
            "events_generated": events_generated,
            "confidence": report.confidence.value
        }

    def audit_hook_retention_failures(self, channel_id: str) -> List[Dict[str, Any]]:
        """
        Scans published videos for the channel and checks for Hook Failures (APV < 65.0%).
        Logs HOOK_FAILURE learning events and flags the associated hook pattern.
        """
        videos = self.repo.list_videos_by_channel(channel_id)
        hook_failures = []

        for v in videos:
            vid_id = v["video_id"]
            snaps = self.repo.get_snapshots_for_video(vid_id)
            if not snaps:
                continue

            # Prioritize 7d or latest snapshot
            snap_map = {s.get("window_name"): s for s in snaps}
            target_snap = snap_map.get("7d") or snap_map.get("48h") or snap_map.get("24h") or snaps[-1]

            apv = float(target_snap.get("avg_percentage_viewed") or 0.0)
            if 0.0 < apv < 65.0:
                feat = self.repo.get_features(vid_id) or {}
                hook_type = feat.get("hook_type", "UNKNOWN")
                hook_text = feat.get("hook_text", "")

                failure_data = {
                    "video_id": vid_id,
                    "title": v.get("title", ""),
                    "avg_percentage_viewed": apv,
                    "hook_type": hook_type,
                    "hook_text": hook_text,
                    "window_name": target_snap.get("window_name")
                }
                hook_failures.append(failure_data)

                # Record HOOK_FAILURE event
                fail_evt = LearningEventModel(
                    channel_id=channel_id,
                    event_type="HOOK_FAILURE",
                    summary=f"Video '{vid_id}' experienced poor retention ({apv:.1f}% APV < 65.0% threshold) with hook type '{hook_type}'.",
                    details=json.dumps(failure_data),
                    confidence="HIGH"
                )
                self.repo.insert_learning_event(fail_evt)

        return hook_failures

    def run_channel_learning_cycle(self, channel_id: str) -> Dict[str, Any]:
        """
        Scans all active/pending experiments for a channel, audits hook retention failures,
        and processes any that meet evaluation criteria.
        """
        hook_failures = self.audit_hook_retention_failures(channel_id)

        exps = self.repo.list_experiments(channel_id=channel_id)
        exp_results = []

        for exp in exps:
            exp_id = exp["experiment_id"]
            status = exp.get("status", "").upper()
            if status in ["RUNNING", "COLLECTING_DATA", "APPROVED", "SCHEDULED", "PROPOSED"]:
                outcome = self.process_experiment_outcome(exp_id)
                if outcome:
                    exp_results.append(outcome)

        return {
            "channel_id": channel_id,
            "hook_failures": hook_failures,
            "hook_failures_count": len(hook_failures),
            "experiment_results": exp_results
        }
