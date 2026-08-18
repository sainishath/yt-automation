# -*- coding: utf-8 -*-
"""
repetition_guard.py
-------------------
Anti-Repetition Engine protecting channels from repetitive or mass-produced content.
Evaluates lexical tokens, character n-grams, and entity overlaps to ensure freshness and originality.
"""

import re
from typing import List, Dict, Any, Tuple, Optional


def tokenize_clean(text: str) -> set:
    """Extracts cleaned lowercase word tokens, stripping punctuation and common stopwords."""
    stopwords = {"what", "if", "the", "a", "an", "and", "or", "in", "on", "of", "to", "for", "with", "by", "about", "how", "why"}
    words = re.findall(r"\b[a-zA-Z0-9]+\b", text.lower())
    return {w for w in words if w not in stopwords and len(w) > 1}


def get_character_ngrams(text: str, n: int = 3) -> set:
    """Extracts character n-grams from cleaned text."""
    clean = re.sub(r"\s+", " ", text.lower().strip())
    if len(clean) < n:
        return {clean}
    return {clean[i:i+n] for i in range(len(clean) - n + 1)}


def check_repetition(
    candidate_title: str,
    candidate_hook: str,
    historical_entries: List[Dict[str, Any]],
    token_threshold: float = 0.60,
    ngram_threshold: float = 0.55
) -> Dict[str, Any]:
    """
    Checks candidate title and hook against historical video assets.
    Returns audit dictionary with allowed status and match details.
    """
    cand_title_tokens = tokenize_clean(candidate_title)
    cand_hook_tokens = tokenize_clean(candidate_hook)
    cand_title_ngrams = get_character_ngrams(candidate_title)

    for entry in historical_entries:
        hist_title = entry.get("title", "")
        hist_hook = entry.get("hook_text", "")
        vid_id = entry.get("video_id", "unknown")

        hist_title_tokens = tokenize_clean(hist_title)
        hist_hook_tokens = tokenize_clean(hist_hook)
        hist_title_ngrams = get_character_ngrams(hist_title)

        # Title Token Jaccard
        if cand_title_tokens and hist_title_tokens:
            t_inter = len(cand_title_tokens & hist_title_tokens)
            t_union = len(cand_title_tokens | hist_title_tokens)
            t_sim = t_inter / max(t_union, 1)
            if t_sim >= token_threshold:
                return {
                    "allowed": False,
                    "reason": f"Title token similarity {round(t_sim, 2)} exceeds threshold {token_threshold}",
                    "matched_video_id": vid_id,
                    "matched_title": hist_title,
                    "similarity_score": round(t_sim, 2)
                }

        # Title N-gram Jaccard
        if cand_title_ngrams and hist_title_ngrams:
            ng_inter = len(cand_title_ngrams & hist_title_ngrams)
            ng_union = len(cand_title_ngrams | hist_title_ngrams)
            ng_sim = ng_inter / max(ng_union, 1)
            if ng_sim >= ngram_threshold:
                return {
                    "allowed": False,
                    "reason": f"Title character n-gram overlap {round(ng_sim, 2)} exceeds threshold {ngram_threshold}",
                    "matched_video_id": vid_id,
                    "matched_title": hist_title,
                    "similarity_score": round(ng_sim, 2)
                }

        # Hook Token Jaccard
        if cand_hook_tokens and hist_hook_tokens:
            h_inter = len(cand_hook_tokens & hist_hook_tokens)
            h_union = len(cand_hook_tokens | hist_hook_tokens)
            h_sim = h_inter / max(h_union, 1)
            if h_sim >= token_threshold:
                return {
                    "allowed": False,
                    "reason": f"Hook token similarity {round(h_sim, 2)} exceeds threshold {token_threshold}",
                    "matched_video_id": vid_id,
                    "matched_hook": hist_hook,
                    "similarity_score": round(h_sim, 2)
                }

    return {
        "allowed": True,
        "reason": "Originality check passed with zero excessive overlap",
        "matched_video_id": None,
        "similarity_score": 0.0
    }
