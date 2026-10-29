# -*- coding: utf-8 -*-
"""
longform_engine/interactive_overlays.py
---------------------------------------
Interactive Visual Overlay Engine for Long-Form Documentaries.
Provides:
  1. Upper-Right Dynamic Act Progress Badges (X=1520, Y=60) with 0.5s fade-in/out
  2. Archival Manuscript / Primary Source Callout Overlays with alpha transparency
  3. Sidechain Audio Compression (threshold=0.08, ratio=6, release=250ms)
     to dynamically dip background orchestral score under voiceover narration.
"""

import os
import sys
import logging
import subprocess
from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def _get_overlay_font(size: int = 20, bold: bool = True) -> ImageFont.ImageFont:
    """Loads clean sans-serif/serif font for HUD overlays."""
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
# 1. UPPER-RIGHT ACT PROGRESS BADGE GENERATOR & OVERLAY
# ═════════════════════════════════════════════════════════════════════════════

def create_act_badge_png(
    act_number: int,
    act_title: str,
    historical_date: str,
    output_png: Path,
    width: int = 360,
    height: int = 86
) -> Path:
    """
    Renders a subtle, semi-transparent HUD pill badge for placement at (1520, 60).
    Displays:
      - Line 1: ACT {act_number} • {historical_date}
      - Line 2: {act_title}
    """
    output_png = Path(output_png)
    output_png.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Pill Background: rgba(16, 14, 20, 215) with golden border
    draw.rounded_rectangle(
        [(2, 2), (width - 2, height - 2)],
        radius=12,
        fill=(16, 14, 22, 210),
        outline=(212, 163, 89, 220),
        width=2
    )

    # 2. Typography
    font_sub = _get_overlay_font(15, bold=True)
    font_title = _get_overlay_font(18, bold=True)

    header_line = f"ACT {act_number} • {historical_date.upper()}"
    draw.text((20, 16), header_line, fill=(240, 195, 115, 255), font=font_sub)

    # Truncate title if long
    disp_title = act_title if len(act_title) <= 30 else act_title[:27] + "..."
    draw.text((20, 44), disp_title, fill=(255, 255, 255, 245), font=font_title)

    img.save(output_png, "PNG")
    return output_png


def burn_act_badge(
    clip_path: Optional[Path] = None,
    *args,
    input_video: Optional[Path] = None,
    output_video: Optional[Path] = None,
    act_number: Optional[int] = None,
    act_title: Optional[str] = None,
    historical_date: Optional[str] = None,
    out_path: Optional[Path] = None,
    duration: Optional[float] = None,
    fade_in_sec: float = 0.5,
    fade_out_sec: float = 0.5,
    pos_x: int = 1520,
    pos_y: int = 60,
    **kwargs
) -> Path:
    """
    Burns an Upper-Right Act Progress Badge into the video at (X=1520, Y=60).
    Fades in at start (0.5s fade) and fades out at act conclusion (0.5s fade).
    Supports signatures:
      burn_act_badge(clip_path, act_number, act_title, historical_date, out_path)
      burn_act_badge(input_video, output_video, act_number, act_title, historical_date, duration)
    """
    in_video = Path(clip_path or input_video or (args[0] if len(args) > 0 and isinstance(args[0], (str, Path)) else None))
    if in_video is None:
        raise ValueError("Input video path must be provided.")

    # Unpack polymorphic arguments
    if len(args) >= 1:
        if isinstance(args[0], int):
            act_number = args[0]
            if len(args) >= 2:
                act_title = str(args[1])
            if len(args) >= 3:
                historical_date = str(args[2])
            if len(args) >= 4:
                out_path = Path(args[3])
        elif isinstance(args[0], (str, Path)):
            out_path = Path(args[0])
            if len(args) >= 2 and isinstance(args[1], int):
                act_number = args[1]
            if len(args) >= 3:
                act_title = str(args[2])
            if len(args) >= 4:
                historical_date = str(args[3])
            if len(args) >= 5 and isinstance(args[4], (int, float)):
                duration = float(args[4])

    final_out = Path(out_path or output_video or (in_video.parent / f"{in_video.stem}_badged.mp4"))
    final_out.parent.mkdir(parents=True, exist_ok=True)

    act_number = act_number or 1
    act_title = act_title or "Chapter"
    historical_date = historical_date or "1453 AD"

    # Auto-detect duration via ffprobe if not explicitly supplied
    if duration is None:
        try:
            probe = subprocess.run([
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(in_video)
            ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=True)
            duration = float(probe.stdout.strip())
        except Exception:
            duration = 8.0

    # Temporary badge PNG
    badge_png = final_out.parent / f"badge_act_{act_number:02d}.png"
    create_act_badge_png(act_number, act_title, historical_date, badge_png)

    # Fade timing
    fade_out_start = max(0.1, duration - fade_out_sec)

    filtergraph = (
        f"[1:v]format=rgba,"
        f"fade=t=in:st=0.0:d={fade_in_sec}:alpha=1,"
        f"fade=t=out:st={fade_out_start:.2f}:d={fade_out_sec}:alpha=1[badge];"
        f"[0:v][badge]overlay={pos_x}:{pos_y}:eof_action=pass[vout]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(in_video),
        "-i", str(badge_png),
        "-filter_complex", filtergraph,
        "-map", "[vout]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "copy",
        str(final_out)
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
    logger.info(f"[Interactive Overlays] Burned Act {act_number} badge at ({pos_x}, {pos_y}) -> {final_out.name}")
    return final_out


# ═════════════════════════════════════════════════════════════════════════════
# 2. PRIMARY SOURCE / MANUSCRIPT DOCUMENT CALLOUT OVERLAY
# ═════════════════════════════════════════════════════════════════════════════

def burn_source_card(
    input_video: Path,
    output_video: Path,
    source_card_png: Path,
    start_sec: float = 1.0,
    duration_sec: float = 6.0,
    fade_sec: float = 0.5
) -> Path:
    """
    Overlays a 1920x1080 transparent manuscript card onto the video clip.
    Fades in smoothly at start_sec and fades out before conclusion.
    """
    input_video = Path(input_video)
    output_video = Path(output_video)
    output_video.parent.mkdir(parents=True, exist_ok=True)

    fade_out_start = max(start_sec + 0.1, start_sec + duration_sec - fade_sec)

    filtergraph = (
        f"[1:v]format=rgba,"
        f"fade=t=in:st={start_sec:.2f}:d={fade_sec}:alpha=1,"
        f"fade=t=out:st={fade_out_start:.2f}:d={fade_sec}:alpha=1[card];"
        f"[0:v][card]overlay=0:0:enable='between(t,{start_sec:.2f},{start_sec + duration_sec:.2f})'[vout]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_video),
        "-i", str(source_card_png),
        "-filter_complex", filtergraph,
        "-map", "[vout]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "copy",
        str(output_video)
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
    logger.info(f"[Interactive Overlays] Burned primary source callout -> {output_video.name}")
    return output_video


# ═════════════════════════════════════════════════════════════════════════════
# 3. SIDECHAIN AUDIO DUCKING ENGINE (FFMPEG sidechaincompress)
# ═════════════════════════════════════════════════════════════════════════════

def apply_sidechain_ducking(
    narration_wav: Optional[Path] = None,
    bgm_wav: Optional[Path] = None,
    *args,
    sfx_wav: Optional[Path] = None,
    out_wav: Optional[Path] = None,
    voice_path: Optional[Path] = None,
    bgm_path: Optional[Path] = None,
    output_audio: Optional[Path] = None,
    threshold: float = 0.08,
    ratio: float = 6.0,
    release_ms: int = 250,
    bgm_volume: float = 0.18,
    **kwargs
) -> Path:
    """
    Applies FFmpeg sidechaincompress to dynamically duck the background orchestral
    score under the voiceover track.
    Supports signatures:
      apply_sidechain_ducking(narration_wav, bgm_wav, sfx_wav, out_wav)
      apply_sidechain_ducking(voice_path, bgm_path, output_audio, ...)
    """
    v_path = Path(narration_wav or voice_path or (args[0] if len(args) > 0 else None))
    b_path = Path(bgm_wav or bgm_path or (args[1] if len(args) > 1 else None))

    # Handle remaining positional args
    if len(args) >= 3:
        if len(args) == 3:
            # Called with (voice, bgm, output)
            target_out = Path(args[2])
        else:
            # Called with (voice, bgm, sfx, output)
            sfx_wav = Path(args[2]) if args[2] is not None else None
            target_out = Path(args[3])
    else:
        target_out = Path(out_wav or output_audio or (v_path.parent / f"{v_path.stem}_ducked.m4a"))

    target_out.parent.mkdir(parents=True, exist_ok=True)

    if not b_path.exists():
        logger.warning(f"[Sidechain Ducking] BGM file '{b_path}' not found; passing raw voiceover.")
        cmd = ["ffmpeg", "-y", "-i", str(v_path), "-c:a", "aac", "-b:a", "192k", str(target_out)]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return target_out

    # Build filtergraph
    has_sfx = sfx_wav is not None and Path(sfx_wav).exists()
    if has_sfx:
        filtergraph = (
            f"[1:a]volume={bgm_volume}[bgm_norm];"
            f"[2:a]volume=0.25[sfx_norm];"
            f"[bgm_norm][sfx_norm]amix=inputs=2[bed];"
            f"[bed][0:a]sidechaincompress="
            f"threshold={threshold}:ratio={ratio}:attack=20:release={release_ms}[ducked_bed];"
            f"[0:a][ducked_bed]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", str(v_path),
            "-stream_loop", "-1", "-i", str(b_path),
            "-stream_loop", "-1", "-i", str(sfx_wav),
            "-filter_complex", filtergraph,
            "-map", "[aout]",
            "-c:a", "aac",
            "-b:a", "192k",
            str(target_out)
        ]
    else:
        filtergraph = (
            f"[1:a]volume={bgm_volume}[bgm_norm];"
            f"[bgm_norm][0:a]sidechaincompress="
            f"threshold={threshold}:ratio={ratio}:attack=20:release={release_ms}[ducked_bgm];"
            f"[0:a][ducked_bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", str(v_path),
            "-stream_loop", "-1", "-i", str(b_path),
            "-filter_complex", filtergraph,
            "-map", "[aout]",
            "-c:a", "aac",
            "-b:a", "192k",
            str(target_out)
        ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
    logger.info(f"[Sidechain Audio Ducking] Applied sidechaincompress (ratio={ratio}, release={release_ms}ms) -> {target_out.name}")
    return target_out
