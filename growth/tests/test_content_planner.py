# -*- coding: utf-8 -*-
"""
test_content_planner.py
-----------------------
Unit tests for the autonomous Content Planner.
"""

import gc
import tempfile
import unittest
from pathlib import Path
from growth.db.database import init_db
from growth.db.models import GrowthRepository, ChannelModel
from growth.planner.content_planner import ContentPlanner


class TestContentPlanner(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_planner.db"
        init_db(self.db_path)
        self.repo = GrowthRepository(self.db_path)
        self.planner = ContentPlanner(self.repo)

        self.repo.upsert_channel(ChannelModel("channel_a", "Chronos Shift", "@ChronosShift", "p1", "History"))
        self.repo.upsert_channel(ChannelModel("channel_b", "Debate Protocol", "@DebateProtocol", "p2", "Debate"))

    def tearDown(self):
        del self.planner
        del self.repo
        gc.collect()
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    def test_plan_next_video_channel_a(self):
        plan = self.planner.plan_next_video("channel_a")
        self.assertEqual(plan["channel_id"], "channel_a")
        self.assertEqual(plan["pipeline_id"], "alternate-history-shorts")
        self.assertIn("topic", plan)
        self.assertIn("strategy_version", plan)
        self.assertEqual(plan["strategy_version"], "v1.0")
        self.assertIn("experiment_id", plan)
        self.assertEqual(plan["status"], "PLANNED")

    def test_plan_next_video_channel_b(self):
        plan = self.planner.plan_next_video("channel_b")
        self.assertEqual(plan["channel_id"], "channel_b")
        self.assertEqual(plan["pipeline_id"], "convo-shorts")
        self.assertIn("topic", plan)
        self.assertEqual(plan["status"], "PLANNED")


if __name__ == "__main__":
    unittest.main()
