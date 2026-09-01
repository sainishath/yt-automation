# Growth Data Model & Integrity Schema

---

## 🗄️ Relational Database Schema (`growth/growth.db`)

The database is built on SQLite with WAL mode enabled and foreign keys enforced.

### Entity Index:
1. **`channels`:** Channel identity (`channel_a`, `channel_b`), handle, audience definition, and frequency.
2. **`videos`:** Globally unique `video_id`, title, duration, YouTube IDs, QA score, and review status.
3. **`video_features`:** Pre-publication extracted characteristics (hook type, word count, scene count, visual change rate, motion intensity, caption density, speaker balance).
4. **`performance_snapshots`:** Multi-window time-series (`1h`, `6h`, `24h`, `48h`, `7d`, `28d`) with a `UNIQUE(video_id, window_name)` constraint.
5. **`topic_candidates`:** 9-state lifecycle topic candidate pool (`DISCOVERED` through `ARCHIVED`).
6. **`experiments`:** Controlled A/B hypothesis registry.
7. **`strategy_versions`:** Immutable strategy profile history (`strategy_v1.0`, `strategy_v1.1`).
8. **`learning_events`:** Audit log of reports and strategy promotions.
9. **`jobs`:** Lifecycle job queue tracking (`PLANNED`, `GENERATING`, `GENERATED`, `QA_FAILED`, `AWAITING_REVIEW`, `REJECTED`, `APPROVED`, `UPLOADING`, `PUBLISHED`, `ANALYTICS_PENDING`, `COMPLETED`, `FAILED`).
