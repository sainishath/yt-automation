# -*- coding: utf-8 -*-
"""
experiment_reports.py
---------------------
Generates comprehensive, explainable EXPERIMENT_STATUS_REPORT.md documents.
Audits the complete closed-loop lifecycle for all first-party experiments:
Active, Completed, Winners, Losers, Inconclusive, Rejected Priors, and Strategy Candidates.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from growth.db.models import GrowthRepository
from growth.experiments.lineage_tracker import ExperimentLineageTracker


def generate_experiment_status_report(
    repo: Optional[GrowthRepository] = None,
    output_path: Optional[str] = None
) -> str:
    """
    Generates a structured, auditable EXPERIMENT_STATUS_REPORT.md markdown report.
    """
    repo = repo or GrowthRepository()
    tracker = ExperimentLineageTracker(repo)
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    experiments = repo.list_experiments()
    active_exps = [e for e in experiments if e.get("status") in ["PROPOSED", "APPROVED", "SCHEDULED", "RUNNING", "COLLECTING_DATA"]]
    completed_exps = [e for e in experiments if e.get("status") in ["ACCEPTED", "REJECTED", "INCONCLUSIVE"]]

    winners = [e for e in completed_exps if e.get("status") == "ACCEPTED"]
    losers = [e for e in completed_exps if e.get("status") == "REJECTED"]
    inconclusive = [e for e in completed_exps if e.get("status") == "INCONCLUSIVE"]

    md = []
    md.append("# First-Party Experiment Status & Closed-Loop Learning Report\n")
    md.append(f"**Generated:** {ts}  ")
    md.append(f"**Total Experiments Tracked:** {len(experiments)}  ")
    md.append(f"**Active Experiments:** {len(active_exps)} | **Completed Experiments:** {len(completed_exps)}  ")
    md.append(f"**Verdict Distribution:** {len(winners)} Treatment Wins, {len(losers)} Control Wins (Prior Overrides), {len(inconclusive)} Inconclusive  \n")
    md.append("---\n")

    # 1. Executive Summary & Core Rules
    md.append("## 1. Executive Summary & First Principles\n")
    md.append(
        "This report tracks every controlled first-party A/B experiment operating in the YouTube Growth System. "
        "Every experiment tests **exactly one isolated variable** with a hard $N \\ge 4$ sample size guard. "
        "Under the system's core governance rule:\n"
        "> **First-Party Evidence Dominance:** External observations only produce bounded priors (weight $\\le 0.25$). "
        "Only empirical first-party channel performance data ($N \\ge 4$) can validate or reject a hypothesis.\n"
    )

    # 2. Portfolio Summary Table
    md.append("## 2. Experiment Portfolio Overview\n")
    md.append("| Status | Count | Key Operational Rule |")
    md.append("|---|:---:|---|")
    md.append(f"| **Active / Running** | {len(active_exps)} | One Variable, One Active Experiment per Variable per Channel |")
    md.append(f"| **Completed — Treatment Won** | {len(winners)} | Promoted to Candidate Strategy Version |")
    md.append(f"| **Completed — Control Won** | {len(losers)} | External Prior Demoted to `REJECTED`, Weight = 0.0 |")
    md.append(f"| **Completed — Inconclusive** | {len(inconclusive)} | Insufficient difference (< 5%), prior remains unconfirmed |")
    md.append(f"| **Total Tracked** | {len(experiments)} | 100% Traceable Lineage |")

    # 3. Active Experiments Table
    md.append("\n---\n## 3. Active Experiments Queue\n")
    if active_exps:
        md.append("| Experiment ID | Channel | Variable Tested | Min Sample | Current Progress | Status | Source |")
        md.append("|---|:---:|---|:---:|:---:|:---:|---|")
        for e in active_exps:
            ctrl_n = e.get("control_count", 0)
            treat_n = e.get("treatment_count", 0)
            min_n = e.get("min_sample_size", 4)
            source = e.get("source_type", "FIRST_PARTY")
            md.append(f"| `{e['experiment_id']}` | **{e['channel_id']}** | `{e['variable_tested']}` | $N \\ge {min_n}$ | C:{ctrl_n}/{min_n}, T:{treat_n}/{min_n} | `{e['status']}` | {source} |")
    else:
        md.append("*No active experiments currently in queue.*\n")

    # 4. Completed Experiments & First-Party Dominance Table
    md.append("\n---\n## 4. Completed Experiments & Evidence Outcomes\n")
    if completed_exps:
        md.append("| Experiment ID | Channel | Variable | Delta (%) | Decision | Prior Override | Confidence |")
        md.append("|---|:---:|---|:---:|:---:|:---:|:---:|")
        for e in completed_exps:
            delta = e.get("delta_percentage", 0.0)
            delta_str = f"{delta:+.1f}%" if delta is not None else "N/A"
            dec = e.get("decision", "INCONCLUSIVE")
            override = "YES (Weight -> 0.0)" if dec == "REJECT_VARIANT" else "NO"
            conf = e.get("confidence", "MEDIUM")
            md.append(f"| `{e['experiment_id']}` | **{e['channel_id']}** | `{e['variable_tested']}` | **{delta_str}** | `{dec}` | {override} | `{conf}` |")
    else:
        md.append("*No completed experiments yet (awaiting empirical video cohort samples).*\n")

    # 5. Detailed Experiment Lineage Cards
    md.append("\n---\n## 5. Detailed Experiment Lineage & Audit Trace\n")
    for e in experiments:
        trace_data = tracker.trace_experiment(e["experiment_id"])
        lineage = trace_data.get("lineage", {})
        md.append(f"### Experiment: `{e['experiment_id']}`\n")
        md.append(f"- **Channel:** `{e['channel_id']}` | **Status:** `{e['status']}` | **Provenance:** `{e.get('provenance', 'FIRST_PARTY')}`")
        md.append(f"- **Hypothesis:** {e['hypothesis']}")
        md.append(f"- **Variable Under Test:** `{e['variable_tested']}` (Single variable isolated)")
        md.append(f"- **Control Definition:** {e['control_definition']}")
        md.append(f"- **Treatment Definition:** {e['variant_definition']}")
        md.append(f"- **Success Metric:** `{e['primary_metric']}` (Min $N={e.get('min_sample_size', 4)}$ per arm)")

        if e.get("external_prior_id"):
            md.append(f"- **Linked External Prior:** `{e['external_prior_id']}` (Initial Weight: {e.get('prior_weight', 0.20):.2f})")

        # Arms
        arms = lineage.get("arms", [])
        if arms:
            arm_summary = ", ".join([f"{a['arm_type']} (`{a['arm_id']}`: {a['sample_count']} samples)" for a in arms])
            md.append(f"- **Registered Arms:** {arm_summary}")

        # Missing links check
        if not trace_data["is_complete"]:
            missing_str = ", ".join(trace_data["missing_links"])
            md.append(f"- **Lineage Status:** `INCOMPLETE` (Pending: {missing_str})")
        else:
            md.append("- **Lineage Status:** `COMPLETE` (100% Traceable)")

        # Result if evaluated
        if e.get("decision"):
            md.append(f"- **Verdict:** `{e['decision']}` | **Delta:** {e.get('delta_percentage', 0.0):+.1f}% | **Evaluated At:** {e.get('evaluated_at')}")

        md.append("\n" + "-" * 50 + "\n")

    # 6. Strategy Candidates & Mutation Pipeline
    md.append("## 6. Strategy Version Lineage & Mutation Candidates\n")
    md.append("Strategy promotions require reproducible empirical evidence ($N \\ge 4$). The hierarchy is:\n")
    md.append("`EXTERNAL_PRIOR` → `EXPERIMENTAL` → `SUPPORTED_BY_FIRST_PARTY` → `CANDIDATE_STRATEGY` → `VALIDATED_STRATEGY`\n")
    if winners:
        for w in winners:
            md.append(f"- **Candidate for Version Promotion:** `{w['experiment_id']}` ({w['variable_tested']} +{w.get('delta_percentage', 0.0):.1f}%)")
    else:
        md.append("*No pending strategy promotion candidates. Current baseline strategies remain active.*\n")

    report_content = "\n".join(md)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_content)

    return report_content
