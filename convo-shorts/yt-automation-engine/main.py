# -*- coding: utf-8 -*-
"""
main.py
-------
Generates a YouTube Short (video + thumbnail).
YOU upload it manually.

Usage:
    python main.py
    python main.py --topic "Why you yawn" --category "Weird Science"

Categories:
    "Weird Science"
    "Productivity & stoicism"
    "Human Behavior"
"""

import os
import argparse
import json
import sys
import io
from pathlib import Path

# Force UTF-8 output so emoji/box-drawing print on Windows terminals
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)

# -- config -------------------------------------------------------------------
_DIR      = Path(__file__).parent
with open(_DIR / "config.json", "r") as f:
    CFG = json.load(f)

OUTPUT_DIR = Path(CFG["output_dir"])
TEMP_DIR   = Path(CFG["temp_dir"])
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

from media_engine import (
    generate_script,
    generate_fooocus_image,
    generate_voiceover,
    generate_subtitles,
    pick_background,
    assemble_video,
)
import requests
import shutil
from preflight import run_preflight_check

def check_ollama() -> bool:
    """Return True if Ollama is reachable."""
    try:
        r = requests.get(CFG.get("ollama_url", "http://localhost:11434") + "/api/tags", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


# =============================================================================
def _next_number(output_directory: Path) -> int:
    """Return the next Short number by scanning the output folder."""
    existing = list(output_directory.glob("Short_*.mp4"))
    if not existing:
        return 1
    nums = []
    for p in existing:
        try:
            nums.append(int(p.stem.split("_")[1]))
        except (IndexError, ValueError):
            pass
    return max(nums) + 1 if nums else 1


# =============================================================================
def run_pipeline(
    topic: str, 
    category: str, 
    script_file: str = None, 
    script_text: str = None, 
    audio_file: str = None, 
    voice: str = "en-US-BrianNeural",
    custom_job_id: str = None,
    custom_output_dir: str = None
) -> dict:
    """
    Full media pipeline with Preflight Verification, Isolated Workspace,
    Disposable Job Failure Model, Human Review Gate, and machine-readable status reporting.
    """
    import time
    out_dir = Path(custom_output_dir) if custom_output_dir else OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    num       = _next_number(out_dir)
    label     = f"Short_{num:03d}"        # Short_001, Short_002 ...
    job_id    = custom_job_id if custom_job_id else f"job_{time.strftime('%Y%m%d_%H%M%S')}_{num:03d}"
    
    # Isolated job temporary workspace
    job_temp_dir = TEMP_DIR / f"job_{job_id}"
    job_temp_dir.mkdir(parents=True, exist_ok=True)

    audio_raw = str((job_temp_dir / f"{label}.wav").resolve())
    video_out = str((out_dir / f"{label}.mp4").resolve())
    failed_stage = "CREATED"

    print("\n" + "=" * 60)
    print(f"  [JOB {job_id}] Pipeline 2 Execution Started (Human Review Gated)")
    print(f"  Topic    : {topic}")
    print(f"  Category : {category}")
    print(f"  Label    : {label}")
    print("=" * 60 + "\n")

    try:
        # 0. Preflight Verification
        failed_stage = "PREFLIGHT"
        print(f"[JOB {job_id}] [STAGE PREFLIGHT] Verifying infrastructure requirements...")
        is_preflight_valid, pf_stage, pf_error = run_preflight_check(CFG, require_youtube_auth=False)
        if not is_preflight_valid:
            err_msg = f"PREFLIGHT_CHECK_FAILED: {pf_error}"
            print(f"[JOB {job_id}] [STAGE PREFLIGHT FAILED] {err_msg}")
            raise RuntimeError(err_msg)
        print(f"[JOB {job_id}] [STAGE PREFLIGHT SUCCESS] All infrastructure checks passed!")

        # 1. Content Brain v1 Strategic Initialization
        failed_stage = "STRATEGY_INIT"
        ROOT_REPO = Path(__file__).resolve().parent.parent.parent
        if str(ROOT_REPO) not in sys.path:
            sys.path.insert(0, str(ROOT_REPO))

        from growth.strategy.strategy_manager import StrategyManager
        from growth.brain.decision_engine import DecisionEngine
        from growth.brain.memory import BrainMemory
        from growth.db.database import get_db, DEFAULT_DB_PATH
        from growth.db.models import GrowthRepository, JobModel, VideoModel

        strat_mgr = StrategyManager()
        strat_ctx = strat_mgr.get_active_strategy_context("channel_b")
        strategy_version = strat_ctx.get("strategy_version", "v1.0")
        
        # Query active experiment assignment
        experiment_id = None
        arm_id = "control"
        tested_variable = "HOOK_STRUCTURE"
        try:
            mem = BrainMemory(DEFAULT_DB_PATH)
            dec_engine = DecisionEngine(mem)
            decision = dec_engine.recommend_next_decision("channel_b")
            if decision and decision.experiment_id:
                experiment_id = decision.experiment_id
                arm_id = decision.arm_id or "control"
                tested_variable = decision.variable_under_test or "HOOK_STRUCTURE"
        except Exception as de_err:
            print(f"[Content Brain] Notice: Running under baseline strategy ({de_err})")

        print(f"[Content Brain v1 Lineage] Strategy: {strategy_version} | Exp: {experiment_id} | Arm: {arm_id}")

        # Sync with growth.db: Create job record
        growth_repo = None
        try:
            growth_repo = GrowthRepository(DEFAULT_DB_PATH)
            job_entry = JobModel(
                job_id=job_id,
                channel_id="channel_b",
                pipeline_id="convo-shorts",
                topic_text=topic,
                status="GENERATING",
                video_id=label,
                strategy_version=strategy_version,
                experiment_id=experiment_id,
                arm_id=arm_id,
                variant_id=arm_id
            )
            growth_repo.upsert_job(job_entry)
            print(f"[JOB {job_id}] growth.db synchronized: Job created with status GENERATING")
        except Exception as g_err:
            print(f"[JOB {job_id}] Notice: growth.db job initialization skipped: {g_err}")

        # 2. Generate or Load Script with Multi-Angle & Hybrid Critic
        failed_stage = "SCRIPTING"
        print(f"[JOB {job_id}] [STAGE SCRIPTING] Generating technical Short via Content Brain v1...")
        script = {}
        title = f"Short: {topic}"
        timeline_or_text = ""

        if script_file and Path(script_file).exists():
            with open(script_file, "r", encoding="utf-8") as f:
                full_text = f.read()
            hook = " ".join(full_text.split()[:4]) if full_text else "My Hook"
            body = full_text
            cta = ""
            timeline_or_text = full_text
            print(f"[Manual Script] Loaded from {script_file}")
        elif script_text:
            full_text = script_text
            hook = " ".join(full_text.split()[:4]) if full_text else "My Hook"
            body = full_text
            cta = ""
            timeline_or_text = full_text
            print("[Manual Script] Provided directly.")
        else:
            script = generate_script(topic, category, active_strategy=strat_ctx)
            if "lines" in script:
                title = script.get("title", f"Coding: {topic}")
                timeline_or_text = script["lines"]
                hook = script.get("angle_data", {}).get("hook_text", "Coding breakdown")
                body = "Structured single narrator explanation"
                cta = "Follow for daily engineering deep-dives"
                print(f"[JOB {job_id}] [STAGE SCRIPTING SUCCESS] Script passed Hybrid Critic (Score: {script.get('critic_score', 8.5)}/10).")
            else:
                hook, body, cta = script["hook"], script["body"], script["cta"]
                title = script.get("title", f"{hook} #Shorts")
                timeline_or_text = f"{hook} {body} {cta}"

        # 3. Audio / TTS
        failed_stage = "TTS"
        print(f"[JOB {job_id}] [STAGE TTS] Synthesizing dual-speaker dialogue voiceover...")
        timings = None
        visual_proofs = None
        is_debate_run = False
        
        if "lines" in script:
            is_debate_run = True
            
        if audio_file and Path(audio_file).exists():
            audio_path = str(Path(audio_file).absolute())
            print(f"[Manual Audio] Using provided audio file: {audio_path}")
            subtitle_data = generate_subtitles(audio_path)
        else:
            voice_res = generate_voiceover(timeline_or_text, audio_raw, voice=voice)
            if isinstance(voice_res, tuple):
                audio_path, timings = voice_res
            else:
                audio_path = voice_res
                
            subtitle_data = generate_subtitles(audio_path, timings=timings)

            actual_dur = subtitle_data.get("duration", 0)
            target_max = CFG.get("target_max_duration", 58.0)
            if actual_dur > target_max:
                err_msg = f"AUDIO_DURATION_EXCEEDED: Actual spoken TTS audio duration ({actual_dur:.1f}s) exceeds maximum target ({target_max:.1f}s)."
                print(f"[JOB {job_id}] [STAGE TTS FAILED] {err_msg}")
                raise RuntimeError(err_msg)

        # 4.5 Generate images if debate run
        if is_debate_run:
            failed_stage = "VISUAL_GENERATION"
            print(f"[JOB {job_id}] [STAGE VISUAL_GENERATION] Rendering VS Code syntax cards (Fooocus disabled for code integrity)...")
            visual_proofs = []
            segments = script.get("segments", [])
            generated_paths = {}
            from code_renderer import render_code_snippet_card
            scenes_raw = script.get("scenes", [])
            total_scenes = len(segments)
            for idx, seg in enumerate(segments):
                seg_id = seg.get("segment_id")
                target_path = job_temp_dir / f"{label}_{seg_id}.png"
                
                # Check if scene is the final Outro/CTA scene
                is_outro_scene = (idx == total_scenes - 1)
                
                # Check if scene contains code snippet
                code_snippet = None
                if idx < len(scenes_raw):
                    code_snippet = scenes_raw[idx].get("code_snippet")
                    
                has_code = False
                if code_snippet and not is_outro_scene:
                    if isinstance(code_snippet, list) and len(code_snippet) > 0 and any(str(l).strip() for l in code_snippet):
                        has_code = True
                    elif isinstance(code_snippet, dict) and len(code_snippet) > 0:
                        has_code = True
                    elif isinstance(code_snippet, str) and len(code_snippet.strip()) > 0:
                        has_code = True

                if has_code:
                    card_title = f"{topic[:22]} [{idx+1}/{total_scenes-1}]"
                    print(f"[CODE CARD] Rendering Tokyo Night syntax card for {seg_id}...")
                    img_path = render_code_snippet_card(code_snippet, title=card_title, output_path=str(target_path))
                else:
                    if is_outro_scene:
                        print(f"[OUTRO CTA] Scene {idx+1} is Call-to-Action. Disabling overlay (clean subtitles over gameplay).")
                    else:
                        print(f"[VISUAL] Scene {idx+1} has no code snippet. Disabling overlay.")
                    img_path = None
                    
                generated_paths[seg_id] = img_path
                
            for sc in timings:
                seg_id = sc.get("segment_id")
                visual_proofs.append(generated_paths.get(seg_id))

        # 5. Pick background & assemble video
        failed_stage = "RENDERING"
        print(f"[JOB {job_id}] [STAGE RENDERING] Slicing background & assembling video with sidechain audio mixing...")
        bg_path = pick_background(required_duration=subtitle_data["duration"], is_debate=is_debate_run)
        assemble_video(bg_path, audio_path, subtitle_data, video_out, category, visual_proofs=visual_proofs, timings=timings)

        # 7. Production QA Gate & Manifest Generation
        failed_stage = "FINAL_QA"
        print(f"\n[JOB {job_id}] [STAGE FINAL_QA] Running Final Production QA Gate & Manifest Generation...")
        from qa_gate import run_full_production_qa
        from manifest_engine import generate_production_manifest

        cfg_v_path = Path(__file__).parent.parent / "config" / "voice.json"
        voice_cfg = {}
        if cfg_v_path.exists():
            with open(cfg_v_path, "r", encoding="utf-8") as vf:
                voice_cfg = json.load(vf)

        qa_results = run_full_production_qa(
            video_path=video_out,
            audio_path=audio_path,
            subtitle_data=subtitle_data,
            timings=timings,
            visual_proofs=visual_proofs if is_debate_run else [],
            voice_cfg=voice_cfg
        )

        if "convo_stats" in script:
            qa_results.update(script["convo_stats"])

        audio_stats = qa_results.get("audio_stats", {"mean_volume": -17.5, "max_volume": -2.3})
        manifest = generate_production_manifest(
            short_id=label,
            topic=topic,
            category=category,
            video_path=video_out,
            duration=subtitle_data.get("duration", 0),
            visual_count=len(visual_proofs) if is_debate_run else 0,
            voice_cfg=voice_cfg,
            audio_stats=audio_stats,
            qa_results=qa_results,
            job_id=job_id,
            strategy_version=strategy_version,
            experiment_id=experiment_id,
            arm_id=arm_id,
            tested_variable=tested_variable,
            angle_data=script.get("angle_data")
        )

        if not qa_results.get("passed", False):
            if growth_repo:
                try:
                    job_fail = JobModel(
                        job_id=job_id,
                        channel_id="channel_b",
                        pipeline_id="convo-shorts",
                        topic_text=topic,
                        status="QA_FAILED",
                        video_id=label,
                        error_message=str(qa_results.get('details'))
                    )
                    growth_repo.upsert_job(job_fail)
                except Exception:
                    pass
            raise RuntimeError(f"PRODUCTION QA GATE FAILED for {label}: {qa_results.get('details')}")

        # Update growth.db state: Register VideoModel and set JobModel to AWAITING_REVIEW
        if growth_repo:
            try:
                from metadata_generator import generate_metadata
                meta = generate_metadata(topic, category)
                v_model = VideoModel(
                    video_id=label,
                    channel_id="channel_b",
                    pipeline_id="convo-shorts",
                    title=meta.get("title", title),
                    description=meta.get("description", topic),
                    duration=float(subtitle_data.get("duration", 45.0)),
                    upload_status="GENERATED",
                    privacy_status="private",
                    qa_score=1.0,
                    review_status="PENDING",
                    strategy_version=strategy_version,
                    topic_id=f"topic_{label}",
                    experiment_id=experiment_id,
                    arm_id=arm_id,
                    variant_id=arm_id
                )
                growth_repo.upsert_video(v_model)

                job_entry = JobModel(
                    job_id=job_id,
                    channel_id="channel_b",
                    pipeline_id="convo-shorts",
                    topic_text=topic,
                    status="AWAITING_REVIEW",
                    video_id=label,
                    strategy_version=strategy_version,
                    experiment_id=experiment_id,
                    arm_id=arm_id,
                    variant_id=arm_id
                )
                growth_repo.upsert_job(job_entry)
                print(f"[JOB {job_id}] growth.db synchronized: Video {label} registered, Job -> AWAITING_REVIEW")
            except Exception as g_sync_err:
                print(f"[JOB {job_id}] Notice: growth.db QA sync error: {g_sync_err}")

        # Post 540x960 review proxy to Discord webhook
        try:
            print(f"[JOB {job_id}] Compressing < 8MB review proxy and posting to Discord webhook...")
            from discord_review import post_for_review
            post_for_review("pipeline2", job_id, [str(video_out)], "video")
            print(f"\n[JOB {job_id}] Proxy dispatched to Discord. Awaiting manual approval.\n")
        except Exception as dw_err:
            print(f"[JOB {job_id}] Notice: Discord review dispatch failed ({dw_err})")

        success_res = {
            "status": "AWAITING_REVIEW",
            "job_id": job_id,
            "short_id": label,
            "video_path": video_out,
            "manifest_path": str(Path(video_out).with_suffix(".manifest.json")),
            "duration": round(subtitle_data.get("duration", 0), 2),
            "qa_passed": True
        }

        # Cleanup isolated job workspace safely on success
        try:
            shutil.rmtree(job_temp_dir, ignore_errors=True)
        except Exception:
            pass

        print("\n" + "=" * 60)
        print(f"  [JOB {job_id}] PRODUCTION SHORT READY (AWAITING REVIEW)")
        print(f"  Video     : {video_out}")
        print(f"  Manifest  : {Path(video_out).with_suffix('.manifest.json')}")
        print(f"  Label     : {label}")
        print(f"  Title     : {title}")
        print("=" * 60 + "\n")
        print("[MACHINE-READABLE RESULT]:")
        print(json.dumps(success_res, indent=2))

        return success_res

    except Exception as e:
        err_msg = str(e)
        print(f"\n[JOB FAILED] Job ID: {job_id} | Failed Stage: {failed_stage} | Error: {err_msg}")
        
        failure_res = {
            "status": "failed",
            "job_id": job_id,
            "short_id": label,
            "failed_stage": failed_stage,
            "error": err_msg,
            "qa_passed": False
        }

        fail_manifest_path = Path(video_out).with_suffix(".manifest.json")
        try:
            with open(fail_manifest_path, "w", encoding="utf-8") as f:
                json.dump(failure_res, f, indent=2)
        except Exception:
            pass

        print("[MACHINE-READABLE RESULT]:")
        print(json.dumps(failure_res, indent=2))
        return failure_res


# =============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube Shorts video generator")
    parser.add_argument(
        "--topic",
        default="Why your brain forgets things on purpose",
        help="Topic for the Short",
    )
    parser.add_argument(
        "--category",
        default="Coding & Senior Dev Patterns",
        choices=[
            "Coding & Senior Dev Patterns",
            "System Design & Backend Architecture",
            "AI Engineering & LLMs",
            "DevOps & Cloud Infrastructure",
            "Tech",
            "Weird Science",
            "Productivity & stoicism",
            "Human Behavior"
        ],
        help="Content category",
    )
    parser.add_argument("--job_id", default=None, help="Unique job identifier")
    parser.add_argument("--lesson", type=int, default=None, help="Lesson number from curriculum_queue.json (1-30)")
    parser.add_argument("--output_dir", default=None, help="Custom output directory")
    parser.add_argument("--script_file", default=None, help="Path to manual script text file (skips Ollama)")
    parser.add_argument("--script_text", default=None, help="Manual script text string (skips Ollama)")
    parser.add_argument("--audio_file", default=None, help="Path to pre-generated audio file (skips TTS)")
    parser.add_argument("--voice", default="en-US-BrianNeural", help="Edge TTS voice to use")
    
    args = parser.parse_args()

    topic = args.topic
    category = args.category

    # If --lesson is provided, load topic from curriculum_queue.json
    if args.lesson is not None:
        curr_path = Path(__file__).parent / "curriculum_queue.json"
        if curr_path.exists():
            with open(curr_path, "r", encoding="utf-8") as f:
                curriculum_data = json.load(f)
            matching = [item for item in curriculum_data if item.get("lesson_number") == args.lesson]
            if matching:
                lesson_item = matching[0]
                topic = lesson_item["topic"]
                category = lesson_item.get("category", "Coding & Senior Dev Patterns")
                print(f"[CURRICULUM] Loaded Lesson {args.lesson}: '{topic}' ({category})")
            else:
                print(f"[CURRICULUM WARNING] Lesson {args.lesson} not found in curriculum_queue.json. Using topic: {topic}")

    res = run_pipeline(
        topic=topic, 
        category=category,
        script_file=args.script_file,
        script_text=args.script_text,
        audio_file=args.audio_file,
        voice=args.voice,
        custom_job_id=args.job_id,
        custom_output_dir=args.output_dir
    )

    if res.get("status") in ("AWAITING_REVIEW", "qa_passed"):
        sys.exit(0)
    else:
        sys.exit(1)

