# Current State Audit: YouTube Automation Stack

**Repository Root:** `d:\Projects\yt-automations`  
**Git Branch:** `feature/growth-intelligence` (branched from `agent/production-freeze`, Commit `7056698` / `830c1ed`)  
**Audit Date:** 2026-08-18  
**Audit Status:** **PRODUCTION-FROZEN CODEBASE AUDITED**

---

## 1. Production Architecture & Boundaries

The repository contains two independently verified and deployed production pipelines:

### Pipeline 1: Alternate-History Shorts (`alternate-history-shorts/`)
- **Server:** `server_alt_history.py` on Port 8000 (`http://127.0.0.1:8000`).
- **Core Runner:** `scripts/pipeline_runner.py`.
- **RAG & Fact Checking:** `scripts/generate_rag_evidence.py` (Wikipedia API + OpenAlex API) and `scripts/generate_script.py` (0 unsupported claims gate).
- **Voice & Alignment:** Edge-TTS synthesis + Whisper DTW word alignment (`scripts/align_whisper.py`).
- **Visual Synthesis:** Fooocus SDXL photorealistic rendering (`scripts/generate_images.py` on Port 7865).
- **Assembly & Motion:** `scripts/assemble_video.py` using **Candidate A Ken Burns Camera Motion** (8% linear zoom/pan, top-left anchor).
- **QA Verification:** `scripts/qa_gate.py` (17/17 QA checks).
- **Review & Upload:** `scripts/discord_review.py` (review proxy) and `scripts/upload_video.py` (YouTube upload with duplicate check).
- **Canonical n8n Workflow:** `alternate_history_production.json` (ID: `xAyYyalPutEsTsDb`).
- **Live Tested Upload:** `MBz1UuEKnmQ` (https://youtu.be/MBz1UuEKnmQ).

### Pipeline 2: Conversational Debate Shorts (`convo-shorts/`)
- **Server:** `yt-automation-engine/server.py` on Port 5001 (`http://127.0.0.1:5001`).
- **Core Engine:** `yt-automation-engine/media_engine.py` and `yt-automation-engine/main.py`.
- **Dialogue & Voice:** Multi-turn host dialogue (35–60% Speaker B word balance, outro $\le 25$ words), dual Piper ONNX voices.
- **Visuals & Compositing:** Fooocus SDXL segment visual cards + background gameplay looping (Subway Surfers / Minecraft).
- **QA Verification:** `yt-automation-engine/qa_gate.py` (Technical, visual, audio, content, rights).
- **Review & Upload:** `yt-automation-engine/discord_review.py` and `yt-automation-engine/uploader.py`.
- **Canonical n8n Workflow:** `n8n_youtube_shorts_workflow.json` (ID: `N3DelK9B5ssN879H`).
- **Live Tested Upload:** `jx3XWe2R2Ng` (https://www.youtube.com/shorts/jx3XWe2R2Ng).

---

## 2. Existing Data Persistence & Analytics Audit

| Component | Current State | Growth System Gap |
|---|---|---|
| **Topic Storage** | Static JSON (`topics.json`, `Topics_Queue.csv`) | No historical scoring, trend momentum, or multi-factor ranking |
| **Video Metadata** | Per-run `metadata.json` / `.manifest.json` in output folders | No centralized database tracking features across runs |
| **Performance Tracking** | Single quota tracker (`quota_tracker.json`) | Zero analytics snapshot collection (1h, 6h, 24h, 7d, 28d) |
| **YouTube Analytics API** | Upload-only OAuth scopes (`youtube.upload`) | Requires analytics collection abstraction (Mock + API ingestion) |
| **Experimentation** | Manual A/B test scripts (cleaned in freeze) | No formal experiment registry, hypothesis tracking, or statistical evaluation |
| **Strategy Memory** | Hardcoded prompts in `generate_script.py` and `media_engine.py` | No versioned strategy state (`strategy_v1.0`, `strategy_v1.1`) |
| **Channel Routing** | Both upload to `@decoded_facts_ai` by default | Requires strict non-secret channel configuration and identity checks |

---

## 3. Reusable Components & Non-Negotiable Boundaries

1. **Reusable Core Engines:**  
   The video generation, RAG, TTS, Whisper alignment, Fooocus SDXL integration, and FFmpeg assembly engines are completely stable and will be invoked as downstream execution units without modification.
2. **Protected Quality Gates:**  
   The 17-point QA gate (`qa_gate.py`), Discord interactive review, and YouTube duplicate protection must remain hard gates that the growth system cannot bypass.
3. **Standalone Independence:**  
   The Content Intelligence system must sit as a decoupled management and learning wrapper in `growth/` (or `content_intelligence/`), ensuring that even if the growth layer is completely disabled, the core pipelines continue to function normally.
