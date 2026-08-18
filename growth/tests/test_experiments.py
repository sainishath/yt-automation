# -*- coding: utf-8 -*-
"""
test_experiments.py
-------------------
Unit tests for the experiment framework and statistical sample size guards.
"""

import unittest
from growth.experiments.experiment_manager import ExperimentManager


class TestExperimentManager(unittest.TestCase):
    def setUp(self):
        self.mgr = ExperimentManager()

    def test_insufficient_sample_size(self):
        # 2 samples each vs min 4 required
        ctrl = [80.0, 82.0]
        var = [85.0, 87.0]
        res = self.mgr.evaluate_experiment("EXP_A_HOOK_01", ctrl, var)
        self.assertEqual(res["status"], "INSUFFICIENT_DATA")
        self.assertEqual(res["verdict"], "COLLECTING_MORE_SAMPLES")

    def test_variant_outperforms_control(self):
        # 4 samples each, variant median higher by > 5%
        ctrl = [78.0, 80.0, 81.0, 82.0] # median 80.5
        var = [88.0, 89.0, 90.0, 92.0]  # median 89.5
        res = self.mgr.evaluate_experiment("EXP_A_HOOK_01", ctrl, var)
        self.assertEqual(res["status"], "EVALUATED")
        self.assertEqual(res["decision"], "ACCEPT_VARIANT")
        self.assertEqual(res["confidence"], "HIGH")

    def test_inconclusive_experiment(self):
        # 4 samples each, very close medians
        ctrl = [80.0, 81.0, 82.0, 83.0]
        var = [80.5, 81.5, 82.0, 82.5]
        res = self.mgr.evaluate_experiment("EXP_A_HOOK_01", ctrl, var)
        self.assertEqual(res["decision"], "INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main()
