# Learning Engine & Strategy Evolution Specification

---

## 🔄 1. Learning Cycle Flow

1. **Snapshot Aggregation:** Ingests 24h performance metrics across published videos.
2. **Postmortem Autopsy:** Classifies each video into `ABOVE_MEDIAN`, `BELOW_MEDIAN`, or `ON_MEDIAN`, highlighting top retention/velocity signals.
3. **Hypothesis Evaluation:** Compares experiment arms once $N \ge 4$.
4. **Strategy Mutation:** If an experiment achieves `ACCEPT_VARIANT` with `HIGH` confidence ($> +5\%$ delta), the engine writes an evolved strategy payload (`strategy_v1.1`) to `strategy_versions` and records a `LEARNING_EVENT`.
5. **Report Compilation:** Outputs the Markdown Weekly Channel Growth Report.
