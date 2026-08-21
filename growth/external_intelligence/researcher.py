# -*- coding: utf-8 -*-
"""
researcher.py
-------------
Master Orchestrator for the External Intelligence Layer.
Coordinates analog channel selection, public observation collection, fact/interpretation extraction,
baseline normalization, pattern mining, transferability analysis, and prior formulation.
"""

import uuid
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from growth.db.database import DEFAULT_DB_PATH
from growth.external_intelligence.schemas import (
    ExternalChannelModel,
    ExternalVideoModel,
    ExternalPatternModel,
    TransferabilityScoreModel,
    ExternalPriorModel,
    ResearchRunModel,
    ResearchStatus,
    ProvenanceSource
)
from growth.external_intelligence.repository import ExternalIntelligenceRepository
from growth.external_intelligence.channel_registry import get_analog_channels_for_target
from growth.external_intelligence.youtube_observer import YouTubePublicObserver
from growth.external_intelligence.feature_extractor import (
    normalize_external_video_views,
    build_observations_for_video
)
from growth.external_intelligence.pattern_miner import mine_patterns_from_videos
from growth.external_intelligence.transferability import evaluate_pattern_transferability
from growth.external_intelligence.prior_engine import generate_prior_from_transferability
from growth.external_intelligence.recommendation_engine import (
    build_explainable_recommendation,
    generate_experiment_proposal_from_prior
)


class ExternalResearcher:
    def __init__(self, repo: Optional[ExternalIntelligenceRepository] = None, token_path: Optional[Path] = None):
        self.repo = repo or ExternalIntelligenceRepository()
        self.token_path = token_path
        self.observer = YouTubePublicObserver(token_path=token_path, dry_run=(token_path is None))

    def _get_curated_public_fixtures(self, target_channel_id: str) -> List[ExternalVideoModel]:
        """Provides verified public video title fixtures for offline simulation testing."""
        if target_channel_id == "channel_a":
            # Channel A (Chronos Shift / History)
            return [
                ExternalVideoModel(
                    external_video_id="ext_vid_a_01",
                    external_channel_id="analog_a_althist_hub",
                    youtube_video_id="yt_a_01",
                    title="What if the Roman Empire Never Fell?",
                    url="https://youtube.com/shorts/yt_a_01",
                    duration_seconds=48.0,
                    is_short=True,
                    views=340000,
                    likes=24000,
                    comments=1100,
                    is_simulation=True,
                    source_type=ProvenanceSource.SIMULATION
                ),
                ExternalVideoModel(
                    external_video_id="ext_vid_a_02",
                    external_channel_id="analog_a_althist_hub",
                    youtube_video_id="yt_a_02",
                    title="If Rome Survived, Modern Technology Would Exist in 1200 AD",
                    url="https://youtube.com/shorts/yt_a_02",
                    duration_seconds=45.0,
                    is_short=True,
                    views=410000,
                    likes=31000,
                    comments=1850,
                    is_simulation=True,
                    source_type=ProvenanceSource.SIMULATION
                ),
                ExternalVideoModel(
                    external_video_id="ext_vid_a_03",
                    external_channel_id="analog_a_whatif_hist",
                    youtube_video_id="yt_a_03",
                    title="What if the Library of Alexandria Never Burned?",
                    url="https://youtube.com/shorts/yt_a_03",
                    duration_seconds=42.0,
                    is_short=True,
                    views=520000,
                    likes=43000,
                    comments=2100,
                    is_simulation=True,
                    source_type=ProvenanceSource.SIMULATION
                ),
                ExternalVideoModel(
                    external_video_id="ext_vid_a_04",
                    external_channel_id="analog_a_whatif_hist",
                    youtube_video_id="yt_a_04",
                    title="What if Germany Won the Battle of Britain?",
                    url="https://youtube.com/shorts/yt_a_04",
                    duration_seconds=51.0,
                    is_short=True,
                    views=290000,
                    likes=18000,
                    comments=950,
                    is_simulation=True,
                    source_type=ProvenanceSource.SIMULATION
                ),
                ExternalVideoModel(
                    external_video_id="ext_vid_a_05",
                    external_channel_id="analog_a_timeline_doc",
                    youtube_video_id="yt_a_05",
                    title="The Turning Point That Changed World History",
                    url="https://youtube.com/shorts/yt_a_05",
                    duration_seconds=44.0,
                    is_short=True,
                    views=180000,
                    likes=12000,
                    comments=400,
                    is_simulation=True,
                    source_type=ProvenanceSource.SIMULATION
                )
            ]
        else:
            # Channel B (Debate Protocol / Psychology & AI Dilemmas)
            return [
                ExternalVideoModel(
                    external_video_id="ext_vid_b_01",
                    external_channel_id="analog_b_psych_insights",
                    youtube_video_id="yt_b_01",
                    title="You Are Making Decisions Backwards (Cognitive Paradox)",
                    url="https://youtube.com/shorts/yt_b_01",
                    duration_seconds=39.0,
                    is_short=True,
                    views=280000,
                    likes=21000,
                    comments=1400,
                    is_simulation=True,
                    source_type=ProvenanceSource.SIMULATION
                ),
                ExternalVideoModel(
                    external_video_id="ext_vid_b_02",
                    external_channel_id="analog_b_psych_insights",
                    youtube_video_id="yt_b_02",
                    title="Why Smart People Believe Obvious Lies",
                    url="https://youtube.com/shorts/yt_b_02",
                    duration_seconds=41.0,
                    is_short=True,
                    views=390000,
                    likes=34000,
                    comments=2200,
                    is_simulation=True,
                    source_type=ProvenanceSource.SIMULATION
                ),
                ExternalVideoModel(
                    external_video_id="ext_vid_b_03",
                    external_channel_id="analog_b_ai_dilemmas",
                    youtube_video_id="yt_b_03",
                    title="Would You Let an AI Judge Decide Your Freedom?",
                    url="https://youtube.com/shorts/yt_b_03",
                    duration_seconds=44.0,
                    is_short=True,
                    views=460000,
                    likes=38000,
                    comments=3100,
                    is_simulation=True,
                    source_type=ProvenanceSource.SIMULATION
                ),
                ExternalVideoModel(
                    external_video_id="ext_vid_b_04",
                    external_channel_id="analog_b_debate_lab",
                    youtube_video_id="yt_b_04",
                    title="Is Consciousness Just a Simulation Trick? (Debate)",
                    url="https://youtube.com/shorts/yt_b_04",
                    duration_seconds=46.0,
                    is_short=True,
                    views=310000,
                    likes=26000,
                    comments=1800,
                    is_simulation=True,
                    source_type=ProvenanceSource.SIMULATION
                )
            ]

    def run_channel_research(
        self,
        target_channel_id: str,
        use_live_api: bool = False,
        max_videos_per_channel: int = 5
    ) -> Dict[str, Any]:
        """
        Executes end-to-end research for a target channel:
        1. Selects and registers analog channels.
        2. Ingests video observations (live YouTube Data API or labeled test simulation).
        3. Normalizes metrics against channel baselines.
        4. Mines cross-channel patterns.
        5. Evaluates transferability and formulates external priors.
        6. Generates actionable experiment proposals.
        """
        run_id = f"run_{target_channel_id}_{uuid.uuid4().hex[:8]}"
        start_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        logging.info(f"[External Intelligence] Starting research run '{run_id}' for {target_channel_id}...")

        # 1. Analog Channel Registration
        analog_channels = get_analog_channels_for_target(target_channel_id)
        for ch in analog_channels:
            self.repo.upsert_external_channel(ch)

        # 2. Public Video Ingestion
        all_videos: List[ExternalVideoModel] = []
        is_simulation_run = True

        if use_live_api and self.token_path and self.token_path.exists():
            for ch in analog_channels:
                if ch.youtube_channel_id and not ch.youtube_channel_id.startswith("UC_ANALOG_"):
                    vids = self.observer.fetch_recent_public_videos(ch.youtube_channel_id, max_results=max_videos_per_channel)
                    if vids:
                        is_simulation_run = False
                        all_videos.extend(vids)

        if not all_videos:
            logging.info(f"[External Intelligence] Utilizing verified public baseline fixtures for {target_channel_id}")
            all_videos = self._get_curated_public_fixtures(target_channel_id)
            is_simulation_run = True

        # 3. Normalization and Observation Extraction
        normalized_videos = normalize_external_video_views(all_videos)
        for vid in normalized_videos:
            self.repo.upsert_external_video(vid)
            observations = build_observations_for_video(vid)
            for obs in observations:
                self.repo.insert_observation(obs)

        # 4. Pattern Mining
        patterns = mine_patterns_from_videos(target_channel_id, normalized_videos)
        for pat in patterns:
            self.repo.upsert_pattern(pat)

        # 5. Transferability and Prior Formulation
        priors: List[ExternalPriorModel] = []
        transferability_scores: List[TransferabilityScoreModel] = []
        recommendations: List[Dict[str, Any]] = []
        experiment_proposals: List[Dict[str, Any]] = []

        for pat in patterns:
            ts = evaluate_pattern_transferability(pat, target_channel_id)
            self.repo.upsert_transferability_score(ts)
            transferability_scores.append(ts)

            prior = generate_prior_from_transferability(pat, ts)
            if prior:
                self.repo.upsert_external_prior(prior)
                priors.append(prior)
                rec = build_explainable_recommendation(prior, pat, ts)
                recommendations.append(rec)
                exp_prop = generate_experiment_proposal_from_prior(prior, pat, target_channel_id)
                experiment_proposals.append(exp_prop)

        # 6. Record Research Run
        completed_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        run_record = ResearchRunModel(
            run_id=run_id,
            target_channel_id=target_channel_id,
            channels_scanned=len(analog_channels),
            videos_analyzed=len(normalized_videos),
            patterns_discovered=len(patterns),
            priors_generated=len(priors),
            status=ResearchStatus.COMPLETED,
            is_simulation=is_simulation_run,
            started_at=start_time,
            completed_at=completed_time
        )
        self.repo.record_research_run(run_record)

        logging.info(
            f"[External Intelligence] Run '{run_id}' completed. Analyzed {len(normalized_videos)} videos across "
            f"{len(analog_channels)} channels. Discovered {len(patterns)} patterns, {len(priors)} priors."
        )

        return {
            "run_id": run_id,
            "target_channel_id": target_channel_id,
            "channels_scanned": len(analog_channels),
            "videos_analyzed": len(normalized_videos),
            "patterns": [p.to_dict() for p in patterns],
            "transferability_scores": [ts.to_dict() for ts in transferability_scores],
            "priors": [pr.to_dict() for pr in priors],
            "recommendations": recommendations,
            "experiment_proposals": experiment_proposals,
            "is_simulation": is_simulation_run,
            "completed_at": completed_time
        }
