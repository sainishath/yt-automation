# Growth System Failure Recovery & Safety Manual

---

## 🛡️ 1. Failure Modes & Recovery Matrix

| Failure Mode | Root Cause | Built-in Mitigation / Recovery Action |
|---|---|---|
| **YouTube API Quota Outage** | 10,000 unit daily limit exceeded | Collector falls back to cached snapshot or simulation mode; upload queue sets job to `RETRY_PENDING`. |
| **Channel ID Mismatch** | Wrong OAuth token loaded for channel | `channel_identity_check.py` throws fatal exception and stops upload before execution. |
| **Discord Rejection** | User rejects video in Discord | Pipeline terminates immediately; job marked as `REJECTED`; 0 auto-retries. |
| **Insufficient Sample Size** | Fewer than 4 videos per experiment arm | Experiment manager returns `INSUFFICIENT_DATA` and continues gathering data without mutating strategy. |
| **Database Lock / Busy** | High concurrency SQLite access | WAL mode (`PRAGMA journal_mode = WAL`) and context-managed connection timeouts prevent corruption. |
| **Growth Server Offline** | Port 8010 process stopped | Production generation engines (`Port 8000` / `Port 5001`) continue to function via direct CLI calls. |
