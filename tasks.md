# Executable Task Checklist — YouTube Automations Overhaul

## Phase 1: Environment & Virtualenv Setup
- [x] Task 1.1: Create `.venv` with `--system-site-packages` using Python 3.11 and verify CUDA/Torch/whisper imports.
- [x] Task 1.2: Verify local Ollama daemon and models (`gemma4:31b-cloud`, `qwen2.5-coder:7b`, `llama3.2:latest`, `qwen2.5vl:7b`).

## Phase 2: Model Routing Upgrade
- [x] Task 2.1: Update Ollama model routing in `alternate-history-shorts/scripts/generate_script.py` and `generate_metadata.py` to use `gemma4:31b-cloud` (with fallback to `qwen2.5-coder:7b`) for scripts, and `qwen2.5-coder:7b` for metadata.
- [x] Task 2.2: Update Ollama model routing in `convo-shorts/yt-automation-engine/media_engine.py`, `metadata_generator.py`, and `growth/brain/p2_multi_angle.py`.
- [x] Task 2.3: Update Ollama model routing in `growth/brain/script_critic.py` to `qwen2.5-coder:7b`.

## Phase 3: High-Retention Butterfly Effect Script & Specificity RAG
- [x] Task 3.1: Rewrite script generation prompt in `generate_script.py` to enforce the 4-part structure (Shock Hook in media res, Historical Anchor, 3-part Concrete Domino Chain, Debate Loop Hook).
- [x] Task 3.2: Update claim verification in `generate_script.py` & `rag_grounding.py` to fact-check ONLY the historical anchor and score counterfactuals on specificity density.
- [x] Task 3.3: Update `growth/brain/script_critic.py` to score specificity density and adjust speech rate benchmark to 2.8 WPS for history.

## Phase 4: Audio Engineering Overhaul (-14 LUFS, Tight Pacing)
- [x] Task 4.1: Update `generate_audio.py` with `--rate=+18%` and inter-sentence dead-air removal via `silenceremove`.
- [x] Task 4.2: Update `assemble_video.py` audio mixing pipeline with master `loudnorm=I=-14:TP=-1.5:LRA=11`.
- [x] Task 4.3: Update `qa_gate.py` to fail audio outside `-18.0 dB` to `-12.0 dB` mean volume.

## Phase 5: Accelerated Visual Pacing & Framing Variety
- [x] Task 5.1: Update `visual_scene_planner.py` to enforce 2.0–2.5s cuts in first 6 seconds (10–12 beats total) and diverse framing angles.

## Phase 6: Database Hygiene & Queue Management CLI
- [x] Task 6.1: Purge `is_simulation=1` and `SIMULATED_BENCHMARK` records from `growth.db` and reset stuck `GENERATING` jobs.
- [x] Task 6.2: Build CLI script `growth/manage_queue.py` to batch-review, re-render, or schedule the 12 `AWAITING_REVIEW` videos at 1 Short/day.

## Phase 7: Verification Gate
- [x] Task 7.1: Re-render "What if the Roman Empire never fell?" end-to-end with `--no_fallback`.
- [x] Task 7.2: Verify `script.json` (4-part dominoes), `scene_plan.json` (10+ beats, diverse shots), and `qa_report.json` (loudness -14 LUFS / 17 checks pass).

## Phase 8: Quality Feedback & Production Polish
- [x] Task 8.1: Eliminate audio clicking and distortion by removing harsh `-40dB` silence-trimming filter and single-pass loudnorm compressor.
- [x] Task 8.2: Implement natural 300ms breath pauses between sentences with natural TTS rate (`--rate=+0%`, 40.03s total duration).
- [x] Task 8.3: Fix subtitle tokenization and alignment in `assemble_video.py` to prevent duplicate words (`steel. steel.`) and elevate MarginV to 680 (mobile UI safe zone).
- [x] Task 8.4: Upgrade `assemble_video.py` to compile all 12 visual beats using OpenCV Subpixel Ken Burns motion clips across all 12 pre-generated SDXL images.
- [x] Task 8.5: Verify 17/17 checks in `qa_gate.py` pass and post 540x960 review proxy (1.09 MB) to Discord webhook `REDACTED_WEBHOOK_ID`.

