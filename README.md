# YouTube Shorts Automation Engine (Dual-Pipeline Production System)

A production-grade, unattended YouTube Shorts generation, validation, review-gating, and publishing platform powering two automated channels:

1. **Pipeline 1: Alternate-History Shorts (`alternate-history-shorts`)**  
   Groundbreaking historical "What-If" shorts with RAG v4 academic evidence grounding, Whisper word-highlight subtitles, Fooocus SDXL photorealistic rendering, and Ken Burns cinematic camera motion.
2. **Pipeline 2: Conversational Debate Shorts (`convo-shorts`)**  
   High-retention debate and psychology shorts with multi-turn dialogue, dual synthetic voices, automated thumbnail generation, and background gameplay integration.

---

## 🏛️ System Architecture

```text
                                 [ n8n Automation Engine (Port 5678) ]
                                    │                           │
                   ┌────────────────┘                           └────────────────┐
                   ▼                                                             ▼
     [ Pipeline 1 Server (Port 8000) ]                             [ Pipeline 2 Server (Port 5001) ]
  (Alternate History Shorts Engine)                             (Conversational Debate Shorts Engine)
                   │                                                             │
   1. RAG v4 Historical Grounding                                1. Multi-Turn Dialogue Generation
   2. Claim Verification (0 Unsupported)                         2. Co-Host Balancing & Fact Checks
   3. Edge-TTS Voice Generation                                  3. Dual-Speaker Piper/Edge TTS
   4. Whisper Word-Level Alignment                               4. Whisper Word-Level Alignment
   5. Semantic Visual Beat Planner                               5. Gameplay Background Integration
   6. Fooocus SDXL Generation (Port 7865)                        6. Fooocus Segment Visual Proofs
   7. 1080x1920 Assembly (Candidate A Motion)                    7. 1080x1920 Video Compilation
   8. 17-Point QA Verification Gate                              8. Multi-Axis QA Verification Gate
                   │                                                             │
                   └──────────────────────┬──────────────────────────────────────┘
                                          ▼
                         [ Discord Review Gate (Webhooks) ]
                                          │
                         ┌────────────────┴────────────────┐
                         ▼                                 ▼
                   [ REJECTED ]                      [ APPROVED ]
                         │                                 │
                 Execution Halts                   YouTube Upload
              (Zero Retries/Spam)              (Idempotent Quota Gate)
                                                           │
                                                           ▼
                                                [ PUBLIC YOUTUBE SHORT ]
```

---

## 🚀 Quick Start (Starting Production Daemons)

### 1. Prerequisites
- Python 3.10+
- FFmpeg installed & on system PATH
- Ollama running locally (`http://127.0.0.1:11434`)
- Fooocus SDXL running locally (`http://127.0.0.1:7865`)
- n8n running locally (`http://127.0.0.1:5678`)

### 2. Launching Servers

```powershell
# In PowerShell (with UTF-8 encoding enabled):
$env:PYTHONIOENCODING="utf-8"

# Terminal 1 — Start Pipeline 1 Server (Port 8000):
python alternate-history-shorts/server_alt_history.py

# Terminal 2 — Start Pipeline 2 Server (Port 5001):
python convo-shorts/yt-automation-engine/server.py
```

---

## 📋 Production Endpoints & CLI Entrypoints

### Pipeline 1 (Alternate History)
- **Health Check:** `GET http://127.0.0.1:8000/health`
- **Trigger Generation:** `POST http://127.0.0.1:8000/generate-alternate-history`
- **Status Check:** `GET http://127.0.0.1:8000/get-status?id=<video_id>`
- **Video Download:** `GET http://127.0.0.1:8000/get-video?id=<video_id>`
- **YouTube Upload:** `POST http://127.0.0.1:8000/upload-youtube`
- **CLI Runner:**
  ```powershell
  python alternate-history-shorts/scripts/pipeline_runner.py --topic "What if the Library of Alexandria never burned?" --video_id "alexandria_01"
  ```

### Pipeline 2 (Convo Shorts)
- **Next Topic:** `GET http://127.0.0.1:5001/get-next-topic`
- **Trigger Generation:** `POST http://127.0.0.1:5001/tts`
- **Discord Review:** `POST http://127.0.0.1:5001/post-discord-review`
- **YouTube Upload:** `POST http://127.0.0.1:5001/upload_youtube`
- **CLI Runner:**
  ```powershell
  python convo-shorts/yt-automation-engine/main.py --topic "Why your brain forgets names" --category "Weird Science"
  ```

---

## ⚡ Orchestration & n8n Workflows

- **Pipeline 1 Active Workflow:** `Alternate History Shorts — Production Pipeline with Discord Review Gate` (`ID: xAyYyalPutEsTsDb`)
- **Pipeline 2 Active Workflow:** `YT Shorts Automation with Discord Review Gate` (`ID: N3DelK9B5ssN879H`)
- **Workflow Canonical Definitions:**
  - Pipeline 1: [`alternate-history-shorts/n8n-workflows/alternate_history_production.json`](file:///d:/Projects/yt-automations/alternate-history-shorts/n8n-workflows/alternate_history_production.json)
  - Pipeline 2: [`convo-shorts/n8n_youtube_shorts_workflow.json`](file:///d:/Projects/yt-automations/convo-shorts/n8n_youtube_shorts_workflow.json)

---

## 🛡️ Production Verification Suite

To run the complete 21-axis production verification suite:
```powershell
$env:PYTHONIOENCODING="utf-8"
python verify_release.py
```

Expected result: **21/21 PASS (0 failures, 0 warnings)**.
