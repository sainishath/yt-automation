# Growth & Content Intelligence Operations Runbook

---

## 🚀 1. Service Startup Sequence

To run the complete production automation stack:

```powershell
$env:PYTHONIOENCODING="utf-8"

# 1. Start Fooocus SDXL Server (Port 7865)
python D:\Projects\Fooocus\launch.py --listen 127.0.0.1 --port 7865

# 2. Start Pipeline 1 Server (Port 8000)
python alternate-history-shorts/server_alt_history.py

# 3. Start Pipeline 2 Server (Port 5001)
python convo-shorts/yt-automation-engine/server.py

# 4. Start Growth Intelligence REST Bridge (Port 8010)
python growth/server.py
```

---

## 📋 2. CLI Command Reference

```powershell
# Initialize growth database schema & seed channel profiles:
python growth/cli.py --init-db

# View real-time visual dashboard:
python growth/cli.py --dashboard

# Generate next content plan for Channel A (History):
python growth/cli.py --plan-next channel_a

# Generate next content plan for Channel B (Debates):
python growth/cli.py --plan-next channel_b

# Run learning cycle & generate weekly report:
python growth/cli.py --run-learning channel_a

# Run full end-to-end closed-loop simulation:
python growth/cli.py --dry-run-loop

# Run complete growth unit test suite:
python growth/run_growth_tests.py
```
