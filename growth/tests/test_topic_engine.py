# -*- coding: utf-8 -*-
"""
test_topic_engine.py
--------------------
Unit tests for topic scoring, deduplication, and topic pool portfolio management.
"""

import unittest
from growth.topic_engine.topic_scorer import score_topic
from growth.topic_engine.deduplicator import calculate_topic_similarity, is_duplicate_topic
from growth.topic_engine.topic_pool import TopicPoolManager


class TestTopicEngine(unittest.TestCase):
    def test_topic_scoring_explainability(self):
        res = score_topic("What if the Roman Empire never fell?", "channel_a", "Empire")
        self.assertGreater(res["final_score"], 0.70)
        self.assertIn("breakdown", res)
        self.assertIn("audience_fit", res["breakdown"])
        self.assertIn("reason", res)

    def test_deduplicator(self):
        topic_a = "What if the Roman Empire never fell?"
        topic_b = "What if the Roman Empire did not fall?"
        topic_c = "Why your brain forgets names in three seconds"

        sim_ab = calculate_topic_similarity(topic_a, topic_b)
        sim_ac = calculate_topic_similarity(topic_a, topic_c)

        self.assertGreaterEqual(sim_ab, 0.40)
        self.assertEqual(sim_ac, 0.0)

        is_dup, matched = is_duplicate_topic(topic_a, [topic_a])
        self.assertTrue(is_dup)

    def test_topic_pool_ranking(self):
        mgr_a = TopicPoolManager("channel_a")
        ranked_a = mgr_a.get_ranked_candidates()
        self.assertGreater(len(ranked_a), 0)
        # Verify descending order of scores
        scores = [item["score"] for item in ranked_a]
        self.assertEqual(scores, sorted(scores, reverse=True))

        # Test history filtering
        mgr_a.set_published_history(["What if the Roman Empire never fell?"])
        filtered_ranked = mgr_a.get_ranked_candidates()
        filtered_topics = [item["topic"] for item in filtered_ranked]
        self.assertNotIn("What if the Roman Empire never fell?", filtered_topics)


if __name__ == "__main__":
    unittest.main()
