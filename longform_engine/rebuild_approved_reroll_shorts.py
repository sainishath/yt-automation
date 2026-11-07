# -*- coding: utf-8 -*-
"""
longform_engine/rebuild_approved_reroll_shorts.py
-------------------------------------------------
Rebuilds rejected Shorts (w3_short_02, w3_short_03, w3_short_04) with:
1. Exact, pristine voiceover synthesis (Edge-TTS en-US-ChristopherNeural).
2. Whisper acoustic alignment directly on the audio track (zero initial_prompt hallucination, zero lag).
3. Precision-synced mobile-safe karaoke ASS subtitles (MarginV=620, yellow highlight on white).
4. Full visual arc progression across the entire short (no truncated scenes or unrendered climaxes).
5. Automatic 540x960 review proxy generation.
"""

import os
import sys
import json
import time
import asyncio
import subprocess
from pathlib import Path

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
        c_start = chunk[0]["start"]
        c_end = chunk[-1]["end"]
        # Ensure each word has active time
        for i, active_item in enumerate(chunk):
            w_start = active_item["start"]
            # Word active end is next word's start, or chunk end
            if i + 1 < len(chunk):
                w_end = max(active_item["end"], chunk[i+1]["start"])
            else:
                w_end = active_item["end"]
            
            if w_end <= w_start:
                w_end = w_start + 0.25

            # Build line text with yellow active word
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


def render_short_video(
    short_id: str,
    script_text: str,
    shot_image_weights: list,  # list of (image_filename, weight)
    meta_info: dict
):
    print(f"\n=======================================================")
    print(f"--> Rebuilding {short_id}...")
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

    # 2. Transcribe with Whisper (word timestamps, NO initial_prompt, condition_on_previous_text=False)
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
    print(f"4. Rendering dynamic 9:16 visual track across all {len(shot_image_weights)} shots...")
    short_temp = TEMP_DIR / f"temp_{short_id}"
    short_temp.mkdir(parents=True, exist_ok=True)

    total_weight = sum(w for _, w in shot_image_weights)
    clip_files = []

    for idx, (img_name, weight) in enumerate(shot_image_weights, 1):
        img_file = IMAGES_DIR / img_name
        if not img_file.exists():
            raise FileNotFoundError(f"Image not found: {img_file}")

        shot_dur = total_dur * (weight / total_weight)
        clip_path = short_temp / f"clip_{idx:02d}_{img_file.stem}.mp4"

        # Alternate zoom in and zoom out
        zoom_expr = "min(zoom+0.0015,1.15)" if idx % 2 == 1 else "max(1.15-0.0015*on,1.0)"

        # High-quality Ken-Burns motion filter reframed to 1080x1920
        vf = (
            f"scale=1920:1080,setsar=1,"
            f"zoompan=z='{zoom_expr}':d={int(shot_dur*30)}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30"
        )

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(img_file),
            "-vf", vf,
            "-t", f"{shot_dur:.3f}",
            "-c:v", "libx264", "-preset", "faster", "-crf", "18", "-pix_fmt", "yuv420p",
            str(clip_path)
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
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
    # ── SHORT 02 ─────────────────────────────────────────────────────────────
    s2_script = (
        "Because they couldn't break Vienna's stone walls from above, the Ottomans began digging fifty feet underground to plant barrels of gunpowder. "
        "To detect the enemy tunnels, defenders placed drums covered in dried peas on cellar floors. "
        "Whenever the peas vibrated, Austrian miners dug frantically downward to intercept them. "
        "Men fought savage, silent battles in suffocating dirt tunnels with daggers, shovels, and sulfur smoke. "
        "On September fourth, a massive mine detonated, blowing a thirty-foot gap in the wall—yet the defenders held the breach with pikes. "
        "Watch the full video on the channel."
    )
    s2_shots = [
        ("act02_shot01.png", 3.5),   # Subterranean dirt tunnel
        ("act02_shot02.png", 3.5),   # Ottoman engineers stacking gunpowder
        ("act02_shot03.png", 6.5),   # Dried peas bouncing on drum
        ("act02_shot04.png", 6.0),   # Austrian miners digging frantically downward
        ("act02_shot05.png", 3.5),   # Hand-to-hand tunnel combat
        ("act02_shot06.png", 3.5),   # Sulfur smoke pumped into tunnel
        ("act02_shot07.png", 3.5),   # Massive mine detonates
        ("act02_shot08.png", 3.0),   # 30-foot smoking breach in wall
        ("act02_shot09.png", 3.0),   # Pikemen holding the breach
        ("act02_shot010.png", 3.4),  # Cathedral spire at night / CTA
    ]
    with open(SHORTS_DIR / "w3_short_02_meta.json", "r", encoding="utf-8") as f:
        s2_meta = json.load(f)
    render_short_video("w3_short_02", s2_script, s2_shots, s2_meta)

    # ── SHORT 03 ─────────────────────────────────────────────────────────────
    s3_script = (
        "Did you know the croissant was invented during the 1683 Siege of Vienna? "
        "While working in his basement before dawn, an Austrian baker heard faint tapping beneath his floor. "
        "He alerted guards just in time, defusing a massive gunpowder mine directly under the town center. "
        "To celebrate, Vienna's bakers created a new pastry shaped like the Ottoman crescent moon—so citizens could literally devour the symbol of their enemy! "
        "And when the Ottoman camp was later captured, abandoned sacks of dark beans were used to create modern European café culture. "
        "Watch the full video on the channel."
    )
    s3_shots = [
        ("act03_shot01.png", 3.5),   # Vienna after two months of siege
        ("act03_shot02.png", 4.5),   # Baker Peter Wendler working in cellar
        ("act03_shot03.png", 4.0),   # Ear to wall hearing metallic tapping
        ("act03_shot04.png", 5.0),   # Defusing mine under the city center
        ("act03_shot05.png", 4.0),   # Bakers shaping crescent Kipferl pastries
        ("act03_shot06.png", 4.0),   # Citizens eating croissants to devour enemy symbol
        ("act03_shot07.png", 4.0),   # Abandoned sacks of coffee beans
        ("act03_shot08.png", 4.5),   # First European café culture
        ("act03_shot09.png", 3.5),   # Cathedral tower distress rocket / CTA
    ]
    with open(SHORTS_DIR / "w3_short_03_meta.json", "r", encoding="utf-8") as f:
        s3_meta = json.load(f)
    render_short_video("w3_short_03", s3_script, s3_shots, s3_meta)

    # ── SHORT 04 ─────────────────────────────────────────────────────────────
    s4_script = (
        "They wore massive wooden wings lined with eagle feathers that made a terrifying roaring whistle when galloping at full charge. "
        "On September 12, 1683, Polish King Jan Sobieski arrived at Vienna with the most feared heavy cavalry on earth: the Winged Hussars. "
        "Carrying hollow nineteen-foot lances designed to out-reach any infantry spear, eighteen thousand horsemen lined up along the crest of the Kahlenberg mountain at sunset. "
        "When the trumpets sounded, they unleashed the largest cavalry charge in human history, tearing down the mountain like an avalanche of steel. "
        "Watch the full video on the channel."
    )
    s4_shots = [
        ("act04_shot03.png", 4.0),   # Close-up of Winged Hussar eagle wings
        ("act04_shot04.png", 4.0),   # Squadron of Winged Hussars
        ("act04_shot01.png", 4.5),   # King Jan III Sobieski on ridge
        ("act04_shot02.png", 4.0),   # Allied European army arriving
        ("act04_shot05.png", 4.5),   # Lowering 19-foot lances
        ("act04_shot07.png", 4.5),   # Sunset along crest of Kahlenberg mountain
        ("act04_shot08.png", 4.0),   # 18,000 horsemen arrayed on ridge
        ("act04_shot09.png", 4.0),   # Freshly rendered avalanche charge downhill!
        ("act04_shot010.png", 4.0),  # Freshly rendered warhorses crashing into lines!
    ]
    with open(SHORTS_DIR / "w3_short_04_meta.json", "r", encoding="utf-8") as f:
        s4_meta = json.load(f)
    render_short_video("w3_short_04", s4_script, s4_shots, s4_meta)

    print("\n[COMPLETE] Successfully re-rendered w3_short_02, w3_short_03, and w3_short_04!")


if __name__ == "__main__":
    main()
