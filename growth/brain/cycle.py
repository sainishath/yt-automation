# -*- coding: utf-8 -*-
"""
cycle.py
--------
Phase 23: Automated Daily Closed-Loop Brain Cycle for Content Intelligence.
Orchestrates snapshot ingestion -> sample accounting -> experiment evaluation ->
learning events -> strategy evolution -> memory update -> opportunity ranking ->
job dispatch (Gated at Discord Review, zero auto-upload authority).
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import json
from pathlib import Path

from growth.db.database import DEFAULT_DB_PATH
from growth.db.models import GrowthRepository
from growth.analytics.snapshot_scheduler import SnapshotScheduler
from growth.experiments.sample_tracker import ExperimentSampleTracker
from growth.experiments.production_adapter import ProductionJobAdapter
from growth.brain.evaluator import MultiArmExperimentEvaluator
from growth.brain.learning_engine import LearningEngine
from growth.brain.strategy_evolution import StrategyEvolutionEngine
from growth.brain.brain import ContentBrain


class DailyBrainCycle:
    """
    Automated daily strategic intelligence cycle.
    Idempotent, non-destructive, and strictly gated against unauthorized publication.
    """

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.repo = GrowthRepository(self.db_path)
        self.scheduler = SnapshotScheduler(self.repo, dry_run=False)
        self.sample_tracker = ExperimentSampleTracker(self.repo)
        self.evaluator = MultiArmExperimentEvaluator(self.repo)
        self.learning_engine = LearningEngine(self.repo, evaluator=self.evaluator)
        self.strategy_evolution = StrategyEvolutionEngine(self.repo)
        self.brain = ContentBrain(self.db_path)
        self.production_adapter = ProductionJobAdapter(self.repo)

    def run_cycle(self, channel_id: str) -> Dict[str, Any]:
        """
        Executes the 10-step closed-loop Content Intelligence cycle.
        """
        start_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # Step 1: Ingest Due YouTube Performance Snapshots (Quota-safe, no fake metrics)
        snapshot_res = self.scheduler.run_pending_snapshot_checks()

        # Step 2: Update Sample Accounting and Reconcile Uploads
        sample_counts = self.brain.memory.get_arm_sample_counts(channel_id)

        # Step 3: Evaluate Eligible Experiments (N >= 4 guard)
        learning_results = self.learning_engine.run_channel_learning_cycle(channel_id)

        # Step 4: Evaluate Strategy Mutation (Propose v1.1 if justified, never overwrite)
        strategy_mutation = self.strategy_evolution.evaluate_strategy_mutation(channel_id)

        # Step 5: Update Brain Memory & Scan Knowledge Gaps
        memory_snapshot = self.brain.memory.get_snapshot(channel_id)
        knowledge_gaps = self.brain.hyp_engine.identify_knowledge_gaps(channel_id)
        knowledge_summary = self.brain.memory.get_knowledge_summary(channel_id)

        # Step 6: Rank Content Opportunities (70/20/10 Portfolio)
        ranked_opps = self.brain.get_ranked_opportunities(channel_id, limit=5)

        # Step 7: Synthesize Next Strategic Recommendation
        decision = self.brain.recommend_next(channel_id)

        # Step 8: Prepare Production Job if active experiment needs cohort balancing
        dispatched_job = None
        if decision.decision_type.value == "RUN_EXPERIMENT" and decision.experiment_id:
            # Check if an unfulfilled job already exists for this arm to maintain idempotency
            existing_jobs = self.repo.list_jobs(channel_id=channel_id, limit=10)
            unfulfilled = [j for j in existing_jobs if j.get("arm_id") == decision.arm_id and j.get("status") in ["PLANNED", "GENERATING", "DISCORD_REVIEW_PENDING", "GENERATED"]]
            if not unfulfilled:
                job_res = self.production_adapter.create_experiment_production_job(channel_id)
                if job_res.get("status") != "NO_EXPERIMENTS_READY":
                    dispatched_job = job_res
            else:
                dispatched_job = {"status": "EXISTING_JOB_PENDING", "job_id": unfulfilled[0]["job_id"]}

        # Step 9: Assemble Cycle Report
        end_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        report = {
            "cycle_id": f"cycle_{channel_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "channel_id": channel_id,
            "started_at": start_time,
            "completed_at": end_time,
            "snapshots_collected": snapshot_res.get("collected_count", 0),
            "sample_counts": sample_counts,
            "learning_events_processed": len(learning_results),
            "strategy_status": strategy_mutation,
            "knowledge_gaps_count": len(knowledge_gaps),
            "knowledge_summary": knowledge_summary,
            "top_opportunity": ranked_opps[0] if ranked_opps else None,
            "recommendation": decision.to_dict(),
            "dispatched_production_job": dispatched_job,
            "human_approval_required": True,
            "auto_upload_enabled": False
        }

        return report
