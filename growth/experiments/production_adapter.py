# -*- coding: utf-8 -*-
"""
production_adapter.py
---------------------
Production Job Adapter & Metadata Carrier.
Connects the Content Planner and Experiment Queue to the actual production pipeline runners
(alternate-history-shorts and convo-shorts).
Ensures experiment metadata (experiment_id, arm_id, arm_type, variable_tested) survives
the full lifecycle:
PLAN -> JOB -> GENERATION -> QA -> DISCORD REVIEW -> UPLOAD -> ANALYTICS.
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from growth.db.models import GrowthRepository, JobModel, VideoModel
from growth.planner.content_planner import ContentPlanner
from growth.experiments.experiment_queue import ExperimentQueue


class ProductionJobAdapter:
    """
    Adapter bridging Growth Intelligence experiment plans with physical production runs.
    """
    def __init__(self, repo: Optional[GrowthRepository] = None):
        self.repo = repo or GrowthRepository()
        self.planner = ContentPlanner(self.repo)
        self.queue = ExperimentQueue(self.repo)

    def create_experiment_production_job(
        self,
        channel_id: str,
        topic_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Plans the next video for a channel, creates a tracked JobModel record in SQLite,
        and produces the exact configuration payload for the production pipeline runner.
        """
        video_plan = self.planner.plan_next_video(channel_id)
        if topic_override:
            video_plan["topic"] = topic_override

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        suffix = os.urandom(2).hex()
        job_id = f"job_{channel_id}_{ts}_{suffix}"

        # Register job in Growth DB
        job = JobModel(
            job_id=job_id,
            channel_id=channel_id,
            pipeline_id=video_plan["pipeline_id"],
            topic_text=video_plan["topic"],
            status="PLANNED",
            strategy_version=video_plan.get("strategy_version", "v1.0"),
            experiment_id=video_plan.get("experiment_id"),
            arm_id=video_plan.get("arm_id"),
            variant_id=video_plan.get("experiment_variant", "CONTROL")
        )
        self.repo.upsert_job(job)

        manifest_metadata = {
            "job_id": job_id,
            "channel_id": channel_id,
            "pipeline_id": video_plan["pipeline_id"],
            "topic": video_plan["topic"],
            "strategy_version": video_plan.get("strategy_version", "v1.0"),
            "is_experiment": video_plan.get("is_experiment", bool(video_plan.get("experiment_id"))),
            "experiment_id": video_plan.get("experiment_id"),
            "arm_id": video_plan.get("arm_id"),
            "arm_type": video_plan.get("arm_type", "CONTROL"),
            "variant_id": video_plan.get("experiment_variant", "CONTROL"),
            "variable_under_test": video_plan.get("variable_under_test"),
            "allocation_tier": video_plan.get("allocation_tier", "proven"),
            "selection_reason": video_plan.get("selection_reason", "")
        }

        return {
            "job_id": job_id,
            "video_plan": video_plan,
            "manifest_metadata": manifest_metadata
        }

    def inject_experiment_into_manifest(self, manifest_file: Path, metadata: Dict[str, Any]) -> None:
        """
        Injects experiment traceability fields into an existing or new run_manifest.json.
        """
        if manifest_file.exists():
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
            except Exception:
                manifest = {}
        else:
            manifest = {}

        manifest["experiment_tracking"] = metadata
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

    def register_generated_video(
        self,
        job_id: str,
        video_id: str,
        duration: float,
        title: str,
        output_dir: Optional[str] = None
    ) -> VideoModel:
        """
        Registers a generated video in Growth DB linked to its parent job, arm, and experiment.
        """
        job = self.repo.get_job(job_id)
        if not job:
            raise ValueError(f"Parent job '{job_id}' not found.")

        # Update job status
        self.repo.upsert_job(JobModel(
            job_id=job["job_id"],
            channel_id=job["channel_id"],
            pipeline_id=job["pipeline_id"],
            topic_text=job["topic_text"],
            status="GENERATED",
            strategy_version=job["strategy_version"],
            experiment_id=job.get("experiment_id"),
            arm_id=job.get("arm_id"),
            variant_id=job.get("variant_id")
        ))

        # Create Video record
        vid = VideoModel(
            video_id=video_id,
            channel_id=job["channel_id"],
            pipeline_id=job["pipeline_id"],
            title=title,
            duration=duration,
            upload_status="GENERATED",
            privacy_status="private",
            review_status="PENDING",
            strategy_version=job["strategy_version"],
            experiment_id=job.get("experiment_id"),
            arm_id=job.get("arm_id"),
            variant_id=job.get("variant_id", "CONTROL")
        )
        self.repo.upsert_video(vid)
        return vid
