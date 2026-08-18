# n8n Growth Orchestration & Integration Specification

---

## ⚡ 1. n8n API Contract & Workflow

The growth server runs on `http://127.0.0.1:8010` providing REST endpoints:

- `GET /api/growth/plan-next?channel=channel_a`: Ingested by n8n to retrieve the next ranked topic and experiment strategy.
- `POST /api/growth/record-upload`: Triggered after successful YouTube upload to start tracking snapshots.
- `POST /api/growth/run-learning-cycle`: Triggered weekly by n8n cron to process historical performance.

Canonical workflow definition: `growth/n8n-workflows/n8n_growth_intelligence_loop.json`.
