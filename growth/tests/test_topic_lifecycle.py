# -*- coding: utf-8 -*-
"""
test_topic_lifecycle.py
------------------------
Unit tests for the topic lifecycle state machine.
"""

import gc
import tempfile
import unittest
from pathlib import Path
from growth.db.database import init_db
from growth.db.models import GrowthRepository, ChannelModel
from growth.topic_engine.topic_lifecycle import TopicLifecycleManager


class TestTopicLifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_lifecycle.db"
        init_db(self.db_path)
        self.repo = GrowthRepository(self.db_path)
        self.repo.upsert_channel(ChannelModel("channel_a", "Chronos Shift", "@ChronosShift", "p1", "History"))
        self.mgr = TopicLifecycleManager(self.db_path)

    def tearDown(self):
        del self.mgr
        del self.repo
        gc.collect()
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    def test_topic_discovery_and_queue(self):
        top_id = self.mgr.add_candidate_topic(
            "channel_a",
            "What if Rome conquered Ireland?",
            "Empire",
            "Classical"
        )
        self.assertTrue(top_id.startswith("top_"))

        queued = self.mgr.get_next_queued_topic("channel_a")
        self.assertIsNotNone(queued)
        self.assertEqual(queued["topic_id"], top_id)
        self.assertEqual(queued["status"], "QUEUED")

        # Advance lifecycle
        self.mgr.update_topic_status(top_id, "PRODUCED")
        produced = self.mgr.list_topics("channel_a", status="PRODUCED")
        self.assertEqual(len(produced), 1)

    def test_duplicate_rejection_in_lifecycle(self):
        self.mgr.add_candidate_topic("channel_a", "What if the Library of Alexandria survived?", "Knowledge")
        with self.assertRaises(ValueError):
            self.mgr.add_candidate_topic("channel_a", "What if the Library of Alexandria survived?", "Knowledge")


if __name__ == "__main__":
    unittest.main()
