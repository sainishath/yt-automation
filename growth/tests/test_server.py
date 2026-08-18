# -*- coding: utf-8 -*-
"""
test_server.py
--------------
Unit tests for the Growth Server REST API handlers.
"""

import gc
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from growth.db.database import init_db
from growth.db.models import GrowthRepository, ChannelModel
from growth.server import GrowthRequestHandler


class TestGrowthServer(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_server.db"
        init_db(self.db_path)
        self.repo = GrowthRepository(self.db_path)
        self.repo.upsert_channel(ChannelModel("channel_a", "Chronos Shift", "@ChronosShift", "p1", "History"))

    def tearDown(self):
        del self.repo
        gc.collect()
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    def test_handler_instantiation(self):
        # Verify handler class exists and has necessary route methods
        self.assertTrue(hasattr(GrowthRequestHandler, "do_GET"))
        self.assertTrue(hasattr(GrowthRequestHandler, "do_POST"))


if __name__ == "__main__":
    unittest.main()
