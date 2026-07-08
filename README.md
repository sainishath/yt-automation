<div align="center">

# 🎬 piper-yt-automation

**Zero-cost YouTube Shorts factory — Ollama generates scripts, Piper voices them, Whisper burns subtitles, FFmpeg assembles the video, n8n schedules the upload. No API bills.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-Backend-000000?style=flat-square&logo=flask)](https://flask.palletsprojects.com)
[![n8n](https://img.shields.io/badge/n8n-Orchestration-EA4B71?style=flat-square)](https://n8n.io)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-black?style=flat-square)](https://ollama.com)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

</div>

---

## 🏗️ Pipeline Architecture

```
n8n Scheduler (daily 9 AM Mon–Fri)
        │
        ▼
┌─────────────────────────────────────────┐
│  Google Sheets — Topics Queue            │
│  Reads today's row: Day / Category /    │
│  Topic                                  │
└───────────────┬─────────────────────────┘
                │ POST /generate_video
                ▼
┌─────────────────────────────────────────┐
│  Flask Backend  (server_ollama.py)       │
│                                         │
│  1. Ollama (Mistral) → Script           │
│     Category-aware prompts:             │
│     • Weird Science → "Your brain…"    │
│     • Productivity  → "Millionaires…" │
│     • Human Behavior → "If someone…"  │
│     Output: Hook / Body / CTA          │
│                                         │
│  2. Piper TTS → Voiceover .wav          │
│     Model: en_US-lessac-medium          │
│     Sample rate: 22 050 Hz              │
│                                         │
│  3. Faster-Whisper → Subtitle .srt      │
│     Word-level timestamps               │
│     Burned as animated captions         │
│                                         │
│  4. OpenCV + FFmpeg → Final .mp4        │
│     Category-coloured caption overlay   │
│     (Cyan / Gold / Hot-pink per niche)  │
│     9:16 vertical format for Shorts     │
└───────────────┬─────────────────────────┘
                │ video file path
                ▼
┌─────────────────────────────────────────┐
│  n8n → YouTube Data API v3 Upload       │
│  Sets title, tags, description, public  │
│  Logs result back to Google Sheets      │
└─────────────────────────────────────────┘
```

**Why fully local?** Every component (Ollama, Piper, Whisper, FFmpeg) runs on-device. The only outbound call is the final YouTube upload — zero LLM API spend per video.

---

## 📦 Components

| Component | Role | Model / Tool |
|---|---|---|
| **Ollama** | Script generation (Hook/Body/CTA) | Mistral (swappable: Llama 3, neural-chat) |
| **Piper TTS** | Offline text-to-speech voiceover | `en_US-lessac-medium.onnx` |
| **Faster-Whisper** | Audio transcription → timed subtitles | `base` model |
| **OpenCV + PIL** | Caption rendering, thumbnail generation | — |
| **FFmpeg** | Audio-video mux, format encoding | — |
| **n8n** | Cron scheduler + workflow orchestrator | Self-hosted |
| **Google Sheets** | Topic queue & upload log | — |
| **YouTube Data API v3** | Final upload + metadata | OAuth 2.0 |

---

## 🎯 Content Categories

Three niche pipelines, each with tuned prompt personas and caption colour schemes:

| Category | Hook Style | Caption Colour |
|---|---|---|
| Weird Science | `"Your brain…"` / `"Scientists found…"` | Cyan `#00FFFF` |
| Productivity & Stoicism | `"Millionaires…"` / `"One habit…"` | Gold `#FFD700` |
| Human Behavior | `"If someone does THIS…"` / `"Watch for…"` | Hot Pink `#FF007F` |

---

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Python dependencies
pip install -r requirements.txt

# Install Ollama and pull a model
# https://ollama.com/download
ollama pull mistral

# Download Piper TTS binary + voice model
# https://github.com/rhasspy/piper/releases
# Place piper.exe and en_US-lessac-medium.onnx in ./data/models/

# FFmpeg must be on PATH
# https://ffmpeg.org/download.html
```

### 2. Start the Flask server

```bash
python files/01_current_setup/server_ollama.py
```

Server starts at `http://localhost:5000`. Verify Ollama is reachable before sending requests.

### 3. Test a single video generation

```bash
curl -X POST http://localhost:5000/generate_video \
  -H "Content-Type: application/json" \
  -d '{"topic": "Why we forget dreams", "category": "Weird Science", "video_id": "test_001"}'
```

Returns:
```json
{
  "status": "success",
  "video_path": "./data/output/test_001.mp4",
  "script": { "hook": "...", "body": "...", "cta": "..." },
  "cost": "$0.00"
}
```

### 4. Set up n8n automation

1. Import `files/01_current_setup/n8n_advanced_workflow.json` into your n8n instance.
2. Configure credentials: Google Sheets OAuth + YouTube OAuth.
3. Set your `YOUTUBE_ACCESS_TOKEN` env variable.
4. The workflow triggers daily at **9 AM Mon–Fri**, reads today's topic from your Google Sheet, calls Flask, waits 5 min for FFmpeg, then uploads.

---

## 📁 Project Structure

```text
piper-yt-automation/
├── files/
│   ├── 01_current_setup/
│   │   ├── server_ollama.py             ← Flask backend (full pipeline)
│   │   ├── n8n_advanced_workflow.json   ← Import into n8n
│   │   ├── n8n_workflow_ollama.md       ← Node-by-node workflow reference
│   │   ├── OLLAMA_SETUP_GUIDE.md        ← Ollama install + model setup
│   │   └── 100_PERCENT_FREE_COMPLETE_SETUP.md  ← End-to-end setup guide
│   └── 02_resources_and_data/
│       └── CONTENT_IDEAS_200_TOPICS.md  ← 200 pre-researched topic ideas
└── README.md
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Script Generation | Ollama (Mistral) — fully local |
| Text-to-Speech | Piper TTS (`en_US-lessac-medium`) — fully local |
| Transcription | Faster-Whisper — fully local |
| Video Assembly | FFmpeg + OpenCV + Pillow |
| Orchestration | n8n (self-hosted) |
| Schedule | Cron via n8n (Mon–Fri 9 AM) |
| Upload | YouTube Data API v3 |
| Topic Queue | Google Sheets |

---

## 📄 License

MIT — see [LICENSE](LICENSE).
