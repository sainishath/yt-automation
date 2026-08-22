# -*- coding: utf-8 -*-
"""
repository.py
-------------
Database access layer for the External Intelligence subsystem.
Provides robust, thread-safe CRUD operations with strict foreign key constraints and WAL support.
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from growth.db.database import get_db, DEFAULT_DB_PATH
from growth.external_intelligence.schemas import (
    ExternalChannelModel,
    ExternalVideoModel,
    ExternalVideoSnapshotModel,
    ExternalObservationModel,
    ExternalEvidenceModel,
    ExternalPatternModel,
    TransferabilityScoreModel,
    ExternalPriorModel,
    ResearchRunModel,
    PriorStatus,
    ResearchStatus,
    ProvenanceSource,
    ObservationType,
    EvidenceLevel,
    TransferabilityClassification,
    PatternType
)


class ExternalIntelligenceRepository:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path

    # ── External Channels ───────────────────────────────────────────────────

    def upsert_external_channel(self, channel: ExternalChannelModel) -> None:
        with get_db(self.db_path) as conn:
            conn.execute("""
                INSERT INTO external_channels (
                    external_channel_id, target_channel_id, channel_title, handle,
                    youtube_channel_id, subscriber_count, video_count, content_niche,
                    similarity_score, similarity_reasons, confidence, is_simulation,
                    source_type, last_researched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(external_channel_id) DO UPDATE SET
                    channel_title=excluded.channel_title,
                    handle=excluded.handle,
                    youtube_channel_id=excluded.youtube_channel_id,
                    subscriber_count=excluded.subscriber_count,
                    video_count=excluded.video_count,
                    content_niche=excluded.content_niche,
                    similarity_score=excluded.similarity_score,
                    similarity_reasons=excluded.similarity_reasons,
                    confidence=excluded.confidence,
                    is_simulation=excluded.is_simulation,
                    source_type=excluded.source_type,
                    last_researched_at=excluded.last_researched_at
            """, (
                channel.external_channel_id,
                channel.target_channel_id,
                channel.channel_title,
                channel.handle,
                channel.youtube_channel_id,
                channel.subscriber_count,
                channel.video_count,
                channel.content_niche,
                channel.similarity_score,
                json.dumps(channel.similarity_reasons),
                channel.confidence,
                1 if channel.is_simulation else 0,
                channel.source_type.value if hasattr(channel.source_type, 'value') else channel.source_type,
                channel.last_researched_at or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ))

    def get_external_channel(self, external_channel_id: str) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            row = conn.execute("SELECT * FROM external_channels WHERE external_channel_id = ?", (external_channel_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            d["similarity_reasons"] = json.loads(d["similarity_reasons"]) if d.get("similarity_reasons") else []
            d["is_simulation"] = bool(d["is_simulation"])
            return d

    def list_external_channels(self, target_channel_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            if target_channel_id:
                rows = conn.execute("SELECT * FROM external_channels WHERE target_channel_id = ? ORDER BY similarity_score DESC", (target_channel_id,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM external_channels ORDER BY similarity_score DESC").fetchall()
            res = []
            for r in rows:
                d = dict(r)
                d["similarity_reasons"] = json.loads(d["similarity_reasons"]) if d.get("similarity_reasons") else []
                d["is_simulation"] = bool(d["is_simulation"])
                res.append(d)
            return res

    # ── External Videos ─────────────────────────────────────────────────────

    def upsert_external_video(self, video: ExternalVideoModel) -> None:
        with get_db(self.db_path) as conn:
            conn.execute("""
                INSERT INTO external_videos (
                    external_video_id, external_channel_id, youtube_video_id, title, url,
                    published_at, duration_seconds, is_short, views, likes, comments,
                    relative_view_multiplier, is_simulation, source_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(external_video_id) DO UPDATE SET
                    title=excluded.title,
                    url=excluded.url,
                    published_at=excluded.published_at,
                    duration_seconds=excluded.duration_seconds,
                    is_short=excluded.is_short,
                    views=excluded.views,
                    likes=excluded.likes,
                    comments=excluded.comments,
                    relative_view_multiplier=excluded.relative_view_multiplier,
                    is_simulation=excluded.is_simulation,
                    source_type=excluded.source_type
            """, (
                video.external_video_id,
                video.external_channel_id,
                video.youtube_video_id,
                video.title,
                video.url,
                video.published_at,
                video.duration_seconds,
                1 if video.is_short else 0,
                video.views,
                video.likes,
                video.comments,
                video.relative_view_multiplier,
                1 if video.is_simulation else 0,
                video.source_type.value if hasattr(video.source_type, 'value') else video.source_type
            ))

    def get_external_video(self, external_video_id: str) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            row = conn.execute("SELECT * FROM external_videos WHERE external_video_id = ?", (external_video_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            d["is_short"] = bool(d["is_short"])
            d["is_simulation"] = bool(d["is_simulation"])
            return d

    def list_external_videos(self, external_channel_id: Optional[str] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            if external_channel_id:
                rows = conn.execute("SELECT * FROM external_videos WHERE external_channel_id = ? ORDER BY views DESC LIMIT ?", (external_channel_id, limit)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM external_videos ORDER BY views DESC LIMIT ?", (limit,)).fetchall()
            res = []
            for r in rows:
                d = dict(r)
                d["is_short"] = bool(d["is_short"])
                d["is_simulation"] = bool(d["is_simulation"])
                res.append(d)
            return res

    # ── External Video Snapshots ─────────────────────────────────────────────

    def upsert_external_video_snapshot(self, snap: ExternalVideoSnapshotModel) -> None:
        with get_db(self.db_path) as conn:
            conn.execute("""
                INSERT INTO external_video_snapshots (
                    external_video_id, window_name, views, likes, comments,
                    relative_view_multiplier, source_type, is_simulation, observed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(external_video_id, window_name) DO UPDATE SET
                    views=excluded.views,
                    likes=excluded.likes,
                    comments=excluded.comments,
                    relative_view_multiplier=excluded.relative_view_multiplier,
                    source_type=excluded.source_type,
                    is_simulation=excluded.is_simulation,
                    observed_at=excluded.observed_at
            """, (
                snap.external_video_id,
                snap.window_name,
                snap.views,
                snap.likes,
                snap.comments,
                snap.relative_view_multiplier,
                snap.source_type.value if hasattr(snap.source_type, "value") else snap.source_type,
                1 if snap.is_simulation else 0,
                snap.observed_at or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ))

    def list_external_video_snapshots(self, external_video_id: str) -> List[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM external_video_snapshots WHERE external_video_id = ? ORDER BY snapshot_id ASC",
                (external_video_id,)
            ).fetchall()
            res = []
            for r in rows:
                d = dict(r)
                d["is_simulation"] = bool(d["is_simulation"])
                res.append(d)
            return res

    # ── Observations ────────────────────────────────────────────────────────

    def upsert_external_observation(self, obs: ExternalObservationModel) -> None:
        self.insert_observation(obs)

    def insert_observation(self, obs: ExternalObservationModel) -> None:
        with get_db(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO external_observations (
                    observation_id, external_video_id, observation_type, field_name,
                    observed_value, interpretation, evidence_level, confidence,
                    is_simulation, source_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.observation_id,
                obs.external_video_id,
                obs.observation_type.value if hasattr(obs.observation_type, 'value') else obs.observation_type,
                obs.field_name,
                obs.observed_value,
                obs.interpretation,
                obs.evidence_level.value if hasattr(obs.evidence_level, 'value') else obs.evidence_level,
                obs.confidence,
                1 if obs.is_simulation else 0,
                obs.source_type.value if hasattr(obs.source_type, 'value') else obs.source_type
            ))

    def list_observations_by_video(self, external_video_id: str) -> List[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM external_observations WHERE external_video_id = ?", (external_video_id,)).fetchall()
            return [dict(r) for r in rows]

    # ── Patterns ────────────────────────────────────────────────────────────

    def upsert_pattern(self, pattern: ExternalPatternModel) -> None:
        with get_db(self.db_path) as conn:
            conn.execute("""
                INSERT INTO external_patterns (
                    pattern_id, target_channel_id, pattern_type, name, description,
                    surface_technique, underlying_principle, our_possible_implementation,
                    frequency, channel_count, video_count, supporting_observations,
                    consistency_score, confidence, is_simulation, source_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(pattern_id) DO UPDATE SET
                    name=excluded.name,
                    description=excluded.description,
                    surface_technique=excluded.surface_technique,
                    underlying_principle=excluded.underlying_principle,
                    our_possible_implementation=excluded.our_possible_implementation,
                    frequency=excluded.frequency,
                    channel_count=excluded.channel_count,
                    video_count=excluded.video_count,
                    supporting_observations=excluded.supporting_observations,
                    consistency_score=excluded.consistency_score,
                    confidence=excluded.confidence,
                    is_simulation=excluded.is_simulation,
                    source_type=excluded.source_type
            """, (
                pattern.pattern_id,
                pattern.target_channel_id,
                pattern.pattern_type.value if hasattr(pattern.pattern_type, 'value') else pattern.pattern_type,
                pattern.name,
                pattern.description,
                pattern.surface_technique,
                pattern.underlying_principle,
                pattern.our_possible_implementation,
                pattern.frequency,
                pattern.channel_count,
                pattern.video_count,
                json.dumps(pattern.supporting_observations),
                pattern.consistency_score,
                pattern.confidence,
                1 if pattern.is_simulation else 0,
                pattern.source_type.value if hasattr(pattern.source_type, 'value') else pattern.source_type
            ))

    def get_pattern(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            row = conn.execute("SELECT * FROM external_patterns WHERE pattern_id = ?", (pattern_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            d["supporting_observations"] = json.loads(d["supporting_observations"]) if d.get("supporting_observations") else []
            d["is_simulation"] = bool(d["is_simulation"])
            return d

    def list_patterns(self, target_channel_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            if target_channel_id:
                rows = conn.execute("SELECT * FROM external_patterns WHERE target_channel_id = ? ORDER BY confidence DESC", (target_channel_id,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM external_patterns ORDER BY confidence DESC").fetchall()
            res = []
            for r in rows:
                d = dict(r)
                d["supporting_observations"] = json.loads(d["supporting_observations"]) if d.get("supporting_observations") else []
                d["is_simulation"] = bool(d["is_simulation"])
                res.append(d)
            return res

    def list_external_patterns(self, target_channel_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.list_patterns(target_channel_id)

    # ── Transferability Scores ──────────────────────────────────────────────

    def upsert_transferability_score(self, score: TransferabilityScoreModel) -> None:
        with get_db(self.db_path) as conn:
            conn.execute("""
                INSERT INTO transferability_scores (
                    transferability_id, pattern_id, target_channel_id,
                    topic_similarity, audience_similarity, format_similarity,
                    production_similarity, evidence_strength, repeatability,
                    overall_transferability_score, classification, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(transferability_id) DO UPDATE SET
                    topic_similarity=excluded.topic_similarity,
                    audience_similarity=excluded.audience_similarity,
                    format_similarity=excluded.format_similarity,
                    production_similarity=excluded.production_similarity,
                    evidence_strength=excluded.evidence_strength,
                    repeatability=excluded.repeatability,
                    overall_transferability_score=excluded.overall_transferability_score,
                    classification=excluded.classification,
                    reason=excluded.reason
            """, (
                score.transferability_id,
                score.pattern_id,
                score.target_channel_id,
                score.topic_similarity,
                score.audience_similarity,
                score.format_similarity,
                score.production_similarity,
                score.evidence_strength,
                score.repeatability,
                score.overall_transferability_score,
                score.classification.value if hasattr(score.classification, 'value') else score.classification,
                score.reason
            ))

    def get_transferability_score(self, pattern_id: str, target_channel_id: str) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            row = conn.execute("SELECT * FROM transferability_scores WHERE pattern_id = ? AND target_channel_id = ?", (pattern_id, target_channel_id)).fetchone()
            return dict(row) if row else None

    def list_transferability_scores(self, target_channel_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            if target_channel_id:
                rows = conn.execute("SELECT * FROM transferability_scores WHERE target_channel_id = ? ORDER BY overall_transferability_score DESC", (target_channel_id,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM transferability_scores ORDER BY overall_transferability_score DESC").fetchall()
            return [dict(r) for r in rows]

    # ── External Priors ─────────────────────────────────────────────────────

    def upsert_external_prior(self, prior: ExternalPriorModel) -> None:
        with get_db(self.db_path) as conn:
            conn.execute("""
                INSERT INTO external_priors (
                    prior_id, target_channel_id, pattern_id, hypothesis,
                    transferability_classification, prior_weight, status,
                    first_party_override_reason, review_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(prior_id) DO UPDATE SET
                    hypothesis=excluded.hypothesis,
                    transferability_classification=excluded.transferability_classification,
                    prior_weight=excluded.prior_weight,
                    status=excluded.status,
                    first_party_override_reason=excluded.first_party_override_reason,
                    review_by=excluded.review_by
            """, (
                prior.prior_id,
                prior.target_channel_id,
                prior.pattern_id,
                prior.hypothesis,
                prior.transferability_classification.value if hasattr(prior.transferability_classification, 'value') else prior.transferability_classification,
                prior.prior_weight,
                prior.status.value if hasattr(prior.status, 'value') else prior.status,
                prior.first_party_override_reason,
                prior.review_by
            ))

    def get_external_prior(self, prior_id: str) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            row = conn.execute("SELECT * FROM external_priors WHERE prior_id = ?", (prior_id,)).fetchone()
            return dict(row) if row else None

    def list_external_priors(self, target_channel_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            query = "SELECT * FROM external_priors WHERE 1=1"
            params = []
            if target_channel_id:
                query += " AND target_channel_id = ?"
                params.append(target_channel_id)
            if status:
                query += " AND status = ?"
                params.append(status)
            query += " ORDER BY prior_weight DESC"
            rows = conn.execute(query, tuple(params)).fetchall()
            return [dict(r) for r in rows]

    def update_prior_status(self, prior_id: str, status: PriorStatus, override_reason: Optional[str] = None) -> None:
        with get_db(self.db_path) as conn:
            conn.execute("""
                UPDATE external_priors SET
                    status = ?,
                    first_party_override_reason = COALESCE(?, first_party_override_reason)
                WHERE prior_id = ?
            """, (
                status.value if hasattr(status, 'value') else status,
                override_reason,
                prior_id
            ))

    # ── Research Runs ───────────────────────────────────────────────────────

    def record_research_run(self, run: ResearchRunModel) -> None:
        with get_db(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO research_runs (
                    run_id, target_channel_id, channels_scanned, videos_analyzed,
                    patterns_discovered, priors_generated, status, error_message,
                    is_simulation, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run.run_id,
                run.target_channel_id,
                run.channels_scanned,
                run.videos_analyzed,
                run.patterns_discovered,
                run.priors_generated,
                run.status.value if hasattr(run.status, 'value') else run.status,
                run.error_message,
                1 if run.is_simulation else 0,
                run.completed_at
            ))
