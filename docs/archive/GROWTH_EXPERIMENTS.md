# Growth Experimentation & Hypothesis Registry

---

## 🔬 1. Controlled Hypothesis Standards

Every experiment must define a single tested variable, control, variant, and primary metric with a minimum sample size threshold ($N \ge 4$ per arm) before drawing conclusions:

### Active Cohorts:
1. **`EXP_A_HOOK_01` (Channel A):**  
   - *Hypothesis:* Opening with an active counterfactual claim yields $\ge 5\%$ higher 24h retention than a polar question.  
   - *Control:* Polar Question.  
   - *Variant:* Active Counterfactual Assertion.  
   - *Primary Metric:* `avg_percentage_viewed`.

2. **`EXP_B_HOOK_01` (Channel B):**  
   - *Hypothesis:* Opening with a direct second-person provocation produces higher comment engagement than a neutral question.  
   - *Control:* Neutral Habit Question.  
   - *Variant:* Direct Second-Person Provocation.  
   - *Primary Metric:* `engagement_rate`.
