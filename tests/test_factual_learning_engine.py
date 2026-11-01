# -*- coding: utf-8 -*-
"""
tests/test_factual_learning_engine.py
-------------------------------------
Comprehensive Unit & Integration Test Suite for Factual History Architecture:
  1. Primary Source Ingestion & Historical Corpora (pipeline/primary_sources.py)
  2. On-Screen Manuscript Translation Card Rendering (pipeline/primary_sources.py)
  3. Tactical Siege Map Animation Engine (longform_engine/tactical_map_renderer.py)
  4. Overland Fleet Transit Animation Engine (longform_engine/tactical_map_renderer.py)
  5. Interactive Overlays & Act Progress Badges (longform_engine/interactive_overlays.py)
  6. Sidechaincompress Audio Ducking (longform_engine/interactive_overlays.py)
  7. Dual-Mode Script Architect Engine (longform_engine/script_architect.py)
  8. Assemble Longform Media Routing (longform_engine/assemble_longform.py)
  9. Week 1 80-Shot Schema & Production Integrity (history_10min_80shots.json)
"""

import os
import sys
import json
import tempfile
import unittest
import subprocess
from pathlib import Path
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(ROOT_DIR / "longform_engine") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "longform_engine"))

from pipeline.primary_sources import (
    extract_primary_sources,
    render_source_card,
    PRIMARY_SOURCE_CORPORA,
    normalize_event_slug
)
from longform_engine.tactical_map_renderer import (
    create_procedural_constantinople_basemap,
    render_tactical_siege_map,
    render_overland_fleet_transit,
)
from longform_engine.interactive_overlays import (
    create_act_badge_png,
    burn_act_badge,
    burn_source_card,
    apply_sidechain_ducking,
)
from longform_engine.script_architect import (
    build_history_documentary_script,
    build_coding_masterclass_script,
)


class TestFactualLearningEngine(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    # ── 1. Primary Source Extraction Tests ────────────────────────────────────

    def test_01_primary_sources_extraction_constantinople(self):
        """Verifies full primary source corpus extraction for the Fall of Constantinople (1453)."""
        sources = extract_primary_sources("constantinople_1453")
        self.assertGreaterEqual(len(sources), 5, "Must contain at least 5 primary eyewitness sources")

        authors = [s["author"] for s in sources]
        self.assertTrue(any("Sphrantzes" in a for a in authors), "Sphrantzes census must be present")
        self.assertTrue(any("Kritovoulos" in a for a in authors), "Kritovoulos supercannon must be present")
        self.assertTrue(any("Barbaro" in a for a in authors), "Barbaro overland fleet must be present")
        self.assertTrue(any("Isidore" in a for a in authors), "Isidore Hagia Sophia must be present")
        self.assertTrue(any("Ducas" in a for a in authors), "Ducas last charge must be present")

        # Verify contracts
        for s in sources:
            self.assertIn("author", s)
            self.assertIn("date", s)
            self.assertIn("original_work", s)
            self.assertTrue("verbatim_quote" in s or "quote" in s)
            self.assertTrue("english_translation" in s or "translation" in s)
            self.assertIn("academic_citation", s)

    def test_02_primary_sources_extraction_other_events(self):
        """Verifies primary source extraction across the 4-week release calendar."""
        # Bronze Age Collapse (1177 BC)
        ba_sources = extract_primary_sources("bronze_age_collapse_1177bc")
        self.assertGreaterEqual(len(ba_sources), 2)
        ba_authors = [s["author"] for s in ba_sources]
        self.assertTrue(any("Ramesses" in a for a in ba_authors))
        self.assertTrue(any("Ammurapi" in a for a in ba_authors))

        # Lost Army of Cambyses (524 BC)
        cambyses_sources = extract_primary_sources("cambyses_lost_army_524bc")
        self.assertGreaterEqual(len(cambyses_sources), 1)
        self.assertIn("Herodotus", cambyses_sources[0]["author"])

        # Operation Mincemeat (1943)
        mincemeat_sources = extract_primary_sources("operation_mincemeat_1943")
        self.assertGreaterEqual(len(mincemeat_sources), 2)
        mm_authors = [s["author"] for s in mincemeat_sources]
        self.assertTrue(any("Montagu" in a for a in mm_authors))

    # ── 2. On-Screen Manuscript Card Rendering ────────────────────────────────

    def test_primary_source_card_generation(self):
        """Verifies Pillow outputs valid 1920x1080 transparent PNG manuscript cards."""
        sources = extract_primary_sources("constantinople_1453")
        sample_source = sources[0]

        card_png = self.test_dir / "sample_source_card.png"
        out_path = render_source_card(sample_source, card_png)

        self.assertTrue(out_path.exists())
        self.assertGreater(out_path.stat().st_size, 15000)

        # Inspect image properties
        with Image.open(out_path) as img:
            self.assertEqual(img.size, (1920, 1080))
            self.assertEqual(img.mode, "RGBA")
            # Verify top corners are transparent (alpha=0)
            top_pixel = img.getpixel((50, 50))
            self.assertEqual(top_pixel[3], 0, "Background outside card box must be transparent (alpha=0)")

    def test_03_render_source_card_png(self):
        """Alias verifying render_source_card compatibility."""
        self.test_primary_source_card_generation()

    # ── 3. Tactical Map & Battle Vector Animation ─────────────────────────────

    def test_tactical_map_animation_rendering(self):
        """Verifies OpenCV/FFmpeg outputs valid 1920x1080 MP4 clips."""
        out_mp4 = self.test_dir / "test_siege_map.mp4"
        custom_vectors = [
            {"x1": 200, "y1": 500, "x2": 450, "y2": 480, "color": (30, 30, 220), "label": "Vanguard", "target_name": "Gate"}
        ]
        # Test signature (base_map_path, vectors, duration_sec, out_mp4, fps=25)
        res = render_tactical_siege_map(
            None,
            custom_vectors,
            1.0,
            out_mp4,
            25
        )

        self.assertTrue(res.exists())
        self.assertGreater(res.stat().st_size, 30000)

        # Verify video stream dimensions via ffprobe
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0",
            str(res)
        ]
        probe_res = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, check=True)
        dims = probe_res.stdout.strip()
        self.assertEqual(dims, "1920,1080", "Tactical map must output exact 1920x1080 resolution")

        # Test overland fleet transit
        out_overland = self.test_dir / "test_overland.mp4"
        res_overland = render_overland_fleet_transit(
            elevation_profile={"ridge_height_m": 68},
            duration_sec=1.0,
            out_mp4=out_overland,
            fps=25
        )
        self.assertTrue(res_overland.exists())
        self.assertGreater(res_overland.stat().st_size, 30000)

    def test_04_tactical_siege_map_rendering(self):
        """Alias for tactical siege map rendering."""
        self.test_tactical_map_animation_rendering()

    # ── 4. Interactive Visual Overlays & Audio Ducking ────────────────────────

    def test_act_badge_overlay_and_sidechain_ducking(self):
        """Verifies overlay filters (act progress badge) and sidechaincompress ducking execute cleanly."""
        # 1. Test Act Badge overlay
        base_video = self.test_dir / "base_video.mp4"
        badged_video = self.test_dir / "badged_video.mp4"
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=1920x1080:d=1.0:r=15",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(base_video)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        res_badge = burn_act_badge(
            clip_path=base_video,
            act_number=1,
            act_title="The Millennium Walls",
            historical_date="1453 AD",
            out_path=badged_video
        )
        self.assertTrue(res_badge.exists())
        self.assertGreater(res_badge.stat().st_size, 1000)

        # 2. Test Sidechain Audio Ducking
        voice_wav = self.test_dir / "voice.wav"
        bgm_wav = self.test_dir / "bgm.wav"
        ducked_out = self.test_dir / "ducked_master.m4a"

        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=1000:duration=1.5", str(voice_wav)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=300:duration=1.5", str(bgm_wav)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        res_duck = apply_sidechain_ducking(
            narration_wav=voice_wav,
            bgm_wav=bgm_wav,
            sfx_wav=None,
            out_wav=ducked_out
        )
        self.assertTrue(res_duck.exists())
        self.assertGreater(res_duck.stat().st_size, 5000)

    def test_06_act_badge_creation_and_overlay(self):
        """Alias for act badge overlay test."""
        self.test_act_badge_overlay_and_sidechain_ducking()

    # ── 5. Week 1 80-Shot Schema & Production Integrity ───────────────────────

    def test_history_80shots_schema_integrity(self):
        """Validates history_10min_80shots.json structure, prompts, and shot metadata."""
        json_path = ROOT_DIR / "longform_engine" / "drafts" / "history_10min_80shots.json"
        self.assertTrue(json_path.exists(), f"80-shot architecture JSON not found: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(len(data.get("acts", [])), 7, "Documentary must contain 7 acts")
        
        all_shots = []
        for act in data["acts"]:
            self.assertIn("act_number", act)
            self.assertIn("title", act)
            self.assertIn("script", act)
            act_shots = act.get("shots") or act.get("visual_shots", [])
            self.assertGreaterEqual(len(act_shots), 10, f"Act {act['act_number']} must have at least 10 shots")
            all_shots.extend(act_shots)

        self.assertEqual(len(all_shots), 80, f"Expected exactly 80 visual shots across 7 acts, got {len(all_shots)}")

        # Validate shot fields and visual taxonomy
        shot_types = set()
        for shot in all_shots:
            self.assertIn("shot_id", shot)
            self.assertIn("shot_type", shot)
            self.assertIn("prompt", shot)
            self.assertIn("motion", shot)
            self.assertIn("negative_prompt", shot)
            self.assertIn("act_number", shot)
            shot_types.add(shot["shot_type"])

        # Check required visual taxonomy components
        has_wide = any("Wide" in st for st in shot_types)
        has_tactical = any("Tactical" in st or "Map" in st for st in shot_types)
        has_troop = any("Troop" in st for st in shot_types)
        has_manuscript = any("Manuscript" in st or "Primary Source" in st for st in shot_types)
        has_macro = any("Macro" in st for st in shot_types)

        self.assertTrue(has_wide, "Taxonomy must include Wide shots")
        self.assertTrue(has_tactical, "Taxonomy must include Tactical Map shots")
        self.assertTrue(has_troop, "Taxonomy must include Medium Troop shots")
        self.assertTrue(has_manuscript, "Taxonomy must include Manuscript / Primary Source shots")
        self.assertTrue(has_macro, "Taxonomy must include Macro shots")

    # ── 6. Dual-Mode Script Architect Engine ──────────────────────────────────

    def test_08_script_architect_dual_mode(self):
        """Verifies script_architect.py supports --mode factual and --mode counterfactual."""
        # Mode A: Factual
        factual_data = build_history_documentary_script(mode="factual", event_slug="fall_of_constantinople_1453")
        self.assertEqual(factual_data["mode"], "factual")
        self.assertEqual(factual_data["primary_sources_count"], 5)
        self.assertIn("The 53 Days That Shattered Rome", factual_data["video_title"])
        # Check that Act 1 has primary source binding
        act1 = factual_data["acts"][0]
        self.assertIn("primary_source_record", act1)
        self.assertIn("George Sphrantzes", act1["historical_grounding"]["primary_source"])

        # Mode B: Counterfactual
        cf_data = build_history_documentary_script(mode="counterfactual", event_slug="fall_of_constantinople_1453")
        self.assertEqual(cf_data["mode"], "counterfactual")
        self.assertEqual(cf_data["primary_sources_count"], 0)
        self.assertIn("What If", cf_data["video_title"])

    # ── 7. Assemble Longform Wiring Verification ─────────────────────────────

    def test_09_assemble_longform_tactical_and_overlay_wiring(self):
        """Verifies assemble_longform.py imports and references tactical map and interactive overlay modules."""
        assemble_file = ROOT_DIR / "longform_engine" / "assemble_longform.py"
        content = assemble_file.read_text(encoding="utf-8")

        self.assertIn("render_tactical_siege_map", content)
        self.assertIn("render_overland_fleet_transit", content)
        self.assertIn("burn_act_badge", content)
        self.assertIn("burn_source_card", content)
        self.assertIn("apply_sidechain_ducking", content)
        self.assertIn("extract_primary_sources", content)
        self.assertIn("--split-shorts", content)

    # ── 8. Weeks 2–4 80-Shot Production Drafts & Derived Shorts Schema ───────

    def test_10_weeks_2_to_4_drafts_and_derived_shorts_schema(self):
        """Verifies 4 weekly 80-shot master drafts (320 shots) and 20 derived shorts manifests."""
        drafts_dir = ROOT_DIR / "longform_engine" / "drafts"
        expected_drafts = [
            ("history_10min_80shots.json", "constantinople_1453", "w1_short_"),
            ("bronze_age_collapse_1177bc_80shots.json", "bronze_age_collapse_1177bc", "w2_short_"),
            ("cambyses_lost_army_524bc_80shots.json", "cambyses_lost_army_524bc", "w3_short_"),
            ("operation_mincemeat_1943_80shots.json", "operation_mincemeat_1943", "w4_short_"),
        ]

        total_shots_all_weeks = 0
        total_shorts_all_weeks = 0

        for draft_filename, expected_slug, short_prefix in expected_drafts:
            draft_path = drafts_dir / draft_filename
            self.assertTrue(draft_path.exists(), f"Draft file {draft_filename} must exist")

            with open(draft_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 7 Acts
            acts = data.get("acts", [])
            self.assertEqual(len(acts), 7, f"{draft_filename} must have exactly 7 acts")

            # 80 Total Shots
            week_shots = 0
            for act in acts:
                shots = act.get("shots", [])
                week_shots += len(shots)
                for shot in shots:
                    self.assertTrue("shot_id" in shot or "shot_number" in shot, "Shot must have shot_id or shot_number")
                    self.assertIn("prompt", shot)
                    self.assertIn("negative_prompt", shot)
                    self.assertTrue(len(shot["negative_prompt"].strip()) > 0, "Negative prompt lock must be non-empty")
                    self.assertIn("shot_type", shot)

            self.assertEqual(week_shots, 80, f"{draft_filename} must have exactly 80 visual shots")
            total_shots_all_weeks += week_shots

            # 5 Derived Shorts Manifest
            derived_shorts = data.get("derived_shorts", [])
            self.assertEqual(len(derived_shorts), 5, f"{draft_filename} must have exactly 5 derived shorts")
            total_shorts_all_weeks += len(derived_shorts)

            for short in derived_shorts:
                self.assertIn("short_id", short)
                self.assertTrue(short["short_id"].startswith(short_prefix))
                self.assertIn("title", short)
                self.assertIn("source_act", short)
                self.assertIn("start_sec", short)
                self.assertIn("duration_sec", short)
                self.assertIn("hook_script", short)
                self.assertTrue(1 <= short["source_act"] <= 7)
                self.assertGreater(short["duration_sec"], 0)
                self.assertTrue(len(short["hook_script"].strip()) > 0)

        self.assertEqual(total_shots_all_weeks, 320, "Total visual shots across all 4 weeks must be 320")
        self.assertEqual(total_shorts_all_weeks, 20, "Total derived shorts across all 4 weeks must be 20")

    # ── 9. Causal Synced Draft & Standalone Short Tests ───────────────────────

    def test_11_causal_test_draft_schema_and_per_shot_narration(self):
        """Verifies constantinople_1453_causal_test.json structure, per-shot narration, and standalone short."""
        causal_draft_path = ROOT_DIR / "longform_engine" / "drafts" / "constantinople_1453_causal_test.json"
        self.assertTrue(causal_draft_path.exists(), "constantinople_1453_causal_test.json must exist")

        with open(causal_draft_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data.get("sync_mode"), "per_shot_narration")
        self.assertEqual(data.get("bgm_mode"), "clean_voice_or_subbass_only")
        acts = data.get("acts", [])
        self.assertEqual(len(acts), 4, "Causal test draft must contain 4 causal acts")

        total_shots = 0
        for act in acts:
            shots = act.get("shots", [])
            total_shots += len(shots)
            for s in shots:
                self.assertIn("shot_id", s)
                self.assertIn("narration", s)
                self.assertTrue(len(s["narration"].strip()) > 0, "Shot must have non-empty narration")
                self.assertIn("prompt", s)
                self.assertIn("causal_step", s)

        self.assertEqual(total_shots, 16, "Causal test draft must contain exactly 16 shots")

        # Verify standalone_short_test
        st = data.get("standalone_short_test", {})
        self.assertIn("title", st)
        beats = st.get("beats", [])
        self.assertIn(len(beats), [5, 15], "Standalone short test must contain 5 or 15 causal cuts/beats")
        for b in beats:
            self.assertIn("beat_id", b)
            self.assertIn("causal_role", b)
            self.assertIn("narration", b)
            self.assertTrue(len(b["narration"].strip()) > 0)
            self.assertIn("prompt", b)

    def test_12_clean_voice_no_bgm_default_and_filter(self):
        """Verifies clean voice default and low-pass filter in assemble_longform.py."""
        assemble_file = ROOT_DIR / "longform_engine" / "assemble_longform.py"
        content = assemble_file.read_text(encoding="utf-8")

        self.assertIn("--enable-bgm", content)
        self.assertIn("lowpass=f=240,highpass=f=45,volume=0.03", content)
        self.assertIn("has_per_shot_narration", content)
        self.assertIn("clip_{shot_id}_synced.mp4", content)

    def test_13_standalone_causal_short_engine(self):
        """Verifies render_standalone_causal_short is callable and imports cleanly."""
        from longform_engine.short_splitter import render_standalone_causal_short, generate_safe_short_ass
        self.assertTrue(callable(render_standalone_causal_short))

        # Test subtitle generation with MarginV=620
        test_ass = self.test_dir / "test_margin620.ass"
        generate_safe_short_ass("In 1453, Mehmed captured Constantinople.", 5.0, test_ass)
        self.assertTrue(test_ass.exists())
        content = test_ass.read_text(encoding="utf-8")
        self.assertIn("MarginV", content)
        self.assertIn(",80,80,620,", content.replace(" ", ""))


if __name__ == "__main__":
    unittest.main()
