# EXTERNAL CONTENT INTELLIGENCE AUDIT

**Repository:** `D:\Projects\yt-automations`  
**Subsystem:** `growth/external_intelligence/`  
**Audit Date:** August 21, 2026  
**Auditor:** Lead ML & Content Intelligence Engineer  

---

## 1. Executive Summary & Existing Subsystem Inventory

The external intelligence subsystem provides public market research, analog channel profiling, pattern mining, and transferability analysis to generate empirical hypotheses for Channel A (Chronos Shift / Alternate History) and Channel B (Debate Protocol / Conversational Shorts).

### Existing Modules Inspected

| Module | Purpose | Current Status | Findings & Capabilities |
|---|---|---|---|
| [`schemas.py`](file:///d:/Projects/yt-automations/growth/external_intelligence/schemas.py) | Data models & Enums | **COMPLETE** | Defines `ExternalChannelModel`, `ExternalVideoModel`, `ExternalObservationModel`, `ExternalPatternModel`, `TransferabilityScoreModel`, `ExternalPriorModel`, and `ProvenanceSource`. Strictly separates `OBJECTIVE_FACT` from `INTERPRETATION`. |
| [`channel_registry.py`](file:///d:/Projects/yt-automations/growth/external_intelligence/channel_registry.py) | Curated benchmark channel archetypes | **COMPLETE** | 10 high-fit benchmark channels (5 for Channel A, 5 for Channel B). Weighted multi-factor similarity scoring across topic, audience, format, duration, and production. |
| [`external_sources.json`](file:///d:/Projects/yt-automations/growth/external_intelligence/external_sources.json) | Source registry | **COMPLETE** | Explicit machine-readable source configuration with URLs, YouTube channel IDs, and target channel relevance. |
| [`youtube_observer.py`](file:///d:/Projects/yt-automations/growth/external_intelligence/youtube_observer.py) | Public YouTube Data API v3 collector | **COMPLETE** | Queries public statistics (views, likes, comments, duration). Enforces provenance tagging (`PUBLIC_YOUTUBE`). |
| [`feature_extractor.py`](file:///d:/Projects/yt-automations/growth/external_intelligence/feature_extractor.py) | Feature parsing & normalization | **COMPLETE** | Extracts title length, character counts, question patterns, entities, hook types, curiosity triggers, and calculates view multipliers relative to channel median. |
| [`pattern_miner.py`](file:///d:/Projects/yt-automations/growth/external_intelligence/pattern_miner.py) | Cross-channel pattern miner | **COMPLETE** | Discovers recurring hook patterns and topic clusters with channel count, video count, consistency score, and relative performance multiplier. |
| [`transferability.py`](file:///d:/Projects/yt-automations/growth/external_intelligence/transferability.py) | Transferability classifier | **COMPLETE** | Classifies transferability into `HIGH`, `MEDIUM`, `LOW`, `DO_NOT_TRANSFER` based on audience, topic, format, production feasibility, and repeatability. |
| [`prior_engine.py`](file:///d:/Projects/yt-automations/growth/external_intelligence/prior_engine.py) | Prior synthesizer | **COMPLETE** | Converts transferable patterns into formal `ExternalPriorModel` hypotheses with bounded prior weights ($\le 0.25$). |
| [`repository.py`](file:///d:/Projects/yt-automations/growth/external_intelligence/repository.py) | SQLite persistence layer | **COMPLETE** | Manages `external_channels`, `external_videos`, `external_observations`, `external_patterns`, `external_priors`, and `transferability_scores` tables. |
| [`dataset_builder.py`](file:///d:/Projects/yt-automations/growth/external_intelligence/dataset_builder.py) | 500+ Public Corpus Builder | **COMPLETE** | Ingests 550 structured public observations across all 10 benchmark channels with non-fabrication guarantees. |

---

## 2. Hard Invariants & Evidence Rules

1. **First-Party Dominance:**
   $$\text{First-Party Experiment Outcome } (N \ge 4) \succ \text{First-Party Snapshots } \succ \text{External Priors } \succ \text{Heuristics}$$
   If our empirical experiment ($N \ge 4$) rejects a variant, the external prior is automatically demoted to `REJECTED` (`prior_weight = 0.0`), triggering a `FIRST_PARTY_OVERRIDE` event.
2. **Hypothesis vs Truth:**
   External intelligence generates **hypotheses** and **opportunities**, never proven strategies or winner declarations.
3. **No Private Analytics Scraping:**
   External data only records publicly visible fields (title, public view count, public likes, public comments, duration). Private creator metrics (retention, swipe-away rate, APV) are marked `NOT_AVAILABLE / FIRST_PARTY_ONLY`.
4. **Channel Isolation:**
   Channel A analog channels (`analog_a_*`) never populate Channel B priors, and Channel B analog channels (`analog_b_*`) never populate Channel A priors.

---

## 3. Schema & Data Quality Evaluation

- **Provenance:** Every external record retains `source_type = ProvenanceSource.PUBLIC_YOUTUBE` and raw video URL.
- **Missing Metrics Handling:** Missing likes or disabled comments are recorded without zero-filling or fabricating fake values.
- **Deduplication & Idempotency:** SQLite primary keys (`external_video_id`, `pattern_id`, `prior_id`) ensure safe rerunability without row duplication.
