# -*- coding: utf-8 -*-
"""
assemble_longform.py
--------------------
End-to-End Media Assembly Pipeline for 10-Minute (16:9 1080p) Long-Form Production.
Supports:
  - Channel B: Coding Masterclass (16:9 Horizontal Split-Screen Cards + Voice + Chapter Markers)
  - Channel A: History Documentary (80-shot visual density, Fooocus SDXL, Smoothstep Ken-Burns Motion Engine, Ambient BGM, Chapter Markers)

Adheres to:
  - Global Rule: Gradio Client API Integration (query components, fn_index=67 setter, async fn_index=68 submit)
  - Global Rule: Windows stdout/stderr Encoding Safety
  - Project Rule: 16:9 Widescreen Ken-Burns pan/zoom & 7% orchestral bed
"""

import os
import sys
import time
import json
import random
import asyncio
import logging
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from longform_engine.horizontal_card_renderer import render_longform_horizontal_card
from longform_engine.motion_engine import render_cinematic_shot
from longform_engine.tactical_map_renderer import (
    render_tactical_siege_map,
    render_overland_fleet_transit,
)
from longform_engine.interactive_overlays import (
    burn_act_badge,
    burn_source_card,
    apply_sidechain_ducking,
)
from pipeline.primary_sources import (
    extract_primary_sources,
    render_source_card,
)
from pipeline.compositor import (
    build_fooocus_scene_prompt,
    detect_split_panel_collage,
    FOOOCUS_NEGATIVE_PROMPT_LOCK,
)

FOOOCUS_URL = os.getenv("FOOOCUS_URL", "http://127.0.0.1:7865")
FOOOCUS_OUTPUTS_DIR = Path(os.getenv("FOOOCUS_OUTPUTS_DIR", str(ROOT_DIR.parent / "Fooocus" / "outputs")))
EDGE_TTS_VOICE_P1 = "en-US-ChristopherNeural"
EDGE_TTS_VOICE_P2 = "en-US-ChristopherNeural"


# ── Audio Synthesis & Duration Helpers ────────────────────────────────────────

async def synthesize_edge_tts_async(text: str, voice: str, out_path: Path) -> Path:
    """Synthesizes high-clarity voiceover track using edge_tts asynchronously."""
    import edge_tts
    out_path.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_path))
    return out_path


def synthesize_speech(text: str, voice: str, out_path: Path) -> Path:
    """Synchronous wrapper for edge_tts synthesis."""
    try:
        asyncio.run(synthesize_edge_tts_async(text, voice, out_path))
        logging.info(f"[TTS] Synthesized {len(text.split())} words -> {out_path.name}")
        return out_path
    except Exception as e:
        logging.error(f"[TTS Error] edge-tts failed: {e}. Falling back to silent wav.")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "85", str(out_path)]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return out_path


def get_audio_duration(file_path: Path) -> float:
    """Returns exact duration of an audio/video file in seconds via ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(file_path)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=True)
    return float(res.stdout.strip())


# ── Fooocus 16:9 Visual Generation (Global Rule Compliant) ────────────────────

def check_fooocus_status(url: str = FOOOCUS_URL) -> bool:
    """Verifies whether the local Fooocus SDXL service is listening and responsive."""
    import urllib.request
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            return True
    except Exception:
        return False


def generate_16x9_visual(
    prompt: str,
    negative_prompt: str,
    output_path: Path,
    aspect_ratio: str = "1344*768",
    style_selections: Optional[List[str]] = None,
    max_retries: int = 2
) -> bool:
    """
    Sends generation request using the strict two-step Gradio API protocol:
      1. Sets parameters dynamically via fn_index=67
      2. Submits generation job asynchronously via fn_index=68 in a wait-loop
    """
    try:
        import shutil
        import tempfile
        from gradio_client import Client

        logging.info(f"[Fooocus 16:9] Connecting to {FOOOCUS_URL}...")
        client = Client(FOOOCUS_URL, verbose=False)

        if len(client.endpoints) <= 68:
            raise RuntimeError(f"Unexpected Fooocus API endpoints structure ({len(client.endpoints)} endpoints).")

        ep67 = client.endpoints[67]
        dep67 = ep67.dependency
        comps = {comp['id']: comp for comp in client.config['components']}

        for attempt in range(1, max_retries + 1):
            try:
                job_start = time.time()
                logging.info(f"[Fooocus 16:9] Generating SDXL 16:9 visual for {output_path.name} (Attempt {attempt}/{max_retries})")

                # Build arguments dynamically
                args = []
                for cid in dep67['inputs']:
                    if cid in comps:
                        comp = comps[cid]
                        val = comp.get('value')
                        if val is None:
                            val = comp.get('props', {}).get('value')
                        args.append(val)
                    else:
                        args.append(None)

                # Sanitize radio types
                for idx, (cid, ctype) in enumerate(zip(dep67['inputs'], ep67.input_component_types)):
                    val = args[idx]
                    if ctype == 'radio' and isinstance(val, list):
                        args[idx] = val[1] if len(val) > 1 else val[0]

                # Overrides
                args[0] = None
                args[1] = False
                args[2] = prompt
                locked_neg = f"{negative_prompt}, {FOOOCUS_NEGATIVE_PROMPT_LOCK}" if negative_prompt else FOOOCUS_NEGATIVE_PROMPT_LOCK
                args[3] = locked_neg
                args[4] = style_selections or ["Fooocus V2", "Fooocus Masterpiece", "Fooocus Cinematic"]
                args[5] = "Speed"

                target_clean = aspect_ratio.replace("*", "×").replace("x", "×").split(" ")[0]
                aspect_choices = comps[dep67['inputs'][6]].get('props', {}).get('choices', [])
                resolved_ratio = aspect_choices[0][1] if isinstance(aspect_choices[0], list) else aspect_choices[0]
                for choice in aspect_choices:
                    val = choice[1] if isinstance(choice, list) else choice
                    if val.startswith(target_clean):
                        resolved_ratio = val
                        break

                args[6] = resolved_ratio
                args[7] = 1
                args[8] = "png"
                args[9] = str(random.randint(1, 1000000000))
                args[13] = "juggernautXL_v8Rundiffusion.safetensors"
                args[14] = "None"
                args[15] = 0.5

                filtered_args = [val for val, ctype in zip(args, ep67.input_component_types) if ctype != 'state']

                gradio_temp = Path(tempfile.gettempdir()) / "gradio"

                # Step 1: Parameter setter
                client.predict(*filtered_args, fn_index=67)

                # Step 2: Asynchronous job submit
                job = client.submit(fn_index=68)
                timeout_sec = 180
                while not job.done():
                    if time.time() - job_start > timeout_sec:
                        try:
                            job.cancel()
                        except Exception:
                            pass
                        raise TimeoutError("Fooocus SDXL generation timed out.")
                    time.sleep(2)

                # Fast Result Extraction: check job.result() directly, avoiding 160 recursive disk globs
                new_img = None
                try:
                    res = job.result()
                    if isinstance(res, (list, tuple)):
                        for item in res:
                            cand_path = None
                            if isinstance(item, str) and item.endswith((".png", ".jpg", ".webp")):
                                cand_path = Path(item)
                            elif isinstance(item, dict) and "name" in item:
                                cand_path = Path(item["name"])
                            elif isinstance(item, (list, tuple)):
                                for sub in item:
                                    if isinstance(sub, str) and sub.endswith((".png", ".jpg", ".webp")):
                                        cand_path = Path(sub)
                                        break
                                    elif isinstance(sub, dict) and "name" in sub:
                                        cand_path = Path(sub["name"])
                                        break
                            if cand_path and cand_path.exists() and cand_path.stat().st_size > 50000:
                                new_img = cand_path
                                break
                except Exception as res_err:
                    logging.debug(f"[Fooocus 16:9] job.result direct extraction notice: {res_err}")

                # Fast fallback: search only files modified since job_start without recursive full-disk scans
                if not new_img:
                    candidates = []
                    search_dirs = [d for d in [FOOOCUS_OUTPUTS_DIR, gradio_temp] if d.exists()]
                    for s_dir in search_dirs:
                        for f in s_dir.glob("*.png"):
                            try:
                                if f.stat().st_mtime >= (job_start - 1.0) and f.stat().st_size > 50000:
                                    candidates.append(f)
                            except Exception:
                                pass
                    if candidates:
                        new_img = max(candidates, key=lambda p: p.stat().st_mtime)

                if new_img and new_img.exists():
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(new_img, output_path)
                    if detect_split_panel_collage(str(output_path)):
                        logging.warning(f"[QA Gate] Defective split-panel collage detected in {output_path.name}; rejecting keyframe.")
                        output_path.unlink(missing_ok=True)
                        continue
                    logging.info(f"[Fooocus 16:9] Generated SDXL visual saved -> {output_path.name} ({time.time() - job_start:.1f}s)")
                    return True

            except Exception as e:
                logging.warning(f"[Fooocus 16:9 Warning] Attempt {attempt} failed: {e}")
                time.sleep(2)

    except Exception as outer_e:
        logging.warning(f"[Fooocus 16:9 Fallback] Fooocus unavailable ({outer_e}). Generating high-contrast proxy canvas.")

    # High-contrast proxy fallback if Fooocus fails
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (1920, 1080), color=(18, 22, 32))
    draw = ImageDraw.Draw(img)
    draw.rectangle([60, 60, 1860, 1020], outline=(70, 85, 120), width=3)
    font = ImageFont.load_default()
    draw.text((100, 100), "PROVISIONAL 16:9 HISTORICAL SCENE PROXY", fill=(255, 200, 80), font=font)
    draw.text((100, 160), f"PROMPT: {prompt[:300]}...", fill=(200, 210, 230), font=font)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path))
    return True


# ── Chapter Metadata Helpers ─────────────────────────────────────────────────

def generate_ffmetadata_file(chapters: List[Dict[str, Any]], output_path: Path) -> Path:
    """Exports FFMETADATA1 file containing chapter markers with millisecond precision."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [";FFMETADATA1", "major_brand=isom", "minor_version=512", "compatible_brands=isomiso2avc1mp41"]
    
    for ch in chapters:
        start_ms = int(ch["start_sec"] * 1000)
        end_ms = int(ch["end_sec"] * 1000)
        lines.append("[CHAPTER]")
        lines.append("TIMEBASE=1/1000")
        lines.append(f"START={start_ms}")
        lines.append(f"END={end_ms}")
        lines.append(f"title={ch['title']}")
        lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    logging.info(f"[Chapter Metadata] Exported {len(chapters)} chapters to: {output_path.name}")
    return output_path


def format_youtube_description_timestamps(chapters: List[Dict[str, Any]]) -> str:
    """Formats YouTube chapter timestamps for video description."""
    lines = []
    for ch in chapters:
        start_s = int(ch["start_sec"])
        minutes = start_s // 60
        seconds = start_s % 60
        lines.append(f"{minutes:02d}:{seconds:02d} - {ch['title']}")
    return "\n".join(lines)


# ── Channel A Assembly Engine ────────────────────────────────────────────────

def assemble_history_documentary(script_path: Path, output_dir: Path, split_shorts: bool = False, allow_proxies: bool = False) -> Path:
    """
    Renders and assembles the 10-Minute Historical Documentary: The Fall of Constantinople (1453):
      1. Synthesizes 7 act voice tracks via edge_tts (authoritative documentary tone).
      2. Renders 16:9 SDXL scenes via Fooocus with subpixel Ken-Burns pan/zoom movement.
      3. Mixes 7% ambient orchestral bed under voiceover.
      4. Injects FFMETADATA1 chapter markers and exports description timestamps.
    """
    with open(script_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    temp_dir = output_dir / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    images_cache = temp_dir / "images"
    images_cache.mkdir(parents=True, exist_ok=True)
    video_segments = []
    chapters = []
    current_time = 0.0

    bgm_file = ROOT_DIR / "alternate-history-shorts" / "config" / "bg_music.mp3"

    print("\n" + "=" * 70)
    print("  ASSEMBLING CHANNEL A: THE FALL OF CONSTANTINOPLE (1453) (1080p)")
    print("=" * 70)

    # Rule 2 Fooocus SDXL Invariant Guard
    fooocus_live = check_fooocus_status(FOOOCUS_URL)
    if not fooocus_live:
        if not allow_proxies:
            print("\n" + "!" * 75)
            print("  [RULE 2 INVARIANT] LOCAL FOOOCUS SDXL SERVICE IS NOT ACTIVE")
            print(f"  Target Endpoint: {FOOOCUS_URL}")
            print("  Per Rule 2: All visual scenes MUST be generated using local Fooocus SDXL.")
            print("  Zero external cloud image APIs permitted.")
            print("")
            print("  ACTION REQUIRED:")
            print("  1. Launch Fooocus SDXL on your machine (or AWS GPU instance):")
            print("     python launch.py --port 7865")
            print("  2. Once Fooocus is active on http://127.0.0.1:7865, re-run:")
            print("     python longform_engine/assemble_longform.py --draft longform_engine/drafts/history_10min_80shots.json --split-shorts")
            print("  (To test assembly, maps, badges, audio ducking, and shorts with proxies, pass --allow-proxies)")
            print("!" * 75 + "\n")
            sys.exit(1)
        else:
            print("\n  [NOTICE] --allow-proxies flag active. Generating procedural test proxies for SDXL shots.\n")

    for act in data["acts"]:
        a_num = act["act_number"]
        a_title = act["title"]
        print(f"\n--> Processing Act {a_num}: {a_title}...")

        # 1. Synthesize Voiceover
        audio_path = temp_dir / f"act_{a_num:02d}.mp3"
        if not audio_path.exists():
            synthesize_speech(act["script"], EDGE_TTS_VOICE_P1, audio_path)
        duration = get_audio_duration(audio_path)
        print(f"    Audio Duration: {duration:.2f}s ({len(act['script'].split())} words)")

        # 2. Record Chapter Marker
        chapters.append({
            "title": f"Act {a_num}: {a_title}",
            "start_sec": current_time,
            "end_sec": current_time + duration
        })
        current_time += duration

        # Check if multi-shot architecture is present
        shots = act.get("shots", [])
        if shots:
            # ── Multi-Shot High-Density Assembly ─────────────────────────────
            num_shots = len(shots)
            shot_dur = duration / num_shots
            act_clips = []
            neg_prompt = "low quality, blurry, modern clothing, electricity, cars, distorted anatomy, text watermark, stretched, squished"

            for s_idx, s in enumerate(shots, start=1):
                shot_id = s.get("shot_id", f"act{a_num:02d}_shot{s_idx:02d}")
                shot_type = s.get("shot_type", "").strip()
                img_path = images_cache / f"{shot_id}.png"
                clip_path = temp_dir / f"clip_{shot_id}.mp4"
                motion_type = s.get("motion", "push_in")

                if not clip_path.exists():
                    # Route specialized tactical visual shot types
                    if shot_type in ["Tactical Map", "Siege Map", "Ballistics Map"]:
                        logging.info(f"    [Tactical Map] Rendering animated siege vectors ({shot_dur:.1f}s)...")
                        render_tactical_siege_map(
                            vectors=s.get("map_vectors"),
                            output_mp4_path=clip_path,
                            duration_sec=shot_dur,
                            title=f"ACT {a_num}: {a_title.upper()}"
                        )
                    elif shot_type in ["Overland Route", "Overland Fleet", "Fleet Transit", "Overland Transit"]:
                        logging.info(f"    [Overland Transit] Rendering Galata ridge fleet transit ({shot_dur:.1f}s)...")
                        render_overland_fleet_transit(
                            ship_count=70,
                            output_mp4_path=clip_path,
                            duration_sec=shot_dur
                        )
                    elif shot_type in ["Primary Source", "Manuscript Card", "Manuscript Callout"]:
                        logging.info(f"    [Primary Source] Rendering manuscript overlay callout ({shot_dur:.1f}s)...")
                        if not img_path.exists():
                            generate_16x9_visual(s["prompt"], neg_prompt, img_path, aspect_ratio="1344*768")
                        base_clip = temp_dir / f"base_{shot_id}.mp4"
                        render_cinematic_shot(
                            image_path=img_path,
                            output_mp4_path=base_clip,
                            duration_sec=shot_dur,
                            motion_type=motion_type,
                            fps=30
                        )
                        source_dict = s.get("primary_source")
                        if not source_dict:
                            sources = extract_primary_sources("fall_of_constantinople_1453")
                            source_dict = sources[min(a_num - 1, len(sources) - 1)] if sources else {}
                        if source_dict:
                            card_png = temp_dir / f"card_{shot_id}.png"
                            render_source_card(source_dict, card_png)
                            burn_source_card(base_clip, clip_path, card_png, start_sec=0.5, duration_sec=max(2.0, shot_dur - 1.0))
                        else:
                            clip_path = base_clip
                    else:
                        # Standard Photorealistic Cinematic SDXL Visual Shot
                        if not img_path.exists():
                            generate_16x9_visual(s["prompt"], neg_prompt, img_path, aspect_ratio="1344*768")
                        render_cinematic_shot(
                            image_path=img_path,
                            output_mp4_path=clip_path,
                            duration_sec=shot_dur,
                            motion_type=motion_type,
                            fps=30
                        )

                act_clips.append(clip_path)

            # Concatenate act clips into act video segment
            act_concat_list = temp_dir / f"concat_act_{a_num:02d}.txt"
            with open(act_concat_list, "w", encoding="utf-8") as f:
                for c in act_clips:
                    f.write(f"file '{c.as_posix()}'\n")

            seg_video_only = temp_dir / f"video_act_{a_num:02d}.mp4"
            cmd_act_concat = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", str(act_concat_list),
                "-c", "copy",
                str(seg_video_only)
            ]
            subprocess.run(cmd_act_concat, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

            # Mux act video with synthesized audio
            seg_mp4 = temp_dir / f"seg_act_{a_num:02d}.mp4"
            cmd_mux = [
                "ffmpeg", "-y",
                "-i", str(seg_video_only),
                "-i", str(audio_path),
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                str(seg_mp4)
            ]
            subprocess.run(cmd_mux, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

            # Burn Upper-Right Act Progress Badge (X=1520, Y=60) with 0.5s fade-in/out
            seg_badged = temp_dir / f"seg_act_{a_num:02d}_badged.mp4"
            hist_date = act.get("historical_date", "1453 AD")
            try:
                burn_act_badge(seg_mp4, seg_badged, a_num, a_title, hist_date, duration=duration)
                video_segments.append(seg_badged)
            except Exception as badge_err:
                logging.warning(f"Failed to burn act badge ({badge_err}); using unbadged segment.")
                video_segments.append(seg_mp4)
            print(f"    Rendered 1080p High-Density Act Segment with Badges ({num_shots} shots, {duration:.2f}s)")

        else:
            # ── Single-Shot Fallback ──────────────────────────────────────────
            primary_prompt = act["visual_prompts"][0]
            neg_prompt = "low quality, blurry, modern clothing, electricity, cars, distorted anatomy, text watermark"
            img_path = temp_dir / f"visual_act_{a_num:02d}.png"
            if not img_path.exists():
                generate_16x9_visual(primary_prompt, neg_prompt, img_path, aspect_ratio="1344*768")

            seg_mp4 = temp_dir / f"seg_act_{a_num:02d}.mp4"
            render_cinematic_shot(
                image_path=img_path,
                output_mp4_path=seg_mp4,
                duration_sec=duration,
                motion_type="push_in",
                fps=30
            )
            # Add audio
            seg_with_audio = temp_dir / f"seg_act_{a_num:02d}_audio.mp4"
            cmd_mux = [
                "ffmpeg", "-y",
                "-i", str(seg_mp4),
                "-i", str(audio_path),
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                str(seg_with_audio)
            ]
            subprocess.run(cmd_mux, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            video_segments.append(seg_with_audio)
            print(f"    Rendered 1080p Ken-Burns Segment: {seg_mp4.name} ({duration:.2f}s)")

    # 5. Concatenate Segments
    concat_list = temp_dir / "concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for seg in video_segments:
            f.write(f"file '{seg.as_posix()}'\n")

    raw_master = temp_dir / "raw_master.mp4"
    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(raw_master)
    ]
    subprocess.run(cmd_concat, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # 6. Audio Ducking with Ambient Orchestral BGM (Sidechaincompress)
    master_with_bgm = temp_dir / "master_with_bgm.mp4"
    if bgm_file.exists():
        print(f"\n--> Applying FFmpeg sidechaincompress audio ducking (threshold=0.08, ratio=6, release=250ms)...")
        ducked_audio = temp_dir / "master_ducked_audio.m4a"
        try:
            raw_audio = temp_dir / "raw_master_voice.aac"
            subprocess.run(["ffmpeg", "-y", "-i", str(raw_master), "-vn", "-c:a", "copy", str(raw_audio)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            apply_sidechain_ducking(raw_audio, bgm_file, ducked_audio, threshold=0.08, ratio=6.0, release_ms=250)
            cmd_final_mux = [
                "ffmpeg", "-y",
                "-i", str(raw_master),
                "-i", str(ducked_audio),
                "-map", "0:v",
                "-map", "1:a",
                "-c:v", "copy",
                "-c:a", "copy",
                "-shortest",
                str(master_with_bgm)
            ]
            subprocess.run(cmd_final_mux, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception as duck_err:
            logging.warning(f"Sidechain ducking fallback ({duck_err}); using amix.")
            cmd_duck = [
                "ffmpeg", "-y",
                "-i", str(raw_master),
                "-stream_loop", "-1", "-i", str(bgm_file),
                "-filter_complex",
                "[1:a]volume=0.07[bgm];[0:a]volume=1.0[voice];[voice][bgm]amix=inputs=2:duration=first:dropout_transition=3[aout]",
                "-map", "0:v", "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k",
                str(master_with_bgm)
            ]
            subprocess.run(cmd_duck, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    else:
        master_with_bgm = raw_master

    # 7. Inject Chapter Markers
    meta_path = temp_dir / "chapters.ffmetadata"
    generate_ffmetadata_file(chapters, meta_path)

    final_master = output_dir / "constantinople_1453_10min_master.mp4"
    cmd_meta = [
        "ffmpeg", "-y",
        "-i", str(master_with_bgm),
        "-i", str(meta_path),
        "-map_metadata", "1",
        "-codec", "copy",
        str(final_master)
    ]
    subprocess.run(cmd_meta, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # 8. Export YouTube Description
    yt_desc_path = output_dir / "youtube_description.txt"
    desc_content = (
        f"{data['video_title']}\n\n"
        f"In 1453, fifty-three days of brutal siege ended a millennium of Roman imperial civilization. "
        f"From the 26-foot Basilic supercannons of master founder Urban to the overland transport of 70 warships "
        f"into the Golden Horn, this documentary traces the collapse of the Theodosian Walls and the dawn of the modern world.\n\n"
        f"CHAPTERS & TIMESTAMPS:\n"
        f"{format_youtube_description_timestamps(chapters)}\n\n"
        f"#History #Constantinople #ByzantineEmpire #OttomanEmpire #Documentary"
    )
    with open(yt_desc_path, "w", encoding="utf-8") as f:
        f.write(desc_content)

    print("\n" + "=" * 70)
    print(f"  ✔ CHANNEL A MASTER ASSEMBLY COMPLETE!")
    print(f"  Master MP4: {final_master}")
    print(f"  Total Duration: {current_time:.1f}s ({current_time/60:.2f} minutes)")
    print(f"  Description: {yt_desc_path}")
    print("=" * 70)

    if split_shorts:
        print("\n" + "-" * 70)
        print("  --> AUTO-SPLITTING 16:9 MASTER INTO 5 VIRAL 9:16 SHORTS (--split-shorts)")
        print("-" * 70)
        from longform_engine.short_splitter import split_master_into_shorts
        shorts_dir = output_dir / "shorts"
        split_master_into_shorts(final_master, manifest_path=script_path, output_dir=shorts_dir)
        print(f"  ✔ 5 Mobile-Safe 9:16 Shorts Generated in: {shorts_dir}")

    return final_master


# ── Channel B Assembly Engine ────────────────────────────────────────────────

def assemble_coding_masterclass(script_path: Path, output_dir: Path) -> Path:
    """Renders and assembles the 10-Minute Python Zero-to-Hero Masterclass."""
    with open(script_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    temp_dir = output_dir / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    video_segments = []
    chapters = []
    current_time = 0.0

    print("\n" + "=" * 70)
    print("  ASSEMBLING CHANNEL B: PYTHON ZERO-TO-HERO MASTERCLASS (1080p)")
    print("=" * 70)

    for mod in data["modules"]:
        m_num = mod["module_number"]
        m_title = mod["title"]
        print(f"\n--> Processing Module {m_num}: {m_title}...")

        audio_path = temp_dir / f"module_{m_num:02d}.mp3"
        if not audio_path.exists():
            synthesize_speech(mod["script"], EDGE_TTS_VOICE_P2, audio_path)
        duration = get_audio_duration(audio_path)
        print(f"    Audio Duration: {duration:.2f}s ({len(mod['script'].split())} words)")

        chapters.append({
            "title": f"Module {m_num}: {m_title}",
            "start_sec": current_time,
            "end_sec": current_time + duration
        })
        current_time += duration

        card_img_path = temp_dir / f"card_module_{m_num:02d}.png"
        render_longform_horizontal_card(
            code_snippet=mod["code_card"]["code"],
            module_number=m_num,
            module_title=m_title,
            key_takeaways=mod["code_card"]["key_takeaways"],
            output_preview=mod["code_card"]["output_preview"],
            output_path=str(card_img_path)
        )

        seg_mp4 = temp_dir / f"seg_module_{m_num:02d}.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(card_img_path),
            "-i", str(audio_path),
            "-c:v", "libx264", "-tune", "stillimage",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-t", f"{duration:.3f}",
            "-shortest",
            str(seg_mp4)
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        video_segments.append(seg_mp4)
        print(f"    Rendered 1080p Segment: {seg_mp4.name} ({duration:.2f}s)")

    concat_list = temp_dir / "concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for seg in video_segments:
            f.write(f"file '{seg.as_posix()}'\n")

    raw_master = temp_dir / "raw_master.mp4"
    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(raw_master)
    ]
    subprocess.run(cmd_concat, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    meta_path = temp_dir / "chapters.ffmetadata"
    generate_ffmetadata_file(chapters, meta_path)

    final_master = output_dir / "python_masterclass_10min_master.mp4"
    cmd_meta = [
        "ffmpeg", "-y",
        "-i", str(raw_master),
        "-i", str(meta_path),
        "-map_metadata", "1",
        "-codec", "copy",
        str(final_master)
    ]
    subprocess.run(cmd_meta, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    yt_desc_path = output_dir / "youtube_description.txt"
    desc_content = (
        f"{data['video_title']}\n\n"
        f"Master the 7 foundational mental models, memory pointers, dynamic typing rules, "
        f"and software engineering best practices that separate senior developers from beginners.\n\n"
        f"TIMESTAMPS & CHAPTERS:\n"
        f"{format_youtube_description_timestamps(chapters)}\n\n"
        f"#Python #Programming #ComputerScience #SoftwareEngineering #LearnPython"
    )
    with open(yt_desc_path, "w", encoding="utf-8") as f:
        f.write(desc_content)

    print("\n" + "=" * 70)
    print(f"  ✔ CHANNEL B MASTER ASSEMBLY COMPLETE!")
    print(f"  Master MP4: {final_master}")
    print(f"  Total Duration: {current_time:.1f}s ({current_time/60:.2f} minutes)")
    print(f"  Description: {yt_desc_path}")
    print("=" * 70)

    return final_master


# ── Main Entrypoint ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="10-Minute Long-Form Media Assembly Pipeline")
    parser.add_argument("--draft", "--script", "--input", dest="draft", type=str, required=True, help="Path to Stage-1 script JSON draft")
    parser.add_argument("--type", "--channel", dest="type", type=str, default=None, choices=["coding", "history"], help="Pipeline type")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory")
    parser.add_argument("--split-shorts", action="store_true", help="Automatically carve 5 vertical 9:16 Shorts from master")
    parser.add_argument("--allow-proxies", action="store_true", help="Allow provisional canvas proxies if Fooocus is not running")

    args = parser.parse_args()
    script_path = Path(args.draft)
    if not script_path.exists():
        print(f"Error: Script file not found: {script_path}")
        sys.exit(1)

    pipe_type = args.type
    if not pipe_type:
        name_lower = script_path.name.lower()
        if "coding" in name_lower or "python" in name_lower:
            pipe_type = "coding"
        else:
            pipe_type = "history"

    out_dir = Path(args.output_dir) if args.output_dir else (ROOT_DIR / "longform_engine" / "output" / f"{pipe_type}_10min")
    out_dir.mkdir(parents=True, exist_ok=True)

    if pipe_type == "coding":
        assemble_coding_masterclass(script_path, out_dir)
    elif pipe_type == "history":
        assemble_history_documentary(script_path, out_dir, split_shorts=args.split_shorts, allow_proxies=args.allow_proxies)


if __name__ == "__main__":
    main()
