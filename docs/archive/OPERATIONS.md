# Production & Growth Operations Manual

---

## 🚀 1. Starting the Entire Production & Growth Stack

```powershell
$env:PYTHONIOENCODING="utf-8"

# 1. Start Fooocus SDXL Daemon (Port 7865)
python D:\Projects\Fooocus\launch.py --listen 127.0.0.1 --port 7865

# 2. Start Pipeline 1 Server (Port 8000)
python alternate-history-shorts/server_alt_history.py

# 3. Start Pipeline 2 Server (Port 5001)
python convo-shorts/yt-automation-engine/server.py
```

---

## 🧪 2. Growth Intelligence Commands

```powershell
# Initialize Database & Seed Channels
python growth/cli.py --init-db

# Plan Next Video for Channel A (History)
python growth/cli.py --plan-next channel_a

# Plan Next Video for Channel B (Debates)
python growth/cli.py --plan-next channel_b

# Run Learning Cycle & Generate Weekly Report
python growth/cli.py --run-learning channel_a

# Execute Full End-to-End Closed-Loop Dry Run
python growth/cli.py --dry-run-loop

# Run Complete Growth Test Suite
python growth/run_growth_tests.py
```

---

## 🛡️ 3. Master Release & Regression Verification

```powershell
# Run Master 21-Axis Release Verification
python verify_release.py
```
