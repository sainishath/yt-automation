# -*- coding: utf-8 -*-
"""
test_strategy.py
----------------
Unit tests for strategy loading, schema compliance, and version isolation.
"""

import unittest
from growth.strategy.strategy_manager import StrategyManager


class TestStrategyManager(unittest.TestCase):
    def setUp(self):
        self.mgr = StrategyManager()

    def test_load_channel_a_strategy(self):
        strat_a = self.mgr.get_active_strategy("channel_a")
        self.assertEqual(strat_a["channel_id"], "channel_a")
        self.assertEqual(strat_a["strategy_version"], "v1.0")
        self.assertIn("winning_patterns", strat_a)

    def test_load_channel_b_strategy(self):
        strat_b = self.mgr.get_active_strategy("channel_b")
        self.assertEqual(strat_b["channel_id"], "channel_b")
        self.assertEqual(strat_b["strategy_version"], "v1.0")
        self.assertIn("winning_patterns", strat_b)

    def test_strategy_validation(self):
        strat_a = self.mgr.get_active_strategy("channel_a")
        plan = {"duration": 45.0}
        res = self.mgr.validate_strategy_compatibility(plan, strat_a)
        self.assertEqual(res["status"], "COMPLIANT")
        self.assertTrue(res["duration_fit"])

        plan_long = {"duration": 90.0}
        res_long = self.mgr.validate_strategy_compatibility(plan_long, strat_a)
        self.assertEqual(res_long["status"], "ADVISORY_DEVIATION")
        self.assertFalse(res_long["duration_fit"])


if __name__ == "__main__":
    unittest.main()
