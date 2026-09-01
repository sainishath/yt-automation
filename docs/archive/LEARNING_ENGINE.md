# Learning Engine & Autonomous Strategy Refinement

---

## 🔄 1. The Periodic Learning Cycle

The Learning Engine evaluates historical content performance and updates strategy memory without destabilizing production code:

```text
Historical Performance Snapshots
              ↓
    Performance Normalizer
              ↓
  Winner / Loser / Outlier Autopsies
              ↓
    Experiment Evaluator
              ↓
Weekly Growth Report & Strategy Update Proposal
              ↓
      Human Review Gate
              ↓
  Active Strategy Version (v1.0 -> v1.1)
```

---

## 📋 2. Automated Postmortem & Autopsy Analysis

For every evaluated video, the system produces a structured postmortem:
- **Strongest Signals:** Identifies standout dimensions (e.g., $1.2\times$ retention baseline or high velocity).
- **Weakest Signals:** Detects drop-off points or low subscriber conversion.
- **Evidence-Based Hypothesis:** Labels underlying reasons (e.g., topic resonance vs pacing fatigue).
- **Actionable Recommendation:** Suggests tactical changes for subsequent cohorts (e.g., tightening beat transitions by 1.0s).

---

## 🏛️ 3. Immutable Strategy Versioning

Strategy updates are never applied as silent code mutations. They are recorded in `growth/strategy/` as immutable versioned snapshots (`strategy_v1.0`, `strategy_v1.1`), ensuring full historical traceability for every published video.
