# First-Party Experiment Status & Closed-Loop Learning Report

**Generated:** 2026-08-21 07:34:01 UTC  
**Total Experiments Tracked:** 4  
**Active Experiments:** 4 | **Completed Experiments:** 0  
**Verdict Distribution:** 0 Treatment Wins, 0 Control Wins (Prior Overrides), 0 Inconclusive  

---

## 1. Executive Summary & First Principles

This report tracks every controlled first-party A/B experiment operating in the YouTube Growth System. Every experiment tests **exactly one isolated variable** with a hard $N \ge 4$ sample size guard. Under the system's core governance rule:
> **First-Party Evidence Dominance:** External observations only produce bounded priors (weight $\le 0.25$). Only empirical first-party channel performance data ($N \ge 4$) can validate or reject a hypothesis.

## 2. Experiment Portfolio Overview

| Status | Count | Key Operational Rule |
|---|:---:|---|
| **Active / Running** | 4 | One Variable, One Active Experiment per Variable per Channel |
| **Completed — Treatment Won** | 0 | Promoted to Candidate Strategy Version |
| **Completed — Control Won** | 0 | External Prior Demoted to `REJECTED`, Weight = 0.0 |
| **Completed — Inconclusive** | 0 | Insufficient difference (< 5%), prior remains unconfirmed |
| **Total Tracked** | 4 | 100% Traceable Lineage |

---
## 3. Active Experiments Queue

| Experiment ID | Channel | Variable Tested | Min Sample | Current Progress | Status | Source |
|---|:---:|---|:---:|:---:|:---:|---|
| `exp_channel_a_hook_structure_counterfactual_question_v1` | **channel_a** | `HOOK_STRUCTURE` | $N \ge 4$ | C:0/4, T:0/4 | `RUNNING` | FIRST_PARTY_DISCOVERY |
| `exp_channel_a_topic_cluster_modern_warfare_and_geopolitical_divergence_v1` | **channel_a** | `TOPIC_CLUSTER` | $N \ge 4$ | C:0/4, T:0/4 | `APPROVED` | FIRST_PARTY_DISCOVERY |
| `exp_channel_b_hook_structure_socratic_question_v1` | **channel_b** | `HOOK_STRUCTURE` | $N \ge 4$ | C:0/4, T:0/4 | `APPROVED` | FIRST_PARTY_DISCOVERY |
| `exp_channel_b_topic_cluster_ai_ethics_and_future_dilemmas_v1` | **channel_b** | `TOPIC_CLUSTER` | $N \ge 4$ | C:0/4, T:0/4 | `APPROVED` | FIRST_PARTY_DISCOVERY |

---
## 4. Completed Experiments & Evidence Outcomes

*No completed experiments yet (awaiting empirical video cohort samples).*


---
## 5. Detailed Experiment Lineage & Audit Trace

### Experiment: `exp_channel_a_hook_structure_counterfactual_question_v1`

- **Channel:** `channel_a` | **Status:** `RUNNING` | **Provenance:** `SIMULATION`
- **Hypothesis:** Implementing 'RAG v4 grounded question hook with Whisper-aligned visual beat' (derived from external pattern 'Counterfactual Question Hook Pattern') will improve channel relative performance by >= 5% in target niche.
- **Variable Under Test:** `HOOK_STRUCTURE` (Single variable isolated)
- **Control Definition:** Standard Chronos Shift Question Hook (e.g. 'What if Rome never fell?')
- **Treatment Definition:** RAG v4 grounded question hook with Whisper-aligned visual beat
- **Success Metric:** `avg_percentage_viewed` (Min $N=4$ per arm)
- **Linked External Prior:** `prior_pat_channel_a_counterfactual_question` (Initial Weight: 0.22)
- **Registered Arms:** CONTROL (`arm_exp_channel_a_hook_structure_counterfactual_question_v1_control`: 0 samples), TREATMENT (`arm_exp_channel_a_hook_structure_counterfactual_question_v1_treatment`: 0 samples)
- **Lineage Status:** `INCOMPLETE` (Pending: videos_unpublished, performance_snapshots_pending, outcome_unevaluated, learning_event_unrecorded)

--------------------------------------------------

### Experiment: `exp_channel_a_topic_cluster_modern_warfare_and_geopolitical_divergence_v1`

- **Channel:** `channel_a` | **Status:** `APPROVED` | **Provenance:** `PUBLIC_YOUTUBE`
- **Hypothesis:** Implementing 'Prioritize candidate topics in MODERN_WARFARE_AND_GEOPOLITICAL_DIVERGENCE pool allocation' (derived from external pattern 'Modern Warfare And Geopolitical Divergence Cluster Pattern') will improve channel relative performance by >= 5% in target niche.
- **Variable Under Test:** `TOPIC_CLUSTER` (Single variable isolated)
- **Control Definition:** Standard Chronos Shift Question Hook (e.g. 'What if Rome never fell?')
- **Treatment Definition:** Prioritize candidate topics in MODERN_WARFARE_AND_GEOPOLITICAL_DIVERGENCE pool allocation
- **Success Metric:** `avg_percentage_viewed` (Min $N=4$ per arm)
- **Linked External Prior:** `prior_pat_channel_a_modern_warfare_and_geopolitical_divergence` (Initial Weight: 0.22)
- **Registered Arms:** CONTROL (`arm_exp_channel_a_topic_cluster_modern_warfare_and_geopolitical_divergence_v1_control`: 0 samples), TREATMENT (`arm_exp_channel_a_topic_cluster_modern_warfare_and_geopolitical_divergence_v1_treatment`: 0 samples)
- **Lineage Status:** `INCOMPLETE` (Pending: production_jobs_unstarted, videos_unpublished, performance_snapshots_pending, outcome_unevaluated, learning_event_unrecorded)

--------------------------------------------------

### Experiment: `exp_channel_b_hook_structure_socratic_question_v1`

- **Channel:** `channel_b` | **Status:** `APPROVED` | **Provenance:** `PUBLIC_YOUTUBE`
- **Hypothesis:** Implementing 'Two-host split debate with Host B presenting analytical counter-argument' (derived from external pattern 'Socratic Question Hook Pattern') will improve channel relative performance by >= 5% in target niche.
- **Variable Under Test:** `HOOK_STRUCTURE` (Single variable isolated)
- **Control Definition:** Standard Debate Protocol Neutral Opening
- **Treatment Definition:** Two-host split debate with Host B presenting analytical counter-argument
- **Success Metric:** `engagement_rate` (Min $N=4$ per arm)
- **Linked External Prior:** `prior_pat_channel_b_socratic_question` (Initial Weight: 0.22)
- **Registered Arms:** CONTROL (`arm_exp_channel_b_hook_structure_socratic_question_v1_control`: 0 samples), TREATMENT (`arm_exp_channel_b_hook_structure_socratic_question_v1_treatment`: 0 samples)
- **Lineage Status:** `INCOMPLETE` (Pending: production_jobs_unstarted, videos_unpublished, performance_snapshots_pending, outcome_unevaluated, learning_event_unrecorded)

--------------------------------------------------

### Experiment: `exp_channel_b_topic_cluster_ai_ethics_and_future_dilemmas_v1`

- **Channel:** `channel_b` | **Status:** `APPROVED` | **Provenance:** `PUBLIC_YOUTUBE`
- **Hypothesis:** Implementing 'Prioritize candidate topics in AI_ETHICS_AND_FUTURE_DILEMMAS pool allocation' (derived from external pattern 'Ai Ethics And Future Dilemmas Cluster Pattern') will improve channel relative performance by >= 5% in target niche.
- **Variable Under Test:** `TOPIC_CLUSTER` (Single variable isolated)
- **Control Definition:** Standard Debate Protocol Neutral Opening
- **Treatment Definition:** Prioritize candidate topics in AI_ETHICS_AND_FUTURE_DILEMMAS pool allocation
- **Success Metric:** `engagement_rate` (Min $N=4$ per arm)
- **Linked External Prior:** `prior_pat_channel_b_ai_ethics_and_future_dilemmas` (Initial Weight: 0.21)
- **Registered Arms:** CONTROL (`arm_exp_channel_b_topic_cluster_ai_ethics_and_future_dilemmas_v1_control`: 0 samples), TREATMENT (`arm_exp_channel_b_topic_cluster_ai_ethics_and_future_dilemmas_v1_treatment`: 0 samples)
- **Lineage Status:** `INCOMPLETE` (Pending: production_jobs_unstarted, videos_unpublished, performance_snapshots_pending, outcome_unevaluated, learning_event_unrecorded)

--------------------------------------------------

## 6. Strategy Version Lineage & Mutation Candidates

Strategy promotions require reproducible empirical evidence ($N \ge 4$). The hierarchy is:

`EXTERNAL_PRIOR` → `EXPERIMENTAL` → `SUPPORTED_BY_FIRST_PARTY` → `CANDIDATE_STRATEGY` → `VALIDATED_STRATEGY`

*No pending strategy promotion candidates. Current baseline strategies remain active.*
