# -*- coding: utf-8 -*-
"""
memory.py
---------
Read-oriented structured memory layer for Content Brain V1.
Aggregates first-party performance, experiments, arms, learning events,
strategy versions, external intelligence, and topic intelligence.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict

from growth.db.models import GrowthRepository
from growth.db.database import DEFAULT_DB_PATH
from growth.external_intelligence.repository import ExternalIntelligenceRepository
from growth.strategy.strategy_manager import StrategyManager
from growth.brain.schemas import BrainMemorySnapshot, KnowledgeLevel


class BrainMemory:
    """
    Structured read-only memory interface for Content Brain.
    Pulls unified context across all repository layers.
    """

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.repo = GrowthRepository(self.db_path)
        self.ext_repo = ExternalIntelligenceRepository(self.db_path)
        self.strat_mgr = StrategyManager()

    def get_published_videos(self, channel_id: str) -> List[Dict[str, Any]]:
        """Retrieves all legitimately published first-party videos for a channel."""
        all_vids = self.repo.list_videos_by_channel(channel_id)
        return [v for v in all_vids if v.get("upload_status") == "UPLOADED_PUBLIC"]

    def get_video_performance_map(self, channel_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Maps video_id to its latest available real performance snapshots.
        Never fabricates missing metrics.
        """
        videos = self.get_published_videos(channel_id)
        perf_map = {}
        for vid in videos:
            vid_id = vid["video_id"]
            snaps = self.repo.get_snapshots_for_video(vid_id)
            feats = self.repo.get_features(vid_id)
            perf_map[vid_id] = {
                "video": vid,
                "features": feats or {},
                "snapshots": {s["window_name"]: s for s in snaps},
                "latest_snapshot": snaps[-1] if snaps else None
            }
        return perf_map

    def get_experiments(self, channel_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Categorizes experiments into active (APPROVED, SCHEDULED, RUNNING, COLLECTING_DATA)
        and completed (EVALUATED, ACCEPTED, REJECTED, INCONCLUSIVE).
        """
        all_exps = self.repo.list_experiments(channel_id=channel_id)
        active = []
        completed = []

        for exp in all_exps:
            status = exp.get("status", "").upper()
            arms = self.repo.get_experiment_arms(exp["experiment_id"])
            exp_dict = dict(exp)
            exp_dict["arms"] = arms

            if status in ["APPROVED", "SCHEDULED", "RUNNING", "COLLECTING_DATA"]:
                active.append(exp_dict)
            elif status in ["EVALUATED", "ACCEPTED", "REJECTED", "INCONCLUSIVE"]:
                completed.append(exp_dict)
            elif status == "PROPOSED":
                active.append(exp_dict)

        return {"active": active, "completed": completed}

    def get_arm_sample_counts(self, channel_id: str) -> Dict[str, int]:
        """
        Returns exact first-party published sample counts for every arm in active experiments.
        """
        exps = self.get_experiments(channel_id)["active"]
        counts = {}
        for exp in exps:
            for arm in exp.get("arms", []):
                counts[arm["arm_id"]] = arm.get("sample_count", 0)
        return counts

    def get_learning_events(self, channel_id: str) -> List[Dict[str, Any]]:
        """Retrieves audit learning events recorded for this channel."""
        return self.repo.list_learning_events(channel_id=channel_id)

    def get_active_strategy(self, channel_id: str) -> Dict[str, Any]:
        """Retrieves active immutable strategy profile."""
        strat = dict(self.strat_mgr.get_active_strategy(channel_id))
        if "portfolio_allocation" not in strat:
            strat["portfolio_allocation"] = {"proven": 0.70, "adjacent": 0.20, "exploratory": 0.10}
        return strat

    def get_external_priors(self, channel_id: str) -> List[Dict[str, Any]]:
        """Retrieves active external priors."""
        return self.ext_repo.list_external_priors(target_channel_id=channel_id)

    def get_external_patterns(self, channel_id: str) -> List[Dict[str, Any]]:
        """Retrieves external patterns for channel."""
        return self.ext_repo.list_patterns(target_channel_id=channel_id)

    def get_topic_candidates(self, channel_id: str) -> List[Dict[str, Any]]:
        """Retrieves available scored topic candidates."""
        try:
            from growth.topic_engine.topic_pool import TopicPoolManager
            mgr = TopicPoolManager(channel_id)
            pub_vids = self.get_published_videos(channel_id)
            mgr.set_published_history([v.get("title", "") for v in pub_vids])
            candidates = mgr.get_ranked_candidates()
            return [
                {
                    "topic_id": f"topic_{c['topic'][:15].lower().replace(' ', '_').replace('?', '')}",
                    "channel_id": channel_id,
                    "topic_text": c["topic"],
                    "category": c["category"],
                    "cluster": c["cluster"],
                    "risk_tier": c.get("risk_tier", "proven"),
                    "score": c.get("score", 0.8),
                    "reason": c.get("reason", "")
                }
                for c in candidates
            ]
        except Exception:
            strat = self.get_active_strategy(channel_id)
            pool = strat.get("topic_pool", [])
            return [
                {
                    "topic_id": f"topic_{i:03d}",
                    "channel_id": channel_id,
                    "topic_text": t.get("topic", t.get("title", "")),
                    "category": t.get("category", "General"),
                    "cluster": t.get("cluster", "General"),
                    "risk_tier": t.get("risk", "proven"),
                    "score": 0.8
                }
                for i, t in enumerate(pool)
            ]

    def get_cluster_performance(self, channel_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Aggregates first-party performance by topic cluster.
        Distinguishes performance from confidence.
        """
        perf_map = self.get_video_performance_map(channel_id)
        cluster_data = defaultdict(lambda: {"count": 0, "views_sum": 0, "apv_sum": 0.0, "videos": []})

        for vid_id, data in perf_map.items():
            cluster = data["features"].get("topic_category") or data["video"].get("category") or "Unassigned"
            snaps = data["snapshots"]
            latest = data["latest_snapshot"]

            cluster_data[cluster]["count"] += 1
            cluster_data[cluster]["videos"].append(vid_id)
            if latest:
                cluster_data[cluster]["views_sum"] += latest.get("views", 0)
                cluster_data[cluster]["apv_sum"] += latest.get("avg_percentage_viewed", 0.0)

        result = {}
        for cluster, stats in cluster_data.items():
            n = stats["count"]
            avg_apv = (stats["apv_sum"] / n) if n > 0 else 0.0
            avg_views = (stats["views_sum"] / n) if n > 0 else 0.0
            result[cluster] = {
                "sample_count": n,
                "avg_views": round(avg_views, 1),
                "avg_percentage_viewed": round(avg_apv, 2),
                "confidence": "HIGH" if n >= 4 else ("MEDIUM" if n >= 2 else "LOW")
            }
        return result

    def get_hook_performance(self, channel_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Aggregates first-party performance by hook structure type.
        """
        perf_map = self.get_video_performance_map(channel_id)
        hook_data = defaultdict(lambda: {"count": 0, "apv_sum": 0.0, "videos": []})

        for vid_id, data in perf_map.items():
            hook_type = data["features"].get("hook_type") or "standard"
            latest = data["latest_snapshot"]

            hook_data[hook_type]["count"] += 1
            hook_data[hook_type]["videos"].append(vid_id)
            if latest:
                hook_data[hook_type]["apv_sum"] += latest.get("avg_percentage_viewed", 0.0)

        result = {}
        for hook, stats in hook_data.items():
            n = stats["count"]
            avg_apv = (stats["apv_sum"] / n) if n > 0 else 0.0
            result[hook] = {
                "sample_count": n,
                "avg_percentage_viewed": round(avg_apv, 2),
                "confidence": "HIGH" if n >= 4 else ("MEDIUM" if n >= 2 else "LOW")
            }
        return result

    def get_snapshot(self, channel_id: str) -> BrainMemorySnapshot:
        """
        Assembles a complete, immutable snapshot of the Brain's current memory for a channel.
        """
        strat = self.get_active_strategy(channel_id)
        vids = self.get_published_videos(channel_id)
        exps = self.get_experiments(channel_id)
        arm_counts = self.get_arm_sample_counts(channel_id)
        learnings = self.get_learning_events(channel_id)
        priors = self.get_external_priors(channel_id)
        cluster_perf = self.get_cluster_performance(channel_id)
        hook_perf = self.get_hook_performance(channel_id)

        return BrainMemorySnapshot(
            channel_id=channel_id,
            strategy_version=strat.get("strategy_version", "v1.0"),
            active_strategy=strat,
            published_videos_count=len(vids),
            active_experiments=exps["active"],
            completed_experiments=exps["completed"],
            first_party_samples_by_arm=arm_counts,
            learning_events=learnings,
            external_priors=priors,
            cluster_performance=cluster_perf,
            hook_performance=hook_perf
        )

    def get_knowledge_state(self, channel_id: str, variable: str, variant_value: str) -> str:
        """
        Determines the explicit knowledge state for a variable/variant:
        SUPPORTED, PROMISING, UNCERTAIN, REJECTED, CONTRADICTED, UNTESTED.
        """
        exps = self.get_experiments(channel_id)
        completed = exps["completed"]
        for exp in completed:
            if exp.get("variable_tested") == variable:
                dec = exp.get("decision")
                n_ctrl = exp.get("control_count", 0)
                n_treat = exp.get("treatment_count", 0)
                if n_ctrl >= 4 and n_treat >= 4:
                    if dec == "ACCEPT_VARIANT":
                        return "SUPPORTED"
                    elif dec == "REJECT_VARIANT":
                        return "REJECTED"

        # Check if external prior is contradicted
        priors = self.get_external_priors(channel_id)
        for p in priors:
            if p.get("status") == "REJECTED":
                return "CONTRADICTED"
            if p.get("status") == "HYPOTHESIS" and p.get("prior_weight", 0) > 0:
                return "PROMISING"

        # Check active experiments
        active = exps["active"]
        for exp in active:
            if exp.get("variable_tested") == variable:
                return "UNCERTAIN"

        return "UNTESTED"

    def get_knowledge_summary(self, channel_id: str) -> Dict[str, Any]:
        """
        Returns structured answers to the core institutional knowledge questions:
        What do we know, what failed, what succeeded, what is uncertain, what external beliefs disproven.
        """
        snapshot = self.get_snapshot(channel_id)
        exps = snapshot.completed_experiments

        supported = []
        rejected = []
        for exp in exps:
            dec = exp.get("decision")
            var = exp.get("variable_tested")
            if dec == "ACCEPT_VARIANT":
                supported.append(f"{var}: {exp.get('variant_definition')} (+{exp.get('delta_percentage', 0):.1f}%)")
            elif dec == "REJECT_VARIANT":
                rejected.append(f"{var}: {exp.get('variant_definition')} ({exp.get('delta_percentage', 0):.1f}%)")

        contradicted = [
            f"{p.get('prior_id')}: {p.get('first_party_override_reason')}"
            for p in snapshot.external_priors if p.get("status") == "REJECTED"
        ]

        active_uncertainties = [
            f"Testing {e.get('variable_tested')} in '{e.get('name')}' (Control: {e.get('control_count', 0)}, Treatment: {e.get('treatment_count', 0)})"
            for e in snapshot.active_experiments
        ]

        return {
            "channel_id": channel_id,
            "strategy_version": snapshot.strategy_version,
            "supported_patterns": supported,
            "rejected_patterns": rejected,
            "contradicted_external_beliefs": contradicted,
            "active_uncertainties": active_uncertainties,
            "total_published_videos": snapshot.published_videos_count
        }
