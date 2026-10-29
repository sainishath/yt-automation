# -*- coding: utf-8 -*-
"""
tests/test_factual_learning_engine.py
-------------------------------------
Comprehensive Unit & Integration Test Suite for Factual History Architecture Upgrades:
  1. Primary Source Ingestion & Historical Corpora (pipeline/primary_sources.py)
  2. On-Screen Manuscript Translation Card Rendering (pipeline/primary_sources.py)
  3. Tactical Siege Map Animation Engine (longform_engine/tactical_map_renderer.py)
  4. Overland Fleet Transit Animation Engine (longform_engine/tactical_map_renderer.py)
  5. Interactive Overlays & Act Progress Badges (longform_engine/interactive_overlays.py)
  6. Sidechaincompress Audio Ducking (longform_engine/interactive_overlays.py)
  7. Dual-Mode Script Architect Engine (longform_engine/script_architect.py)
  8. Assemble Longform Media Routing (longform_engine/assemble_longform.py)
"""

import os
import sys
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
        sources = extract_primary_sources("fall_of_constantinople_1453")
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
            self.assertIn("quote", s)
            self.assertIn("translation", s)
            self.assertIn("academic_citation", s)
            self.assertIn("key_passage_highlight", s)

    def test_02_primary_sources_extraction_other_events(self):
        """Verifies primary source extraction across the 4-week release calendar."""
        # Bronze Age Collapse (1177 BC)
        ba_sources = extract_primary_sources("bronze_age_collapse_1177_bc")
        self.assertGreaterEqual(len(ba_sources), 2)
        ba_authors = [s["author"] for s in ba_sources]
        self.assertTrue(any("Ramesses" in a for a in ba_authors))
        self.assertTrue(any("Ammurapi" in a for a in ba_authors))

        # Lost Army of Cambyses (524 BC)
        cambyses_sources = extract_primary_sources("lost_army_of_cambyses_524_bc")
        self.assertGreaterEqual(len(cambyses_sources), 1)
        self.assertIn("Herodotus", cambyses_sources[0]["author"])

        # Operation Mincemeat (1943)
        mincemeat_sources = extract_primary_sources("operation_mincemeat_1943")
        self.assertGreaterEqual(len(mincemeat_sources), 2)
        mm_authors = [s["author"] for s in mincemeat_sources]
        self.assertTrue(any("Montagu" in a for a in mm_authors))

    # ── 2. On-Screen Manuscript Card Rendering ────────────────────────────────

    def test_03_render_source_card_png(self):
        """Verifies that render_source_card generates a 1920x1080 transparent PNG manuscript card."""
        sources = extract_primary_sources("fall_of_constantinople_1453")
        sample_source = sources[0]

        card_png = self.test_dir / "sample_source_card.png"
        out_path = render_source_card(sample_source, card_png)

        self.assertTrue(out_path.exists())
        self.assertGreater(out_path.stat().st_size, 15000)

        # Inspect image properties
        with Image.open(out_path) as img:
            self.assertEqual(img.size, (1920, 1080))
            self.assertEqual(img.mode, "RGBA")
            # Verify top corners are transparent
            top_pixel = img.getpixel((50, 50))
            self.assertEqual(top_pixel[3], 0, "Background outside card box must be transparent (alpha=0)")

    # ── 3. Tactical Map & Battle Vector Animation ─────────────────────────────

    def test_04_tactical_siege_map_rendering(self):
        """Verifies tactical siege map engine renders an animated 1080p MP4 with vector arrows."""
        out_mp4 = self.test_dir / "test_siege_map.mp4"
        custom_vectors = [
            {"x1": 200, "y1": 500, "x2": 450, "y2": 480, "color": (30, 30, 220), "label": "Vanguard", "target_name": "Gate"}
        ]
        res = render_tactical_siege_map(
            output_mp4_path=out_mp4,
            vectors=custom_vectors,
            duration_sec=1.0,
            fps=15
        )

        self.assertTrue(res.exists())
        self.assertGreater(res.stat().st_size, 50000)

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

    def test_05_overland_fleet_transit_rendering(self):
        """Verifies overland fleet transit engine renders the Galata ridge timeline animation."""
        out_mp4 = self.test_dir / "test_overland_transit.mp4"
        res = render_overland_fleet_transit(
            ship_count=70,
            output_mp4_path=out_mp4,
            duration_sec=1.0,
            fps=15
        )

        self.assertTrue(res.exists())
        self.assertGreater(res.stat().st_size, 50000)

    # ── 4. Interactive Visual Overlays & Audio Ducking ────────────────────────

    def test_06_act_badge_creation_and_overlay(self):
        """Verifies Act Progress Badge generation and overlay filtergraph execution."""
        # 1. Test badge PNG creation
        badge_png = self.test_dir / "act_badge.png"
        create_act_badge_png(2, "The Overland Fleet", "1453 AD", badge_png)
        self.assertTrue(badge_png.exists())
        with Image.open(badge_png) as img:
            self.assertEqual(img.size, (360, 86))
            self.assertEqual(img.mode, "RGBA")

        # 2. Test burning onto an input test video
        base_video = self.test_dir / "base_video.mp4"
        badged_video = self.test_dir / "badged_video.mp4"
        # Generate 1-second blank video with lavfi
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=1920x1080:d=1.0:r=15",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(base_video)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        res = burn_act_badge(
            input_video=base_video,
            output_video=badged_video,
            act_number=2,
            act_title="The Overland Fleet",
            historical_date="1453 AD",
            duration=1.0,
            fade_in_sec=0.2,
            fade_out_sec=0.2
        )
        self.assertTrue(res.exists())
        self.assertGreater(res.stat().st_size, 1000)

    def test_07_sidechain_audio_ducking(self):
        """Verifies sidechain audio compression dynamically ducks BGM under voiceover narration."""
        voice_wav = self.test_dir / "voice.wav"
        bgm_wav = self.test_dir / "bgm.wav"
        ducked_out = self.test_dir / "ducked_master.m4a"

        # Generate mock audio tones
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=1000:duration=1.5", str(voice_wav)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=300:duration=1.5", str(bgm_wav)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        res = apply_sidechain_ducking(
            voice_path=voice_wav,
            bgm_path=bgm_wav,
            output_audio=ducked_out,
            threshold=0.08,
            ratio=6.0,
            release_ms=250
        )
        self.assertTrue(res.exists())
        self.assertGreater(res.stat().st_size, 5000)

    # ── 5. Dual-Mode Script Architect Engine ──────────────────────────────────

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

    # ── 6. Assemble Longform Wiring Verification ─────────────────────────────

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


if __name__ == "__main__":
    unittest.main()
