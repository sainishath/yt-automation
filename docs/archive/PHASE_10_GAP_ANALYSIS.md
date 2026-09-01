# Phase 10: Production Experiment Execution + Performance Ingestion
## Pre-Implementation Gap Analysis & Engineering Plan

---

### 1. What Phase 9 Already Provides
1. **Experiment Registry & Schema:**
   - Table `experiments` with full hypothesis contracts, provenance, bounded prior weight ($\le 0.25$), $N \ge 4$ sample guards, single-variable validation, and evaluation columns.
   - Table `experiment_arms` storing individual `CONTROL` and `TREATMENT` arms.
2. **First-Party Dominance & Outcome Engine:**
   - `evaluate_and_apply_dominance()` enforces First-Party Dominance: when $N \ge 4$ test produces $\le -5.0\%$ delta, linked external prior is set to `REJECTED`, `prior_weight = 0.0`, and override reason is recorded.
   - When delta is $\ge +5.0\%$, prior is set to `SUPPORTED` and a `STRATEGY_PROPOSAL` learning event is emitted.
3. **Queue & Lineage Foundation:**
   - `ExperimentQueue` filters ready experiments by channel with single-variable conflict prevention.
   - `ExperimentLineageTracker` builds end-to-end audit trace.
   - `generate_experiment_status_report()` generates `EXPERIMENT_STATUS_REPORT.md`.

---

### 2. What Phase 10 Partially Provides & Existing Interfaces
1. **Production Pipeline Interfaces:**
   - **Pipeline 1 (`alternate-history-shorts/`):** `run_pipeline1(topic, video_id, ...)` generates `run_manifest.json` and `metadata.json`, runs RAG v4 grounding, TTS, Whisper alignment, SDXL image generation, video assembly, QA gate (17/17), and Discord review.
   - **Pipeline 2 (`convo-shorts/`):** Dual Piper voices, dynamic subtitles, gameplay backgrounds, QA gate (16/16), and Discord review.
2. **Snapshot Infrastructure:**
   - `growth/analytics/collector.py` and `growth/analytics/snapshot_scheduler.py` define the 6 canonical windows (1h, 6h, 24h, 48h, 7d, 28d) and query `YouTubeApiCollector`.

---

### 3. Exact Missing Links to Close in Phase 10

| Area | Existing State | Missing Link in Phase 10 | Solution |
|---|---|---|---|
| **1. Sample Balancing** | Simple alternating assignment by sequence number. | Dynamic cohort balancing based on actual published sample counts per arm (`control_count` vs `treatment_count`). | Update `ExperimentQueue` to inspect real arm sample counts and prioritize the lagging arm until $N=4$ is reached on both. |
| **2. Experiment Satiation Guard** | Saturated experiments ($N \ge 4$ on both arms) could continue receiving jobs. | Saturated experiments must transition to `COLLECTING_DATA` / `EVALUATED` and yield the queue to the next waiting experiment. | In `ExperimentQueue`, check if `control_count >= min_sample and treatment_count >= min_sample`. If so, mark ready for evaluation and skip. |
| **3. Production Job Adapter** | `ContentPlanner` output dict had `experiment_id` and `arm_id`, but no direct integration helper to register jobs in `growth.db` and inject into pipeline manifests. | `JobDispatcher` / `ProductionJobAdapter` creating verified `JobModel` records and attaching experiment metadata to `run_manifest.json`. | Add `ProductionJobAdapter` creating deterministic `JobModel` and metadata injection for Pipeline 1 and Pipeline 2. |
| **4. Control vs Treatment Mapping** | Treatment definitions were descriptive strings. | Need exact parameter mapping per variable (`HOOK_STRUCTURE` $\to$ hook prompt parameter; `TOPIC_CLUSTER` $\to$ topic pool filter). | Audit and document exact production parameter modifications for all 4 registered experiments. |
| **5. Due Window Enforcement & Zero Fake Data** | `SnapshotScheduler` checked `elapsed >= win_delta`, but needed robust tolerance handling and explicit `SNAPSHOT_PENDING` / `ANALYTICS_UNAVAILABLE` when YouTube Data API or Analytics API is unavailable. | Ensure real production snapshots NEVER fabricate simulated numbers in production tables. | Hard guard in `YouTubeApiCollector` returning `ANALYTICS_PENDING` or real Data API stats when live API is queried. |
| **6. Upload Sample Accounting** | Upload callback needed idempotent sample count incrementing. | Ensure duplicate upload callbacks cannot increment the same arm sample count twice. | Check if `video_id` has already been recorded as `UPLOADED_PUBLIC` before incrementing `arm.sample_count`. |
| **7. REST API & CLI Execution** | Basic list and evaluate commands existed. | Missing `--approve-experiment <id>`, `--next-experiment-job <channel>`, `--register-upload`, `--snapshot-status`. | Add the missing execution and management endpoints to `growth/server.py` and `growth/cli.py`. |

---

### 4. Control vs Treatment Audit for Registered Experiments

#### Channel A: `exp_channel_a_hook_structure_counterfactual_question_v1`
- **Variable Isolated:** `HOOK_STRUCTURE`
- **Control Arm:** Standard Chronos Shift Question Hook (e.g. *"What if the Roman Empire never fell?"*)
- **Treatment Arm:** RAG v4 grounded counterfactual question hook with Whisper-aligned visual beat (e.g. *"In 476 AD, Rome didn't collapse. Instead, Emperor Zeno unified the legions..."*)
- **Parameter Injected:** `script_hook_template` / `hook_style` in `generate_script.py`.
- **Invariance Guard:** Topic, SDXL prompt style, motion speed (8% Ken Burns), voice (Edge-TTS ChristopherNeural), and duration (45s) remain constant.

#### Channel A: `exp_channel_a_topic_cluster_modern_warfare_and_geopolitical_divergence_v1`
- **Variable Isolated:** `TOPIC_CLUSTER`
- **Control Arm:** General Alternate History turning points pool.
- **Treatment Arm:** Prioritized Modern Warfare & Geopolitical Divergence cluster (e.g. Cold War 1962, WW2 divergence).
- **Parameter Injected:** Topic candidate selection in `TopicPoolManager`.
- **Invariance Guard:** Script structure, visual pipeline, and assembly remain constant.

#### Channel B: `exp_channel_b_hook_structure_socratic_question_v1`
- **Variable Isolated:** `HOOK_STRUCTURE`
- **Control Arm:** Standard Debate Protocol Neutral Opening.
- **Treatment Arm:** Socratic Provocation Question Opening with immediate Host A vs Host B tension.
- **Parameter Injected:** Opening dialogue turn in `convo-shorts` script template.
- **Invariance Guard:** Dual Piper voices, subtitle styles, and gameplay background remain constant.

#### Channel B: `exp_channel_b_topic_cluster_ai_ethics_and_future_dilemmas_v1`
- **Variable Isolated:** `TOPIC_CLUSTER`
- **Control Arm:** General Psychology / Curiosity pool.
- **Treatment Arm:** AI Ethics & Future Dilemmas pool.
- **Parameter Injected:** Topic candidate selection in `TopicPoolManager`.
- **Invariance Guard:** Dialogue structure and video formatting remain constant.

---

### 5. Implementation Order

1. **Step 1: Experiment Queue & Sample Balancing Engine (`growth/experiments/experiment_queue.py`):**
   - Enhance `select_experiment_for_topic` with real sample balancing (`control_count` vs `treatment_count`).
   - Add completion/satiation checks ($N \ge 4$ on both arms $\to$ advance to `EVALUATED` / `COLLECTING_DATA`).
   - Add `approve_experiment()` and `transition_experiment()` methods.
2. **Step 2: Production Job Adapter & Metadata Carrier (`growth/experiments/production_adapter.py`):**
   - Create `ProductionJobAdapter` creating deterministic `JobModel` instances with `experiment_id`, `arm_id`, `arm_type`, `topic_id`, `channel_id`, `strategy_version`.
   - Injects experiment metadata into pipeline manifests (`run_manifest.json`, `metadata.json`).
3. **Step 3: Sample Accounting & Upload Registration (`growth/experiments/sample_tracker.py`):**
   - Ensure upload callbacks idempotently register real YouTube uploads, record `youtube_video_id`, and increment arm sample counts exactly once.
   - Enforce that Discord-rejected videos never increment sample counts.
4. **Step 4: Real Performance Ingestion & Snapshot Scheduler Hardening (`growth/analytics/`):**
   - Ensure snapshot windows are strictly enforced by elapsed time.
   - Ensure missing API credentials record `SNAPSHOT_PENDING` / `ANALYTICS_UNAVAILABLE` without fabricating fake metrics.
5. **Step 5: REST API & CLI Extensions (`growth/server.py`, `growth/cli.py`):**
   - Add `--approve-experiment`, `--next-experiment-job`, `--register-upload`, `--snapshot-status`.
   - Add REST endpoints `POST /api/growth/experiments/approve`, `POST /api/growth/jobs/create-experiment-job`.
6. **Step 6: Dedicated Test Suite (`growth/tests/test_phase10_production_execution.py`):**
   - 25+ unit tests verifying all 25 Phase 10 test conditions.
7. **Step 7: Production Dry-Run & Verification:**
   - Execute complete dry-run on live database.
   - Run `python growth/run_growth_tests.py` and `python verify_release.py`.
   - Generate `PHASE_10_PRODUCTION_EXECUTION_IMPLEMENTATION_REPORT.md`.
