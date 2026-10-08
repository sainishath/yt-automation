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
    force_rebuild: bool = False,
    is_factual: Optional[bool] = None,
    series_name: Optional[str] = None,
    part_number: Optional[int] = None,
    total_parts: Optional[int] = None
) -> Dict[str, Any]:
    """
    Executes the end-to-end Channel A production workflow.
    Supports both Counterfactual Alternate History and 100% Factual RAG Documentary modes.
    Supports multi-part serialized narrative sagas with cliffhangers.
    Strictly halts at AWAITING_REVIEW after sending a proxy to Discord.
    """
    start_time = time.time()
    if not video_id:
        video_id = f"video_{int(time.time())}_{os.urandom(2).hex()}"
    job_id = f"job_{video_id}"

    base_out = Path(output_dir) if output_dir else _BASE_DIR / "output"
    video_path = base_out / video_id
    video_path.mkdir(parents=True, exist_ok=True)

    # 1. Content Brain v1 Strategic Initialization
    ROOT_REPO = Path(__file__).resolve().parent.parent.parent
    if str(ROOT_REPO) not in sys.path:
        sys.path.insert(0, str(ROOT_REPO))

    from growth.strategy.strategy_manager import StrategyManager
    from growth.brain.decision_engine import DecisionEngine
    from growth.brain.memory import BrainMemory
    from growth.db.database import DEFAULT_DB_PATH

    strat_mgr = StrategyManager()
    strat_ctx = strat_mgr.get_active_strategy_context("channel_a")
    strategy_version = strat_ctx.get("strategy_version", "v1.0")

    experiment_id = None
    arm_id = "control"
    variant_id = "control"
    tested_variable = "HOOK_STRUCTURE"
    try:
        mem = BrainMemory(DEFAULT_DB_PATH)
        dec_engine = DecisionEngine(mem)
        decision = dec_engine.recommend_next_decision("channel_a")
        if decision and decision.experiment_id:
            experiment_id = decision.experiment_id
            arm_id = decision.arm_id or "control"
            variant_id = arm_id
            tested_variable = decision.variable_under_test or "HOOK_STRUCTURE"
    except Exception as de_err:
        logger.info(f"[Content Brain] Running under baseline strategy: {de_err}")

    # 1. Initialize run_manifest.json with Content Brain Lineage
    manifest_path = video_path / "run_manifest.json"
    manifest = {
        "video_id": video_id,
        "topic": topic,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pipeline_version": "1.0-production",
        "status": "RUNNING",
        "content_brain": {
            "strategy_version": strategy_version,
            "experiment_id": experiment_id,
            "arm_id": arm_id,
            "tested_variable": tested_variable
        },
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
    print(f"  Strategy: {strategy_version} | Exp: {experiment_id} | Arm: {arm_id}")
    print(f"=======================================================\n")

    # ----------------------------------------------------
    # Sync with Growth Intelligence Database (growth.db)
    # ----------------------------------------------------
    growth_repo = None
    try:
        from growth.db.models import GrowthRepository, JobModel, VideoModel
        from growth.db.database import DEFAULT_DB_PATH
        growth_repo = GrowthRepository(DEFAULT_DB_PATH)
        job_entry = JobModel(
            job_id=job_id,
            channel_id="channel_a",
            pipeline_id="alternate-history-shorts",
            topic_text=topic,
            status="GENERATING",
            video_id=video_id,
            strategy_version=strategy_version,
            experiment_id=experiment_id,
            arm_id=arm_id,
            variant_id=variant_id
        )
        growth_repo.upsert_job(job_entry)
        logger.info(f"[{video_id}] growth.db synchronized: Job {job_id} set to GENERATING.")
    except Exception as g_err:
        logger.warning(f"[{video_id}] Notice: growth.db job initialization skipped: {g_err}")

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
        logger.info(f"[{video_id}] Stage 2: Script Generation & Post-Verification with Hybrid Critic...")
        script = generate_script(
            topic,
            video_id,
            style_config,
            output_dir=str(base_out),
            strategy_context=strat_ctx,
            is_factual=is_factual,
            series_name=series_name,
            part_number=part_number,
            total_parts=total_parts
        )
        if script.get("status") == "BLOCKED":
            manifest["stages"]["script"] = "BLOCKED"
            manifest["status"] = "BLOCKED"
            manifest["failures"].append("Script generation blocked by RAG / Critic gate")
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
            manifest["status"] = "AWAITING_REVIEW"
            logger.info(f"[{video_id}] PIPELINE QA PASSED - TRANSITIONING TO AWAITING_REVIEW")

            # Update growth.db state: Register video & mark job AWAITING_REVIEW
            if growth_repo:
                try:
                    final_mp4 = manifest["artifacts"].get("final_video")
                    duration_sec = qa_report.get("metrics", {}).get("duration_seconds", 45.0)
                    meta_path = video_path / "metadata.json"
                    meta_title = f"What If {topic}?"
                    meta_desc = ""
                    if meta_path.exists():
                        try:
                            with open(meta_path, "r", encoding="utf-8") as mf_json:
                                meta_d = json.load(mf_json)
                                meta_title = meta_d.get("title", meta_title)
                                meta_desc = meta_d.get("description", meta_desc)
                        except Exception:
                            pass

                    v_model = VideoModel(
                        video_id=video_id,
                        channel_id="channel_a",
                        pipeline_id="alternate-history-shorts",
                        title=meta_title,
                        description=meta_desc,
                        duration=float(duration_sec),
                        upload_status="GENERATED",
                        privacy_status="private",
                        qa_score=1.0,
                        review_status="PENDING",
                        strategy_version=strategy_version,
                        topic_id=f"topic_{video_id}",
                        experiment_id=experiment_id,
                        arm_id=arm_id,
                        variant_id=variant_id
                    )
                    growth_repo.upsert_video(v_model)

                    job_entry = JobModel(
                        job_id=job_id,
                        channel_id="channel_a",
                        pipeline_id="alternate-history-shorts",
                        topic_text=topic,
                        status="AWAITING_REVIEW",
                        video_id=video_id,
                        strategy_version=strategy_version,
                        experiment_id=experiment_id,
                        arm_id=arm_id,
                        variant_id=variant_id
                    )
                    growth_repo.upsert_job(job_entry)
                    logger.info(f"[{video_id}] growth.db synchronized: Video {video_id} registered, Job {job_id} -> AWAITING_REVIEW.")
                except Exception as g_sync_err:
                    logger.warning(f"[{video_id}] Notice: growth.db QA sync error: {g_sync_err}")

            # Post to Discord Review Webhook
            try:
                logger.info(f"[{video_id}] Compressing < 8MB review proxy and posting to Discord webhook...")
                from discord_review import post_for_review
                final_mp4 = manifest["artifacts"].get("final_video")
                if final_mp4 and os.path.exists(final_mp4):
                    post_for_review("pipeline1", job_id, [final_mp4], "video")
                    print(f"\n[{video_id}] Proxy dispatched to Discord. Awaiting manual approval.\n")
                else:
                    logger.warning(f"[{video_id}] Final MP4 artifact not found at {final_mp4}")
            except Exception as dw_err:
                logger.error(f"[{video_id}] Discord review dispatch failed: {dw_err}")
        else:
            manifest["status"] = "BLOCKED"
            manifest["failures"].extend(qa_report.get("failures", []))
            logger.error(f"[{video_id}] PIPELINE RUN BLOCKED AT QA GATE: {manifest['failures']}")
            if growth_repo:
                try:
                    job_fail = JobModel(
                        job_id=job_id,
                        channel_id="channel_a",
                        pipeline_id="alternate-history-shorts",
                        topic_text=topic,
                        status="QA_FAILED",
                        video_id=video_id,
                        error_message="; ".join(manifest["failures"])
                    )
                    growth_repo.upsert_job(job_fail)
                except Exception:
                    pass

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
    parser.add_argument("--topic", required=True, help="Alternate history what-if topic or historical event")
    parser.add_argument("--video_id", help="Custom video folder ID")
    parser.add_argument("--output_dir", default=None, help="Custom output directory")
    parser.add_argument("--force", action="store_true", help="Force rebuild all assets")
    parser.add_argument("--no_fallback", action="store_true", help="Disallow Pillow proof fallback for images")
    parser.add_argument("--factual", action="store_true", help="Run in 100%% factual historical documentary mode")
    parser.add_argument("--series_name", default=None, help="Name of the multi-part historical saga")
    parser.add_argument("--part_number", type=int, default=None, help="Current episode/part number in the series")
    parser.add_argument("--total_parts", type=int, default=None, help="Total number of parts in the series")
    args = parser.parse_args()

    allow_fallback = not args.no_fallback
    res = run_pipeline1(
        args.topic,
        video_id=args.video_id,
        output_dir=args.output_dir,
        allow_fallback=allow_fallback,
        force_rebuild=args.force,
        is_factual=args.factual,
        series_name=args.series_name,
        part_number=args.part_number,
        total_parts=args.total_parts
    )

    print(f"\n=======================================================")
    print(f"  RUNNER SUMMARY: {res.get('video_id')} -> {res.get('status')}")
    print(f"  Final Video: {res.get('video_path')}")
    print(f"  Total Execution Time: {res.get('total_time_seconds')}s")
    print(f"=======================================================\n")
    sys.exit(0 if res.get("status") in ("AWAITING_REVIEW", "READY") else 1)
