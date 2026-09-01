# Operator Runbook: Starting Production Automation

This guide provides the exact step-by-step procedure to start the entire YouTube automation and Content Intelligence system from a clean machine restart.

---

## ⚡ 1. Pre-Flight Environment Setup

Open PowerShell and configure UTF-8 encoding:

```powershell
$env:PYTHONIOENCODING="utf-8"
cd d:\Projects\yt-automations
```

---

## 🚀 2. Start Core Production Services

### Step 2.1: Start Fooocus SDXL Generation Daemon (Port 7865)
In a dedicated terminal:
```powershell
$env:PYTHONIOENCODING="utf-8"
python D:\Projects\Fooocus\launch.py --listen 127.0.0.1 --port 7865
```

### Step 2.2: Start Pipeline 1 Server — Alternate History (Port 8000)
In a dedicated terminal:
```powershell
$env:PYTHONIOENCODING="utf-8"
python alternate-history-shorts/server_alt_history.py
```

### Step 2.3: Start Pipeline 2 Server — Conversational Debates (Port 5001)
In a dedicated terminal:
```powershell
$env:PYTHONIOENCODING="utf-8"
python convo-shorts/yt-automation-engine/server.py
```

### Step 2.4: Start Growth Intelligence REST Bridge (Port 8010)
In a dedicated terminal:
```powershell
$env:PYTHONIOENCODING="utf-8"
python growth/server.py
```

---

## 🔑 3. One-Time YouTube OAuth Authorization

### For Channel A (Chronos Shift):
```powershell
python alternate-history-shorts/scripts/upload_video.py --auth_only
```
- Sign in to the **Chronos Shift** YouTube account in your browser and allow all requested permissions (`upload`, `readonly`, `analytics`).
- Update `config/channels/pipeline1_channel.json` with the authenticated channel ID.

### For Channel B (Debate Protocol):
- Ensure the Pipeline 2 server is running (Port 5001).
- Visit `http://localhost:5001/auth-youtube` in your web browser.
- Sign in to the **Debate Protocol** YouTube account and grant permissions.
- Update `config/channels/pipeline2_channel.json` with the authenticated channel ID.

---

## 📊 4. Daily Production & Operations

### View Real-Time Observability Dashboard:
```powershell
python growth/cli.py --dashboard
```

### Generate & Inspect the Next Planned Video for Channel A:
```powershell
python growth/cli.py --plan-next channel_a
```

### Generate & Inspect the Next Planned Video for Channel B:
```powershell
python growth/cli.py --plan-next channel_b
```

### Check and Ingest Overdue Performance Snapshots:
```powershell
python growth/cli.py --check-snapshots
```

### Run Periodic Learning Cycle & Generate Weekly Report:
```powershell
python growth/cli.py --run-learning channel_a
```

### Create a Hot Database Backup:
```powershell
python -c "from growth.db.backup import create_database_backup; create_database_backup()"
```

---

## 🧪 5. Verification Suite

Run full automated verification before any production deployment:

```powershell
# 1. Run Growth Suite (42 tests)
python growth/run_growth_tests.py

# 2. Run Master 21-Axis Release Verification
python verify_release.py
```
