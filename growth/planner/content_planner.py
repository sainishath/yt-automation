# -*- coding: utf-8 -*-
"""
content_planner.py
------------------
Autonomous Content Planner that decides:
- What topic to produce next
- Which strategy version to apply
- Which experiment arm to assign
- Why this decision was made
"""

from typing import Dict, Any, Optional
from growth.db.models import GrowthRepository
from growth.strategy.strategy_manager import StrategyManager
from growth.topic_engine.topic_pool import TopicPoolManager
from growth.experiments.experiment_manager import ExperimentManager


class ContentPlanner:
    def __init__(self, repo: GrowthRepository):
        self.repo = repo
        self.strat_mgr = StrategyManager()
        self.exp_mgr = ExperimentManager()

    def plan_next_video(self, channel_id: str) -> Dict[str, Any]:
        """
        Synthesizes topic intelligence, strategy version, and experiment queue
        into a concrete, explainable execution plan for the production engine.
        """
        strat = self.strat_mgr.get_active_strategy(channel_id)
        topic_mgr = TopicPoolManager(channel_id)

        # Filter published history
        published_vids = self.repo.list_videos_by_channel(channel_id)
        history_titles = [v["title"] for v in published_vids]
        topic_mgr.set_published_history(history_titles)

        ranked_topics = topic_mgr.get_ranked_candidates()
        if not ranked_topics:
            raise RuntimeError(f"No available candidate topics in topic pool for {channel_id}")

        selected_topic = ranked_topics[0]

        # Determine experiment assignment
        active_experiments = strat.get("active_experiments", [])
        assigned_exp = None
        assigned_variant = "CONTROL"
        if active_experiments:
            assigned_exp = active_experiments[0]
            # Simple alternating variant assignment based on existing video count
            assigned_variant = "VARIANT" if (len(published_vids) % 2 == 1) else "CONTROL"

        target_duration = 45.0 if channel_id == "channel_a" else 40.0

        plan = {
            "channel_id": channel_id,
            "pipeline_id": "alternate-history-shorts" if channel_id == "channel_a" else "convo-shorts",
            "topic": selected_topic["topic"],
            "category": selected_topic["category"],
            "cluster": selected_topic["cluster"],
            "target_duration_seconds": target_duration,
            "strategy_version": strat.get("strategy_version", "v1.0"),
            "experiment_id": assigned_exp,
            "experiment_variant": assigned_variant,
            "selection_reason": selected_topic.get("reason", "Top ranked topic in pool"),
            "status": "PLANNED"
        }

        return plan
