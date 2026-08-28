# -*- coding: utf-8 -*-
"""
test_content_brain_v1_critic.py
---------------------------------
Unit and integration tests for Content Brain v1 Hybrid Script Critic,
P2 Multi-Angle Generator, and Causal Attribution Autopsies.
"""

import unittest
import tempfile
import json
from pathlib import Path
from growth.brain.script_critic import HybridScriptCritic, CriticEvaluationResult
from growth.brain.p2_multi_angle import generate_p2_multi_angle_concept
from growth.learning.autopsy_analyzer import generate_video_autopsy
from growth.strategy.strategy_manager import StrategyManager

class TestContentBrainV1Critic(unittest.TestCase):
    def setUp(self):
        self.critic = HybridScriptCritic()
        self.strategy_bounds = {
            "min_duration_seconds": 30.0,
            "max_duration_seconds": 55.0,
            "min_word_count": 60,
            "max_word_count": 135
        }

    def test_01_deterministic_word_count_and_duration_pass(self):
        script_data = {
            "scenes": [
                {"narration_text": "Here is why senior developers avoid running massive monolithic database instances for heavy read traffic in production."},
                {"narration_text": "Adding expensive CPU cores to a single primary database increases infrastructure cost without solving write lock contention."},
                {"narration_text": "Instead high scale systems deploy dedicated read replicas to handle all analytical and user query volume in parallel.", "code_snippet": ["db_read = connect_replica()"]},
                {"narration_text": "This clean architecture isolates write operations completely and guarantees sub-millisecond response latency under sudden traffic spikes."},
                {"narration_text": "Always scale your database queries horizontally with read replicas before touching vertical hardware compute limits."}
            ]
        }
        passed, errors, metrics = self.critic.evaluate_deterministic(
            script_data=script_data,
            strategy_bounds=self.strategy_bounds,
            speech_rate_wps=2.8
        )
        self.assertTrue(passed, f"Deterministic evaluation failed: {errors}")
        self.assertEqual(len(errors), 0)
        self.assertGreater(metrics["total_words"], 60)
        self.assertTrue(metrics["has_code_snippet"])

    def test_02_deterministic_fluff_rejection(self):
        fluff_script = {
            "scenes": [
                {"narration_text": "Welcome back hey guys in this video we are going to explore databases."},
                {"narration_text": "Databases are important for applications."},
                {"narration_text": "Make sure to comment your thoughts."}
            ]
        }
        passed, errors, metrics = self.critic.evaluate_deterministic(
            script_data=fluff_script,
            strategy_bounds=self.strategy_bounds
        )
        self.assertFalse(passed)
        self.assertTrue(any("Fluff intro detected" in e for e in errors))

    def test_03_structured_causal_attribution_autopsy(self):
        features = {
            "video_id": "vid_test_001",
            "hook_type": "Code Smell Trap",
            "topic_category": "System Design"
        }
        normalized_summary = {
            "raw_24h": {"avg_percentage_viewed": 89.5, "views_per_hour": 120.0},
            "normalized": {"composite_performance_score": 1.35, "retention_multiplier": 1.25, "view_multiplier": 1.40}
        }
        experiment_data = {
            "experiment_id": "EXP_P2_HOOK_004",
            "variable_tested": "HOOK_STRUCTURE",
            "arm_id": "treatment_code_first"
        }
        autopsy = generate_video_autopsy(
            video_id="vid_test_001",
            features=features,
            normalized_summary=normalized_summary,
            experiment_data=experiment_data
        )
        self.assertEqual(autopsy["performance_verdict"], "ABOVE_MEDIAN")
        self.assertIn("causal_attribution", autopsy)
        self.assertEqual(autopsy["causal_attribution"]["experiment_id"], "EXP_P2_HOOK_004")
        self.assertIn("learned_rule", autopsy)
        self.assertIn("Code Smell Trap", autopsy["learned_rule"])

    def test_05_critic_fails_closed_on_ollama_unavailable(self):
        # Point to invalid port to simulate network failure
        offline_critic = HybridScriptCritic(ollama_url="http://127.0.0.1:59999")
        script_data = {
            "scenes": [
                {"narration_text": "Here is why senior developers avoid running massive monolithic database instances for heavy read traffic in production."},
                {"narration_text": "Adding expensive CPU cores to a single primary database increases infrastructure cost without solving write lock contention."},
                {"narration_text": "Instead high scale systems deploy dedicated read replicas to handle all analytical and user query volume in parallel.", "code_snippet": ["db_read = connect_replica()"]},
                {"narration_text": "This clean architecture isolates write operations completely and guarantees sub-millisecond response latency under sudden traffic spikes."},
                {"narration_text": "Always scale your database queries horizontally with read replicas before touching vertical hardware compute limits."}
            ]
        }
        res = offline_critic.evaluate_script(
            topic="Database Sharding",
            script_data=script_data,
            channel_type="p2_coding",
            strategy_bounds=self.strategy_bounds
        )
        self.assertFalse(res.passed, "Critic must FAIL CLOSED when Ollama is unreachable!")
        self.assertFalse(res.tier2_semantic_passed)
        self.assertEqual(res.overall_score, 0.0)
        self.assertTrue(any("MANUAL_REVIEW_REQUIRED" in r for r in res.actionable_revisions))

    def test_06_strategy_immutable_versioning_on_learned_rule(self):
        sm = StrategyManager()
        new_ver = sm.record_learned_rule("channel_a", "Active question hooks boost 7d APV by +8%", "EXP_TEST_001")
        self.assertTrue(new_ver.startswith("v"))
        # Verify file exists
        p = sm.strategy_dir / f"channel_a_strategy_{new_ver}.json"
        self.assertTrue(p.exists())
        # Clean up temporary test strategy version
        try:
            p.unlink()
        except Exception:
            pass

if __name__ == "__main__":
    unittest.main()
