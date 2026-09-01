# -*- coding: utf-8 -*-
"""
compile_series.py
-----------------
Automated 16:9 Long-Form Series Compilation & Omnibus Engine for Channel A.

Features:
1. Converts 9:16 vertical Shorts episodes into 1920x1080 16:9 widescreen layout:
   - Heavily blurred and dimmed background wings (boxblur=25:5, eq=brightness=-0.08:contrast=1.05).
   - High-fidelity centered 9:16 foreground video overlay.
2. Seamlessly stitches sequential multi-part episodes into a single master omnibus.
3. Automatically computes clickable YouTube chapter timestamps (00:00 Part 1, 00:45 Part 2, etc.).
4. Generates comprehensive long-form metadata (title, chapters, description, tags).
5. Directly integrates with upload_video.py for one-command YouTube publishing.
"""

import os
import sys
import json
import time
import shutil
import argparse
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

_DIR = Path(__file__).parent.resolve()
_BASE_DIR = _DIR.parent.resolve()
sys.path.insert(0, str(_DIR))

# Setup logging
LOG_FILE = _BASE_DIR / "compilation.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("SeriesCompiler")


def get_video_duration(video_path: Path) -> float:
    """Probes exact video duration in seconds via ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())


def format_timestamp(seconds: float) -> str:
    """Formats float seconds into standard YouTube timestamp mm:ss or hh:mm:ss."""
    s = int(round(seconds))
    hrs = s // 3600
    mins = (s % 3600) // 60
    secs = s % 60
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def convert_clip_to_16x9(
    input_clip: Path,
    output_clip: Path,
    temp_dir: Path
) -> Path:
    """
    Converts a 9:16 vertical MP4 into a 1920x1080 16:9 widescreen layout with
    blurred dynamic background wings and centered crisp foreground.
    """
    output_clip.parent.mkdir(parents=True, exist_ok=True)
    
    # FFmpeg filtergraph:
    # 1. Scale input to fill 1920x1080 background, crop, blur heavily (boxblur=25:5), dim slightly
    # 2. Scale input to height 1080 for crisp foreground
    # 3. Center foreground over background at (W-w)/2:0
    filter_graph = (
        "[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,boxblur=25:5,eq=brightness=-0.08:contrast=1.05[bg]; "
        "[0:v]scale=-1:1080[fg]; "
        "[bg][fg]overlay=(W-w)/2:0[v_out]"
    )
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_clip.resolve()),
        "-filter_complex", filter_graph,
        "-map", "[v_out]",
        "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        str(output_clip.resolve())
    ]
    
    logger.info(f"Converting {input_clip.name} to 16:9 Widescreen layout...")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg 16:9 conversion failed for {input_clip}: {proc.stderr}")
        
    return output_clip


def compile_series(
    clips: List[Path],
    series_name: str,
    output_dir: Optional[Path] = None,
    custom_title: Optional[str] = None,
    upload: bool = False,
    privacy: str = "public"
) -> Dict[str, Any]:
    """
    Compiles a sequential list of 9:16 episode clips into a master 16:9 omnibus video.
    Auto-generates chapter breakdown metadata and optionally uploads to YouTube.
    """
    if not clips or len(clips) == 0:
        raise ValueError("No video clips provided for series compilation.")

    out_base = output_dir or _BASE_DIR / "output" / "series_compilations"
    series_slug = "".join(c if c.isalnum() else "_" for c in series_name).strip("_")
    timestamp_slug = time.strftime("%Y%m%d_%H%M%S")
    series_workspace = out_base / f"{series_slug}_{timestamp_slug}"
    series_workspace.mkdir(parents=True, exist_ok=True)
    
    temp_dir = series_workspace / "temp_16x9_clips"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Starting 16:9 Series Compilation for '{series_name}' ({len(clips)} episodes)...")
    print(f"\n{'='*55}\n  SERIES OMNIBUS COMPILATION: '{series_name}'\n  Episodes: {len(clips)} clips\n  Workspace: {series_workspace}\n{'='*55}\n")

    # 1. Convert each episode clip to 16:9 widescreen format
    converted_clips = []
    chapter_metadata = []
    current_time_sec = 0.0

    for idx, clip in enumerate(clips):
        part_num = idx + 1
        clip_path = Path(clip)
        if not clip_path.exists():
            raise FileNotFoundError(f"Episode clip not found at: {clip_path}")
            
        dur = get_video_duration(clip_path)
        timestamp_str = format_timestamp(current_time_sec)
        
        # Determine episode title from parent metadata if available
        ep_title = f"Part {part_num}"
        meta_file = clip_path.parent.parent / "metadata.json"
        if meta_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as mf:
                    m = json.load(mf)
                    ep_title = m.get("title", f"Part {part_num}")
            except Exception:
                pass

        chapter_metadata.append({
            "part_number": part_num,
            "title": ep_title,
            "start_time_seconds": round(current_time_sec, 2),
            "timestamp": timestamp_str,
            "duration_seconds": round(dur, 2),
            "original_clip": str(clip_path.resolve())
        })
        
        target_16x9_clip = temp_dir / f"part_{part_num:02d}_16x9.mp4"
        convert_clip_to_16x9(clip_path, target_16x9_clip, temp_dir)
        converted_clips.append(target_16x9_clip)
        
        current_time_sec += dur

    # 2. Concat all 16:9 clips into single master omnibus MP4
    concat_list_file = series_workspace / "concat_list.txt"
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for c in converted_clips:
            safe_p = str(c.resolve()).replace("\\", "/")
            f.write(f"file '{safe_p}'\n")

    master_mp4 = series_workspace / f"{series_slug}_Omnibus_1080p.mp4"
    logger.info(f"Stitching {len(converted_clips)} widescreen clips into master omnibus...")
    
    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list_file.resolve()),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        str(master_mp4.resolve())
    ]
    
    proc_c = subprocess.run(cmd_concat, capture_output=True, text=True)
    if proc_c.returncode != 0:
        raise RuntimeError(f"FFmpeg concatenation failed: {proc_c.stderr}")

    total_duration = get_video_duration(master_mp4)

    # 3. Generate YouTube Long-Form Metadata & Chapters
    chapter_text = "\n".join([f"{c['timestamp']} {c['title']}" for c in chapter_metadata])
    
    title = custom_title or f"{series_name} — Complete Documentary Series (Full Omnibus)"
    description = (
        f"Experience the complete {len(clips)}-part historical documentary saga of '{series_name}' in full 1080p widescreen.\n\n"
        f"CHAPTER TIMESTAMPS:\n"
        f"{chapter_text}\n\n"
        f"Subscribe for more epic historical turning points, counterfactuals, and deep-dive documentaries.\n\n"
        f"[Altered or Synthetic Content: This documentary contains AI-assisted visual and audio reconstructions.]\n\n"
        f"#History #Documentary #{series_slug} #FullSeries #Omnibus"
    )
    
    tags = [
        series_name,
        "History Documentary",
        "Full Documentary",
        "Omnibus",
        "Complete Series",
        "World History",
        "Chronos Shift",
        "Historical Turning Points"
    ]

    metadata_doc = {
        "series_name": series_name,
        "title": title,
        "description": description,
        "tags": tags,
        "total_duration_seconds": round(total_duration, 2),
        "total_episodes": len(clips),
        "chapters": chapter_metadata,
        "master_video_path": str(master_mp4.resolve()),
        "compiled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
    }

    metadata_path = series_workspace / "series_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as mf:
        json.dump(metadata_doc, mf, indent=2, ensure_ascii=False)

    print(f"\n{'='*55}\n  SERIES COMPILATION COMPLETE: {master_mp4.name}\n  Duration:   {format_timestamp(total_duration)} ({total_duration:.1f}s)\n  Chapters:   {len(chapter_metadata)} episodes indexed\n  Metadata:   {metadata_path}\n{'='*55}\n")

    # 4. Optional Automatic Upload to YouTube via upload_video.py
    upload_result = None
    if upload:
        logger.info(f"Initiating YouTube upload for long-form series: '{title}'...")
        from upload_video import upload_video
        upload_result = upload_video(
            final_mp4=master_mp4,
            title=title,
            description=description,
            tags=tags,
            privacy=privacy
        )

    return {
        "status": "SUCCESS",
        "series_name": series_name,
        "master_video": str(master_mp4.resolve()),
        "metadata_file": str(metadata_path.resolve()),
        "total_duration_seconds": total_duration,
        "chapters": chapter_metadata,
        "upload_result": upload_result
    }


def find_clips_for_series(series_query: str, base_dir: Path = None) -> List[Path]:
    """Finds all final MP4 files matching a series query across output directory."""
    search_base = base_dir or _BASE_DIR / "output"
    matched_clips = []
    
    # 1. Search for directories matching series_query
    for p in search_base.glob(f"*{series_query}*"):
        if p.is_dir():
            final_p = p / "final" / f"{p.name}_final.mp4"
            if final_p.exists():
                matched_clips.append(final_p)
            else:
                for cand in (p / "final").glob("*.mp4"):
                    matched_clips.append(cand)
                    break
                    
    # 2. Check run_manifests for series metadata
    if not matched_clips:
        for man in search_base.glob("**/run_manifest.json"):
            try:
                with open(man, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    s_info = data.get("series", {})
                    if series_query.lower() in str(s_info.get("series_name", "")).lower() or series_query.lower() in str(data.get("topic", "")).lower():
                        vid_p = man.parent / "final" / f"{man.parent.name}_final.mp4"
                        if vid_p.exists():
                            matched_clips.append(vid_p)
            except Exception:
                pass

    return sorted(list(set(matched_clips)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Channel A 16:9 Long-Form Series Compilation Engine")
    parser.add_argument("--series_name", required=True, help="Name of the historical series saga")
    parser.add_argument("--clips", nargs="+", default=None, help="List of episode .mp4 file paths")
    parser.add_argument("--query", default=None, help="Search query to automatically discover episode clips in output/")
    parser.add_argument("--output_dir", default=None, help="Custom output directory")
    parser.add_argument("--title", default=None, help="Custom long-form YouTube title")
    parser.add_argument("--upload", action="store_true", help="Upload compiled 16:9 series to YouTube")
    parser.add_argument("--privacy", choices=["public", "unlisted", "private"], default="public", help="Upload privacy status")
    args = parser.parse_args()

    clip_paths = []
    if args.clips:
        clip_paths = [Path(c) for c in args.clips]
    elif args.query or args.series_name:
        search_term = args.query or args.series_name
        clip_paths = find_clips_for_series(search_term)

    if not clip_paths:
        print(f"[ERROR] No matching clips found for series '{args.series_name}'. Provide explicit --clips paths.")
        sys.exit(1)

    res = compile_series(
        clips=clip_paths,
        series_name=args.series_name,
        output_dir=Path(args.output_dir) if args.output_dir else None,
        custom_title=args.title,
        upload=args.upload,
        privacy=args.privacy
    )
    print(f"[SUCCESS] Series compiled successfully to: {res.get('master_video')}")
