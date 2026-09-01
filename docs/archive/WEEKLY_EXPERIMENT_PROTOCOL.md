# WEEKLY EXPERIMENT PROTOCOL & LEARNING CADENCE

**System:** YouTube Automation & Closed-Loop Content Intelligence  
**Target:** Operational Cadence, Cohort Management & Strategic Synthesis  
**Repository:** `D:\Projects\yt-automations`  
**Branch:** `feature/growth-intelligence`  
**Date:** August 21, 2026  

---

## 1. Operational Publishing & Cohort Cadence

To balance statistical rigor with consistent YouTube channel momentum, each channel follows a structured operational tempo:

```text
  [Daily Tempo]           : 1 Video / Day per Channel (7 Videos / Week)
  [Experiment Cohort]     : 4 Control + 4 Treatment = 8 Videos Total (~8–10 Days per Experiment)
  [Balancing Strategy]    : Dynamic Cohort Balancer automatically assigns the next job to the lagging arm
  [Human Gate]            : Every video requires 17/17 (or 16/16) QA Pass + Discord Human Approval
```

---

## 2. Weekly Synthesis & Learning Loop Schedule

| Day / Phase | Operations Executed | System Action |
|---|---|---|
| **Daily (Days 1–7)** | Production, QA, Discord Gate, Upload, Snapshot Tracking | Ingests 1h, 6h, 24h, 48h, 7d snapshots; emits `VIDEO_DIAGNOSTIC` events. |
| **Weekly Review (End of Week)** | Mature Cohort Synthesis & Strategic Evaluation | Evaluates all experiments with $N \ge 4$; computes statistical significance; updates beliefs. |
| **Strategy Mutation Gate** | Immutable Version Proposal (`v1.0` $\to$ `v1.1`) | If winning experiment detected and cooldown expired (>7 days), creates new strategy version. |
| **Next Week Queue** | 70/20/10 Production Queue Generation | Generates `brain_production_plan_{channel}.json` for the upcoming cohort. |

---

## 3. Progressive 70/20/10 Portfolio Evolution

The allocation of production resources evolves as first-party empirical data matures:

```text
  [EARLY STAGE] (0–10 Videos)   : 70% Strategy v1.0 Baseline
                                  20% External Prior Experiments (Counterfactual / Socratic Hooks)
                                  10% High-Risk Exploratory Concepts
                                  ▲ (External evidence heavy, First-party weak)
                                  │
  [MIDDLE STAGE] (10–30 Videos) : 70% First-Party Validated Core Patterns
                                  20% Single-Variable Micro-Experiments (Pacing, Topic Clusters)
                                  10% Exploratory Analogs
                                  ▲ (Balanced empirical + external)
                                  │
  [MATURE STAGE] (30+ Videos)   : 70% Highly Optimized Empirical Core (v1.2+)
                                  20% Incremental Single-Variable Refinements
                                  10% Continuous External Radar Discovery
```

---

## 4. Weekly Learning Report Specification

At the end of each weekly cycle, the Brain generates a structured `WEEKLY_LEARNING_REPORT`:
1. **Executive Summary:** Videos analyzed, mature videos count, experiments completed.
2. **Cohort Accounting:** Active experiment status with exact Control / Treatment sample breakdown.
3. **Strongest Empirical Signals:** Top-performing hooks, topics, and retention slopes.
4. **Negative Knowledge (`DO_NOT_USE`):** Explicitly rejected techniques and empirical reasons.
5. **Belief & Prior Updates:** External priors validated or demoted (`FIRST_PARTY_OVERRIDE`).
6. **Strategy Version Status:** Active immutable version and mutation history.
7. **Upcoming Production Plan:** Machine-readable next-video recommendations for each channel.
