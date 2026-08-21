# External Intelligence Reality Audit Report

**Repository Root:** `d:/Projects/yt-automations`  
**Audit Date:** 2026-08-21  
**Audit Scope:** Pre-implementation architectural and reality audit of external intelligence capabilities across the codebase.

---

## 1. CURRENT BRANCH & COMMIT STATUS

- **Current Branch:** `feature/growth-intelligence`
- **Current Commit:** `b1d3cb7d06967a4307711af99fd7974dad87f5a0` (*"feat(channels): link authenticated Channel A and Channel B identities with live security guards"*)
- **Worktree Status:** Clean (`nothing to commit, working tree clean`).
- **Base Branches Present:** `main`, `agent/production-freeze`.

---

## 2. EXTERNAL INTELLIGENCE FILES: REAL VS. SCAFFOLDING

- **Directory Status:** `growth/external_intelligence/` **DOES NOT EXIST YET** (clean greenfield state).
- **Existing External Research Files in Workspace:** None. Zero previous external scraping or intelligence scripts.
- **Scaffolding vs Real Code:** Clean start — No phantom scaffolding or dead boilerplate exists.

---

## 3. REAL DATA COLLECTION CAPABILITY & MOCKS

- **YouTube API Access:** 
  * Authenticated OAuth tokens exist for Channel A (`alternate-history-shorts/config/token.json`) and Channel B (`convo-shorts/yt-automation-engine/youtube_token.pickle`) with full scopes: `youtube.upload`, `youtube.readonly`, `yt-analytics.readonly`.
  * Public YouTube Data API v3 access is available for querying channels, playlists, search results, and public video metadata (`videos().list(part='snippet,statistics,contentDetails')` and `channels().list(part='snippet,statistics,contentDetails')`).
  * Web research capabilities exist via direct HTTP queries (Europe PMC, OpenAlex, arXiv, Wikipedia in Pipeline 1 RAG).
- **Mock/Simulation Capabilities:** 
  * `growth/analytics/mock_data_generator.py` exists for first-party offline curve simulations.
  * **Strict Data Provenance Rule:** The codebase strictly tags data sources (`REAL_YOUTUBE_ANALYTICS`, `REAL_YOUTUBE_STATS_ONLY`, `SIMULATION_FALLBACK`). 
  * **No-Fake-Data Invariant:** External intelligence will enforce mandatory provenance (`REAL_EXTERNAL_DATA`, `PUBLIC_YOUTUBE`, `SIMULATION`), ensuring zero fabricated competitor metrics are written into production research tables.

---

## 4. DATABASE SUPPORT & ENTITY EXPANSION

- **Current Database:** SQLite in WAL mode with foreign keys enabled (`growth/growth.db`, `growth/db/schema.sql`).
- **Current Entities (9 tables):** `channels`, `videos`, `video_features`, `performance_snapshots`, `topic_candidates`, `experiments`, `strategy_versions`, `learning_events`, `jobs`.
- **Hot Backup Utility:** `growth/db/backup.py` with SQLite online backup API (`conn.backup()`).
- **Required New External Intelligence Tables:**
  1. `external_channels` (analog channels with similarity metadata and channel stats)
  2. `external_videos` (observed public videos, durations, view counts, publication dates)
  3. `external_observations` (granular facts vs interpretations with confidence levels)
  4. `external_evidence` (corroborated cross-channel evidence items)
  5. `external_patterns` (mined patterns with frequency, supporting channels/videos, confidence)
  6. `external_priors` (bounded hypothesis priors with status, transferability, expiry)
  7. `transferability_scores` (multi-dimensional transferability evaluations)
  8. `research_runs` (audit log of external research runs, duration, channels scanned)

---

## 5. EXISTING INTEGRATION POINTS

| Subsystem | File Location | Integration Method |
|---|---|---|
| **Topic Engine** | `growth/topic_engine/topic_scorer.py`, `topic_pool.py` | Bounded secondary prior signal in topic scoring (`FIRST_PARTY > EXTERNAL > HEURISTIC`). |
| **Experiment Engine** | `growth/experiments/registry.py`, `experiment_manager.py` | Generates candidate single-variable A/B experiments with $N \ge 4$ requirement. |
| **Learning Engine** | `growth/learning/learning_engine.py` | Distinguishes `FIRST_PARTY_LEARNING` vs `EXTERNAL_PRIOR`; first-party evidence dominates and overrides external hypotheses. |
| **REST Server** | `growth/server.py` | Exposes read-only research endpoints (`GET /api/external-intelligence/...`). External intelligence has **ZERO** publishing authority. |
| **CLI** | `growth/cli.py` | Adds commands (`--research-external`, `--research-report`, `--generate-external-experiments`). |
| **n8n Orchestration** | `growth/n8n-workflows/` | Weekly external research trigger feeding candidate experiments into review gate. |

---

## 6. EXISTING TEST COVERAGE

- **Current Growth Test Suite:** **42/42 PASS** across 17 test modules (`growth/run_growth_tests.py`).
- **Master Release Verification:** **21/21 PASS** (`verify_release.py`).
- **Isolation:** 0 cross-pipeline imports between `alternate-history-shorts`, `convo-shorts`, and `growth`.

---

## 7. FROZEN PRODUCTION IMPACT & ZERO-REGRESSION ASSURANCE

- **Pipeline 1 (`alternate-history-shorts/`):** **ZERO MODIFICATIONS**. RAG v4 academic grounding, 0 unsupported claims gate, Whisper alignment, Fooocus SDXL, Candidate A Ken Burns motion, 17/17 QA checks, Discord review, and uploader remain untouched.
- **Pipeline 2 (`convo-shorts/`):** **ZERO MODIFICATIONS**. Dual Piper TTS voices, dialogue balancing, dynamic subtitles, gameplay canvas, 16/16 QA checks, Discord review, and uploader remain untouched.
- **Discord Review Gate:** Remains the mandatory final gate before any video reaches YouTube. External intelligence cannot publish or mutate production generation code.

---

## 8. RECOMMENDED IMPLEMENTATION ORDER

```text
STAGE 1: Data Foundation (Schema, Models, Provenance Enums, DB Migrations)
   ↓
STAGE 2: Analog Channel Research (Channel A & B Analog Registry, Similarity Scoring, Public Data Collector)
   ↓
STAGE 3: Video Observation & Feature Extraction (Fact vs Interpretation, Public Metrics, Baseline Normalization)
   ↓
STAGE 4: Pattern Mining (Recurring Multi-Channel Pattern Discovery, Corroboration Engine)
   ↓
STAGE 5: Transferability Engine (Bounded Multi-Dimensional Scoring, Surface vs Principle Analysis)
   ↓
STAGE 6: External Priors & Experiment Integration (Bounded Priors, First-Party Override Rule, A/B Candidates N>=4)
   ↓
STAGE 7: Reports, CLI, REST API, Tests (Growth Suite 42+ Tests & Master Release 21/21 Verification)
```
