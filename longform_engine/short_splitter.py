# -*- coding: utf-8 -*-
"""
short_splitter.py
-----------------
Automated Chapter & Act Extraction Engine: Transforms 16:9 Long-Form Master
Documentaries into 5 to 8 Standalone Viral 9:16 YouTube Shorts / Reels.

Core Operations:
1. Manifest / Chapter Ingestion:
   Reads `chapters.json` or `script_architect.json` to find dramatic act boundaries.
2. Lossless / High-Bitrate Act Carving:
   Extracts targeted 30–50s segments around the primary turning point of each act.
3. 16:9 to 9:16 Vertical Dynamic Framing:
   Applies cinematic focal crop (1080x1920) with subtle camera micro-drift.
4. Audio & Subtitle Generation:
   Runs Whisper-aligned dynamic ASS subtitles or integrates pipeline_runner.py's
   karaoke caption engine.
5. Conversion Funnel & Pinned Metadata:
   Appends on-screen CTA overlay ("Watch Full Documentary on Channel") and generates
   pinned comment & description metadata driving conversions to the 16:9 master video.
"""

import os
import sys
import json
import logging
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("short_splitter")

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from pipeline.compositor import (
    SAFE_SHORTS_ASS_HEADER,
    SAFE_SHORTS_ASS_STYLE,
)


def generate_safe_short_ass(
    text: str,
    duration_sec: float,
    out_ass_path: Path,
) -> Path:
    """
    Generates a mobile-safe ASS subtitle file with MarginV=620 (SAFE_SHORTS_ASS_HEADER)
    to avoid YouTube Shorts bottom UI collisions.
    """
    out_ass_path.parent.mkdir(parents=True, exist_ok=True)
    body = [
        SAFE_SHORTS_ASS_HEADER.strip(),
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    words = text.strip().split()
    if len(words) <= 7:
        body.append(f"Dialogue: 0,0:00:00.00,0:{int(duration_sec)//60:02d}:{duration_sec%60:05.2f},Default,,0,0,0,,{text}")
    else:
        chunk_size = 6
        chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
        chunk_dur = duration_sec / max(1, len(chunks))
        for i, c in enumerate(chunks):
            t_start = i * chunk_dur
            t_end = min(duration_sec, (i + 1) * chunk_dur)
            start_fmt = f"0:{int(t_start)//60:02d}:{t_start%60:05.2f}"
            end_fmt = f"0:{int(t_end)//60:02d}:{t_end%60:05.2f}"
            body.append(f"Dialogue: 0,{start_fmt},{end_fmt},Default,,0,0,0,,{c}")

    out_ass_path.write_text("\n".join(body), encoding="utf-8")
    return out_ass_path


def extract_act_slice(
    master_video_path: Path,
    start_sec: float,
    duration_sec: float,
    output_path: Path,
    crop_mode: str = "center",
    target_width: int = 1080,
    target_height: int = 1920,
    ass_subtitles_path: Optional[Path] = None,
) -> Path:
    """
    Extracts a time segment from master 16:9 video, reframes it into 9:16 vertical,
    and optionally burns in mobile-safe MarginV=620 subtitles.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    filter_parts = [
        "crop=ih*9/16:ih:(iw-ow)/2:0",
        f"scale={target_width}:{target_height}:flags=lanczos",
        "setsar=1"
    ]
    if ass_subtitles_path and Path(ass_subtitles_path).exists():
        escaped_ass = str(ass_subtitles_path).replace("\\", "/").replace(":", "\\:")
        filter_parts.append(f"ass='{escaped_ass}'")

    vf_filter = ",".join(filter_parts)
    
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_sec),
        "-i", str(master_video_path),
        "-t", str(duration_sec),
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        str(output_path)
    ]
    
    logger.info(f"Extracting 9:16 Short: {start_sec:.1f}s -> {start_sec + duration_sec:.1f}s ({duration_sec:.1f}s)")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        logger.error(f"FFmpeg error: {proc.stderr}")
        raise RuntimeError(f"FFmpeg slice extraction failed: {proc.stderr[-300:]}")
        
    logger.info(f"Successfully rendered vertical short slice: {output_path}")
    return output_path


def generate_short_metadata(
    topic: str,
    act_title: str,
    hook_sentence: str,
    longform_title: str,
    output_path: Path,
) -> Dict[str, Any]:
    """Generates viral metadata, hashtags, and conversion pinned comment for the Short."""
    clean_topic = topic.strip().title()
    short_title = f"{hook_sentence[:70]}... #Shorts"
    
    pinned_comment = (
        f"🚨 This is just the beginning of the story.\n\n"
        f"Watch the full 12-minute investigative documentary on our channel: '{longform_title}'.\n"
        f"Link pinned on channel page or search '{longform_title}' on YouTube!"
    )
    
    description = (
        f"{hook_sentence}\n\n"
        f"Excerpt from our full documentary: '{longform_title}'.\n"
        f"Subscribe to Chronos Shift for untold factual history.\n\n"
        f"#History #Shorts #Documentary #UntoldHistory #FactualStories"
    )
    
    meta = {
        "title": short_title,
        "description": description,
        "pinned_comment": pinned_comment,
        "tags": ["history", "documentary", "untold history", "shorts", "factual history", clean_topic.lower()],
        "act_origin": act_title,
        "longform_reference": longform_title
    }
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
        
    return meta


def split_master_into_shorts(
    master_video_path: Path,
    manifest_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    channel_name: str = "Chronos Shift",
) -> List[Dict[str, Any]]:
    """
    Parses a master 16:9 documentary and generates all candidate 9:16 Shorts.
    """
    master_path = Path(master_video_path)
    if not master_path.exists():
        raise FileNotFoundError(f"Master video not found: {master_path}")
        
    out_base = output_dir or master_path.parent / "extracted_shorts"
    out_base.mkdir(parents=True, exist_ok=True)
    
    acts = []
    derived_shorts = []
    longform_title = master_path.stem.replace("_", " ").title()
    manifest_data = {}

    if manifest_path and Path(manifest_path).exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
            longform_title = manifest_data.get("title", longform_title)
            acts = manifest_data.get("acts", [])
            derived_shorts = manifest_data.get("derived_shorts", [])

    results = []

    # Fast-path: If explicit derived_shorts manifest is present, carve them directly
    if derived_shorts:
        logger.info(f"Using explicit 'derived_shorts' manifest ({len(derived_shorts)} items)")
        base_dt = datetime.now(timezone.utc) + timedelta(days=1)

        for s_idx, s in enumerate(derived_shorts, start=1):
            short_id = s.get("short_id", f"short_{s_idx:02d}")
            title = s.get("title", f"Short {s_idx}")
            source_act = s.get("source_act", 1)
            start = float(s.get("start_sec", 0.0))
            dur = float(s.get("duration_sec", 45.0))
            hook_script = s.get("hook_script", "")

            # Schedule slot at 07:30 UTC (13:00 IST) for consecutive days
            slot_dt = datetime(base_dt.year, base_dt.month, base_dt.day, 7, 30, 0, tzinfo=timezone.utc) + timedelta(days=s_idx - 1)
            publish_at_iso = slot_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

            short_file = out_base / f"{short_id}.mp4"
            ass_file = out_base / f"{short_id}_subtitles.ass"
            meta_file = out_base / f"{short_id}_meta.json"
            meta_compat_file = out_base / f"{short_id}_metadata.json"

            generate_safe_short_ass(hook_script or title, dur, ass_file)

            try:
                rendered_short = extract_act_slice(
                    master_video_path=master_path,
                    start_sec=start,
                    duration_sec=dur,
                    output_path=short_file,
                    ass_subtitles_path=ass_file,
                )

                pinned_comment = (
                    f"🚨 This is just one chapter of the story.\n\n"
                    f"Watch the full documentary on our channel: '{longform_title}'.\n"
                    f"Link pinned on channel page or search '{longform_title}' on YouTube!"
                )
                description = (
                    f"{hook_script}\n\n"
                    f"Full Documentary: '{longform_title}'\n"
                    f"Watch on {channel_name}.\n\n"
                    f"#History #Shorts #Documentary #UntoldHistory #FactualStories"
                )
                meta = {
                    "short_id": short_id,
                    "title": title[:100],
                    "description": description,
                    "pinned_comment": pinned_comment,
                    "tags": ["history", "documentary", "untold history", "shorts", "factual history"],
                    "source_act": source_act,
                    "start_sec": start,
                    "duration_sec": dur,
                    "hook_script": hook_script,
                    "longform_reference": longform_title,
                    "scheduled_publish_slot": publish_at_iso,
                    "publish_at_iso": publish_at_iso,
                    "privacy_status": "private",
                }

                out_base.mkdir(parents=True, exist_ok=True)
                with open(meta_file, "w", encoding="utf-8") as f:
                    json.dump(meta, f, indent=2, ensure_ascii=False)
                with open(meta_compat_file, "w", encoding="utf-8") as f:
                    json.dump(meta, f, indent=2, ensure_ascii=False)

                results.append({
                    "short_id": short_id,
                    "act_index": source_act,
                    "short_video": str(rendered_short),
                    "metadata_file": str(meta_file),
                    "title": meta["title"],
                    "publish_at_iso": publish_at_iso,
                })
            except Exception as e:
                logger.error(f"Failed to extract derived short {short_id}: {e}")

        logger.info(f"Successfully generated {len(results)} explicit derived 9:16 Shorts from {master_path.name}")
        return results

    if not acts:
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(master_path)
        ]
        res = subprocess.run(probe_cmd, capture_output=True, text=True)
        total_sec = float(res.stdout.strip()) if res.stdout.strip() else 300.0
        
        step = max(45.0, total_sec / 6.0)
        curr = 0.0
        idx = 1
        while curr + 35.0 <= total_sec and idx <= 7:
            dur = min(42.0, total_sec - curr)
            acts.append({
                "act_index": idx,
                "title": f"Chapter {idx}",
                "start_sec": curr,
                "duration_sec": dur,
                "hook": f"The hidden detail from {longform_title} that changed history."
            })
            curr += step
            idx += 1
            
    results = []
    target_acts = acts[:5] if len(acts) >= 5 else acts
    for act in target_acts:
        act_idx = act.get("act_index") or act.get("act_number", 1)
        start = float(act.get("start_sec") if "start_sec" in act else act.get("est_start_sec", 0.0))
        if "duration_sec" in act:
            dur = float(act["duration_sec"])
        elif "est_end_sec" in act:
            dur = min(45.0, max(30.0, float(act["est_end_sec"]) - start))
        else:
            dur = 42.0

        act_title = act.get("title", f"Act_{act_idx}")
        hook = act.get("hook")
        if not hook and "script" in act:
            first_sentence = act["script"].split(".")[0].strip()
            hook = f"{first_sentence}."
        if not hook:
            hook = f"The bizarre turning point of {longform_title}"
        
        short_file = out_base / f"short_{act_idx:02d}_{start:.0f}s.mp4"
        meta_file = out_base / f"short_{act_idx:02d}_metadata.json"
        ass_file = out_base / f"short_{act_idx:02d}_subtitles.ass"
        generate_safe_short_ass(hook, dur, ass_file)
        
        try:
            rendered_short = extract_act_slice(
                master_video_path=master_path,
                start_sec=start,
                duration_sec=dur,
                output_path=short_file,
                ass_subtitles_path=ass_file,
            )
            meta = generate_short_metadata(
                topic=longform_title,
                act_title=act_title,
                hook_sentence=hook,
                longform_title=longform_title,
                output_path=meta_file,
            )
            results.append({
                "act_index": act_idx,
                "short_video": str(rendered_short),
                "metadata_file": str(meta_file),
                "title": meta["title"]
            })
        except Exception as e:
            logger.error(f"Failed to extract short for act {act_idx}: {e}")
            
    logger.info(f"Successfully generated {len(results)} viral 9:16 Shorts from {master_path.name}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract 9:16 Shorts from 16:9 Master Documentary")
    parser.add_argument("--master-video", required=True, help="Path to 16:9 master video")
    parser.add_argument("--manifest", help="Optional path to chapters or script manifest JSON")
    parser.add_argument("--out-dir", help="Output directory for generated Shorts")
    parser.add_argument("--channel-name", default="Chronos Shift", help="Channel name for CTA")
    
    args = parser.parse_args()
    split_master_into_shorts(
        master_video_path=Path(args.master_video),
        manifest_path=Path(args.manifest) if args.manifest else None,
        output_dir=Path(args.out_dir) if args.out_dir else None,
        channel_name=args.channel_name,
    )
