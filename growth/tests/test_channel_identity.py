# -*- coding: utf-8 -*-
"""
test_channel_identity.py
------------------------
Unit tests for channel identity verification and mismatch enforcement.
"""

import unittest
from growth.channels.channel_identity_check import (
    load_channel_config, verify_channel_identity, enforce_channel_match
)


class TestChannelIdentity(unittest.TestCase):
    def test_load_channel_configs(self):
        cfg1 = load_channel_config("pipeline1")
        self.assertEqual(cfg1["channel_id"], "channel_a")
        self.assertEqual(cfg1["channel_name"], "Chronos Shift")

        cfg2 = load_channel_config("pipeline2")
        self.assertEqual(cfg2["channel_id"], "channel_b")
        self.assertEqual(cfg2["channel_name"], "Debate Protocol")

    def test_verify_identity_match(self):
        cfg1 = load_channel_config("pipeline1")
        res = verify_channel_identity(
            "pipeline1",
            authenticated_channel_id=cfg1["expected_youtube_channel_id"],
            authenticated_channel_name="sai nishath",
            allow_placeholder=True
        )
        self.assertEqual(res["verdict"], "MATCH")

    def test_mismatch_rejection(self):
        # When placeholder is not allowed, mismatch must return MISMATCH and enforce_channel_match must raise
        res = verify_channel_identity(
            "pipeline1",
            authenticated_channel_id="UC_WRONG_CHANNEL_ID",
            authenticated_channel_name="Wrong Channel",
            allow_placeholder=False
        )
        self.assertEqual(res["verdict"], "MISMATCH")

        with self.assertRaises(RuntimeError):
            enforce_channel_match(
                "pipeline1",
                authenticated_channel_id="UC_WRONG_CHANNEL_ID",
                authenticated_channel_name="Wrong Channel"
            )


if __name__ == "__main__":
    unittest.main()
