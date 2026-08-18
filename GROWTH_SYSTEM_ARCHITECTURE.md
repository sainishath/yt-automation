# Growth & Content Intelligence Architecture Specification

---

## 🏛️ 1. Directory Structure

The content intelligence system is organized inside `growth/` to keep production generation decoupled from analytics and learning:

```text
growth/
├── README.md
├── db/
│   ├── schema.sql
│   ├── database.py
│   └── models.py
├── channels/
│   ├── pipeline1_channel.json
│   ├── pipeline2_channel.json
│   └── channel_identity_check.py
├── analytics/
│   ├── collector.py
│   ├── normalizer.py
│   └── mock_data_generator.py
├── features/
│   ├── feature_extractor_p1.py
│   ├── feature_extractor_p2.py
│   └── schema.py
├── topic_engine/
│   ├── topic_scorer.py
│   ├── topic_pool.py
│   └── deduplicator.py
├── strategy/
│   ├── strategy_manager.py
│   ├── channel_a_strategy_v1.json
│   └── channel_b_strategy_v1.json
├── experiments/
│   ├── experiment_manager.py
│   └── registry.py
├── learning/
│   ├── learning_engine.py
│   ├── report_generator.py
│   └── autopsy_analyzer.py
├── planner/
│   └── content_planner.py
└── tests/
    ├── test_db.py
    ├── test_analytics.py
    ├── test_features.py
    ├── test_topic_engine.py
    ├── test_strategy.py
    ├── test_experiments.py
    ├── test_learning_engine.py
    └── test_channel_identity.py
```

---

## 🗄️ 2. Database Schema Specification (`growth.db`)

```sql
-- Channels Table
CREATE TABLE IF NOT EXISTS channels (
    channel_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    handle TEXT NOT NULL,
    pipeline_id TEXT NOT NULL,
    content_category TEXT NOT NULL,
    audience_definition TEXT,
    posting_frequency TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Videos Table
CREATE TABLE IF NOT EXISTS videos (
    video_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    pipeline_id TEXT NOT NULL,
    topic_id TEXT,
    title TEXT NOT NULL,
    description TEXT,
    duration REAL NOT NULL,
    youtube_video_id TEXT,
    youtube_url TEXT,
    upload_status TEXT NOT NULL,
    privacy_status TEXT NOT NULL,
    qa_score REAL,
    review_status TEXT NOT NULL,
    strategy_version TEXT NOT NULL,
    experiment_id TEXT,
    variant_id TEXT,
    generation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    publish_timestamp TIMESTAMP,
    FOREIGN KEY(channel_id) REFERENCES channels(channel_id)
);

-- Video Features Table
CREATE TABLE IF NOT EXISTS video_features (
    video_id TEXT PRIMARY KEY,
    topic_category TEXT,
    hook_type TEXT,
    hook_score REAL,
    hook_text TEXT,
    word_count INTEGER,
    scene_count INTEGER,
    avg_scene_duration REAL,
    visual_change_rate REAL,
    motion_type TEXT,
    motion_intensity REAL,
    caption_density REAL,
    narrative_structure TEXT,
    speaker_balance REAL,
    turn_count INTEGER,
    controversy_level REAL,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(video_id) REFERENCES videos(video_id)
);

-- Performance Snapshots Table (Time Series)
CREATE TABLE IF NOT EXISTS performance_snapshots (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT NOT NULL,
    window_name TEXT NOT NULL, -- '1h', '6h', '24h', '48h', '7d', '28d'
    snapshot_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    subscribers_gained INTEGER DEFAULT 0,
    watch_time_minutes REAL DEFAULT 0.0,
    avg_view_duration_seconds REAL DEFAULT 0.0,
    avg_percentage_viewed REAL DEFAULT 0.0,
    views_per_hour REAL DEFAULT 0.0,
    engagement_rate REAL DEFAULT 0.0,
    subscriber_conversion_rate REAL DEFAULT 0.0,
    relative_performance_score REAL DEFAULT 0.0,
    data_source TEXT NOT NULL, -- 'YOUTUBE_API' or 'MOCK_ENGINE'
    data_freshness TEXT NOT NULL,
    FOREIGN KEY(video_id) REFERENCES videos(video_id)
);

-- Topic Candidates Table
CREATE TABLE IF NOT EXISTS topic_candidates (
    topic_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    topic_text TEXT NOT NULL,
    category TEXT NOT NULL,
    cluster TEXT,
    score REAL DEFAULT 0.0,
    score_breakdown TEXT, -- JSON breakdown
    status TEXT NOT NULL, -- 'candidate', 'approved', 'generated', 'published', 'retired'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(channel_id) REFERENCES channels(channel_id)
);

-- Experiments Table
CREATE TABLE IF NOT EXISTS experiments (
    experiment_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    name TEXT NOT NULL,
    hypothesis TEXT NOT NULL,
    variable_tested TEXT NOT NULL,
    control_definition TEXT NOT NULL,
    variant_definition TEXT NOT NULL,
    primary_metric TEXT NOT NULL,
    min_sample_size INTEGER DEFAULT 10,
    status TEXT NOT NULL, -- 'PROPOSED', 'ACTIVE', 'COMPLETED', 'REJECTED'
    result TEXT,
    confidence TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(channel_id) REFERENCES channels(channel_id)
);

-- Strategy Versions Table
CREATE TABLE IF NOT EXISTS strategy_versions (
    version_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    version_number TEXT NOT NULL,
    strategy_payload TEXT NOT NULL, -- JSON config
    change_summary TEXT,
    approval_status TEXT NOT NULL, -- 'PROPOSED', 'ACTIVE', 'SUPERSEDED'
    activated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(channel_id) REFERENCES channels(channel_id)
);

-- Learning Events Table
CREATE TABLE IF NOT EXISTS learning_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT NOT NULL,
    event_type TEXT NOT NULL, -- 'WEEKLY_REPORT', 'AUTOPSY', 'STRATEGY_PROPOSAL'
    summary TEXT NOT NULL,
    details TEXT,
    confidence TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(channel_id) REFERENCES channels(channel_id)
);
```

---

## 🔄 3. Closed-Loop Execution Flow

1. **Topic Generation & Ranking (`topic_engine`):**  
   Pulls from topic candidate pool; scores each topic using multi-factor equation (audience fit, past cluster performance, novelty, fact-check difficulty).
2. **Strategy Context Injection (`strategy`):**  
   Selects active strategy version (`strategy_v1.0`) and checks active experiment queue (e.g., question hook vs counterfactual statement).
3. **Execution via Frozen Pipelines:**  
   Calls `http://127.0.0.1:8000` (P1) or `http://127.0.0.1:5001` (P2) with topic & parameters.
4. **Feature Extraction (`features`):**  
   Parses `metadata.json`, `qa_report.json`, Whisper timings, and prompts into structured database features.
5. **Publishing & Identity Verification (`channels`):**  
   `channel_identity_check.py` verifies OAuth token channel ID against destination channel. Discord review gate requires explicit approval.
6. **Analytics Collection (`analytics`):**  
   Gathers snapshots at 1h, 6h, 24h, 48h, 7d, 28d; normalizes performance against recent channel medians.
7. **Learning & Strategy Refinement (`learning`):**  
   Evaluates A/B experiment variants; writes weekly learning reports and proposes versioned strategy updates.
