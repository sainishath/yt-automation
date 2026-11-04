# -*- coding: utf-8 -*-
"""
longform_engine/review_gate.py
--------------------------------
Human-in-the-Loop (HITL) Review Staging Gate for Longform Documentaries & Derived Shorts.

Ensures that NO video (Long-Form or Short) is ever uploaded publicly or scheduled to YouTube
without explicit human review and approval.

Capabilities:
1. Lists all staged video candidate jobs in `longform_engine/output/pending_review/`.
2. Inspects and displays job packaging, runtime, word count, scheduled release slot, and
   the formatted 4-point review checklist:
     [ ] Visuals: No modern artifacts or deformed anatomy?
     [ ] Voice: Clear pacing and pronunciation?
     [ ] Subtitles: Centered in safe-zone (MarginV=620) with no typos?
     [ ] Packaging: Hook and thumbnail verified?
3. Interactive Actions:
   - [1] Approve & Schedule: Moves files to `longform_engine/output/approved/{video_id}/`
         and triggers `upload_video.py` with `--privacy private` or `--privacy scheduled`.
   - [2] Re-roll Single Shot: Prompts for `shot_id` (e.g. `act03_shot02`), re-runs image
         generation for that specific prompt, re-muxes the video clip, and updates
         `master_video.mp4` without re-rendering the other 79 shots.
   - [3] Reject & Scrap: Moves files to `longform_engine/output/scrapped/{video_id}/`
         and locks the run manifest so all future YouTube upload attempts are rejected.
"""

from __future__ import annotations

import os
import re
import sys
import json
import shutil
import logging
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta

# Ensure repo root is on sys.path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("review_gate")

SAFE_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")


def _validate_safe_id(val: str, field_name: str = "job_id") -> str:
    """Validates job_id or shot_id against path traversal or shell/filename injection."""
    clean = str(val or "").strip()
    if not clean or not SAFE_ID_REGEX.match(clean):
        raise ValueError(f"Invalid {field_name} '{val}': must match ^[a-zA-Z0-9_\\-]+$")
    return clean

OUTPUT_BASE = _ROOT / "longform_engine" / "output"
DEFAULT_PENDING_DIR = OUTPUT_BASE / "pending_review"
DEFAULT_APPROVED_DIR = OUTPUT_BASE / "approved"
DEFAULT_SCRAPPED_DIR = OUTPUT_BASE / "scrapped"

UPLOAD_SCRIPT_PATH = _ROOT / "alternate-history-shorts" / "scripts" / "upload_video.py"

CHECKLIST_ITEMS = [
    "Visuals: No modern artifacts or deformed anatomy?",
    "Voice: Clear pacing and pronunciation?",
    "Subtitles: Centered in safe-zone (MarginV=620) with no typos?",
    "Packaging: Hook and thumbnail verified?",
]


def get_staging_paths(base_dir: Optional[Path] = None) -> Tuple[Path, Path, Path]:
    """Returns (pending_dir, approved_dir, scrapped_dir) from base_dir or default."""
    if base_dir:
        b = Path(base_dir)
        # If base_dir itself is named 'pending_review', its parent is base
        if b.name == "pending_review":
            return b, b.parent / "approved", b.parent / "scrapped"
        return b / "pending_review", b / "approved", b / "scrapped"
    return DEFAULT_PENDING_DIR, DEFAULT_APPROVED_DIR, DEFAULT_SCRAPPED_DIR


def list_pending_jobs(base_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Scans pending_review directory and returns list of staged candidate jobs."""
    pending_dir, _, _ = get_staging_paths(base_dir)
    jobs: List[Dict[str, Any]] = []

    if not pending_dir.exists():
        return jobs

    for entry in sorted(pending_dir.iterdir()):
        if not entry.is_dir():
            continue

        job_id = entry.name
        meta_file = entry / "metadata.json"
        meta: Dict[str, Any] = {}
        if meta_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read metadata for {job_id}: {e}")

        master_video = entry / "master_video.mp4"
        thumbnail = entry / "thumbnail.png"
        shorts_dir = entry / "shorts"
        shorts_count = len(list(shorts_dir.glob("*.mp4"))) if shorts_dir.exists() else 0

        runtime = meta.get("runtime") or meta.get("duration_sec", 0.0)
        word_count = meta.get("word_count") or meta.get("total_word_count", 0)
        title = meta.get("title") or meta.get("video_title", job_id)
        scheduled_slot = meta.get("scheduled_publish_slot") or meta.get("publish_at_iso", "Unscheduled")

        jobs.append({
            "job_id": job_id,
            "path": str(entry),
            "title": title,
            "runtime": runtime,
            "word_count": word_count,
            "scheduled_publish_slot": scheduled_slot,
            "has_master": master_video.exists(),
            "has_thumbnail": thumbnail.exists(),
            "shorts_count": shorts_count,
            "status": meta.get("status", "PENDING_REVIEW"),
        })

    return jobs


def get_job_details(job_id: str, base_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Retrieves full details and formatted checklist for a specific job."""
    job_id = _validate_safe_id(job_id, "job_id")
    pending_dir, _, _ = get_staging_paths(base_dir)
    job_path = pending_dir / job_id
    if not job_path.exists():
        raise FileNotFoundError(f"Job '{job_id}' not found in {pending_dir}")

    meta_file = job_path / "metadata.json"
    meta: Dict[str, Any] = {}
    if meta_file.exists():
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

    master_video = job_path / "master_video.mp4"
    thumbnail = job_path / "thumbnail.png"
    shorts_dir = job_path / "shorts"
    shorts_files = sorted([f.name for f in shorts_dir.glob("*.mp4")]) if shorts_dir.exists() else []

    runtime_sec = float(meta.get("runtime") or meta.get("duration_sec", 0.0))
    minutes = int(runtime_sec // 60)
    seconds = int(runtime_sec % 60)
    formatted_runtime = f"{minutes}m {seconds:02d}s ({runtime_sec:.1f}s)" if runtime_sec > 0 else "Unknown"

    word_count = meta.get("word_count") or meta.get("total_word_count", 0)
    title = meta.get("title") or meta.get("video_title", job_id)
    slot = meta.get("scheduled_publish_slot") or meta.get("publish_at_iso", "Unscheduled")

    formatted_checklist = "Review Checklist:\n" + "\n".join(f"  [ ] {item}" for item in CHECKLIST_ITEMS)

    return {
        "job_id": job_id,
        "job_path": str(job_path),
        "title": title,
        "runtime_seconds": runtime_sec,
        "formatted_runtime": formatted_runtime,
        "word_count": word_count,
        "scheduled_publish_slot": slot,
        "has_master_video": master_video.exists(),
        "has_thumbnail": thumbnail.exists(),
        "shorts": shorts_files,
        "shorts_count": len(shorts_files),
        "status": meta.get("status", "PENDING_REVIEW"),
        "metadata": meta,
        "checklist": CHECKLIST_ITEMS,
        "formatted_checklist": formatted_checklist,
    }


def approve_and_schedule(
    job_id: str,
    privacy: str = "private",
    base_dir: Optional[Path] = None,
    run_upload: bool = True,
    publish_at_iso: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Approve & Schedule action:
    Moves files from `pending_review/{job_id}/` to `approved/{job_id}/`,
    updates metadata status to 'APPROVED', and calls `upload_video.py`
    with `--privacy private` or `--privacy scheduled`.
    """
    job_id = _validate_safe_id(job_id, "job_id")
    if privacy not in ("private", "scheduled", "unlisted", "public"):
        privacy = "private"

    pending_dir, approved_dir, _ = get_staging_paths(base_dir)
    src_path = pending_dir / job_id
    if not src_path.exists():
        raise FileNotFoundError(f"Cannot approve job '{job_id}': folder not found in {pending_dir}")

    approved_dir.mkdir(parents=True, exist_ok=True)
    dst_path = approved_dir / job_id

    # If destination exists already, remove or merge
    if dst_path.exists():
        shutil.rmtree(dst_path)

    shutil.move(str(src_path), str(dst_path))
    logger.info(f"[HITL Review Gate] Moved {job_id} to approved destination: {dst_path}")

    # Update metadata
    meta_path = dst_path / "metadata.json"
    meta: Dict[str, Any] = {}
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            meta = {}

    meta["status"] = "APPROVED"
    meta["approved_at"] = datetime.now(timezone.utc).isoformat()
    meta["approved_privacy"] = privacy
    if publish_at_iso:
        meta["scheduled_publish_slot"] = publish_at_iso
        meta["publish_at_iso"] = publish_at_iso

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    # Update run_manifest.json for compliance guard
    manifest_path = dst_path / "run_manifest.json"
    manifest: Dict[str, Any] = {}
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as mf:
                manifest = json.load(mf)
        except Exception:
            manifest = {}
    manifest["status"] = "APPROVED"
    manifest["reviewed_by"] = "HUMAN_OPERATOR"
    manifest["approved_at"] = meta["approved_at"]
    manifest["privacy"] = privacy
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2)

    upload_result = None
    if run_upload:
        logger.info(f"[HITL Review Gate] Invoking upload_video.py for {job_id} (privacy={privacy})...")
        cmd = [
            sys.executable,
            str(UPLOAD_SCRIPT_PATH),
            "--video_id", job_id,
            "--output_dir", str(approved_dir),
            "--privacy", privacy,
        ]
        if publish_at_iso:
            cmd.extend(["--publish_at", publish_at_iso])

        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            upload_result = {
                "returncode": res.returncode,
                "stdout": res.stdout[-400:] if res.stdout else "",
                "stderr": res.stderr[-400:] if res.stderr else "",
            }
            if res.returncode == 0:
                logger.info(f"[HITL Review Gate] upload_video.py completed successfully for {job_id}.")
            else:
                logger.warning(f"[HITL Review Gate] upload_video.py notice (code {res.returncode}): {res.stderr[:200]}")
        except Exception as ue:
            logger.warning(f"[HITL Review Gate] Could not spawn upload subprocess: {ue}")
            upload_result = {"error": str(ue)}

    return {
        "job_id": job_id,
        "status": "APPROVED",
        "privacy": privacy,
        "approved_dir": str(dst_path),
        "metadata_file": str(meta_path),
        "upload_result": upload_result,
    }


def reroll_single_shot(
    job_id: str,
    shot_id: str,
    base_dir: Optional[Path] = None,
    allow_proxies: bool = True,
) -> Dict[str, Any]:
    """
    Re-roll Single Shot action:
    Finds prompt for `shot_id` (e.g. `act03_shot02`), re-runs image generation
    for that specific prompt, re-muxes the video clip, and updates `master_video.mp4`
    without re-rendering the other 79 shots.
    """
    from longform_engine.assemble_longform import (
        generate_16x9_visual,
        render_cinematic_shot,
        get_audio_duration,
        synthesize_speech,
        EDGE_TTS_VOICE_P1,
        generate_thumbnail,
        burn_act_badge,
    )
    from pipeline.compositor import FOOOCUS_NEGATIVE_PROMPT_LOCK

    job_id = _validate_safe_id(job_id, "job_id")
    shot_id = _validate_safe_id(shot_id, "shot_id")
    pending_dir, _, _ = get_staging_paths(base_dir)
    job_path = pending_dir / job_id
    if not job_path.exists():
        raise FileNotFoundError(f"Cannot reroll shot in job '{job_id}': folder not found in {pending_dir}")

    meta_file = job_path / "metadata.json"
    meta: Dict[str, Any] = {}
    if meta_file.exists():
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

    # Locate draft script
    draft_path_str = meta.get("draft_path")
    draft_data: Dict[str, Any] = {}
    if draft_path_str and Path(draft_path_str).exists():
        with open(draft_path_str, "r", encoding="utf-8") as df:
            draft_data = json.load(df)
    else:
        # Check standard draft directories
        possible_draft = _ROOT / "longform_engine" / "drafts" / f"{job_id}_80shots.json"
        if possible_draft.exists():
            with open(possible_draft, "r", encoding="utf-8") as df:
                draft_data = json.load(df)

    # Search for shot definition across acts
    target_shot: Optional[Dict[str, Any]] = None
    target_act_num: int = 1
    acts = draft_data.get("acts", [])

    for a_idx, act in enumerate(acts, start=1):
        shots = act.get("shots", [])
        for s_idx, s in enumerate(shots, start=1):
            sid = s.get("shot_id") or f"act{a_idx:02d}_shot{s_idx:02d}"
            if sid == shot_id:
                target_shot = s
                target_act_num = a_idx
                break
        if target_shot:
            break

    # If shot was not found by exact string, attempt parsing act/shot indices
    if not target_shot:
        try:
            # Format: act03_shot02
            clean_sid = shot_id.lower().replace("act", "").replace("shot", "")
            parts = clean_sid.split("_")
            if len(parts) == 2:
                a_i = int(parts[0]) - 1
                s_i = int(parts[1]) - 1
                if 0 <= a_i < len(acts):
                    act_shots = acts[a_i].get("shots", [])
                    if 0 <= s_i < len(act_shots):
                        target_shot = act_shots[s_i]
                        target_act_num = a_i + 1
        except Exception:
            pass

    prompt = target_shot.get("prompt") if target_shot else f"Photorealistic 16:9 cinematic historical scene for {shot_id}"
    neg_prompt = target_shot.get("negative_prompt", FOOOCUS_NEGATIVE_PROMPT_LOCK) if target_shot else FOOOCUS_NEGATIVE_PROMPT_LOCK
    motion = target_shot.get("motion", "push_in") if target_shot else "push_in"
    narration = target_shot.get("narration", "") if target_shot else ""

    temp_dir = job_path / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    images_cache = temp_dir / "images"
    images_cache.mkdir(parents=True, exist_ok=True)

    img_path = images_cache / f"{shot_id}.png"
    # Remove existing image to ensure fresh generation
    if img_path.exists():
        img_path.unlink()

    logger.info(f"[HITL Review Gate] Re-rolling visual keyframe for {shot_id} in job {job_id}...")
    generate_16x9_visual(
        prompt=prompt,
        negative_prompt=neg_prompt,
        output_path=img_path,
        aspect_ratio="1344*768",
        allow_proxies=allow_proxies,
    )

    # Re-mux single shot video clip
    shot_audio_path = temp_dir / f"audio_{shot_id}.mp3"
    if not shot_audio_path.exists() or shot_audio_path.stat().st_size < 100:
        if narration:
            synthesize_speech(narration, EDGE_TTS_VOICE_P1, shot_audio_path)
        else:
            # Default 6-second silent audio if no narration exists
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                "-t", "6.0", str(shot_audio_path)
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    shot_dur = get_audio_duration(shot_audio_path)
    if shot_dur < 1.0:
        shot_dur = 6.0

    shot_video_only = temp_dir / f"video_{shot_id}.mp4"
    render_cinematic_shot(
        image_path=img_path,
        output_mp4_path=shot_video_only,
        duration_sec=shot_dur,
        motion_type=motion,
        fps=30
    )

    clip_synced = temp_dir / f"clip_{shot_id}_synced.mp4"
    cmd_mux = [
        "ffmpeg", "-y",
        "-i", str(shot_video_only),
        "-i", str(shot_audio_path),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(clip_synced)
    ]
    subprocess.run(cmd_mux, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    logger.info(f"[HITL Review Gate] Single shot clip re-muxed successfully: {clip_synced.name}")

    # Re-assemble the affected act segment
    act_concat_list = temp_dir / f"concat_act_{target_act_num:02d}.txt"
    seg_mp4 = temp_dir / f"seg_act_{target_act_num:02d}.mp4"
    seg_badged_mp4 = temp_dir / f"seg_act_{target_act_num:02d}_badged.mp4"
    if act_concat_list.exists():
        cmd_act = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(act_concat_list),
            "-c", "copy",
            str(seg_mp4)
        ]
        subprocess.run(cmd_act, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        # Update badged act segment referenced by concat_list.txt
        act_title = f"Act {target_act_num}"
        if 0 <= target_act_num - 1 < len(acts):
            act_title = acts[target_act_num - 1].get("title", act_title)
        try:
            burn_act_badge(seg_mp4, seg_badged_mp4, act_title, target_act_num)
        except Exception:
            shutil.copy(seg_mp4, seg_badged_mp4)

    # Re-assemble master_video.mp4 if master concatenation list is present
    master_concat_list = temp_dir / "concat_list.txt"
    master_video = job_path / "master_video.mp4"
    chapters_meta = temp_dir / "chapters.ffmetadata"

    if master_concat_list.exists():
        raw_master = temp_dir / "raw_master.mp4"
        cmd_master = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(master_concat_list),
            "-c", "copy",
            str(raw_master)
        ]
        subprocess.run(cmd_master, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        if chapters_meta.exists():
            cmd_meta = [
                "ffmpeg", "-y",
                "-i", str(raw_master),
                "-i", str(chapters_meta),
                "-map_metadata", "1",
                "-codec", "copy",
                str(master_video)
            ]
            subprocess.run(cmd_meta, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        else:
            shutil.copy(raw_master, master_video)
    elif not master_video.exists():
        # In isolated test or single-shot preview mode, copy synced clip to master
        shutil.copy(clip_synced, master_video)

    # Update thumbnail if shot_id was the first shot
    thumb_path = job_path / "thumbnail.png"
    if "01_shot01" in shot_id or not thumb_path.exists():
        generate_thumbnail(master_video, thumb_path, fallback_image=img_path)

    # Update metadata audit trail
    rerolls = meta.get("rerolls", [])
    rerolls.append({
        "shot_id": shot_id,
        "act": target_act_num,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt": prompt[:80] + "...",
        "image_file": str(img_path.name),
    })
    meta["rerolls"] = rerolls
    with open(meta_file, "w", encoding="utf-8") as mf:
        json.dump(meta, mf, indent=2, ensure_ascii=False)

    logger.info(f"[HITL Review Gate] Shot {shot_id} successfully re-rolled and master_video.mp4 updated.")
    return {
        "job_id": job_id,
        "shot_id": shot_id,
        "status": "REROLLED",
        "image_path": str(img_path),
        "clip_path": str(clip_synced),
        "master_video": str(master_video),
        "total_rerolls": len(rerolls),
    }


def reject_and_scrap(
    job_id: str,
    reason: str = "",
    base_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Reject & Scrap action:
    Moves files to `longform_engine/output/scrapped/{video_id}/`,
    sets status to 'REJECTED_SCRAPPED', and writes run_manifest.json
    so any future upload attempts to YouTube are permanently rejected.
    """
    job_id = _validate_safe_id(job_id, "job_id")
    pending_dir, _, scrapped_dir = get_staging_paths(base_dir)
    src_path = pending_dir / job_id
    if not src_path.exists():
        raise FileNotFoundError(f"Cannot scrap job '{job_id}': folder not found in {pending_dir}")

    scrapped_dir.mkdir(parents=True, exist_ok=True)
    dst_path = scrapped_dir / job_id

    if dst_path.exists():
        shutil.rmtree(dst_path)

    shutil.move(str(src_path), str(dst_path))
    logger.info(f"[HITL Review Gate] Moved {job_id} to scrapped destination: {dst_path}")

    # Update metadata.json
    meta_path = dst_path / "metadata.json"
    meta: Dict[str, Any] = {}
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            meta = {}

    meta["status"] = "REJECTED_SCRAPPED"
    meta["rejected_at"] = datetime.now(timezone.utc).isoformat()
    meta["rejection_reason"] = reason or "Human reviewer rejected visual quality/packaging."
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    # Write run_manifest.json with permanent rejection status
    manifest_path = dst_path / "run_manifest.json"
    manifest = {
        "job_id": job_id,
        "status": "REJECTED_SCRAPPED",
        "rejection_reason": meta["rejection_reason"],
        "rejected_at": meta["rejected_at"],
        "reviewed_by": "HUMAN_OPERATOR",
        "lock": "PERMANENT_SCRAP_LOCK",
    }
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2)

    logger.info(f"[HITL Review Gate] Job {job_id} permanently scrapped. Reason: {meta['rejection_reason']}")
    return {
        "job_id": job_id,
        "status": "REJECTED_SCRAPPED",
        "scrapped_dir": str(dst_path),
        "reason": meta["rejection_reason"],
    }


def interactive_cli(target_job_id: Optional[str] = None):
    """Interactive Command-Line Interface for Human Review Staging Gate."""
    print("\n" + "=" * 70)
    print("      HUMAN-IN-THE-LOOP (HITL) VIDEO REVIEW STAGING GATE")
    print("=" * 70)

    job_id = target_job_id
    if not job_id:
        jobs = list_pending_jobs()
        if not jobs:
            print("\n  [INFO] No pending review jobs found in:")
            print(f"         {DEFAULT_PENDING_DIR}")
            print("\n  Render a video first via assemble_longform.py.")
            print("=" * 70 + "\n")
            return

        print(f"\n  Found {len(jobs)} job(s) pending review:\n")
        for idx, j in enumerate(jobs, start=1):
            dur_min = j['runtime'] / 60 if j['runtime'] else 0
            print(f"  [{idx}] {j['job_id']}")
            print(f"      Title: {j['title']}")
            print(f"      Runtime: {dur_min:.1f}m | Word count: {j['word_count']} | Shorts: {j['shorts_count']}")
            print(f"      Scheduled Slot: {j['scheduled_publish_slot']}")
            print()

        try:
            selection = input("  Select job number to review (or 'q' to quit): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            return

        if selection.lower() in ("q", "quit", "exit", ""):
            return

        try:
            sel_idx = int(selection) - 1
            selected_job = jobs[sel_idx]
            job_id = selected_job["job_id"]
        except Exception:
            print("Invalid selection.")
            return

    details = get_job_details(job_id)

    print("\n" + "-" * 70)
    print(f"  JOB DETAILS: {details['title']} ({job_id})")
    print("-" * 70)
    print(f"  Runtime:                {details['formatted_runtime']}")
    print(f"  Word Count:             {details['word_count']}")
    print(f"  Scheduled Publish Slot: {details['scheduled_publish_slot']}")
    print(f"  Master Video:           {'Present (master_video.mp4)' if details['has_master_video'] else 'MISSING'}")
    print(f"  Thumbnail:              {'Present (thumbnail.png)' if details['has_thumbnail'] else 'MISSING'}")
    print(f"  Derived 9:16 Shorts:    {details['shorts_count']} items in shorts/")
    print("\n" + details["formatted_checklist"])
    print("-" * 70)

    print("\n  ACTIONS:")
    print("    [1] Approve & Schedule  (moves to approved/ and calls upload_video.py)")
    print("    [2] Re-roll Single Shot (prompts for shot_id e.g. act03_shot02)")
    print("    [3] Reject & Scrap      (permanently scraps video)")
    print("    [q] Cancel / Quit")

    try:
        action = input("\n  Enter action [1-3] or 'q': ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    if action == "1":
        print("\n  Select Upload Privacy:")
        print("    [1] private (Default / Recommended)")
        print("    [2] scheduled (YouTube automated release queue)")
        p_choice = input("  Enter privacy [1/2] (default 1): ").strip()
        privacy = "scheduled" if p_choice == "2" else "private"
        res = approve_and_schedule(job_id, privacy=privacy)
        print(f"\n  [OK] Job '{job_id}' APPROVED successfully!")
        print(f"  Target Directory: {res['approved_dir']}")
        print(f"  Privacy: {res['privacy']}")

    elif action == "2":
        shot_id = input("\n  Enter shot_id to re-roll (e.g. act03_shot02): ").strip()
        if not shot_id:
            print("Shot ID required.")
            return
        res = reroll_single_shot(job_id, shot_id=shot_id, allow_proxies=True)
        print(f"\n  [OK] Shot '{shot_id}' re-rolled successfully!")
        print(f"  Updated Clip: {res['clip_path']}")
        print(f"  Master Video: {res['master_video']}")

    elif action == "3":
        reason = input("\n  Enter rejection reason: ").strip()
        res = reject_and_scrap(job_id, reason=reason)
        print(f"\n  [OK] Job '{job_id}' SCRAPPED.")
        print(f"  Moved to: {res['scrapped_dir']}")

    print("\n" + "=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Human-in-the-Loop Review Staging Gate")
    parser.add_argument("--list", action="store_true", help="List all pending jobs")
    parser.add_argument("--job", dest="job_id", default=None, help="Target job ID")
    parser.add_argument("--action", choices=["approve", "reroll", "reject", "details"], default=None, help="Action to perform")
    parser.add_argument("--privacy", choices=["private", "scheduled", "unlisted", "public"], default="private", help="Privacy target for approval")
    parser.add_argument("--publish-at", dest="publish_at_iso", default=None, help="ISO timestamp for scheduled release")
    parser.add_argument("--shot-id", dest="shot_id", default=None, help="Shot ID to re-roll (e.g. act03_shot02)")
    parser.add_argument("--reason", default="", help="Rejection reason")
    parser.add_argument("--no-upload", action="store_true", help="Do not trigger upload subprocess on approval")
    parser.add_argument("--allow-proxies", action="store_true", default=True, help="Allow provisional canvas proxies during re-roll")

    args = parser.parse_args()

    if args.list:
        jobs = list_pending_jobs()
        print(f"Pending jobs ({len(jobs)}):")
        for j in jobs:
            print(f"  - {j['job_id']}: {j['title']} (Runtime: {j['runtime']:.1f}s, Shorts: {j['shorts_count']})")
        return

    if args.action and not args.job_id:
        parser.error("--job is required when --action is specified")

    if args.action == "details":
        d = get_job_details(args.job_id)
        print(json.dumps(d, indent=2))
        return

    if args.action == "approve":
        res = approve_and_schedule(
            args.job_id,
            privacy=args.privacy,
            run_upload=not args.no_upload,
            publish_at_iso=args.publish_at_iso,
        )
        print(f"Approved job {args.job_id}: {res}")
        return

    if args.action == "reroll":
        if not args.shot_id:
            parser.error("--shot-id is required for reroll action")
        res = reroll_single_shot(args.job_id, shot_id=args.shot_id, allow_proxies=args.allow_proxies)
        print(f"Rerolled shot {args.shot_id}: {res}")
        return

    if args.action == "reject":
        res = reject_and_scrap(args.job_id, reason=args.reason)
        print(f"Scrapped job {args.job_id}: {res}")
        return

    # Default to interactive CLI if no action specified
    interactive_cli(target_job_id=args.job_id)


if __name__ == "__main__":
    main()
