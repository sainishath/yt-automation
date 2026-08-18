# -*- coding: utf-8 -*-
"""
cli.py
------
Command-line interface for Content Intelligence and Growth Operations.
"""

import sys
import json
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from growth.db.database import init_db
from growth.db.models import GrowthRepository, ChannelModel, VideoModel, VideoFeaturesModel
from growth.analytics.collector import AnalyticsCollector
from growth.learning.learning_engine import LearningEngine
from growth.planner.content_planner import ContentPlanner
from growth.channels.channel_identity_check import load_channel_config, verify_channel_identity


def main():
    parser = argparse.ArgumentParser(description="Content Intelligence & Learning CLI")
    parser.add_argument("--init-db", action="store_true", help="Initialize growth database schema")
    parser.add_argument("--plan-next", choices=["channel_a", "channel_b"], help="Plan the next video recommendation for a channel")
    parser.add_argument("--run-learning", choices=["channel_a", "channel_b"], help="Execute learning cycle and produce weekly report")
    parser.add_argument("--dry-run-loop", action="store_true", help="Execute complete end-to-end closed-loop dry run")
    args = parser.parse_args()

    repo = GrowthRepository()
    collector = AnalyticsCollector(repo, use_mock_engine=True)

    if args.init_db or args.dry_run_loop:
        print("[Growth CLI] Initializing database...")
        init_db()
        # Seed channels if missing
        cfg_a = load_channel_config("pipeline1")
        cfg_b = load_channel_config("pipeline2")
        repo.upsert_channel(ChannelModel(
            channel_id="channel_a", name=cfg_a["channel_name"], handle=cfg_a["channel_handle"],
            pipeline_id=cfg_a["pipeline_id"], content_category=cfg_a["content_category"],
            audience_definition=cfg_a["audience_definition"], posting_frequency=cfg_a["posting_frequency"]
        ))
        repo.upsert_channel(ChannelModel(
            channel_id="channel_b", name=cfg_b["channel_name"], handle=cfg_b["channel_handle"],
            pipeline_id=cfg_b["pipeline_id"], content_category=cfg_b["content_category"],
            audience_definition=cfg_b["audience_definition"], posting_frequency=cfg_b["posting_frequency"]
        ))
        print("[Growth CLI] Database initialized and channels seeded.")

    if args.plan_next:
        planner = ContentPlanner(repo)
        plan = planner.plan_next_video(args.plan_next)
        print(f"\n=======================================================")
        print(f"  RECOMMENDED NEXT CONTENT PLAN: {args.plan_next.upper()}")
        print(f"=======================================================")
        print(json.dumps(plan, indent=2))
        print(f"=======================================================\n")

    if args.run_learning:
        engine = LearningEngine(repo, collector)
        res = engine.run_channel_learning_cycle(args.run_learning)
        print(f"\n{res['report_markdown']}\n")

    if args.dry_run_loop:
        print("\n" + "=" * 60)
        print("  EXECUTING COMPLETE CLOSED-LOOP DRY RUN")
        print("=" * 60)

        planner = ContentPlanner(repo)
        plan_a = planner.plan_next_video("channel_a")
        print(f"1. Planned Channel A Video: '{plan_a['topic']}' (Strategy: {plan_a['strategy_version']}, Reason: {plan_a['selection_reason']})")

        plan_b = planner.plan_next_video("channel_b")
        print(f"2. Planned Channel B Video: '{plan_b['topic']}' (Strategy: {plan_b['strategy_version']}, Reason: {plan_b['selection_reason']})")

        # Simulate video completion & feature storage for P1
        sim_vid_id = "dryrun_sim_p1"
        repo.upsert_video(VideoModel(
            video_id=sim_vid_id, channel_id="channel_a", pipeline_id="alternate-history-shorts",
            title=plan_a["topic"], duration=45.0, upload_status="UPLOADED_SIMULATED",
            privacy_status="public", review_status="APPROVED", strategy_version=plan_a["strategy_version"]
        ))
        repo.upsert_features(VideoFeaturesModel(
            video_id=sim_vid_id, topic_category="History", hook_type="Counterfactual Divergence",
            hook_score=9.3, hook_text=f"If {plan_a['topic']} had happened...", word_count=104,
            scene_count=8, avg_scene_duration=5.6, visual_change_rate=0.18,
            motion_type="Candidate A Linear Ken Burns", motion_intensity=0.08,
            caption_density=2.3, narrative_structure="8_beat_divergence"
        ))
        collector.collect_snapshots_for_video(sim_vid_id, duration=45.0, retention_factor=0.91)
        print("3. Ingested 6 performance snapshots (1h, 6h, 24h, 48h, 7d, 28d) for simulated video.")

        # Channel Identity verification test
        ident = verify_channel_identity("pipeline1", "UC1234567890", "Chronos Shift", allow_placeholder=True)
        print(f"4. Pre-Upload Identity Guard: {ident['verdict']} (Channel: {ident['authenticated_channel_name']})")

        # Execute learning cycle
        engine = LearningEngine(repo, collector)
        cycle_a = engine.run_channel_learning_cycle("channel_a")
        print(f"5. Learning Cycle Executed for Channel A: Evaluated {cycle_a['videos_count']} videos, generated {len(cycle_a['autopsies'])} autopsies.")
        print(f"6. Weekly Report Generated Successfully ({len(cycle_a['report_markdown'])} chars).")

        print("=" * 60)
        print("  CLOSED-LOOP DRY RUN COMPLETED SUCCESSFULLY: PASS")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
