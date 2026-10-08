# -*- coding: utf-8 -*-
"""
render_act1_benchmark.py
------------------------
Gate Test: Renders Act 1 of "The Fall of Constantinople (1453)" with the new 80-shot visual density.
- 11 distinct Fooocus SDXL 16:9 images (~7.14s per cut).
- Strict zero-stretch geometry enforcement (1920x1080).
- Alternating smoothstep motion archetypes (push-in, pan-right, pull-out, pan-left-up).
- Authoritative Edge-TTS narration + 7% ambient orchestral BGM.
- Output: longform_engine/drafts/test_act1_80shot_cinematic.mp4
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path

ROOT_DIR = Path("D:/Projects/yt-automations")
sys.path.insert(0, str(ROOT_DIR))

from longform_engine.assemble_longform import (
    synthesize_speech,
    get_audio_duration,
    generate_16x9_visual,
    EDGE_TTS_VOICE_P1
)
from longform_engine.motion_engine import render_cinematic_shot

SCRIPT_JSON = ROOT_DIR / "longform_engine" / "drafts" / "history_10min_80shots.json"
OUT_DIR = ROOT_DIR / "longform_engine" / "drafts" / "act1_benchmark"
OUT_MASTER = ROOT_DIR / "longform_engine" / "drafts" / "test_act1_80shot_cinematic.mp4"
BGM_FILE = ROOT_DIR / "alternate-history-shorts" / "config" / "bg_music.mp3"


def run_act1_benchmark():
    print("=" * 70)
    print("  ACT 1 BENCHMARK: 11-SHOT CINEMATIC KEN-BURNS GATE TEST")
    print("=" * 70)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    images_dir = OUT_DIR / "images"
    clips_dir = OUT_DIR / "clips"
    images_dir.mkdir(parents=True, exist_ok=True)
    clips_dir.mkdir(parents=True, exist_ok=True)

    with open(SCRIPT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    act1 = data["acts"][0]
    script_text = act1["script"]
    shots = act1["shots"]
    num_shots = len(shots)

    # 1. Synthesize Act 1 Audio
    print(f"\n[1/4] Synthesizing Act 1 Narration ({len(script_text.split())} words)...")
    audio_path = OUT_DIR / "act1_voiceover.mp3"
    if not audio_path.exists():
        synthesize_speech(script_text, EDGE_TTS_VOICE_P1, audio_path)
    total_duration = get_audio_duration(audio_path)
    print(f"  ✔ Audio Duration: {total_duration:.2f}s ({total_duration/num_shots:.2f}s per shot across {num_shots} cuts)")

    shot_duration = total_duration / num_shots

    # 2. Generate 11 Fooocus SDXL 16:9 Visuals
    print(f"\n[2/4] Generating/Reusing {num_shots} Native 16:9 Fooocus SDXL Visual Assets...")
    image_paths = []
    neg_prompt = "low quality, blurry, modern clothing, electricity, cars, distorted anatomy, text watermark, stretched, squished"

    for idx, s in enumerate(shots, start=1):
        shot_id = s["shot_id"]
        prompt = s["prompt"]
        img_out = images_dir / f"{shot_id}.png"
        
        print(f"\n  --> [{idx}/{num_shots}] {s['shot_type']} ({s['motion']})")
        print(f"      Prompt: {prompt[:90]}...")
        
        t0 = time.time()
        if not img_out.exists():
            generate_16x9_visual(prompt, neg_prompt, img_out, aspect_ratio="1344*768")
            print(f"      Saved: {img_out.name} ({time.time() - t0:.1f}s)")
        else:
            print(f"      Reusing cached: {img_out.name}")
        image_paths.append(img_out)

    # 3. Render 11 Ken-Burns Animated Clips
    print(f"\n[3/4] Rendering 11 Smoothstep Ken-Burns 1080p Video Clips...")
    clip_paths = []
    for idx, (s, img_p) in enumerate(zip(shots, image_paths), start=1):
        clip_out = clips_dir / f"clip_{s['shot_id']}.mp4"
        motion_type = s["motion"]
        
        t0 = time.time()
        render_cinematic_shot(
            image_path=img_p,
            output_mp4_path=clip_out,
            duration_sec=shot_duration,
            motion_type=motion_type,
            fps=30
        )
        print(f"  ✔ Rendered Clip {idx}/{num_shots} ({motion_type}, {shot_duration:.2f}s) in {time.time() - t0:.2f}s")
        clip_paths.append(clip_out)

    # 4. Concatenate & Audio Muxing
    print(f"\n[4/4] Concatenating 11 Clips & Ducking Ambient Orchestral Score...")
    concat_list = OUT_DIR / "concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for c in clip_paths:
            # Use full posix path to eliminate path resolution errors
            f.write(f"file '{c.as_posix()}'\n")

    raw_video = OUT_DIR / "raw_video.mp4"
    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(raw_video)
    ]
    subprocess.run(cmd_concat, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # Final mux with voice and 7% BGM
    if BGM_FILE.exists():
        cmd_final = [
            "ffmpeg", "-y",
            "-i", str(raw_video),
            "-i", str(audio_path),
            "-stream_loop", "-1", "-i", str(BGM_FILE),
            "-filter_complex",
            "[2:a]volume=0.07[bgm];[1:a]volume=1.0[voice];[voice][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(OUT_MASTER)
        ]
    else:
        cmd_final = [
            "ffmpeg", "-y",
            "-i", str(raw_video),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(OUT_MASTER)
        ]

    subprocess.run(cmd_final, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    print("\n" + "=" * 70)
    print(f"  ✔ ACT 1 BENCHMARK COMPLETE!")
    print(f"  Master MP4: {OUT_MASTER}")
    print(f"  File Size: {OUT_MASTER.stat().st_size / (1024*1024):.2f} MB")
    print(f"  Total Duration: {get_audio_duration(OUT_MASTER):.2f}s")
    print("=" * 70)


if __name__ == "__main__":
    run_act1_benchmark()
