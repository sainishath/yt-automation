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
    secondary_metrics TEXT, -- JSON array
    min_sample_size INTEGER DEFAULT 4,
    target_sample_size INTEGER DEFAULT 4,
    source_type TEXT DEFAULT 'FIRST_PARTY_DISCOVERY', -- 'EXTERNAL_PRIOR', 'FIRST_PARTY_DISCOVERY', 'GENERAL_HEURISTIC'
    underlying_principle TEXT,
    status TEXT NOT NULL, -- 'PROPOSED', 'APPROVED', 'SCHEDULED', 'RUNNING', 'COLLECTING_DATA', 'EVALUATED', 'ACCEPTED', 'REJECTED', 'INCONCLUSIVE', 'CANCELLED'
    result TEXT,
    confidence TEXT,
    external_pattern_id TEXT,
    external_prior_id TEXT,
    source_channels TEXT, -- JSON array or comma-separated
    transferability_score REAL,
    transferability_classification TEXT,
    prior_weight REAL,
    provenance TEXT DEFAULT 'FIRST_PARTY', -- 'FIRST_PARTY', 'EXTERNAL_INTELLIGENCE', 'SIMULATION'
    rationale TEXT,
    decision TEXT,
    decision_reason TEXT,
    delta_percentage REAL,
    control_count INTEGER DEFAULT 0,
    treatment_count INTEGER DEFAULT 0,
    control_median REAL,
    treatment_median REAL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    evaluated_at TIMESTAMP,
    first_party_override_status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(channel_id) REFERENCES channels(channel_id),
    FOREIGN KEY(external_pattern_id) REFERENCES external_patterns(pattern_id),
    FOREIGN KEY(external_prior_id) REFERENCES external_priors(prior_id)
);

CREATE TABLE IF NOT EXISTS experiment_arms (
    arm_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    arm_type TEXT NOT NULL, -- 'CONTROL', 'TREATMENT'
    name TEXT NOT NULL,
    definition TEXT NOT NULL,
    sample_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'ACTIVE', -- 'ACTIVE', 'PAUSED', 'COMPLETED'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(experiment_id) REFERENCES experiments(experiment_id)
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
    event_type TEXT NOT NULL, -- 'WEEKLY_REPORT', 'AUTOPSY', 'STRATEGY_PROPOSAL', 'STRATEGY_MUTATION', 'FIRST_PARTY_OVERRIDE', 'EXPERIMENT_COMPLETED'
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
    topic_id TEXT,
    topic_text TEXT NOT NULL,
    status TEXT NOT NULL, -- 'PLANNED', 'GENERATING', 'GENERATED', 'QA_FAILED', 'AWAITING_REVIEW', 'REJECTED', 'APPROVED', 'UPLOADING', 'PUBLISHED', 'ANALYTICS_PENDING', 'COMPLETED', 'FAILED', 'RETRY_PENDING'
    strategy_version TEXT,
    experiment_id TEXT,
    arm_id TEXT,
    variant_id TEXT,
    error_message TEXT,
    attempt_count INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(channel_id) REFERENCES channels(channel_id),
    FOREIGN KEY(experiment_id) REFERENCES experiments(experiment_id),
    FOREIGN KEY(arm_id) REFERENCES experiment_arms(arm_id)
);

CREATE INDEX IF NOT EXISTS idx_experiments_channel ON experiments(channel_id);
CREATE INDEX IF NOT EXISTS idx_experiments_status ON experiments(status);
CREATE INDEX IF NOT EXISTS idx_experiment_arms_exp ON experiment_arms(experiment_id);
CREATE INDEX IF NOT EXISTS idx_videos_exp ON videos(experiment_id);
CREATE INDEX IF NOT EXISTS idx_jobs_exp ON jobs(experiment_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_vid ON performance_snapshots(video_id);


-- ── External Intelligence Tables ──────────────────────────────────────────

CREATE TABLE IF NOT EXISTS external_channels (
    external_channel_id TEXT PRIMARY KEY,
    target_channel_id TEXT NOT NULL, -- 'channel_a' or 'channel_b'
    channel_title TEXT NOT NULL,
    handle TEXT,
    youtube_channel_id TEXT,
    subscriber_count INTEGER DEFAULT 0,
    video_count INTEGER DEFAULT 0,
    content_niche TEXT NOT NULL,
    similarity_score REAL DEFAULT 0.0,
    similarity_reasons TEXT, -- JSON array
    confidence TEXT DEFAULT 'HIGH', -- 'HIGH', 'MEDIUM', 'LOW'
    is_simulation INTEGER DEFAULT 0, -- 0 for real public data, 1 for simulation
    source_type TEXT NOT NULL, -- 'PUBLIC_YOUTUBE', 'SIMULATION'
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_researched_at TIMESTAMP,
    FOREIGN KEY(target_channel_id) REFERENCES channels(channel_id)
);

CREATE TABLE IF NOT EXISTS external_videos (
    external_video_id TEXT PRIMARY KEY,
    external_channel_id TEXT NOT NULL,
    youtube_video_id TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    published_at TIMESTAMP,
    duration_seconds REAL DEFAULT 0.0,
    is_short INTEGER DEFAULT 1,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    relative_view_multiplier REAL DEFAULT 1.0, -- Normalized to channel median
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_simulation INTEGER DEFAULT 0,
    source_type TEXT NOT NULL, -- 'PUBLIC_YOUTUBE', 'SIMULATION'
    FOREIGN KEY(external_channel_id) REFERENCES external_channels(external_channel_id)
);

CREATE TABLE IF NOT EXISTS external_observations (
    observation_id TEXT PRIMARY KEY,
    external_video_id TEXT NOT NULL,
    observation_type TEXT NOT NULL, -- 'OBJECTIVE_FACT', 'INTERPRETATION'
    field_name TEXT NOT NULL,
    observed_value TEXT NOT NULL,
    interpretation TEXT,
    evidence_level TEXT NOT NULL, -- 'OBSERVATION', 'EXTERNAL_EVIDENCE'
    confidence REAL DEFAULT 1.0,
    is_simulation INTEGER DEFAULT 0,
    source_type TEXT NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(external_video_id) REFERENCES external_videos(external_video_id)
);

CREATE TABLE IF NOT EXISTS external_evidence (
    evidence_id TEXT PRIMARY KEY,
    target_channel_id TEXT NOT NULL,
    pattern_type TEXT NOT NULL,
    claim_summary TEXT NOT NULL,
    supporting_channel_count INTEGER DEFAULT 0,
    supporting_video_count INTEGER DEFAULT 0,
    performance_evidence TEXT, -- JSON summary of baseline multiples
    confidence REAL DEFAULT 0.0,
    is_simulation INTEGER DEFAULT 0,
    source_type TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(target_channel_id) REFERENCES channels(channel_id)
);

CREATE TABLE IF NOT EXISTS external_patterns (
    pattern_id TEXT PRIMARY KEY,
    target_channel_id TEXT NOT NULL,
    pattern_type TEXT NOT NULL, -- 'HOOK_STRUCTURE', 'TOPIC_CLUSTER', 'NARRATIVE_FLOW', 'CTA_FORMAT'
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    surface_technique TEXT NOT NULL,
    underlying_principle TEXT NOT NULL,
    our_possible_implementation TEXT NOT NULL,
    frequency REAL DEFAULT 0.0,
    channel_count INTEGER DEFAULT 0,
    video_count INTEGER DEFAULT 0,
    supporting_observations TEXT, -- JSON list of observation IDs
    consistency_score REAL DEFAULT 0.0,
    confidence REAL DEFAULT 0.0,
    is_simulation INTEGER DEFAULT 0,
    source_type TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(target_channel_id) REFERENCES channels(channel_id)
);

CREATE TABLE IF NOT EXISTS transferability_scores (
    transferability_id TEXT PRIMARY KEY,
    pattern_id TEXT NOT NULL,
    target_channel_id TEXT NOT NULL,
    topic_similarity REAL NOT NULL,
    audience_similarity REAL NOT NULL,
    format_similarity REAL NOT NULL,
    production_similarity REAL NOT NULL,
    evidence_strength REAL NOT NULL,
    repeatability REAL NOT NULL,
    overall_transferability_score REAL NOT NULL,
    classification TEXT NOT NULL, -- 'HIGH', 'MEDIUM', 'LOW', 'DO_NOT_TRANSFER'
    reason TEXT NOT NULL,
    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(pattern_id) REFERENCES external_patterns(pattern_id),
    FOREIGN KEY(target_channel_id) REFERENCES channels(channel_id)
);

CREATE TABLE IF NOT EXISTS external_priors (
    prior_id TEXT PRIMARY KEY,
    target_channel_id TEXT NOT NULL,
    pattern_id TEXT NOT NULL,
    hypothesis TEXT NOT NULL,
    transferability_classification TEXT NOT NULL,
    prior_weight REAL DEFAULT 0.20, -- Bounded influence (max 0.30)
    status TEXT NOT NULL, -- 'HYPOTHESIS', 'TESTING', 'SUPPORTED', 'REJECTED', 'EXPIRED'
    first_party_override_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    review_by TIMESTAMP,
    FOREIGN KEY(target_channel_id) REFERENCES channels(channel_id),
    FOREIGN KEY(pattern_id) REFERENCES external_patterns(pattern_id)
);

CREATE TABLE IF NOT EXISTS research_runs (
    run_id TEXT PRIMARY KEY,
    target_channel_id TEXT NOT NULL,
    channels_scanned INTEGER DEFAULT 0,
    videos_analyzed INTEGER DEFAULT 0,
    patterns_discovered INTEGER DEFAULT 0,
    priors_generated INTEGER DEFAULT 0,
    status TEXT NOT NULL, -- 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'PARTIAL'
    error_message TEXT,
    is_simulation INTEGER DEFAULT 0,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY(target_channel_id) REFERENCES channels(channel_id)
);
