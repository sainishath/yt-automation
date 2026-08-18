# -*- coding: utf-8 -*-
"""
deduplicator.py
---------------
Detects duplicate or near-duplicate topics using token Jaccard similarity
and historical entity overlap.
"""

import re
from typing import List, Set, Tuple


def _normalize_tokens(text: str) -> Set[str]:
    """Tokenizes and removes common stop words for comparison."""
    stopwords = {"what", "if", "the", "a", "an", "in", "of", "and", "to", "why", "how", "did", "never", "ever"}
    words = re.findall(r"\b[a-zA-Z0-9]+\b", text.lower())
    return {w for w in words if w not in stopwords}


def calculate_topic_similarity(topic_a: str, topic_b: str) -> float:
    """Computes token Jaccard similarity between two topic strings."""
    tokens_a = _normalize_tokens(topic_a)
    tokens_b = _normalize_tokens(topic_b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a.intersection(tokens_b)
    union = tokens_a.union(tokens_b)
    return len(intersection) / len(union)


def is_duplicate_topic(candidate_topic: str, existing_topics: List[str], threshold: float = 0.65) -> Tuple[bool, str]:
    """
    Checks if candidate topic is too similar to any existing topic.
    Returns (is_duplicate, matching_topic).
    """
    for ex in existing_topics:
        sim = calculate_topic_similarity(candidate_topic, ex)
        if sim >= threshold:
            return True, ex
    return False, ""
