-- schema.sql: Growth & Content Intelligence Database Schema

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

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
    UNIQUE(video_id, window_name),
    FOREIGN KEY(video_id) REFERENCES videos(video_id)
);

CREATE TABLE IF NOT EXISTS topic_candidates (
    topic_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    topic_text TEXT NOT NULL,
    category TEXT NOT NULL,
    cluster TEXT,
    score REAL DEFAULT 0.0,
    score_breakdown TEXT, -- JSON
    status TEXT NOT NULL, -- 'DISCOVERED', 'SCORED', 'QUEUED', 'ASSIGNED', 'PRODUCED', 'PUBLISHED', 'MEASURED', 'LEARNED', 'ARCHIVED'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(channel_id) REFERENCES channels(channel_id)
);

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

CREATE TABLE IF NOT EXISTS learning_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT NOT NULL,
    event_type TEXT NOT NULL, -- 'WEEKLY_REPORT', 'AUTOPSY', 'STRATEGY_PROPOSAL', 'STRATEGY_MUTATION'
    summary TEXT NOT NULL,
    details TEXT,
    confidence TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(channel_id) REFERENCES channels(channel_id)
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    pipeline_id TEXT NOT NULL,
    video_id TEXT,
    topic_text TEXT NOT NULL,
    status TEXT NOT NULL, -- 'PLANNED', 'GENERATING', 'GENERATED', 'QA_FAILED', 'AWAITING_REVIEW', 'REJECTED', 'APPROVED', 'UPLOADING', 'PUBLISHED', 'ANALYTICS_PENDING', 'COMPLETED', 'FAILED', 'RETRY_PENDING'
    strategy_version TEXT,
    experiment_id TEXT,
    variant_id TEXT,
    error_message TEXT,
    attempt_count INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(channel_id) REFERENCES channels(channel_id)
);
