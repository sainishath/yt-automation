# FIRST-PARTY LEARNING PROTOCOL

**System:** YouTube Automation & Closed-Loop Content Intelligence  
**Target:** Empirical Learning, Statistical Attribution & Belief Updates  
**Repository:** `D:\Projects\yt-automations`  
**Branch:** `feature/growth-intelligence`  
**Date:** August 21, 2026  

---

## 1. Video Maturity States & Snapshot Decision Hierarchy

To prevent premature overreaction to early algorithmic fluctuations, performance observations are categorized into four strict maturity states:

```text
  [1h / 6h]       ──►  IMMATURE      : Rapid sanity checks, zero-view upload defects, audio clipping.
                                       (NO strategic mutations allowed)
  [24h / 48h]     ──►  PRELIMINARY   : Initial audience reaction, early diagnostic attribution.
                                       (Emits diagnostic events, updates cohort queues)
  [7d]            ──►  MATURE        : Primary evaluation window. Algorithmic distribution settled.
                                       (Drives statistical arm comparisons, belief updates, strategy evolution)
  [28d]           ──►  LONG_TERM     : Evergreen performance and decay calibration.
                                       (Calibrates historical channel baselines)
```

---

## 2. Multi-Dimensional Performance Attribution

Every mature video is analyzed across key production dimensions to isolate causal factors:

| Dimension | Metric Analyzed | Threshold / Signal | Strategic Attribution |
|---|---|---|---|
| **Topic Demand** | Total Views & VPH vs Channel Median | $\ge 1.2\times$ Median = High Demand | Informs candidate topic pool allocation. |
| **Hook Retention** | Initial Drop-off (0–3s) / Early APV | $\ge 85\%$ APV = Strong Hook | Validates opening question or active statement format. |
| **Narrative Pacing** | Mid-Video Retention Slope (4–35s) | Smooth slope (no cliff) = High Pacing | Validates 3.2s visual beat transitions & Whisper sync. |
| **Ending & CTA** | Final 5s Retention & Comment Ratio | $\ge 2.5\%$ Comment Rate = Viral Clash | Validates pinned question and dual-perspective takeaway. |

---

## 3. Belief Update & State Transition Model

Beliefs regarding content patterns transition through a deterministic lifecycle based on empirical sample accumulation:

```text
                      BELIEF STATE TRANSITION LIFECYCLE
                                      │
                                      ▼
             [HYPOTHESIS / EXTERNAL PRIOR] (Weight <= 0.25, Confidence: LOW)
                                      │
                                      │ (First-Party Video Published)
                                      ▼
                      [VALIDATING] (1 <= N < 4 per arm, Confidence: LOW)
                                      │
                                      │ (N >= 4 Valid Samples per Arm Reached)
                        ┌─────────────┴─────────────┐
                        ▼                           ▼
          [PROMOTED] (Delta >= +5.0%)    [REJECTED / FIRST_PARTY_OVERRIDE] (Delta <= -5.0%)
          • Strategy Mutation (v1.1)     • Prior demoted to 0.0 weight
          • Confidence: HIGH             • Added to DO_NOT_USE Registry
          • Enters 70% Proven Tier       • Confidence: HIGH
```

---

## 4. Statistical Safeguards Against Small Sample Noise & Thrashing

1. **Hard $N \ge 4$ Sample Guard:** No experiment decision or strategy promotion can occur before both Control and Treatment arms accumulate at least 4 mature first-party samples.
2. **Median Absolute Deviation (MAD) Outlier Filtering:** Evaluates median APV rather than arithmetic mean to prevent one single viral outlier or zero-view anomaly from corrupting statistical evaluation.
3. **Minimum Effect Threshold ($|\Delta| \ge 5.0\%$):** Requires at least a 5.0% relative APV delta between arms. Deltas within $[-5\%, +5\%]$ are classified as `INCONCLUSIVE` (retaining the Control baseline).
4. **Strategy Mutation Cooldown:** Imposes a 7-day cooldown between strategy version promotions (`v1.0` $\to$ `v1.1`), preventing daily strategy thrashing.
5. **Negative Knowledge Persistence:** Failed patterns are permanently recorded in the `DO_NOT_USE` registry, preventing the Brain from repeatedly re-testing previously rejected ideas.
