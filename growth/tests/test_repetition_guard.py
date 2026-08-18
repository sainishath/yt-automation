# -*- coding: utf-8 -*-
"""
test_repetition_guard.py
------------------------
Unit tests for the anti-repetition and originality engine.
"""

import unittest
from growth.topic_engine.repetition_guard import check_repetition, tokenize_clean, get_character_ngrams


class TestRepetitionGuard(unittest.TestCase):
    def setUp(self):
        self.history = [
            {
                "video_id": "vid_alexandria",
                "title": "What if the Library of Alexandria never burned?",
                "hook_text": "Imagine a world where centuries of ancient knowledge survived the flames."
            },
            {
                "video_id": "vid_rome",
                "title": "What if the Roman Empire never fell?",
                "hook_text": "If Roman legions held their borders against barbarian invasions."
            }
        ]

    def test_original_topic_allowed(self):
        res = check_repetition(
            candidate_title="What if the Industrial Revolution began in Song Dynasty China?",
            candidate_hook="What if steam-powered iron foundries transformed ancient China?",
            historical_entries=self.history
        )
        self.assertTrue(res["allowed"])
        self.assertEqual(res["similarity_score"], 0.0)

    def test_near_duplicate_title_rejected(self):
        res = check_repetition(
            candidate_title="What if Library of Alexandria never burned down?",
            candidate_hook="Imagine if ancient Alexandria scrolls survived.",
            historical_entries=self.history
        )
        self.assertFalse(res["allowed"])
        self.assertEqual(res["matched_video_id"], "vid_alexandria")

    def test_near_duplicate_hook_rejected(self):
        res = check_repetition(
            candidate_title="The Untouched Vaults of Egypt",
            candidate_hook="Imagine a world where centuries of ancient knowledge survived the flames.",
            historical_entries=self.history
        )
        self.assertFalse(res["allowed"])
        self.assertEqual(res["matched_video_id"], "vid_alexandria")


if __name__ == "__main__":
    unittest.main()
