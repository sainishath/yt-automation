# -*- coding: utf-8 -*-
"""
opportunity_engine.py
---------------------
Discovers, scores, and ranks content opportunities for Content Brain V1.
Uses multi-factor scoring with transparent sub-factor attribution.
"""

from typing import List, Dict, Optional, Any
from growth.brain.schemas import (
    ContentOpportunity,
    EvidenceItem,
    EvidenceSource,
    ConfidenceLevel
)
from growth.brain.memory import BrainMemory
from growth.brain.evidence import EvidenceEvaluator


class OpportunityEngine:
    """
    Ranks potential content ideas across proven, adjacent, and exploratory tiers.
    Balances first-party retention with novelty and experimental value.
    """

    def __init__(self, memory: BrainMemory, evaluator: Optional[EvidenceEvaluator] = None):
        self.memory = memory
        self.evaluator = evaluator or EvidenceEvaluator(memory)

    def rank_opportunities(
        self,
        channel_id: str,
        limit: int = 10
    ) -> List[ContentOpportunity]:
        """
        Discovers candidate topics, scores each across 6 explicit dimensions,
        and returns ranked opportunities with complete explanation.
        """
        raw_candidates = self.memory.get_topic_candidates(channel_id)
        if not raw_candidates:
            # Fallback to strategy pool if candidates table is empty
            strat = self.memory.get_active_strategy(channel_id)
            pool = strat.get("topic_pool", [])
            raw_candidates = [
                {
                    "topic_id": f"topic_{i:03d}",
                    "channel_id": channel_id,
                    "topic_text": t.get("topic", t.get("title", "")),
                    "category": t.get("category", "General"),
                    "cluster": t.get("cluster", "General"),
                    "score": 0.8
                }
                for i, t in enumerate(pool)
            ]

        # Get published topics for similarity/novelty check
        published_vids = self.memory.get_published_videos(channel_id)
        published_titles = [v.get("title", "").lower() for v in published_vids]

        cluster_perf = self.memory.get_cluster_performance(channel_id)
        priors = self.memory.get_external_priors(channel_id)
        active_exps = self.memory.get_experiments(channel_id)["active"]

        opportunities: List[ContentOpportunity] = []

        for cand in raw_candidates:
            topic_text = cand.get("topic_text", "")
            cluster = cand.get("cluster", cand.get("category", "General"))
            angle = cand.get("category", "Speculative Turning Point")

            # 1. First-Party Support (0.0 to 1.0)
            c_stat = cluster_perf.get(cluster)
            if c_stat and c_stat["sample_count"] > 0:
                # Normalized based on APV relative to 80% baseline
                fp_support = min(1.0, c_stat["avg_percentage_viewed"] / 100.0)
            else:
                fp_support = 0.5  # Neutral default

            # 2. Audience / Strategy Fit (0.0 to 1.0)
            aud_fit = float(cand.get("score", 0.75))

            # 3. External Intelligence Support (0.0 to 1.0)
            ext_support = 0.0
            for p in priors:
                if cluster.lower() in p.get("hypothesis", "").lower() or cluster.lower() in p.get("pattern_id", "").lower():
                    ext_support = max(ext_support, p.get("prior_weight", 0.2) * 4.0)

            # 4. Novelty Score (0.0 to 1.0)
            novelty = 1.0
            cand_words = set(topic_text.lower().split())
            for pub in published_titles:
                pub_words = set(pub.split())
                if cand_words and pub_words:
                    jaccard = len(cand_words & pub_words) / len(cand_words | pub_words)
                    if jaccard > 0.4:
                        novelty = min(novelty, max(0.1, 1.0 - jaccard))

            # 5. Experiment Value (0.0 to 1.0)
            # High if an active experiment tests a variable in this domain
            exp_val = 0.5
            for exp in active_exps:
                if exp.get("variable_tested") in ["TOPIC_CLUSTER", "HOOK_STRUCTURE"]:
                    exp_val = 0.85
                    break

            # 6. Production Feasibility
            feasibility = 1.0

            # Penalties
            repetition_penalty = 0.3 if novelty < 0.4 else 0.0
            uncertainty_penalty = 0.15 if (fp_support == 0.5 and ext_support == 0.0) else 0.0

            # Multi-factor score
            overall_score = (
                0.35 * fp_support +
                0.25 * aud_fit +
                0.15 * ext_support +
                0.15 * novelty +
                0.10 * exp_val
                - repetition_penalty
                - uncertainty_penalty
            )
            overall_score = max(0.0, min(1.0, overall_score))

            # Portfolio tier assignment
            if fp_support >= 0.75 and uncertainty_penalty == 0.0:
                tier = "proven"
            elif novelty >= 0.7 and (ext_support > 0.3 or exp_val > 0.7):
                tier = "adjacent"
            else:
                tier = "exploratory"

            # Proposed hook construction
            proposed_hook = f"What if {topic_text.replace('What if ', '').replace('?', '')}?"

            evidence_items, conf = self.evaluator.evaluate_hypothesis_evidence(
                channel_id=channel_id,
                variable="TOPIC_CLUSTER",
                variant_value=cluster,
                topic_cluster=cluster
            )

            explanation = (
                f"Cluster: '{cluster}' (FP Support: {fp_support:.2f}, Fit: {aud_fit:.2f}, "
                f"External: {ext_support:.2f}, Novelty: {novelty:.2f}, Exp Value: {exp_val:.2f}, "
                f"Penalties: -{repetition_penalty + uncertainty_penalty:.2f})"
            )

            opp = ContentOpportunity(
                opportunity_id=f"opp_{cand.get('topic_id', topic_text[:15]).lower().replace(' ', '_')}",
                channel_id=channel_id,
                topic=topic_text,
                topic_cluster=cluster,
                content_angle=angle,
                proposed_hook=proposed_hook,
                audience_reason=f"Targets audience interested in {cluster} turning points.",
                evidence_items=evidence_items,
                novelty_score=novelty,
                experiment_value=exp_val,
                production_feasibility=feasibility,
                first_party_support=fp_support,
                external_support=ext_support,
                uncertainty_penalty=uncertainty_penalty,
                repetition_penalty=repetition_penalty,
                overall_score=overall_score,
                portfolio_tier=tier,
                explanation=explanation
            )
            opportunities.append(opp)

        opportunities.sort(key=lambda o: o.overall_score, reverse=True)
        return opportunities[:limit]
