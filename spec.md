# System Specification — Channel A (Chronos Shift / Alternate History Shorts) Video Production

## 1. System Invariants & Architecture
- **Pipeline Identifier:** `alternate-history-shorts` (Channel A / Chronos Shift).
- **Execution Entrypoint:** `alternate-history-shorts/scripts/pipeline_runner.py`.
- **Visual Synthesis:** 100% full-screen 9:16 cinematic SDXL visuals generated strictly via local Fooocus SDXL (`http://127.0.0.1:7865`). Zero external image API calls or fallbacks.
- **Motion Engine:** Ken-Burns Candidate A 8% pan/zoom camera motion.
- **Narration Engine:** Authoritative documentary voice (`en-US-ChristopherNeural`, Edge-TTS).
- **Audio Alignment:** Word-level acoustic alignment via `faster-whisper`.
- **Quality Assurance:** Strict 17/17 QA gate execution (`alternate-history-shorts/scripts/qa_gate.py`).
- **Review & Approval Gate:** Automated < 8MB 540x960 review proxy delivery to Discord webhook `1528622690980724807`. Status transitions to `AWAITING_REVIEW`. Zero automatic uploads without human approval.

## 2. Topic Selection
- **Selected Topic:** "What if the Roman Empire never fell?" (Rank #1 in Channel A topic candidate pool, score 0.801, category: Empire, cluster: Classical).

## 3. Interfaces & State Transitions
- **Service Stack:**
  - Ollama (`http://127.0.0.1:11434`): `llama3.2:latest` for RAG claim verification and script critic.
  - Fooocus SDXL (`http://127.0.0.1:7865`): Gradio client API integration (`fn_index=67`, `fn_index=68`).
- **Database Tracking:** `growth/growth.db` (jobs and videos state synchronization).
