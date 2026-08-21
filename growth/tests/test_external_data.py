# -*- coding: utf-8 -*-
"""
test_external_data.py
---------------------
Unit tests for the External Intelligence data foundation, schemas, constraints, and repository layer.
"""

import gc
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from growth.db.database import init_db
from growth.db.models import GrowthRepository, ChannelModel
from growth.external_intelligence.schemas import (
    ExternalChannelModel,
    ExternalVideoModel,
    ExternalObservationModel,
    ExternalPatternModel,
    TransferabilityScoreModel,
    ExternalPriorModel,
    ResearchRunModel,
    ProvenanceSource,
    ObservationType,
    EvidenceLevel,
    TransferabilityClassification,
    PriorStatus,
    PatternType,
    ResearchStatus,
)
from growth.external_intelligence.repository import ExternalIntelligenceRepository


class TestExternalDataFoundation(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_ext.db"
        init_db(self.db_path)

        # Seed target channel
        growth_repo = GrowthRepository(self.db_path)
        growth_repo.upsert_channel(ChannelModel(
            channel_id="channel_a",
            name="Chronos Shift",
            handle="@ChronosShiftAI",
            pipeline_id="alternate-history-shorts",
            content_category="Education/History"
        ))
        self.repo = ExternalIntelligenceRepository(self.db_path)

    def tearDown(self):
        gc.collect()
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    def test_external_channel_upsert_and_retrieval(self):
        ch = ExternalChannelModel(
            external_channel_id="ext_ch_001",
            target_channel_id="channel_a",
            channel_title="History Counterfactuals Hub",
            handle="@HistHub",
            youtube_channel_id="UC_EXT_123",
            subscriber_count=250000,
            video_count=180,
            content_niche="Alternate History Shorts",
            similarity_score=0.88,
            similarity_reasons=["High topic overlap in Rome and WW2", "Shorts duration 40-50s"],
            confidence="HIGH",
            is_simulation=False,
            source_type=ProvenanceSource.PUBLIC_YOUTUBE
        )
        self.repo.upsert_external_channel(ch)

        retrieved = self.repo.get_external_channel("ext_ch_001")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["channel_title"], "History Counterfactuals Hub")
        self.assertEqual(retrieved["similarity_score"], 0.88)
        self.assertFalse(retrieved["is_simulation"])
        self.assertEqual(retrieved["source_type"], "PUBLIC_YOUTUBE")
        self.assertEqual(len(retrieved["similarity_reasons"]), 2)

    def test_external_video_and_observation_lifecycle(self):
        ch = ExternalChannelModel(
            external_channel_id="ext_ch_002",
            target_channel_id="channel_a",
            channel_title="Speculative History",
            content_niche="History Shorts"
        )
        self.repo.upsert_external_channel(ch)

        vid = ExternalVideoModel(
            external_video_id="ext_vid_001",
            external_channel_id="ext_ch_002",
            youtube_video_id="yt_ext_vid_99",
            title="What if the Library of Alexandria Never Burned?",
            url="https://youtube.com/shorts/yt_ext_vid_99",
            duration_seconds=44.5,
            is_short=True,
            views=120000,
            likes=9500,
            comments=420,
            relative_view_multiplier=2.1,
            is_simulation=False,
            source_type=ProvenanceSource.PUBLIC_YOUTUBE
        )
        self.repo.upsert_external_video(vid)

        # Level 1 Observation (Fact)
        obs_fact = ExternalObservationModel(
            observation_id="obs_001",
            external_video_id="ext_vid_001",
            observation_type=ObservationType.OBJECTIVE_FACT,
            field_name="hook_text",
            observed_value="What if the Library of Alexandria never burned?",
            evidence_level=EvidenceLevel.LEVEL_1_OBSERVATION,
            confidence=1.0,
            is_simulation=False,
            source_type=ProvenanceSource.PUBLIC_YOUTUBE
        )
        self.repo.insert_observation(obs_fact)

        # Level 2 Observation (Interpretation)
        obs_interp = ExternalObservationModel(
            observation_id="obs_002",
            external_video_id="ext_vid_001",
            observation_type=ObservationType.INTERPRETATION,
            field_name="hook_structure",
            observed_value="Polar Counterfactual Question",
            interpretation="Sparks immediate cognitive counterfactual curiosity",
            evidence_level=EvidenceLevel.LEVEL_2_EXTERNAL_EVIDENCE,
            confidence=0.90,
            is_simulation=False,
            source_type=ProvenanceSource.PUBLIC_YOUTUBE
        )
        self.repo.insert_observation(obs_interp)

        observations = self.repo.list_observations_by_video("ext_vid_001")
        self.assertEqual(len(observations), 2)
        fact_item = next(o for o in observations if o["observation_type"] == "OBJECTIVE_FACT")
        interp_item = next(o for o in observations if o["observation_type"] == "INTERPRETATION")
        self.assertEqual(fact_item["field_name"], "hook_text")
        self.assertIn("cognitive", interp_item["interpretation"])

    def test_pattern_and_transferability_lifecycle(self):
        pat = ExternalPatternModel(
            pattern_id="pat_counterfactual_hook_01",
            target_channel_id="channel_a",
            pattern_type=PatternType.HOOK_STRUCTURE,
            name="Ancient Turning Point Counterfactual Question",
            description="Opening video with 'What if [Ancient Event] never happened?'",
            surface_technique="What if question opening",
            underlying_principle="Cognitive dissonance and counterfactual divergence curiosity",
            our_possible_implementation="RAG-grounded historical divergence hook with 0 unsupported claims",
            frequency=0.74,
            channel_count=5,
            video_count=42,
            supporting_observations=["obs_001", "obs_002"],
            consistency_score=0.85,
            confidence=0.92,
            is_simulation=False,
            source_type=ProvenanceSource.PUBLIC_YOUTUBE
        )
        self.repo.upsert_pattern(pat)

        score = TransferabilityScoreModel(
            transferability_id="ts_pat_001",
            pattern_id="pat_counterfactual_hook_01",
            target_channel_id="channel_a",
            topic_similarity=0.95,
            audience_similarity=0.90,
            format_similarity=0.95,
            production_similarity=0.85,
            evidence_strength=0.90,
            repeatability=0.88,
            overall_transferability_score=0.91,
            classification=TransferabilityClassification.HIGH,
            reason="Direct 1:1 match in historical niche, format, and pacing."
        )
        self.repo.upsert_transferability_score(score)

        prior = ExternalPriorModel(
            prior_id="prior_hook_001",
            target_channel_id="channel_a",
            pattern_id="pat_counterfactual_hook_01",
            hypothesis="Opening with an Ancient Turning Point Counterfactual question will increase 24h retention by >= 5%.",
            transferability_classification=TransferabilityClassification.HIGH,
            prior_weight=0.25,
            status=PriorStatus.HYPOTHESIS
        )
        self.repo.upsert_external_prior(prior)

        priors = self.repo.list_external_priors("channel_a")
        self.assertEqual(len(priors), 1)
        self.assertEqual(priors[0]["status"], "HYPOTHESIS")
        self.assertEqual(priors[0]["prior_weight"], 0.25)

        # Update prior upon testing
        self.repo.update_prior_status("prior_hook_001", PriorStatus.TESTING)
        updated_priors = self.repo.list_external_priors("channel_a", status="TESTING")
        self.assertEqual(len(updated_priors), 1)
        self.assertEqual(updated_priors[0]["status"], "TESTING")


if __name__ == "__main__":
    unittest.main()
