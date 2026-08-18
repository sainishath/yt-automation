# Production Operations Manual & Runbook

---

## 🚀 1. Starting the Automation Stack

Before running scheduled workflows, ensure the local daemon stack is operational.

```powershell
# Set UTF-8 encoding in PowerShell
$env:PYTHONIOENCODING="utf-8"

# 1. Start Fooocus SDXL Daemon (Port 7865)
python D:\Projects\Fooocus\launch.py --listen 127.0.0.1 --port 7865

# 2. Start Pipeline 1 Server (Port 8000)
python alternate-history-shorts/server_alt_history.py

# 3. Start Pipeline 2 Server (Port 5001)
python convo-shorts/yt-automation-engine/server.py
```

---

## 🧪 2. Safe Dry-Run & Testing Protocol

To execute a dry-run test without making public YouTube uploads:

### Pipeline 1 Dry-Run
```powershell
# Generate video and run 17/17 QA checks without uploading:
python alternate-history-shorts/scripts/pipeline_runner.py --topic "What if the Roman Empire never fell?" --video_id "dry_run_p1"
```

### Pipeline 2 Dry-Run
```powershell
# Generate conversational debate and verify QA:
python convo-shorts/yt-automation-engine/main.py --topic "Can AI ever become truly conscious?" --category "Tech Debate"
```

---

## 🛡️ 3. Authorizing Dedicated YouTube Channels

To authorize or change the YouTube channel for either pipeline independently:

### Authorizing Channel A (Pipeline 1)
```powershell
python alternate-history-shorts/scripts/upload_video.py --auth_only
```
*Opens Google consent screen $\to$ select the dedicated Google account for Channel A $\to$ saves to `alternate-history-shorts/config/token.json`.*

### Authorizing Channel B (Pipeline 2)
```powershell
# Visit in browser:
http://localhost:5001/auth-youtube
```
*Spins up temporary callback on Port 8090 $\to$ select the dedicated Google account for Channel B $\to$ saves to `convo-shorts/yt-automation-engine/youtube_token.pickle`.*

---

## 🔧 4. Troubleshooting & Failure Recovery

| Issue | Root Cause | Recovery Procedure |
|---|---|---|
| **RAG Sufficiency Error** | Fictional topic or sparse Wikipedia/OpenAlex data | Ensure historical entity spelling is valid; check `evidence_packet.json` |
| **QA Gate Failure** | Codec mismatch, volume clipping, or duration $<30$s | Inspect `<output_dir>/qa_report.json`; check FFmpeg build |
| **YouTube Upload 403** | OAuth token scope expired or invalid | Re-run `--auth_only` or `/auth-youtube` flow for the relevant channel |
| **YouTube Daily Quota Exceeded** | Daily 10,000 unit limit reached | Quota resets at 00:00 UTC; tracker located in `quota_tracker.json` |
