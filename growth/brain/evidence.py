# -*- coding: utf-8 -*-
"""
evidence.py
-----------
Hierarchical evidence evaluation and First-Party Dominance enforcement for Brain V1.

Hierarchy:
1. First-Party Experiment Outcomes (N >= 4, controlled single-variable)
2. First-Party Performance Snapshots (real YouTube metrics)
3. First-Party Recurring Patterns
4. External Intelligence (Priors and Analog Channel Observations)
5. Heuristic / LLM Reasoning
"""

from typing import List, Dict, Tuple, Optional, Any
from growth.brain.schemas import (
    EvidenceSource,
    ConfidenceLevel,
    EvidenceItem,
    KnowledgeLevel
)
from growth.brain.memory import BrainMemory
from growth.db.models import LearningEventModel


class EvidenceEvaluator:
    """
    Evaluates evidence strength, assigns calibrated confidence levels,
    and enforces First-Party Dominance over external intelligence.
    """

    def __init__(self, memory: BrainMemory):
        self.memory = memory

    def evaluate_hypothesis_evidence(
        self,
        channel_id: str,
        variable: str,
        variant_value: str,
        topic_cluster: Optional[str] = None
    ) -> Tuple[List[EvidenceItem], ConfidenceLevel]:
        """
        Gathers all available evidence supporting or refuting a variant across hierarchy levels.
        Returns sorted evidence items (highest hierarchy first) and overall calibrated confidence.
        """
        evidence_items: List[EvidenceItem] = []

        # 1. First-Party Completed Experiments
        exps = self.memory.get_experiments(channel_id)["completed"]
        for exp in exps:
            if exp.get("variable_tested") == variable:
                decision = exp.get("decision", "INCONCLUSIVE")
                delta = exp.get("delta_percentage", 0.0)
                n_ctrl = exp.get("control_count", 0)
                n_treat = exp.get("treatment_count", 0)
                total_n = n_ctrl + n_treat

                conf = ConfidenceLevel.HIGH if (n_ctrl >= 4 and n_treat >= 4) else ConfidenceLevel.LOW
                desc = f"First-Party Experiment '{exp['experiment_id']}' outcome: {decision} (Delta: {delta:+.1f}%, Samples: {total_n})"
                evidence_items.append(EvidenceItem(
                    source=EvidenceSource.FIRST_PARTY_EXPERIMENT,
                    metric_name="delta_percentage",
                    metric_value=delta,
                    sample_size=total_n,
                    description=desc,
                    provenance=f"experiment:{exp['experiment_id']}",
                    confidence=conf
                ))

        # 2. First-Party Published Video Snapshots
        vids = self.memory.get_published_videos(channel_id)
        if variable == "HOOK_STRUCTURE":
            hook_stats = self.memory.get_hook_performance(channel_id).get(variant_value)
            if hook_stats and hook_stats["sample_count"] > 0:
                n = hook_stats["sample_count"]
                apv = hook_stats["avg_percentage_viewed"]
                conf = ConfidenceLevel.HIGH if n >= 4 else (ConfidenceLevel.MEDIUM if n >= 2 else ConfidenceLevel.LOW)
                evidence_items.append(EvidenceItem(
                    source=EvidenceSource.FIRST_PARTY_SNAPSHOT,
                    metric_name="avg_percentage_viewed",
                    metric_value=apv,
                    sample_size=n,
                    description=f"First-Party published videos with hook '{variant_value}': {apv:.1f}% APV across {n} videos",
                    provenance="first_party_videos",
                    confidence=conf
                ))

        if topic_cluster:
            cluster_stats = self.memory.get_cluster_performance(channel_id).get(topic_cluster)
            if cluster_stats and cluster_stats["sample_count"] > 0:
                n = cluster_stats["sample_count"]
                views = cluster_stats["avg_views"]
                conf = ConfidenceLevel.HIGH if n >= 4 else (ConfidenceLevel.MEDIUM if n >= 2 else ConfidenceLevel.LOW)
                evidence_items.append(EvidenceItem(
                    source=EvidenceSource.FIRST_PARTY_SNAPSHOT,
                    metric_name="avg_views",
                    metric_value=views,
                    sample_size=n,
                    description=f"First-Party cluster '{topic_cluster}' performance: {views:.0f} avg views across {n} videos",
                    provenance=f"cluster:{topic_cluster}",
                    confidence=conf
                ))

        # 3. External Intelligence (Priors & Patterns)
        priors = self.memory.get_external_priors(channel_id)
        for prior in priors:
            pat_id = prior.get("pattern_id", "")
            if variable.lower() in prior.get("hypothesis", "").lower() or variable.lower() in pat_id.lower():
                status = prior.get("status", "HYPOTHESIS")
                weight = prior.get("prior_weight", 0.0)
                trans = prior.get("transferability_classification", "MEDIUM")
                desc = f"External Prior '{prior['prior_id']}': {prior['hypothesis']} (Weight: {weight:.2f}, Transferability: {trans}, Status: {status})"
                evidence_items.append(EvidenceItem(
                    source=EvidenceSource.EXTERNAL_PRIOR,
                    metric_name="prior_weight",
                    metric_value=weight,
                    sample_size=prior.get("sample_size", 1),
                    description=desc,
                    provenance=f"external_prior:{prior['prior_id']}",
                    confidence=ConfidenceLevel.LOW  # External is always hypothesis only
                ))

        # Determine overall calibrated confidence
        has_high_fp_exp = any(e.source == EvidenceSource.FIRST_PARTY_EXPERIMENT and e.confidence == ConfidenceLevel.HIGH for e in evidence_items)
        has_fp_snapshots = any(e.source == EvidenceSource.FIRST_PARTY_SNAPSHOT and e.sample_size >= 4 for e in evidence_items)

        if has_high_fp_exp or has_fp_snapshots:
            overall_confidence = ConfidenceLevel.HIGH
        elif any(e.source in [EvidenceSource.FIRST_PARTY_SNAPSHOT, EvidenceSource.FIRST_PARTY_PATTERN] and e.sample_size >= 2 for e in evidence_items):
            overall_confidence = ConfidenceLevel.MEDIUM
        else:
            overall_confidence = ConfidenceLevel.LOW

        return evidence_items, overall_confidence

    def check_first_party_override(self, channel_id: str, experiment_id: str) -> Optional[Dict[str, Any]]:
        """
        Enforces First-Party Dominance: If a completed experiment rejects an external prior's hypothesis
        with N >= 4, demotes the prior and records FIRST_PARTY_OVERRIDE.
        """
        exp_data = self.memory.repo.get_experiment(experiment_id)
        if not exp_data:
            return None

        status = exp_data.get("status", "").upper()
        decision = exp_data.get("decision", "").upper()
        ctrl_n = exp_data.get("control_count", 0)
        treat_n = exp_data.get("treatment_count", 0)
        prior_id = exp_data.get("external_prior_id")

        if decision == "REJECT_VARIANT" and ctrl_n >= 4 and treat_n >= 4 and prior_id:
            override_event = LearningEventModel(
                channel_id=channel_id,
                event_type="FIRST_PARTY_OVERRIDE",
                summary=f"First-party experiment '{experiment_id}' rejected variant (N={ctrl_n+treat_n}). External prior '{prior_id}' demoted.",
                details=f'{{"experiment_id": "{experiment_id}", "prior_id": "{prior_id}", "control_count": {ctrl_n}, "treatment_count": {treat_n}}}',
                confidence="HIGH"
            )
            self.memory.repo.insert_learning_event(override_event)

            # Update prior status in external repo
            prior_row = self.memory.ext_repo.get_external_prior(prior_id)
            if prior_row:
                prior_row["status"] = "REJECTED"
                prior_row["prior_weight"] = 0.0
                prior_row["first_party_override_reason"] = f"Rejected in first-party experiment {experiment_id}"
                from growth.external_intelligence.schemas import ExternalPriorModel
                self.memory.ext_repo.upsert_external_prior(ExternalPriorModel(**prior_row))

            return {
                "action": "FIRST_PARTY_OVERRIDE_APPLIED",
                "experiment_id": experiment_id,
                "prior_id": prior_id,
                "confidence": "HIGH"
            }

        return None
