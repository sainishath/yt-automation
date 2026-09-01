# Content Intelligence & Learning System

---

## 🏛️ 1. Architecture Overview

The Content Intelligence System operates as a modular, decoupled learning and optimization layer wrapping our two frozen production generation pipelines (`alternate-history-shorts` and `convo-shorts`).

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

## 🔒 2. Production Safety & Decoupling Rules

1. **Frozen Production Integrity:**  
   The growth engine never directly alters the core generation logic (Candidate A Ken Burns motion, RAG evidence grounding, Whisper alignment, 17/17 QA gates, or Discord review approval).
2. **Channel Identity Guard:**  
   `channel_identity_check.py` validates the authenticated channel ID before upload, preventing accidental cross-channel publishing.
3. **Advisory Strategy Layer:**  
   Strategy recommendations are strictly advisory and never override factual verification or safety checks.
4. **Zero Secret Commitment:**  
   All channel configs in `config/channels/` contain strictly public/non-secret parameters. Tokens and client secrets remain external and protected in `.gitignore`.
