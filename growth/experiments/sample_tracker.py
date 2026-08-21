# -*- coding: utf-8 -*-
"""
sample_tracker.py
-----------------
Experiment Sample Accounting & Upload Registration Engine.
Enforces the fundamental First-Party Accounting Rules:
1. An experiment sample is ONLY a published first-party video on YouTube.
2. Rejected Discord submissions, QA failures, or unuploaded drafts NEVER count as samples.
3. Duplicate upload registrations are strictly IDEMPOTENT and do not double-count samples.
4. Sample counts directly track progress toward the N >= 4 milestone.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from growth.db.models import GrowthRepository, VideoModel, ExperimentModel


class ExperimentSampleTracker:
    """
    Manages sample accounting and lifecycle transitions upon video generation, review, and publication.
    """
    def __init__(self, repo: Optional[GrowthRepository] = None):
        self.repo = repo or GrowthRepository()

    def register_real_upload(
        self,
        video_id: str,
        youtube_video_id: str,
        youtube_url: Optional[str] = None,
        privacy: str = "public",
        publish_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Idempotently registers a verified YouTube upload in Growth DB.
        Increments the associated experiment arm sample count exactly once.
        """
        video_data = self.repo.get_video(video_id)
        if not video_data:
            raise ValueError(f"Video '{video_id}' not found in database.")

        pub_ts = publish_time or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        yt_url = youtube_url or f"https://youtu.be/{youtube_video_id}"

        # Idempotency check: If already registered as UPLOADED_PUBLIC, do not double-increment sample count
        is_already_uploaded = (video_data.get("upload_status") == "UPLOADED_PUBLIC" and video_data.get("youtube_video_id") == youtube_video_id)

        # Update video record
        updated_vid = VideoModel(
            video_id=video_data["video_id"],
            channel_id=video_data["channel_id"],
            pipeline_id=video_data["pipeline_id"],
            title=video_data["title"],
            duration=float(video_data.get("duration", 45.0)),
            upload_status="UPLOADED_PUBLIC",
            youtube_video_id=youtube_video_id,
            youtube_url=yt_url,
            privacy_status=privacy,
            review_status="APPROVED",
            strategy_version=video_data.get("strategy_version", "v1.0"),
            experiment_id=video_data.get("experiment_id"),
            arm_id=video_data.get("arm_id"),
            variant_id=video_data.get("variant_id", "CONTROL"),
            publish_timestamp=pub_ts
        )
        self.repo.upsert_video(updated_vid)

        arm_id = video_data.get("arm_id")
        exp_id = video_data.get("experiment_id")
        sample_count = 0

        if is_already_uploaded:
            logging.info(f"[SampleTracker] Video '{video_id}' already registered as uploaded. Preserving sample count.")
            if arm_id:
                arm = self.repo.get_experiment_arm(arm_id)
                sample_count = arm.get("sample_count", 0) if arm else 0
            return {
                "status": "ALREADY_REGISTERED",
                "video_id": video_id,
                "youtube_video_id": youtube_video_id,
                "arm_id": arm_id,
                "sample_count": sample_count
            }

        # Increment sample count for the arm
        if arm_id:
            sample_count = self.repo.increment_arm_sample_count(arm_id)

        # Update parent experiment counts and status
        if exp_id:
            exp_data = self.repo.get_experiment(exp_id)
            if exp_data:
                arms = self.repo.get_experiment_arms(exp_id)
                ctrl_arm = next((a for a in arms if a["arm_type"] == "CONTROL"), None)
                treat_arm = next((a for a in arms if a["arm_type"] == "TREATMENT"), None)

                ctrl_count = ctrl_arm["sample_count"] if ctrl_arm else 0
                treat_count = treat_arm["sample_count"] if treat_arm else 0
                min_sample = exp_data.get("min_sample_size", 4)

                exp_data["control_count"] = ctrl_count
                exp_data["treatment_count"] = treat_count

                # If both arms have collected >= min_sample, transition to COLLECTING_DATA
                if ctrl_count >= min_sample and treat_count >= min_sample:
                    if exp_data.get("status") in ["RUNNING", "SCHEDULED"]:
                        exp_data["status"] = "COLLECTING_DATA"

                self.repo.upsert_experiment(ExperimentModel(**{
                    k: exp_data[k] for k in ExperimentModel.__dataclass_fields__ if k in exp_data
                }))

        return {
            "status": "UPLOAD_REGISTERED",
            "video_id": video_id,
            "youtube_video_id": youtube_video_id,
            "youtube_url": yt_url,
            "arm_id": arm_id,
            "sample_count": sample_count
        }

    def record_operator_rejection(
        self,
        video_id: str,
        rejection_reason: str = "Rejected by human reviewer in Discord"
    ) -> Dict[str, Any]:
        """
        Records human operator rejection.
        Preserves video audit history without incrementing the arm sample count.
        """
        video_data = self.repo.get_video(video_id)
        if not video_data:
            raise ValueError(f"Video '{video_id}' not found in database.")

        updated_vid = VideoModel(
            video_id=video_data["video_id"],
            channel_id=video_data["channel_id"],
            pipeline_id=video_data["pipeline_id"],
            title=video_data["title"],
            duration=float(video_data.get("duration", 45.0)),
            upload_status="REJECTED_BY_OPERATOR",
            youtube_video_id=video_data.get("youtube_video_id"),
            youtube_url=video_data.get("youtube_url"),
            privacy_status="private",
            review_status="REJECTED",
            strategy_version=video_data.get("strategy_version", "v1.0"),
            experiment_id=video_data.get("experiment_id"),
            arm_id=video_data.get("arm_id"),
            variant_id=video_data.get("variant_id", "CONTROL")
        )
        self.repo.upsert_video(updated_vid)

        return {
            "status": "REJECTED_RECORDED",
            "video_id": video_id,
            "experiment_id": video_data.get("experiment_id"),
            "arm_id": video_data.get("arm_id"),
            "reason": rejection_reason,
            "sample_count_incremented": False
        }
