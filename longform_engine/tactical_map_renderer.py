# -*- coding: utf-8 -*-
"""
longform_engine/tactical_map_renderer.py
----------------------------------------
Tactical Map & Battle Dynamic Vector Animation Engine.
Renders 16:9 animated tactical maps (1920x1080 at 30fps) for historical documentaries:
  1. Animated dotted troop movement arrows and naval maneuvers
  2. Pulsing battle radar markers & siege perimeters
  3. Mehmed II's 70-warship overland transit timeline across the Galata ridge
  4. Topographic camera push-in and smoothstep vector interpolation
Pipes raw frames directly to FFmpeg (H.264 / yuv420p) with zero-stretch 1080p output.
"""

import os
import sys
import math
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def _get_font(size: int = 24, bold: bool = True) -> ImageFont.ImageFont:
    """Loads clean font for map overlays."""
    candidates = [
        "C:\\Windows\\Fonts\\segoeuib.ttf" if bold else "C:\\Windows\\Fonts\\segoeui.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\georgiab.ttf" if bold else "C:\\Windows\\Fonts\\georgia.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()


# ═════════════════════════════════════════════════════════════════════════════
# 1. PROCEDURAL HISTORICAL BASEMAP GENERATOR (1920x1080 ANTIQUE PARCHMENT)
# ═════════════════════════════════════════════════════════════════════════════

def create_procedural_constantinople_basemap() -> np.ndarray:
    """
    Renders a 1920x1080 antique cartographic basemap of the Constantinople peninsula,
    Golden Horn inlet, Bosporus strait, Sea of Marmara, and Galata hill ridge.
    """
    # 1. Antique Parchment / Vellum Base (warm muted sepia)
    w, h = 1920, 1080
    base = np.zeros((h, w, 3), dtype=np.uint8)
    base[:, :] = [185, 215, 230]  # BGR warm parchment (approx #E6D7B9)

    # Add gentle cartographic vignette and texture noise
    noise = np.random.randint(-8, 9, (h, w, 3), dtype=np.int16)
    textured = np.clip(base.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # 2. Water Bodies (Muted slate blue / antique teal BGR: [175, 155, 110])
    water_color = (170, 150, 110) # BGR
    water_mask = np.zeros((h, w), dtype=np.uint8)

    # Sea of Marmara (South & Southeast water body)
    cv2.rectangle(water_mask, (0, 780), (1920, 1080), 255, -1)
    marmara_pts = np.array([
        [0, 680], [350, 710], [800, 740], [1300, 750], [1550, 680], [1920, 700],
        [1920, 1080], [0, 1080]
    ], np.int32)
    cv2.fillPoly(water_mask, [marmara_pts], 255)

    # The Golden Horn (Curving waterway between City and Galata)
    golden_horn_pts = np.array([
        [500, 220], [750, 280], [1050, 360], [1300, 430], [1500, 520], [1650, 570],
        [1660, 620], [1520, 600], [1320, 500], [1080, 420], [780, 340], [480, 270]
    ], np.int32)
    cv2.fillPoly(water_mask, [golden_horn_pts], 255)

    # The Bosporus Strait (North-South channel to Black Sea)
    bosporus_pts = np.array([
        [1500, 0], [1580, 180], [1620, 350], [1650, 570], [1780, 700], [1920, 750],
        [1920, 0]
    ], np.int32)
    cv2.fillPoly(water_mask, [bosporus_pts], 255)

    # Smooth coastlines
    water_mask = cv2.GaussianBlur(water_mask, (15, 15), 0)
    for c in range(3):
        textured[:, :, c] = np.where(water_mask > 120, water_color[c], textured[:, :, c])

    # 3. Draw Shoreline Inks (Double ink line)
    contours, _ = cv2.findContours((water_mask > 120).astype(np.uint8), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(textured, contours, -1, (75, 60, 45), 2, cv2.LINE_AA) # Dark sepia ink line
    cv2.drawContours(textured, contours, -1, (120, 105, 90), 1, cv2.LINE_AA)

    # 4. Draw Landward Fortifications: Theodosian Triple Walls (4-mile barrier)
    # Wall runs from Sea of Marmara coast (x: 420, y: 720) North-North-East to Blachernae / Golden Horn (x: 490, y: 250)
    wall_pts = np.array([[430, 720], [450, 600], [470, 460], [490, 340], [510, 240]], np.int32)
    # Outer moat & outer wall (crimson ink hash)
    cv2.polylines(textured, [wall_pts], isClosed=False, color=(35, 30, 130), thickness=6, lineType=cv2.LINE_AA)
    cv2.polylines(textured, [wall_pts + np.array([-10, 0])], isClosed=False, color=(50, 45, 160), thickness=3, lineType=cv2.LINE_AA)
    # Turret bastions
    for pt in wall_pts:
        cv2.circle(textured, tuple(pt), 7, (20, 20, 90), -1, cv2.LINE_AA)
        cv2.circle(textured, tuple(pt), 9, (212, 163, 89), 2, cv2.LINE_AA)

    # 5. Boom Chain across Golden Horn Entrance
    # From Seraglio Point (x: 1530, y: 580) to Galata Tower (x: 1470, y: 460)
    cv2.line(textured, (1530, 580), (1470, 460), (40, 40, 40), 4, cv2.LINE_AA)
    for t_step in np.linspace(0, 1, 8):
        cx = int(1530 + t_step * (1470 - 1530))
        cy = int(580 + t_step * (460 - 580))
        cv2.circle(textured, (cx, cy), 4, (180, 180, 180), -1, cv2.LINE_AA)

    # 6. Add Historical Geography Callouts via PIL
    pil_img = Image.fromarray(cv2.cvtColor(textured, cv2.COLOR_BGR2RGB))
    p_draw = ImageDraw.Draw(pil_img)
    f_title = _get_font(26, bold=True)
    f_label = _get_font(18, bold=True)
    f_italic = _get_font(16, bold=False)

    # Labels
    p_draw.text((650, 520), "CONSTANTINOPLE", fill=(60, 45, 35), font=f_title)
    p_draw.text((700, 560), "(BYZANTINE IMPERIAL CAPITAL)", fill=(90, 75, 65), font=f_italic)

    p_draw.text((250, 470), "THEODOSIAN WALLS\n(TRIPLE BARRIER)", fill=(140, 25, 25), font=f_label)
    p_draw.text((950, 310), "GOLDEN HORN (HALIÇ)", fill=(40, 60, 80), font=f_label)
    p_draw.text((1050, 820), "PROPONTIS (SEA OF MARMARA)", fill=(40, 60, 80), font=f_label)
    p_draw.text((1660, 250), "BOSPORUS\nSTRAIT", fill=(40, 60, 80), font=f_label)
    p_draw.text((1320, 330), "GALATA / PERA\n(GENOESE COLONY)", fill=(75, 60, 50), font=f_label)
    p_draw.text((1490, 500), "BOOM CHAIN", fill=(200, 30, 30), font=f_italic)
    p_draw.text((1350, 620), "HAGIA SOPHIA", fill=(130, 95, 20), font=f_label)

    # Compass Rose / North Arrow in Upper-Right
    cx_rose, cy_rose = 1790, 110
    p_draw.ellipse([cx_rose - 40, cy_rose - 40, cx_rose + 40, cy_rose + 40], outline=(140, 110, 60), width=2)
    p_draw.line([cx_rose, cy_rose - 46, cx_rose, cy_rose + 46], fill=(120, 30, 30), width=2)
    p_draw.line([cx_rose - 46, cy_rose, cx_rose + 46, cy_rose], fill=(140, 110, 60), width=2)
    p_draw.text((cx_rose - 6, cy_rose - 68), "N", fill=(120, 30, 30), font=f_title)

    res_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    return res_bgr


# ═════════════════════════════════════════════════════════════════════════════
# 2. TACTICAL SIEGE MAP ANIMATION (ARROWS, RADAR PULSES, ZOOM)
# ═════════════════════════════════════════════════════════════════════════════

def render_tactical_siege_map(
    base_map_path: Optional[Path] = None,
    vectors: Optional[List[Dict[str, Any]]] = None,
    output_mp4_path: Path = Path("output/tactical_siege_map.mp4"),
    duration_sec: float = 8.0,
    title: str = "SIEGE OF CONSTANTINOPLE • TACTICAL ASSAULT (APRIL 1453)",
    fps: int = 30
) -> Path:
    """
    Renders an animated 1920x1080 MP4 tactical map video:
      - Progressive animated dotted arrows illustrating troop maneuvers
      - Pulsing radar battle circles at defensive gate stress points
      - Topographic push-in camera zoom (1.00x to 1.04x)
      - Legend overlay in top-left
    """
    output_mp4_path = Path(output_mp4_path)
    output_mp4_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Load or Generate Basemap
    if base_map_path and Path(base_map_path).exists():
        raw_base = cv2.imread(str(base_map_path))
        if raw_base.shape[:2] != (1080, 1920):
            raw_base = cv2.resize(raw_base, (1920, 1080), interpolation=cv2.INTER_CUBIC)
    else:
        raw_base = create_procedural_constantinople_basemap()

    # Default vectors if none provided
    if not vectors:
        vectors = [
            {
                "x1": 180, "y1": 480, "x2": 440, "y2": 470,
                "color": (25, 30, 200),  # Red BGR (Ottoman Vanguard)
                "label": "Ottoman Center • Janissary Corps",
                "target_name": "St. Romanus Gate"
            },
            {
                "x1": 210, "y1": 280, "x2": 480, "y2": 310,
                "color": (25, 70, 220),
                "label": "Zaganos Pasha • European Levies",
                "target_name": "Blachernae Palace Breach"
            },
            {
                "x1": 200, "y1": 660, "x2": 430, "y2": 630,
                "color": (25, 70, 220),
                "label": "Ishak Pasha • Anatolian Army",
                "target_name": "Golden Gate Perimeter"
            }
        ]

    total_frames = int(duration_sec * fps)
    h, w = 1080, 1920

    # 2. FFmpeg Pipeline Spawn
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{w}x{h}",
        "-pix_fmt", "bgr24",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        str(output_mp4_path)
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    try:
        for f_idx in range(total_frames):
            t = f_idx / max(1, total_frames - 1)
            # Smoothstep interpolation
            s = 3.0 * (t ** 2) - 2.0 * (t ** 3)

            # Camera zoom (1.00x -> 1.035x)
            zoom = 1.00 + 0.035 * s
            crop_w = int(w / zoom)
            crop_h = int(h / zoom)
            x1_crop = (w - crop_w) // 2
            y1_crop = (h - crop_h) // 2
            frame = raw_base[y1_crop:y1_crop + crop_h, x1_crop:x1_crop + crop_w].copy()
            frame = cv2.resize(frame, (w, h), interpolation=cv2.INTER_LINEAR)

            # Draw Animated Movement Vectors
            for v in vectors:
                vx1, vy1 = v["x1"], v["y1"]
                vx2, vy2 = v["x2"], v["y2"]
                v_col = v.get("color", (20, 20, 210))

                # Current arrowhead tip position
                curr_x = int(vx1 + s * (vx2 - vx1))
                curr_y = int(vy1 + s * (vy2 - vy1))

                # Draw dotted/segmented shaft
                num_dots = 16
                for d_i in range(num_dots):
                    d_t = d_i / num_dots
                    if d_t <= s:
                        px = int(vx1 + d_t * (vx2 - vx1))
                        py = int(vy1 + d_t * (vy2 - vy1))
                        cv2.circle(frame, (px, py), 4, v_col, -1, cv2.LINE_AA)

                # Arrowhead at current tip
                angle = math.atan2(vy2 - vy1, vx2 - vx1)
                tip_len = 16
                p_left = (
                    int(curr_x - tip_len * math.cos(angle - math.pi / 6)),
                    int(curr_y - tip_len * math.sin(angle - math.pi / 6))
                )
                p_right = (
                    int(curr_x - tip_len * math.cos(angle + math.pi / 6)),
                    int(curr_y - tip_len * math.sin(angle + math.pi / 6))
                )
                pts_arrow = np.array([[curr_x, curr_y], p_left, p_right], np.int32)
                cv2.fillPoly(frame, [pts_arrow], v_col, lineType=cv2.LINE_AA)

                # Pulsing Radar Breach Marker at Target
                pulse_phase = (f_idx % 30) / 30.0
                pulse_radius = int(8 + pulse_phase * 22)
                pulse_alpha = 1.0 - pulse_phase
                overlay = frame.copy()
                cv2.circle(overlay, (vx2, vy2), pulse_radius, (20, 20, 230), 2, cv2.LINE_AA)
                cv2.circle(overlay, (vx2, vy2), 5, (20, 20, 230), -1, cv2.LINE_AA)
                cv2.addWeighted(overlay, pulse_alpha, frame, 1.0 - pulse_alpha, 0, frame)

            # Draw HUD Tactical Badge / Title
            pil_overlay = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            p_draw = ImageDraw.Draw(pil_overlay)
            f_hud_title = _get_font(22, bold=True)
            f_hud_sub = _get_font(15, bold=False)

            # Title card box
            p_draw.rounded_rectangle([(40, 40), (620, 125)], radius=10, fill=(18, 16, 24), outline=(212, 163, 89), width=2)
            p_draw.text((60, 52), title, fill=(240, 195, 115), font=f_hud_title)
            p_draw.text((60, 88), "PRIMARY HISTORICAL CORRIDOR • THEODOSIAN LANDWALL BREACHES", fill=(190, 180, 170), font=f_hud_sub)

            # Vector labels in lower left
            ly = 880
            for idx, v in enumerate(vectors):
                label_txt = f"{v.get('label', 'Troop Movement')} -> {v.get('target_name', 'Breach')}"
                p_draw.rounded_rectangle([(40, ly + idx * 36), (580, ly + idx * 36 + 30)], radius=6, fill=(18, 16, 24), outline=(140, 110, 60), width=1)
                p_draw.text((54, ly + idx * 36 + 5), label_txt, fill=(240, 225, 210), font=f_hud_sub)

            final_frame = cv2.cvtColor(np.array(pil_overlay), cv2.COLOR_RGB2BGR)
            proc.stdin.write(final_frame.tobytes())

        proc.stdin.close()
        _, stderr_data = proc.communicate(timeout=60)
    except Exception as e:
        if proc.stdin and not proc.stdin.closed:
            try:
                proc.stdin.close()
            except Exception:
                pass
        proc.kill()
        raise RuntimeError(f"Tactical map render failed: {e}")

    if proc.returncode != 0:
        err_msg = stderr_data.decode("utf-8", errors="replace") if stderr_data else "Unknown error"
        raise RuntimeError(f"Tactical map FFmpeg process exited with code {proc.returncode}: {err_msg}")

    logger.info(f"[Tactical Map Engine] Successfully rendered {duration_sec}s tactical map -> {output_mp4_path}")
    return output_mp4_path


# ═════════════════════════════════════════════════════════════════════════════
# 3. OVERLAND FLEET TRANSIT ENGINE (70 WARSHIPS ACROSS GALATA RIDGE)
# ═════════════════════════════════════════════════════════════════════════════

def render_overland_fleet_transit(
    elevation_profile: Optional[List[Dict[str, Any]]] = None,
    ship_count: int = 70,
    output_mp4_path: Path = Path("output/overland_fleet_transit.mp4"),
    duration_sec: float = 8.0,
    fps: int = 30
) -> Path:
    """
    Renders an animated timeline tracking Mehmed II's 70 warships hauled
    overland from the Bosporus up over the Galata ridge (~200ft elevation)
    and down into the Golden Horn overnight (April 21–22, 1453).
    Includes:
      - Map route animation with ship markers traversing the ridge
      - Dynamic ship progress counter: "SHIPS TRANSPORTED: X / 70"
      - Elevation profile chart sub-panel showing height ascent/descent
    """
    output_mp4_path = Path(output_mp4_path)
    output_mp4_path.parent.mkdir(parents=True, exist_ok=True)

    w, h = 1920, 1080
    total_frames = int(duration_sec * fps)

    # 1. Start with the historical basemap
    basemap = create_procedural_constantinople_basemap()

    # Overland route coords: From Bosporus shore (x: 1610, y: 320) over Pera ridge (x: 1450, y: 350) into Golden Horn (x: 1180, y: 400)
    route_pts = [
        (1630, 280), # Diplokionion / Dolmabahce on Bosporus
        (1540, 310),
        (1440, 340), # Pera / Galata Ridge Crest (60m elevation)
        (1310, 380),
        (1180, 420)  # Kasimpasa on Golden Horn
    ]

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{w}x{h}",
        "-pix_fmt", "bgr24",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        str(output_mp4_path)
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    try:
        for f_idx in range(total_frames):
            t = f_idx / max(1, total_frames - 1)
            # Smoothstep
            s = 3.0 * (t ** 2) - 2.0 * (t ** 3)
            current_ships = int(s * ship_count)

            frame = basemap.copy()

            # Draw Route Line on Map (Golden dotted road with rollers)
            for i in range(len(route_pts) - 1):
                p_start = route_pts[i]
                p_end = route_pts[i + 1]
                cv2.line(frame, p_start, p_end, (212, 163, 89), 4, cv2.LINE_AA)

            # Draw moving warships along route
            for ship_idx in range(min(current_ships + 1, 14)):
                ship_t = max(0.0, min(1.0, s - (ship_idx * 0.05)))
                if ship_t > 0:
                    # Interpolate along multi-segment route
                    seg_len = 1.0 / (len(route_pts) - 1)
                    seg_idx = min(int(ship_t / seg_len), len(route_pts) - 2)
                    local_t = (ship_t - seg_idx * seg_len) / seg_len

                    sx = int(route_pts[seg_idx][0] + local_t * (route_pts[seg_idx + 1][0] - route_pts[seg_idx][0]))
                    sy = int(route_pts[seg_idx][1] + local_t * (route_pts[seg_idx + 1][1] - route_pts[seg_idx][1]))

                    # Draw warship icon
                    cv2.circle(frame, (sx, sy), 7, (20, 30, 210), -1, cv2.LINE_AA)
                    cv2.circle(frame, (sx, sy), 9, (240, 210, 110), 2, cv2.LINE_AA)

            # Draw Bottom Elevation Profile Sub-Panel
            # Box: x: 1100 to 1860, y: 720 to 1020
            panel_x1, panel_y1, panel_x2, panel_y2 = 1100, 720, 1860, 1020
            cv2.rectangle(frame, (panel_x1, panel_y1), (panel_x2, panel_y2), (20, 18, 24), -1)
            cv2.rectangle(frame, (panel_x1, panel_y1), (panel_x2, panel_y2), (212, 163, 89), 2)

            # Draw Ridge Elevation Curve inside panel
            # Ascent from Bosporus (0m) -> Ridge (60m) -> Golden Horn (0m)
            prof_w = panel_x2 - panel_x1 - 80
            prof_h = panel_y2 - panel_y1 - 100
            curve_pts = []
            for step in np.linspace(0, 1, 50):
                cx = int(panel_x1 + 40 + step * prof_w)
                # Inverted parabola for elevation peak
                height_norm = math.sin(step * math.pi)
                cy = int(panel_y2 - 40 - height_norm * prof_h)
                curve_pts.append([cx, cy])

            cv2.polylines(frame, [np.array(curve_pts, np.int32)], isClosed=False, color=(90, 180, 240), thickness=3, lineType=cv2.LINE_AA)

            # Current elevation marker
            marker_x = int(panel_x1 + 40 + s * prof_w)
            marker_h = math.sin(s * math.pi)
            marker_y = int(panel_y2 - 40 - marker_h * prof_h)
            cv2.circle(frame, (marker_x, marker_y), 8, (20, 20, 240), -1, cv2.LINE_AA)
            cv2.circle(frame, (marker_x, marker_y), 11, (240, 210, 120), 2, cv2.LINE_AA)

            # PIL Overlays for Texts
            pil_f = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            p_draw = ImageDraw.Draw(pil_f)
            f_main = _get_font(24, bold=True)
            f_sub = _get_font(16, bold=False)
            f_huge = _get_font(34, bold=True)

            # Header Badge
            p_draw.rounded_rectangle([(40, 40), (740, 135)], radius=12, fill=(18, 16, 24), outline=(212, 163, 89), width=2)
            p_draw.text((60, 52), "OPERATION OVERLAND FLEET: GALATA RIDGE", fill=(240, 195, 115), font=f_main)
            p_draw.text((60, 92), "NIGHT OF APRIL 21–22, 1453 • BYPASSING THE GOLDEN HORN CHAIN", fill=(200, 190, 180), font=f_sub)

            # Ship Counter HUD in Elevation Panel
            p_draw.text((panel_x1 + 40, panel_y1 + 18), "OVERLAND TRANSIT CONTOUR (2.5 MILES)", fill=(240, 195, 115), font=f_main)
            counter_str = f"WARSHIPS OVERLAND: {current_ships} / {ship_count}"
            p_draw.text((panel_x1 + 40, panel_y1 + 48), counter_str, fill=(255, 230, 120), font=f_huge)
            p_draw.text((panel_x1 + 40, panel_y2 - 32), "BOSPORUS (0m)                     GALATA RIDGE (+60m)                     GOLDEN HORN (0m)", fill=(170, 160, 150), font=f_sub)

            out_bgr = cv2.cvtColor(np.array(pil_f), cv2.COLOR_RGB2BGR)
            proc.stdin.write(out_bgr.tobytes())

        proc.stdin.close()
        _, stderr_data = proc.communicate(timeout=60)
    except Exception as e:
        if proc.stdin and not proc.stdin.closed:
            try:
                proc.stdin.close()
            except Exception:
                pass
        proc.kill()
        raise RuntimeError(f"Overland fleet transit animation failed: {e}")

    if proc.returncode != 0:
        err_msg = stderr_data.decode("utf-8", errors="replace") if stderr_data else "Unknown error"
        raise RuntimeError(f"FFmpeg overland transit animation process exited with code {proc.returncode}: {err_msg}")

    logger.info(f"[Tactical Map Engine] Successfully rendered {duration_sec}s overland fleet transit -> {output_mp4_path}")
    return output_mp4_path
