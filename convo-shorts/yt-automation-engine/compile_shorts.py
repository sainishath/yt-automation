#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compile_shorts.py
-----------------
Long-form Compilation Engine.

Converts a sequence of 9:16 YouTube Shorts into a single 16:9 horizontal
video - each Short gets a blurred full-width cinematic background with the
crisp 9:16 clip overlaid in the centre.

Usage:
    python compile_shorts.py --all
    python compile_shorts.py --from_clip Short_004

FFmpeg stream-splitting note:
    [0:v] is referenced twice (blur bg + sharp fg), so we use split=2 to
    declare two named pads [bg_src][fg_src], preventing the
    "Input pad already connected" error on older FFmpeg builds.
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path


# -- Config -------------------------------------------------------------------

def _load_config() -> dict:
    cfg_path = Path(__file__).parent / "config.json"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)


# -- ffprobe integrity check --------------------------------------------------

def _is_valid_video(file_path: str) -> bool:
    """Use ffprobe to confirm the file is a non-corrupt video with a duration."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        return result.returncode == 0 and result.stdout.strip() != ""
    except FileNotFoundError:
        print("[ffprobe] WARNING: ffprobe not found -- skipping integrity check.")
        return True  # Assume valid if ffprobe missing


# -- Per-clip 9:16 to 16:9 transcode ------------------------------------------

def _transcode_clip(input_path: str, output_path: str, idx: int, total: int) -> bool:
    """
    Convert a 9:16 Short to a cinematic 16:9 clip.
    Uses split=2 to avoid filter-graph pad-reuse errors.
    """
    filter_str = (
        "[0:v]split=2[bg_src][fg_src]; "
        "[bg_src]scale=1920:1080:force_original_aspect_ratio=increase,"
        "crop=1920:1080,boxblur=20:10[bg]; "
        "[fg_src]scale=608:1080[fg]; "
        "[bg][fg]overlay=(W-w)/2:(H-h)/2[v_out]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-filter_complex", filter_str,
        "-map", "[v_out]", "-map", "0:a",
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-c:a", "aac", "-ar", "44100",
        output_path,
    ]

    name = Path(input_path).name
    print(f"  [{idx:02d}/{total:02d}] Transcoding {name} -> 16:9...")
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    if result.returncode != 0:
        err = result.stderr.decode("utf-8", errors="ignore")[-1000:]
        print(f"  WARNING: FFmpeg error for {name}:\n{err}")
        return False

    size_mb = Path(output_path).stat().st_size / (1024 * 1024)
    print(f"         Done ({size_mb:.1f} MB)")
    return True


# -- Main compilation ---------------------------------------------------------

def build_compilation(from_clip: str = None, process_all: bool = False) -> None:
    cfg        = _load_config()
    video_dir  = cfg.get("output_dir",  "./videos")
    temp_dir   = cfg.get("temp_dir",    "./temp")
    out_name   = cfg.get("compilation_output_name", "compilation_weekly.mp4")

    os.makedirs(temp_dir, exist_ok=True)

    # Discover and validate source Shorts
    all_shorts = sorted(
        f for f in os.listdir(video_dir)
        if f.startswith("Short_") and f.endswith(".mp4")
    )

    valid_shorts = []
    print(f"\nScanning {len(all_shorts)} candidate files in {video_dir}...")
    for name in all_shorts:
        full = os.path.join(video_dir, name)
        if _is_valid_video(full):
            valid_shorts.append(name)
        else:
            print(f"  Skipping corrupt/unreadable file: {name}")

    if not valid_shorts:
        print("ERROR: No valid Shorts found. Aborting.")
        sys.exit(1)

    # Apply --from_clip boundary
    if not process_all and from_clip:
        if from_clip in valid_shorts:
            start_idx    = valid_shorts.index(from_clip)
            valid_shorts = valid_shorts[start_idx:]
            print(f"Starting from: {from_clip} ({len(valid_shorts)} clips selected)")
        else:
            print(f"WARNING: '{from_clip}' not found. Processing all.")

    print(f"\nTarget sequence ({len(valid_shorts)} clips): {valid_shorts}\n")

    # Transcode each clip
    processed = []
    total = len(valid_shorts)

    for idx, short_name in enumerate(valid_shorts, start=1):
        input_path  = os.path.join(video_dir, short_name)
        output_path = os.path.join(temp_dir, f"compiled_trans_{idx:03d}.mp4")

        success = _transcode_clip(input_path, output_path, idx, total)
        if success:
            processed.append(output_path)
        else:
            print(f"  Skipping {short_name} due to transcode failure.")

    if not processed:
        print("ERROR: All transcodes failed. Aborting concat step.")
        sys.exit(1)

    # Write FFmpeg concat manifest
    manifest_path = os.path.join(temp_dir, "concat_manifest.txt")
    with open(manifest_path, "w", encoding="utf-8") as mf:
        for clip in processed:
            safe = os.path.abspath(clip).replace("\\", "/")
            mf.write(f"file '{safe}'\n")

    # Concatenate
    final_path = os.path.join(video_dir, out_name)
    print(f"\nConcatenating {len(processed)} clips -> {final_path}")

    concat_cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", manifest_path,
        "-c", "copy",
        final_path,
    ]
    result = subprocess.run(concat_cmd, capture_output=True)

    if result.returncode != 0:
        err = result.stderr.decode("utf-8", errors="ignore")[-1000:]
        print(f"ERROR: Concat failed:\n{err}")
        sys.exit(1)

    final_mb = Path(final_path).stat().st_size / (1024 * 1024)
    print(f"Compilation complete: {final_path}  ({final_mb:.1f} MB)")

    # Cleanup temp files
    print("Cleaning up temp transcodes...")
    for clip in processed:
        try:
            os.remove(clip)
        except OSError:
            pass
    try:
        os.remove(manifest_path)
    except OSError:
        pass

    print("Done. Ready to upload.")


# -- CLI ----------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Piper-YT Long-Form Compilation Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python compile_shorts.py --all\n"
            "  python compile_shorts.py --from_clip Short_004\n"
        ),
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--all",
        action="store_true",
        help="Compile every valid Short in the output directory.",
    )
    group.add_argument(
        "--from_clip",
        metavar="Short_00X",
        type=str,
        help="Compile sequentially starting from this Short onward.",
    )

    args = parser.parse_args()
    build_compilation(from_clip=args.from_clip, process_all=args.all)
