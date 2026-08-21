# -*- coding: utf-8 -*-
"""
models.py
---------
Data models and CRUD accessors for Content Intelligence entities.
"""

import json
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from pathlib import Path
from growth.db.database import get_db, DEFAULT_DB_PATH


@dataclass
class ChannelModel:
    channel_id: str
    name: str
    handle: str
    pipeline_id: str
    content_category: str
    audience_definition: str = ""
    posting_frequency: str = ""


@dataclass
class VideoModel:
    video_id: str
    channel_id: str
    pipeline_id: str
    title: str
    duration: float
    upload_status: str = "GENERATED"
    privacy_status: str = "private"
    review_status: str = "PENDING"
    strategy_version: str = "v1.0"
    topic_id: Optional[str] = None
    description: Optional[str] = None
    youtube_video_id: Optional[str] = None
    youtube_url: Optional[str] = None
    qa_score: Optional[float] = None
    experiment_id: Optional[str] = None
    arm_id: Optional[str] = None
    variant_id: Optional[str] = None
    publish_timestamp: Optional[str] = None


@dataclass
class VideoFeaturesModel:
    video_id: str
    topic_category: str
    hook_type: str
    hook_score: float
    hook_text: str
    word_count: int
    scene_count: int
    avg_scene_duration: float
    visual_change_rate: float
    motion_type: str
    motion_intensity: float
    caption_density: float
    narrative_structure: str
    speaker_balance: float = 0.0
    turn_count: int = 0
    controversy_level: float = 0.0


@dataclass
class PerformanceSnapshotModel:
    video_id: str
    window_name: str
    views: int
    likes: int
    comments: int
    shares: int
    subscribers_gained: int
    watch_time_minutes: float
    avg_view_duration_seconds: float
    avg_percentage_viewed: float
    views_per_hour: float
    engagement_rate: float
    subscriber_conversion_rate: float
    relative_performance_score: float
    data_source: str
    data_freshness: str
    snapshot_id: Optional[int] = None


@dataclass
class JobModel:
    job_id: str
    channel_id: str
    pipeline_id: str
    topic_text: str
    status: str
    video_id: Optional[str] = None
    topic_id: Optional[str] = None
    strategy_version: Optional[str] = None
    experiment_id: Optional[str] = None
    arm_id: Optional[str] = None
    variant_id: Optional[str] = None
    error_message: Optional[str] = None
    attempt_count: int = 1


@dataclass
class ExperimentArmModel:
    arm_id: str
    experiment_id: str
    arm_type: str  # 'CONTROL', 'TREATMENT'
    name: str
    definition: str
    sample_count: int = 0
    status: str = "ACTIVE"  # 'ACTIVE', 'PAUSED', 'COMPLETED'
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExperimentModel:
    experiment_id: str
    channel_id: str
    name: str
    hypothesis: str
    variable_tested: str
    control_definition: str
    variant_definition: str
    primary_metric: str
    secondary_metrics: Optional[List[str]] = None
    min_sample_size: int = 4
    target_sample_size: int = 4
    source_type: str = "FIRST_PARTY_DISCOVERY"  # 'EXTERNAL_PRIOR', 'FIRST_PARTY_DISCOVERY', 'GENERAL_HEURISTIC'
    underlying_principle: Optional[str] = None
    status: str = "PROPOSED"
    result: Optional[str] = None
    confidence: Optional[str] = None
    external_pattern_id: Optional[str] = None
    external_prior_id: Optional[str] = None
    source_channels: Optional[List[str]] = None
    transferability_score: Optional[float] = None
    transferability_classification: Optional[str] = None
    prior_weight: Optional[float] = None
    provenance: str = "FIRST_PARTY"
    rationale: Optional[str] = None
    decision: Optional[str] = None
    decision_reason: Optional[str] = None
    delta_percentage: Optional[float] = None
    control_count: int = 0
    treatment_count: int = 0
    control_median: Optional[float] = None
    treatment_median: Optional[float] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    evaluated_at: Optional[str] = None
    first_party_override_status: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)




class GrowthRepository:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path

    def upsert_channel(self, channel: ChannelModel) -> None:
        with get_db(self.db_path) as conn:
            conn.execute("""
                INSERT INTO channels (channel_id, name, handle, pipeline_id, content_category, audience_definition, posting_frequency)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(channel_id) DO UPDATE SET
                    name=excluded.name,
                    handle=excluded.handle,
                    content_category=excluded.content_category,
                    audience_definition=excluded.audience_definition,
                    posting_frequency=excluded.posting_frequency
            """, (
                channel.channel_id, channel.name, channel.handle, channel.pipeline_id,
                channel.content_category, channel.audience_definition, channel.posting_frequency
            ))

    def get_channel(self, channel_id: str) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            row = conn.execute("SELECT * FROM channels WHERE channel_id = ?", (channel_id,)).fetchone()
            return dict(row) if row else None

    def upsert_video(self, video: VideoModel) -> None:
        with get_db(self.db_path) as conn:
            conn.execute("""
                INSERT INTO videos (
                    video_id, channel_id, pipeline_id, topic_id, title, description,
                    duration, youtube_video_id, youtube_url, upload_status, privacy_status,
                    qa_score, review_status, strategy_version, experiment_id, arm_id, variant_id,
                    publish_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
                ON CONFLICT(video_id) DO UPDATE SET
                    title=excluded.title,
                    description=excluded.description,
                    duration=excluded.duration,
                    youtube_video_id=excluded.youtube_video_id,
                    youtube_url=excluded.youtube_url,
                    upload_status=excluded.upload_status,
                    privacy_status=excluded.privacy_status,
                    qa_score=excluded.qa_score,
                    review_status=excluded.review_status,
                    strategy_version=excluded.strategy_version,
                    experiment_id=excluded.experiment_id,
                    arm_id=excluded.arm_id,
                    variant_id=excluded.variant_id,
                    publish_timestamp=COALESCE(excluded.publish_timestamp, videos.publish_timestamp)
            """, (
                video.video_id, video.channel_id, video.pipeline_id, video.topic_id,
                video.title, video.description, video.duration, video.youtube_video_id,
                video.youtube_url, video.upload_status, video.privacy_status, video.qa_score,
                video.review_status, video.strategy_version, video.experiment_id, video.arm_id,
                video.variant_id, video.publish_timestamp
            ))

    def get_video(self, video_id: str) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            row = conn.execute("SELECT * FROM videos WHERE video_id = ?", (video_id,)).fetchone()
            return dict(row) if row else None

    def list_videos_by_channel(self, channel_id: str) -> List[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM videos WHERE channel_id = ? ORDER BY generation_timestamp DESC", (channel_id,)).fetchall()
            return [dict(r) for r in rows]

    def list_videos_by_experiment(self, experiment_id: str) -> List[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM videos WHERE experiment_id = ? ORDER BY publish_timestamp ASC", (experiment_id,)).fetchall()
            return [dict(r) for r in rows]

    def upsert_features(self, feat: VideoFeaturesModel) -> None:
        with get_db(self.db_path) as conn:
            conn.execute("""
                INSERT INTO video_features (
                    video_id, topic_category, hook_type, hook_score, hook_text,
                    word_count, scene_count, avg_scene_duration, visual_change_rate,
                    motion_type, motion_intensity, caption_density, narrative_structure,
                    speaker_balance, turn_count, controversy_level
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(video_id) DO UPDATE SET
                    topic_category=excluded.topic_category,
                    hook_type=excluded.hook_type,
                    hook_score=excluded.hook_score,
                    hook_text=excluded.hook_text,
                    word_count=excluded.word_count,
                    scene_count=excluded.scene_count,
                    avg_scene_duration=excluded.avg_scene_duration,
                    visual_change_rate=excluded.visual_change_rate,
                    motion_type=excluded.motion_type,
                    motion_intensity=excluded.motion_intensity,
                    caption_density=excluded.caption_density,
                    narrative_structure=excluded.narrative_structure,
                    speaker_balance=excluded.speaker_balance,
                    turn_count=excluded.turn_count,
                    controversy_level=excluded.controversy_level
            """, (
                feat.video_id, feat.topic_category, feat.hook_type, feat.hook_score,
                feat.hook_text, feat.word_count, feat.scene_count, feat.avg_scene_duration,
                feat.visual_change_rate, feat.motion_type, feat.motion_intensity,
                feat.caption_density, feat.narrative_structure, feat.speaker_balance,
                feat.turn_count, feat.controversy_level
            ))

    def get_features(self, video_id: str) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            row = conn.execute("SELECT * FROM video_features WHERE video_id = ?", (video_id,)).fetchone()
            return dict(row) if row else None

    def insert_snapshot(self, snap: PerformanceSnapshotModel) -> int:
        with get_db(self.db_path) as conn:
            cur = conn.execute("""
                INSERT INTO performance_snapshots (
                    video_id, window_name, views, likes, comments, shares,
                    subscribers_gained, watch_time_minutes, avg_view_duration_seconds,
                    avg_percentage_viewed, views_per_hour, engagement_rate,
                    subscriber_conversion_rate, relative_performance_score,
                    data_source, data_freshness
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(video_id, window_name) DO UPDATE SET
                    views=excluded.views,
                    likes=excluded.likes,
                    comments=excluded.comments,
                    shares=excluded.shares,
                    subscribers_gained=excluded.subscribers_gained,
                    watch_time_minutes=excluded.watch_time_minutes,
                    avg_view_duration_seconds=excluded.avg_view_duration_seconds,
                    avg_percentage_viewed=excluded.avg_percentage_viewed,
                    views_per_hour=excluded.views_per_hour,
                    engagement_rate=excluded.engagement_rate,
                    subscriber_conversion_rate=excluded.subscriber_conversion_rate,
                    relative_performance_score=excluded.relative_performance_score,
                    data_source=excluded.data_source,
                    data_freshness=excluded.data_freshness
            """, (
                snap.video_id, snap.window_name, snap.views, snap.likes, snap.comments,
                snap.shares, snap.subscribers_gained, snap.watch_time_minutes,
                snap.avg_view_duration_seconds, snap.avg_percentage_viewed, snap.views_per_hour,
                snap.engagement_rate, snap.subscriber_conversion_rate,
                snap.relative_performance_score, snap.data_source, snap.data_freshness
            ))
            return cur.lastrowid

    def get_snapshots_for_video(self, video_id: str) -> List[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM performance_snapshots WHERE video_id = ? ORDER BY snapshot_id ASC", (video_id,)).fetchall()
            return [dict(r) for r in rows]

    def upsert_job(self, job: JobModel) -> None:
        with get_db(self.db_path) as conn:
            conn.execute("""
                INSERT INTO jobs (
                    job_id, channel_id, pipeline_id, video_id, topic_id, topic_text,
                    status, strategy_version, experiment_id, arm_id, variant_id,
                    error_message, attempt_count, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(job_id) DO UPDATE SET
                    status=excluded.status,
                    video_id=excluded.video_id,
                    topic_id=excluded.topic_id,
                    strategy_version=excluded.strategy_version,
                    experiment_id=excluded.experiment_id,
                    arm_id=excluded.arm_id,
                    variant_id=excluded.variant_id,
                    error_message=excluded.error_message,
                    attempt_count=excluded.attempt_count,
                    updated_at=CURRENT_TIMESTAMP
            """, (
                job.job_id, job.channel_id, job.pipeline_id, job.video_id, job.topic_id,
                job.topic_text, job.status, job.strategy_version, job.experiment_id,
                job.arm_id, job.variant_id, job.error_message, job.attempt_count
            ))

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            return dict(row) if row else None

    def list_jobs(self, channel_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            if channel_id:
                rows = conn.execute("SELECT * FROM jobs WHERE channel_id = ? ORDER BY created_at DESC LIMIT ?", (channel_id, limit)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    def upsert_experiment_arm(self, arm: ExperimentArmModel) -> None:
        with get_db(self.db_path) as conn:
            conn.execute("""
                INSERT INTO experiment_arms (
                    arm_id, experiment_id, arm_type, name, definition, sample_count, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(arm_id) DO UPDATE SET
                    name=excluded.name,
                    definition=excluded.definition,
                    sample_count=excluded.sample_count,
                    status=excluded.status
            """, (
                arm.arm_id, arm.experiment_id, arm.arm_type, arm.name,
                arm.definition, arm.sample_count, arm.status
            ))

    def get_experiment_arms(self, experiment_id: str) -> List[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM experiment_arms WHERE experiment_id = ? ORDER BY arm_type ASC", (experiment_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_experiment_arm(self, arm_id: str) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            row = conn.execute("SELECT * FROM experiment_arms WHERE arm_id = ?", (arm_id,)).fetchone()
            return dict(row) if row else None

    def increment_arm_sample_count(self, arm_id: str) -> int:
        with get_db(self.db_path) as conn:
            conn.execute("UPDATE experiment_arms SET sample_count = sample_count + 1 WHERE arm_id = ?", (arm_id,))
            row = conn.execute("SELECT sample_count FROM experiment_arms WHERE arm_id = ?", (arm_id,)).fetchone()
            return row["sample_count"] if row else 0

    def upsert_experiment(self, exp: ExperimentModel) -> None:
        sec_metrics_json = json.dumps(exp.secondary_metrics) if exp.secondary_metrics else None
        src_channels_json = json.dumps(exp.source_channels) if exp.source_channels else None

        with get_db(self.db_path) as conn:
            conn.execute("""
                INSERT INTO experiments (
                    experiment_id, channel_id, name, hypothesis, variable_tested,
                    control_definition, variant_definition, primary_metric, secondary_metrics,
                    min_sample_size, target_sample_size, source_type, underlying_principle,
                    status, result, confidence, external_pattern_id, external_prior_id,
                    source_channels, transferability_score, transferability_classification,
                    prior_weight, provenance, rationale, decision, decision_reason,
                    delta_percentage, control_count, treatment_count, control_median,
                    treatment_median, started_at, completed_at, evaluated_at,
                    first_party_override_status, updated_at
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
                )
                ON CONFLICT(experiment_id) DO UPDATE SET
                    name=excluded.name,
                    hypothesis=excluded.hypothesis,
                    variable_tested=excluded.variable_tested,
                    control_definition=excluded.control_definition,
                    variant_definition=excluded.variant_definition,
                    primary_metric=excluded.primary_metric,
                    secondary_metrics=excluded.secondary_metrics,
                    min_sample_size=excluded.min_sample_size,
                    target_sample_size=excluded.target_sample_size,
                    source_type=excluded.source_type,
                    underlying_principle=excluded.underlying_principle,
                    status=excluded.status,
                    result=excluded.result,
                    confidence=excluded.confidence,
                    external_pattern_id=excluded.external_pattern_id,
                    external_prior_id=excluded.external_prior_id,
                    source_channels=excluded.source_channels,
                    transferability_score=excluded.transferability_score,
                    transferability_classification=excluded.transferability_classification,
                    prior_weight=excluded.prior_weight,
                    provenance=excluded.provenance,
                    rationale=excluded.rationale,
                    decision=excluded.decision,
                    decision_reason=excluded.decision_reason,
                    delta_percentage=excluded.delta_percentage,
                    control_count=excluded.control_count,
                    treatment_count=excluded.treatment_count,
                    control_median=excluded.control_median,
                    treatment_median=excluded.treatment_median,
                    started_at=excluded.started_at,
                    completed_at=excluded.completed_at,
                    evaluated_at=excluded.evaluated_at,
                    first_party_override_status=excluded.first_party_override_status,
                    updated_at=CURRENT_TIMESTAMP
            """, (
                exp.experiment_id, exp.channel_id, exp.name, exp.hypothesis, exp.variable_tested,
                exp.control_definition, exp.variant_definition, exp.primary_metric, sec_metrics_json,
                exp.min_sample_size, exp.target_sample_size, exp.source_type, exp.underlying_principle,
                exp.status, exp.result, exp.confidence, exp.external_pattern_id,
                exp.external_prior_id, src_channels_json, exp.transferability_score,
                exp.transferability_classification, exp.prior_weight, exp.provenance, exp.rationale,
                exp.decision, exp.decision_reason, exp.delta_percentage, exp.control_count, exp.treatment_count,
                exp.control_median, exp.treatment_median, exp.started_at, exp.completed_at, exp.evaluated_at,
                exp.first_party_override_status
            ))

    def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            row = conn.execute("SELECT * FROM experiments WHERE experiment_id = ?", (experiment_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            if d.get("secondary_metrics"):
                try:
                    d["secondary_metrics"] = json.loads(d["secondary_metrics"])
                except Exception:
                    pass
            if d.get("source_channels"):
                try:
                    d["source_channels"] = json.loads(d["source_channels"])
                except Exception:
                    pass
            return d

    def list_experiments(self, channel_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            query = "SELECT * FROM experiments WHERE 1=1"
            params = []
            if channel_id:
                query += " AND channel_id = ?"
                params.append(channel_id)
            if status:
                query += " AND status = ?"
                params.append(status)
            query += " ORDER BY created_at DESC"
            rows = conn.execute(query, tuple(params)).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                if d.get("secondary_metrics"):
                    try:
                        d["secondary_metrics"] = json.loads(d["secondary_metrics"])
                    except Exception:
                        pass
                if d.get("source_channels"):
                    try:
                        d["source_channels"] = json.loads(d["source_channels"])
                    except Exception:
                        pass
                results.append(d)
            return results

    def get_experiment_full_lineage(self, experiment_id: str) -> Dict[str, Any]:
        """
        Retrieves the complete closed-loop audit lineage for an experiment:
        prior -> pattern -> experiment -> arms -> jobs -> videos -> snapshots -> learning events -> strategy.
        """
        with get_db(self.db_path) as conn:
            exp = self.get_experiment(experiment_id)
            if not exp:
                return {"experiment_id": experiment_id, "status": "NOT_FOUND", "is_complete": False}

            arms = self.get_experiment_arms(experiment_id)
            jobs = conn.execute("SELECT * FROM jobs WHERE experiment_id = ? ORDER BY created_at ASC", (experiment_id,)).fetchall()
            videos = conn.execute("SELECT * FROM videos WHERE experiment_id = ? ORDER BY publish_timestamp ASC", (experiment_id,)).fetchall()

            vid_ids = [v["video_id"] for v in videos]
            snapshots = []
            if vid_ids:
                placeholders = ",".join("?" * len(vid_ids))
                snap_rows = conn.execute(f"SELECT * FROM performance_snapshots WHERE video_id IN ({placeholders}) ORDER BY snapshot_id ASC", tuple(vid_ids)).fetchall()
                snapshots = [dict(s) for s in snap_rows]

            # Fetch linked prior and pattern
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

            # Check lineage completeness
            is_complete = bool(exp and arms and len(videos) >= exp.get("min_sample_size", 4) * 2 and snapshots)

            return {
                "experiment_id": experiment_id,
                "is_complete": is_complete,
                "experiment": exp,
                "external_prior": prior,
                "external_pattern": pattern,
                "arms": arms,
                "jobs": [dict(j) for j in jobs],
                "videos": [dict(v) for v in videos],
                "snapshots_count": len(snapshots),
                "snapshots": snapshots
            }
