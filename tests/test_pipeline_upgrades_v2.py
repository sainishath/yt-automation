# -*- coding: utf-8 -*-
"""
tests/test_pipeline_upgrades_v2.py
----------------------------------
Unit and integration tests for the v2 Pipeline Upgrades calibrated to the @sainishath4220 forensic audit:
1. Anti-Repetition, Anti-Hedging & Entity Cap Script Gate (Module A: pipeline/verify_claims.py)
2. Two-Phase Counterfactual RAG Verifier (Module A: pipeline/verify_claims.py)
3. Fooocus SDXL Negative Prompt Lock & Split-Panel Collage QA Gate (Module B: pipeline/compositor.py)
4. Mobile-Safe Shorts Subtitles (MarginV=620, 72pt bold yellow/white) (Module B: pipeline/compositor.py & assemble_video.py)
5. Compliant YouTube API Upload, Synthetic Media Disclosure & RAG Citations (Module C: pipeline/upload_guard.py)
6. Counterfactual Divergence Pre-Check & 6-Step Outlier Title Rubric (growth/scorer.py & growth/topic_engine/topic_scorer.py)
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import cv2
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(ROOT_DIR / "alternate-history-shorts" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "alternate-history-shorts" / "scripts"))

import yt_automations_pipeline_upgrades as root_upgrades
from pipeline.verify_claims import (
    BANNED_HEDGING_AND_FILLER_PATTERNS,
    audit_script_quality,
    verify_counterfactual_beats_deterministic,
    verify_counterfactual_script_with_cloud_llm,
)
from pipeline.compositor import (
    FOOOCUS_NEGATIVE_PROMPT_LOCK,
    MOTION_TRAJECTORIES,
    SAFE_SHORTS_ASS_HEADER,
    SAFE_SHORTS_ASS_STYLE,
    build_fooocus_scene_prompt,
    detect_split_panel_collage,
)
from pipeline.upload_guard import (
    append_rag_citations_to_description,
    build_youtube_insert_body,
    send_discord_alert,
)
from growth.scorer import (
    check_counterfactual_divergence,
    evaluate_6step_outlier_title_rubric,
)
from growth.topic_engine.topic_scorer import score_topic
from assemble_video import align_and_generate_ass
from generate_script import (
    deduplicate_script_ngrams,
    extract_primary_title_entity,
    validate_and_enrich_script,
    verify_and_revise_script_claims,
)
from generate_images import validate_image, generate_pillow_proof_image
from visual_scene_planner import build_fallback_scene_plan, clean_visual_prompt_string


class TestPipelineUpgradesV2(unittest.TestCase):
    def test_01_audit_script_quality_catches_egypt_duplicate_loop(self):
        egypt_beats = [
            "The Great Pyramid of Giza was commissioned by Pharaoh Khufu during the fourth dynasty.",
            "The Great Pyramid of Giza was commissioned by Pharaoh Khufu during the fourth dynasty of Egypt.",
            "Workers hauled limestone blocks across the desert sands.",
        ]
        res = audit_script_quality(egypt_beats, "Great Pyramid of Giza")
        self.assertFalse(res["passed"])
        self.assertTrue(any("word overlap" in issue for issue in res["issues"]))

    def test_02_audit_script_quality_catches_rome_hedging_and_entity_spam(self):
        rome_beats = [
            "Imagine if the Roman Empire had survived into the modern world.",
            "The Roman Empire might have industrialized centuries earlier.",
            "The Roman Empire could have potentially colonized the Americas.",
            "It is possible that the Roman Empire would rule Europe today.",
            "Join us as we explore how the Roman Empire changed history.",
        ]
        res = audit_script_quality(rome_beats, "Roman Empire")
        self.assertFalse(res["passed"])
        self.assertTrue(any("hedging/filler" in issue for issue in res["issues"]))
        self.assertTrue(any("repeated" in issue for issue in res["issues"]))

    def test_03_audit_script_quality_passes_clean_present_tense_script(self):
        clean_beats = [
            "It is November 1942. German Sixth Army panzers shatter the Volga riverbanks and seize Stalingrad.",
            "With the river artery severed, General Paulus locks down the southern Caucasus rail corridor.",
            "By spring 1943, Axis armored columns capture the Baku oil fields, starving Red Army depots of fuel.",
            "Fueled by Caspian crude, Luftwaffe squadrons fortify the Ural frontier across Eurasia.",
            "With the Volga lost in 1942, does Moscow sue for peace or fight from Siberia?",
        ]
        res = audit_script_quality(clean_beats, "Stalingrad")
        self.assertTrue(res["passed"], f"Unexpected issues: {res['issues']}")
        self.assertEqual(len(res["issues"]), 0)

    def test_04_two_phase_counterfactual_verifier_catches_stalingrad_real_history_contradiction(self):
        contradictory_beats = [
            "In winter 1942, German forces launched a massive offensive against Stalingrad on the Volga.",
            "General Paulus pushed the Sixth Army into the industrial heart of the ruined city.",
            "Fierce street fighting raged across the tractor factory and Mamayev Kurgan.",
            "In the end, it was the Soviet Union that emerged victorious, marking a turning point in World War II.",
        ]
        audit = verify_counterfactual_beats_deterministic(
            "What If Nazi Germany Captured Stalingrad?", contradictory_beats
        )
        self.assertFalse(audit.avoids_real_history_ending_contradiction)
        self.assertFalse(audit.answers_title_what_if_premise)
        self.assertFalse(audit.beat_audits[-1].is_valid)
        self.assertTrue(len(audit.beat_audits[-1].rewritten_beat_if_invalid) > 20)

    def test_05_split_panel_collage_detector_catches_horizontal_divider_and_passes_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            # 1. Create a synthetic image with natural texture (should PASS -> detect_split_panel_collage == False)
            rng = np.random.default_rng(123)
            clean_img = rng.integers(30, 220, size=(384, 216), dtype=np.uint8)
            clean_path = Path(tmp) / "clean_single_frame.png"
            cv2.imwrite(str(clean_path), clean_img)
            self.assertFalse(detect_split_panel_collage(str(clean_path)))

            # 2. Inject a solid horizontal split-panel divider bar in the center (should FAIL -> True)
            collage_img = clean_img.copy()
            collage_img[190:196, :] = 255  # Solid white divider bar across full width
            collage_path = Path(tmp) / "split_panel_collage.png"
            cv2.imwrite(str(collage_path), collage_img)
            self.assertTrue(detect_split_panel_collage(str(collage_path)))
            self.assertTrue(root_upgrades.detect_split_panel_collage(str(collage_path)))

    def test_06_fooocus_prompt_lock_blocks_mandalorian_and_gibberish_text(self):
        payload = build_fooocus_scene_prompt("Roman centurion holding banner in snow", "Ancient Rome 100 AD")
        self.assertIn("Single full-bleed vertical 9:16 cinematic photograph", payload["prompt"])
        self.assertIn("no text, no split screen", payload["prompt"])
        for banned in ["mandalorian helmet", "T-visor helmet", "split screen", "gibberish text", "modern ballpoint pen"]:
            self.assertIn(banned, payload["negative_prompt"])

    def test_07_safe_shorts_ass_subtitles_margin_v_620(self):
        self.assertIn("620,1", SAFE_SHORTS_ASS_STYLE)
        self.assertIn("620,1", SAFE_SHORTS_ASS_HEADER)

        whisper_words = [
            {"word": "German", "start": 0.0, "end": 0.4},
            {"word": "panzers", "start": 0.4, "end": 0.9},
            {"word": "seize", "start": 0.9, "end": 1.3},
            {"word": "Stalingrad.", "start": 1.3, "end": 2.0},
        ]
        ass_text = align_and_generate_ass(whisper_words, "German panzers seize Stalingrad.", {})
        self.assertIn(",80,80,620,1", ass_text)
        self.assertIn("&H0000FFFF", ass_text)

    def test_08_youtube_insert_body_and_rag_citations(self):
        evidence_packet = {
            "sources": [
                {
                    "title": "Battle of Stalingrad",
                    "publisher": "Wikimedia Foundation (Wikipedia)",
                    "url": "https://en.wikipedia.org/wiki/Battle_of_Stalingrad",
                }
            ]
        }
        body = build_youtube_insert_body(
            title="What If Nazi Germany Captured Stalingrad?",
            description="In November 1942, the Volga falls.",
            tags=["stalingrad", "history", "what if"],
            category_id="27",
            evidence_packet=evidence_packet,
        )
        self.assertEqual(body["snippet"]["categoryId"], "27")
        self.assertTrue(body["status"]["containsSyntheticMedia"])
        self.assertFalse(body["status"]["selfDeclaredMadeForKids"])
        self.assertIn("Historical Sources & References (RAG Verified):", body["snippet"]["description"])
        self.assertIn("https://en.wikipedia.org/wiki/Battle_of_Stalingrad", body["snippet"]["description"])

    def test_09_counterfactual_divergence_precheck_blocks_berlin_wall_tautology(self):
        # Real history disguised as What-If (Short #5 bug)
        bad_berlin = check_counterfactual_divergence("What If a Single Wall Divided East and West Berlin?")
        self.assertFalse(bad_berlin["is_valid_counterfactual"])

        # Vague clickbait without divergence (Short #2 bug)
        bad_egypt = check_counterfactual_divergence("What If Ancient Egypt Built a Pyramid Like This?")
        self.assertFalse(bad_egypt["is_valid_counterfactual"])

        # True counterfactual divergences
        good_rome = check_counterfactual_divergence("What If the Roman Empire Never Fell?")
        self.assertTrue(good_rome["is_valid_counterfactual"])

        good_stalingrad = check_counterfactual_divergence("What If Nazi Germany Captured Stalingrad?")
        self.assertTrue(good_stalingrad["is_valid_counterfactual"])

        # Verify topic_scorer penalizes the non-counterfactual Berlin Wall title
        berlin_score = score_topic("What If a Single Wall Divided East and West Berlin?", "channel_a", "Cold War")
        self.assertLessEqual(berlin_score["final_score"], 0.25)
        self.assertFalse(berlin_score["is_valid_counterfactual"])

        rome_score = score_topic("What If the Roman Empire Never Fell?", "channel_a", "Empire")
        self.assertGreater(rome_score["final_score"], 0.75)
        self.assertTrue(rome_score["is_valid_counterfactual"])

    def test_10_generate_script_deduplicates_and_repairs_stalingrad_contradiction(self):
        entity = extract_primary_title_entity("What If the Roman Empire Never Fell?")
        self.assertIn("Roman Empire", entity)

        script_data = {
            "topic": "What If Nazi Germany Captured Stalingrad?",
            "hook": "In November 1942, German panzers seize the Volga.",
            "scenes": [
                {
                    "scene_number": 1,
                    "narration": "In November 1942, German Sixth Army divisions reach the Volga River at Stalingrad.",
                    "visual_prompt": "German tanks on snowy riverbank in 1942",
                },
                {
                    "scene_number": 2,
                    "narration": "General Paulus severs the river supply corridor feeding the southern front.",
                    "visual_prompt": "Volga river frozen under artillery smoke",
                },
                {
                    "scene_number": 3,
                    "narration": "In November 1942, German Sixth Army divisions reach the Volga River at Stalingrad.",
                    "visual_prompt": "German infantry advancing through ruins",
                },
                {
                    "scene_number": 4,
                    "narration": "It might have allowed panzer columns to capture the Baku oil fields by spring 1943.",
                    "visual_prompt": "Caucasus oil derricks under winter sky",
                },
                {
                    "scene_number": 5,
                    "narration": "In the end, it was the Soviet Union that emerged victorious at Stalingrad.",
                    "visual_prompt": "Eastern Front map in 1943",
                },
                {
                    "scene_number": 6,
                    "narration": "Join us as we explore how Moscow fights from beyond the Urals.",
                    "visual_prompt": "Ural mountain fortifications in winter",
                },
            ],
        }
        deduped = deduplicate_script_ngrams(script_data)
        with tempfile.TemporaryDirectory() as tmp, patch("generate_script.requests.post", side_effect= RuntimeError("Ollama offline in unit test")):
            revised, report = verify_and_revise_script_claims(
                deduped,
                {"historical_claims": [{"claim_id": "c1", "claim_type": "FACT", "claim": "Battle of Stalingrad 1942"}]},
                "test_vid",
                output_dir=tmp,
                is_factual=False,
            )
            beats = [s["narration"] for s in revised["scenes"]]
            audit = audit_script_quality(beats, "Stalingrad")
            self.assertTrue(audit["passed"], f"Expected repaired script to pass audit, got: {audit['issues']}")
            self.assertNotIn("soviet union that emerged victorious", " ".join(beats).lower())

    def test_11_visual_scene_planner_and_image_validator_integration(self):
        script_data = {
            "topic": "What If the Roman Empire Never Fell?",
            "scenes": [
                {
                    "scene_id": 1,
                    "narration": "In 476 AD, Emperor Majorian crushes the Vandals and fortifies Ravenna.",
                    "visual_prompt": "Roman legions marching past stone aqueduct",
                }
            ],
        }
        fallback_beats = build_fallback_scene_plan(script_data, {"total_duration": 10.0})
        scene_0 = fallback_beats[0]
        self.assertIn("Single full-bleed vertical 9:16 cinematic photograph", scene_0["visual_prompt"])
        self.assertIn("mandalorian helmet", scene_0["negative_prompt"])
        self.assertIn("split screen", scene_0["negative_prompt"])

        cleaned_prompt = clean_visual_prompt_string(
            "Medium shot", "split-screen propaganda poster of Roman soldiers", "Ancient Rome"
        )
        self.assertIn("Single full-bleed vertical 9:16 cinematic shot", cleaned_prompt)
        self.assertIn("no text, no split screen", cleaned_prompt)

        with tempfile.TemporaryDirectory() as tmp:
            proof_path = Path(tmp) / "scene_01.png"
            ok = generate_pillow_proof_image(scene_0, proof_path)
            self.assertTrue(ok)
            self.assertTrue(validate_image(proof_path))

            # Now draw a solid white split-panel divider bar across the middle and verify rejection
            img = cv2.imread(str(proof_path))
            h, w, _ = img.shape
            img[h // 2 - 4 : h // 2 + 4, :, :] = 255
            cv2.imwrite(str(proof_path), img)
            self.assertFalse(validate_image(proof_path))

    def test_12_no_hardcoded_webhooks_in_discord_review(self):
        p1_discord = (ROOT_DIR / "alternate-history-shorts" / "scripts" / "discord_review.py").read_text(encoding="utf-8")
        shared_discord = (ROOT_DIR / "shared" / "discord_review.py").read_text(encoding="utf-8")
        self.assertNotIn("https://discord.com/api/webhooks/", p1_discord)
        self.assertNotIn("https://discord.com/api/webhooks/", shared_discord)


if __name__ == "__main__":
    unittest.main()
