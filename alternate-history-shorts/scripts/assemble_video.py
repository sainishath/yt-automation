import os
import sys
import json
import time
import shutil
import subprocess
import argparse
import logging
import re
from pathlib import Path

# Setup logging to pipeline.log and stdout
LOG_FILE = Path("pipeline.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

def format_ass_timestamp(seconds: float) -> str:
    """Formats seconds into ASS timestamp format H:MM:SS.cs"""
    cs = int(round(seconds * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def map_color_to_ass(color_name: str) -> str:
    color_map = {
        "white": "&H00FFFFFF",
        "black": "&H00000000",
        "yellow": "&H0000FFFF",
        "cyan": "&H00FFFF00",
        "magenta": "&H00FF00FF"
    }
    cleaned = color_name.lower().strip()
    return color_map.get(cleaned, cleaned if cleaned.startswith("&h") else "&H00FFFFFF")

def clean_word(w: str) -> str:
    """Strips punctuation and normalizes word to lowercase alphanumeric for matching."""
    return re.sub(r"[^a-zA-Z0-9]", "", w).lower()

def align_words(orig_words: list, whisper_words: list, time_offset: float = 0.0) -> list:
    """
    Robust word-level alignment that pairs script tokens with Whisper word timestamps.
    Handles sub-word splits (e.g., 'steam-powered' -> 'steam' + '-powered') without
    off-by-one shifts or trailing duplicate words.
    """
    aligned = []
    w_idx = 0
    num_w = len(whisper_words)

    for orig_word in orig_words:
        orig_clean = clean_word(orig_word)
        if not orig_clean:
            continue

        if w_idx >= num_w:
            start = (aligned[-1]["end"] - time_offset) if aligned else 0.0
            aligned.append({
                "word": orig_word,
                "start": start + time_offset,
                "end": start + time_offset + 0.3
            })
            continue

        start_time = whisper_words[w_idx]["start"] + time_offset
        end_time = whisper_words[w_idx]["end"] + time_offset
        matched_clean = clean_word(whisper_words[w_idx].get("word", ""))
        w_idx += 1

        # Sub-word accumulation: e.g. steam + powered or iron + fisted
        while len(matched_clean) < len(orig_clean) and w_idx < num_w:
            next_clean = clean_word(whisper_words[w_idx].get("word", ""))
            if next_clean and (next_clean in orig_clean or orig_clean.startswith(matched_clean + next_clean)):
                matched_clean += next_clean
                end_time = whisper_words[w_idx]["end"] + time_offset
                w_idx += 1
            else:
                break

        aligned.append({
            "word": orig_word,
            "start": start_time,
            "end": end_time
        })

    return aligned

def generate_ass_content(aligned_words: list, style_cfg: dict, max_words: int = 3, max_chars: int = 15) -> str:
    """
    Deduplicates consecutive identical words, groups words into readable chunks (2-3 words),
    and generates a v4.00+ ASS subtitle file strictly positioned in the safe zone.
    """
    # 1. Deduplicate consecutive identical words
    deduped = []
    for w in aligned_words:
        w_text = w["word"].strip()
        if deduped:
            prev_text = deduped[-1]["word"].strip()
            if clean_word(w_text) == clean_word(prev_text) and abs(w["start"] - deduped[-1]["end"]) < 0.6:
                # Merge into previous word
                deduped[-1]["end"] = max(deduped[-1]["end"], w["end"])
                continue
        deduped.append(w)

    # 2. Group into chunks
    chunks = []
    chunk = []
    chunk_chars = 0

    for word_info in deduped:
        w_text = word_info["word"].strip()
        if not chunk:
            chunk.append(word_info)
            chunk_chars = len(w_text)
        elif len(chunk) >= max_words or (chunk_chars + len(w_text) + 1 > max_chars):
            chunks.append(chunk)
            chunk = [word_info]
            chunk_chars = len(w_text)
        else:
            chunk.append(word_info)
            chunk_chars += len(w_text) + 1

    if chunk:
        chunks.append(chunk)

    # 3. Build ASS content with enhanced mobile legibility
    font = style_cfg.get("font", "Arial")
    bold = "1"
    if "bold" in font.lower():
        font = font.replace("Bold", "").replace("bold", "").strip()

    size = style_cfg.get("size", 64)
    color = map_color_to_ass(style_cfg.get("color", "white"))
    out_color = map_color_to_ass(style_cfg.get("outline_color", "black"))
    out_width = style_cfg.get("outline_width", 4)
    shadow_depth = style_cfg.get("shadow", 2)
    # MarginV=680 places subtitles squarely in the upper-middle safe zone above mobile UI
    margin_v = style_cfg.get("margin_v", 680)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},{color},&H000000FF,{out_color},&H80000000,{bold},0,0,0,100,100,0,0,1,{out_width},{shadow_depth},2,10,10,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events = []
    for c in chunks:
        start_t = format_ass_timestamp(c[0]["start"])
        end_t = format_ass_timestamp(c[-1]["end"])
        text = " ".join([w["word"].strip() for w in c])
        events.append(f"Dialogue: 0,{start_t},{end_t},Default,,0,0,0,,{text}")

    return header + "\n".join(events) + "\n"

def render_scene_frames_opencv(
    img_path: Path,
    duration: float,
    focal_u: float = 0.50,
    focal_v: float = 0.35,
    zoom_target: float = 1.10,
    t_hit: float = 2.5,
    fps: int = 25,
    out_width: int = 1080,
    out_height: int = 1920
):
    """
    Generator that yields raw BGR bytes for every frame of the scene using OpenCV
    subpixel affine warping with C1 Continuous Smoothstep interpolation (3*tau^2 - 2*tau^3).
    Guarantees ultra-smooth, jitter-free Directional Focal Zoom-In.
    """
    import cv2
    import numpy as np

    img = cv2.imread(str(img_path))
    if img is None:
        raise FileNotFoundError(f"Failed to load image: {img_path}")

    ih, iw = img.shape[:2]
    total_frames = max(1, int(round(duration * fps)))

    start_u, start_v = 0.50, 0.40
    start_zoom = 1.00

    target_zoom = max(1.02, min(1.06, zoom_target if zoom_target > 1.0 else 1.04))
    target_u = max(0.20, min(0.80, focal_u))
    target_v = max(0.20, min(0.65, focal_v))

    target_aspect = out_width / out_height

    for f_idx in range(total_frames):
        tau = f_idx / float(max(1, total_frames - 1))
        smooth_tau = 3.0 * (tau ** 2) - 2.0 * (tau ** 3)

        curr_zoom = start_zoom + (target_zoom - start_zoom) * smooth_tau
        curr_u = start_u + (target_u - start_u) * smooth_tau
        curr_v = start_v + (target_v - start_v) * smooth_tau

        crop_h = ih / curr_zoom
        crop_w = crop_h * target_aspect

        if crop_w > iw:
            crop_w = iw / curr_zoom
            crop_h = crop_w / target_aspect

        center_x = curr_u * iw
        center_y = curr_v * ih

        half_w = crop_w / 2.0
        half_h = crop_h / 2.0
        center_x = max(half_w, min(iw - half_w, center_x))
        center_y = max(half_h, min(ih - half_h, center_y))

        src_pts = np.float32([
            [center_x - half_w, center_y - half_h],
            [center_x + half_w, center_y - half_h],
            [center_x - half_w, center_y + half_h]
        ])
        dst_pts = np.float32([
            [0, 0],
            [out_width, 0],
            [0, out_height]
        ])

        M = cv2.getAffineTransform(src_pts, dst_pts)
        warped = cv2.warpAffine(
            img, M, (out_width, out_height),
            flags=cv2.INTER_LANCZOS4,
            borderMode=cv2.BORDER_REFLECT_101
        )

        yield warped.tobytes()

def build_beat_video_clip(
    idx: int,
    img_path: Path,
    duration: float,
    out_clip_path: Path,
    focal_u: float = 0.50,
    focal_v: float = 0.35,
    zoom_target: float = 1.04,
    t_hit: float = 2.5
) -> bool:
    """
    Renders a single visual beat video clip using OpenCV subpixel warping streamed into FFmpeg stdin.
    """
    fps = 25
    out_w, out_h = 1080, 1920

    cmd_ffmpeg = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{out_w}x{out_h}",
        "-pix_fmt", "bgr24",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "veryfast",
        "-crf", "18",
        "-t", f"{duration:.3f}",
        str(out_clip_path.resolve())
    ]

    try:
        proc = subprocess.Popen(
            cmd_ffmpeg,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        for frame_bytes in render_scene_frames_opencv(
            img_path=img_path,
            duration=duration,
            focal_u=focal_u,
            focal_v=focal_v,
            zoom_target=zoom_target,
            t_hit=t_hit,
            fps=fps,
            out_width=out_w,
            out_height=out_h
        ):
            proc.stdin.write(frame_bytes)

        proc.stdin.close()
        proc.wait()

        if proc.returncode != 0:
            logging.error(f"FFmpeg OpenCV rawvideo stream failed for beat {idx} (code {proc.returncode})")
            return False

    except Exception as e:
        logging.error(f"OpenCV subpixel frame streaming failed for beat {idx}: {e}")
        return False

    return True

def assemble_video(video_id: str, output_dir: str = "output", thumbnail_scene: int = 0) -> str:
    start_time = time.time()

    video_path = Path(output_dir) / video_id
    script_path = video_path / "script.json"

    if not script_path.exists():
        raise FileNotFoundError(f"script.json not found for {video_id} at {script_path}")

    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    # Load assembly config
    _BASE_DIR = Path(__file__).parent.parent.resolve()
    cfg_path = _BASE_DIR / "config" / "assembly.json"
    if not cfg_path.exists():
        cfg_path = Path("config/assembly.json")
    if not cfg_path.exists():
        raise FileNotFoundError(f"assembly.json not found in config/ folder ({cfg_path})")
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    scenes = script.get("scenes", [])
    audio_dir = video_path / "audio"
    images_dir = video_path / "images"
    final_dir = video_path / "final"
    final_dir.mkdir(parents=True, exist_ok=True)

    # 1. Subtitles Preparation (Per-scene and Master)
    style_cfg = cfg.get("caption_style", {})
    alignment_cache_path = audio_dir / "alignment_cache.json"

    all_aligned_words = []
    whisper_model = None

    if alignment_cache_path.exists():
        logging.info("Using cached word alignments from alignment_cache.json...")
        with open(alignment_cache_path, "r", encoding="utf-8") as af:
            cached_data = json.load(af)

        cached_scenes = {s["file_name"]: s for s in cached_data.get("scenes", [])}

        for idx, scene in enumerate(scenes):
            narration = scene.get("narration", "")
            orig_words = narration.split()
            fname = f"scene_{idx:03d}.mp3"
            c_scene = cached_scenes.get(fname, {})
            w_words = c_scene.get("words", [])
            g_start = float(c_scene.get("global_start", 0.0))

            # Scene-level ASS (starts at 0.0)
            scene_aligned = align_words(orig_words, w_words, time_offset=0.0)
            scene_ass_file = audio_dir / f"scene_{idx:03d}.ass"
            scene_ass_content = generate_ass_content(scene_aligned, style_cfg)
            with open(scene_ass_file, "w", encoding="utf-8") as sf:
                sf.write(scene_ass_content)

            # Master-level ASS (starts at global_start)
            master_aligned = align_words(orig_words, w_words, time_offset=g_start)
            all_aligned_words.extend(master_aligned)
    else:
        logging.info("alignment_cache.json not found; running Whisper transcription...")
        import whisper
        model_name = cfg.get("whisper_model", "base.en")
        whisper_model = whisper.load_model(model_name)

        curr_time = 0.0
        for idx, scene in enumerate(scenes):
            narration = scene.get("narration", "")
            orig_words = narration.split()
            audio_file = audio_dir / f"scene_{idx:03d}.mp3"
            if not audio_file.exists():
                raise FileNotFoundError(f"Missing audio file: {audio_file}")

            res = whisper_model.transcribe(
                str(audio_file),
                word_timestamps=True,
                initial_prompt=narration,
                language="en"
            )
            w_words = []
            for seg in res.get("segments", []):
                for w in seg.get("words", []):
                    w_words.append(w)

            # Scene-level ASS
            scene_aligned = align_words(orig_words, w_words, time_offset=0.0)
            scene_ass_file = audio_dir / f"scene_{idx:03d}.ass"
            scene_ass_content = generate_ass_content(scene_aligned, style_cfg)
            with open(scene_ass_file, "w", encoding="utf-8") as sf:
                sf.write(scene_ass_content)

            # Master-level ASS
            master_aligned = align_words(orig_words, w_words, time_offset=curr_time)
            all_aligned_words.extend(master_aligned)

            # Measure audio duration
            dur_probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(audio_file)],
                capture_output=True, text=True
            )
            try:
                curr_time += float(json.loads(dur_probe.stdout)["format"]["duration"])
            except Exception:
                curr_time += float(scene.get("actual_duration_seconds", 5.0))

    # Write Master Subtitles ASS
    master_ass_path = audio_dir / "master_subtitles.ass"
    master_ass_content = generate_ass_content(all_aligned_words, style_cfg)
    with open(master_ass_path, "w", encoding="utf-8") as mf:
        mf.write(master_ass_content)
    logging.info(f"Master subtitle file generated: {master_ass_path.name}")

    # 2. Visual Beats Preparation
    plan_path = video_path / "scene_plan.json"
    visual_beats = []
    if plan_path.exists():
        try:
            with open(plan_path, "r", encoding="utf-8") as pf:
                sp_data = json.load(pf)
                visual_beats = sp_data.get("visual_beats", [])
        except Exception as pe:
            logging.warning(f"Could not load scene_plan.json: {pe}")

    # Fallback to scenes if no visual_beats in plan
    if not visual_beats:
        logging.info("No visual_beats in scene_plan.json; falling back to 1 beat per scene.")
        for idx, s in enumerate(scenes):
            visual_beats.append({
                "beat_id": f"beat_{idx+1:03d}",
                "duration": float(s.get("actual_duration_seconds", s.get("estimated_duration_seconds", 5.0))),
                "focal_u": 0.50,
                "focal_v": 0.35,
                "zoom_target": 1.04,
                "t_hit": 2.5
            })

    total_beats = len(visual_beats)
    logging.info(f"Rendering {total_beats} visual beats with OpenCV Subpixel Ken Burns...")

    beat_clips = []
    all_png_files = sorted(images_dir.glob("beat_*.png"), key=lambda p: int("".join(c for c in p.stem if c.isdigit()) or 0))

    for b_idx, beat in enumerate(visual_beats):
        b_num = b_idx + 1
        dur = float(beat.get("duration", 3.0))
        f_u = float(beat.get("focal_u", 0.50))
        f_v = float(beat.get("focal_v", 0.35))
        z_tgt = float(beat.get("zoom_target", 1.04))
        t_hit = float(beat.get("t_hit", dur * 0.55))

        # Identify image file
        img_candidates = [
            images_dir / f"beat_{b_num:03d}.png",
            images_dir / f"beat_{b_idx:03d}.png",
            images_dir / f"scene_{b_idx:03d}.png"
        ]
        chosen_img = None
        for cand in img_candidates:
            if cand.exists():
                chosen_img = cand
                break

        if not chosen_img:
            if all_png_files:
                clamped_idx = min(b_idx, len(all_png_files) - 1)
                chosen_img = all_png_files[clamped_idx]
            else:
                raise FileNotFoundError(f"No image file found for visual beat {b_num}")

        out_clip = audio_dir / f"beat_{b_idx:03d}_video.mp4"
        logging.info(f"  Rendering beat {b_num}/{total_beats} ({chosen_img.name}, {dur:.2f}s, focal=({f_u:.2f}, {f_v:.2f}))...")
        success = build_beat_video_clip(
            idx=b_idx,
            img_path=chosen_img,
            duration=dur,
            out_clip_path=out_clip,
            focal_u=f_u,
            focal_v=f_v,
            zoom_target=z_tgt,
            t_hit=t_hit
        )
        if not success:
            raise RuntimeError(f"Failed to render video for visual beat {b_idx}")

        beat_clips.append(out_clip)

    # 3. Concatenate Beat Video Clips into raw_visuals.mp4
    video_manifest = audio_dir / "video_concat_manifest.txt"
    with open(video_manifest, "w", encoding="utf-8") as vf:
        for clip in beat_clips:
            vf.write(f"file '{clip.name}'\n")

    raw_visuals = audio_dir / "raw_visuals.mp4"
    concat_video_cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", "video_concat_manifest.txt",
        "-c", "copy",
        str(raw_visuals.resolve())
    ]
    logging.info("Concatenating visual beats into master visual stream...")
    res_vc = subprocess.run(concat_video_cmd, cwd=str(audio_dir), capture_output=True)
    if res_vc.returncode != 0:
        err = res_vc.stderr.decode("utf-8", errors="ignore")[-1000:]
        raise RuntimeError(f"Video concatenation failed:\n{err}")

    # 4. Concatenate Scene Audio Files into master_voice.mp3
    audio_manifest = audio_dir / "audio_concat_manifest.txt"
    with open(audio_manifest, "w", encoding="utf-8") as af:
        for idx in range(len(scenes)):
            af.write(f"file 'scene_{idx:03d}.mp3'\n")

    master_voice = audio_dir / "master_voice.mp3"
    concat_audio_cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", "audio_concat_manifest.txt",
        "-c", "copy",
        str(master_voice.resolve())
    ]
    logging.info("Concatenating scene voice audio into master voice stream...")
    res_ac = subprocess.run(concat_audio_cmd, cwd=str(audio_dir), capture_output=True)
    if res_ac.returncode != 0:
        err = res_ac.stderr.decode("utf-8", errors="ignore")[-1000:]
        raise RuntimeError(f"Audio concatenation failed:\n{err}")

    # Calculate master audio duration for strict sync
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        str(master_voice.resolve())
    ]
    res_p = subprocess.run(probe_cmd, capture_output=True, text=True)
    master_duration = float(json.loads(res_p.stdout)["format"]["duration"])
    logging.info(f"Master voice duration: {master_duration:.2f}s")

    # 5. Background Music Mixing & Subtitle Burning (Single-Pass Clean Audio)
    music_path = _BASE_DIR / "config" / "bg_music.mp3"
    if not music_path.exists():
        music_path = Path("config/bg_music.mp3")

    final_output = final_dir / f"{video_id}_final.mp4"
    rel_ass = master_ass_path.name

    if music_path.exists():
        music_vol = cfg.get("music_volume_db", -25)
        # Linear volume calculation from dB
        linear_vol = round(10 ** (music_vol / 20), 4)
        logging.info(f"Mixing background music: {music_path.name} at {music_vol} dB (linear {linear_vol})...")

        filter_complex = (
            f"[1:a]volume=1.0[voice];"
            f"[2:a]volume={linear_vol}[bg];"
            f"[voice][bg]amix=inputs=2:duration=first:dropout_transition=0[a_out];"
            f"[0:v]subtitles={rel_ass}[v_out]"
        )

        final_cmd = [
            "ffmpeg", "-y",
            "-i", raw_visuals.name,
            "-i", master_voice.name,
            "-stream_loop", "-1", "-i", str(music_path.resolve()),
            "-filter_complex", filter_complex,
            "-map", "[v_out]",
            "-map", "[a_out]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", f"{master_duration:.2f}",
            str(final_output.resolve())
        ]
    else:
        logging.info("Background music not found; burning subtitles with master voice stream...")
        filter_complex = f"[0:v]subtitles={rel_ass}[v_out]"
        final_cmd = [
            "ffmpeg", "-y",
            "-i", raw_visuals.name,
            "-i", master_voice.name,
            "-filter_complex", filter_complex,
            "-map", "[v_out]",
            "-map", "1:a",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", f"{master_duration:.2f}",
            str(final_output.resolve())
        ]

    logging.info(f"Executing final assembly & subtitle burning to {final_output.name}...")
    res_final = subprocess.run(final_cmd, cwd=str(audio_dir), capture_output=True)
    if res_final.returncode != 0:
        err = res_final.stderr.decode("utf-8", errors="ignore")[-1500:]
        raise RuntimeError(f"Final video assembly failed:\n{err}")

    # 6. Cleanup Temporary Intermediates
    for clip in beat_clips:
        if clip.exists():
            clip.unlink()
    if video_manifest.exists():
        video_manifest.unlink()
    if audio_manifest.exists():
        audio_manifest.unlink()
    if raw_visuals.exists():
        raw_visuals.unlink()

    # 7. Final Validation Probing
    logging.info("Validating compiled video output with ffprobe...")
    val_probe = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration:stream=codec_type,width,height",
        "-of", "json",
        str(final_output)
    ]
    res_vp = subprocess.run(val_probe, capture_output=True, text=True)
    if res_vp.returncode == 0:
        v_info = json.loads(res_vp.stdout)
        act_dur = float(v_info.get("format", {}).get("duration", 0.0))
        streams = v_info.get("streams", [])
        has_v = any(s.get("codec_type") == "video" for s in streams)
        has_a = any(s.get("codec_type") == "audio" for s in streams)
        logging.info(f"Assembly Verified: Duration={act_dur:.2f}s, VideoStream={has_v}, AudioStream={has_a}")
        if not has_v or not has_a:
            raise RuntimeError("Final video is missing audio or video streams!")

    elapsed = time.time() - start_time
    logging.info(f"Video assembly completed successfully in {elapsed:.2f} seconds.")
    return str(final_output)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video_id", required=True, help="Video folder name to compile")
    parser.add_argument("--output_dir", default="output", help="Base output directory")
    parser.add_argument("--thumbnail_scene", type=int, default=0, help="Thumbnail scene index")
    args = parser.parse_args()

    try:
        assemble_video(args.video_id, args.output_dir, thumbnail_scene=args.thumbnail_scene)
    except Exception as e:
        logging.error(f"Assembly failed: {e}")
        sys.exit(1)
