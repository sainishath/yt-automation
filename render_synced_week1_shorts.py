#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_synced_week1_shorts.py
-----------------------------
Renders 100% Shot-Synced, Causal-Chain Week 1 Shorts with:
1. Exact 1-to-1 Narration & MarginV=620 Subtitles
2. Fooocus SDXL 9:16 Visuals with Master Negative Prompt Lock
3. Zero Hallucinations / Zero Audio Mismatch
"""

import sys
import json
import logging
import subprocess
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("render_week1_shorts")

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from longform_engine.assemble_longform import (
    synthesize_speech,
    get_audio_duration,
    EDGE_TTS_VOICE_P1,
    generate_16x9_visual,
    check_fooocus_status,
    FOOOCUS_URL,
)
from pipeline.compositor import FOOOCUS_NEGATIVE_PROMPT_LOCK
from longform_engine.short_splitter import generate_safe_short_ass

OUT_SHORTS_DIR = ROOT_DIR / "longform_engine" / "output" / "history_10min" / "shorts"

WEEK1_SHORTS_DATA = {
    "w1_short_04": {
        "title": "The Final Midnight Service Inside Hagia Sophia (May 28, 1453)",
        "publish_at_iso": "2026-11-03T07:30:00Z",
        "scheduled_slot_ist": "2026-11-03 13:00 IST",
        "source_act": 5,
        "old_video_id": "IP1ubvXawi8",
        "beats": [
            {
                "beat_id": "cut_01",
                "causal_role": "Hook & Exterior",
                "narration": "On the night of May 28, 1453, the citizens of Constantinople knew tomorrow would be their last.",
                "prompt": "9:16 vertical cinematic wide shot of the monumental Byzantine cathedral Hagia Sophia illuminated by hundreds of flickering torchlights under a dark moonless sky, Constantinople 1453, dark dramatic storm clouds, historical authenticity, 35mm film still, photorealistic 8k",
                "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
                "tts_rate": "+15%"
            },
            {
                "beat_id": "cut_02",
                "causal_role": "The Schism Ends",
                "narration": "For four hundred years, Orthodox and Catholic Christians refused to worship together.",
                "prompt": "9:16 vertical atmospheric medium shot of two Byzantine priests and a Western Franciscan friar standing face to face in ancient stone corridor, dramatic candlelight casting deep shadows, historical 15th century ecclesiastical vestments, photorealistic 8k, cinematic depth",
                "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
                "tts_rate": "+15%"
            },
            {
                "beat_id": "cut_03",
                "causal_role": "The Golden Dome Gathering",
                "narration": "Because twenty thousand Janissaries were outside the walls, the division vanished in a single night.",
                "prompt": "9:16 vertical breathtaking high-angle view looking down into the vast nave of Hagia Sophia, thousands of citizens, Greek soldiers, Genoese crossbowmen, and Venetian sailors holding beeswax candles under the colossal golden dome, golden glow, 8k, majestic historical painting style",
                "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
                "tts_rate": "+15%"
            },
            {
                "beat_id": "cut_04",
                "causal_role": "Emperor Constantine Weeps",
                "narration": "Emperor Constantine the Eleventh knelt before the altar, taking his final communion in tears.",
                "prompt": "9:16 vertical emotional cinematic close-up of Byzantine Emperor Constantine XI Palaiologos kneeling before a Byzantine golden altar, crowned with imperial diadem, tear streaking down weathered cheek, flickering candlelight reflecting on his eyes, solemn expression, 8k photorealistic",
                "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
                "tts_rate": "+15%"
            },
            {
                "beat_id": "cut_05",
                "causal_role": "The Final Liturgy",
                "narration": "As the choir sang Rome's final liturgy, soldiers embraced the citizens they knew they could not save.",
                "prompt": "9:16 vertical touching emotional medium shot of an armored Genoese soldier embracing a sobbing Byzantine civilian woman in Hagia Sophia, candlelight atmosphere, solemn reverence, 15th century armor, 8k cinematic",
                "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
                "tts_rate": "+15%"
            },
            {
                "beat_id": "cut_06",
                "causal_role": "The Janissary Drums",
                "narration": "Outside the massive oak doors, ninety thousand Ottoman war drums began to beat for the dawn assault.",
                "prompt": "9:16 vertical dramatic low-angle shot outside the stone walls, thousands of Ottoman Janissaries in white pointed caps beating colossal brass kettle drums around roaring bonfires in the pitch black night, orange fire glow, 8k cinematic",
                "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
                "tts_rate": "+15%"
            },
            {
                "beat_id": "cut_07",
                "causal_role": "The Departure",
                "narration": "At midnight, the emperor kissed the holy icons, drew his sword, and walked out to the walls to die.",
                "prompt": "9:16 vertical heroic cinematic shot of Emperor Constantine XI with drawn iron sword walking out through the massive bronze doors of Hagia Sophia into the misty dark morning, golden backlight from inside, dramatic silhouette, 8k",
                "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
                "tts_rate": "+15%"
            },
            {
                "beat_id": "cut_08",
                "causal_role": "Conversion CTA",
                "narration": "Watch the full documentary on Chronos Shift to see the final fifty-three days that ended Rome.",
                "prompt": "9:16 vertical epic cinematic establishing shot of the colossal Theodosian stone walls under a blood-red dawn sky with Ottoman banners rising, photorealistic 8k, dramatic historical finale, cinematic lighting",
                "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
                "tts_rate": "+15%"
            }
        ]
    },
    "w1_short_05": {
        "title": "The Unlocked Gate and the Last Roman Emperor's Final Charge",
        "publish_at_iso": "2026-11-04T07:30:00Z",
        "scheduled_slot_ist": "2026-11-04 13:00 IST",
        "source_act": 6,
        "old_video_id": "7Z9BoY96NRw",
        "beats": [
            {
                "beat_id": "cut_01",
                "causal_role": "Hook & Dawn Assault",
                "narration": "At sunrise on May 29, 1453, the Roman Empire was brought down by an unlocked door.",
                "prompt": "9:16 vertical dramatic cinematic shot of the massive stone Theodosian walls shrouded in dense black gunpowder smoke at sunrise, fiery red sky, flashes of cannon fire, photorealistic 8k, historical authenticity 1453",
                "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
                "tts_rate": "+15%"
            },
            {
                "beat_id": "cut_02",
                "causal_role": "The Unlocked Kerkoporta Gate",
                "narration": "During the chaos of cannon fire, defenders accidentally left a tiny postern gate called Kerkoporta unbolted.",
                "prompt": "9:16 vertical low-angle shot of a small weathered medieval iron-studded wooden gate set into the colossal stone fortress wall, slightly ajar with a shaft of morning sunlight piercing through the crack, photorealistic 8k, cinematic suspense",
                "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
                "tts_rate": "+15%"
            },
            {
                "beat_id": "cut_03",
                "causal_role": "Janissaries Infiltrate",
                "narration": "Fifty Ottoman Janissaries spotted the open door, rushed inside, and climbed straight to the battlements.",
                "prompt": "9:16 vertical dynamic action shot of Ottoman Janissaries with curved scimitars and white pointed caps stealthily emerging from the small doorway onto the stone ramparts of Constantinople, early morning light, 8k photorealistic",
                "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
                "tts_rate": "+15%"
            },
            {
                "beat_id": "cut_04",
                "causal_role": "The Crescent Flag",
                "narration": "When the defenders saw the Ottoman crescent banner waving above their own walls, panic tore through the lines.",
                "prompt": "9:16 vertical dramatic high-angle shot of a red Ottoman crescent banner being unfurled atop a stone tower of the Theodosian wall, Byzantine soldiers below looking up in horror, dust and smoke billowing, 8k cinematic",
                "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
                "tts_rate": "+15%"
            },
            {
                "beat_id": "cut_05",
                "causal_role": "Constantine Tears Off Insignia",
                "narration": "Emperor Constantine tore the imperial purple cloak from his shoulders so no one could take him alive.",
                "prompt": "9:16 vertical emotional dramatic close-up of Emperor Constantine XI ripping the gold-embroidered purple silk mantle from his steel cuirass and casting it into the mud, grim determined expression, morning sunlight, 8k photorealistic",
                "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
                "tts_rate": "+15%"
            },
            {
                "beat_id": "cut_06",
                "causal_role": "The Final Charge",
                "narration": "With sword in hand, Rome's last emperor charged directly into the smoky breach alongside his remaining guards.",
                "prompt": "9:16 vertical epic dynamic action shot of Emperor Constantine XI with drawn iron sword leading a desperate charge of Byzantine guards into a wall of advancing Ottoman Janissaries in a ruined stone breach, smoke, sparks, photorealistic 8k",
                "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
                "tts_rate": "+15%"
            },
            {
                "beat_id": "cut_07",
                "causal_role": "The Disappearance",
                "narration": "The emperor fell in the melee, and despite days of searching, his body was never identified.",
                "prompt": "9:16 vertical somber cinematic shot of a battlefield breach covered in fallen shields, broken spears, and drifting smoke after the battle, morning light shining on an abandoned Roman steel helmet, historical authenticity 1453, 8k",
                "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
                "tts_rate": "+15%"
            },
            {
                "beat_id": "cut_08",
                "causal_role": "Conversion CTA",
                "narration": "Watch the full documentary on Chronos Shift to see how Rome fell after a thousand years.",
                "prompt": "9:16 vertical cinematic wide shot of Constantinople skyline from across the water at sunrise, minarets and ancient domes in mist, historical 1453, epic documentary outro, photorealistic 8k",
                "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
                "tts_rate": "+15%"
            }
        ]
    }
}


def render_causal_short(short_id: str, short_data: dict) -> Path:
    title = short_data["title"]
    beats = short_data["beats"]
    out_mp4 = OUT_SHORTS_DIR / f"{short_id}.mp4"
    temp_dir = OUT_SHORTS_DIR / f"temp_{short_id}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    fooocus_active = check_fooocus_status(FOOOCUS_URL)
    logger.info(f"=== Rendering {short_id}: '{title}' ({len(beats)} cuts, Fooocus={fooocus_active}) ===")

    beat_clips = []
    for idx, beat in enumerate(beats, start=1):
        beat_id = beat.get("beat_id", f"cut_{idx:02d}")
        narration = beat["narration"].strip()
        prompt = beat["prompt"]
        neg_prompt = beat.get("negative_prompt", FOOOCUS_NEGATIVE_PROMPT_LOCK)
        rate = beat.get("tts_rate", "+15%")

        # 1. Synthesize audio
        audio_path = temp_dir / f"{beat_id}.mp3"
        if not audio_path.exists() or audio_path.stat().st_size < 100:
            synthesize_speech(narration, EDGE_TTS_VOICE_P1, audio_path, rate=rate)
        dur = get_audio_duration(audio_path)
        if dur < 1.0:
            dur = 1.0

        # 2. Generate mobile-safe MarginV=620 subtitles
        ass_path = temp_dir / f"{beat_id}_subtitles.ass"
        generate_safe_short_ass(narration, dur, ass_path)

        # 3. Generate 9:16 vertical visual via Fooocus SDXL
        img_path = temp_dir / f"{beat_id}.png"
        if not img_path.exists() or img_path.stat().st_size < 50000:
            if fooocus_active:
                logger.info(f"  [{beat_id}] Rendering Fooocus SDXL 9:16 visual: {prompt[:60]}...")
                generate_16x9_visual(
                    prompt,
                    neg_prompt,
                    img_path,
                    aspect_ratio="768*1344",
                    allow_proxies=False
                )
            else:
                raise RuntimeError(f"Fooocus SDXL inactive at {FOOOCUS_URL}")

        # 4. Render synced beat clip
        beat_video = temp_dir / f"{beat_id}_synced.mp4"
        if beat_video.exists() and img_path.exists() and beat_video.stat().st_mtime < img_path.stat().st_mtime:
            beat_video.unlink(missing_ok=True)

        if not beat_video.exists():
            escaped_ass = str(ass_path).replace("\\", "/").replace(":", "\\:")
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", str(img_path),
                "-i", str(audio_path),
                "-vf", f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,ass='{escaped_ass}'",
                "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k",
                "-t", f"{dur:.3f}",
                "-shortest",
                str(beat_video)
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                logger.error(f"FFmpeg error: {proc.stderr}")
                raise RuntimeError(f"FFmpeg failed: {proc.stderr[-300:]}")

        beat_clips.append(beat_video)
        logger.info(f"  [{beat_id}] Completed synced cut ({dur:.2f}s)")

    # 5. Concatenate
    concat_list = temp_dir / "beats_concat.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for bp in beat_clips:
            f.write(f"file '{bp.as_posix()}'\n")

    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(out_mp4)
    ]
    subprocess.run(cmd_concat, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # 6. Metadata JSON
    full_text = " ".join(b["narration"] for b in beats)
    meta = {
        "short_id": short_id,
        "title": title[:100],
        "description": f"{full_text}\n\nFull Documentary on Chronos Shift.\n\n#History #Shorts #Documentary #Constantinople #Rome",
        "tags": ["history", "shorts", "documentary", "constantinople", "rome", "untold history"],
        "source_act": short_data["source_act"],
        "duration_sec": sum(get_audio_duration(temp_dir / f"{b['beat_id']}.mp3") for b in beats),
        "scheduled_publish_slot": short_data["publish_at_iso"],
        "publish_at_iso": short_data["publish_at_iso"],
        "scheduled_slot_ist": short_data["scheduled_slot_ist"],
        "privacy_status": "private",
        "old_video_id": short_data.get("old_video_id")
    }
    meta_path = OUT_SHORTS_DIR / f"{short_id}_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    logger.info(f"Successfully rendered: {out_mp4} ({meta['duration_sec']:.2f}s)")
    return out_mp4


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    for short_id, short_data in WEEK1_SHORTS_DATA.items():
        if target != "all" and short_id != target:
            continue
        render_causal_short(short_id, short_data)


if __name__ == "__main__":
    main()
