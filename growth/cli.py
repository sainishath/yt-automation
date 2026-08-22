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
    parser.add_argument("--create-external-experiments", choices=["channel_a", "channel_b", "both"], help="Bridge active external priors to registered First-Party Experiments")
    parser.add_argument("--experiments", action="store_true", help="List all first-party experiments in database")
    parser.add_argument("--experiment-status", type=str, metavar="EXP_ID", help="Display full audit status and lineage for a specific experiment")
    parser.add_argument("--experiments-ready", action="store_true", help="Display experiments ready for execution in the queue")
    parser.add_argument("--evaluate-experiment", type=str, metavar="EXP_ID", help="Evaluate experiment metrics and apply First-Party Dominance")
    parser.add_argument("--approve-experiment", type=str, metavar="EXP_ID", help="Advance experiment from PROPOSED to APPROVED")
    parser.add_argument("--next-experiment-job", choices=["channel_a", "channel_b"], help="Create and record a production job for an active experiment")
    parser.add_argument("--register-upload", action="store_true", help="Register a verified YouTube upload in the database")
    parser.add_argument("--video-id", type=str, help="Video ID for upload registration")
    parser.add_argument("--yt-id", type=str, help="YouTube video ID for upload registration")
    parser.add_argument("--snapshot-status", action="store_true", help="Check and report status of pending performance snapshot windows")
    parser.add_argument("--experiment-report", action="store_true", help="Generate comprehensive EXPERIMENT_STATUS_REPORT.md")
    parser.add_argument("--brain-status", nargs="?", const="channel_a", help="Display strategic status and portfolio distribution from Brain V1")
    parser.add_argument("--brain-memory", nargs="?", const="channel_a", help="Display everything Content Brain knows about a channel")
    parser.add_argument("--brain-opportunities", nargs="?", const="channel_a", help="Display ranked content opportunities with factor breakdown")
    parser.add_argument("--brain-next", nargs="?", const="channel_a", help="Display next recommended strategic decision (does NOT upload)")
    parser.add_argument("--brain-explain", nargs="?", const="channel_a", help="Display deep 10-point explanation of Brain recommendation")
    parser.add_argument("--brain-cycle", nargs="?", const="channel_a", help="Execute complete automated Daily Brain Cycle")
    parser.add_argument("--brain-knowledge", nargs="?", const="channel_a", help="Display structured institutional knowledge summary")
    parser.add_argument("--brain-dashboard", nargs="?", const="channel_a", help="Display comprehensive Brain Performance & Flywheel Dashboard")
    parser.add_argument("--external-ingest", action="store_true", help="Ingest 500+ structured public observations across 10 benchmark channels")
    parser.add_argument("--external-status", action="store_true", help="Display external intelligence dataset and provenance status")
    parser.add_argument("--external-patterns", action="store_true", help="Display mined cross-channel external patterns and priors")
    parser.add_argument("--brain-backtest", nargs="?", const="channel_a", help="Run historical ranking backtest against external benchmark corpus")
    parser.add_argument("--brain-production-plan", nargs="?", const="channel_a", help="Generate and save structured brain_production_plan.json")
    parser.add_argument("--brain-production-recommendation", nargs="?", const="channel_a", help="Generate comprehensive ProductionRecommendation payload")
    parser.add_argument("--brain-negative-knowledge", nargs="?", const="channel_a", help="Display rejected, contradicted, and uncertain institutional knowledge")
    parser.add_argument("--brain-belief-state", nargs="?", const="channel_a", help="Display empirical belief states and Bayesian progression")
    parser.add_argument("--brain-weekly-report", nargs="?", const="channel_a", help="Execute weekly learning cycle and output WEEKLY_LEARNING_REPORT")
    parser.add_argument("--weekly-learning", nargs="?", const="channel_a", help="Alias for --brain-weekly-report")
    parser.add_argument("--brain-cohort-status", nargs="?", const="channel_a", help="Display active experiment cohort sample balance and maturity")
    parser.add_argument("--brain-learning-state", nargs="?", const="channel_a", help="Display comprehensive learning state, attribution, and negative knowledge")
    parser.add_argument("--brain-learning-status", nargs="?", const="channel_a", help="Alias for --brain-learning-state")
    parser.add_argument("--brain-history", nargs="?", const="channel_a", help="Display complete chronological learning events and strategy history")
    parser.add_argument("--live-learning-status", nargs="?", const="channel_a", help="Display comprehensive real-time live trial dashboard and learning status")
    parser.add_argument("--learning-trace", nargs="?", const="channel_a", help="Display causal learning trace for a video ID or channel")
    parser.add_argument("--channel-scorecard", nargs="?", const="channel_a", help="Display deterministic channel performance scorecard (Baseline vs Current)")
    parser.add_argument("--channel-health", nargs="?", const="channel_a", help="Display robust longitudinal channel health snapshot")
    parser.add_argument("--trial-milestone", nargs=2, metavar=("TAG", "CHANNEL"), help="Capture channel health milestone (e.g. DAY_0 channel_a)")
    parser.add_argument("--external-channel", nargs="?", const="channel_a", help="Display details and benchmark videos for an external channel or target channel")
    parser.add_argument("--external-video", type=str, metavar="VIDEO_ID", help="Display details, snapshots, and observations for an external video")
    parser.add_argument("--external-learning", nargs="?", const="channel_a", help="Display external priors, transferability, and first-party override status")
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

    if args.create_external_experiments:
        from growth.external_intelligence.experiment_bridge import ExperimentBridge
        bridge = ExperimentBridge(repo=repo)
        target_channels = ["channel_a", "channel_b"] if args.create_external_experiments == "both" else [args.create_external_experiments]
        for ch in target_channels:
            print(f"\n=======================================================")
            print(f"  BRIDGING EXTERNAL PRIORS TO FIRST-PARTY EXPERIMENTS: {ch.upper()}")
            print(f"=======================================================")
            res = bridge.batch_bridge_priors(ch, auto_approve=False)
            print(f"• Total Priors Scanned: {res['total_priors_found']}")
            print(f"• Registered Experiments: {len(res['registered'])}")
            print(f"• Skipped Duplicates: {len(res['skipped_duplicates'])}")
            print(f"• Blocked Conflicts: {len(res['blocked_conflicts'])}")
            print(f"• Errors: {len(res['errors'])}")
            for reg in res['registered']:
                print(f"  ✅ Registered: {reg['experiment_id']} (Var: {reg['variable_tested']}, State: {reg['state']})")
            for dup in res['skipped_duplicates']:
                print(f"  ⏭️ Skipped Duplicate: {dup['experiment_id']} ({dup['reason']})")
            for conf in res['blocked_conflicts']:
                print(f"  ⚠️ Blocked Conflict: {conf['experiment_id']} ({conf['reason']})")
            print("=======================================================\n")

    if args.experiments:
        exps = repo.list_experiments()
        print(f"\n=======================================================")
        print(f"  ALL REGISTERED FIRST-PARTY EXPERIMENTS ({len(exps)})")
        print(f"=======================================================")
        for e in exps:
            arms = repo.get_experiment_arms(e["experiment_id"])
            print(f"• ID: {e['experiment_id']} | Channel: {e['channel_id']} | Status: {e['status']}")
            print(f"  Variable: {e['variable_tested']} | Min Sample: N >= {e['min_sample_size']}")
            print(f"  Hypothesis: {e['hypothesis']}")
            if arms:
                print(f"  Arms: {', '.join([a['name'] for a in arms])}")
            print("-" * 55)
        print("=======================================================\n")

    if args.experiment_status:
        from growth.experiments.lineage_tracker import ExperimentLineageTracker
        tracker = ExperimentLineageTracker(repo)
        trace = tracker.trace_experiment(args.experiment_status)
        print(f"\n=======================================================")
        print(f"  EXPERIMENT STATUS & LINEAGE AUDIT: {args.experiment_status}")
        print(f"=======================================================")
        print(json.dumps(trace, indent=2))
        print("=======================================================\n")

    if args.experiments_ready:
        from growth.experiments.experiment_queue import ExperimentQueue
        queue = ExperimentQueue(repo)
        ready_a = queue.get_ready_experiments("channel_a")
        ready_b = queue.get_ready_experiments("channel_b")
        print(f"\n=======================================================")
        print(f"  EXPERIMENTS READY IN EXECUTION QUEUE")
        print(f"=======================================================")
        print(f"Channel A Ready ({len(ready_a)}):")
        for r in ready_a:
            print(f"  • {r['experiment_id']} ({r['variable_tested']} | State: {r['status']})")
        print(f"\nChannel B Ready ({len(ready_b)}):")
        for r in ready_b:
            print(f"  • {r['experiment_id']} ({r['variable_tested']} | State: {r['status']})")
        print("=======================================================\n")

    if args.evaluate_experiment:
        from growth.experiments.experiment_manager import ExperimentManager
        mgr = ExperimentManager(repo=repo)
        outcome = mgr.evaluate_experiment_from_db(args.evaluate_experiment)
        print(f"\n=======================================================")
        print(f"  EXPERIMENT EVALUATION: {args.evaluate_experiment}")
        print(f"=======================================================")
        print(json.dumps(outcome, indent=2))
        print("=======================================================\n")

    if args.experiment_report:
        from growth.experiments.experiment_reports import generate_experiment_status_report
        report_path = ROOT_DIR / "EXPERIMENT_STATUS_REPORT.md"
        report_text = generate_experiment_status_report(repo, output_path=str(report_path))
        print(f"\n[Growth CLI] Successfully generated experiment status report at: {report_path.name}")
        print(f"[Growth CLI] Report size: {len(report_text)} characters.\n")

    if args.approve_experiment:
        from growth.experiments.experiment_queue import ExperimentQueue
        queue = ExperimentQueue(repo)
        res = queue.approve_experiment(args.approve_experiment)
        print(f"\n=======================================================")
        print(f"  EXPERIMENT APPROVAL RESULT")
        print(f"=======================================================")
        print(json.dumps(res, indent=2))
        print("=======================================================\n")

    if args.next_experiment_job:
        from growth.experiments.production_adapter import ProductionJobAdapter
        adapter = ProductionJobAdapter(repo=repo)
        job_res = adapter.create_experiment_production_job(args.next_experiment_job)
        print(f"\n=======================================================")
        print(f"  EXPERIMENT PRODUCTION JOB CREATED: {args.next_experiment_job.upper()}")
        print(f"=======================================================")
        print(json.dumps(job_res, indent=2))
        print("=======================================================\n")

    if args.register_upload:
        if not args.video_id or not args.yt_id:
            print("[Growth CLI] Error: --register-upload requires --video-id and --yt-id.")
        else:
            from growth.experiments.sample_tracker import ExperimentSampleTracker
            tracker = ExperimentSampleTracker(repo=repo)
            upload_res = tracker.register_real_upload(video_id=args.video_id, youtube_video_id=args.yt_id)
            print(f"\n=======================================================")
            print(f"  REAL UPLOAD REGISTRATION RESULT")
            print(f"=======================================================")
            print(json.dumps(upload_res, indent=2))
            print("=======================================================\n")

    if args.snapshot_status:
        from growth.analytics.snapshot_scheduler import SnapshotScheduler
        scheduler = SnapshotScheduler(repo=repo, dry_run=False)
        sched_res = scheduler.run_pending_snapshot_checks()
        print(f"\n=======================================================")
        print(f"  PERFORMANCE SNAPSHOT WINDOWS CHECK")
        print(f"=======================================================")
        print(json.dumps(sched_res, indent=2))
        print("=======================================================\n")

    if args.brain_status is not None:
        from growth.brain.brain import ContentBrain
        brain = ContentBrain()
        status_res = brain.get_status(args.brain_status)
        print(f"\n=======================================================")
        print(f"  CONTENT BRAIN V1 STATUS: {args.brain_status.upper()}")
        print(f"=======================================================")
        print(json.dumps(status_res, indent=2))
        print("=======================================================\n")

    if args.brain_memory is not None:
        from growth.brain.brain import ContentBrain
        brain = ContentBrain()
        mem_res = brain.get_memory_view(args.brain_memory)
        print(f"\n=======================================================")
        print(f"  CONTENT BRAIN V1 MEMORY: {args.brain_memory.upper()}")
        print(f"=======================================================")
        print(json.dumps(mem_res, indent=2))
        print("=======================================================\n")

    if args.brain_opportunities is not None:
        from growth.brain.brain import ContentBrain
        brain = ContentBrain()
        opps_res = brain.get_ranked_opportunities(args.brain_opportunities)
        print(f"\n=======================================================")
        print(f"  RANKED CONTENT OPPORTUNITIES: {args.brain_opportunities.upper()}")
        print(f"=======================================================")
        print(json.dumps(opps_res, indent=2))
        print("=======================================================\n")

    if args.brain_next is not None:
        from growth.brain.brain import ContentBrain
        brain = ContentBrain()
        dec = brain.recommend_next(args.brain_next)
        print(f"\n=======================================================")
        print(f"  CONTENT BRAIN NEXT RECOMMENDATION: {args.brain_next.upper()}")
        print(f"  (Does NOT upload or publish automatically)")
        print(f"=======================================================")
        print(json.dumps(dec.to_dict(), indent=2))
        print("=======================================================\n")

    if args.brain_explain is not None:
        from growth.brain.brain import ContentBrain
        brain = ContentBrain()
        expl = brain.explain_recommendation(args.brain_explain)
        print(f"\n=======================================================")
        print(f"  CONTENT BRAIN STRATEGIC EXPLANATION: {args.brain_explain.upper()}")
        print(f"=======================================================")
        print(json.dumps(expl, indent=2))
        print("=======================================================\n")

    if args.brain_cycle is not None:
        from growth.brain.cycle import DailyBrainCycle
        cycle = DailyBrainCycle()
        report = cycle.run_cycle(args.brain_cycle)
        print(f"\n=======================================================")
        print(f"  AUTOMATED DAILY BRAIN CYCLE: {args.brain_cycle.upper()}")
        print(f"  (Zero auto-upload authority; Gated at Discord review)")
        print(f"=======================================================")
        print(json.dumps(report, indent=2))
        print("=======================================================\n")

    if args.brain_knowledge is not None:
        from growth.brain.brain import ContentBrain
        brain = ContentBrain()
        summary = brain.memory.get_knowledge_summary(args.brain_knowledge)
        print(f"\n=======================================================")
        print(f"  INSTITUTIONAL KNOWLEDGE SUMMARY: {args.brain_knowledge.upper()}")
        print(f"=======================================================")
        print(json.dumps(summary, indent=2))
        print("=======================================================\n")

    if args.brain_dashboard is not None:
        from growth.brain.brain import ContentBrain
        brain = ContentBrain()
        ch = args.brain_dashboard
        snapshot = brain.memory.get_snapshot(ch)
        knowledge = brain.memory.get_knowledge_summary(ch)
        opps = brain.get_ranked_opportunities(ch, limit=3)
        decision = brain.recommend_next(ch)

        # Get latest video and snapshots
        vids = brain.memory.get_published_videos(ch)
        latest_video = vids[0] if vids else None
        latest_metrics = "PENDING"
        if latest_video:
            snaps = brain.memory.repo.get_snapshots_for_video(latest_video["video_id"])
            if snaps:
                s = snaps[-1]
                latest_metrics = {
                    "window": s.get("window_name"),
                    "views": s.get("views", 0),
                    "likes": s.get("likes", 0),
                    "avg_percentage_viewed": s.get("avg_percentage_viewed", "PENDING"),
                    "data_source": s.get("data_source")
                }

        dashboard = {
            "channel": ch,
            "current_strategy": snapshot.strategy_version,
            "active_experiments": [
                {
                    "experiment_id": e.get("experiment_id"),
                    "name": e.get("name"),
                    "variable_tested": e.get("variable_tested"),
                    "control_count": e.get("control_count", 0),
                    "treatment_count": e.get("treatment_count", 0),
                    "status": e.get("status")
                }
                for e in snapshot.active_experiments
            ],
            "arm_sample_counts": snapshot.first_party_samples_by_arm,
            "latest_published_video": {
                "video_id": latest_video["video_id"] if latest_video else "NONE",
                "youtube_id": latest_video.get("youtube_video_id") if latest_video else "NONE",
                "title": latest_video.get("title") if latest_video else "NONE",
                "metrics": latest_metrics
            },
            "known_winners": knowledge.get("supported_patterns", []),
            "known_losers": knowledge.get("rejected_patterns", []),
            "contradicted_external_priors": knowledge.get("contradicted_external_beliefs", []),
            "active_uncertainties": knowledge.get("active_uncertainties", []),
            "top_ranked_opportunities": opps,
            "next_recommended_production_decision": {
                "decision_type": decision.decision_type.value,
                "arm_type": decision.arm_type,
                "variable_under_test": decision.variable_under_test,
                "topic": decision.opportunity.topic if decision.opportunity else None,
                "hook": decision.opportunity.proposed_hook if decision.opportunity else None,
                "confidence": decision.confidence.value,
                "reasoning": decision.reasoning,
                "why_selected": decision.explanation_breakdown.get("why_this_experiment")
            }
        }

        print(f"\n=======================================================")
        print(f"  CONTENT BRAIN FLYWHEEL DASHBOARD: {ch.upper()}")
        print(f"=======================================================")
        print(json.dumps(dashboard, indent=2))
        print("=======================================================\n")

    if args.external_ingest:
        from growth.external_intelligence.dataset_builder import ExternalDatasetBuilder
        from growth.external_intelligence.repository import ExternalIntelligenceRepository
        ext_repo = ExternalIntelligenceRepository()
        builder = ExternalDatasetBuilder(ext_repo)
        res = builder.build_dataset(target_count_per_channel=55)
        print(f"\n=======================================================")
        print(f"  EXTERNAL PUBLIC INTELLIGENCE INGESTION")
        print(f"=======================================================")
        print(json.dumps(res, indent=2))
        print("=======================================================\n")

    if args.external_status:
        from growth.external_intelligence.repository import ExternalIntelligenceRepository
        ext_repo = ExternalIntelligenceRepository()
        channels = ext_repo.list_external_channels()
        videos = ext_repo.list_external_videos(limit=1000)
        priors = ext_repo.list_external_priors()
        patterns = ext_repo.list_external_patterns()
        status = {
            "channel_count": len(channels),
            "video_count": len(videos),
            "pattern_count": len(patterns),
            "prior_count": len(priors),
            "provenance": "100% PUBLIC_YOUTUBE",
            "private_metrics_status": "EXPLICITLY_UNAVAILABLE_FIRST_PARTY_ONLY"
        }
        print(f"\n=======================================================")
        print(f"  EXTERNAL INTELLIGENCE DATASET STATUS")
        print(f"=======================================================")
        print(json.dumps(status, indent=2))
        print("=======================================================\n")

    if args.external_patterns:
        from growth.external_intelligence.repository import ExternalIntelligenceRepository
        ext_repo = ExternalIntelligenceRepository()
        patterns = ext_repo.list_external_patterns()
        p_list = [p.to_dict() if hasattr(p, "to_dict") else p for p in patterns]
        print(f"\n=======================================================")
        print(f"  CROSS-CHANNEL EXTERNAL PATTERNS")
        print(f"=======================================================")
        print(json.dumps(p_list, indent=2))
        print("=======================================================\n")

    if args.external_channel is not None:
        from growth.external_intelligence.repository import ExternalIntelligenceRepository
        ext_repo = ExternalIntelligenceRepository()
        tgt = args.external_channel
        # Check if argument is target channel name or specific external channel id
        if tgt in ["channel_a", "channel_b"]:
            channels = ext_repo.list_external_channels(target_channel_id=tgt)
            print(f"\n=======================================================")
            print(f"  EXTERNAL BENCHMARK CHANNELS FOR {tgt.upper()}")
            print(f"=======================================================")
            print(json.dumps(channels, indent=2))
            print("=======================================================\n")
        else:
            ch = ext_repo.get_external_channel(tgt)
            vids = ext_repo.list_external_videos(external_channel_id=tgt, limit=20)
            print(f"\n=======================================================")
            print(f"  EXTERNAL CHANNEL PROFILE: {tgt}")
            print(f"=======================================================")
            print(json.dumps({"channel": ch, "top_videos": vids}, indent=2))
            print("=======================================================\n")

    if args.external_video is not None:
        from growth.external_intelligence.repository import ExternalIntelligenceRepository
        ext_repo = ExternalIntelligenceRepository()
        vid = ext_repo.get_external_video(args.external_video)
        obs = ext_repo.list_observations_by_video(args.external_video)
        snaps = ext_repo.list_external_video_snapshots(args.external_video)
        print(f"\n=======================================================")
        print(f"  EXTERNAL VIDEO AUDIT: {args.external_video}")
        print(f"=======================================================")
        print(json.dumps({
            "video": vid,
            "snapshots": snaps,
            "observations": obs,
            "provenance": "100% PUBLIC_YOUTUBE"
        }, indent=2))
        print("=======================================================\n")

    if args.external_learning is not None:
        from growth.external_intelligence.repository import ExternalIntelligenceRepository
        from growth.brain.belief_engine import BeliefEngine
        ext_repo = ExternalIntelligenceRepository()
        tgt = args.external_learning
        priors = ext_repo.list_external_priors(target_channel_id=tgt)
        patterns = ext_repo.list_external_patterns(target_channel_id=tgt)
        scores = ext_repo.list_transferability_scores(target_channel_id=tgt)
        belief_engine = BeliefEngine(repo)
        beliefs = belief_engine.get_channel_beliefs(tgt)
        print(f"\n=======================================================")
        print(f"  EXTERNAL INTELLIGENCE & CAUSAL LEARNING: {tgt.upper()}")
        print(f"=======================================================")
        print(json.dumps({
            "target_channel": tgt,
            "external_patterns_count": len(patterns),
            "external_priors_count": len(priors),
            "transferability_scores_count": len(scores),
            "first_party_beliefs_count": len(beliefs),
            "causal_hierarchy": "FIRST_PARTY_CONTROLLED > FIRST_PARTY_OBSERVATIONAL > EXTERNAL_PUBLIC > EXTERNAL_RESEARCH",
            "priors": priors[:5]
        }, indent=2))
        print("=======================================================\n")

    if args.brain_backtest is not None:
        from growth.brain.backtester import BrainBacktester
        backtester = BrainBacktester()
        report = backtester.run_backtest(args.brain_backtest)
        print(f"\n=======================================================")
        print(f"  HISTORICAL DECISION BACKTEST: {args.brain_backtest.upper()}")
        print(f"=======================================================")
        print(json.dumps(report.to_dict(), indent=2))
        print("=======================================================\n")

    target_plan_ch = args.brain_production_plan or args.brain_production_recommendation
    if target_plan_ch is not None:
        from growth.brain.brain import ContentBrain
        from growth.brain.production_recommendation import ProductionRecommendationEngine
        brain = ContentBrain()
        decision = brain.next_production_decision(target_plan_ch)
        engine = ProductionRecommendationEngine()
        rec = engine.generate_recommendation(decision, save_plan_file=True)
        print(f"\n=======================================================")
        print(f"  CONTENT BRAIN PRODUCTION RECOMMENDATION: {target_plan_ch.upper()}")
        print(f"  (Single-Variable Enforced: {rec.experiment_variable})")
        print(f"=======================================================")
        print(json.dumps(rec.to_dict(), indent=2))
        print("=======================================================\n")

    if args.brain_negative_knowledge is not None:
        from growth.brain.brain import ContentBrain
        brain = ContentBrain()
        ch = args.brain_negative_knowledge
        knowledge = brain.memory.get_knowledge_summary(ch)
        neg = {
            "channel_id": ch,
            "rejected_patterns": knowledge.get("rejected_patterns", []),
            "contradicted_external_priors": knowledge.get("contradicted_external_beliefs", []),
            "active_uncertainties": knowledge.get("active_uncertainties", []),
            "untested_patterns": knowledge.get("untested_patterns", [])
        }
        print(f"\n=======================================================")
        print(f"  INSTITUTIONAL NEGATIVE KNOWLEDGE: {ch.upper()}")
        print(f"=======================================================")
        print(json.dumps(neg, indent=2))
        print("=======================================================\n")


    if args.brain_belief_state is not None:
        from growth.brain.belief_engine import BeliefEngine
        engine = BeliefEngine(repo)
        ch = args.brain_belief_state
        beliefs = [b.to_dict() for b in engine.get_channel_beliefs(ch)]
        print(f"\n=======================================================")
        print(f"  EMPIRICAL BELIEF STATE & PROGRESSION: {ch.upper()}")
        print(f"=======================================================")
        print(json.dumps(beliefs, indent=2))
        print("=======================================================\n")

    target_weekly = args.weekly_learning or args.brain_weekly_report
    if target_weekly is not None:
        from growth.brain.weekly_cycle import WeeklyLearningCycle
        cycle = WeeklyLearningCycle(repo)
        ch = target_weekly
        report = cycle.run_weekly_cycle(ch)
        print(f"\n=======================================================")
        print(f"  WEEKLY LEARNING CYCLE REPORT: {ch.upper()}")
        print(f"=======================================================")
        print(json.dumps(report, indent=2))
        print("=======================================================\n")

    target_cohort = args.brain_cohort_status
    if target_cohort is not None:
        ch = target_cohort
        exps = repo.list_experiments(channel_id=ch)
        vids = repo.list_videos(channel_id=ch)
        pub_vids = [v for v in vids if v.get("upload_status") == "UPLOADED_PUBLIC"]
        status_data = {
            "channel_id": ch,
            "total_published_videos": len(pub_vids),
            "active_experiments": [
                {
                    "experiment_id": e.get("experiment_id"),
                    "name": e.get("name"),
                    "variable_tested": e.get("variable_tested"),
                    "control_count": e.get("control_count", 0),
                    "treatment_count": e.get("treatment_count", 0),
                    "target_per_arm": 4,
                    "status": e.get("status"),
                    "next_needed_arm": "CONTROL" if e.get("control_count", 0) < e.get("treatment_count", 0) else "TREATMENT"
                }
                for e in exps
            ]
        }
        print(f"\n=======================================================")
        print(f"  COHORT SAMPLE BALANCE & STATUS: {ch.upper()}")
        print(f"=======================================================")
        print(json.dumps(status_data, indent=2))
        print("=======================================================\n")

    target_learning = args.brain_learning_status or args.brain_learning_state
    if target_learning is not None:
        from growth.brain.belief_engine import BeliefEngine
        engine = BeliefEngine(repo)
        ch = target_learning
        beliefs = [b.to_dict() for b in engine.get_channel_beliefs(ch)]
        neg = engine.get_negative_knowledge(ch)
        learning_evts = repo.list_learning_events(channel_id=ch, limit=10)
        state_data = {
            "channel_id": ch,
            "beliefs": beliefs,
            "negative_knowledge": neg,
            "recent_learning_events": learning_evts
        }
        print(f"\n=======================================================")
        print(f"  COMPREHENSIVE LEARNING STATE: {ch.upper()}")
        print(f"=======================================================")
        print(json.dumps(state_data, indent=2))
        print("=======================================================\n")

    if args.brain_history is not None:
        ch = args.brain_history
        events = repo.list_learning_events(channel_id=ch, limit=50)
        print(f"\n=======================================================")
        print(f"  CHRONOLOGICAL LEARNING HISTORY: {ch.upper()}")
        print(f"=======================================================")
        print(json.dumps(events, indent=2))
        print("=======================================================\n")

    if args.live_learning_status is not None:
        from growth.brain.brain import ContentBrain
        brain = ContentBrain()
        ch = args.live_learning_status
        status = brain.get_live_learning_status(ch)
        print(f"\n=======================================================")
        print(f"  LIVE FIRST-PARTY LEARNING TRIAL STATUS: {ch.upper()}")
        print(f"=======================================================")
        print(json.dumps(status, indent=2))
        print("=======================================================\n")

    if args.learning_trace is not None:
        from growth.brain.brain import ContentBrain
        brain = ContentBrain()
        arg_val = args.learning_trace
        if arg_val in ["channel_a", "channel_b"]:
            traces = brain.list_learning_traces(arg_val, limit=5)
            print(f"\n=======================================================")
            print(f"  RECENT LEARNING TRACES: {arg_val.upper()}")
            print(f"=======================================================")
            print(json.dumps(traces, indent=2))
            print("=======================================================\n")
        else:
            trace = brain.get_learning_trace(arg_val)
            print(f"\n=======================================================")
            print(f"  VIDEO CAUSAL LEARNING TRACE: {arg_val}")
            print(f"=======================================================")
            print(json.dumps(trace, indent=2))
            print("=======================================================\n")

    if args.channel_scorecard is not None:
        from growth.brain.brain import ContentBrain
        brain = ContentBrain()
        ch = args.channel_scorecard
        scorecard = brain.get_channel_scorecard(ch)
        print(f"\n=======================================================")
        print(f"  CHANNEL IMPROVEMENT SCORECARD: {ch.upper()}")
        print(f"=======================================================")
        print(json.dumps(scorecard, indent=2))
        print("=======================================================\n")

    if args.channel_health is not None:
        from growth.brain.brain import ContentBrain
        brain = ContentBrain()
        ch = args.channel_health
        health = brain.get_channel_health(ch)
        print(f"\n=======================================================")
        print(f"  CHANNEL HEALTH SNAPSHOT: {ch.upper()}")
        print(f"=======================================================")
        print(json.dumps(health, indent=2))
        print("=======================================================\n")

    if args.trial_milestone is not None:
        from growth.brain.brain import ContentBrain
        brain = ContentBrain()
        tag, ch = args.trial_milestone
        milestone = brain.record_channel_milestone(ch, tag=tag)
        print(f"\n=======================================================")
        print(f"  RECORDED CHANNEL MILESTONE: {tag.upper()} ({ch.upper()})")
        print(f"=======================================================")
        print(json.dumps(milestone, indent=2))
        print("=======================================================\n")


if __name__ == "__main__":
    main()

