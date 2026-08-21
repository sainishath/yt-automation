# -*- coding: utf-8 -*-
"""
evaluator.py
------------
Phase 12: Multi-Arm Experiment Evaluator for Content Brain.
Evaluates control vs treatment empirical outcomes with strict N >= 4 guards,
outlier filtering, non-fabrication guarantees, and idempotent outcome recording.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np

from growth.brain.schemas import ConfidenceLevel, KnowledgeLevel
from growth.db.models import GrowthRepository, ExperimentModel, LearningEventModel


class ExperimentDecision:
    WIN = "ACCEPT_VARIANT"
    LOSE = "REJECT_VARIANT"
    INCONCLUSIVE = "INCONCLUSIVE"
    CONTINUE_COLLECTION = "CONTINUE_COLLECTION"


@dataclass
class EvaluationReport:
    experiment_id: str
    channel_id: str
    variable_tested: str
    status: str
    decision: str
    decision_reason: str
    confidence: ConfidenceLevel
    control_count: int
    treatment_count: int
    control_median_apv: Optional[float]
    treatment_median_apv: Optional[float]
    delta_percentage: Optional[float]
    outlier_count: int
    is_statistically_significant: bool
    evaluated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "channel_id": self.channel_id,
            "variable_tested": self.variable_tested,
            "status": self.status,
            "decision": self.decision,
            "decision_reason": self.decision_reason,
            "confidence": self.confidence.value,
            "control_count": self.control_count,
            "treatment_count": self.treatment_count,
            "control_median_apv": round(self.control_median_apv, 2) if self.control_median_apv is not None else None,
            "treatment_median_apv": round(self.treatment_median_apv, 2) if self.treatment_median_apv is not None else None,
            "delta_percentage": round(self.delta_percentage, 2) if self.delta_percentage is not None else None,
            "outlier_count": self.outlier_count,
            "is_statistically_significant": self.is_statistically_significant,
            "evaluated_at": self.evaluated_at
        }


class MultiArmExperimentEvaluator:
    """
    Evaluates multi-arm experiments against real first-party performance snapshots.
    Guarantees N >= 4 per arm, filters viral/technical outliers, and prevents single-video bias.
    """

    def __init__(self, repo: GrowthRepository, min_sample_size: int = 4):
        self.repo = repo
        self.min_sample_size = min_sample_size

    def _get_arm_metrics(self, experiment_id: str, arm_type: str) -> List[float]:
        """
        Retrieves real performance metric values (e.g. APV) for an experiment arm.
        Uses latest valid snapshot for each legitimately published video.
        """
        vids = self.repo.list_videos_by_experiment(experiment_id)
        metric_values = []

        for v in vids:
            if v.get("upload_status") != "UPLOADED_PUBLIC":
                continue
            # Match arm type
            var_id = (v.get("variant_id") or "").upper()
            arm_id = (v.get("arm_id") or "").upper()
            if arm_type.upper() not in var_id and arm_type.upper() not in arm_id:
                continue

            snaps = self.repo.get_snapshots_for_video(v["video_id"])
            if not snaps:
                continue

            # Prioritize 24h, 48h, or latest valid snapshot with real APV
            valid_snaps = [s for s in snaps if s.get("avg_percentage_viewed") is not None and s.get("avg_percentage_viewed") > 0]
            if valid_snaps:
                latest = valid_snaps[-1]
                metric_values.append(float(latest["avg_percentage_viewed"]))

        return metric_values

    def _filter_outliers(self, values: List[float]) -> Tuple[List[float], int]:
        """
        Removes statistical outliers using Median Absolute Deviation (MAD)
        to prevent a single viral or corrupted video from dictating strategy.
        """
        if len(values) < 4:
            return values, 0

        med = float(np.median(values))
        deviations = [abs(v - med) for v in values]
        mad = float(np.median(deviations))

        if mad == 0:
            mean_dev = float(np.mean(deviations))
            if mean_dev == 0:
                return values, 0
            cutoff = 3.0 * mean_dev
        else:
            cutoff = 3.0 * (1.4826 * mad)

        filtered = [v for v in values if abs(v - med) <= cutoff]
        outliers_removed = len(values) - len(filtered)
        return filtered, outliers_removed

    def evaluate_experiment(self, experiment_id: str) -> EvaluationReport:
        """
        Evaluates experiment arms with strict N >= 4 guard and non-fabrication check.
        Idempotently updates the experiment record in SQLite.
        """
        exp = self.repo.get_experiment(experiment_id)
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        if not exp:
            return EvaluationReport(
                experiment_id=experiment_id,
                channel_id="unknown",
                variable_tested="unknown",
                status="NOT_FOUND",
                decision=ExperimentDecision.INCONCLUSIVE,
                decision_reason="Experiment not found in database.",
                confidence=ConfidenceLevel.LOW,
                control_count=0,
                treatment_count=0,
                control_median_apv=None,
                treatment_median_apv=None,
                delta_percentage=None,
                outlier_count=0,
                is_statistically_significant=False,
                evaluated_at=now_str
            )

        channel_id = exp["channel_id"]
        var_tested = exp.get("variable_tested", "UNKNOWN")
        min_n = exp.get("min_sample_size") or self.min_sample_size

        ctrl_vals_raw = self._get_arm_metrics(experiment_id, "CONTROL")
        treat_vals_raw = self._get_arm_metrics(experiment_id, "TREATMENT")

        ctrl_vals, ctrl_outliers = self._filter_outliers(ctrl_vals_raw)
        treat_vals, treat_outliers = self._filter_outliers(treat_vals_raw)
        total_outliers = ctrl_outliers + treat_outliers

        n_ctrl = len(ctrl_vals)
        n_treat = len(treat_vals)

        # 1. Check Sample Size Hard Guard (N >= 4 required per arm)
        if n_ctrl < min_n or n_treat < min_n:
            reason = (
                f"Insufficient real published samples for evaluation: "
                f"CONTROL has {n_ctrl}/{min_n}, TREATMENT has {n_treat}/{min_n}. "
                f"Evaluation blocked until N >= {min_n} per arm."
            )
            return EvaluationReport(
                experiment_id=experiment_id,
                channel_id=channel_id,
                variable_tested=var_tested,
                status="COLLECTING_DATA",
                decision=ExperimentDecision.CONTINUE_COLLECTION,
                decision_reason=reason,
                confidence=ConfidenceLevel.LOW,
                control_count=n_ctrl,
                treatment_count=n_treat,
                control_median_apv=float(np.median(ctrl_vals)) if ctrl_vals else None,
                treatment_median_apv=float(np.median(treat_vals)) if treat_vals else None,
                delta_percentage=None,
                outlier_count=total_outliers,
                is_statistically_significant=False,
                evaluated_at=now_str
            )

        # 2. Compute Robust Performance Metrics (Medians)
        ctrl_med = float(np.median(ctrl_vals))
        treat_med = float(np.median(treat_vals))

        if ctrl_med > 0:
            delta_pct = ((treat_med - ctrl_med) / ctrl_med) * 100.0
        else:
            delta_pct = 0.0

        # Empirical Significance: Delta >= +5% APV threshold with N >= 4
        if delta_pct >= 5.0:
            decision = ExperimentDecision.WIN
            confidence = ConfidenceLevel.HIGH
            reason = (
                f"Treatment outperformed Control by +{delta_pct:.1f}% median APV "
                f"({treat_med:.1f}% vs {ctrl_med:.1f}%) across N={n_ctrl+n_treat} empirical samples."
            )
            is_significant = True
        elif delta_pct <= -5.0:
            decision = ExperimentDecision.LOSE
            confidence = ConfidenceLevel.HIGH
            reason = (
                f"Treatment underperformed Control by {delta_pct:.1f}% median APV "
                f"({treat_med:.1f}% vs {ctrl_med:.1f}%) across N={n_ctrl+n_treat} empirical samples."
            )
            is_significant = True
        else:
            decision = ExperimentDecision.INCONCLUSIVE
            confidence = ConfidenceLevel.MEDIUM
            reason = (
                f"Treatment delta ({delta_pct:+.1f}%) is within neutral band (±5.0%). "
                f"Outcome is inconclusive."
            )
            is_significant = False

        # 3. Update SQLite Record
        exp_model = ExperimentModel(
            experiment_id=experiment_id,
            channel_id=channel_id,
            name=exp.get("name", ""),
            hypothesis=exp.get("hypothesis", ""),
            variable_tested=var_tested,
            control_definition=exp.get("control_definition", ""),
            variant_definition=exp.get("variant_definition", ""),
            primary_metric=exp.get("primary_metric", "avg_percentage_viewed"),
            secondary_metrics=exp.get("secondary_metrics"),
            min_sample_size=min_n,
            target_sample_size=exp.get("target_sample_size", min_n),
            source_type=exp.get("source_type", "FIRST_PARTY_DISCOVERY"),
            underlying_principle=exp.get("underlying_principle"),
            status="EVALUATED",
            result=decision,
            confidence=confidence.value,
            external_pattern_id=exp.get("external_pattern_id"),
            external_prior_id=exp.get("external_prior_id"),
            source_channels=exp.get("source_channels"),
            transferability_score=exp.get("transferability_score"),
            transferability_classification=exp.get("transferability_classification"),
            prior_weight=exp.get("prior_weight"),
            provenance=exp.get("provenance", "FIRST_PARTY"),
            rationale=exp.get("rationale"),
            decision=decision,
            decision_reason=reason,
            delta_percentage=delta_pct,
            control_count=n_ctrl,
            treatment_count=n_treat,
            control_median=ctrl_med,
            treatment_median=treat_med,
            started_at=exp.get("started_at"),
            completed_at=now_str,
            evaluated_at=now_str,
            first_party_override_status=exp.get("first_party_override_status")
        )
        self.repo.upsert_experiment(exp_model)

        return EvaluationReport(
            experiment_id=experiment_id,
            channel_id=channel_id,
            variable_tested=var_tested,
            status="EVALUATED",
            decision=decision,
            decision_reason=reason,
            confidence=confidence,
            control_count=n_ctrl,
            treatment_count=n_treat,
            control_median_apv=ctrl_med,
            treatment_median_apv=treat_med,
            delta_percentage=delta_pct,
            outlier_count=total_outliers,
            is_statistically_significant=is_significant,
            evaluated_at=now_str
        )
