# -*- coding: utf-8 -*-
"""
lineage_tracker.py
------------------
Closed-Loop Lineage Tracking Engine.
Traces and audits the complete lineage of an experiment from external observation
through production jobs, YouTube video upload, analytics snapshots, outcome evaluation,
learning events, and strategy versioning.
"""

from typing import Dict, Any, List, Optional
from growth.db.models import GrowthRepository
from growth.db.database import get_db


class ExperimentLineageTracker:
    """
    Traces and audits the complete lifecycle and lineage of experiments.
    """
    def __init__(self, repo: Optional[GrowthRepository] = None):
        self.repo = repo or GrowthRepository()

    def trace_experiment(self, experiment_id: str) -> Dict[str, Any]:
        """
        Builds the complete end-to-end lineage trace for an experiment.
        Flags incomplete links explicitly.
        """
        with get_db(self.repo.db_path) as conn:
            exp = self.repo.get_experiment(experiment_id)
            if not exp:
                return {
                    "experiment_id": experiment_id,
                    "status": "NOT_FOUND",
                    "is_complete": False,
                    "trace": None,
                    "missing_links": ["experiment_not_found"]
                }

            channel_id = exp["channel_id"]
            min_sample = exp.get("min_sample_size", 4)

            # 1. External Prior & Pattern
            prior = None
            if exp.get("external_prior_id"):
                p_row = conn.execute("SELECT * FROM external_priors WHERE prior_id = ?", (exp["external_prior_id"],)).fetchone()
                if p_row:
                    prior = dict(p_row)

            pattern = None
            if exp.get("external_pattern_id"):
                pat_row = conn.execute("SELECT * FROM external_patterns WHERE pattern_id = ?", (exp["external_pattern_id"],)).fetchone()
                if pat_row:
                    pattern = dict(pat_row)

            # 2. Experiment Arms
            arms = self.repo.get_experiment_arms(experiment_id)

            # 3. Production Jobs
            job_rows = conn.execute("SELECT * FROM jobs WHERE experiment_id = ? ORDER BY created_at ASC", (experiment_id,)).fetchall()
            jobs = [dict(j) for j in job_rows]

            # 4. Generated & Published Videos
            vid_rows = conn.execute("SELECT * FROM videos WHERE experiment_id = ? ORDER BY publish_timestamp ASC", (experiment_id,)).fetchall()
            videos = [dict(v) for v in vid_rows]

            # 5. Performance Snapshots
            vid_ids = [v["video_id"] for v in videos]
            snapshots = []
            if vid_ids:
                placeholders = ",".join("?" * len(vid_ids))
                snap_rows = conn.execute(f"SELECT * FROM performance_snapshots WHERE video_id IN ({placeholders}) ORDER BY snapshot_id ASC", tuple(vid_ids)).fetchall()
                snapshots = [dict(s) for s in snap_rows]

            # 6. Learning Events
            learning_rows = conn.execute("SELECT * FROM learning_events WHERE details LIKE ? ORDER BY created_at DESC", (f"%{experiment_id}%",)).fetchall()
            learnings = [dict(l) for l in learning_rows]

            # 7. Active Strategy Version
            strat_row = conn.execute("SELECT * FROM strategy_versions WHERE channel_id = ? AND approval_status = 'ACTIVE' ORDER BY created_at DESC LIMIT 1", (channel_id,)).fetchone()
            strategy_version = dict(strat_row) if strat_row else None

            # Determine missing links
            missing_links = []
            if exp.get("source_type") == "EXTERNAL_PRIOR" and not prior:
                missing_links.append("external_prior_unlinked")
            if not arms:
                missing_links.append("experiment_arms_unregistered")
            if not jobs:
                missing_links.append("production_jobs_unstarted")
            if not videos:
                missing_links.append("videos_unpublished")
            elif len(videos) < min_sample * 2:
                missing_links.append(f"insufficient_samples_({len(videos)}/{min_sample * 2}_needed)")
            if not snapshots:
                missing_links.append("performance_snapshots_pending")
            if exp.get("status") not in ["ACCEPTED", "REJECTED", "INCONCLUSIVE"]:
                missing_links.append("outcome_unevaluated")
            if not learnings:
                missing_links.append("learning_event_unrecorded")

            is_complete = (len(missing_links) == 0)

            return {
                "experiment_id": experiment_id,
                "channel_id": channel_id,
                "name": exp["name"],
                "variable_tested": exp["variable_tested"],
                "status": exp["status"],
                "is_complete": is_complete,
                "missing_links": missing_links,
                "lineage": {
                    "source_type": exp.get("source_type", "FIRST_PARTY_DISCOVERY"),
                    "external_prior": prior,
                    "external_pattern": pattern,
                    "arms_count": len(arms),
                    "arms": arms,
                    "jobs_count": len(jobs),
                    "videos_count": len(videos),
                    "videos": videos,
                    "snapshots_count": len(snapshots),
                    "snapshots": snapshots,
                    "learnings_count": len(learnings),
                    "learning_events": learnings,
                    "active_strategy_version": strategy_version.get("version_number") if strategy_version else "v1.0"
                }
            }
