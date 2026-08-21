# REAL PRODUCTION FLYWHEEL AUDIT (Phases 11–28)

**Repository:** `D:\Projects\yt-automations`  
**Branch:** `feature/growth-intelligence`  
**Audit Date:** August 21, 2026  
**Auditor:** Lead Autonomous Intelligence Engineer  

---

## 1. System Overview & Invariant Matrix

The YouTube Automation & Growth Intelligence platform has reached the closed-loop operational stage. The system links strategic decision-making (`growth/brain/`), physical generation pipelines (`alternate-history-shorts`, `convo-shorts`), QA verification, Discord human review, real YouTube publishing, snapshot collection, multi-arm evaluation, and immutable strategy evolution.

### Core Hard Invariants
1. **Zero Fabricated YouTube Metrics:** YouTube Data API v3 and Analytics API v2 only. Missing metrics remain `ANALYTICS_PENDING` (never guessed as 0).
2. **First-Party Dominance:** Empirical first-party experiment results ($N \ge 4$) strictly demote contradictory external priors (`FIRST_PARTY_OVERRIDE`).
3. **$N \ge 4$ Evaluation Guard:** No experiment winner may be declared or promoted without at least 4 valid published samples per arm.
4. **Single-Variable Discipline:** Experiments isolate exactly one variable (e.g. `HOOK_STRUCTURE`); multi-variable proposals are strictly rejected.
5. **Strategy Immutability:** Existing version files (`v1.0.json`) are never overwritten; promotions yield new immutable versions (`v1.1.json`).
6. **Mandatory Human Discord Gate:** The Content Brain has zero direct YouTube upload authority. Every public video requires operator approval in Discord.
7. **Channel Isolation:** Chronos Shift (`channel_a`) and Debate Protocol (`channel_b`) remain completely isolated across models, datasets, learnings, and strategies.

---

## 2. Comprehensive Flywheel Subsystem Trace

| Step | Subsystem / File | Current Status | Findings & Implementation Details |
|---|---|---|---|
| **1. Strategic Decision** | `growth/brain/decision_engine.py`<br>`growth/brain/brain.py` | **IMPLEMENTED** | Determines next action based on active experiment cohort balance (`TREATMENT: 1, CONTROL: 0` $\to$ recommends `CONTROL`). |
| **2. Opportunity Ranking** | `growth/brain/opportunity_engine.py` | **IMPLEMENTED** | Multi-factor ranking: 0.35 FP APV + 0.25 Aud + 0.15 Ext + 0.15 Nov + 0.10 Exp across 70/20/10 portfolio. |
| **3. Hypothesis Formation** | `growth/brain/hypothesis_engine.py` | **IMPLEMENTED** | Generates single-variable hypothesis with explicit constants and expected learning. |
| **4. Job Dispatch & Adapter** | `growth/experiments/production_adapter.py`<br>`growth/brain/cycle.py` | **IMPLEMENTED** | Connects Brain decision to SQLite `jobs` table and pipeline manifest. Idempotency verified. |
| **5. Core Video Generation** | `alternate-history-shorts/scripts/`<br>`convo-shorts/scripts/` | **IMPLEMENTED & FROZEN** | Production pipelines generate 1080x1920 60fps video with dual EdgeTTS/Piper voices, SDXL art, and 8% Ken Burns motion. |
| **6. Automated QA Gate** | `scripts/run_qa_suite.py` | **IMPLEMENTED** | 17/17 QA (Pipeline 1) and 16/16 QA (Pipeline 2) must pass with 0 failures before review. |
| **7. Discord Review Gate** | `alternate-history-shorts/scripts/discord_review.py`<br>`shared/discord_review.py` | **IMPLEMENTED (MANUAL OPERATOR GATE)** | Compresses video to 540x960 proxy, posts to Discord webhook. Requires operator reply (`approve <job_id>` or `reject <job_id>`). |
| **8. Real YouTube Upload** | `alternate-history-shorts/scripts/upload_to_youtube.py`<br>`convo-shorts/scripts/upload_to_youtube.py` | **IMPLEMENTED** | Dedicated OAuth credentials per channel with channel ID validation before upload. |
| **9. Upload Registration** | `growth/experiments/sample_tracker.py`<br>`growth/cli.py --register-upload` | **IMPLEMENTED** | Idempotently increments arm sample counts upon verified YouTube upload. Duplicate registrations preserved. |
| **10. Snapshot Scheduling** | `growth/analytics/snapshot_scheduler.py` | **IMPLEMENTED** | Checks elapsed time against 6 windows (1h, 6h, 24h, 48h, 7d, 28d). |
| **11. Analytics Ingestion** | `growth/analytics/youtube_api_collector.py` | **IMPLEMENTED** | Queries YouTube API v3/v2 for live views, likes, comments, and APV. |
| **12. Multi-Arm Evaluation** | `growth/brain/evaluator.py` | **IMPLEMENTED** | Enforces $N \ge 4$ guard, applies MAD outlier filtering, and calculates median APV delta. |
| **13. Learning Extraction** | `growth/brain/learning_engine.py` | **IMPLEMENTED** | Emits `EXPERIMENT_COMPLETED`, `FIRST_PARTY_OVERRIDE`, and `STRATEGY_PROPOSAL` learning events. |
| **14. Memory Accumulation** | `growth/brain/memory.py` | **IMPLEMENTED** | Tracks `SUPPORTED`, `PROMISING`, `UNCERTAIN`, `REJECTED`, `CONTRADICTED`, `UNTESTED` states. |
| **15. Strategy Evolution** | `growth/brain/strategy_evolution.py` | **IMPLEMENTED** | Evaluates immutable mutation (`v1.0` $\to$ `v1.1`) upon $N \ge 4$ win. |
| **16. Daily Brain Cycle** | `growth/brain/cycle.py` | **IMPLEMENTED** | Idempotently runs all 10 analytical steps without auto-uploading. |

---

## 3. Dangerous Assumptions & Edge Cases Audited

1. **Snapshot Scheduler Eligibility:** Non-uploaded or rejected videos should be explicitly filtered in `snapshot_scheduler.py` to avoid calling YouTube Data API for unuploaded video IDs. *(Hardened in Task 5).*
2. **Production Job Idempotency:** Calling `--brain-cycle` multiple times while a job is pending Discord review must not create duplicate jobs. *(Hardened in Task 3).*
3. **Outlier Distortion:** Extreme viral hits or corrupt data can skew means; the Evaluator strictly employs Median Absolute Deviation (MAD) on medians. *(Hardened in Task 12).*
4. **Missing Metrics Handling:** Distinguishes `OBSERVED`, `NOT_AVAILABLE`, and `PENDING` rather than recording false zeros. *(Hardened in Task 12).*

---

## 4. Manual vs Automated Division of Responsibility

- **Fully Automated:** Decision planning, opportunity ranking, single-variable hypothesis formulation, job payload construction, video rendering, Whisper alignment, dynamic subtitle burning, audio ducking, 17/17 QA verification, Discord proxy upload, snapshot scheduling, real metric ingestion, statistical evaluation, learning extraction, memory updates, strategy mutation proposal.
- **Intentionally Manual (Hard Invariant):**
  - **Discord Operator Review:** Must explicitly approve/reject the compiled video before YouTube upload.
  - **YouTube API Publishing Execution:** Initiated upon operator approval to guarantee human in the loop.
