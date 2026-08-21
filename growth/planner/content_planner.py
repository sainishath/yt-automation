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
from growth.experiments.experiment_queue import ExperimentQueue


class ContentPlanner:
    def __init__(self, repo: GrowthRepository):
        self.repo = repo
        self.strat_mgr = StrategyManager()
        self.exp_mgr = ExperimentManager(repo=repo)
        self.exp_queue = ExperimentQueue(repo=repo)

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
        vid_seq = len(published_vids) + 1

        # Use ExperimentQueue for portfolio allocation and arm assignment
        exp_assignment = self.exp_queue.select_experiment_for_topic(
            channel_id=channel_id,
            topic_dict=selected_topic,
            video_sequence_number=vid_seq
        )

        target_duration = 45.0 if channel_id == "channel_a" else 40.0

        plan = {
            "channel_id": channel_id,
            "pipeline_id": "alternate-history-shorts" if channel_id == "channel_a" else "convo-shorts",
            "topic": selected_topic["topic"],
            "category": selected_topic["category"],
            "cluster": selected_topic["cluster"],
            "target_duration_seconds": target_duration,
            "strategy_version": strat.get("strategy_version", "v1.0"),
            "experiment_id": exp_assignment.get("experiment_id"),
            "arm_id": exp_assignment.get("arm_id"),
            "experiment_variant": exp_assignment.get("variant_id", "CONTROL"),
            "variable_under_test": exp_assignment.get("variable_under_test"),
            "allocation_tier": exp_assignment.get("allocation_tier", "proven"),
            "selection_reason": selected_topic.get("reason", "Top ranked topic in pool"),
            "status": "PLANNED"
        }

        return plan

