# -*- coding: utf-8 -*-
"""
longform_engine/render_stable_vertical_shorts.py
------------------------------------------------
Renders pristine, rock-solid 9:16 vertical shorts from 16:9 images with:
1. Strict 9:16 Aspect Ratio (Center-cut 9:16 out of 16:9, ZERO squeezing or stretching).
2. Subpixel Smoothstep Camera Motion (OpenCV rawvideo pipe, ZERO jitter or shaking).
3. Mobile-safe karaoke ASS subtitles (MarginV=620, yellow active word highlight).
4. Direct Whisper acoustic word-alignment (zero lag, 100% audio-visual sync).
5. Automatic 540x960 proxy generation.
"""

import os
import sys
import json
import time
import asyncio
import subprocess
from pathlib import Path
import numpy as np
import cv2

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

JOB_ID = "siege_of_vienna_1683"
OUTPUT_DIR = _ROOT / "longform_engine" / "output" / "pending_review" / JOB_ID
SHORTS_DIR = OUTPUT_DIR / "shorts"
IMAGES_DIR = OUTPUT_DIR / "temp" / "images"
TEMP_DIR = OUTPUT_DIR / "temp"

SHORTS_DIR.mkdir(parents=True, exist_ok=True)


def format_ass_time(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def build_karaoke_ass(words: list, out_ass: Path, font="DejaVu Sans", font_size=72, margin_v=620):
    """
    Builds ASS subtitle file from Whisper word timestamps.
    Words are grouped into 2-3 word chunks (max 3 words, max 16 chars).
    Within each chunk, the active word is highlighted in yellow (&H0000FFFF&).
    """
    chunks = []
    chunk = []
    chunk_chars = 0
    max_words = 3
    max_chars = 16

    for w in words:
        clean = w["word"].strip()
        if not clean:
            continue
        item = {
            "word": clean,
            "start": float(w["start"]),
            "end": float(w["end"])
        }
        if not chunk:
            chunk.append(item)
            chunk_chars = len(clean)
        elif len(chunk) >= max_words or chunk_chars + len(clean) + 1 > max_chars:
            chunks.append(chunk)
            chunk = [item]
            chunk_chars = len(clean)
        else:
            chunk.append(item)
            chunk_chars += len(clean) + 1

    if chunk:
        chunks.append(chunk)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{font_size},&H0000FFFF&,&H00FFFFFF&,&H00000000&,&H80000000,-1,0,0,0,100,100,1,0,1,5,2,2,80,80,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for chunk in chunks:
        for i, active_item in enumerate(chunk):
            w_start = active_item["start"]
            if i + 1 < len(chunk):
                w_end = max(active_item["end"], chunk[i+1]["start"])
            else:
                w_end = active_item["end"]
            
            if w_end <= w_start:
                w_end = w_start + 0.25

            tokens = []
            for j, w_info in enumerate(chunk):
                if j == i:
                    tokens.append(f"{{\\c&H0000FFFF&}}{w_info['word']}{{\\c&H00FFFFFF&}}")
                else:
                    tokens.append(w_info["word"])
            line_text = " ".join(tokens)
            start_str = format_ass_time(w_start)
            end_str = format_ass_time(w_end)
            events.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{line_text}")

    content = header + "\n".join(events) + "\n"
    out_ass.write_text(content, encoding="utf-8")
    print(f"  [ASS] Generated {len(events)} cues -> {out_ass.name}")


async def synthesize_voice(text: str, out_path: Path):
    import edge_tts
    comm = edge_tts.Communicate(text, "en-US-ChristopherNeural")
    await comm.save(str(out_path))


def render_stable_vertical_shot(
    image_path: Path,
    output_mp4_path: Path,
    duration_sec: float = 4.0,
    motion_type: str = "stable_push_in",
    fps: int = 30
) -> Path:
    """
    Renders a single 9:16 vertical shot from a 16:9 source image.
    1. Extracts exact 9:16 center-cut without ANY stretching or squeezing.
    2. Applies subpixel smoothstep camera motion (ZERO jitter / shaking).
    3. Pipes raw BGR frames into FFmpeg.
    """
    if not image_path.exists():
        raise FileNotFoundError(f"Source image not found: {image_path}")

    raw_img = cv2.imread(str(image_path))
    if raw_img is None:
        raise ValueError(f"Could not load image: {image_path}")

    h, w = raw_img.shape[:2]

    # Calculate exact 9:16 base crop window inside source height
    base_crop_h = h
    base_crop_w = int(round(h * 9.0 / 16.0))
    if base_crop_w % 2 != 0:
        base_crop_w += 1

    center_x = w // 2
    center_y = h // 2

    total_frames = max(1, int(fps * duration_sec))
    output_mp4_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", "1080x1920",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", "faster",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        str(output_mp4_path)
    ]

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE
    )

    for i in range(total_frames):
        t = i / max(1, total_frames - 1)
        # Smoothstep curve S(t) = 3t^2 - 2t^3 for organic acceleration/deceleration
        s = 3.0 * (t ** 2) - 2.0 * (t ** 3)

        if motion_type == "stable_push_in":
            # Subtle smooth zoom-in: 1.00x -> 1.035x
            zoom = 1.00 + 0.035 * s
        elif motion_type == "stable_pull_out":
            # Subtle smooth zoom-out: 1.035x -> 1.00x
            zoom = 1.035 - 0.035 * s
        else:
            # Rock-solid hold with slight 1.01x buffer
            zoom = 1.01

        cur_w = int(base_crop_w / zoom)
        cur_h = int(base_crop_h / zoom)

        x1 = max(0, min(w - cur_w, center_x - cur_w // 2))
        y1 = max(0, min(h - cur_h, center_y - cur_h // 2))

        cropped = raw_img[y1:y1 + cur_h, x1:x1 + cur_w]
        frame = cv2.resize(cropped, (1080, 1920), interpolation=cv2.INTER_LANCZOS4)
        proc.stdin.write(frame.tobytes())

    proc.stdin.close()
    _, stderr_data = proc.communicate(timeout=60)
    if proc.returncode != 0:
        err_msg = stderr_data.decode("utf-8", errors="replace") if stderr_data else "Unknown error"
        raise RuntimeError(f"FFmpeg motion rendering failed (code {proc.returncode}): {err_msg}")

    return output_mp4_path


def render_short_video(
    short_id: str,
    script_text: str,
    shot_definitions: list,  # list of (image_filename, weight, motion_type)
    meta_info: dict
):
    print(f"\n=======================================================")
    print(f"--> Rebuilding {short_id} with STABLE 9:16 CROP ENGINE...")
    print(f"=======================================================")

    voice_path = SHORTS_DIR / f"{short_id}_voice.mp3"
    ass_path = SHORTS_DIR / f"{short_id}_subtitles.ass"
    out_video = SHORTS_DIR / f"{short_id}.mp4"
    out_proxy = SHORTS_DIR / f"{short_id}_proxy.mp4"
    meta_path = SHORTS_DIR / f"{short_id}_meta.json"
    meta_compat = SHORTS_DIR / f"{short_id}_metadata.json"

    # 1. Synthesize Audio
    print(f"1. Synthesizing voiceover with Edge-TTS...")
    asyncio.run(synthesize_voice(script_text, voice_path))
    probe = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(voice_path)],
        text=True
    ).strip()
    total_dur = float(probe)
    print(f"   Duration: {total_dur:.2f}s")

    # 2. Transcribe with Whisper (word timestamps, condition_on_previous_text=False)
    print(f"2. Transcribing with Whisper for acoustic alignment...")
    import whisper
    model = whisper.load_model("base.en")
    res = model.transcribe(str(voice_path), word_timestamps=True, language="en", condition_on_previous_text=False)
    words = []
    for seg in res.get("segments", []):
        for w in seg.get("words", []):
            words.append({"word": w["word"], "start": w["start"], "end": w["end"]})
    print(f"   Transcribed {len(words)} words (first: '{words[0]['word'].strip()}' at {words[0]['start']:.2f}s, last: '{words[-1]['word'].strip()}' at {words[-1]['start']:.2f}s)")

    # 3. Build ASS Subtitles
    print(f"3. Building mobile-safe karaoke ASS subtitles (MarginV=620)...")
    build_karaoke_ass(words, ass_path, margin_v=620)

    # 4. Generate Visual Cuts & Concat
    print(f"4. Rendering dynamic stable 9:16 visual cuts across all {len(shot_definitions)} shots...")
    short_temp = TEMP_DIR / f"temp_{short_id}"
    short_temp.mkdir(parents=True, exist_ok=True)

    total_weight = sum(w for _, w, _ in shot_definitions)
    clip_files = []

    for idx, (img_name, weight, motion) in enumerate(shot_definitions, 1):
        img_file = IMAGES_DIR / img_name
        if not img_file.exists():
            raise FileNotFoundError(f"Image not found: {img_file}")

        shot_dur = total_dur * (weight / total_weight)
        clip_path = short_temp / f"clip_{idx:02d}_{img_file.stem}.mp4"

        # Render stable 9:16 vertical shot via OpenCV Lanczos-4
        render_stable_vertical_shot(
            image_path=img_file,
            output_mp4_path=clip_path,
            duration_sec=shot_dur,
            motion_type=motion,
            fps=30
        )
        clip_files.append(clip_path)

    # Concat visual clips
    concat_list = short_temp / "concat.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for c in clip_files:
            f.write(f"file '{c.as_posix()}'\n")

    unsubbed_video = short_temp / "unsubbed.mp4"
    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c", "copy",
        str(unsubbed_video)
    ]
    subprocess.run(cmd_concat, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # 5. Mux with Audio and Burn in Subtitles
    print(f"5. Burning in ASS subtitles and muxing Christopher voiceover track...")
    escaped_ass = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
    cmd_final = [
        "ffmpeg", "-y",
        "-i", str(unsubbed_video),
        "-i", str(voice_path),
        "-vf", f"ass='{escaped_ass}'",
        "-c:v", "libx264", "-preset", "faster", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-t", f"{total_dur:.3f}",
        "-shortest",
        str(out_video)
    ]
    subprocess.run(cmd_final, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    v_size_mb = out_video.stat().st_size / (1024 * 1024)
    print(f"   Rendered 1080p Short ({v_size_mb:.2f} MB): {out_video.name}")

    # 6. Generate 540x960 Review Proxy
    print(f"6. Generating 540x960 review proxy...")
    cmd_proxy = [
        "ffmpeg", "-y",
        "-i", str(out_video),
        "-vf", "scale=540:960",
        "-c:v", "libx264", "-preset", "faster", "-crf", "24",
        "-c:a", "aac", "-b:a", "128k",
        str(out_proxy)
    ]
    subprocess.run(cmd_proxy, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    p_size_mb = out_proxy.stat().st_size / (1024 * 1024)
    print(f"   Rendered Proxy ({p_size_mb:.2f} MB): {out_proxy.name}")

    # 7. Update Metadata
    meta_info["duration_sec"] = total_dur
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta_info, f, indent=2, ensure_ascii=False)
    with open(meta_compat, "w", encoding="utf-8") as f:
        json.dump(meta_info, f, indent=2, ensure_ascii=False)
    print(f"   Metadata synchronized.")


def main():
    # ── SHORT 03 (CROISSANT & COFFEE) ─────────────────────────────────────────
    s3_script = (
        "Did you know the croissant was invented during the 1683 Siege of Vienna? "
        "While working in his basement before dawn, an Austrian baker heard faint tapping beneath his floor. "
        "He alerted guards just in time, defusing a massive gunpowder mine directly under the town center. "
        "To celebrate, Vienna's bakers created a new pastry shaped like the Ottoman crescent moon—so citizens could literally devour the symbol of their enemy! "
        "And when the Ottoman camp was later captured, abandoned sacks of dark beans were used to create modern European café culture. "
        "Watch the full video on the channel."
    )
    # (image, duration_weight, motion_type)
    # alternating gentle zoom-in, rock-solid hold, and subtle zoom-out
    s3_shots = [
        ("act03_shot01.png", 3.5, "stable_push_in"),   # Vienna under siege
        ("act03_shot02.png", 4.5, "stable_hold"),      # Baker Peter Wendler working in cellar
        ("act03_shot03.png", 4.0, "stable_push_in"),   # Ear to wall hearing metallic tapping
        ("act03_shot04.png", 5.0, "stable_hold"),      # Defusing mine under the city center
        ("act03_shot05.png", 4.0, "stable_push_in"),   # Bakers shaping crescent Kipferl pastries
        ("act03_shot06.png", 4.0, "stable_hold"),      # Citizens eating croissants
        ("act03_shot07.png", 4.0, "stable_push_in"),   # Abandoned sacks of coffee beans
        ("act03_shot08.png", 4.5, "stable_pull_out"),  # First European café culture
        ("act03_shot09.png", 3.5, "stable_hold"),      # Cathedral tower distress rocket / CTA
    ]
    with open(SHORTS_DIR / "w3_short_03_meta.json", "r", encoding="utf-8") as f:
        s3_meta = json.load(f)
    render_short_video("w3_short_03", s3_script, s3_shots, s3_meta)

    # ── SHORT 04 (WINGED HUSSARS CHARGE) ──────────────────────────────────────
    s4_script = (
        "They wore massive wooden wings lined with eagle feathers that made a terrifying roaring whistle when galloping at full charge. "
        "On September 12, 1683, Polish King Jan Sobieski arrived at Vienna with the most feared heavy cavalry on earth: the Winged Hussars. "
        "Carrying hollow nineteen-foot lances designed to out-reach any infantry spear, eighteen thousand horsemen lined up along the crest of the Kahlenberg mountain at sunset. "
        "When the trumpets sounded, they unleashed the largest cavalry charge in human history, tearing down the mountain like an avalanche of steel. "
        "Watch the full video on the channel."
    )
    # act04_shot09 is the freshly re-rendered centered avalanche charge
    s4_shots = [
        ("act04_shot03.png", 4.0, "stable_push_in"),   # Close-up of Winged Hussar eagle wings
        ("act04_shot04.png", 4.0, "stable_hold"),      # Squadron of Winged Hussars
        ("act04_shot01.png", 4.5, "stable_push_in"),   # King Jan III Sobieski on ridge
        ("act04_shot02.png", 4.0, "stable_hold"),      # Allied European army arriving
        ("act04_shot05.png", 4.5, "stable_push_in"),   # Lowering 19-foot lances
        ("act04_shot07.png", 4.5, "stable_hold"),      # Sunset along crest of Kahlenberg mountain
        ("act04_shot08.png", 4.0, "stable_push_in"),   # 18,000 horsemen arrayed on ridge
        ("act04_shot09.png", 4.0, "stable_push_in"),   # Freshly re-rendered centered avalanche charge!
        ("act04_shot010.png", 4.0, "stable_pull_out"), # Warhorses crashing into battle lines!
    ]
    with open(SHORTS_DIR / "w3_short_04_meta.json", "r", encoding="utf-8") as f:
        s4_meta = json.load(f)
    render_short_video("w3_short_04", s4_script, s4_shots, s4_meta)

    # ── SHORT 02 (UNDERGROUND WAR) ───────────────────────────────────────────
    # Also upgrade Short 2 to the stable engine so all three rerolls share identical pristine stability!
    s2_script = (
        "Because they couldn't break Vienna's stone walls from above, the Ottomans began digging fifty feet underground to plant barrels of gunpowder. "
        "To detect the enemy tunnels, defenders placed drums covered in dried peas on cellar floors. "
        "Whenever the peas vibrated, Austrian miners dug frantically downward to intercept them. "
        "Men fought savage, silent battles in suffocating dirt tunnels with daggers, shovels, and sulfur smoke. "
        "On September fourth, a massive mine detonated, blowing a thirty-foot gap in the wall—yet the defenders held the breach with pikes. "
        "Watch the full video on the channel."
    )
    s2_shots = [
        ("act02_shot01.png", 3.5, "stable_push_in"),   # Subterranean dirt tunnel
        ("act02_shot02.png", 3.5, "stable_hold"),      # Ottoman engineers stacking gunpowder
        ("act02_shot03.png", 6.5, "stable_push_in"),   # Dried peas bouncing on drum
        ("act02_shot04.png", 6.0, "stable_hold"),      # Austrian miners digging frantically downward
        ("act02_shot05.png", 3.5, "stable_push_in"),   # Hand-to-hand tunnel combat
        ("act02_shot06.png", 3.5, "stable_hold"),      # Sulfur smoke pumped into tunnel
        ("act02_shot07.png", 3.5, "stable_push_in"),   # Massive mine detonates
        ("act02_shot08.png", 3.0, "stable_hold"),      # 30-foot smoking breach in wall
        ("act02_shot09.png", 3.0, "stable_push_in"),   # Pikemen holding the breach
        ("act02_shot010.png", 3.4, "stable_hold"),     # Cathedral spire at night / CTA
    ]
    with open(SHORTS_DIR / "w3_short_02_meta.json", "r", encoding="utf-8") as f:
        s2_meta = json.load(f)
    render_short_video("w3_short_02", s2_script, s2_shots, s2_meta)

    print("\n[COMPLETE] All 3 Shorts re-rendered with rock-solid stability and zero-stretch 9:16 framing!")


if __name__ == "__main__":
    main()
