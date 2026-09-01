# -*- coding: utf-8 -*-
"""
daily_scheduler.py
------------------
Automates daily video production quotas for Channel A (Chronos Shift / History)
and Channel B (Debate Protocol / Coding Curriculum).

Tracks:
1. Current lesson pointer for serialized coding curriculum (curriculum_queue.json).
2. History topic pool to ensure factual diversity.
3. Synchronous execution with error logging and status reporting.
"""

import sys
import json
import random
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

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
    """Loads state tracking current lesson and completed topics."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "current_lesson": 2,
        "completed_history_topics": [],
        "production_log": []
    }


def save_state(state: dict):
    """Saves updated state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def run_pipeline_1(topic: str) -> bool:
    """Executes Pipeline 1 for factual history documentary Short."""
    print(f"\n{'='*60}")
    print(f"  [PIPELINE 1] Launching Factual History Short: '{topic}'")
    print(f"{'='*60}")
    
    script_path = ROOT_DIR / "alternate-history-shorts" / "scripts" / "pipeline_runner.py"
    cmd = [
        sys.executable,
        str(script_path),
        "--topic", topic,
        "--factual"
    ]
    
    env = dict(sys.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    
    res = subprocess.run(cmd, cwd=str(ROOT_DIR), env=env)
    return res.returncode == 0


def run_pipeline_2(lesson_num: int) -> bool:
    """Executes Pipeline 2 for sequential coding curriculum Short."""
    print(f"\n{'='*60}")
    print(f"  [PIPELINE 2] Launching Coding Curriculum Short: Lesson {lesson_num}")
    print(f"{'='*60}")
    
    script_path = ROOT_DIR / "convo-shorts" / "yt-automation-engine" / "main.py"
    cmd = [
        sys.executable,
        str(script_path),
        "--lesson", str(lesson_num)
    ]
    
    env = dict(sys.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    
    res = subprocess.run(cmd, cwd=str(ROOT_DIR), env=env)
    return res.returncode == 0


def run_day_1_batch():
    """Generates 3 factual history videos and Lessons 2, 3, 4."""
    print("\n" + "#"*60)
    print("  LAUNCHING DAY 1 PRODUCTION BATCH (6 VIDEOS TOTAL)")
    print("#"*60 + "\n")
    
    history_day_1 = [
        "The Battle of Stalingrad",
        "The Industrial Revolution",
        "Ancient Egypt: The Great Pyramid"
    ]
    
    coding_day_1 = [2, 3, 4]
    
    state = load_state()
    
    # 1. Run Pipeline 1 Batch
    for topic in history_day_1:
        success = run_pipeline_1(topic)
        state["production_log"].append({
            "pipeline": "pipeline_1",
            "topic": topic,
            "success": success
        })
        if success and topic not in state["completed_history_topics"]:
            state["completed_history_topics"].append(topic)
        save_state(state)
        
    # 2. Run Pipeline 2 Batch
    for lesson in coding_day_1:
        success = run_pipeline_2(lesson)
        state["production_log"].append({
            "pipeline": "pipeline_2",
            "lesson": lesson,
            "success": success
        })
        if success:
            state["current_lesson"] = max(state["current_lesson"], lesson + 1)
        save_state(state)
        
    print("\n" + "#"*60)
    print("  DAY 1 PRODUCTION BATCH COMPLETE — ALL PROXIES POSTED TO DISCORD")
    print("#"*60 + "\n")


def run_daily_quota(num_history: int = 2, num_coding: int = 2):
    """Generates standard daily quota (2 history + 2 coding lessons)."""
    print("\n" + "#"*60)
    print(f"  RUNNING DAILY PRODUCTION QUOTA ({num_history} History + {num_coding} Coding)")
    print("#"*60 + "\n")
    
    state = load_state()
    
    # 1. Pick unused history topics
    available_history = [t for t in FACTUAL_HISTORY_POOL if t not in state["completed_history_topics"]]
    if len(available_history) < num_history:
        available_history = FACTUAL_HISTORY_POOL[:]
        
    selected_history = random.sample(available_history, num_history)
    for topic in selected_history:
        success = run_pipeline_1(topic)
        state["production_log"].append({
            "pipeline": "pipeline_1",
            "topic": topic,
            "success": success
        })
        if success:
            state["completed_history_topics"].append(topic)
        save_state(state)
        
    # 2. Run sequential coding lessons
    current_lesson = state.get("current_lesson", 2)
    for i in range(num_coding):
        lesson_to_run = current_lesson + i
        success = run_pipeline_2(lesson_to_run)
        state["production_log"].append({
            "pipeline": "pipeline_2",
            "lesson": lesson_to_run,
            "success": success
        })
        if success:
            state["current_lesson"] = lesson_to_run + 1
        save_state(state)
        
    print("\n" + "#"*60)
    print("  DAILY QUOTA COMPLETE — ALL PROXIES POSTED TO DISCORD")
    print("#"*60 + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--day-1":
        run_day_1_batch()
    elif len(sys.argv) > 1 and sys.argv[1] == "--daily-quota":
        run_daily_quota()
    else:
        print("Usage: python daily_scheduler.py [--day-1 | --daily-quota]")
