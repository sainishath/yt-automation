# -*- coding: utf-8 -*-
"""
learning_engine.py
------------------
Coordinates historical analysis, calculates winner/loser patterns,
evaluates A/B experiments, and mutates strategy versions upon proven evidence.
Records structured learning events with explicit evidence and confidence levels.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from growth.db.database import get_db
from growth.db.models import GrowthRepository
from growth.analytics.collector import AnalyticsCollector
from growth.topic_engine.topic_pool import TopicPoolManager
from growth.experiments.experiment_manager import ExperimentManager
from growth.learning.report_generator import generate_weekly_growth_report
from growth.learning.autopsy_analyzer import generate_video_autopsy
from growth.strategy.strategy_manager import StrategyManager


class LearningEngine:
    def __init__(self, repo: GrowthRepository, collector: AnalyticsCollector):
        self.repo = repo
        self.collector = collector
        self.exp_mgr = ExperimentManager()
        self.strat_mgr = StrategyManager()

    def run_channel_learning_cycle(self, channel_id: str) -> Dict[str, Any]:
        """
        Executes a complete learning cycle for a channel:
        1. Queries videos and normalized summaries.
        2. Generates video autopsies.
        3. Evaluates active experiments.
        4. Evolves strategy version if experimental evidence is proven.
        5. Re-ranks topic candidates.
        6. Produces a markdown report.
        """
        channel_data = self.repo.get_channel(channel_id)
        if not channel_data:
            raise ValueError(f"Channel not found: {channel_id}")

        videos = self.repo.list_videos_by_channel(channel_id)
        summaries = []
        autopsies = []

        for v in videos:
            s_sum = self.collector.get_video_normalized_summary(v["video_id"], channel_id)
            if s_sum:
                summaries.append(s_sum)
                feat = self.repo.get_features(v["video_id"]) or {}
                autopsies.append(generate_video_autopsy(v["video_id"], feat, s_sum))

        # Evaluate active experiments with REAL database observations
        exp_results = []
        promoted_strategy = None

        active_exps = self.repo.list_active_experiments(channel_id) if hasattr(self.repo, "list_active_experiments") else []
        if not active_exps:
            # Fallback to predefined experiment registry for this channel
            from growth.experiments.registry import PREDEFINED_EXPERIMENTS
            active_exps = [e for e in PREDEFINED_EXPERIMENTS if e.get("channel_id") == channel_id]

        for exp in active_exps:
            exp_id = exp.get("experiment_id")
            arms = exp.get("arms", [])
            ctrl_arm_id = next((a.get("arm_id") for a in arms if a.get("arm_type", "").upper() == "CONTROL"), "control")
            var_arm_id = next((a.get("arm_id") for a in arms if a.get("arm_type", "").upper() == "TREATMENT"), "treatment")

            # Query real video observations for each arm from performance snapshots
            ctrl_obs = []
            var_obs = []
            for v in videos:
                vid = v.get("video_id")
                v_arm = v.get("arm_id")
                s_sum = self.collector.get_video_normalized_summary(vid, channel_id)
                if not s_sum:
                    continue

                # Metric used: 7-day avg_percentage_viewed or normalized retention multiplier
                perf_val = s_sum.get("raw_24h", {}).get("avg_percentage_viewed") or s_sum.get("normalized", {}).get("composite_performance_score", 0.0)

                if v_arm == ctrl_arm_id or (not v_arm and vid.endswith("_ctrl")):
                    ctrl_obs.append(float(perf_val))
                elif v_arm == var_arm_id or (not v_arm and vid.endswith("_var")):
                    var_obs.append(float(perf_val))

            eval_res = self.exp_mgr.evaluate_experiment(exp_id, ctrl_obs, var_obs)
            eval_res["control_arm"] = ctrl_arm_id
            eval_res["treatment_arm"] = var_arm_id
            eval_res["metric_used"] = "7d_avg_percentage_viewed"
            exp_results.append(eval_res)

            if eval_res.get("decision") == "ACCEPT_VARIANT" and eval_res.get("confidence") == "HIGH":
                promoted_strategy = self._promote_strategy(channel_id, eval_res, [v["video_id"] for v in videos])

            # Apply First-Party Dominance to active external priors when sufficient evidence exists
            if eval_res.get("status") == "EVALUATED":
                try:
                    from growth.external_intelligence.repository import ExternalIntelligenceRepository
                    from growth.external_intelligence.prior_engine import apply_first_party_override
                    from growth.external_intelligence.schemas import ExternalPriorModel, TransferabilityClassification, PriorStatus
                    ext_repo = ExternalIntelligenceRepository(self.repo.db_path)
                    priors_raw = ext_repo.list_external_priors(channel_id)
                    for pr in priors_raw:
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
                        updated = apply_first_party_override(prior_model, eval_res)
                        ext_repo.upsert_external_prior(updated)
                except Exception:
                    pass

        topic_mgr = TopicPoolManager(channel_id)
        published_titles = [v["title"] for v in videos]
        topic_mgr.set_published_history(published_titles)
        ranked_topics = topic_mgr.get_ranked_candidates()

        report_md = generate_weekly_growth_report(
            channel_id=channel_id,
            channel_name=channel_data["name"],
            video_summaries=summaries,
            experiment_results=exp_results,
            recommended_topics=ranked_topics
        )

        # Log learning event in database
        event_details = {
            "evaluated_videos": [v["video_id"] for v in videos],
            "autopsies_count": len(autopsies),
            "experiment_results": exp_results,
            "promoted_strategy": promoted_strategy
        }

        with get_db(self.repo.db_path) as conn:
            conn.execute("""
                INSERT INTO learning_events (channel_id, event_type, summary, details, confidence)
                VALUES (?, 'WEEKLY_REPORT', ?, ?, 'HIGH')
            """, (
                channel_id,
                f"Evaluated {len(videos)} videos with {len(exp_results)} experiment conclusions",
                json.dumps(event_details)
            ))

        return {
            "channel_id": channel_id,
            "videos_count": len(videos),
            "summaries_count": len(summaries),
            "autopsies": autopsies,
            "experiment_results": exp_results,
            "promoted_strategy": promoted_strategy,
            "recommended_topics": ranked_topics,
            "report_markdown": report_md
        }

    def _promote_strategy(self, channel_id: str, experiment_result: Dict[str, Any], supporting_vids: List[str]) -> str:
        """Promotes and records a new version of the channel strategy."""
        current_strat = self.strat_mgr.get_active_strategy(channel_id)
        curr_ver = current_strat.get("strategy_version", "v1.0")
        new_ver = "v1.1" if curr_ver == "v1.0" else "v2.0"

        updated_strat = dict(current_strat)
        updated_strat["strategy_version"] = new_ver
        updated_strat["promoted_from_experiment"] = experiment_result["experiment_id"]
        updated_strat["promotion_rationale"] = f"Variant outperformed control by {experiment_result['delta_percentage']}%"

        with get_db(self.repo.db_path) as conn:
            conn.execute("""
                INSERT INTO strategy_versions (version_id, channel_id, version_number, strategy_payload, change_summary, approval_status)
                VALUES (?, ?, ?, ?, ?, 'ACTIVE')
            """, (
                f"{channel_id}_{new_ver}",
                channel_id,
                new_ver,
                json.dumps(updated_strat),
                f"Adopted variant from {experiment_result['experiment_id']}"
            ))

            # Record strategy mutation learning event
            mutation_details = {
                "experiment_id": experiment_result["experiment_id"],
                "delta_percentage": experiment_result["delta_percentage"],
                "supporting_video_ids": supporting_vids,
                "previous_strategy_version": curr_ver,
                "new_strategy_version": new_ver
            }
            conn.execute("""
                INSERT INTO learning_events (channel_id, event_type, summary, details, confidence)
                VALUES (?, 'STRATEGY_MUTATION', ?, ?, 'HIGH')
            """, (
                channel_id,
                f"Promoted {channel_id} strategy to {new_ver} based on {experiment_result['experiment_id']}",
                json.dumps(mutation_details)
            ))

        return new_ver
