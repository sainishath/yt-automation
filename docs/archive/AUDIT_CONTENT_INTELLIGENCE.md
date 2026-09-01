# Content Intelligence & Learning System Audit

---

## 1. System Objectives & The Closed-Loop Vision

The objective is to establish an **autonomous, evidence-based learning cycle** around both production pipelines:

```text
               ┌────────────────────────────────────────────────────────┐
               │              RESEARCH & TOPIC INTELLIGENCE            │
               │   (P1: History & What-If  |  P2: Debates & Psychology) │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │                STRATEGY & EXPERIMENT ENGINE            │
               │  (Strategy v1.0, Experiment Assignment, Hook Scoring)  │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │               FROZEN PRODUCTION GENERATION             │
               │          (Pipeline 1 Server  |  Pipeline 2 Server)     │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │               HARD QUALITY & REVIEW GATES              │
               │       (17-Point QA  |  Discord Human Approval)         │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │               PUBLISH (CHANNEL-SEGREGATED)             │
               │       (Channel A: History  |  Channel B: Debates)      │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │               YOUTUBE ANALYTICS INGESTION              │
               │       (Snapshots: 1h, 6h, 24h, 48h, 7d, 28d)           │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │              PERFORMANCE ANALYSIS & NORMALIZATION      │
               │     (Retention, Velocity, APV, Conversion, Medians)    │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │             LEARNING ENGINE & STRATEGY UPDATE          │
               │     (Statistical Hypotheses -> Strategy Update v1.1)   │
               └────────────────────────────────────────────────────────┘
```

---

## 2. Key Modules to Implement in `growth/`

1. **`growth/db/` (Data Persistence Layer):**  
   SQLite relational database (`growth.db`) tracking `channels`, `videos`, `video_features`, `performance_snapshots`, `experiments`, `topic_candidates`, `strategy_versions`, and `learning_events`.
2. **`growth/analytics/` (Analytics Collector & Normalizer):**  
   Multi-window ingestion engine collecting metrics at 1h, 6h, 24h, 48h, 7d, 28d; normalizes metrics against channel baseline and recent median.
3. **`growth/features/` (Video Feature Extractor):**  
   Extracts 25+ structured numerical and categorical features per video (hook type, word count, visual change rate, narrative structure, audio pacing, controversy level).
4. **`growth/topic_engine/` (Topic Intelligence & Deduplication):**  
   Multi-factor topic scoring formula ($70\%$ proven concepts, $20\%$ adjacent experiments, $10\%$ high-risk experiments) with semantic deduplication.
5. **`growth/strategy/` (Strategy Engine & Versioning):**  
   Immutable versioned strategy profiles (`channel_a_strategy.json`, `channel_b_strategy.json`) storing audience models, winning patterns, and experiment queues.
6. **`growth/experiments/` (Experiment Framework):**  
   Hypothesis-driven A/B test registry tracking variable, control, variant, sample size, and statistical significance.
7. **`growth/learning/` (Learning Engine):**  
   Periodic analyzer generating weekly growth reports, winner/loser autopsies, and strategy update proposals.
8. **`growth/channels/` (Channel Identity & Upload Safeguards):**  
   Channel configuration files and pre-upload identity verifier preventing accidental cross-channel publishing.

---

## 3. Risk Assessment & Safety Architecture

| Risk | Mitigation |
|---|---|
| **Pipeline Destabilization** | Growth system sits as a non-invasive wrapper around existing servers; zero changes to Candidate A motion, RAG, or QA. |
| **Analytics API Quota / Outage** | Collector operates in mock/fallback mode when API is unavailable; production generation never blocks on analytics. |
| **Premature / Hallucinated Strategy Changes** | Strategy updates require human approval; strictly distinguishes observation from causality with `INSUFFICIENT_DATA` guards. |
| **Wrong-Channel Upload** | `channel_identity_check.py` validates authenticated Google Channel ID against expected channel before upload; mismatch causes immediate hard abort. |
| **Credential Leakage** | All channel configs are strictly non-secret; tokens and client secrets remain external, managed in local `.gitignore`. |
