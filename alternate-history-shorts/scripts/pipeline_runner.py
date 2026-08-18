# -*- coding: utf-8 -*-
"""
pipeline_runner.py
------------------
Unified Production Orchestrator for Pipeline 1 (Alternate-History Shorts).
Executes the full automated workflow from Topic to QA-verified Final MP4 without manual intervention:
1. Initialize clean workspace and run_manifest.json
2. RAG v4 Evidence Generation & Sufficiency Gating
3. Script Generation & Claim Verification
4. TTS Audio Generation (Edge-TTS)
5. Whisper Word-Level Acoustic Alignment
6. Semantic Visual Scene Planning & RAG Visual Evidence Injection
7. Beat-Level Image Generation (Fooocus / Fallback Proofing)
8. Video Assembly (Motion + ASS Highlights + Audio Muxing + Music)
9. YouTube Metadata Generation
10. Final QA Gate Validation
"""

import os
import sys
import json
import time
import shutil
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional

_DIR = Path(__file__).parent.resolve()
_BASE_DIR = _DIR.parent.resolve()
sys.path.insert(0, str(_DIR))

from rag_grounding import generate_evidence_packet
from generate_script import generate_script
from generate_audio import process_video_audio
from whisper_alignment import align_video_job
from visual_scene_planner import plan_visual_scenes
from generate_images import process_video_images
from assemble_video import assemble_video
from generate_metadata import generate_video_metadata
from qa_gate import run_pipeline1_qa

# Logging setup
LOG_FILE = _BASE_DIR / "pipeline.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("PipelineRunner")


def run_pipeline1(
    topic: str,
    video_id: Optional[str] = None,
    output_dir: Optional[str] = None,
    allow_fallback: bool = True,
    force_rebuild: bool = False
) -> Dict[str, Any]:
    """
    Full end-to-end production pipeline execution for Pipeline 1.
    Returns machine-readable run summary dictionary.
    """
    start_time = time.time()
    if not video_id:
        video_id = f"video_{int(time.time())}_{os.urandom(2).hex()}"

    base_out = Path(output_dir) if output_dir else _BASE_DIR / "output"
    video_path = base_out / video_id
    video_path.mkdir(parents=True, exist_ok=True)

    # 1. Initialize run_manifest.json
    manifest_path = video_path / "run_manifest.json"
    manifest = {
        "video_id": video_id,
        "topic": topic,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pipeline_version": "1.0-production",
        "status": "RUNNING",
        "stages": {
            "rag": "PENDING",
            "script": "PENDING",
            "audio": "PENDING",
            "alignment": "PENDING",
            "scene_plan": "PENDING",
            "images": "PENDING",
            "assembly": "PENDING",
            "metadata": "PENDING",
            "qa": "PENDING"
        },
        "artifacts": {},
        "failures": []
    }

    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2, ensure_ascii=False)

    print(f"\n=======================================================")
    print(f"  PIPELINE 1 PRODUCTION RUN: {video_id} ")
    print(f"  Topic: \"{topic}\"")
    print(f"=======================================================\n")

    # Load style configuration
    style_path = _BASE_DIR / "config" / "style.json"
    with open(style_path, "r", encoding="utf-8") as sf:
        style_config = json.load(sf)

    try:
        # ----------------------------------------------------
        # Stage 1: RAG v4 Evidence Generation
        # ----------------------------------------------------
        logger.info(f"[{video_id}] Stage 1: RAG v4 Grounding & Evidence Extraction...")
        evidence_packet = generate_evidence_packet(video_id, topic, output_dir=str(base_out))
        retrieval_status = evidence_packet.get("retrieval_status", "INSUFFICIENT")

        if retrieval_status == "INSUFFICIENT":
            manifest["stages"]["rag"] = "BLOCKED"
            manifest["status"] = "BLOCKED"
            manifest["failures"].append(f"RAG evidence is INSUFFICIENT for topic: '{topic}'")
            with open(manifest_path, "w", encoding="utf-8") as mf:
                json.dump(manifest, mf, indent=2, ensure_ascii=False)
            logger.error(f"[{video_id}] Pipeline blocked: Insufficient historical grounding.")
            return {"status": "BLOCKED", "reason": "INSUFFICIENT_HISTORICAL_EVIDENCE", "manifest": manifest}

        manifest["stages"]["rag"] = "PASS"
        manifest["artifacts"]["evidence_packet"] = str((video_path / "evidence_packet.json").as_posix())

        # ----------------------------------------------------
        # Stage 2: Script Generation & Claim Verification
        # ----------------------------------------------------
        logger.info(f"[{video_id}] Stage 2: Script Generation & Post-Verification...")
        script = generate_script(topic, video_id, style_config, output_dir=str(base_out), evidence_packet=evidence_packet)
        if script.get("status") == "BLOCKED":
            manifest["stages"]["script"] = "BLOCKED"
            manifest["status"] = "BLOCKED"
            manifest["failures"].append("Script generation blocked by RAG gate")
            with open(manifest_path, "w", encoding="utf-8") as mf:
                json.dump(manifest, mf, indent=2, ensure_ascii=False)
            return {"status": "BLOCKED", "reason": "SCRIPT_GENERATION_BLOCKED", "manifest": manifest}

        manifest["stages"]["script"] = "PASS"
        manifest["artifacts"]["script"] = str((video_path / "script.json").as_posix())

        # ----------------------------------------------------
        # Stage 3: Audio Generation
        # ----------------------------------------------------
        logger.info(f"[{video_id}] Stage 3: TTS Audio Generation...")
        audio_res = process_video_audio(video_id, output_dir=str(base_out))
        manifest["stages"]["audio"] = "PASS"
        manifest["artifacts"]["audio_dir"] = str((video_path / "audio").as_posix())

        # ----------------------------------------------------
        # Stage 4: Whisper Alignment
        # ----------------------------------------------------
        logger.info(f"[{video_id}] Stage 4: Whisper Word-Level Alignment...")
        alignment_cache = align_video_job(video_id, output_dir=str(base_out), force_rebuild=force_rebuild)
        manifest["stages"]["alignment"] = "PASS"
        manifest["artifacts"]["alignment_cache"] = str((video_path / "audio" / "alignment_cache.json").as_posix())

        # ----------------------------------------------------
        # Stage 5: Semantic Visual Scene Planning & RAG Injection
        # ----------------------------------------------------
        logger.info(f"[{video_id}] Stage 5: Semantic Visual Scene Planning & RAG Grounding...")
        scene_plan = plan_visual_scenes(video_id, output_dir=str(base_out), force_rebuild=force_rebuild)
        manifest["stages"]["scene_plan"] = "PASS"
        manifest["artifacts"]["scene_plan"] = str((video_path / "scene_plan.json").as_posix())

        # ----------------------------------------------------
        # Stage 6: Image Generation
        # ----------------------------------------------------
        logger.info(f"[{video_id}] Stage 6: Image Generation...")
        img_res = process_video_images(
            video_id,
            output_dir=str(base_out),
            force_rebuild=force_rebuild,
            allow_fallback_flag=allow_fallback
        )
        manifest["stages"]["images"] = "PASS"
        manifest["artifacts"]["images_dir"] = str((video_path / "images").as_posix())

        # ----------------------------------------------------
        # Stage 7: Video Assembly
        # ----------------------------------------------------
        logger.info(f"[{video_id}] Stage 7: Video Assembly & Subtitle Burning...")
        final_mp4 = assemble_video(video_id, output_dir=str(base_out))
        manifest["stages"]["assembly"] = "PASS"
        manifest["artifacts"]["final_video"] = str(Path(final_mp4).as_posix())

        # ----------------------------------------------------
        # Stage 8: Metadata Generation
        # ----------------------------------------------------
        logger.info(f"[{video_id}] Stage 8: Metadata Generation...")
        metadata = generate_video_metadata(video_id, output_dir=str(base_out))
        manifest["stages"]["metadata"] = "PASS"
        manifest["artifacts"]["metadata"] = str((video_path / "metadata.json").as_posix())

        # ----------------------------------------------------
        # Stage 9: Final QA Gate
        # ----------------------------------------------------
        logger.info(f"[{video_id}] Stage 9: Production QA Gate...")
        qa_report = run_pipeline1_qa(video_id, output_dir=str(base_out))
        manifest["stages"]["qa"] = qa_report.get("status", "BLOCKED")
        manifest["qa_metrics"] = qa_report.get("metrics", {})

        if qa_report.get("passed", False):
            manifest["status"] = "READY"
            logger.info(f"[{video_id}] PIPELINE RUN COMPLETE - STATUS: READY")
        else:
            manifest["status"] = "BLOCKED"
            manifest["failures"].extend(qa_report.get("failures", []))
            logger.error(f"[{video_id}] PIPELINE RUN BLOCKED AT QA GATE: {manifest['failures']}")

    except Exception as e:
        logger.error(f"[{video_id}] Fatal Pipeline Error: {e}", exc_info=True)
        manifest["status"] = "FAILED"
        manifest["failures"].append(str(e))

    finally:
        total_time = round(time.time() - start_time, 2)
        manifest["total_time_seconds"] = total_time
        manifest["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(manifest_path, "w", encoding="utf-8") as mf:
            json.dump(manifest, mf, indent=2, ensure_ascii=False)

    return {
        "status": manifest["status"],
        "video_id": video_id,
        "video_path": manifest["artifacts"].get("final_video", ""),
        "total_time_seconds": total_time,
        "manifest": manifest
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline 1 Automated Production Runner")
    parser.add_argument("--topic", required=True, help="Alternate history what-if topic")
    parser.add_argument("--video_id", help="Custom video folder ID")
    parser.add_argument("--output_dir", default=None, help="Custom output directory")
    parser.add_argument("--force", action="store_true", help="Force rebuild all assets")
    parser.add_argument("--no_fallback", action="store_true", help="Disallow Pillow proof fallback for images")
    args = parser.parse_args()

    allow_fallback = not args.no_fallback
    res = run_pipeline1(
        args.topic,
        video_id=args.video_id,
        output_dir=args.output_dir,
        allow_fallback=allow_fallback,
        force_rebuild=args.force
    )

    print(f"\n=======================================================")
    print(f"  RUNNER SUMMARY: {res.get('video_id')} -> {res.get('status')}")
    print(f"  Final Video: {res.get('video_path')}")
    print(f"  Total Execution Time: {res.get('total_time_seconds')}s")
    print(f"=======================================================\n")
    sys.exit(0 if res.get("status") == "READY" else 1)
