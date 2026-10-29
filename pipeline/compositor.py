# -*- coding: utf-8 -*-
"""
pipeline/compositor.py
----------------------
Module B: Fooocus SDXL Negative Prompt Lock, Split-Panel Detector & Safe Subtitles.

Fixes:
- Short 3 (Stalingrad, fqClEqxTJBE @ 0:29): 3-panel collage with AI gibberish text "TIP PROGAPNINTA"
- Short 5 (Rome, zNzOWnYZheA @ 0:16, 0:23, 0:34): 2-panel split grid & Star Wars Mandalorian helmet
- Short 1 (Berlin Wall, 3acz-TlpYx0 @ 0:08, 0:24): Clocks on guard tower & medieval castle in open farmland
- Short 4 (Alexandria, SEjKTQpHOOU @ 0:15): Modern ballpoint pen & hardcover book in ancient Egypt
- All 5 Shorts on @sainishath4220: Subtitles at bottom edge (y > 1700) covered by YouTube Shorts UI
"""

from __future__ import annotations

import random
import subprocess
from typing import Dict
import cv2
import numpy as np

FOOOCUS_NEGATIVE_PROMPT_LOCK = (
    "text, letters, typography, watermark, signature, gibberish text, poster text, signage, "
    "split screen, multi-panel, collage, comic strip, 2-panel grid, 3-panel grid, horizontal divider, "
    "frame border, sci-fi armor, mandalorian helmet, T-visor helmet, modern ballpoint pen, modern hardhats, "
    "wall clocks on exterior tower, medieval castle in 20th century city, blurry, deformed hands, extra limbs"
)


def build_fooocus_scene_prompt(scene_description: str, era_context: str) -> Dict[str, str]:
    """Enforces single-frame vertical composition and period-accurate visual constraints for Fooocus SDXL."""
    positive = (
        f"Single full-bleed vertical 9:16 cinematic photograph, {era_context}, {scene_description}, "
        "dramatic volumetric lighting, historically authentic wardrobe and architecture, 35mm archival film grain, "
        "no text, no split screen"
    )
    return {"prompt": positive, "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK}


def detect_split_panel_collage(image_path: str) -> bool:
    """
    17-Point QA Gate addition: Detects horizontal split-screen divider bars (like Rome @ 0:23 and Stalingrad @ 0:29)
    by scanning the middle 60% of the image for uniform horizontal separator lines.
    Returns True if a defective multi-panel grid is detected so Fooocus regenerates the keyframe.
    """
    img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return False
    h, _ = img.shape
    mid_band = img[int(h * 0.25) : int(h * 0.75), :]
    row_std = np.std(mid_band, axis=1)
    # A solid white/black/gray horizontal divider bar across the full width has near-zero row std
    return bool(np.any(row_std < 3.5))


MOTION_TRAJECTORIES = [
    "zoompan=z='min(zoom+0.0010,1.18)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps=30",
    "zoompan=z='if(eq(on,1),1.18,max(zoom-0.0010,1.0))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps=30",
    "zoompan=z='1.12':x='(iw-iw/zoom)*(on/{frames})':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps=30",
    "zoompan=z='1.12':x='(iw-iw/zoom)*(1-on/{frames})':y='(ih-ih/zoom)*(on/{frames})':d={frames}:s=1080x1920:fps=30",
]

# Moves captions up to MarginV=620 (72pt bold yellow/white) so YouTube Shorts bottom UI never blocks them
SAFE_SHORTS_ASS_STYLE = (
    "Style: Default,DejaVu Sans,72,&H0000FFFF,&H00FFFFFF,&H00000000,&H80000000,"
    "-1,0,0,0,100,100,1,0,1,5,2,2,80,80,620,1"
)

SAFE_SHORTS_ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,72,&H0000FFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,5,2,2,80,80,620,1
"""


def render_dynamic_short_scene(image_path: str, duration_sec: float, output_clip_path: str) -> None:
    """Renders a 9:16 keyframe with randomized camera motion instead of frozen Candidate A Ken Burns."""
    frames = max(1, int(duration_sec * 30))
    motion_expr = random.choice(MOTION_TRAJECTORIES).format(frames=frames)
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", str(image_path),
        "-vf", f"{motion_expr},format=yuv420p",
        "-t", f"{duration_sec:.2f}", "-c:v", "libx264", "-preset", "fast", "-crf", "20", str(output_clip_path),
    ]
    subprocess.run(cmd, check=True)
