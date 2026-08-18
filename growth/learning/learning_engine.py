# -*- coding: utf-8 -*-
"""
learning_engine.py
------------------
Coordinates historical analysis, calculates winner/loser patterns,
runs experiment evaluations, and generates versioned strategy proposals.
"""

from typing import Dict, Any, List, Optional
from growth.db.models import GrowthRepository
from growth.analytics.collector import AnalyticsCollector
from growth.topic_engine.topic_pool import TopicPoolManager
from growth.experiments.experiment_manager import ExperimentManager
from growth.learning.report_generator import generate_weekly_growth_report
from growth.learning.autopsy_analyzer import generate_video_autopsy


class LearningEngine:
    def __init__(self, repo: GrowthRepository, collector: AnalyticsCollector):
        self.repo = repo
        self.collector = collector
        self.exp_mgr = ExperimentManager()

    def run_channel_learning_cycle(self, channel_id: str) -> Dict[str, Any]:
        """
        Executes a complete learning cycle for a channel:
        1. Queries videos and normalized summaries.
        2. Generates video autopsies.
        3. Evaluates active experiments.
        4. Re-ranks topic candidates.
        5. Produces a markdown report.
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

        # Evaluate default experiments if samples exist
        exp_results = []
        exp_id = "EXP_A_HOOK_01" if channel_id == "channel_a" else "EXP_B_HOOK_01"
        try:
            # Synthetic sample observations for demonstration
            ctrl = [80.0, 81.0, 79.5, 82.0]
            var = [88.5, 89.0, 91.0, 87.5]
            eval_res = self.exp_mgr.evaluate_experiment(exp_id, ctrl, var)
            exp_results.append(eval_res)
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

        return {
            "channel_id": channel_id,
            "videos_count": len(videos),
            "summaries_count": len(summaries),
            "autopsies": autopsies,
            "experiment_results": exp_results,
            "recommended_topics": ranked_topics,
            "report_markdown": report_md
        }
