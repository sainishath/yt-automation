# -*- coding: utf-8 -*-
"""
pattern_miner.py
----------------
Discovers recurring patterns across multi-channel external video observations.
Calculates pattern frequency, multi-channel corroboration, consistency, and performance evidence.
"""

from collections import defaultdict
from typing import Dict, Any, List, Optional
from growth.external_intelligence.schemas import (
    ExternalVideoModel,
    ExternalPatternModel,
    PatternType,
    ProvenanceSource
)
from growth.external_intelligence.feature_extractor import (
    extract_title_facts,
    infer_title_interpretations
)


def mine_patterns_from_videos(
    target_channel_id: str,
    videos: List[ExternalVideoModel]
) -> List[ExternalPatternModel]:
    """
    Mines empirical patterns from a corpus of observed analog videos.
    Requires patterns to appear across multiple videos and measures performance multipliers.
    """
    if not videos:
        return []

    # Group videos by hook type and topic cluster
    hook_groups: Dict[str, List[ExternalVideoModel]] = defaultdict(list)
    cluster_groups: Dict[str, List[ExternalVideoModel]] = defaultdict(list)
    channel_video_counts: Dict[str, set] = defaultdict(set)

    for v in videos:
        facts = extract_title_facts(v.title)
        interp = infer_title_interpretations(v.title, facts)
        h_type = interp["hook_type"]
        c_type = interp["topic_cluster"]

        hook_groups[h_type].append(v)
        cluster_groups[c_type].append(v)
        channel_video_counts[h_type].add(v.external_channel_id)
        channel_video_counts[c_type].add(v.external_channel_id)

    total_vids = len(videos)
    patterns: List[ExternalPatternModel] = []

    # 1. Mine Hook Structure Patterns
    for hook_name, v_list in hook_groups.items():
        if len(v_list) < 2:
            continue

        freq = round(len(v_list) / max(total_vids, 1), 3)
        ch_count = len(channel_video_counts[hook_name])
        avg_multiplier = round(sum(v.relative_view_multiplier for v in v_list) / len(v_list), 2)
        consistency = round(min(ch_count / 2.0, 1.0) * min(len(v_list) / 4.0, 1.0), 2)
        confidence = round(min(0.5 + (0.2 * ch_count) + (0.1 * min(avg_multiplier, 2.0)), 0.95), 2)

        # Mapping surface technique to underlying principle
        if hook_name == "COUNTERFACTUAL_QUESTION":
            surface = "Opening video with an explicit 'What if...?' question"
            principle = "Triggers hypothetical counterfactual curiosity and narrative anticipation"
            our_impl = "RAG v4 grounded question hook with Whisper-aligned visual beat"
        elif hook_name == "ACTIVE_COUNTERFACTUAL_CLAIM":
            surface = "Opening with a bold conditional claim ('If [X] had happened, [Y] would exist')"
            principle = "Immediate high-stakes world-building without interrogative pause"
            our_impl = "Counterfactual thesis statement in Beat #0 with 0 unsupported claims verification"
        elif hook_name == "DIRECT_PROVOCATION":
            surface = "Direct second-person address ('You are doing X wrong')"
            principle = "Ego engagement and instant cognitive friction"
            our_impl = "Host A provocative debate opening challenging common assumptions"
        elif hook_name == "SOCRATIC_QUESTION":
            surface = "Posing an ethical/psychological paradox question"
            principle = "Invites viewer commentary and dual-perspective reflection"
            our_impl = "Two-host split debate with Host B presenting analytical counter-argument"
        else:
            surface = f"Standard {hook_name} structure"
            principle = "Direct topical presentation"
            our_impl = "Standard production pipeline narration"

        pat_id = f"pat_{target_channel_id}_{hook_name.lower()}"
        pat = ExternalPatternModel(
            pattern_id=pat_id,
            target_channel_id=target_channel_id,
            pattern_type=PatternType.HOOK_STRUCTURE,
            name=f"{hook_name.replace('_', ' ').title()} Hook Pattern",
            description=f"Videos utilizing {hook_name} appear across {ch_count} analog channels with average {avg_multiplier}x baseline views.",
            surface_technique=surface,
            underlying_principle=principle,
            our_possible_implementation=our_impl,
            frequency=freq,
            channel_count=ch_count,
            video_count=len(v_list),
            supporting_observations=[f"obs_fact_title_{v.youtube_video_id}" for v in v_list[:10]],
            consistency_score=consistency,
            confidence=confidence,
            is_simulation=any(v.is_simulation for v in v_list),
            source_type=ProvenanceSource.PUBLIC_YOUTUBE if not any(v.is_simulation for v in v_list) else ProvenanceSource.SIMULATION
        )
        patterns.append(pat)

    # 2. Mine Topic Cluster Patterns
    for cluster_name, v_list in cluster_groups.items():
        if len(v_list) < 2:
            continue

        freq = round(len(v_list) / max(total_vids, 1), 3)
        ch_count = len(channel_video_counts[cluster_name])
        avg_multiplier = round(sum(v.relative_view_multiplier for v in v_list) / len(v_list), 2)
        confidence = round(min(0.6 + (0.15 * ch_count), 0.95), 2)

        pat_id = f"pat_{target_channel_id}_{cluster_name.lower()}"
        pat = ExternalPatternModel(
            pattern_id=pat_id,
            target_channel_id=target_channel_id,
            pattern_type=PatternType.TOPIC_CLUSTER,
            name=f"{cluster_name.replace('_', ' ').title()} Cluster Pattern",
            description=f"Topic cluster {cluster_name} represents {round(freq * 100)}% of high-retention external Shorts.",
            surface_technique=f"Focusing content on {cluster_name}",
            underlying_principle="Audience familiarity and high baseline historical/scientific curiosity",
            our_possible_implementation=f"Prioritize candidate topics in {cluster_name} pool allocation",
            frequency=freq,
            channel_count=ch_count,
            video_count=len(v_list),
            supporting_observations=[f"obs_fact_title_{v.youtube_video_id}" for v in v_list[:10]],
            consistency_score=0.85,
            confidence=confidence,
            is_simulation=any(v.is_simulation for v in v_list),
            source_type=ProvenanceSource.PUBLIC_YOUTUBE if not any(v.is_simulation for v in v_list) else ProvenanceSource.SIMULATION
        )
        patterns.append(pat)

    return patterns
