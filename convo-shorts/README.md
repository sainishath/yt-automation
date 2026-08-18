# Pipeline 2 — Conversational YouTube Shorts Suite

Production-hardened, two-person conversational YouTube Shorts generator with factual QA grounding, audio-driven semantic visual timing, Fooocus visual synthesis, sidechain BGM ducking, Discord interactive approval gate, and automated YouTube private upload.

---

## 1. Prerequisites & Environment

- **OS:** Windows 10/11 (64-bit) or Linux/macOS
- **Python:** Python 3.10+
- **GPU:** NVIDIA GPU with CUDA support (e.g. RTX 4070 Laptop GPU / Desktop GPU)
- **External Binaries:**
  - `ffmpeg` & `ffprobe` (on system PATH)
  - `piper.exe` (located in root directory or `data/piper.exe`)
- **Daemons & Services:**
  - **Ollama Server:** Running at `http://127.0.0.1:11434` with model `llama3.1:latest`
  - **Fooocus Server:** Running at `http://127.0.0.1:7865` with SDXL pipeline

---

## 2. Voice Models & Asset Structure

Ensure the following local models and assets are present:

```
convo-shorts/
├── models/
│   ├── voices/
│   │   └── en_US-ryan-medium.onnx          # Speaker A Voice (Piper)
│   └── en_US-libritts_r-medium.onnx        # Speaker B Voice (LibriTTS-R Speaker 4)
├── assets/
│   ├── backgrounds/active/
│   │   └── minecraft_bg.mp4                # Gameplay / background video source
│   └── bgm/
│       └── lofi.mp3                        # Background music track
```

---

## 3. Configuration & Environment Setup

Copy `.env.example` to `.env` and set your credentials:

```bash
cp .env.example .env
```

Key environment variables:
- `PYTHONIOENCODING=utf-8` (Required for Windows stdout symbol rendering)
- `STRICT_FOOOCUS=1` (Enforces Fooocus visual generation quality gate)

---

## 4. Production Execution (CLI & Headless)

To launch a production Short job locally or from n8n:

```powershell
$env:PYTHONIOENCODING="utf-8"; $env:STRICT_FOOOCUS="1"; python main.py --topic "Why deep ocean creatures glow in total darkness" --category "Weird Science"
```

### Optional Arguments:
- `--topic`: Topic string for the Short (required)
- `--category`: Category string (`"Weird Science"`, `"Human Behavior"`, `"Productivity & stoicism"`, `"Tech"`)
- `--job_id`: Custom unique job ID (e.g. `job_20260816_144500_001`)
- `--output_dir`: Custom output directory for final videos and manifests
- `--upload`: Automatically trigger private YouTube upload upon QA pass

---

## 5. Machine-Readable Result Specification

`main.py` terminates with a deterministic exit code (`0` for success, `1` for failure) and outputs a machine-readable JSON result object on standard stdout:

### Success Output (`exit code 0`):
```json
{
  "status": "qa_passed",
  "job_id": "job_20260816_150843_002",
  "short_id": "Short_002",
  "video_path": "D:\\Projects\\yt-automations\\convo-shorts\\yt-automation-engine\\videos\\Short_002.mp4",
  "manifest_path": "D:\\Projects\\yt-automations\\convo-shorts\\yt-automation-engine\\videos\\Short_002.manifest.json",
  "duration": 50.08,
  "qa_passed": true
}
```

### Failure Output (`exit code 1`):
```json
{
  "status": "failed",
  "job_id": "job_20260816_150843_002",
  "short_id": "Short_002",
  "failed_stage": "TTS",
  "error": "Error details...",
  "qa_passed": false
}
```

---

## 6. Job Lifecycle & Disposable Failure Model

1. **Preflight Check (`PREFLIGHT`):** Verifies FFmpeg, Ollama model, Fooocus port, Piper models, background assets, and directory permissions before starting AI generation.
2. **Script Generation & Grounding (`SCRIPTING`):** Generates dual-persona co-equal script, enforcing factual grounding, initiative balance, and a brief natural outro.
3. **TTS Synthesis (`TTS`):** Synthesizes dialogue per speaker, measures actual Whisper audio timestamps, and normalizes loudnorm levels.
4. **Visual Generation (`VISUAL_GENERATION`):** Generates 896x896 Fooocus images mapped to semantic visual beats.
5. **Video Assembly (`RENDERING`):** Slices background gameplay, overlays visual proofs, applies dynamic Ken-Burns movement, and renders 1080x1920 60 FPS H.264 video with sidechain BGM ducking.
6. **Production QA Gate (`FINAL_QA`):** Validates technical specs, visual asset integrity, audio levels, and content balance. Writes production manifest.
7. **Disposable Job Failure Model:** On unrecoverable error at any stage, the job is marked `FAILED`, intermediate files inside `temp/job_<job_id>` are safely cleaned, no fake upload is triggered, and `main.py` exits with code `1`.

---

## 7. Discord Interactive Approval & YouTube Upload

1. **OAuth Setup (One-time):**
   Visit `http://localhost:5001/auth-youtube` to authorize YouTube Data API v3 access. OAuth tokens are cached in `youtube_token.pickle`.
2. **Discord Approval Listener:**
   Run `python discord_bot_listener.py` to listen for Discord review channel approvals.
3. **Upload Safety:**
   All uploads default to `privacyStatus: "private"`. Videos are uploaded only after explicit QA pass and human/n8n approval. Manifests are automatically updated with the YouTube video ID.

---

## 8. n8n Workflow Integration

Import `n8n_youtube_shorts_workflow.json` into n8n:
- **Schedule Trigger:** Triggers daily/weekly jobs.
- **Execute Pipeline Node:** Executes `main.py` via shell command.
- **Parse JSON Node:** Evaluates `qa_passed == true`.
- **Discord Review Node:** Posts preview video to Discord channel with interactive approval links.
- **Upload Node:** On approval, triggers `POST /upload_youtube` to publish private video to YouTube.
