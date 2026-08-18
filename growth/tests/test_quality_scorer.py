# -*- coding: utf-8 -*-
"""
test_quality_scorer.py
----------------------
Unit tests for the pre-upload content quality scorer.
"""

import unittest
from growth.quality.quality_scorer import evaluate_content_quality


class TestQualityScorer(unittest.TestCase):
    def test_high_quality_evaluation(self):
        feat = {"hook_score": 9.2, "avg_scene_duration": 5.2}
        qa = {"status": "PASS", "failed_count": 0}
        res = evaluate_content_quality(feat, qa, evidence_status="PREFERRED", is_duplicate=False)
        self.assertGreaterEqual(res["composite_quality_score"], 8.5)
        self.assertEqual(res["verdict"], "EXCELLENT")
        self.assertTrue(res["qa_passed"])

    def test_duplicate_penalization(self):
        feat = {"hook_score": 9.0, "avg_scene_duration": 5.0}
        qa = {"status": "PASS", "failed_count": 0}
        res = evaluate_content_quality(feat, qa, evidence_status="PREFERRED", is_duplicate=True)
        self.assertLess(res["composite_quality_score"], 9.0)
        self.assertEqual(res["dimension_scores"]["originality"], 4.0)


if __name__ == "__main__":
    unittest.main()
