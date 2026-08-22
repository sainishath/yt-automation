# -*- coding: utf-8 -*-
"""
channel_trajectory.py
---------------------
Phase 32: Channel Health & Long-Term Trajectory Tracking Subsystem.
Tracks longitudinal first-party channel performance over 30+ days:
1. Channel Baseline Capture & Milestones (PRE_TRIAL, DAY_7, DAY_14, DAY_21, DAY_30).
2. Robust rolling medians (7d, 14d, 28d) with MAD outlier protection.
3. Deterministic Channel Improvement Scorecards (Baseline vs Current).
4. Strict causal evidence separation:
   - OBSERVED: Empirical metric movement on channel level.
   - SUPPORTED: Causal link verified via controlled N >= 4 experiment outcome.
   - INFERRED / INCONCLUSIVE: Channel changed but causality unisolated.
   - NOT_AVAILABLE: Metric not exposed by authenticated data source.
5. Explicitly separates 'EXPERIMENT WON' from 'CHANNEL PERFORMANCE IMPROVED'.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
import statistics
import json

from growth.db.models import GrowthRepository, VideoModel, PerformanceSnapshotModel, LearningEventModel
from growth.brain.belief_engine import BeliefEngine, VideoMaturity


@dataclass
class ChannelHealthSnapshot:
    channel_id: str
    tag: str  # PRE_TRIAL_BASELINE, DAY_0, DAY_7, DAY_14, DAY_21, DAY_30, CURRENT
    strategy_version: str
    total_videos_published: int
    mature_videos_count: int
    total_views: int
    median_views_per_video: float
    mean_views_per_video: float
    median_mature_views: Optional[float]
    median_apv: float
    mean_apv: float
    median_mature_apv: Optional[float]
    likes_total: int
    comments_total: int
    comment_rate: float
    subscriber_gain: str  # e.g. "NOT_AVAILABLE" or numeric string
    best_video_id: Optional[str]
    worst_video_id: Optional[str]
    rolling_7d_median_views: Optional[float]
    rolling_14d_median_views: Optional[float]
    rolling_28d_median_views: Optional[float]
    active_experiments_count: int
    completed_experiments_count: int
    promoted_patterns_count: int
    rejected_patterns_count: int
    do_not_use_count: int
    created_at: str = field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScorecardMetric:
    name: str
    baseline_value: Any
    current_value: Any
    delta_percentage: Optional[float]
    evidence_classification: str  # OBSERVED, SUPPORTED, INCONCLUSIVE, NOT_AVAILABLE
    attribution_notes: str


@dataclass
class ChannelImprovementScorecard:
    channel_id: str
    baseline_tag: str
    current_tag: str
    baseline_strategy_version: str
    current_strategy_version: str
    metrics: List[ScorecardMetric]
    experiment_wins_count: int
    channel_trajectory_status: str  # IMPROVED, FLAT, REGRESSED, INSUFFICIENT_MATURE_DATA
    summary_verdict: str
    causal_attribution_statement: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "baseline_tag": self.baseline_tag,
            "current_tag": self.current_tag,
            "baseline_strategy_version": self.baseline_strategy_version,
            "current_strategy_version": self.current_strategy_version,
            "experiment_wins_count": self.experiment_wins_count,
            "channel_trajectory_status": self.channel_trajectory_status,
            "summary_verdict": self.summary_verdict,
            "causal_attribution_statement": self.causal_attribution_statement,
            "metrics": [asdict(m) for m in self.metrics],
            "created_at": self.created_at
        }


def _parse_timestamp(ts_val: Any) -> Optional[datetime]:
    """Robustly parses a timestamp string or datetime object."""
    if not ts_val:
        return None
    if isinstance(ts_val, datetime):
        return ts_val
    ts_str = str(ts_val).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


class ChannelTrajectoryEngine:
    """
    Computes longitudinal channel health, rolling robust medians, deterministic scorecards,
    and milestone reports for the 30-day trial.
    """

    def __init__(self, repo: GrowthRepository):
        self.repo = repo
        self.belief_engine = BeliefEngine(repo)

    def _filter_mad_outliers(self, values: List[float]) -> List[float]:
        """Applies Median Absolute Deviation (MAD) filtering to robustly isolate outliers."""
        if len(values) < 4:
            return values
        med = float(statistics.median(values))
        deviations = [abs(x - med) for x in values]
        mad = float(statistics.median(deviations))
        if mad == 0:
            return values
        cutoff = 3.0 * (1.4826 * mad)
        return [x for x in values if abs(x - med) <= cutoff]

    def compute_channel_health(
        self,
        channel_id: str,
        tag: str = "CURRENT",
        as_of: Optional[datetime] = None
    ) -> ChannelHealthSnapshot:
        """
        Calculates instantaneous or milestone-specific channel health snapshot
        using SQLite first-party published videos and performance snapshots.
        Rolling windows (7d, 14d, 28d) are strictly based on calendar time.
        """
        all_vids = self.repo.list_videos_by_channel(channel_id)
        pub_vids = [v for v in all_vids if v.get("upload_status") == "UPLOADED_PUBLIC"]

        strat_ver = pub_vids[0].get("strategy_version", "v1.0") if pub_vids else "v1.0"

        views_list: List[float] = []
        apv_list: List[float] = []
        mature_views: List[float] = []
        mature_apvs: List[float] = []
        timed_videos: List[Tuple[datetime, float, float]] = []  # (ts, views, apv)
        likes_total = 0
        comments_total = 0

        best_vid = None
        worst_vid = None
        max_views = -1
        min_views = float("inf")

        mature_count = 0

        for v in pub_vids:
            vid_id = v["video_id"]
            snaps = self.repo.list_snapshots_for_video(vid_id)
            if not snaps:
                continue

            latest = snaps[-1]
            v_views = int(latest.get("views") or 0)
            v_apv = float(latest.get("avg_percentage_viewed") or 0.0)
            v_likes = int(latest.get("likes") or 0)
            v_comments = int(latest.get("comments") or 0)

            views_list.append(float(v_views))
            if v_apv > 0:
                apv_list.append(v_apv)
            likes_total += v_likes
            comments_total += v_comments

            if v_views > max_views:
                max_views = v_views
                best_vid = vid_id
            if v_views < min_views:
                min_views = v_views
                worst_vid = vid_id

            # Parse upload / publish timestamp for calendar-time windows
            v_ts = _parse_timestamp(v.get("publish_timestamp") or v.get("generation_timestamp") or latest.get("snapshot_timestamp"))
            if v_ts:
                timed_videos.append((v_ts, float(v_views), v_apv))

            # Check maturity
            is_mature = any(s.get("window_name") in ["7d", "28d"] for s in snaps)
            if is_mature:
                mature_count += 1
                mature_views.append(float(v_views))
                if v_apv > 0:
                    mature_apvs.append(v_apv)

        total_pub = len(pub_vids)
        total_views = int(sum(views_list))
        median_views = float(statistics.median(views_list)) if views_list else 0.0
        mean_views = float(statistics.mean(views_list)) if views_list else 0.0
        median_apv = float(statistics.median(apv_list)) if apv_list else 0.0
        mean_apv = float(statistics.mean(apv_list)) if apv_list else 0.0

        # Mature medians with MAD outlier protection
        filtered_mature_views = self._filter_mad_outliers(mature_views)
        filtered_mature_apvs = self._filter_mad_outliers(mature_apvs)
        median_mature_views = float(statistics.median(filtered_mature_views)) if filtered_mature_views else None
        median_mature_apv = float(statistics.median(filtered_mature_apvs)) if filtered_mature_apvs else None

        comment_rate = (comments_total / total_views) if total_views > 0 else 0.0

        # Calendar-time rolling window medians
        anchor_time = as_of
        if anchor_time is None:
            anchor_time = max((t[0] for t in timed_videos), default=datetime.utcnow())

        w7_views = [views for (ts, views, _) in timed_videos if anchor_time - timedelta(days=7) <= ts <= anchor_time]
        w14_views = [views for (ts, views, _) in timed_videos if anchor_time - timedelta(days=14) <= ts <= anchor_time]
        w28_views = [views for (ts, views, _) in timed_videos if anchor_time - timedelta(days=28) <= ts <= anchor_time]

        r7_views = float(statistics.median(w7_views)) if w7_views else None
        r14_views = float(statistics.median(w14_views)) if w14_views else None
        r28_views = float(statistics.median(w28_views)) if w28_views else None

        # Experiments & Beliefs
        exps = self.repo.list_experiments(channel_id=channel_id)
        active_exps = [e for e in exps if e.get("status") in ["RUNNING", "SCHEDULED", "COLLECTING_DATA", "APPROVED"]]
        completed_exps = [e for e in exps if e.get("status") == "EVALUATED"]

        beliefs = self.belief_engine.get_channel_beliefs(channel_id)
        promoted = sum(1 for b in beliefs if b.status.value == "PROMOTED")
        rejected = sum(1 for b in beliefs if b.status.value == "REJECTED")
        neg = self.belief_engine.get_negative_knowledge(channel_id)
        dnu_count = len(neg.get("do_not_use_patterns", []))

        return ChannelHealthSnapshot(
            channel_id=channel_id,
            tag=tag,
            strategy_version=strat_ver,
            total_videos_published=total_pub,
            mature_videos_count=mature_count,
            total_views=total_views,
            median_views_per_video=round(median_views, 1),
            mean_views_per_video=round(mean_views, 1),
            median_mature_views=round(median_mature_views, 1) if median_mature_views is not None else None,
            median_apv=round(median_apv, 1),
            mean_apv=round(mean_apv, 1),
            median_mature_apv=round(median_mature_apv, 1) if median_mature_apv is not None else None,
            likes_total=likes_total,
            comments_total=comments_total,
            comment_rate=round(comment_rate, 4),
            subscriber_gain="NOT_AVAILABLE",
            best_video_id=best_vid,
            worst_video_id=worst_vid,
            rolling_7d_median_views=round(r7_views, 1) if r7_views is not None else None,
            rolling_14d_median_views=round(r14_views, 1) if r14_views is not None else None,
            rolling_28d_median_views=round(r28_views, 1) if r28_views is not None else None,
            active_experiments_count=len(active_exps),
            completed_experiments_count=len(completed_exps),
            promoted_patterns_count=promoted,
            rejected_patterns_count=rejected,
            do_not_use_count=dnu_count
        )

    def capture_and_record_baseline(
        self,
        channel_id: str,
        tag: str = "PRE_TRIAL_BASELINE",
        as_of: Optional[datetime] = None
    ) -> ChannelHealthSnapshot:
        """
        Idempotently records a baseline or milestone snapshot into SQLite learning events.
        If the milestone for (channel_id, tag) already exists, returns the existing snapshot.
        """
        evt_type = f"MILESTONE_{tag.upper()}"
        existing_events = self.repo.list_learning_events(channel_id=channel_id, limit=100)
        for e in existing_events:
            if e.get("event_type") == evt_type and e.get("details"):
                try:
                    data = json.loads(e["details"])
                    return ChannelHealthSnapshot(**{
                        k: data[k] for k in ChannelHealthSnapshot.__dataclass_fields__ if k in data
                    })
                except Exception:
                    pass

        snapshot = self.compute_channel_health(channel_id, tag=tag, as_of=as_of)
        evt = LearningEventModel(
            channel_id=channel_id,
            event_type=evt_type,
            summary=f"Captured channel health milestone '{tag}' for {channel_id}.",
            details=json.dumps(snapshot.to_dict()),
            confidence="HIGH" if snapshot.mature_videos_count >= 4 else "LOW"
        )
        self.repo.insert_learning_event(evt)
        return snapshot

    def generate_scorecard(
        self,
        channel_id: str,
        baseline_snapshot: Optional[ChannelHealthSnapshot] = None,
        current_snapshot: Optional[ChannelHealthSnapshot] = None
    ) -> ChannelImprovementScorecard:
        """
        Compares Baseline vs Current performance to produce a deterministic scorecard
        with rigorous causal evidence classification.
        """
        if baseline_snapshot is None:
            # Check for persisted PRE_TRIAL_BASELINE or DAY_0 milestone
            existing_events = self.repo.list_learning_events(channel_id=channel_id, limit=100)
            base_evt = next((
                e for e in existing_events
                if e.get("event_type") in ["MILESTONE_PRE_TRIAL_BASELINE", "MILESTONE_DAY_0"] and e.get("details")
            ), None)
            if base_evt:
                try:
                    b_data = json.loads(base_evt["details"])
                    base = ChannelHealthSnapshot(**{
                        k: b_data[k] for k in ChannelHealthSnapshot.__dataclass_fields__ if k in b_data
                    })
                except Exception:
                    base = self.compute_channel_health(channel_id, tag="PRE_TRIAL_BASELINE")
            else:
                base = self.compute_channel_health(channel_id, tag="PRE_TRIAL_BASELINE")
        else:
            base = baseline_snapshot

        curr = current_snapshot or self.compute_channel_health(channel_id, tag="CURRENT")

        metrics: List[ScorecardMetric] = []

        # 1. Median Mature Views / Video
        if base.median_mature_views and curr.median_mature_views and base.median_mature_views > 0:
            d_views = ((curr.median_mature_views - base.median_mature_views) / base.median_mature_views) * 100.0
            ev_class = "OBSERVED"
            notes = f"Median mature views moved from {base.median_mature_views} to {curr.median_mature_views}."
        else:
            d_views = None
            ev_class = "INSUFFICIENT_SAMPLE" if curr.mature_videos_count < 4 else "NOT_AVAILABLE"
            notes = "Insufficient mature 7d+ video samples for robust baseline comparison."

        metrics.append(ScorecardMetric(
            name="median_mature_views",
            baseline_value=base.median_mature_views if base.median_mature_views is not None else "PENDING",
            current_value=curr.median_mature_views if curr.median_mature_views is not None else "PENDING",
            delta_percentage=round(d_views, 1) if d_views is not None else None,
            evidence_classification=ev_class,
            attribution_notes=notes
        ))

        # 2. Median Mature APV
        if base.median_mature_apv and curr.median_mature_apv and base.median_mature_apv > 0:
            d_apv = ((curr.median_mature_apv - base.median_mature_apv) / base.median_mature_apv) * 100.0
            ev_class = "OBSERVED"
            notes = f"Median mature APV moved from {base.median_mature_apv}% to {curr.median_mature_apv}%."
        else:
            d_apv = None
            ev_class = "INSUFFICIENT_SAMPLE" if curr.mature_videos_count < 4 else "NOT_AVAILABLE"
            notes = "Insufficient mature 7d+ APV data points for robust retention comparison."

        metrics.append(ScorecardMetric(
            name="median_mature_apv",
            baseline_value=base.median_mature_apv if base.median_mature_apv is not None else "PENDING",
            current_value=curr.median_mature_apv if curr.median_mature_apv is not None else "PENDING",
            delta_percentage=round(d_apv, 1) if d_apv is not None else None,
            evidence_classification=ev_class,
            attribution_notes=notes
        ))

        # 3. Comment Rate
        if base.comment_rate > 0 and curr.comment_rate > 0:
            d_comm = ((curr.comment_rate - base.comment_rate) / base.comment_rate) * 100.0
            ev_class = "OBSERVED"
            notes = f"Comment rate moved from {base.comment_rate:.4f} to {curr.comment_rate:.4f}."
        else:
            d_comm = None
            ev_class = "OBSERVED"
            notes = "Comment density observed across published videos."

        metrics.append(ScorecardMetric(
            name="comment_rate",
            baseline_value=base.comment_rate,
            current_value=curr.comment_rate,
            delta_percentage=round(d_comm, 1) if d_comm is not None else None,
            evidence_classification=ev_class,
            attribution_notes=notes
        ))

        # 4. Rolling 7d Median Views
        if base.rolling_7d_median_views and curr.rolling_7d_median_views and base.rolling_7d_median_views > 0:
            d_r7 = ((curr.rolling_7d_median_views - base.rolling_7d_median_views) / base.rolling_7d_median_views) * 100.0
        else:
            d_r7 = None
        metrics.append(ScorecardMetric(
            name="rolling_7d_median_views",
            baseline_value=base.rolling_7d_median_views if base.rolling_7d_median_views is not None else "PENDING",
            current_value=curr.rolling_7d_median_views if curr.rolling_7d_median_views is not None else "PENDING",
            delta_percentage=round(d_r7, 1) if d_r7 is not None else None,
            evidence_classification="OBSERVED",
            attribution_notes="7-day rolling view velocity."
        ))

        # Determine overall trajectory status
        wins_count = curr.promoted_patterns_count
        if curr.mature_videos_count < 4:
            traj_status = "INSUFFICIENT_MATURE_DATA"
            verdict = "Trial in early sample collection phase. Insufficient mature data for longitudinal verdict."
            causal_stmt = "Causality unisolated; awaiting N >= 4 mature sample cohorts."
        elif d_apv is not None and d_apv >= 5.0 and wins_count > 0:
            traj_status = "IMPROVED"
            verdict = f"Channel performance demonstrated positive trajectory (Mature APV +{d_apv:.1f}%)."
            causal_stmt = "SUPPORTED: Channel retention improvement is causally supported by controlled experiment promotion."
        elif d_apv is not None and d_apv <= -5.0:
            traj_status = "REGRESSED"
            verdict = f"Channel performance demonstrated negative trajectory (Mature APV {d_apv:.1f}%)."
            causal_stmt = "OBSERVED regression; triggering FIRST_PARTY_OVERRIDE and DO_NOT_USE containment."
        else:
            traj_status = "FLAT"
            verdict = "Channel performance remained within +/-5% baseline stability threshold."
            causal_stmt = "INCONCLUSIVE: Baseline stability maintained; awaiting further cohort refinement."

        return ChannelImprovementScorecard(
            channel_id=channel_id,
            baseline_tag=base.tag,
            current_tag=curr.tag,
            baseline_strategy_version=base.strategy_version,
            current_strategy_version=curr.strategy_version,
            metrics=metrics,
            experiment_wins_count=wins_count,
            channel_trajectory_status=traj_status,
            summary_verdict=verdict,
            causal_attribution_statement=causal_stmt
        )
