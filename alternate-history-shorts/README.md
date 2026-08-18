# Pipeline 1: Alternate-History Shorts Engine

A dedicated, autonomous YouTube Shorts engine producing historically grounded, cinematic counterfactual "What-If" shorts with academic RAG grounding, neural voice synthesis, Whisper word-highlight subtitles, and Fooocus SDXL photorealistic rendering.

---

## 🏛️ Pipeline Architecture

```text
[Topic Input]
     │
     ▼
[Stage 1: RAG v4 Academic Evidence Grounding]
  ├── Wikipedia API & OpenAlex API Entity Search
  ├── Historical Sufficiency Gate (Rejects fictional/non-existent entities)
  └── Visual Evidence Extraction (Materials, Architecture, Lighting, Attire)
     │
     ▼
[Stage 2: Script Writing & Claim Verification]
  ├── Active Counterfactual Spoken Hook Generation (Score >= 8.5/10)
  ├── 8-Beat Counterfactual Narrative Arc
  └── 100% Atomic Claim Verification Gate (0 Unsupported Claims)
     │
     ▼
[Stage 3: Audio Synthesis & Word-Level Alignment]
  ├── Edge-TTS Neural Voice Generation (ChristopherNeural / GuyNeural)
  └── Whisper ASR DTW Word-Level Alignment & Timing Cache
     │
     ▼
[Stage 4: Semantic Visual Scene Planner]
  ├── Dynamic Narration Timing Segmentation
  └── RAG Visual Evidence Prompt Injection
     │
     ▼
[Stage 5: Fooocus SDXL Native 1080x1920 Generation]
  └── Async Parameter Setter (fn_index=67) & Queue Submitter (fn_index=68)
     │
     ▼
[Stage 6: Video Assembly & Subtitles]
  ├── Candidate A Ken Burns Camera Motion (8% linear zoom/pan, top-left anchor)
  ├── 1080x1920 Native ASS Karaoke Word-Highlight Subtitles
  ├── Ambient Background Music Mixing (-22 dB ducked)
  └── FFmpeg Libx264 25 FPS Compilation
     │
     ▼
[Stage 7: 17-Point QA Verification Gate]
  └── Resolution (1080x1920), Codecs (H.264/AAC), Volume (-24dB to -0.5dB), 0 Unsupported Claims
     │
     ▼
[Stage 8: Discord Review Gate & YouTube Publishing]
  ├── 540x960 Review Proxy Posted to Discord
  └── Idempotent YouTube Upload (with Synthetic Media Disclosure & Quota Gate)
```

---

## 🚀 Quick Start & CLI Entrypoints

### Starting the Server
```powershell
$env:PYTHONIOENCODING="utf-8"
python server_alt_history.py
```
*Runs on `http://127.0.0.1:8000`.*

### Manual CLI Execution (Dry-Run / Production)
```powershell
python scripts/pipeline_runner.py --topic "What if the Library of Alexandria never burned?" --video_id "alexandria_01"
```

### Authorizing Channel A (Dedicated YouTube Account)
```powershell
python scripts/upload_video.py --auth_only
```
*Saves OAuth token to `config/token.json` (or path configured in `P1_YOUTUBE_TOKEN`).*

---

## 🛡️ Production Verification
Run internal test suite:
```powershell
python scripts/run_tests.py
```
