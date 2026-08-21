# -*- coding: utf-8 -*-
"""
test_brain_backtester.py
------------------------
Unit and integration tests for BrainBacktester.
Validates hit rates, rank correlations, and baseline comparisons against external dataset.
"""

import unittest
import tempfile
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from growth.db.database import init_db
from growth.external_intelligence.repository import ExternalIntelligenceRepository
from growth.external_intelligence.dataset_builder import ExternalDatasetBuilder
from growth.brain.memory import BrainMemory
from growth.brain.backtester import BrainBacktester, BacktestReport


class TestBrainBacktester(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_backtest.db"
        init_db(self.db_path)

        self.ext_repo = ExternalIntelligenceRepository(self.db_path)
        self.builder = ExternalDatasetBuilder(self.ext_repo)
        # Populate dataset with 55 videos per channel
        self.builder.build_dataset(target_count_per_channel=55)

        self.memory = BrainMemory(self.db_path)
        self.backtester = BrainBacktester(self.ext_repo, self.memory)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_01_run_backtest_channel_a(self):
        """1. Executes historical backtest on Channel A analog videos."""
        report = self.backtester.run_backtest("channel_a", limit=50)
        self.assertIsInstance(report, BacktestReport)
        self.assertEqual(report.channel_id, "channel_a")
        self.assertTrue(report.total_candidates_evaluated > 0)
        self.assertTrue(0.0 <= report.top_10_hit_rate <= 1.0)
        self.assertTrue(0.0 <= report.top_20_hit_rate <= 1.0)
        self.assertTrue(-1.0 <= report.spearman_correlation <= 1.0)
        self.assertTrue(0.0 <= report.random_baseline_precision <= 1.0)
        self.assertTrue(0.0 <= report.calibration_score <= 1.0)

    def test_02_run_backtest_channel_b(self):
        """2. Executes historical backtest on Channel B analog videos."""
        report = self.backtester.run_backtest("channel_b", limit=50)
        self.assertIsInstance(report, BacktestReport)
        self.assertEqual(report.channel_id, "channel_b")
        self.assertTrue(report.total_candidates_evaluated > 0)
        self.assertTrue(0.0 <= report.top_10_hit_rate <= 1.0)

    def test_03_backtest_fallback_on_empty_data(self):
        """3. Handles empty database gracefully with baseline defaults."""
        empty_db = Path(self.tmp_dir.name) / "empty.db"
        init_db(empty_db)
        empty_ext_repo = ExternalIntelligenceRepository(empty_db)
        empty_memory = BrainMemory(empty_db)
        backtester = BrainBacktester(empty_ext_repo, empty_memory)

        report = backtester.run_backtest("channel_a")
        self.assertEqual(report.total_candidates_evaluated, 0)
        self.assertEqual(report.top_10_hit_rate, 0.0)


if __name__ == "__main__":
    unittest.main()
