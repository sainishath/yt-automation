# -*- coding: utf-8 -*-
"""
brain.py
--------
Content Brain V1 Facade.
Unified interface for memory retrieval, opportunity discovery, hypothesis formation,
multi-factor scoring, and explainable decision generation.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any

from growth.db.database import DEFAULT_DB_PATH
from growth.brain.schemas import BrainDecision, ContentOpportunity, Hypothesis
from growth.brain.memory import BrainMemory
from growth.brain.evidence import EvidenceEvaluator
from growth.brain.opportunity_engine import OpportunityEngine
from growth.brain.hypothesis_engine import HypothesisEngine
from growth.brain.decision_engine import DecisionEngine
from growth.brain.explanation_engine import ExplanationEngine


class ContentBrain:
    """
    Unified Content Brain V1 Facade.
    Acts as a strategic decision engine without direct publishing authority.
    """

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.memory = BrainMemory(self.db_path)
        self.evaluator = EvidenceEvaluator(self.memory)
        self.opp_engine = OpportunityEngine(self.memory, self.evaluator)
        self.hyp_engine = HypothesisEngine(self.memory, self.evaluator)
        self.expl_engine = ExplanationEngine()
        self.decision_engine = DecisionEngine(
            memory=self.memory,
            evaluator=self.evaluator,
            opp_engine=self.opp_engine,
            hyp_engine=self.hyp_engine,
            expl_engine=self.expl_engine
        )

    def get_status(self, channel_id: str) -> Dict[str, Any]:
        """
        Provides a comprehensive overview of active strategy, experiments,
        portfolio allocations, and pending decisions for a channel.
        """
        snapshot = self.memory.get_snapshot(channel_id)
        decision = self.decision_engine.recommend_next_decision(channel_id)

        strat = snapshot.active_strategy
        alloc = strat.get("portfolio_allocation", {"proven": 0.70, "adjacent": 0.20, "exploratory": 0.10})

        return {
            "channel_id": channel_id,
            "strategy_version": snapshot.strategy_version,
            "published_videos_count": snapshot.published_videos_count,
            "active_experiments_count": len(snapshot.active_experiments),
            "completed_experiments_count": len(snapshot.completed_experiments),
            "active_arms_sample_counts": snapshot.first_party_samples_by_arm,
            "learning_events_count": len(snapshot.learning_events),
            "external_priors_count": len(snapshot.external_priors),
            "portfolio_allocation": alloc,
            "next_recommended_decision": {
                "decision_type": decision.decision_type.value,
                "arm_type": decision.arm_type,
                "variable_under_test": decision.variable_under_test,
                "topic": decision.opportunity.topic if decision.opportunity else None,
                "confidence": decision.confidence.value,
                "reasoning": decision.reasoning
            }
        }

    def get_memory_view(self, channel_id: str) -> Dict[str, Any]:
        """
        Returns structured view of everything the Brain currently 'knows' about a channel.
        """
        snapshot = self.memory.get_snapshot(channel_id)
        return snapshot.to_dict()

    def get_ranked_opportunities(self, channel_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Returns scored and ranked content opportunities with factor breakdown.
        """
        opps = self.opp_engine.rank_opportunities(channel_id, limit=limit)
        return [o.to_dict() for o in opps]

    def recommend_next(self, channel_id: str) -> BrainDecision:
        """
        Generates the next strategic decision.
        """
        return self.decision_engine.recommend_next_decision(channel_id)

    def next_production_decision(self, channel_id: str) -> BrainDecision:
        """
        Operational endpoint for determining the next production decision.
        Inspects active experiments, cohort balances, 70/20/10 portfolio,
        and returns a fully traceable BrainDecision.
        """
        return self.decision_engine.recommend_next_decision(channel_id)

    def explain_recommendation(self, channel_id: str) -> Dict[str, Any]:
        """
        Returns deep 10-point explanation for the current recommendation.
        """
        decision = self.recommend_next(channel_id)
        return {
            "decision_id": decision.decision_id,
            "channel_id": decision.channel_id,
            "decision_type": decision.decision_type.value,
            "arm_type": decision.arm_type,
            "variable_under_test": decision.variable_under_test,
            "confidence": decision.confidence.value,
            "reasoning": decision.reasoning,
            "explanation": decision.explanation_breakdown,
            "invariants": decision.invariants
        }

    def get_belief_state(self, channel_id: str) -> List[Dict[str, Any]]:
        """
        Returns current empirical belief states for the channel.
        """
        from growth.db.models import GrowthRepository
        from growth.brain.belief_engine import BeliefEngine
        repo = GrowthRepository(self.db_path)
        engine = BeliefEngine(repo)
        return [b.to_dict() for b in engine.get_channel_beliefs(channel_id)]

    def get_negative_knowledge(self, channel_id: str) -> Dict[str, Any]:
        """
        Returns institutional negative knowledge (DO_NOT_USE registry).
        """
        from growth.db.models import GrowthRepository
        from growth.brain.belief_engine import BeliefEngine
        repo = GrowthRepository(self.db_path)
        engine = BeliefEngine(repo)
        return engine.get_negative_knowledge(channel_id)

    def run_weekly_learning_cycle(self, channel_id: str) -> Dict[str, Any]:
        """
        Executes complete weekly learning cycle and writes WEEKLY_LEARNING_REPORT.md.
        """
        from growth.db.models import GrowthRepository
        from growth.brain.weekly_cycle import WeeklyLearningCycle
        repo = GrowthRepository(self.db_path)
        cycle = WeeklyLearningCycle(repo)
        return cycle.run_weekly_cycle(channel_id)

    def get_live_learning_status(self, channel_id: str) -> Dict[str, Any]:
        """
        Returns comprehensive real-time live trial learning status for a channel.
        """
        from growth.db.models import GrowthRepository
        from growth.brain.belief_engine import BeliefEngine, VideoMaturity
        from growth.brain.production_recommendation import ProductionRecommendationEngine
        repo = GrowthRepository(self.db_path)
        belief_engine = BeliefEngine(repo)

        strat = self.memory.get_active_strategy(channel_id)
        strat_ver = strat.get("strategy_version", "v1.0")

        vids = repo.list_videos_by_channel(channel_id)
        pub_vids = [v for v in vids if v.get("upload_status") == "UPLOADED_PUBLIC"]

        # Calculate mature videos
        mature_count = 0
        missing_metrics = 0
        total_snaps_count = 0
        latest_24h = None
        latest_48h = None

        for v in pub_vids:
            snaps = repo.list_snapshots_for_video(v["video_id"])
            total_snaps_count += len(snaps)
            for s in snaps:
                if s.get("avg_percentage_viewed") is None:
                    missing_metrics += 1
                if s.get("window_name") in ["7d", "28d"]:
                    mature_count += 1
                if s.get("window_name") == "24h" and not latest_24h:
                    latest_24h = {"video_id": v["video_id"], "views": s.get("views"), "apv": s.get("avg_percentage_viewed")}
                if s.get("window_name") == "48h" and not latest_48h:
                    latest_48h = {"video_id": v["video_id"], "views": s.get("views"), "apv": s.get("avg_percentage_viewed")}

        exps = repo.list_experiments(channel_id=channel_id)
        active_exp_info = None
        mature_exps = []
        for e in exps:
            if e.get("status") in ["RUNNING", "SCHEDULED", "COLLECTING_DATA", "APPROVED"]:
                if not active_exp_info:
                    active_exp_info = {
                        "experiment_id": e.get("experiment_id"),
                        "name": e.get("name"),
                        "variable_tested": e.get("variable_tested"),
                        "control_count": e.get("control_count", 0),
                        "treatment_count": e.get("treatment_count", 0),
                        "target_per_arm": 4,
                        "status": e.get("status"),
                        "current_arm_needed": "CONTROL" if e.get("control_count", 0) < e.get("treatment_count", 0) else "TREATMENT"
                    }
            elif e.get("status") == "EVALUATED":
                mature_exps.append(e)

        # Latest video and diagnostic
        latest_vid = pub_vids[0] if pub_vids else None
        latest_diag_dict = None
        if latest_vid:
            diag = belief_engine.generate_video_diagnostic(latest_vid["video_id"])
            if diag:
                latest_diag_dict = diag.to_dict()

        # Next decision
        decision = self.decision_engine.recommend_next_decision(channel_id)
        rec_engine = ProductionRecommendationEngine()
        rec = rec_engine.generate_recommendation(decision, save_plan_file=False)

        # Negative knowledge & beliefs
        neg_data = belief_engine.get_negative_knowledge(channel_id)
        beliefs = belief_engine.get_channel_beliefs(channel_id)
        winners = [b.name for b in beliefs if b.status.value == "PROMOTED"]
        rejected = [b.name for b in beliefs if b.status.value == "REJECTED"]

        # Channel Health & Scorecard
        from growth.brain.channel_trajectory import ChannelTrajectoryEngine
        traj_engine = ChannelTrajectoryEngine(repo)
        health_snapshot = traj_engine.compute_channel_health(channel_id, tag="CURRENT")
        scorecard = traj_engine.generate_scorecard(channel_id, current_snapshot=health_snapshot)

        data_quality = "HEALTHY" if missing_metrics == 0 else "DATA_PENDING"

        return {
            "channel_id": channel_id,
            "strategy_version": strat_ver,
            "videos_published": len(pub_vids),
            "videos_mature": mature_count,
            "channel_health": health_snapshot.to_dict(),
            "channel_scorecard": scorecard.to_dict(),
            "active_experiment": active_exp_info,
            "latest_video": {
                "video_id": latest_vid.get("video_id") if latest_vid else None,
                "title": latest_vid.get("title") if latest_vid else None,
                "youtube_video_id": latest_vid.get("youtube_video_id") if latest_vid else None,
                "arm": latest_vid.get("variant_id") if latest_vid else None,
                "diagnostic": latest_diag_dict
            } if latest_vid else None,
            "latest_24h_result": latest_24h,
            "latest_48h_result": latest_48h,
            "mature_experiments": [e.get("experiment_id") for e in mature_exps],
            "winners": winners,
            "rejected_patterns": rejected,
            "do_not_use_count": len(neg_data.get("do_not_use_patterns", [])),
            "next_video_plan": {
                "topic": rec.topic,
                "angle": rec.angle,
                "hook": rec.hook_recommendation,
                "experiment_id": decision.experiment_id,
                "arm": decision.arm_type,
                "variable_tested": decision.variable_under_test,
                "why_reason": decision.reasoning
            },
            "data_quality": {
                "status": data_quality,
                "total_snapshots": total_snaps_count,
                "missing_metrics": missing_metrics
            }
        }

    def get_channel_health(self, channel_id: str, tag: str = "CURRENT") -> Dict[str, Any]:
        """
        Returns longitudinal first-party channel health snapshot.
        """
        from growth.db.models import GrowthRepository
        from growth.brain.channel_trajectory import ChannelTrajectoryEngine
        repo = GrowthRepository(self.db_path)
        traj_engine = ChannelTrajectoryEngine(repo)
        return traj_engine.compute_channel_health(channel_id, tag=tag).to_dict()

    def get_channel_scorecard(self, channel_id: str) -> Dict[str, Any]:
        """
        Returns deterministic channel improvement scorecard (Baseline vs Current).
        """
        from growth.db.models import GrowthRepository
        from growth.brain.channel_trajectory import ChannelTrajectoryEngine
        repo = GrowthRepository(self.db_path)
        traj_engine = ChannelTrajectoryEngine(repo)
        return traj_engine.generate_scorecard(channel_id).to_dict()

    def record_channel_milestone(self, channel_id: str, tag: str) -> Dict[str, Any]:
        """
        Captures and persists a channel health milestone into SQLite.
        """
        from growth.db.models import GrowthRepository
        from growth.brain.channel_trajectory import ChannelTrajectoryEngine
        repo = GrowthRepository(self.db_path)
        traj_engine = ChannelTrajectoryEngine(repo)
        return traj_engine.capture_and_record_baseline(channel_id, tag=tag).to_dict()

    def get_learning_trace(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Returns full causal learning trace for a specific video.
        """
        from growth.db.models import GrowthRepository
        from growth.brain.learning_trace import LearningTraceEngine
        repo = GrowthRepository(self.db_path)
        trace_engine = LearningTraceEngine(repo)
        trace = trace_engine.generate_trace_for_video(video_id)
        return trace.to_dict() if trace else None

    def list_learning_traces(self, channel_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Returns recent learning traces for a channel.
        """
        from growth.db.models import GrowthRepository
        from growth.brain.learning_trace import LearningTraceEngine
        repo = GrowthRepository(self.db_path)
        trace_engine = LearningTraceEngine(repo)
        return trace_engine.list_recent_traces(channel_id, limit=limit)
