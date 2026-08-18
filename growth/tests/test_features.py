# -*- coding: utf-8 -*-
"""
test_features.py
----------------
Unit tests for Pipeline 1 and Pipeline 2 feature extractors.
"""

import json
import tempfile
import unittest
from pathlib import Path
from growth.features.feature_extractor_p1 import extract_p1_features
from growth.features.feature_extractor_p2 import extract_p2_features


class TestFeatureExtractors(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_p1_feature_extraction(self):
        v_dir = self.root / "alexandria_01"
        v_dir.mkdir(parents=True)
        with open(v_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump({"title": "What If Alexandria Never Burned?"}, f)
        with open(v_dir / "scene_plan.json", "w", encoding="utf-8") as f:
            json.dump([
                {"scene_id": 0, "narration_text": "What if Ptolemy XIII never burned the Library of Alexandria?"},
                {"scene_id": 1, "narration_text": "Ancient scrolls preserved geometry."}
            ], f)
        with open(v_dir / "run_manifest.json", "w", encoding="utf-8") as f:
            json.dump({"metrics": {"duration": 48.0, "word_count": 110}}, f)

        feats = extract_p1_features("alexandria_01", self.root, topic_category="Ancient History")
        self.assertEqual(feats.video_id, "alexandria_01")
        self.assertEqual(feats.scene_count, 2)
        self.assertEqual(feats.hook_type, "Question/Provocation")
        self.assertEqual(feats.word_count, 110)
        self.assertEqual(feats.avg_scene_duration, 24.0)

    def test_p2_feature_extraction(self):
        manifest_file = self.root / "debate_01.manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump({
                "dialogue": [
                    {"speaker": "Host A", "text": "Why do you wake up at 3:17 AM every night?"},
                    {"speaker": "Host B", "text": "Is it because of cortisol spikes?"},
                    {"speaker": "Host A", "text": "Exactly, your brain enters micro-arousal."}
                ],
                "timing": {"duration": 40.0}
            }, f)

        feats = extract_p2_features("debate_01", manifest_file, topic_category="Psychology")
        self.assertEqual(feats.video_id, "debate_01")
        self.assertEqual(feats.turn_count, 3)
        self.assertEqual(feats.hook_type, "Polar Question")
        self.assertGreater(feats.speaker_balance, 0.0)


if __name__ == "__main__":
    unittest.main()
