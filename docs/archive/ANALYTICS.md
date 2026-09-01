# YouTube Analytics & Performance Normalization

---

## ⏱️ 1. Multi-Window Ingestion Intervals

Performance is captured across distinct time windows to track velocity and avoid comparing fresh uploads directly against mature library content:

| Window | Hours Elapsed | Core Signals Captured |
|:---:|:---:|---|
| **1h** | 1.0 hr | Initial subscriber reaction, early CTR, first-hour velocity |
| **6h** | 6.0 hrs | Shorts feed discovery momentum, swipe-away vs viewed rate |
| **24h** | 24.0 hrs | Primary normalization baseline, Average Percentage Viewed (APV), comment depth |
| **48h** | 48.0 hrs | Algorithm distribution plateau or breakout acceleration |
| **7d** | 168.0 hrs | Mid-term retention stability, subscriber conversion rate |
| **28d** | 672.0 hrs | Long-term evergreen value and search/browse contributions |

---

## 🧮 2. Normalization & Scoring Formulas

### Robust Baseline (10-Video Median)
Rather than comparing against arithmetic means (skewed by viral spikes), the system computes medians:
- $\text{Median Views}_{24h} = \text{median}(\text{views}_{1..10})$
- $\text{Median APV} = \text{median}(\text{APV}_{1..10})$
- $\text{Median Engagement Rate} = \text{median}(\text{engagement}_{1..10})$

### Composite Normalized Performance Score (v1.0)
$$\text{Score} = 0.40 \cdot \text{Retention Multiplier} + 0.35 \cdot \min(\text{View Multiplier}, 3.0) + 0.25 \cdot \text{Engagement Multiplier}$$

*Capping View Multiplier at $3.0\times$ prevents single viral outliers from distorting subsequent topic selection.*
