# -*- coding: utf-8 -*-
"""
topic_pool.py
-------------
Manages structured topic pools for Channel A and Channel B with balanced
portfolio allocation: 70% proven concepts, 20% adjacent, 10% high-risk experiments.
"""

from typing import List, Dict, Any
from growth.topic_engine.topic_scorer import score_topic
from growth.topic_engine.deduplicator import is_duplicate_topic


DEFAULT_CHANNEL_A_TOPICS = [
    {"topic": "What if the Roman Empire never fell?", "category": "Empire", "cluster": "Classical", "risk": "proven"},
    {"topic": "What if the Library of Alexandria survived?", "category": "Knowledge", "cluster": "Antiquity", "risk": "proven"},
    {"topic": "What if the Spanish Armada conquered England?", "category": "Empire", "cluster": "Early Modern", "risk": "proven"},
    {"topic": "What if the steam engine was adopted in Ancient Greece?", "category": "Tech", "cluster": "Antiquity", "risk": "adjacent"},
    {"topic": "What if the Cold War turned hot in 1962?", "category": "Geopolitics", "cluster": "Modern", "risk": "adjacent"},
    {"topic": "What if Neanderthals coexisted with modern civilization?", "category": "Evolution", "cluster": "Prehistory", "risk": "high_risk"},
]

DEFAULT_CHANNEL_B_TOPICS = [
    {"topic": "Why your brain forgets names in three seconds", "category": "Psychology", "cluster": "Memory", "risk": "proven"},
    {"topic": "Why you wake up at 3:17 AM every night", "category": "Biology", "cluster": "Sleep", "risk": "proven"},
    {"topic": "Can AI ever experience subjective pain?", "category": "AI Ethics", "cluster": "Singularity", "risk": "proven"},
    {"topic": "How negotiators use silence to control conversations", "category": "Dark Psychology", "cluster": "Social", "risk": "adjacent"},
    {"topic": "The Ship of Theseus paradox explained in 40 seconds", "category": "Philosophy", "cluster": "Paradox", "risk": "adjacent"},
    {"topic": "Are we living inside an ancestor simulation?", "category": "Philosophy", "cluster": "Cosmology", "risk": "high_risk"},
]


class TopicPoolManager:
    def __init__(self, channel_id: str):
        self.channel_id = channel_id
        self.raw_pool = DEFAULT_CHANNEL_A_TOPICS if channel_id == "channel_a" else DEFAULT_CHANNEL_B_TOPICS
        self.published_history: List[str] = []

    def set_published_history(self, history: List[str]) -> None:
        self.published_history = history

    def get_ranked_candidates(self) -> List[Dict[str, Any]]:
        """Returns non-duplicate candidate topics sorted by composite topic score."""
        ranked = []
        for item in self.raw_pool:
            topic_str = item["topic"]
            is_dup, matched = is_duplicate_topic(topic_str, self.published_history)
            if is_dup:
                continue

            score_res = score_topic(topic_str, self.channel_id, item["category"])
            ranked.append({
                "topic": topic_str,
                "category": item["category"],
                "cluster": item["cluster"],
                "risk_tier": item["risk"],
                "score": score_res["final_score"],
                "breakdown": score_res["breakdown"],
                "reason": score_res["reason"]
            })

        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked
