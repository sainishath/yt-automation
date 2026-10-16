# System Overhaul Specification — YouTube Automations High-Retention Architecture

## 1. System Invariants & Model Routing Topology
- **Creative Reasoning & Script Synthesis (`generate_script.py`, `media_engine.py`, `p2_multi_angle.py`):**
  - Primary Model: `gemma4:31b-cloud` via local Ollama (`http://127.0.0.1:11434`).
  - Fallback Model: `qwen2.5-coder:7b` (auto-fallback if primary unavailable or times out).
- **Structured JSON & Extraction (`visual_scene_planner.py`, `generate_metadata.py`, `metadata_generator.py`, `script_critic.py`):**
  - Model: `qwen2.5-coder:7b` with deterministic temperature (0.1–0.2).
- **Lightweight Fallback:** `llama3.2:latest` reserved strictly for offline/emergency fallback.
- **Visual Synthesis & Hardware Invariant:**
  - Fooocus SDXL at `D:\AI-Tools\Fooocus` on `http://127.0.0.1:7865` (zero cloud image APIs).

## 2. Script & Narrative Architecture: "Butterfly Effect Cascades"
- **Pacing & Word Count:**
  - Speech rate target: 2.8–3.2 words per second (WPS).
  - Target spoken word count: 95–108 words across 32–36 seconds.
- **Strict 4-Part Structure:**
  1. **0–3s Shock Hook:** In media res with hyper-specific paradoxical future outcome + exact year. Banned: repeating the title question as the first sentence.
  2. **3–10s Historical Anchor (Point of Divergence):** Exact historical person, battle, or invention cited directly from RAG grounding evidence.
  3. **10–28s Concrete Domino Chain:** 3 cascading counterfactual consequences with named dates, technologies, borders, or rulers. Banned: vague filler ("thrived", "beacon of learning", "new heights", "endured").
  4. **28–35s Debate Loop Hook:** Divisive, comment-driving question syntactically looping into opening frame.
- **RAG & Critic Grounding Invariant:**
  - Fact-check ONLY the Point of Divergence / Historical Anchor against RAG evidence.
  - Grade downstream counterfactual scenes on **specificity density** (density of concrete nouns, dates, named mechanisms) rather than penalizing speculative claims.

## 3. Acoustic & Audio Engineering Contracts
- **TTS Synthesis:** Edge-TTS speech rate configured to `+18%` (`--rate=+18%`).
- **Dead-Air Removal:** FFmpeg filter stripping inter-sentence pauses > 180ms:
  `silenceremove=stop_periods=-1:stop_duration=0.18:stop_threshold=-40dB:leave_silence=0.06`
- **Master Audio Normalization:** Broadcast-standard `loudnorm=I=-14:TP=-1.5:LRA=11`.
- **QA Loudness Gate (`qa_gate.py`):** `mean_volume_db` must be between `-18.0 dB` and `-12.0 dB` (failing inaudible audio like `-29.3 dB`).

## 4. Visual Direction & Beat Pacing Contracts
- **Beat Density:**
  - Visual cut every 2.0–2.5 seconds during the initial 6-second hook window.
  - Total beat count: minimum 10–12 visual beats per 35-second Short.
- **Framing Diversity:**
  - Dynamic cycling across: `extreme close-up portrait`, `overhead strategic war map`, `low-angle architectural shot`, `dramatic over-the-shoulder`.
  - Strict ban on repeating `"Wide-angle documentary shot of..."` on consecutive beats.

## 5. Database Hygiene & Operational Queue
- **Purge Invariant:** Delete `is_simulation=1` and `SIMULATED_BENCHMARK` rows from `growth.db`.
- **Stuck Jobs Reset:** Reset 8 orphaned `GENERATING` jobs to `FAILED_RESET` or `PLANNED`.
- **Review Queue Management CLI:** Single unified CLI tool (`growth/manage_queue.py`) to batch-review, re-render, or schedule the 12 `AWAITING_REVIEW` videos (1 Short/day cadence).
