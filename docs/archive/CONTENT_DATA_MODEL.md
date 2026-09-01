# Content Data Model Specification

---

## 🗄️ Database Architecture (`growth/growth.db`)

The database is built on SQLite with relational integrity across 8 core entities:

```text
               ╔═══════════════════╗
               ║     CHANNELS      ║
               ╚═════════╦═════════╝
                         │ 1:N
               ╔═════════▼═════════╗          1:1          ╔═══════════════════╗
               ║      VIDEOS       ║ ◄────────────────────►║  VIDEO_FEATURES   ║
               ╚═════════╦═════════╝                       ╚═══════════════════╝
                         │ 1:N
               ╔═════════▼═════════╗
               ║PERFORMANCE_SNAP...║ (1h, 6h, 24h, 48h, 7d, 28d)
               ╚═══════════════════╝

    ┌────────────────────────┬────────────────────────┬────────────────────────┐
    ▼                        ▼                        ▼                        ▼
╔═══════════════════╗  ╔═══════════════════╗  ╔═══════════════════╗  ╔═══════════════════╗
║ TOPIC_CANDIDATES  ║  ║    EXPERIMENTS    ║  ║ STRATEGY_VERSIONS ║  ║  LEARNING_EVENTS  ║
╚═══════════════════╝  ╚═══════════════════╝  ╚═══════════════════╝  ╚═══════════════════╝
```

---

## 📋 Entity Descriptions

1. **`channels`:** Tracks channel identity (`channel_a`, `channel_b`), branding names, handles, audience definitions, posting frequencies, and pipeline mappings.
2. **`videos`:** Primary record for every generated/published video, tracking global `video_id`, title, duration, YouTube IDs/URLs, QA scores, review status, and strategy version.
3. **`video_features`:** Captures 16+ measurable content features per video (hook type, hook score, word count, scene count, visual change rate, motion intensity, caption density, speaker balance, controversy level).
4. **`performance_snapshots`:** Multi-window time-series snapshots (`1h`, `6h`, `24h`, `48h`, `7d`, `28d`) storing raw metrics (views, likes, comments, shares, subs, watch time, APV) and normalized metrics (`views_per_hour`, `engagement_rate`, `relative_performance_score`).
5. **`topic_candidates`:** Candidate topic pool storing topic text, cluster, explainable score breakdown, and status (`candidate`, `approved`, `generated`, `published`, `retired`).
6. **`experiments`:** A/B hypothesis test registry tracking variable tested, control, variant, primary metric, minimum sample size, and statistical confidence.
7. **`strategy_versions`:** Immutable strategy profile history (`strategy_v1.0`, `strategy_v1.1`) storing audience models, winning patterns, and experiment queues.
8. **`learning_events`:** Audit trail of learning engine runs, autopsies, and strategy update proposals.
