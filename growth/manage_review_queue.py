# -*- coding: utf-8 -*-
"""
manage_review_queue.py
----------------------
CLI management tool for videos in AWAITING_REVIEW queue across Channel A and Channel B.
Allows batch-reviewing, approving, scheduling at 1 Short/day cadence, and re-rendering.
"""

import sys
import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime, timedelta

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from growth.db.database import get_db

def list_awaiting_review():
    """Lists all videos currently in AWAITING_REVIEW status."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT job_id, channel_id, pipeline_id, video_id, topic_text, created_at, status
            FROM jobs
            WHERE status = 'AWAITING_REVIEW'
            ORDER BY channel_id, created_at ASC;
        """)
        jobs = cursor.fetchall()

    if not jobs:
        print("\n[Queue] No jobs currently in AWAITING_REVIEW.\n")
        return []

    print("\n" + "=" * 95)
    print(f"  AWAITING REVIEW QUEUE ({len(jobs)} items)")
    print("=" * 95)
    print(f"{'#':<3} | {'Channel':<10} | {'Video ID':<26} | {'Created At':<19} | {'Topic'}")
    print("-" * 95)
    for idx, j in enumerate(jobs, 1):
        ch = j["channel_id"] or ("channel_a" if "alt" in (j["pipeline_id"] or "") else "channel_b")
        print(f"{idx:<3} | {ch:<10} | {j['video_id'][:26]:<26} | {j['created_at'][:19]:<19} | {j['topic_text']}")
    print("=" * 95 + "\n")
    return jobs

def approve_jobs(job_ids=None, approve_all=False):
    """Marks specified or all AWAITING_REVIEW jobs as APPROVED."""
    with get_db() as conn:
        cursor = conn.cursor()
        if approve_all:
            cursor.execute("UPDATE jobs SET status = 'APPROVED', updated_at = CURRENT_TIMESTAMP WHERE status = 'AWAITING_REVIEW';")
            count = cursor.rowcount
            print(f"[Queue] Successfully approved all {count} videos in AWAITING_REVIEW.")
        elif job_ids:
            placeholders = ",".join("?" for _ in job_ids)
            cursor.execute(f"UPDATE jobs SET status = 'APPROVED', updated_at = CURRENT_TIMESTAMP WHERE job_id IN ({placeholders}) OR video_id IN ({placeholders});", job_ids + job_ids)
            count = cursor.rowcount
            print(f"[Queue] Successfully approved {count} specified videos.")

def schedule_approved(cadence_per_day: int = 1, start_date: str = None):
    """
    Schedules APPROVED (or AWAITING_REVIEW with auto-approve) videos at 1 Short/day per channel.
    """
    base_date = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else (datetime.utcnow().date() + timedelta(days=1))
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT job_id, channel_id, pipeline_id, video_id, topic_text
            FROM jobs
            WHERE status = 'APPROVED'
            ORDER BY channel_id, created_at ASC;
        """)
        jobs = cursor.fetchall()

    if not jobs:
        print("[Queue] No jobs eligible for scheduling.")
        return

    channel_queues = {}
    for j in jobs:
        ch = j["channel_id"] or ("channel_a" if "alt" in (j["pipeline_id"] or "") else "channel_b")
        channel_queues.setdefault(ch, []).append(j)

    schedule_plan = []
    with get_db() as conn:
        cursor = conn.cursor()
        for ch, ch_jobs in channel_queues.items():
            curr_date = base_date
            for idx, job in enumerate(ch_jobs):
                publish_time = f"{curr_date.isoformat()}T17:00:00Z"
                cursor.execute("""
                    UPDATE jobs 
                    SET status = 'SCHEDULED', updated_at = CURRENT_TIMESTAMP 
                    WHERE job_id = ?;
                """, (job["job_id"],))
                
                # Update corresponding video record if present
                cursor.execute("""
                    UPDATE videos 
                    SET upload_status = 'SCHEDULED', publish_timestamp = ? 
                    WHERE video_id = ?;
                """, (publish_time, job["video_id"]))
                
                schedule_plan.append({
                    "channel": ch,
                    "job_id": job["job_id"],
                    "video_id": job["video_id"],
                    "topic": job["topic_text"],
                    "scheduled_date": publish_time
                })
                curr_date += timedelta(days=1)

    print("\n" + "=" * 90)
    print(f"  AUTOMATED 1 SHORT/DAY SCHEDULING PLAN ({len(schedule_plan)} scheduled)")
    print("=" * 90)
    print(f"{'Channel':<11} | {'Publish Date':<20} | {'Video ID':<26} | {'Topic'}")
    print("-" * 90)
    for item in schedule_plan:
        print(f"{item['channel']:<11} | {item['scheduled_date'][:19]:<20} | {item['video_id'][:26]:<26} | {item['topic']}")
    print("=" * 90 + "\n")

def main():
    parser = argparse.ArgumentParser(description="YouTube Automations Review Queue Management CLI")
    parser.add_argument("--list", action="store_true", help="List all jobs in AWAITING_REVIEW")
    parser.add_argument("--approve-all", action="store_true", help="Batch approve all awaiting review jobs")
    parser.add_argument("--approve", nargs="+", help="Approve specific job IDs")
    parser.add_argument("--schedule", action="store_true", help="Schedule approved videos at 1 Short/day per channel")
    parser.add_argument("--start-date", help="Start date for scheduling (YYYY-MM-DD)")
    args = parser.parse_args()

    if args.list:
        list_awaiting_review()
    elif args.approve_all:
        approve_jobs(approve_all=True)
    elif args.approve:
        approve_jobs(job_ids=args.approve)
    elif args.schedule:
        schedule_approved(cadence_per_day=1, start_date=args.start_date)
    else:
        list_awaiting_review()

if __name__ == "__main__":
    main()
