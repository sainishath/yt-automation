# -*- coding: utf-8 -*-
"""
assemble_video.py
-----------------
Pipeline 1 Stage 4 Video Compositor:
- Mobile-Safe Shorts Subtitles (SAFE_SHORTS_ASS_HEADER: MarginV=620, 72pt bold yellow/white with 5px outline)
- 4-Trajectory Dynamic Camera Motion Matrix (Push-In, Pull-Back, Lateral Pan, Diagonal Pan-Tilt)
- FFmpeg sidechaincompress Audio Ducking over dark cinematic tension beds
"""

import os
import sys
import json
import time
import shutil
import subprocess
import argparse
import logging
from pathlib import Path

_ROOT_REPO = Path(__file__).resolve().parent.parent.parent
if str(_ROOT_REPO) not in sys.path:
    sys.path.insert(0, str(_ROOT_REPO))

from pipeline.compositor import (
    MOTION_TRAJECTORIES,
    SAFE_SHORTS_ASS_HEADER,
    SAFE_SHORTS_ASS_STYLE,
    render_dynamic_short_scene,
)

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
    return color_map.get(cleaned, cleaned if cleaned.startswith("&h") else "&H0000FFFF")

def align_and_generate_ass(whisper_words: list, original_text: str, style_cfg: dict, max_words: int = 3, max_chars: int = 16) -> str:
    """
    Aligns Whisper's word timestamps with the exact spelling and punctuation from script.json,
    then generates a v4.00+ ASS subtitle file in the Mobile-Safe Zone (MarginV=620, 72pt bold
    yellow/white active-word highlighting with 5px black outline).
    """
    orig_words = original_text.split()
    aligned = []
    orig_idx = 0
    
    for w_word in whisper_words:
        w_text = w_word["word"].strip().lower()
        if orig_idx < len(orig_words):
            orig_word = orig_words[orig_idx]
            orig_clean = orig_word.strip(".,;:?!'\"()[]{}").lower()
            
            if w_text in orig_clean or orig_clean in w_text or not w_text:
                aligned.append({
                    "word": orig_word,
                    "start": w_word["start"],
                    "end": w_word["end"]
                })
                orig_idx += 1
            else:
                aligned.append({
                    "word": orig_word,
                    "start": w_word["start"],
                    "end": w_word["end"]
                })
                orig_idx += 1
        else:
            aligned.append({
                "word": w_word["word"],
                "start": w_word["start"],
                "end": w_word["end"]
            })
            
    # Catch any remaining words in script
    while orig_idx < len(orig_words) and aligned:
        aligned.append({
            "word": orig_words[orig_idx],
            "start": aligned[-1]["end"],
            "end": aligned[-1]["end"] + 0.2
        })
        orig_idx += 1
        
    # Group words into chunks
    chunks = []
    chunk = []
    chunk_chars = 0
    
    for word_info in aligned:
        w_text = word_info["word"].strip()
        if not chunk:
            chunk.append(word_info)
            chunk_chars = len(w_text)
        elif len(chunk) >= max_words or chunk_chars + len(w_text) + 1 > max_chars:
            chunks.append(chunk)
            chunk = [word_info]
            chunk_chars = len(w_text)
        else:
            chunk.append(word_info)
            chunk_chars += len(w_text) + 1
            
    if chunk:
        chunks.append(chunk)
        
    # Build ASS content using SAFE_SHORTS_ASS_HEADER defaults (MarginV=620, 72pt bold yellow/white, 5px outline)
    font = style_cfg.get("font", "DejaVu Sans")
    if "bold" in font.lower():
        font = font.replace("Bold", "").replace("bold", "").strip() or "DejaVu Sans"
        
    size = int(style_cfg.get("size", 72))
    primary_color = map_color_to_ass(style_cfg.get("color", "yellow"))
    secondary_color = map_color_to_ass(style_cfg.get("secondary_color", "white"))
    out_color = map_color_to_ass(style_cfg.get("outline_color", "black"))
    out_width = int(style_cfg.get("outline_width", 5))
    shadow_depth = int(style_cfg.get("shadow", 2))
    margin_v = int(style_cfg.get("margin_v", 620))
    margin_l = int(style_cfg.get("margin_l", 80))
    margin_r = int(style_cfg.get("margin_r", 80))
    # Enforce mobile-safe floor (never allow captions in the bottom YouTube Shorts UI dead zone < 500px)
    if margin_v < 500:
        margin_v = 620
    
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},{primary_color},{secondary_color},{out_color},&H80000000,-1,0,0,0,100,100,1,0,1,{out_width},{shadow_depth},2,{margin_l},{margin_r},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    events = []
    for chunk in chunks:
        # Active-word yellow/white highlighting across each word in the chunk
        for active_idx, active_word in enumerate(chunk):
            w_start = format_ass_timestamp(active_word["start"])
            w_end = format_ass_timestamp(
                chunk[active_idx + 1]["start"] if active_idx + 1 < len(chunk) else active_word["end"]
            )
            styled_tokens = []
            for tok_idx, tok in enumerate(chunk):
                raw_tok = tok["word"].strip()
                if tok_idx == active_idx:
                    styled_tokens.append(f"{{\\c{primary_color}&}}{raw_tok}{{\\c{secondary_color}&}}")
                else:
                    styled_tokens.append(f"{{\\c{secondary_color}&}}{raw_tok}")
            text_line = " ".join(styled_tokens)
            events.append(f"Dialogue: 0,{w_start},{w_end},Default,,0,0,0,,{text_line}")
        
    return header + "\n".join(events) + "\n"

def transcribe_scene(model, audio_path: Path, narration_text: str, style_cfg: dict) -> str:
    """Uses Whisper to transcribe the audio and returns aligned ASS content."""
    logging.info(f"Transcribing {audio_path.name} with Whisper...")
    result = model.transcribe(
        str(audio_path),
        word_timestamps=True,
        initial_prompt=narration_text,
        language="en"
    )
    
    words = []
    for segment in result.get("segments", []):
        for w in segment.get("words", []):
            words.append({
                "word": w["word"],
                "start": w["start"],
                "end": w["end"]
            })
            
    if not words:
        logging.warning("No word-level timestamps returned, fallback to segment timestamps.")
        for segment in result.get("segments", []):
            words.append({
                "word": segment.get("text", ""),
                "start": segment.get("start", 0.0),
                "end": segment.get("end", 1.0)
            })
            
    return align_and_generate_ass(words, narration_text, style_cfg)

def render_scene_frames_opencv(
    img_path: Path,
    duration: float,
    focal_u: float = 0.50,
    focal_v: float = 0.35,
    zoom_target: float = 1.15,
    t_hit: float = 2.5,
    fps: int = 25,
    out_width: int = 1080,
    out_height: int = 1920,
    trajectory_idx: int = 0
):
    """
    Generator that yields raw BGR bytes for every frame of the scene using OpenCV
    subpixel affine warping with C1 Continuous Smoothstep interpolation across the
    4-Trajectory Camera Motion Matrix:
      0: Dynamic Push-In Zoom (1.00x -> 1.18x)
      1: Dramatic Pull-Back Reveal (1.18x -> 1.00x)
      2: Horizontal Lateral Pan at 1.12x zoom
      3: Diagonal Pan-Tilt at 1.12x zoom
    """
    import cv2
    import numpy as np

    img = cv2.imread(str(img_path))
    if img is None:
        raise FileNotFoundError(f"Failed to load image: {img_path}")

    ih, iw = img.shape[:2]
    total_frames = max(1, int(round(duration * fps)))

    traj_mode = trajectory_idx % 4
    clamped_u = max(0.25, min(0.75, focal_u))
    clamped_v = max(0.25, min(0.65, focal_v))

    if traj_mode == 0:
        # Trajectory 0: Push-In Zoom (1.00 -> 1.18)
        start_zoom, target_zoom = 1.00, max(1.12, min(1.18, zoom_target if zoom_target > 1.08 else 1.16))
        start_u, start_v = 0.50, 0.42
        target_u, target_v = clamped_u, clamped_v
    elif traj_mode == 1:
        # Trajectory 1: Pull-Back Zoom-Out Reveal (1.18 -> 1.00)
        start_zoom, target_zoom = 1.18, 1.00
        start_u, start_v = clamped_u, clamped_v
        target_u, target_v = 0.50, 0.45
    elif traj_mode == 2:
        # Trajectory 2: Horizontal Lateral Pan at 1.12x
        start_zoom, target_zoom = 1.12, 1.12
        start_u, target_u = 0.38, 0.62
        start_v, target_v = clamped_v, clamped_v
    else:
        # Trajectory 3: Diagonal Pan-Tilt at 1.12x
        start_zoom, target_zoom = 1.12, 1.14
        start_u, target_u = 0.62, 0.38
        start_v, target_v = 0.34, 0.54

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


def build_scene_clip(
    idx: int,
    img_path: Path,
    audio_path: Path,
    ass_path: Path,
    duration: float,
    out_clip_path: Path,
    focal_u: float = 0.50,
    focal_v: float = 0.35,
    zoom_target: float = 1.15,
    t_hit: float = 2.5
) -> bool:
    """
    Compiles a single scene video clip with 4-trajectory OpenCV subpixel motion,
    audio muxing, and mobile-safe ASS subtitle burning (MarginV=620).
    """
    audio_dir = audio_path.parent
    rel_audio = audio_path.name
    rel_ass = ass_path.name
    rel_out = out_clip_path.name

    fps = 25
    out_w, out_h = 1080, 1920
    temp_video = f"temp_video_{idx}.mp4"

    logging.info(
        f"Assembling scene {idx} with Dynamic Camera Trajectory #{idx % 4}: "
        f"Focal=({focal_u:.2f}, {focal_v:.2f}), Zoom={zoom_target:.2f}x"
    )

    cmd_ffmpeg = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{out_w}x{out_h}",
        "-pix_fmt", "bgr24",
        "-r", str(fps),
        "-i", "-",
        "-vf", f"subtitles={rel_ass}",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "veryfast",
        "-crf", "20",
        "-t", f"{duration:.2f}",
        temp_video
    ]

    try:
        proc = subprocess.Popen(
            cmd_ffmpeg,
            cwd=str(audio_dir),
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
            out_height=out_h,
            trajectory_idx=idx
        ):
            proc.stdin.write(frame_bytes)

        proc.stdin.close()
        proc.wait()

        if proc.returncode != 0:
            logging.error(f"FFmpeg OpenCV rawvideo stream failed for scene {idx} (code {proc.returncode})")
            return False

    except Exception as e:
        logging.error(f"OpenCV subpixel frame streaming failed for scene {idx}: {e}")
        return False

    # 2. Mux synthesized audio stream
    cmd_merge = [
        "ffmpeg", "-y",
        "-i", temp_video,
        "-i", rel_audio,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", f"{duration:.2f}",
        rel_out
    ]

    res_merge = subprocess.run(cmd_merge, cwd=str(audio_dir), capture_output=True)

    temp_path = audio_dir / temp_video
    if temp_path.exists():
        temp_path.unlink()

    if res_merge.returncode != 0:
        err = res_merge.stderr.decode("utf-8", errors="ignore")[-1000:]
        logging.error(f"FFmpeg muxing error for scene {idx}:\n{err}")
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
        
    model_name = cfg.get("whisper_model", "base.en")
    
    # 1. Step A: Transcription with Whisper
    logging.info(f"Loading Whisper model '{model_name}'...")
    import whisper
    whisper_model = whisper.load_model(model_name)
    
    scenes = script.get("scenes", [])
    audio_dir = video_path / "audio"
    images_dir = video_path / "images"
    final_dir = video_path / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    
    compiled_clips = []

    plan_path = video_path / "scene_plan.json"
    scene_plan_beats = []
    if plan_path.exists():
        try:
            with open(plan_path, "r", encoding="utf-8") as pf:
                sp_data = json.load(pf)
                scene_plan_beats = sp_data.get("visual_beats", [])
        except Exception as pe:
            logging.warning(f"Could not load scene_plan.json: {pe}")

    for idx, scene in enumerate(scenes):
        narration = scene.get("narration", "")
        duration = float(scene.get("actual_duration_seconds", scene.get("estimated_duration_seconds", 5.0)))

        audio_file = audio_dir / f"scene_{idx:03d}.mp3"
        beat_alt = images_dir / f"beat_{idx+1:03d}.png"
        beat_files = sorted(images_dir.glob("beat_*.png"), key=lambda p: int("".join(c for c in p.stem if c.isdigit()) or 0))
        if beat_alt.exists():
            img_file = beat_alt
        elif (images_dir / f"scene_{idx:03d}.png").exists():
            img_file = images_dir / f"scene_{idx:03d}.png"
        elif beat_files:
            clamped_idx = min(idx, len(beat_files) - 1)
            img_file = beat_files[clamped_idx]
        else:
            img_file = images_dir / f"scene_{idx:03d}.png"
        ass_file = audio_dir / f"scene_{idx:03d}.ass"
        out_clip = audio_dir / f"scene_{idx:03d}_compiled.mp4"

        if not audio_file.exists():
            raise FileNotFoundError(f"Missing audio file for scene {idx}: {audio_file}")
        if not img_file.exists():
            raise FileNotFoundError(f"Missing image file for scene {idx}: {img_file}")

        focal_u = 0.50
        focal_v = 0.35
        zoom_tgt = 1.15
        t_hit = duration * 0.55

        if idx < len(scene_plan_beats):
            sp_beat = scene_plan_beats[idx]
            focal_u = float(sp_beat.get("focal_u", 0.50))
            focal_v = float(sp_beat.get("focal_v", 0.35))
            zoom_tgt = float(sp_beat.get("zoom_target", 1.15))
            t_hit = float(sp_beat.get("t_hit", duration * 0.55))

        style_cfg = cfg.get("caption_style", {})
        ass_content = transcribe_scene(whisper_model, audio_file, narration, style_cfg)
        with open(ass_file, "w", encoding="utf-8") as sf:
            sf.write(ass_content)

        success = build_scene_clip(
            idx=idx,
            img_path=img_file,
            audio_path=audio_file,
            ass_path=ass_file,
            duration=duration,
            out_clip_path=out_clip,
            focal_u=focal_u,
            focal_v=focal_v,
            zoom_target=zoom_tgt,
            t_hit=t_hit
        )
        if not success:
            raise RuntimeError(f"Failed to assemble scene {idx} clip.")

        compiled_clips.append(out_clip)

    if 0 < thumbnail_scene < len(compiled_clips):
        logging.info(f"Setting scene {thumbnail_scene} as the video thumbnail cover frame.")
        thumb_clip = compiled_clips.pop(thumbnail_scene)
        compiled_clips.insert(0, thumb_clip)
        
    # 2. Step D: Concatenation (Hard Cuts)
    manifest_path = audio_dir / "concat_manifest.txt"
    with open(manifest_path, "w", encoding="utf-8") as mf:
        for clip in compiled_clips:
            mf.write(f"file '{clip.name}'\n")
            
    raw_video = final_dir / "raw_concat.mp4"
    concat_cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", "concat_manifest.txt",
        "-c", "copy",
        str(raw_video.resolve())
    ]
    
    logging.info("Concatenating scene clips...")
    res = subprocess.run(concat_cmd, cwd=str(audio_dir), capture_output=True)
    if res.returncode != 0:
        err = res.stderr.decode("utf-8", errors="ignore")[-1000:]
        raise RuntimeError(f"Concatenation failed:\n{err}")
        
    if manifest_path.exists():
        manifest_path.unlink()
        
    # 3. Step E: Background Tension Bed Integration with FFmpeg sidechaincompress Audio Ducking
    music_path = _BASE_DIR / "config" / "bg_music.mp3"
    if not music_path.exists():
        music_path = Path("config/bg_music.mp3")
    final_output = final_dir / f"{video_id}_final.mp4"
    
    if music_path.exists():
        logging.info(f"Mixing background audio bed ({music_path.name}) with sidechaincompress ducking...")
        music_vol = cfg.get("music_volume_db", -18)
        linear_vol = round(10 ** (music_vol / 20), 3)
        
        sidechain_filter = (
            f"[0:a]aresample=async=1,aformat=sample_rates=44100:channel_layouts=stereo,volume=1.0,asplit=2[voice_main][voice_sc];"
            f"[1:a]aresample=async=1,aformat=sample_rates=44100:channel_layouts=stereo,lowpass=f=1800,volume={linear_vol}[bg_raw];"
            f"[bg_raw][voice_sc]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=250[bg_ducked];"
            f"[voice_main][bg_ducked]amix=inputs=2:duration=first:dropout_transition=2[a_out]"
        )
        mix_cmd = [
            "ffmpeg", "-y",
            "-i", str(raw_video),
            "-stream_loop", "-1", "-i", str(music_path),
            "-filter_complex", sidechain_filter,
            "-map", "0:v", "-map", "[a_out]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            str(final_output)
        ]
        res = subprocess.run(mix_cmd, capture_output=True)
        if res.returncode != 0:
            logging.warning("sidechaincompress filter fallback to standard amix...")
            fallback_filter = (
                f"[0:a]aresample=async=1,aformat=sample_rates=44100:channel_layouts=stereo,volume=1.0[voice];"
                f"[1:a]aresample=async=1,aformat=sample_rates=44100:channel_layouts=stereo,volume={linear_vol}[bg];"
                f"[voice][bg]amix=inputs=2:duration=first:dropout_transition=2[a_out]"
            )
            mix_cmd[mix_cmd.index("-filter_complex") + 1] = fallback_filter
            res = subprocess.run(mix_cmd, capture_output=True)
            if res.returncode != 0:
                err = res.stderr.decode("utf-8", errors="ignore")[-1000:]
                raise RuntimeError(f"Background music mixing failed:\n{err}")
    else:
        logging.warning("Background music config/bg_music.mp3 not found. Exporting voice-only final video.")
        shutil.copy(raw_video, final_output)
        
    if raw_video.exists():
        raw_video.unlink()
        
    # 4. Step F: Export & Validation
    logging.info("Validating final video output...")
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration:stream=codec_type",
        "-of", "json",
        str(final_output)
    ]
    res = subprocess.run(probe_cmd, capture_output=True, text=True)
    if res.returncode == 0:
        info = json.loads(res.stdout)
        duration_act = float(info.get("format", {}).get("duration", 0.0))
        streams = info.get("streams", [])
        has_video = any(s.get("codec_type") == "video" for s in streams)
        has_audio = any(s.get("codec_type") == "audio" for s in streams)
        
        total_expected_duration = sum(
            float(s.get("actual_duration_seconds", s.get("estimated_duration_seconds", 5.0)))
            for s in scenes
        )
        
        logging.info(f"Validation successful! Final Video Duration: {duration_act:.2f}s (Expected: {total_expected_duration:.2f}s)")
        logging.info(f"Has Video Stream: {has_video}, Has Audio Stream: {has_audio}")
        if not has_video or not has_audio:
            raise RuntimeError("Final video is missing video or audio streams!")
    else:
        logging.warning("ffprobe validation failed to run, assuming file is correct.")
        
    elapsed = time.time() - start_time
    logging.info(f"Stage 4 Video Assembly completed successfully in {elapsed:.2f} seconds.")
    return str(final_output)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video_id", required=True, help="Video folder name to compile")
    parser.add_argument("--output_dir", default="output", help="Base output directory")
    parser.add_argument(
        "--thumbnail_scene",
        type=int,
        default=0,
        help="The scene index whose first frame should serve as the cover/thumbnail for Shorts."
    )
    args = parser.parse_args()
    
    try:
        assemble_video(args.video_id, args.output_dir, thumbnail_scene=args.thumbnail_scene)
    except Exception as e:
        logging.error(f"Assembly failed: {e}")
        sys.exit(1)
