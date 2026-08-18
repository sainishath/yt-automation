# YouTube Content Intelligence: Brutal Reality Audit

**Repository Root:** `d:\Projects\yt-automations`  
**Git Branch:** `feature/growth-intelligence`  
**Audit Date:** 2026-08-18  
**Audit Purpose:** Evaluate code reality vs documented claims across all growth components.

---

## 🔍 System Component Reality Classification

| Component | Status | Reality Assessment |
|---|:---:|---|
| **1. Database Layer (`growth/db/`)** | **PRODUCTION-READY** | Real SQLite database with WAL mode, foreign keys, constraints, and models for 9 entities (including `jobs` and `video_features`). |
| **2. Channel Identity Guard (`growth/channels/`)** | **PRODUCTION-READY** | Strict channel identity verifier (`channel_identity_check.py`) that performs a hard abort on channel ID mismatch. Non-secret configs in `config/channels/`. |
| **3. Video Feature Extractor (`growth/features/`)** | **PRODUCTION-READY** | Real pre-publication feature extractors for P1 (`feature_extractor_p1.py`) and P2 (`feature_extractor_p2.py`) parsing real manifests, scene plans, and audio metrics. |
| **4. Live YouTube Data API (`growth/analytics/`)** | **PARTIAL** | `youtube_api_collector.py` calls `youtube.videos().list()` for live views, likes, and comments, but previously filled missing analytics fields (shares, retention) with hardcoded heuristics. Needs explicit data provenance (`REAL_YOUTUBE`, `REAL_YOUTUBE_STATS_ONLY`, `SIMULATION_FALLBACK`). |
| **5. Live YouTube Analytics API (`growth/analytics/`)** | **SCAFFOLD** | `youtubeAnalytics.reports().query` was stubbed. Requires real API query construction, date window calculation, and missing metric handling. |
| **6. Metric Normalizer (`growth/analytics/normalizer.py`)** | **PRODUCTION-READY** | Computes real 10-video median baselines and versioned composite scores ($40\%$ retention, $35\%$ velocity, $25\%$ engagement) with outlier caps. |
| **7. Topic Scoring Engine (`growth/topic_engine/topic_scorer.py`)**| **PRODUCTION-READY** | Real, deterministic, explainable multi-factor scoring formula (`topic_score_v1`). |
| **8. Topic Deduplicator (`growth/topic_engine/deduplicator.py`)** | **PRODUCTION-READY** | Real token Jaccard similarity engine with a $0.65$ threshold. |
| **9. Topic Lifecycle Machine (`growth/topic_engine/topic_lifecycle.py`)** | **PRODUCTION-READY** | Real 9-state machine (`DISCOVERED` through `ARCHIVED`) with SQLite persistence. |
| **10. Strategy Memory & Versioning (`growth/strategy/`)** | **PRODUCTION-READY** | Immutable versioned JSON strategy profiles for Channel A and Channel B. |
| **11. A/B Experiment Framework (`growth/experiments/`)** | **PRODUCTION-READY** | Hypothesis registry and evaluator enforcing $N \ge 4$ sample minimums per arm. |
| **12. Learning Engine (`growth/learning/learning_engine.py`)** | **PARTIAL** | Generates real autopsies and weekly markdown reports, and inserts `strategy_versions` upon high-confidence experiment acceptance, but needs automated tracking of underlying video IDs and structured `LearningEvent` records. |
| **13. Content Planner (`growth/planner/content_planner.py`)** | **PRODUCTION-READY** | Synthesizes topic pool ranking, active strategy version, and experiment arm into a complete `NEXT_VIDEO_PLAN` JSON. |
| **14. REST API Bridge (`growth/server.py`)** | **PRODUCTION-READY** | Real HTTP server on Port 8010 handling `GET /api/growth/plan-next`, `POST /api/growth/record-upload`, and `GET /api/growth/dashboard`. |
| **15. n8n Workflow Integration (`growth/n8n-workflows/`)** | **REAL** | Canonical JSON workflow connecting daily scheduler $\to$ growth plan $\to$ pipeline generation $\to$ QA $\to$ Discord approval $\to$ upload $\to$ record upload. |
| **16. Observability Dashboard (`growth/cli.py`)** | **PRODUCTION-READY** | Real ASCII terminal dashboard (`--dashboard`) displaying channel metrics, active experiments, and next queued videos. |
| **17. Frozen Pipeline Protections** | **PRODUCTION-READY** | Candidate A Ken Burns motion, RAG evidence grounding, 17-point QA gate, and Discord review gates remain 100% untouched. |

---

## 🛠️ Required Production Hardening Actions

1. **Harden YouTube API Ingestion (`growth/analytics/youtube_api_collector.py` & `collector.py`):**
   - Integrate `youtubeAnalytics.reports().query(...)` with exact date-range calculations (`startDate`, `endDate`).
   - Strictly mark data provenance: `REAL_YOUTUBE_ANALYTICS`, `REAL_YOUTUBE_STATS_ONLY`, or `SIMULATION_FALLBACK`.
   - Never invent or fabricate numbers when live metrics are pending or unavailable.
2. **Harden Snapshot Worker & Multi-Window Scheduling (`growth/analytics/snapshot_scheduler.py`):**
   - Dedicated scheduler checking which videos are eligible for `1h`, `6h`, `24h`, `48h`, `7d`, `28d` snapshots.
   - Idempotent recording preventing duplicate snapshots for the same window.
3. **Harden Learning Engine (`growth/learning/learning_engine.py`):**
   - Record explicit structured `LearningEvent` records linking hypothesis observations with supporting video IDs.
4. **Harden Test Matrix (`growth/tests/`):**
   - Add negative tests for channel ID mismatch, expired tokens, duplicate snapshots, quota exhaustion, and API failure recovery.
