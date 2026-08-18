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
    upload_status: str
    privacy_status: str
    review_status: str
    strategy_version: str
    topic_id: Optional[str] = None
    description: Optional[str] = None
    youtube_video_id: Optional[str] = None
    youtube_url: Optional[str] = None
    qa_score: Optional[float] = None
    experiment_id: Optional[str] = None
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
    strategy_version: Optional[str] = None
    experiment_id: Optional[str] = None
    variant_id: Optional[str] = None
    error_message: Optional[str] = None
    attempt_count: int = 1


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
                    qa_score, review_status, strategy_version, experiment_id, variant_id,
                    publish_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
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
                    variant_id=excluded.variant_id,
                    publish_timestamp=COALESCE(excluded.publish_timestamp, videos.publish_timestamp)
            """, (
                video.video_id, video.channel_id, video.pipeline_id, video.topic_id,
                video.title, video.description, video.duration, video.youtube_video_id,
                video.youtube_url, video.upload_status, video.privacy_status, video.qa_score,
                video.review_status, video.strategy_version, video.experiment_id, video.variant_id,
                video.publish_timestamp
            ))

    def get_video(self, video_id: str) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            row = conn.execute("SELECT * FROM videos WHERE video_id = ?", (video_id,)).fetchone()
            return dict(row) if row else None

    def list_videos_by_channel(self, channel_id: str) -> List[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM videos WHERE channel_id = ? ORDER BY generation_timestamp DESC", (channel_id,)).fetchall()
            return [dict(r) for r in rows]

    def upsert_features(self, feat: VideoFeaturesModel) -> None:
        with get_db(self.db_path) as conn:
            conn.execute("""
                INSERT INTO video_features (
                    video_id, topic_category, hook_type, hook_score, hook_text, word_count,
                    scene_count, avg_scene_duration, visual_change_rate, motion_type,
                    motion_intensity, caption_density, narrative_structure, speaker_balance,
                    turn_count, controversy_level
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
                feat.video_id, feat.topic_category, feat.hook_type, feat.hook_score, feat.hook_text,
                feat.word_count, feat.scene_count, feat.avg_scene_duration, feat.visual_change_rate,
                feat.motion_type, feat.motion_intensity, feat.caption_density, feat.narrative_structure,
                feat.speaker_balance, feat.turn_count, feat.controversy_level
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
                    job_id, channel_id, pipeline_id, video_id, topic_text,
                    status, strategy_version, experiment_id, variant_id,
                    error_message, attempt_count, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(job_id) DO UPDATE SET
                    status=excluded.status,
                    video_id=excluded.video_id,
                    error_message=excluded.error_message,
                    attempt_count=excluded.attempt_count,
                    updated_at=CURRENT_TIMESTAMP
            """, (
                job.job_id, job.channel_id, job.pipeline_id, job.video_id, job.topic_text,
                job.status, job.strategy_version, job.experiment_id, job.variant_id,
                job.error_message, job.attempt_count
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
