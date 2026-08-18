# Deep Production Audit: YouTube Content Intelligence & Learning System

**Repository Root:** `d:\Projects\yt-automations`  
**Branch:** `feature/growth-intelligence`  
**Audit Date:** 2026-08-18  
**Audit Scope:** Full audit across `growth/`, `alternate-history-shorts/`, `convo-shorts/`, `config/channels/`, n8n workflows, database, analytics, and quality gates.

---

## 25-Point Comprehensive Production Assessment

### 1. What is genuinely implemented?
- **Relational Data Persistence:** SQLite schema (`growth.db`) with 8 tables and `GrowthRepository` CRUD methods.
- **Channel Isolation & Identity Guards:** Channel config files (`pipeline1_channel.json`, `pipeline2_channel.json`) and pre-upload identity validator (`channel_identity_check.py`) that strictly aborts on channel ID mismatch.
- **Measurable Feature Extraction:** Pre-publication feature extractors for Pipeline 1 (`feature_extractor_p1.py`) and Pipeline 2 (`feature_extractor_p2.py`) extracting 16+ features per video.
- **Metric Normalization Engine:** Multi-factor normalizer (`normalizer.py`) computing 10-video median baselines and composite performance scores ($40\%$ retention, $35\%$ velocity, $25\%$ engagement).
- **Topic Portfolio & Deduplication:** Topic scorer (`topic_score_v1`), token Jaccard deduplicator (`deduplicator.py`), and topic pool manager (`topic_pool.py`).
- **A/B Experiment Framework:** Hypothesis registry and sample-size evaluator requiring $N \ge 4$ before rendering a verdict.
- **Reporting & Autopsy:** Automated postmortem generator (`autopsy_analyzer.py`) and Markdown Weekly Channel Growth Report generator (`report_generator.py`).
- **Autonomous Planner:** `content_planner.py` synthesizing topic ranking, strategy context, and experiment queue.

### 2. What is only a mock/stub?
- **Live YouTube Analytics Ingestion:** `growth/analytics/collector.py` currently falls back to `mock_data_generator.py`. The real YouTube Analytics API integration (`youtubeAnalytics.reports().query(...)` / `youtube.videos().list(...)`) needs to be fully wired to handle real OAuth scopes, rate limits, and quota handling.
- **Automated Strategy Version Bump:** `learning_engine.py` evaluates experiments and outputs markdown, but does not yet write `channel_a_strategy_v2.json` to disk automatically upon verified experiment acceptance.

### 3. What is deterministic?
- Topic scoring equations (`topic_scorer.py`).
- Token Jaccard similarity and deduplication thresholds (`deduplicator.py`).
- Metric normalization formulas and median baselines (`normalizer.py`).
- Feature extraction parsing from manifests, scene plans, and audio timings.
- Database relational CRUD queries and integrity constraints.

### 4. What requires real YouTube API data?
- Actual view counts, impressions, traffic sources, average percentage viewed (APV), subscriber conversion rate, and retention curve drop-off timestamps for published videos.

### 5. What currently runs automatically?
- Unit tests (`growth/run_growth_tests.py`).
- Master release verification (`verify_release.py`).
- Feature extraction upon run completion.
- Closed-loop simulation and dry-run loop (`growth/cli.py --dry-run-loop`).

### 6. What currently requires manual execution?
- Initiating the learning cycle CLI (`python growth/cli.py --run-learning channel_a`).
- Triggering YouTube Analytics snapshot pulls across scheduled windows (`1h`, `6h`, `24h`, `48h`, `7d`, `28d`).
- Moving topics from `candidate` to production trigger in n8n.

### 7. What is connected to n8n?
- Existing production generation workflows (`xAyYyalPutEsTsDb` for P1 and `N3DelK9B5ssN879H` for P2) are active in n8n, calling ports `8000` and `5001` with Discord approval gates.

### 8. What is NOT connected to n8n?
- Direct HTTP polling from n8n to fetch the next planned topic from `growth/planner/content_planner.py`. (Requires a dedicated REST API bridge).
- Automated webhook from uploader back to growth database to register upload events and schedule analytics ingestion.

### 9. What can currently produce the next video automatically?
- `growth/planner/content_planner.py` produces the complete structured plan JSON (`channel_id`, `topic`, `category`, `cluster`, `strategy_version`, `experiment_id`, `experiment_variant`, `target_duration`).
- When passed to `pipeline_runner.py` or `media_engine.py`, full generation, QA, and Discord posting execute automatically.

### 10. What cannot produce the next video automatically?
- Autonomous scheduling across days of the week without an external cron/n8n schedule trigger.

### 11. What can automatically learn?
- Autopsy analysis classifies videos into `ABOVE_MEDIAN`, `BELOW_MEDIAN`, or `ON_MEDIAN`, identifying strong/weak signals.
- Experiment evaluator determines whether `VARIANT_OUTPERFORMS_CONTROL` ($> +5\%$ delta) or `CONTROL_OUTPERFORMS_VARIANT` ($< -5\%$ delta) once $N \ge 4$.

### 12. What merely records data?
- `performance_snapshots` table records time-series metrics.
- `learning_events` table logs report executions.

### 13. What strategy changes are actually applied?
- Active strategy version (`strategy_v1.0`) is passed to the planner, enforcing duration boundaries and experiment selection.

### 14. What strategy changes are merely proposed?
- Recommended topic additions and pacing adjustments generated in markdown reports are proposed to the user rather than auto-mutating pipeline generation code.

### 15. Security risks:
- **Low:** All channel configs contain zero secrets. OAuth tokens and client secrets are ignored in `.gitignore`.
- **Mitigation:** Pre-commit scans enforce zero secret leaks.

### 16. Data integrity risks:
- SQLite table locks during high-frequency concurrent writes.
- **Mitigation:** Wrap DB transactions in connection context managers with WAL mode enabled.

### 17. YouTube API limitations:
- YouTube Data API quota: 10,000 units/day. Video upload costs 1,600 units (max 6 uploads/day).
- YouTube Analytics API reports have a 24-to-48 hour reporting lag for certain dimensions (e.g. traffic sources, retention curves).
- **Mitigation:** 1h/6h snapshots pull real-time data from `videos().list(part='statistics')`, while 24h/7d snapshots pull granular data from `youtubeAnalytics.reports().query(...)`.

### 18. Analytics limitations:
- First-hour subscriber changes may be too small ($< 5$) to calculate statistically significant conversion rates without sufficient view volume.

### 19. Failure/retry weaknesses:
- If network drops during YouTube upload or analytics fetch, exponential backoff is required to avoid infinite retry storms.

### 20. Duplicate upload risks:
- **Zero Risk:** Both `upload_video.py` and `uploader.py` feature strict idempotency checks against `metadata.json` and `.manifest.json`.

### 21. Duplicate topic risks:
- **Zero Risk:** `deduplicator.py` filters candidates with token Jaccard similarity $\ge 0.65$ against published history.

### 22. Experiment contamination risks:
- If multiple variables change at once (e.g., changing both hook and duration simultaneously), causal attribution fails.
- **Mitigation:** Enforce single-variable experiment registry.

### 23. Cross-channel contamination risks:
- **Zero Risk:** Separate database channel foreign keys, independent topic pools, and strict pre-upload channel identity check.

### 24. Database migration risks:
- Schema updates must use non-destructive `CREATE TABLE IF NOT EXISTS` and versioned migration scripts.

### 25. Unverified assumptions:
- Assumes YouTube Analytics API access will be granted for the authenticated accounts. If scopes are missing, system must gracefully fall back to `videos().list` statistics and mock simulation.
