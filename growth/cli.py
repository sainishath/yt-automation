# -*- coding: utf-8 -*-
"""
cli.py
------
Command-line interface for Content Intelligence and Growth Operations.
Supports initialization, planning, learning, snapshot collection, and observability dashboard.
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
from growth.analytics.snapshot_scheduler import SnapshotScheduler
from growth.learning.learning_engine import LearningEngine
from growth.planner.content_planner import ContentPlanner
from growth.channels.channel_identity_check import load_channel_config, verify_channel_identity


def display_dashboard(repo: GrowthRepository):
    """Renders a rich terminal dashboard with channel metrics, active experiments, and next queue."""
    vids_a = repo.list_videos_by_channel("channel_a")
    vids_b = repo.list_videos_by_channel("channel_b")

    print("\n" + "╔" + "═" * 68 + "╗")
    print("║        📊 YOUTUBE CONTENT INTELLIGENCE DASHBOARD                  ║")
    print("╚" + "═" * 68 + "╝")

    print("\n┌── 🏛️ CHANNEL A: Chronos Shift (Alternate History) " + "─" * 20 + "┐")
    print(f"│  • Published Videos: {len(vids_a):<4} | Active Strategy: v1.0 | Frequency: 3-4/wk │")
    if vids_a:
        top_v = vids_a[0]
        print(f"│  • Latest Video: {top_v['title'][:48]:<48} │")
    print("└" + "─" * 68 + "┘")

    print("\n┌── 🎙️ CHANNEL B: Debate Protocol (Conversational Debates) " + "─" * 15 + "┐")
    print(f"│  • Published Videos: {len(vids_b):<4} | Active Strategy: v1.0 | Frequency: 5-7/wk │")
    if vids_b:
        top_vb = vids_b[0]
        print(f"│  • Latest Video: {top_vb['title'][:48]:<48} │")
    print("└" + "─" * 68 + "┘")

    print("\n┌── 🧪 ACTIVE A/B EXPERIMENT QUEUE " + "─" * 37 + "┐")
    print("│  • EXP_A_HOOK_01: Question Hook vs Active Counterfactual Statement │")
    print("│  • EXP_B_HOOK_01: Direct Provocation vs Neutral Habit Question     │")
    print("└" + "─" * 68 + "┘\n")


def main():
    parser = argparse.ArgumentParser(description="Content Intelligence & Growth CLI")
    parser.add_argument("--init-db", action="store_true", help="Initialize growth database schema")
    parser.add_argument("--plan-next", choices=["channel_a", "channel_b"], help="Plan the next video recommendation for a channel")
    parser.add_argument("--run-learning", choices=["channel_a", "channel_b"], help="Execute learning cycle and produce weekly report")
    parser.add_argument("--check-snapshots", action="store_true", help="Check and collect pending analytics snapshots")
    parser.add_argument("--dashboard", action="store_true", help="Display visual terminal metrics dashboard")
    parser.add_argument("--dry-run-loop", action="store_true", help="Execute complete end-to-end closed-loop dry run")
    parser.add_argument("--research-external", choices=["channel_a", "channel_b", "both"], help="Execute public analog channel research")
    parser.add_argument("--research-report", action="store_true", help="Generate comprehensive EXTERNAL_INTELLIGENCE_REPORT.md")
    parser.add_argument("--generate-external-experiments", choices=["channel_a", "channel_b"], help="Generate A/B experiment proposals from external priors")
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

    if args.dashboard:
        display_dashboard(repo)

    if args.check_snapshots:
        scheduler = SnapshotScheduler(repo, dry_run=True)
        res = scheduler.run_pending_snapshot_checks()
        print(f"\n[Growth CLI] Snapshot Check Results: Collected {res['collected_count']}, Skipped {res['already_present_count']}, Errors: {len(res['errors'])}\n")

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

    if args.research_external:
        from growth.external_intelligence.researcher import ExternalResearcher
        researcher = ExternalResearcher()
        target_channels = ["channel_a", "channel_b"] if args.research_external == "both" else [args.research_external]
        for ch in target_channels:
            print(f"\n=======================================================")
            print(f"  EXECUTING EXTERNAL RESEARCH: {ch.upper()}")
            print(f"=======================================================")
            res = researcher.run_channel_research(ch, use_live_api=True)
            print(f"• Channels Scanned: {res['channels_scanned']}")
            print(f"• Videos Analyzed: {res['videos_analyzed']}")
            print(f"• Data Provenance: {'SIMULATION' if res.get('is_simulation') else 'REAL_PUBLIC_YOUTUBE'}")
            print(f"• Patterns Mined: {len(res['patterns'])}")
            print(f"• Priors Formulated: {len(res['priors'])}")
            print(f"• Recommendations: {len(res['recommendations'])}")
            for idx, r in enumerate(res['recommendations'], 1):
                print(f"  {idx}. {r['what']} (Transferability: {r['transferability']}, Status: {r['status']})")
                print(f"     Why: {r['why']}")
            print("=======================================================\n")

    if args.research_report:
        from growth.external_intelligence.researcher import ExternalResearcher
        from growth.external_intelligence.research_reports import generate_external_intelligence_markdown_report
        researcher = ExternalResearcher()
        res_a = researcher.run_channel_research("channel_a", use_live_api=True)
        res_b = researcher.run_channel_research("channel_b", use_live_api=True)
        report_path = ROOT_DIR / "EXTERNAL_INTELLIGENCE_REPORT.md"
        report_text = generate_external_intelligence_markdown_report(res_a, res_b, output_path=str(report_path))
        print(f"\n[Growth CLI] Successfully generated external intelligence report at: {report_path.name}")
        print(f"[Growth CLI] Report size: {len(report_text)} characters.\n")

    if args.generate_external_experiments:
        from growth.external_intelligence.researcher import ExternalResearcher
        researcher = ExternalResearcher()
        res = researcher.run_channel_research(args.generate_external_experiments, use_live_api=True)
        print(f"\n=======================================================")
        print(f"  PROPOSED A/B EXPERIMENTS: {args.generate_external_experiments.upper()}")
        print(f"=======================================================")
        for exp in res.get("experiment_proposals", []):
            print(f"• Experiment ID: {exp['experiment_id']}")
            print(f"  Name: {exp['name']}")
            print(f"  Hypothesis: {exp['hypothesis']}")
            print(f"  Control: {exp['control_definition']}")
            print(f"  Variant: {exp['variant_definition']}")
            print(f"  Sample Size: N >= {exp['min_sample_size']} per arm | Primary Metric: {exp['primary_metric']}")
            print("-" * 55)
        print("=======================================================\n")


if __name__ == "__main__":
    main()
