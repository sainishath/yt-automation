# Production Operations Manual

---

## 1. Runtime Daemons & Prerequisites

Ensure the following 4 services are running before triggering automated workflows:

| Service | Port | Launch Command / URL |
|---|:---:|---|
| **Ollama Local LLM** | 11434 | `http://127.0.0.1:11434` (requires `llama3.1` or `llama3.2`) |
| **Fooocus SDXL Daemon** | 7865 | `python D:/Projects/Fooocus/launch.py --listen 127.0.0.1 --port 7865` |
| **n8n Automation Engine** | 5678 | `http://127.0.0.1:5678` |
| **Pipeline 1 Server** | 8000 | `$env:PYTHONIOENCODING="utf-8"; python alternate-history-shorts/server_alt_history.py` |
| **Pipeline 2 Server** | 5001 | `$env:PYTHONIOENCODING="utf-8"; python convo-shorts/yt-automation-engine/server.py` |

---

## 2. Triggering Production Runs

### Option A: Via n8n Automated Scheduler (Standard Production)
- **Pipeline 1:** Runs automatically on schedule (Mon, Wed, Fri at 10:00 AM) or via Webhook `POST http://localhost:5678/webhook/trigger-alternate-history`.
- **Pipeline 2:** Runs automatically via workflow `N3DelK9B5ssN879H` from topic spreadsheet queue.

### Option B: Via HTTP API (Controlled Manual Run)
```powershell
# Trigger Pipeline 1:
Invoke-RestMethod -Uri "http://127.0.0.1:8000/generate-alternate-history" -Method Post -ContentType "application/json" -Body '{"topic": "What if the Roman Empire never fell?", "video_id": "manual_prod_01"}'

# Trigger Pipeline 2:
Invoke-RestMethod -Uri "http://127.0.0.1:5001/tts" -Method Post -ContentType "application/json" -Body '{"title": "Why your brain forgets names", "category": "Weird Science", "sync": true}'
```

---

## 3. Discord Review Gate Operations

When generation succeeds and passes all QA checks, a review proxy is posted to Discord.

- **To Approve:**
  Reply in Discord: `approve <video_id>`  
  *Result:* Video is uploaded to YouTube, status becomes `UPLOADED`, and public link is posted to Discord.
- **To Reject:**
  Reply in Discord: `reject <video_id>`  
  *Result:* Workflow stops immediately. No YouTube upload occurs.

---

## 4. Failure Recovery Procedures

1. **If RAG Sufficiency Fails:**
   - The topic is flagged as `INSUFFICIENT` historical evidence.
   - Generation is automatically blocked with HTTP 400 error.
   - Review topic spelling or supply specific historical entities in `evidence_packet.json`.
2. **If QA Gate Fails:**
   - Inspect `<video_dir>/qa_report.json` to identify which check failed (resolution, duration, codecs, volume, unsupported claims).
   - Re-run `pipeline_runner.py` or inspect prompt parameters.
3. **If YouTube Upload Fails Due to Quota:**
   - Quota tracker limits daily usage to 10,000 units (~6 uploads/day).
   - Wait until midnight UTC for quota reset, or inspect `config/quota_tracker.json`.
