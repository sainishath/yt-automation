# Growth Analytics & Live YouTube API Ingestion

---

## 📡 1. Ingestion Engine Architecture (`growth/analytics/`)

- **YouTube Data API v3:** Ingests live public statistics (`views`, `likes`, `comments`, `duration`) via `videos().list(part='statistics,snippet')`.
- **YouTube Analytics API v2:** Queries channel-level retention, watch time, and subscriber conversions via `youtubeAnalytics.reports().query(...)`.
- **Multi-Window Ingestion Schedule:** `1h`, `6h`, `24h`, `48h`, `7d`, `28d`.
- **Offline Simulation Fallback:** When API tokens are not provided, gracefully falls back to deterministic simulation tagging snapshots with `SIMULATION_FALLBACK` rather than crashing.

---

## 🧮 2. Normalization & Scoring

- **Baseline Calculation:** Uses the median of the 10 most recent 24h snapshots.
- **Composite Score Formula:**
  $$\text{Score} = 0.40 \cdot \text{Retention Multiplier} + 0.35 \cdot \min(\text{View Multiplier}, 3.0) + 0.25 \cdot \text{Engagement Multiplier}$$
