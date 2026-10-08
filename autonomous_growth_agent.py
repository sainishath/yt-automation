# -*- coding: utf-8 -*-
"""
autonomous_growth_agent.py
--------------------------
Autonomous, Local-First YouTube Shorts Generation, Automated Publishing,
and Closed-Loop Empirical Growth Engine.

Architecture:
1. Strategy Context: Ingests active winning rules & hook constraints from Content Brain memory.
2. Video Generation: Produces 1080x1920 Shorts (Pipeline 1: History, Pipeline 2: Coding).
3. QA Validation: Strictly verifies audio, duration, canvas sizing, and subtitle alignment.
4. Autonomous Upload: Publishes to live YouTube channel via official Data API v3.
5. Analytics Collection: Queries live views, retention, and engagement metrics.
6. Empirical Evolution: Runs LearningEngine to detect hook failures vs winners,
   mutating strategies (v1.0 -> v1.1) to continuously optimize view counts.
"""

import os
import sys
import json
import time
import random
import argparse
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Ensure root repository directory is on sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Load .env configuration
load_dotenv(ROOT_DIR / ".env")
os.environ["PYTHONIOENCODING"] = "utf-8"
if "ALLOW_FOOOCUS_FALLBACK" not in os.environ:
    os.environ["ALLOW_FOOOCUS_FALLBACK"] = "1"

# Configure logging
LOG_FILE = ROOT_DIR / "autonomous_growth.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [GrowthAgent] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("GrowthAgent")

# Growth Database & Memory components
from growth.db.database import get_db, DEFAULT_DB_PATH
from growth.db.models import GrowthRepository, JobModel, VideoModel
from growth.strategy.strategy_manager import StrategyManager
from growth.analytics.collector import AnalyticsCollector
from growth.learning.learning_engine import LearningEngine

STATE_FILE = ROOT_DIR / "growth" / "schedule_state.json"
CURRICULUM_FILE = ROOT_DIR / "convo-shorts" / "yt-automation-engine" / "curriculum_queue.json"

FACTUAL_HISTORY_POOL = [
    "The Fall of Constantinople 1453",
    "The Library of Alexandria",
    "The Apollo 11 Moon Landing",
    "The Construction of the Roman Colosseum",
    "The Silk Road Trade Network",
    "The Invention of the Printing Press",
    "The Discovery of Penicillin",
    "The Battle of Midway 1942",
    "The Code of Hammurabi",
    "The Wright Brothers First Flight 1903",
    "The Building of the Panama Canal",
    "The Black Death of 1347",
    "The Manhattan Project",
    "The Rosetta Stone Decipherment",
    "The Renaissance in Florence",
    "The Battle of Waterloo 1815",
    "The First Submarine: The Turtle 1776",
    "The Voyager Golden Record",
    "The Sinking of the Titanic 1912",
    "The California Gold Rush 1849"
]


def load_state() -> dict:
    """Loads schedule state tracking current lesson and completed topics."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading schedule state: {e}")
    return {
        "current_lesson": 2,
        "completed_history_topics": [],
        "production_log": []
    }


def save_state(state: dict):
    """Saves updated schedule state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def sync_analytics_and_learn(repo: GrowthRepository, channel_id: str) -> dict:
    """
    Syncs live YouTube analytics for published videos and executes the closed-loop learning cycle.
    Evolves channel strategy if experimental hypotheses are proven with statistical significance.
    """
    logger.info(f"=== [STEP: ANALYTICS & LEARNING] Syncing performance for {channel_id} ===")
    
    # 1. Fetch live analytics snapshots
    try:
        from growth.analytics.fetch_analytics import fetch_due_snapshots
        snap_res = fetch_due_snapshots(repo=repo, dry_run=False)
        logger.info(f"Snapshots collected: {snap_res.get('collected_count', 0)}, skipped: {snap_res.get('skipped_count', 0)}")
    except Exception as e:
        logger.warning(f"Analytics ingestion notice: {e}")

    # 2. Run Learning Cycle
    try:
        collector = AnalyticsCollector(repo, use_mock_engine=False)
        engine = LearningEngine(repo, collector)
        learning_res = engine.run_channel_learning_cycle(channel_id)
        
        promoted = learning_res.get("promoted_strategy")
        if promoted:
            logger.info(f"*** STRATEGY MUTATION PROMOTED *** Channel {channel_id} evolved to: {promoted}")
        else:
            logger.info(f"Learning cycle complete. Active strategy maintained.")
        return learning_res
    except Exception as e:
        logger.warning(f"Learning engine notice: {e}")
        return {"status": "skipped", "error": str(e)}


def run_channel_b_cycle(
    lesson_override: int = None,
    privacy: str = "public",
    dry_run: bool = False
) -> dict:
    """
    Executes 1 complete cycle for Channel B (Debate Protocol / Coding):
    1. Reads active strategy rules from memory.
    2. Generates video via convo-shorts engine.
    3. Runs 16/16 QA validation gate.
    4. Automatically publishes to YouTube.
    5. Syncs growth.db and updates curriculum pointer.
    """
    repo = GrowthRepository(DEFAULT_DB_PATH)
    strat_mgr = StrategyManager()
    active_strat = strat_mgr.get_active_strategy_context("channel_b")
    strat_ver = active_strat.get("strategy_version", "v1.0")

    state = load_state()
    lesson_num = lesson_override if lesson_override is not None else state.get("current_lesson", 2)

    logger.info("=" * 65)
    logger.info(f"  [CHANNEL B] Launching Coding Short: Lesson {lesson_num}")
    logger.info(f"  Active Strategy: {strat_ver} | Learned Rules: {len(active_strat.get('learned_rules', []))}")
    logger.info("=" * 65)

    # 1. Identify Topic from Curriculum Queue
    topic = f"Python Coding: Lesson {lesson_num}"
    category = "Coding & Senior Dev Patterns"
    if CURRICULUM_FILE.exists():
        try:
            with open(CURRICULUM_FILE, "r", encoding="utf-8") as cf:
                c_data = json.load(cf)
            match = [item for item in c_data if item.get("lesson_number") == lesson_num]
            if match:
                topic = match[0].get("topic", topic)
                category = match[0].get("category", category)
        except Exception as e:
            logger.warning(f"Curriculum load warning: {e}")

    logger.info(f"Lesson Topic: '{topic}' ({category})")

    # 2. Run Pipeline 2 Generation
    engine_dir = ROOT_DIR / "convo-shorts" / "yt-automation-engine"
    if str(engine_dir) not in sys.path:
        sys.path.insert(0, str(engine_dir))
    
    from main import run_pipeline as run_pipeline_2

    job_id = f"job_auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}_L{lesson_num:03d}"
    res = run_pipeline_2(
        topic=topic,
        category=category,
        custom_job_id=job_id
    )

    if not res.get("qa_passed", False):
        err = f"Pipeline 2 QA Gate failed for Lesson {lesson_num}: {res.get('error')}"
        logger.error(err)
        return {"success": False, "error": err}

    video_path = res.get("video_path")
    short_id = res.get("short_id")
    duration = res.get("duration", 45.0)

    logger.info(f"Video Generated Successfully: {short_id} ({duration}s) at {video_path}")

    # 3. Autonomous YouTube Upload
    yt_id = None
    yt_url = None
    if not dry_run:
        logger.info(f"Uploading {short_id} to YouTube Channel B (Privacy: {privacy})...")
        from uploader import upload_to_youtube as p2_upload
        from metadata_generator import generate_metadata

        meta = generate_metadata(topic, category)
        title = meta.get("title", f"Short: {topic}")
        desc = meta.get("description", topic)
        tags = meta.get("tags", ["#shorts", "#coding", "#python"])

        up_res = p2_upload(
            video_path=video_path,
            title=title,
            description=desc,
            hashtags=tags,
            privacy_status=privacy
        )

        if up_res.get("status") == "success":
            yt_id = up_res.get("video_id")
            yt_url = up_res.get("url")
            logger.info(f"*** YOUTUBE UPLOAD SUCCESS *** ID: {yt_id} | URL: {yt_url}")

            # Register upload in growth.db
            from growth.experiments.sample_tracker import ExperimentSampleTracker
            tracker = ExperimentSampleTracker(repo=repo)
            tracker.register_real_upload(
                video_id=short_id,
                youtube_video_id=yt_id,
                youtube_url=yt_url,
                privacy=privacy
            )

            # Mark job as PUBLISHED
            with get_db(repo.db_path) as conn:
                conn.execute(
                    "UPDATE jobs SET status = 'PUBLISHED', updated_at = CURRENT_TIMESTAMP WHERE job_id = ?",
                    (job_id,)
                )
        else:
            logger.error(f"YouTube upload failed: {up_res.get('error')}")
            return {"success": False, "error": up_res.get("error")}
    else:
        logger.info(f"[DRY-RUN] Video staged locally at {video_path}. Upload skipped.")

    # 4. Advance Curriculum Pointer & Log Success
    state["current_lesson"] = lesson_num + 1
    state["production_log"].append({
        "pipeline": "pipeline_2",
        "lesson": lesson_num,
        "topic": topic,
        "short_id": short_id,
        "youtube_video_id": yt_id,
        "timestamp": datetime.now().isoformat(),
        "success": True
    })
    save_state(state)

    # 5. Run Closed-Loop Learning
    sync_analytics_and_learn(repo, "channel_b")

    return {
        "success": True,
        "channel": "channel_b",
        "lesson": lesson_num,
        "topic": topic,
        "video_path": video_path,
        "youtube_video_id": yt_id,
        "youtube_url": yt_url,
        "duration": duration,
        "strategy_version": strat_ver
    }


def run_channel_a_cycle(
    topic_override: str = None,
    privacy: str = "public",
    dry_run: bool = False
) -> dict:
    """
    Executes 1 complete cycle for Channel A (Chronos Shift / History):
    1. Reads active strategy rules from memory.
    2. Generates video via alternate-history-shorts engine.
    3. Runs 17/17 QA validation gate.
    4. Automatically publishes to YouTube.
    5. Syncs growth.db and updates topic pool.
    """
    repo = GrowthRepository(DEFAULT_DB_PATH)
    strat_mgr = StrategyManager()
    active_strat = strat_mgr.get_active_strategy_context("channel_a")
    strat_ver = active_strat.get("strategy_version", "v1.0")

    state = load_state()

    # 1. Select Topic
    if topic_override:
        topic = topic_override
    else:
        completed = state.get("completed_history_topics", [])
        avail = [t for t in FACTUAL_HISTORY_POOL if t not in completed]
        if not avail:
            avail = FACTUAL_HISTORY_POOL[:]
        topic = random.choice(avail)

    logger.info("=" * 65)
    logger.info(f"  [CHANNEL A] Launching History Short: '{topic}'")
    logger.info(f"  Active Strategy: {strat_ver} | Learned Rules: {len(active_strat.get('learned_rules', []))}")
    logger.info("=" * 65)

    # 2. Run Pipeline 1 Generation
    p1_script_dir = ROOT_DIR / "alternate-history-shorts" / "scripts"
    if str(p1_script_dir) not in sys.path:
        sys.path.insert(0, str(p1_script_dir))

    from pipeline_runner import run_pipeline1

    video_id = f"video_{int(time.time())}_{random.randint(1000, 9999):04x}"
    p1_res = run_pipeline1(
        topic=topic,
        video_id=video_id,
        allow_fallback=True,
        factual=True
    )

    if not p1_res.get("qa_passed", False):
        err = f"Pipeline 1 QA Gate failed for topic '{topic}'"
        logger.error(err)
        return {"success": False, "error": err}

    final_mp4 = p1_res.get("final_mp4")
    duration = p1_res.get("duration", 45.0)

    logger.info(f"Video Generated Successfully: {video_id} ({duration}s) at {final_mp4}")

    # 3. Autonomous YouTube Upload
    yt_id = None
    yt_url = None
    if not dry_run:
        logger.info(f"Uploading {video_id} to YouTube Channel A (Privacy: {privacy})...")
        from upload_video import upload_video as p1_upload

        title = f"What If {topic}?"
        desc = f"Exploring history: {topic}\n\n#Shorts #History #Documentary"
        tags = ["#shorts", "#history", "#whatif", "#documentary"]

        meta_p = Path(final_mp4).parent.parent / "metadata.json"
        if meta_p.exists():
            try:
                with open(meta_p, "r", encoding="utf-8") as mf:
                    m = json.load(mf)
                    title = m.get("title", title)
                    desc = m.get("description", desc)
                    tags = m.get("tags", tags)
            except Exception:
                pass

        up_res = p1_upload(
            video_id=video_id,
            final_mp4=Path(final_mp4),
            title=title,
            description=desc,
            tags=tags,
            privacy=privacy
        )

        yt_id = up_res.get("youtube_video_id")
        yt_url = up_res.get("public_url")
        logger.info(f"*** YOUTUBE UPLOAD SUCCESS *** ID: {yt_id} | URL: {yt_url}")

        # Register upload in growth.db
        from growth.experiments.sample_tracker import ExperimentSampleTracker
        tracker = ExperimentSampleTracker(repo=repo)
        tracker.register_real_upload(
            video_id=video_id,
            youtube_video_id=yt_id,
            youtube_url=yt_url,
            privacy=privacy
        )
    else:
        logger.info(f"[DRY-RUN] Video staged locally at {final_mp4}. Upload skipped.")

    # 4. Advance State & Topic Pool
    if topic not in state["completed_history_topics"]:
        state["completed_history_topics"].append(topic)
    state["production_log"].append({
        "pipeline": "pipeline_1",
        "topic": topic,
        "video_id": video_id,
        "youtube_video_id": yt_id,
        "timestamp": datetime.now().isoformat(),
        "success": True
    })
    save_state(state)

    # 5. Run Closed-Loop Learning
    sync_analytics_and_learn(repo, "channel_a")

    return {
        "success": True,
        "channel": "channel_a",
        "topic": topic,
        "video_path": str(final_mp4),
        "youtube_video_id": yt_id,
        "youtube_url": yt_url,
        "duration": duration,
        "strategy_version": strat_ver
    }


def main():
    parser = argparse.ArgumentParser(description="Autonomous Growth Agent for YouTube Shorts")
    parser.add_argument("--channel", choices=["channel_a", "channel_b", "both"], default="channel_b",
                        help="Target YouTube channel (channel_a: History, channel_b: Coding)")
    parser.add_argument("--lesson", type=int, default=None, help="Specific lesson number for channel_b")
    parser.add_argument("--topic", type=str, default=None, help="Specific topic override")
    parser.add_argument("--privacy", choices=["public", "unlisted", "private"], default="public",
                        help="YouTube upload privacy visibility")
    parser.add_argument("--dry-run", action="store_true", help="Render & test locally without live YouTube upload")
    parser.add_argument("--once", action="store_true", help="Execute 1 full cycle and exit")
    parser.add_argument("--quota", type=int, default=1, help="Number of videos to generate in this run")
    parser.add_argument("--daemon", action="store_true", help="Run indefinitely on a recurring schedule")
    parser.add_argument("--interval", type=float, default=12.0, help="Interval in hours between daemon runs")
    parser.add_argument("--learn-only", action="store_true", help="Run analytics sync and learning engine only")

    args = parser.parse_args()

    repo = GrowthRepository(DEFAULT_DB_PATH)

    # Mode: Learn Only
    if args.learn_only:
        logger.info("Executing Learn-Only mode across channels...")
        if args.channel in ["channel_a", "both"]:
            sync_analytics_and_learn(repo, "channel_a")
        if args.channel in ["channel_b", "both"]:
            sync_analytics_and_learn(repo, "channel_b")
        logger.info("Learn-Only execution complete.")
        return

    iteration = 0
    while True:
        iteration += 1
        logger.info(f"\n{'#'*65}\n  STARTING PRODUCTION RUN (Iteration {iteration})\n{'#'*65}")

        for q in range(args.quota):
            if args.quota > 1:
                logger.info(f"\n--- Processing Video {q+1}/{args.quota} ---")

            if args.channel in ["channel_b", "both"]:
                res_b = run_channel_b_cycle(
                    lesson_override=args.lesson,
                    privacy=args.privacy,
                    dry_run=args.dry_run
                )
                print("\n[RESULT CHANNEL B]:", json.dumps(res_b, indent=2))

            if args.channel in ["channel_a", "both"]:
                res_a = run_channel_a_cycle(
                    topic_override=args.topic,
                    privacy=args.privacy,
                    dry_run=args.dry_run
                )
                print("\n[RESULT CHANNEL A]:", json.dumps(res_a, indent=2))

        if args.once or not args.daemon:
            logger.info("Single execution run completed successfully.")
            break

        sleep_secs = int(args.interval * 3600)
        logger.info(f"Sleeping for {args.interval} hours ({sleep_secs}s) until next autonomous cycle...")
        time.sleep(sleep_secs)


if __name__ == "__main__":
    main()
