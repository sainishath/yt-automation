# CLOSED-LOOP LEARNING SYSTEM ARCHITECTURE

**System:** YouTube Automation & Content Intelligence Platform  
**Target:** First-Party Autonomous Empirical Learning Flywheel  
**Repository:** `D:\Projects\yt-automations`  
**Branch:** `feature/growth-intelligence`  
**Date:** August 21, 2026  

---

## 1. End-to-End Flywheel Architecture Map

```text
=========================================================================================================
                               CLOSED-LOOP LEARNING FLYWHEEL
=========================================================================================================

 [1. STRATEGIC DECISION]
         │  • 70/20/10 Portfolio Allocation
         │  • Next Experiment & Cohort Balancer (Prioritizes Lagging Arm)
         ▼
 [2. PRODUCTION RECOMMENDATION]
         │  • Packaging, Title, Hook, 6-Beat Script Arc, Pacing, Invariants
         │  • Saves `brain_production_plan_{channel}.json`
         ▼
 [3. PHYSICAL PIPELINE GENERATION]
         │  • Pipeline 1: Chronos Shift (SDXL + Ken Burns + ChristopherNeural)
         │  • Pipeline 2: Debate Protocol (Split-Host + Piper Ryan/Samantha)
         ▼
 [4. 17/17 & 16/16 QA VERIFICATION]
         │  • 0-Tolerance Automated Gate (Audio mix, aspect ratio, frame rate, captions)
         ▼
 [5. MANDATORY DISCORD REVIEW GATE] ───► [HUMAN OPERATOR] ───► Approved / Rejected
         │                                                      (Zero direct auto-upload)
         ▼
 [6. REAL YOUTUBE PUBLISHING]
         │  • Channel-isolated OAuth credentials (ID verification)
         │  • Idempotent Sample Registration in SQLite `experiments`/`arms`
         ▼
 [7. 6-WINDOW SNAPSHOT SCHEDULER]
         │  • 1h / 6h   ──► IMMATURE (Early diagnostic & anomaly alerts)
         │  • 24h / 48h ──► PRELIMINARY (Video-level diagnostic attribution)
         │  • 7d        ──► MATURE (Cohort statistical comparison & belief updates)
         │  • 28d       ──► LONG-TERM (Historical baseline calibration)
         ▼
 [8. MULTI-DIMENSIONAL ATTRIBUTION & DIAGNOSTICS]
         │  • Topic Demand, Hook Retention, Pacing, Ending Punchline
         ▼
 [9. MULTI-ARM COHORT EVALUATION]
         │  • N >= 4 Hard Guard per Arm
         │  • Median Absolute Deviation (MAD) Outlier Protection
         │  • Minimum Effect Delta (>= 5.0% APV)
         ▼
 [10. BELIEF UPDATE & LEARNING ENGINE]
         │  • First-Party Dominance (`FIRST_PARTY_OVERRIDE`)
         │  • Negative Knowledge Persistence (`DO_NOT_USE` Registry)
         │  • Institutional Memory Update (`growth/brain/memory.py`)
         ▼
 [11. IMMUTABLE STRATEGY EVOLUTION]
         │  • Proposes version mutation (`v1.0` ──► `v1.1`) only upon N >= 4 win
         │  • Cooldown Safeguard (7-day mutation lock)
         ▼
 [12. NEXT PRODUCTION PLAN] ─────────────► (Feeds back into Step 1)
=========================================================================================================
```

---

## 2. Component Inventory: Existing vs Enhanced

| Subsystem | File Path | Status | Role in Closed Loop |
|---|---|---|---|
| **Content Brain Facade** | `growth/brain/brain.py` | **IMPLEMENTED** | Orchestrates recommendations, memory queries, explanations, and decisions. |
| **Production Recommendation** | `growth/brain/production_recommendation.py` | **IMPLEMENTED** | Generates packaging, script arcs, pacing, and single-variable contracts. |
| **Multi-Arm Evaluator** | `growth/brain/evaluator.py` | **IMPLEMENTED** | Computes median APV delta, enforces $N \ge 4$ guard, and applies MAD outlier protection. |
| **Learning Engine** | `growth/brain/learning_engine.py` | **ENHANCED** | Emits `VIDEO_DIAGNOSTIC`, `EXPERIMENT_COMPLETED`, `FIRST_PARTY_OVERRIDE`, and updates belief states. |
| **Belief & Negative Knowledge** | `growth/brain/belief_engine.py` | **NEW** | Tracks Bayesian/empirical belief transitions (`HYPOTHESIS` $\to$ `VALIDATING` $\to$ `PROMOTED` / `REJECTED`) and persists `DO_NOT_USE` registry. |
| **Strategy Evolution** | `growth/brain/strategy_evolution.py` | **IMPLEMENTED** | Creates immutable versioned mutations (`v1.0` $\to$ `v1.1`) with 7-day cooldown. |
| **Weekly Learning Cycle** | `growth/brain/weekly_cycle.py` | **NEW** | Generates `WEEKLY_LEARNING_REPORT.md` analyzing mature cohorts and next week's queue. |
| **Snapshot Scheduler** | `growth/analytics/snapshot_scheduler.py` | **IMPLEMENTED** | Collects live snapshots across 6 windows with maturity classifications. |
| **Production Adapters** | `growth/experiments/production_adapter.py` | **IMPLEMENTED** | Injects experiment metadata into generation manifests idempotently. |
| **QA Verification Suites** | `scripts/run_qa_suite.py` | **IMPLEMENTED** | 17/17 QA (Pipeline 1) and 16/16 QA (Pipeline 2) zero-tolerance gate. |
| **Discord Human Review** | `alternate-history-shorts/scripts/discord_review.py` | **IMPLEMENTED** | Human in the loop gate before public YouTube upload. |

---

## 3. Strict Closed-Loop Invariants

1. **No Metric Fabrication:** Missing analytics remain `PENDING` / `NOT_AVAILABLE`.
2. **First-Party Dominance:** Empirical first-party data ($N \ge 4$) strictly overrides contradictory external priors.
3. **Statistical Sample Guard:** No strategy mutation or winner declaration is permitted before $N \ge 4$ valid samples per arm.
4. **Single-Variable Discipline:** Exactly one variable is tested per experiment (e.g. `HOOK_STRUCTURE`), while all other production parameters are locked as invariants.
5. **Zero Direct Auto-Upload Authority:** The Content Brain cannot publish to YouTube without human approval in Discord.
6. **Strict Channel Isolation:** Chronos Shift (`channel_a`) and Debate Protocol (`channel_b`) maintain separate strategies, models, and learnings.
