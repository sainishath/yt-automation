# -*- coding: utf-8 -*-
"""
weekly_cycle.py
---------------
Weekly Experiment Synthesis & Learning Cycle.
Aggregates mature cohorts, updates beliefs, proposes versioned strategy mutations
under cooldown safeguards, and generates WEEKLY_LEARNING_REPORT.md.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, timedelta
import json

from growth.db.models import GrowthRepository, VideoModel, PerformanceSnapshotModel, LearningEventModel
from growth.brain.belief_engine import BeliefEngine, VideoMaturity, BeliefStatus
from growth.brain.evaluator import MultiArmExperimentEvaluator, ExperimentDecision
from growth.brain.learning_engine import LearningEngine
from growth.brain.strategy_evolution import StrategyEvolutionEngine
from growth.brain.decision_engine import DecisionEngine
from growth.brain.production_recommendation import ProductionRecommendationEngine
from growth.brain.memory import BrainMemory


class WeeklyLearningCycle:
    """
    Executes the weekly strategic synthesis loop for Content Brain.
    """

    def __init__(
        self,
        repo: GrowthRepository,
        output_dir: Optional[Path] = None
    ):
        self.repo = repo
        self.output_dir = Path(output_dir) if output_dir else Path(repo.db_path).parent.parent
        self.belief_engine = BeliefEngine(repo)
        self.evaluator = MultiArmExperimentEvaluator(repo)
        self.learning_engine = LearningEngine(repo, evaluator=self.evaluator)
        self.strategy_evolution = StrategyEvolutionEngine(repo)
        self.memory = BrainMemory(repo.db_path)
        self.decision_engine = DecisionEngine(self.memory)
        self.rec_engine = ProductionRecommendationEngine(output_dir=self.output_dir)

    def run_weekly_cycle(self, channel_id: str) -> Dict[str, Any]:
        """
        Executes complete weekly synthesis:
        1. Classifies video maturity across 1h, 6h, 24h, 48h, 7d snapshots.
        2. Evaluates mature experiment cohorts (N >= 4).
        3. Emits learning events & FIRST_PARTY_OVERRIDE.
        4. Evaluates immutable strategy mutation under 7-day cooldown.
        5. Updates negative knowledge (DO_NOT_USE registry).
        6. Generates next week's 70/20/10 production recommendation plan.
        7. Produces WEEKLY_LEARNING_REPORT.md.
        """
        start_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Video Accounting & Maturity Classification
        all_videos = self.repo.list_videos(channel_id=channel_id, limit=200)
        published_vids = [v for v in all_videos if v.get("upload_status") == "UPLOADED_PUBLIC"]

        mature_vids = []
        preliminary_vids = []
        immature_vids = []
        diagnostics = []

        for v in published_vids:
            vid_id = v.get("video_id")
            snaps = self.repo.list_snapshots_for_video(vid_id)
            if not snaps:
                immature_vids.append(vid_id)
                continue

            latest_window = snaps[-1].get("window_name", "24h")
            maturity = self.belief_engine.classify_maturity(latest_window)
            if maturity == VideoMaturity.MATURE:
                mature_vids.append(vid_id)
            elif maturity == VideoMaturity.PRELIMINARY:
                preliminary_vids.append(vid_id)
            else:
                immature_vids.append(vid_id)

            # Generate video diagnostic
            diag = self.belief_engine.generate_video_diagnostic(vid_id)
            if diag:
                diagnostics.append(diag.to_dict())

        # 2. Experiment Evaluation (N >= 4 guard)
        active_exps = self.repo.list_experiments(channel_id=channel_id)
        eval_reports = []
        completed_exps = []

        for exp in active_exps:
            exp_id = exp.get("experiment_id")
            report = self.evaluator.evaluate_experiment(exp_id)
            eval_reports.append(report.to_dict())

            if report.status == "EVALUATED":
                completed_exps.append(exp_id)
                # Process learning events & first-party overrides
                self.learning_engine.process_experiment_outcome(exp_id)

        # 3. Strategy Mutation Check (with Cooldown)
        strategy_mutation = self.strategy_evolution.evaluate_strategy_mutation(channel_id)

        # 4. Belief State & Negative Knowledge
        beliefs = [b.to_dict() for b in self.belief_engine.get_channel_beliefs(channel_id)]
        neg_knowledge = self.belief_engine.get_negative_knowledge(channel_id)

        # 5. Next Production Decision & Plan
        decision = self.decision_engine.recommend_next_decision(channel_id)
        recommendation = self.rec_engine.generate_recommendation(decision, save_plan_file=True)

        end_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        report_data = {
            "channel_id": channel_id,
            "period_start": start_time,
            "period_end": end_time,
            "total_published_videos": len(published_vids),
            "maturity_breakdown": {
                "mature_count": len(mature_vids),
                "preliminary_count": len(preliminary_vids),
                "immature_count": len(immature_vids)
            },
            "active_experiments_count": len(active_exps),
            "completed_experiments_count": len(completed_exps),
            "experiment_evaluations": eval_reports,
            "strategy_mutation_status": strategy_mutation,
            "belief_states": beliefs,
            "negative_knowledge": neg_knowledge,
            "next_production_plan": recommendation.to_dict(),
            "diagnostics_summary": diagnostics[:5]
        }

        # 6. Write WEEKLY_LEARNING_REPORT.md
        md_content = self._format_markdown_report(report_data)
        report_path = self.output_dir / f"WEEKLY_LEARNING_REPORT_{channel_id.upper()}.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        return report_data

    def _format_markdown_report(self, data: Dict[str, Any]) -> str:
        ch = data["channel_id"].upper()
        mb = data["maturity_breakdown"]
        strat = data["strategy_mutation_status"]
        plan = data["next_production_plan"]

        return f"""# WEEKLY CONTENT INTELLIGENCE & LEARNING REPORT: {ch}

**Generated At:** {data['period_end']}  
**Channel ID:** `{data['channel_id']}`  

---

## 1. Executive Summary & Video Accounting

- **Total Published Videos:** {data['total_published_videos']}
- **Mature Videos (7d+):** {mb['mature_count']}
- **Preliminary Videos (24h/48h):** {mb['preliminary_count']}
- **Immature Videos (1h/6h):** {mb['immature_count']}
- **Active Experiments:** {data['active_experiments_count']}
- **Completed Experiments ($N \\ge 4$):** {data['completed_experiments_count']}

---

## 2. Strategy & Version Evolution

- **Current Version:** `{strat.get('current_version', 'v1.0')}`
- **Mutation Action:** `{strat.get('action', 'NO_MUTATION_WARRANTED')}`
- **Reason:** {strat.get('reason', 'N/A')}

---

## 3. Institutional Negative Knowledge (`DO_NOT_USE`)

- **Rejected Patterns Count:** {data['negative_knowledge']['rejected_count']}
- **Active Uncertainties Count:** {data['negative_knowledge']['uncertain_count']}

---

## 4. Next Week's Recommended Production Plan

- **Topic:** {plan.get('topic')}
- **Packaging Title:** {plan.get('title_recommendation')}
- **Opening Hook:** {plan.get('hook_recommendation')}
- **Pacing & Duration:** {plan.get('pacing_recommendation')} ({plan.get('target_duration')})
- **Voice Recommendation:** {plan.get('voice_recommendation')}
- **Single-Variable Invariants Locked:** {len(plan.get('invariants', []))} production invariants enforced.
- **Expected Learning:** {plan.get('expected_learning')}

---
*Report generated automatically by Content Brain Closed-Loop Learning Subsystem.*
"""
