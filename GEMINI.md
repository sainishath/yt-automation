# Project Antigravity Rules — YouTube Automations

## 1. Dual-Pipeline Architecture & Strict Isolation
- **Pipeline 1 (`alternate-history-shorts` / Channel A / Chronos Shift):**
  - Must always be invoked via `alternate-history-shorts/scripts/pipeline_runner.py`.
  - 100% full-screen 9:16 cinematic SDXL visuals with Ken-Burns pan/zoom movement.
  - Zero Minecraft or gameplay footage.
  - Narrator: Single authoritative documentary voice (`en-US-ChristopherNeural`, Edge-TTS) with orchestral BGM.
  - Discord Review Webhook: `1528622690980724807`.
- **Pipeline 2 (`convo-shorts` / Channel B / Debate Protocol):**
  - Must always be invoked via `convo-shorts/yt-automation-engine/main.py`.
  - Full-screen retentive gameplay background (Minecraft/Subway Surfers) with centered upper-zone 896x896 Fooocus image overlays & syntax-highlighted code cards.
  - Senior Technical Narrator voice (`en_US-ryan-medium.onnx` / Piper TTS) with multi-angle concept generation (`growth/brain/p2_multi_angle.py`).
  - Discord Review Webhook: `1528609697089982494`.
- **Strict Invariant:** Neither pipeline shall ever import, call, or share video assembly wrappers from the other.

## 2. Image Generation & Fooocus SDXL Invariant
- All visual scenes and overlays MUST be generated using local Fooocus SDXL on `http://127.0.0.1:7865`.
- **Zero External Image API Calls:** Never fall back to external APIs (Gemini/Nano/Banana/DALL-E) or consume cloud image API keys.
- If local Fooocus is unavailable, halt production immediately and prompt the user to ensure the local Fooocus service or Docker container is active on port 7865.

## 3. Human Gate & Discord Review Approval
- Every video generation must pass multi-axis QA (17/17 for Channel A, 16/16 for Channel B) and generate a `540x960` proxy.
- Proxies must be posted to the channel's respective Discord webhook.
- Never upload videos to YouTube automatically without explicit Discord human approval or direct user confirmation.

## 4. Empirical Growth Intelligence ($N \ge 4$)
- First-party empirical metrics strictly dominate external priors.
- Strategy promotions and experiment decisions require $N \ge 4$ mature samples per arm (7-day maturity).

## 5. External Intelligence & ML Feature Matrix Standards
- **Relational Excel Corpus as Source Evidence:** Multi-sheet workbooks (`CHANNELS`, `VIDEOS`, `TRANSCRIPTS`, `CONTENT_ANALYSIS`, `PERFORMANCE`, `SOURCES`) serve as immutable evidence. Programmatic transformations convert them into ML feature matrices (`.csv`, `.parquet`) via Python.
- **Strict Target Leakage Guard:**
  - Model inputs (`feat_*`) must contain only signals that would have been available at the defined prediction time.
  - This includes script lexical statistics, hook/explanation encodings, duration, visual style, and channel-size information when temporally eligible.
  - Performance metrics (`views`, `relative_views`, `performance_class`) are strictly designated as supervised targets (`target_*`) or independent audit annotations (`annot_*`).
  - Researcher classifications (`annot_researcher_class`) must never be used as predictive features.
  - Derived features must be audited for indirect temporal or target leakage; the `feat_*` namespace alone does not make a feature prediction-safe.
- **Zero Fabrication & Quarantine Provenance:**
  - Non-canonical surrogate IDs or unresolvable endpoints must be preserved in quarantine tables with explicit rejection reasons.
  - Never fabricate or guess 11-character YouTube video IDs.
  - Repaired identifiers must have explicit public provenance and must not silently overwrite the original researcher-provided value.
