# -*- coding: utf-8 -*-
"""
visual_scene_planner.py
-----------------------
Standalone Pipeline-1 module for semantic visual scene planning.

Utilizes local Ollama (llama3.2:latest) to analyze narration text and identify
semantic visual beats, then uses deterministic token matching against
alignment_cache.json to establish accurate audio-driven start and end timestamps.

Output: output/{video_id}/scene_plan.json
"""

import os
import sys
import json
import time
import re
import requests
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Import local whisper_alignment and rag_grounding modules
sys.path.append(str(Path(__file__).parent))
from whisper_alignment import normalize_word, align_video_job
from rag_grounding import retrieve_beat_visual_evidence

# Setup logging to pipeline.log and stdout
LOG_FILE = Path("pipeline.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "llama3.2:latest"

def parse_llm_json(raw_text: str, default: Any = None) -> Any:
    """Safely extracts and parses JSON content from LLM output, stripping markdown code fences."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        return default

def build_full_narration(scenes: List[Dict[str, Any]]) -> str:
    """Concatenates all scene narrations into a clean, single text string."""
    return " ".join([s.get("narration", "").strip() for s in scenes if s.get("narration", "").strip()])

def align_excerpt_to_timeline(
    excerpt: str,
    global_timeline: List[Dict[str, Any]],
    fallback_start: float = 0.0,
    fallback_end: float = 5.0
) -> Tuple[float, float, str]:
    """
    Deterministically maps a narration text excerpt onto Whisper word global timeline tokens.
    Returns (start_time, end_time, status).
    """
    excerpt_tokens = [normalize_word(t) for t in excerpt.split() if normalize_word(t)]
    if not excerpt_tokens or not global_timeline:
        return (fallback_start, fallback_end, "fallback_empty")

    timeline_tokens = [w.get("normalized", "") for w in global_timeline]
    
    # Subsequence matching algorithm
    best_start_idx = -1
    best_end_idx = -1
    best_match_score = 0

    first_tok = excerpt_tokens[0]
    last_tok = excerpt_tokens[-1]

    # 1. Search for first token match
    candidate_start_indices = [i for i, tok in enumerate(timeline_tokens) if tok == first_tok]

    if not candidate_start_indices:
        # Fallback: search for any partial match of the first 3 tokens
        for i, tok in enumerate(timeline_tokens):
            if any(tok == et for et in excerpt_tokens[:3]):
                candidate_start_indices.append(i)

    for s_idx in candidate_start_indices:
        # Look ahead for last token or sequential matching
        e_idx = s_idx + len(excerpt_tokens) - 1
        if e_idx < len(timeline_tokens) and timeline_tokens[e_idx] == last_tok:
            best_start_idx = s_idx
            best_end_idx = e_idx
            best_match_score = len(excerpt_tokens)
            break

        # Bounded search window within len(excerpt_tokens) + 4
        search_max = min(len(timeline_tokens), s_idx + len(excerpt_tokens) + 4)
        for cand_e in range(s_idx, search_max):
            if timeline_tokens[cand_e] == last_tok:
                score = sum(1 for a, b in zip(excerpt_tokens, timeline_tokens[s_idx:cand_e+1]) if a == b)
                if score > best_match_score:
                    best_start_idx = s_idx
                    best_end_idx = cand_e
                    best_match_score = score

    if best_start_idx != -1 and best_end_idx != -1:
        start_time = global_timeline[best_start_idx]["global_start"]
        end_time = global_timeline[best_end_idx]["global_end"]
        if end_time > start_time:
            return (round(start_time, 3), round(end_time, 3), "aligned")

    # Fallback ratio match if exact token sequence matching failed
    logging.warning(f"[Visual Planner Warning] Token alignment exact match failed for: '{excerpt[:40]}...'. Using ratio fallback.")
    return (fallback_start, fallback_end, "fallback_ratio")

def request_ollama_semantic_beats(
    topic: str,
    grounding_facts: str,
    full_narration: str,
    max_retries: int = 2
) -> List[Dict[str, Any]]:
    """
    Queries Ollama (llama3.2:latest) to group narration text into semantic visual beats.
    The LLM outputs strictly semantic JSON with verbatim narration text excerpts (NO timestamps).
    """
    prompt = f"""You are an expert visual director for historical YouTube Shorts.
Your task is to break down the following historical narration into distinct SEMANTIC VISUAL BEATS.

Topic: "{topic}"
Era Grounding Facts: "{grounding_facts}"

Full Spoken Narration:
"{full_narration}"

CRITICAL VISUAL DIRECTIVES:
1. ORIGINAL SCENE BOUNDARIES ARE NOT VISUAL BOUNDARIES. Treat narration as a continuous stream.
2. NEVER assume:
   - one input scene = one visual beat
   - one sentence = one visual beat
   - every sentence requires a new image
3. YOU MUST SPLIT A SENTENCE when it contains multiple visually distinct events:
   EXAMPLE OF SPLITTING A COMPOUND SENTENCE:
   Text: "At dawn, Caesar's fleet entered Alexandria harbor, and hours later catastrophic flames erupted from the docks."
   -> Beat 1 excerpt: "At dawn, Caesar's fleet entered Alexandria harbor," (Visual: Roman fleet anchoring at dawn)
   -> Beat 2 excerpt: "and hours later catastrophic flames erupted from the docks." (Visual: Docks engulfed in fire)
4. YOU SHOULD MERGE CONSECUTIVE SENTENCES when they describe the exact same subject, location, action, and visual state:
   EXAMPLE OF MERGING CONSECUTIVE SENTENCES:
   Text: "Ancient scrolls burned in the dark hall. Rare manuscripts turned to ash."
   -> Beat excerpt: "Ancient scrolls burned in the dark hall. Rare manuscripts turned to ash." (Visual: Close-up of burning papyrus manuscripts)
5. CREATE A NEW BEAT ONLY when there is a meaningful visual change such as:
   - new subject
   - new location
   - major action change
   - cause/effect event
   - time transition
   - before/after state
   - major change in scale or perspective
   - major emotional/narrative transition
6. Do NOT create a new beat merely because a sentence ended, punctuation appeared, or the original script scene changed.
7. Target visual beat duration is roughly 3.5 to 5.5 seconds of spoken text.
8. EVERY beat MUST contain a "narration_text_excerpt" that is an EXACT, UNMODIFIED, CONTIGUOUS excerpt copied directly from the Full Spoken Narration text above. Do NOT paraphrase or alter any words.
9. DO NOT output any numeric timestamps, start times, end times, or durations. Python will derive all timestamps deterministically.

Return ONLY a valid JSON object in this exact schema:
{{
  "visual_beats": [
    {{
      "beat_id": "beat_001",
      "narration_text_excerpt": "Exact verbatim excerpt copied from narration",
      "visual_concept": "Detailed description of what is visually visible",
      "camera_shot": "Cinematic camera angle (e.g. Cinematic wide shot, Medium action shot, Close-up)",
      "visual_transition_reason": "Specific semantic visual reason why the image changes here"
    }}
  ]
}}
"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.3
        }
    }

    for attempt in range(1, max_retries + 1):
        try:
            logging.info(f"[Visual Planner] Querying Ollama for semantic visual beats (Attempt {attempt}/{max_retries})...")
            response = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=90)
            response.raise_for_status()

            raw = response.json().get("response", "").strip()
            parsed = parse_llm_json(raw, {})
            beats = parsed.get("visual_beats", [])
            if isinstance(beats, list) and len(beats) > 0:
                logging.info(f"[Visual Planner] Successfully received {len(beats)} semantic beats from Ollama.")
                return beats
            else:
                logging.warning(f"[Visual Planner Warning] Ollama returned empty or invalid beats list on attempt {attempt}.")
        except Exception as e:
            logging.warning(f"[Visual Planner Warning] Ollama query attempt {attempt} failed: {e}")

    return []

def apply_duration_validation_rules(
    beats: List[Dict[str, Any]],
    total_duration: float
) -> List[Dict[str, Any]]:
    """
    Applies deterministic duration validation & rules to aligned visual beats:
    - Guarantees complete continuous timeline (start_0 = 0.0, end_last = total_duration, start_i = end_{i-1}).
    - Merges beats shorter than 2.5s with adjacent beats.
    - Splits beats longer than 7.0s at sentence/phrase midpoints into 2 camera angles.
    """
    if not beats:
        return []

    # 1. Enforce timeline continuity (no gaps or overlaps)
    current_time = 0.0
    for idx, beat in enumerate(beats):
        b_start = current_time
        b_end = beat.get("end_time", b_start + 4.0)

        # Final beat extends to total duration
        if idx == len(beats) - 1:
            b_end = max(b_start + 2.5, total_duration)
        elif b_end <= b_start + 1.0:
            b_end = round(b_start + 4.0, 3)

        beat["start_time"] = round(b_start, 3)
        beat["end_time"] = round(b_end, 3)
        beat["duration"] = round(b_end - b_start, 3)
        current_time = b_end

    # 2. Merge short beats (< 2.5s) into previous beat where possible
    merged_beats = []
    for beat in beats:
        if merged_beats and beat["duration"] < 2.5:
            prev = merged_beats[-1]
            prev["end_time"] = beat["end_time"]
            prev["duration"] = round(prev["end_time"] - prev["start_time"], 3)
            prev["narration_text"] += " " + beat["narration_text"]
            prev["visual_concept"] += f" / {beat['visual_concept']}"
            logging.info(f"[Visual Planner Rule] Merged short beat ({beat['duration']:.2f}s) into beat '{prev['beat_id']}'.")
        else:
            merged_beats.append(beat)

    # 3. Split long beats (> 7.0s) into 2 visual camera variations
    final_beats = []
    beat_counter = 1
    for beat in merged_beats:
        dur = beat["duration"]
        if dur > 7.0:
            mid_time = round(beat["start_time"] + (dur / 2.0), 3)
            
            # Beat Part 1
            b1 = dict(beat)
            b1["beat_id"] = f"beat_{beat_counter:03d}"
            b1["end_time"] = mid_time
            b1["duration"] = round(mid_time - beat["start_time"], 3)
            b1["camera_shot"] = "Cinematic wide shot"
            final_beats.append(b1)
            beat_counter += 1

            # Beat Part 2
            b2 = dict(beat)
            b2["beat_id"] = f"beat_{beat_counter:03d}"
            b2["start_time"] = mid_time
            b2["duration"] = round(beat["end_time"] - mid_time, 3)
            b2["camera_shot"] = "Medium detailed shot"
            b2["visual_concept"] = f"Detailed view of {beat['visual_concept']}"
            final_beats.append(b2)
            beat_counter += 1
            logging.info(f"[Visual Planner Rule] Split long beat ({dur:.2f}s) into two distinct camera shots.")
        else:
            beat["beat_id"] = f"beat_{beat_counter:03d}"
            final_beats.append(beat)
            beat_counter += 1

    return final_beats

def build_fallback_scene_plan(
    script: Dict[str, Any],
    alignment_cache: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Creates a deterministic sentence-boundary fallback scene plan
    if Ollama is offline or fails to return structured JSON.
    """
    logging.warning("[Visual Planner Fallback] Using sentence-boundary fallback scene planner.")
    scenes = script.get("scenes", [])
    global_timeline = alignment_cache.get("global_timeline", [])
    total_duration = alignment_cache.get("total_duration", 40.0)

    fallback_beats = []
    global_offset = 0.0

    for idx, s in enumerate(scenes):
        narration = s.get("narration", "")
        s_dur = s.get("actual_duration_seconds", s.get("estimated_duration_seconds", 5.0))
        vis_prompt = s.get("visual_prompt", f"Cinematic shot illustrating {script.get('topic')}")

        start_t = round(global_offset, 3)
        end_t = round(global_offset + s_dur, 3)
        if idx == len(scenes) - 1:
            end_t = total_duration

        fallback_beats.append({
            "beat_id": f"beat_{idx+1:03d}",
            "start_time": start_t,
            "end_time": end_t,
            "duration": round(end_t - start_t, 3),
            "narration_text": narration,
            "visual_concept": narration[:60],
            "visual_prompt": vis_prompt,
            "camera_shot": "Cinematic shot",
            "visual_transition_reason": "Script scene transition (fallback)",
            "alignment_status": "fallback_scene",
            "generation_status": "pending"
        })
        global_offset += s_dur

    return fallback_beats

def plan_visual_scenes(
    video_id: str,
    output_dir: str = "output",
    force_rebuild: bool = False
) -> Dict[str, Any]:
    """
    Main orchestration function for Stage 3 Visual Scene Planning.
    Produces output/{video_id}/scene_plan.json.
    """
    video_path = Path(output_dir) / video_id
    script_path = video_path / "script.json"
    audio_dir = video_path / "audio"
    cache_path = audio_dir / "alignment_cache.json"
    plan_output_path = video_path / "scene_plan.json"

    if not script_path.exists():
        raise FileNotFoundError(f"script.json not found for {video_id} at {script_path}")

    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    # Guarantee alignment_cache.json exists
    if not cache_path.exists() or force_rebuild:
        alignment_cache = align_video_job(video_id, output_dir, force_rebuild=force_rebuild)
    else:
        with open(cache_path, "r", encoding="utf-8") as cf:
            alignment_cache = json.load(cf)

    topic = script.get("topic", "Alternate History")
    grounding_facts = script.get("grounding_facts", "Historical era styling locked to pre-industrial period.")
    scenes = script.get("scenes", [])
    full_narration = build_full_narration(scenes)
    global_timeline = alignment_cache.get("global_timeline", [])
    total_duration = alignment_cache.get("total_duration", 40.0)

    # Load RAG v4 evidence packet if available
    evidence_packet = {}
    packet_path = video_path / "evidence_packet.json"
    if packet_path.exists():
        try:
            with open(packet_path, "r", encoding="utf-8") as ef:
                evidence_packet = json.load(ef)
        except Exception as e:
            logging.warning(f"[Visual Planner Warning] Failed loading evidence packet: {e}")

    # 1. Request semantic visual beats from Ollama
    raw_beats = request_ollama_semantic_beats(topic, grounding_facts, full_narration)
    planner_mode = "llm_semantic"

    if not raw_beats:
        raw_beats = build_fallback_scene_plan(script, alignment_cache)
        planner_mode = "fallback"

    # 2. Perform deterministic text-to-Whisper alignment and RAG v4 visual evidence grounding
    aligned_beats = []
    current_time = 0.0

    if planner_mode == "llm_semantic":
        for idx, beat in enumerate(raw_beats):
            excerpt = beat.get("narration_text_excerpt", "")
            est_beat_dur = total_duration / len(raw_beats)
            fallback_start = current_time
            fallback_end = min(total_duration, current_time + est_beat_dur)

            start_t, end_t, align_status = align_excerpt_to_timeline(
                excerpt, global_timeline, fallback_start, fallback_end
            )

            cam_shot = beat.get("camera_shot", "Cinematic wide shot")
            vis_concept = beat.get("visual_concept", excerpt[:60])

            # Retrieve beat-specific visual evidence and anachronism rules from RAG v4
            beat_evidence = retrieve_beat_visual_evidence(evidence_packet, excerpt, vis_concept) if evidence_packet else {}
            prompt_hint = beat_evidence.get("visual_prompt_hint", "")

            if prompt_hint:
                enriched_prompt = f"{cam_shot} of {vis_concept}. {prompt_hint}, 8k resolution, highly detailed, masterwork."
            else:
                enriched_prompt = f"{cam_shot} of {vis_concept}. Era details: {grounding_facts[:120]}, 8k resolution, highly detailed, masterwork."

            aligned_beats.append({
                "beat_id": f"beat_{idx+1:03d}",
                "start_time": start_t,
                "end_time": end_t,
                "duration": round(end_t - start_t, 3),
                "narration_text": excerpt,
                "visual_concept": vis_concept,
                "visual_prompt": enriched_prompt,
                "camera_shot": cam_shot,
                "rag_visual_evidence": [v.get("description", "") for v in beat_evidence.get("relevant_visual_evidence", [])],
                "rag_must_include": beat_evidence.get("must_include", []),
                "rag_avoid_anachronisms": beat_evidence.get("avoid_anachronisms", []),
                "visual_transition_reason": beat.get("visual_transition_reason", "Semantic beat transition"),
                "alignment_status": align_status,
                "generation_status": "pending"
            })
            current_time = end_t
    else:
        aligned_beats = raw_beats

    # 3. Apply post-alignment duration validation & rules
    final_beats = apply_duration_validation_rules(aligned_beats, total_duration)

    scene_plan = {
        "video_id": video_id,
        "topic": topic,
        "total_duration_seconds": total_duration,
        "planner_model": OLLAMA_MODEL if planner_mode == "llm_semantic" else "fallback_rules",
        "planner_mode": planner_mode,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_beats": len(final_beats),
        "visual_beats": final_beats
    }

    # Write output scene_plan.json
    with open(plan_output_path, "w", encoding="utf-8") as pf:
        json.dump(scene_plan, pf, indent=2, ensure_ascii=False)

    logging.info(f"[Visual Planner] Successfully created scene_plan.json at {plan_output_path} with {len(final_beats)} beats.")
    return scene_plan

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standalone Visual Scene Planner for Pipeline 1")
    parser.add_argument("--video_id", required=True, help="Video folder ID to plan")
    parser.add_argument("--output_dir", default="output", help="Base output directory")
    parser.add_argument("--force", action="store_true", help="Force rebuild scene plan")
    args = parser.parse_args()

    try:
        plan = plan_visual_scenes(args.video_id, args.output_dir, force_rebuild=args.force)
        print(f"\n==============================================")
        print(f"  Visual Scene Plan Summary: {plan['video_id']} ")
        print(f"  Mode: {plan['planner_mode']} | Beats: {plan['total_beats']} | Duration: {plan['total_duration_seconds']}s")
        print("==============================================\n")
        print(f"{'Beat ID':<9} | {'Timeline (s)':<15} | {'Duration':<8} | {'Camera Shot':<20} | {'Visual Concept'}")
        print("-" * 80)
        for b in plan["visual_beats"]:
            time_str = f"[{b['start_time']:05.2f} - {b['end_time']:05.2f}]"
            print(f"{b['beat_id']:<9} | {time_str:<15} | {b['duration']:<8.2f} | {b['camera_shot']:<20} | {b['visual_concept'][:30]}")
        print("-" * 80 + "\n")
        print(f"OK Scene plan saved to: output/{args.video_id}/scene_plan.json")
    except Exception as e:
        logging.error(f"Visual scene planning failed: {e}")
        sys.exit(1)
