# -*- coding: utf-8 -*-
"""
test_outlier_analyzer.py
------------------------
Unit tests for the viral outlier analyzer.
"""

import unittest
from growth.analytics.outlier_analyzer import analyze_performance_outlier


class TestOutlierAnalyzer(unittest.TestCase):
    def setUp(self):
        self.baseline = {
            "median_views_24h": 1000.0,
            "median_avg_percentage_viewed": 85.0
        }

    def test_normal_video_not_outlier(self):
        snap = {"views": 1400, "avg_percentage_viewed": 86.0}
        res = analyze_performance_outlier(snap, self.baseline)
        self.assertFalse(res["is_outlier"])
        self.assertEqual(res["signal_type"], "NORMAL_DISTRIBUTION")

    def test_repeatable_viral_outlier(self):
        snap = {"views": 5000, "avg_percentage_viewed": 91.0}
        res = analyze_performance_outlier(snap, self.baseline)
        self.assertTrue(res["is_outlier"])
        self.assertEqual(res["view_multiplier"], 5.0)
        self.assertEqual(res["capped_view_multiplier"], 3.0)
        self.assertEqual(res["signal_type"], "REPEATABLE_FORMAT_AND_TOPIC_SIGNAL")

    def test_isolated_click_spike_outlier(self):
        snap = {"views": 4500, "avg_percentage_viewed": 72.0}
        res = analyze_performance_outlier(snap, self.baseline)
        self.assertTrue(res["is_outlier"])
        self.assertEqual(res["signal_type"], "ISOLATED_ALGORITHMIC_OR_CLICK_SPIKE")
        self.assertEqual(res["learning_action"], "CAP_MULTIPLIER_AND_EXPLORE_CAUTIOUSLY")


if __name__ == "__main__":
    unittest.main()
