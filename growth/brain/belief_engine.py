# -*- coding: utf-8 -*-
"""
belief_engine.py
----------------
Core Belief Update, Maturity Classification, Multi-Dimensional Attribution,
and Negative Knowledge Subsystem for the Content Brain.
"""

from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import statistics

from growth.db.models import GrowthRepository, VideoModel, PerformanceSnapshotModel, LearningEventModel
from growth.external_intelligence.repository import ExternalIntelligenceRepository
from growth.external_intelligence.schemas import ExternalPriorModel, PriorStatus
from growth.brain.schemas import ConfidenceLevel, KnowledgeState, KnowledgeLevel


class VideoMaturity(Enum):
    IMMATURE = "IMMATURE"        # 1h, 6h: Sanity check / zero-view diagnostic only
    PRELIMINARY = "PRELIMINARY"  # 24h, 48h: Initial attribution & diagnostic learning
    MATURE = "MATURE"            # 7d: Primary evaluation window for cohort comparison
    LONG_TERM = "LONG_TERM"      # 28d: Historical baseline & evergreen decay


class BeliefStatus(Enum):
    HYPOTHESIS = "HYPOTHESIS"
    VALIDATING = "VALIDATING"
    PROMOTED = "PROMOTED"
    REJECTED = "REJECTED"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass
class VideoDiagnostic:
    video_id: str
    channel_id: str
    maturity: VideoMaturity
    experiment_id: Optional[str] = None
    arm: Optional[str] = None
    views: int = 0
    views_per_hour: float = 0.0
    relative_to_channel_median: float = 1.0
    hook_signal: str = "NEUTRAL"
    topic_signal: str = "NORMAL_DEMAND"
    pacing_signal: str = "ACCEPTABLE"
    ending_signal: str = "NORMAL"
    comment_signal: str = "NORMAL"
    topic_fit_score: float = 0.5
    hook_retention_score: float = 0.5
    pacing_score: float = 0.5
    ending_engagement_score: float = 0.5
    relative_view_multiplier: float = 1.0
    anomaly_flags: List[str] = field(default_factory=list)
    evidence_level: str = "FIRST_PARTY_DIAGNOSTIC"
    summary: str = ""
    what_worked: List[str] = field(default_factory=list)
    what_failed: List[str] = field(default_factory=list)
    recommended_retest: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "video_id": self.video_id,
            "channel_id": self.channel_id,
            "maturity": self.maturity.value,
            "experiment_id": self.experiment_id,
            "arm": self.arm,
            "views": self.views,
            "views_per_hour": round(self.views_per_hour, 2),
            "relative_to_channel_median": round(self.relative_to_channel_median, 3),
            "hook_signal": self.hook_signal,
            "topic_signal": self.topic_signal,
            "pacing_signal": self.pacing_signal,
            "ending_signal": self.ending_signal,
            "comment_signal": self.comment_signal,
            "topic_fit_score": round(self.topic_fit_score, 3),
            "hook_retention_score": round(self.hook_retention_score, 3),
            "pacing_score": round(self.pacing_score, 3),
            "ending_engagement_score": round(self.ending_engagement_score, 3),
            "relative_view_multiplier": round(self.relative_view_multiplier, 3),
            "anomaly_flags": self.anomaly_flags,
            "evidence_level": self.evidence_level,
            "summary": self.summary,
            "what_worked": self.what_worked,
            "what_failed": self.what_failed,
            "recommended_retest": self.recommended_retest,
            "created_at": self.created_at
        }


@dataclass
class PatternBelief:
    pattern_id: str
    target_channel_id: str
    variable_type: str  # 'HOOK_STRUCTURE', 'TOPIC_CLUSTER', 'PACING', 'VOICE'
    name: str
    status: BeliefStatus
    confidence: ConfidenceLevel
    prior_weight: float
    first_party_samples: int
    control_samples: int
    treatment_samples: int
    observed_lift_percentage: Optional[float] = 0.0
    first_party_override: bool = False
    rejection_reason: Optional[str] = None
    last_updated: str = field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "target_channel_id": self.target_channel_id,
            "variable_type": self.variable_type,
            "name": self.name,
            "status": self.status.value,
            "confidence": self.confidence.value,
            "prior_weight": round(self.prior_weight, 3) if self.prior_weight is not None else 0.0,
            "first_party_samples": self.first_party_samples,
            "control_samples": self.control_samples,
            "treatment_samples": self.treatment_samples,
            "observed_lift_percentage": round(self.observed_lift_percentage, 1) if self.observed_lift_percentage is not None else 0.0,
            "first_party_override": self.first_party_override,
            "rejection_reason": self.rejection_reason,
            "last_updated": self.last_updated
        }


class BeliefEngine:
    """
    Manages Bayesian/empirical belief progression, video attribution diagnostics,
    and institutional negative knowledge persistence.
    """

    def __init__(self, repo: GrowthRepository, ext_repo: Optional[ExternalIntelligenceRepository] = None):
        self.repo = repo
        self.ext_repo = ext_repo or ExternalIntelligenceRepository(repo.db_path)

    def classify_maturity(self, window_name: str) -> VideoMaturity:
        """Classifies performance snapshot into a strict maturity tier."""
        w = window_name.lower()
        if w in ["1h", "6h"]:
            return VideoMaturity.IMMATURE
        elif w in ["24h", "48h"]:
            return VideoMaturity.PRELIMINARY
        elif w in ["7d"]:
            return VideoMaturity.MATURE
        elif w in ["28d"]:
            return VideoMaturity.LONG_TERM
        return VideoMaturity.PRELIMINARY

    def generate_video_diagnostic(self, video_id: str) -> Optional[VideoDiagnostic]:
        """
        Calculates multi-dimensional diagnostic attribution for a video
        based on available snapshots and baseline performance.
        """
        video = self.repo.get_video(video_id)
        if not video:
            return None

        snaps = self.repo.list_snapshots_for_video(video_id)
        if not snaps:
            return None

        # Sort snapshots by window priority (7d > 48h > 24h > 6h > 1h)
        window_weights = {"7d": 4, "48h": 3, "24h": 2, "6h": 1, "1h": 0}
        snaps.sort(key=lambda s: window_weights.get(s.get("window_name", ""), 0), reverse=True)
        latest_snap = snaps[0]
        maturity = self.classify_maturity(latest_snap.get("window_name", "24h"))

        views = int(latest_snap.get("views") or 0)
        vph = float(latest_snap.get("views_per_hour") or 0.0)
        apv = float(latest_snap.get("avg_percentage_viewed") or 0.0)
        likes = int(latest_snap.get("likes") or 0)
        comments = int(latest_snap.get("comments") or 0)

        # Baseline comparisons
        all_channel_vids = self.repo.list_videos(channel_id=video.get("channel_id"), limit=100)
        all_apvs = []
        all_views = []
        for v in all_channel_vids:
            v_snaps = self.repo.list_snapshots_for_video(v.get("video_id"))
            if v_snaps:
                snap_apv = v_snaps[-1].get("avg_percentage_viewed")
                if snap_apv is not None:
                    all_apvs.append(float(snap_apv))
                snap_v = v_snaps[-1].get("views")
                if snap_v is not None:
                    all_views.append(int(snap_v))

        median_apv = float(statistics.median(all_apvs)) if all_apvs else 75.0
        median_views = float(statistics.median(all_views)) if all_views else max(float(views), 1.0)

        rel_view_multiplier = views / max(median_views, 1) if median_views > 0 else 1.0

        # Multi-factor score computation
        topic_fit = min(1.0, max(0.2, rel_view_multiplier * 0.8))
        hook_score = min(1.0, max(0.1, apv / max(median_apv, 50.0)))
        pacing_score = min(1.0, max(0.2, (apv / 100.0) * 1.1))
        comment_ratio = comments / max(views, 1)
        ending_score = min(1.0, max(0.3, comment_ratio * 50.0 + (0.5 if likes > 0 else 0.2)))

        # Signal labels
        hook_signal = "STRONG_POSITIVE" if hook_score >= 1.1 else ("POSITIVE" if hook_score >= 0.9 else ("NEGATIVE" if hook_score < 0.75 else "NEUTRAL"))
        topic_signal = "HIGH_DEMAND" if rel_view_multiplier >= 1.25 else ("LOW_DEMAND" if rel_view_multiplier < 0.75 else "NORMAL_DEMAND")
        pacing_signal = "OPTIMAL_RETENTION" if pacing_score >= 0.85 else ("PACING_DRAG" if pacing_score < 0.7 else "ACCEPTABLE")
        ending_signal = "HIGH_ENGAGEMENT" if ending_score >= 0.8 else ("LOW_ENGAGEMENT" if ending_score < 0.4 else "NORMAL")
        comment_signal = "HIGH_COMMENT_DENSITY" if comment_ratio >= 0.02 else "NORMAL"

        anomaly_flags = []
        if views == 0 and maturity in [VideoMaturity.PRELIMINARY, VideoMaturity.MATURE]:
            anomaly_flags.append("ZERO_VIEWS_DEFECT")
        if apv < 30.0 and views > 10:
            anomaly_flags.append("ABNORMAL_EARLY_DROPOFF")
        if rel_view_multiplier > 4.0:
            anomaly_flags.append("VIRAL_OUTLIER")

        evidence_level = "FIRST_PARTY_MATURE" if maturity == VideoMaturity.MATURE else "FIRST_PARTY_DIAGNOSTIC"

        what_worked = []
        what_failed = []

        if hook_score >= 0.9:
            what_worked.append("High early retention (Hook structure effectively captured attention)")
        else:
            what_failed.append("Early audience drop-off (Hook structure underperformed baseline)")

        if pacing_score >= 0.8:
            what_worked.append("Smooth mid-video retention (3.2s visual rhythm sustained attention)")
        else:
            what_failed.append("Mid-video pacing drag (Excessive static visual duration)")

        if ending_score >= 0.7:
            what_worked.append("Strong comment engagement (Controversial/Socratic CTA triggered discussion)")

        summary = (
            f"Video '{video.get('title')}' ({maturity.value}): APV {apv:.1f}% vs Median {median_apv:.1f}% "
            f"(Views: {views}, Rel Mult: {rel_view_multiplier:.2f}x, Hook: {hook_signal})."
        )

        diag = VideoDiagnostic(
            video_id=video_id,
            channel_id=video.get("channel_id"),
            maturity=maturity,
            experiment_id=video.get("experiment_id"),
            arm=video.get("variant_id"),
            views=views,
            views_per_hour=vph,
            relative_to_channel_median=rel_view_multiplier,
            hook_signal=hook_signal,
            topic_signal=topic_signal,
            pacing_signal=pacing_signal,
            ending_signal=ending_signal,
            comment_signal=comment_signal,
            topic_fit_score=topic_fit,
            hook_retention_score=hook_score,
            pacing_score=pacing_score,
            ending_engagement_score=ending_score,
            relative_view_multiplier=rel_view_multiplier,
            anomaly_flags=anomaly_flags,
            evidence_level=evidence_level,
            summary=summary,
            what_worked=what_worked,
            what_failed=what_failed,
            recommended_retest=video.get("variant_id") if hook_score < 0.8 else None
        )

        # Store learning event
        evt = LearningEventModel(
            channel_id=video.get("channel_id"),
            event_type="VIDEO_DIAGNOSTIC",
            summary=summary,
            details=json.dumps(diag.to_dict()),
            confidence="MEDIUM" if maturity in [VideoMaturity.MATURE, VideoMaturity.PRELIMINARY] else "LOW"
        )
        self.repo.insert_learning_event(evt)
        return diag

    def get_channel_beliefs(self, channel_id: str) -> List[PatternBelief]:
        """
        Synthesizes the complete empirical belief state for a channel across all
        external priors, active experiments, and historical outcomes.
        """
        priors = self.ext_repo.list_external_priors(target_channel_id=channel_id)
        exps = self.repo.list_experiments(channel_id=channel_id)
        patterns = self.ext_repo.list_patterns(target_channel_id=channel_id)

        exp_by_prior = {e.get("external_prior_id"): e for e in exps if e.get("external_prior_id")}
        pat_by_id = {p.get("pattern_id"): p for p in patterns}

        beliefs = []
        for pr in priors:
            pid = pr.get("prior_id")
            pat_id = pr.get("pattern_id")
            pat_info = pat_by_id.get(pat_id, {})
            name = pat_info.get("name", pr.get("hypothesis", pid))
            var_type = pat_info.get("pattern_type", "HOOK_STRUCTURE")

            exp = exp_by_prior.get(pid)
            ctrl_cnt = exp.get("control_count", 0) if exp else 0
            treat_cnt = exp.get("treatment_count", 0) if exp else 0
            total_fp = ctrl_cnt + treat_cnt
            delta = exp.get("delta_percentage", 0.0) if exp else 0.0

            # Determine Belief Status & Confidence
            if pr.get("status") == "REJECTED" or (exp and exp.get("decision") == "LOSE"):
                status = BeliefStatus.REJECTED
                confidence = ConfidenceLevel.HIGH if (ctrl_cnt >= 4 and treat_cnt >= 4) else ConfidenceLevel.MEDIUM
                prior_weight = 0.0
                override = True
                rejection_reason = "Empirical first-party N >= 4 experiment outcome resulted in negative retention delta."
            elif exp and exp.get("decision") == "ACCEPT_VARIANT":
                status = BeliefStatus.PROMOTED
                confidence = ConfidenceLevel.HIGH
                prior_weight = 1.0
                override = False
                rejection_reason = None
            elif total_fp > 0:
                status = BeliefStatus.VALIDATING
                confidence = ConfidenceLevel.LOW
                prior_weight = pr.get("prior_weight", 0.2)
                override = False
                rejection_reason = None
            else:
                status = BeliefStatus.HYPOTHESIS
                confidence = ConfidenceLevel.LOW
                prior_weight = pr.get("prior_weight", 0.2)
                override = False
                rejection_reason = None

            beliefs.append(PatternBelief(
                pattern_id=pid,
                target_channel_id=channel_id,
                variable_type=var_type,
                name=name,
                status=status,
                confidence=confidence,
                prior_weight=prior_weight,
                first_party_samples=total_fp,
                control_samples=ctrl_cnt,
                treatment_samples=treat_cnt,
                observed_lift_percentage=delta,
                first_party_override=override,
                rejection_reason=rejection_reason
            ))

        return beliefs

    def get_negative_knowledge(self, channel_id: str) -> Dict[str, Any]:
        """
        Retrieves institutional negative knowledge (DO_NOT_USE registry,
        rejected hypotheses, and active uncertainties) for a channel.
        """
        beliefs = self.get_channel_beliefs(channel_id)
        rejected = [b.to_dict() for b in beliefs if b.status == BeliefStatus.REJECTED]
        uncertain = [b.to_dict() for b in beliefs if b.status in [BeliefStatus.VALIDATING, BeliefStatus.HYPOTHESIS]]

        return {
            "channel_id": channel_id,
            "do_not_use_patterns": rejected,
            "rejected_count": len(rejected),
            "active_uncertainties": uncertain,
            "uncertain_count": len(uncertain),
            "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }
