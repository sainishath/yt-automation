# -*- coding: utf-8 -*-
"""
test_external_intelligence.py
------------------------------
Comprehensive unit test suite for the External Intelligence subsystem.
Verifies similarity scoring, observation extraction, pattern mining, transferability,
bounded external priors, and strict First-Party Evidence Dominance.
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
    ExternalPatternModel,
    TransferabilityScoreModel,
    ExternalPriorModel,
    PriorStatus,
    TransferabilityClassification,
    PatternType,
    ProvenanceSource
)
from growth.external_intelligence.repository import ExternalIntelligenceRepository
from growth.external_intelligence.channel_registry import (
    calculate_channel_similarity,
    get_analog_channels_for_target
)
from growth.external_intelligence.feature_extractor import (
    extract_title_facts,
    infer_title_interpretations,
    normalize_external_video_views,
    build_observations_for_video
)
from growth.external_intelligence.pattern_miner import mine_patterns_from_videos
from growth.external_intelligence.transferability import evaluate_pattern_transferability
from growth.external_intelligence.prior_engine import (
    generate_prior_from_transferability,
    apply_first_party_override
)
from growth.external_intelligence.recommendation_engine import (
    generate_experiment_proposal_from_prior,
    build_explainable_recommendation
)
from growth.external_intelligence.researcher import ExternalResearcher
from growth.external_intelligence.research_reports import generate_external_intelligence_markdown_report


class TestExternalIntelligenceSuite(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_ext_suite.db"
        init_db(self.db_path)

        growth_repo = GrowthRepository(self.db_path)
        growth_repo.upsert_channel(ChannelModel(
            channel_id="channel_a",
            name="Chronos Shift",
            handle="@ChronosShiftAI",
            pipeline_id="alternate-history-shorts",
            content_category="Education/History"
        ))
        growth_repo.upsert_channel(ChannelModel(
            channel_id="channel_b",
            name="Debate Protocol",
            handle="@DebateProtocol",
            pipeline_id="convo-shorts",
            content_category="Education/Entertainment"
        ))
        self.repo = ExternalIntelligenceRepository(self.db_path)
        self.researcher = ExternalResearcher(repo=self.repo)

    def tearDown(self):
        gc.collect()
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    def test_channel_similarity_scoring(self):
        metrics = {
            "topic_similarity": 0.95,
            "audience_similarity": 0.90,
            "format_similarity": 0.95,
            "duration_similarity": 0.90,
            "storytelling_similarity": 0.95,
            "production_similarity": 0.85
        }
        res = calculate_channel_similarity(metrics)
        self.assertGreaterEqual(res["similarity_score"], 0.90)
        self.assertEqual(res["confidence"], "HIGH")
        self.assertGreater(len(res["similarity_reasons"]), 0)

    def test_fact_vs_interpretation_separation(self):
        title = "What if the Roman Empire Never Fell?"
        facts = extract_title_facts(title)
        self.assertTrue(facts["starts_what_if"])
        self.assertTrue(facts["has_question_mark"])
        self.assertEqual(facts["title_word_count"], 7)

        interp = infer_title_interpretations(title, facts)
        self.assertEqual(interp["hook_type"], "COUNTERFACTUAL_QUESTION")
        self.assertEqual(interp["topic_cluster"], "ANCIENT_EMPIRES_AND_TURNING_POINTS")
        self.assertGreaterEqual(interp["confidence"], 0.90)

    def test_baseline_view_normalization_and_outlier_cap(self):
        vids = [
            ExternalVideoModel(external_video_id="v1", external_channel_id="c1", youtube_video_id="y1", title="T1", url="u1", views=1000),
            ExternalVideoModel(external_video_id="v2", external_channel_id="c1", youtube_video_id="y2", title="T2", url="u2", views=2000),
            ExternalVideoModel(external_video_id="v3", external_channel_id="c1", youtube_video_id="y3", title="T3", url="u3", views=10000) # Outlier
        ]
        norm = normalize_external_video_views(vids, outlier_cap_multiplier=3.0)
        # Median is 2000. v1=0.5x, v2=1.0x, v3=5.0x capped to 3.0x
        self.assertEqual(norm[0].relative_view_multiplier, 0.5)
        self.assertEqual(norm[1].relative_view_multiplier, 1.0)
        self.assertEqual(norm[2].relative_view_multiplier, 3.0)

    def test_pattern_mining_and_corroboration(self):
        vids = self.researcher._get_curated_public_fixtures("channel_a")
        norm_vids = normalize_external_video_views(vids)
        patterns = mine_patterns_from_videos("channel_a", norm_vids)
        self.assertGreater(len(patterns), 0)

        counterfactual_pat = next((p for p in patterns if "COUNTERFACTUAL" in p.name.upper()), None)
        self.assertIsNotNone(counterfactual_pat)
        self.assertGreaterEqual(counterfactual_pat.channel_count, 1)
        self.assertGreater(len(counterfactual_pat.underlying_principle), 10)

    def test_transferability_classification(self):
        pat_high = ExternalPatternModel(
            pattern_id="pat_test_01",
            target_channel_id="channel_a",
            pattern_type=PatternType.HOOK_STRUCTURE,
            name="Ancient Turning Point Counterfactual Question",
            description="Counterfactual question opening",
            surface_technique="What if question",
            underlying_principle="Cognitive dissonance and alternate world curiosity",
            our_possible_implementation="RAG-grounded historical divergence in Beat #0",
            confidence=0.90,
            consistency_score=0.85
        )
        score = evaluate_pattern_transferability(pat_high, "channel_a")
        self.assertEqual(score.classification, TransferabilityClassification.HIGH)
        self.assertGreaterEqual(score.overall_transferability_score, 0.80)

        # Incompatible talking head pattern
        pat_incompatible = ExternalPatternModel(
            pattern_id="pat_test_02",
            target_channel_id="channel_a",
            pattern_type=PatternType.HOOK_STRUCTURE,
            name="Talking Head Jump Cuts",
            description="Presenter talking directly to camera",
            surface_technique="Live-action talking_head presentation",
            underlying_principle="Presenter personality",
            our_possible_implementation="None",
            confidence=0.80,
            consistency_score=0.70
        )
        score_incomp = evaluate_pattern_transferability(pat_incompatible, "channel_a")
        self.assertIn(score_incomp.classification, [TransferabilityClassification.LOW, TransferabilityClassification.DO_NOT_TRANSFER])

    def test_first_party_dominance_overrides_external_prior(self):
        """
        CRITICAL ARCHITECTURAL TEST:
        External prior suggests technique X (+15% expected).
        Our empirical experiment (N=4) proves technique X underperformed by -7.5%.
        Result: External prior MUST be rejected and override reason logged.
        """
        pat = ExternalPatternModel(
            pattern_id="pat_provocation_test",
            target_channel_id="channel_b",
            pattern_type=PatternType.HOOK_STRUCTURE,
            name="Extreme Direct Provocation Hook",
            description="Aggressive opening",
            surface_technique="Accusatory statement",
            underlying_principle="Viewer agitation",
            our_possible_implementation="Aggressive opening claim",
            confidence=0.85,
            consistency_score=0.80
        )
        ts = TransferabilityScoreModel(
            transferability_id="ts_prov_01",
            pattern_id="pat_provocation_test",
            target_channel_id="channel_b",
            topic_similarity=0.90, audience_similarity=0.90, format_similarity=0.90,
            production_similarity=0.90, evidence_strength=0.85, repeatability=0.80,
            overall_transferability_score=0.88,
            classification=TransferabilityClassification.HIGH,
            reason="High alignment"
        )
        prior = generate_prior_from_transferability(pat, ts)
        self.assertEqual(prior.status, PriorStatus.HYPOTHESIS)
        self.assertGreater(prior.prior_weight, 0.0)

        # Simulated empirical first-party test results (N=4, negative delta -7.5%)
        first_party_result = {
            "decision": "REJECT_VARIANT",
            "verdict": "CONTROL_OUTPERFORMS_VARIANT",
            "control_count": 4,
            "variant_count": 4,
            "delta_percentage": -7.5
        }

        updated_prior = apply_first_party_override(prior, first_party_result)
        self.assertEqual(updated_prior.status, PriorStatus.REJECTED)
        self.assertEqual(updated_prior.prior_weight, 0.0)
        self.assertIn("First-party empirical test (N=4) contradicted external prior", updated_prior.first_party_override_reason)

    def test_experiment_proposal_generation(self):
        pat = ExternalPatternModel(
            pattern_id="pat_ext_hook_a",
            target_channel_id="channel_a",
            pattern_type=PatternType.HOOK_STRUCTURE,
            name="Ancient Empire Survival Hook",
            description="Rome survival hook",
            surface_technique="If Rome survived...",
            underlying_principle="Technological acceleration in ancient times",
            our_possible_implementation="Active counterfactual conditional thesis in Beat 0",
            channel_count=3,
            video_count=12,
            confidence=0.88
        )
        ts = evaluate_pattern_transferability(pat, "channel_a")
        prior = generate_prior_from_transferability(pat, ts)
        self.assertIsNotNone(prior)

        exp_prop = generate_experiment_proposal_from_prior(prior, pat, "channel_a")
        self.assertEqual(exp_prop["min_sample_size"], 4)
        self.assertEqual(exp_prop["primary_metric"], "avg_percentage_viewed")
        self.assertIn("EXP_A_EXT_", exp_prop["experiment_id"])

    def test_end_to_end_research_orchestration_and_reporting(self):
        res_a = self.researcher.run_channel_research("channel_a", use_live_api=False)
        self.assertEqual(res_a["target_channel_id"], "channel_a")
        self.assertGreater(res_a["videos_analyzed"], 0)
        self.assertGreater(len(res_a["patterns"]), 0)
        self.assertGreater(len(res_a["priors"]), 0)

        res_b = self.researcher.run_channel_research("channel_b", use_live_api=False)
        self.assertEqual(res_b["target_channel_id"], "channel_b")
        self.assertGreater(res_b["videos_analyzed"], 0)

        # Generate markdown report
        report_text = generate_external_intelligence_markdown_report(res_a, res_b)
        self.assertIn("# External Intelligence & Analog Channel Research Report", report_text)
        self.assertIn("First-Party Evidence Dominance", report_text)
        self.assertIn("What is NOT Transferable", report_text)


if __name__ == "__main__":
    unittest.main()
