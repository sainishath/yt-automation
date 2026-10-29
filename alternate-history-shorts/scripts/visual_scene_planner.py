# -*- coding: utf-8 -*-
"""
visual_scene_planner.py
-----------------------
Standalone Pipeline-1 module for semantic visual scene planning.

Utilizes local Ollama to analyze narration text and identify
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

# Import local whisper_alignment, rag_grounding, and pipeline.compositor modules
sys.path.append(str(Path(__file__).parent))
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from whisper_alignment import normalize_word, align_video_job
from rag_grounding import retrieve_beat_visual_evidence
from pipeline.compositor import FOOOCUS_NEGATIVE_PROMPT_LOCK, build_fooocus_scene_prompt

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

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("SCENE_PLANNER_MODEL", os.getenv("OLLAMA_FALLBACK_MODEL", "qwen2.5-coder:7b"))

def parse_llm_json(raw_text: str, default: Any = None) -> Any:
    """Safely extracts and parses JSON content from LLM output, stripping markdown code fences or surrounding text."""
    text = raw_text.strip()
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
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
        match = re.search(r'(\{.*\})', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
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
    Queries Ollama to group narration text into semantic visual beats.
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
2. FAST VISUAL PACING (HIGH RETENTION REQUIREMENT):
   - In the FIRST 6 SECONDS, enforce a visual cut every 2.0 to 2.5 seconds (at least 3 distinct visual shots in the opening hook).
   - Across the entire Short, generate 10 to 12 distinct visual beats (average 2.5 to 3.2 seconds per shot).
   - NEVER allow a single image to remain on screen for more than 3.5 seconds.
3. DIVERSE CINEMATIC CAMERA FRAMING (SINGLE FULL-BLEED 9:16 FRAME, NO SPLIT SCREEN, NO POSTERS/TEXT):
   - Cycle dynamically across varied framing angles:
     * "Extreme close-up portrait of..." (intense weathered face, eyes, historical commander or figure)
     * "Overhead strategic war map depicting..." (tactical cartography without text labels, terrain, military formations)
     * "Low-angle architectural shot of..." (towering stone columns, aqueducts, monuments)
     * "Dramatic over-the-shoulder view of..." (commander looking over legions or assembly)
     * "Macro cinematic detail of..." (iron forge, wax seal, papyrus scroll)
   - STRICT BAN: NEVER request posters, signage, typography, or split-screen collages.
4. YOU MUST SPLIT A SENTENCE when it contains multiple visually distinct events or exceeds 2.5 seconds.
5. EVERY beat MUST contain a "narration_text_excerpt" that is an EXACT, UNMODIFIED, CONTIGUOUS excerpt copied directly from the Full Spoken Narration text above. Do NOT paraphrase.
6. EVERY beat MUST define a primary visual focal target:
   - "focal_keyword": A single critical word from the excerpt that represents the subject being highlighted.
   - "focal_u": Normalized horizontal coordinate (0.20 to 0.80, default 0.50).
   - "focal_v": Normalized vertical coordinate (0.20 to 0.65, default 0.40).
   - "zoom_target": Slow zoom target factor (1.04 to 1.18, default 1.12).

Return ONLY a valid JSON object in this exact schema:
{{
  "visual_beats": [
    {{
      "beat_id": "beat_001",
      "narration_text_excerpt": "Exact verbatim excerpt copied from narration",
      "visual_concept": "Detailed description of what is visually visible with lighting and mood (no text, no split screen)",
      "camera_shot": "Extreme close-up portrait | Overhead strategic war map | Low-angle architectural shot | Dramatic over-the-shoulder | Macro cinematic detail",
      "focal_keyword": "flames",
      "focal_u": 0.50,
      "focal_v": 0.40,
      "zoom_target": 1.12,
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
                try:
                    requests.post(f"{OLLAMA_URL}/api/generate", json={"model": OLLAMA_MODEL, "keep_alive": 0}, timeout=2)
                except Exception:
                    pass
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
    - Merges beats shorter than 1.6s with adjacent beats.
    - Splits beats longer than 2.6s (first 6s) or 3.6s into 2 camera angles.
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

    # 2. Merge only micro-beats (< 1.6s) into previous beat where possible
    merged_beats = []
    for beat in beats:
        if merged_beats and beat["duration"] < 1.6:
            prev = merged_beats[-1]
            prev["end_time"] = beat["end_time"]
            prev["duration"] = round(prev["end_time"] - prev["start_time"], 3)
            prev["narration_text"] += " " + beat["narration_text"]
            prev["visual_concept"] += f" / {beat['visual_concept']}"
            logging.info(f"[Visual Planner Rule] Merged micro-beat ({beat['duration']:.2f}s) into beat '{prev['beat_id']}'.")
        else:
            merged_beats.append(beat)

    # 3. Dynamic Camera Angle Palette
    camera_cycle = [
        ("Extreme close-up portrait", "Intense close-up view focusing on expression and eyes"),
        ("Overhead strategic war map", "Tactical cartography with regional borders and territorial movements"),
        ("Low-angle architectural shot", "Dramatic low-angle view emphasizing massive stone structures and scale"),
        ("Dramatic over-the-shoulder", "Over-the-shoulder perspective observing the historical event"),
        ("Macro cinematic detail", "Detailed macro shot focusing on technology, forged iron, or documents")
    ]

    # 4. Split beats longer than 2.6s in first 6s, or longer than 3.6s afterwards
    split_beats = []
    for beat in merged_beats:
        dur = beat["duration"]
        start_t = beat["start_time"]
        max_allowed = 2.6 if start_t < 6.0 else 3.6
        if dur > max_allowed:
            mid_time = round(start_t + (dur / 2.0), 3)
            
            b1 = dict(beat)
            b1["end_time"] = mid_time
            b1["duration"] = round(mid_time - start_t, 3)
            split_beats.append(b1)

            b2 = dict(beat)
            b2["start_time"] = mid_time
            b2["duration"] = round(beat["end_time"] - mid_time, 3)
            cycle_idx = len(split_beats) % len(camera_cycle)
            b2["camera_shot"] = camera_cycle[cycle_idx][0]
            b2["visual_concept"] = f"{camera_cycle[cycle_idx][1]} of {beat.get('visual_concept', '')}"
            split_beats.append(b2)
            logging.info(f"[Visual Planner Rule] Split long beat ({dur:.2f}s) into two camera angles for fast pacing.")
        else:
            split_beats.append(beat)

    # 5. Guarantee 10-12 visual beats per Short: split longest if < 10, merge shortest if > 12
    while len(split_beats) < 10 and len(split_beats) > 0:
        longest_idx = max(range(len(split_beats)), key=lambda i: split_beats[i]["duration"])
        target = split_beats[longest_idx]
        if target["duration"] < 2.0:
            break
        dur = target["duration"]
        mid = round(target["start_time"] + (dur / 2.0), 3)
        b1 = dict(target)
        b1["end_time"] = mid
        b1["duration"] = round(mid - target["start_time"], 3)
        
        b2 = dict(target)
        b2["start_time"] = mid
        b2["duration"] = round(target["end_time"] - mid, 3)
        cycle_idx = len(split_beats) % len(camera_cycle)
        b2["camera_shot"] = camera_cycle[cycle_idx][0]
        b2["visual_concept"] = f"{camera_cycle[cycle_idx][1]} of {target.get('visual_concept', '')}"

        split_beats[longest_idx] = b1
        split_beats.insert(longest_idx + 1, b2)

    while len(split_beats) > 12:
        best_merge_idx = min(range(len(split_beats) - 1), key=lambda i: split_beats[i]["duration"] + split_beats[i+1]["duration"])
        prev = split_beats[best_merge_idx]
        curr = split_beats[best_merge_idx + 1]
        prev["end_time"] = curr["end_time"]
        prev["duration"] = round(prev["end_time"] - prev["start_time"], 3)
        prev["narration_text"] += " " + curr.get("narration_text", "")
        prev["visual_concept"] += " / " + curr.get("visual_concept", "")
        split_beats.pop(best_merge_idx + 1)

    # 6. Normalize beat timeline strictly to [0.0, total_duration]
    total_beats_duration = sum(max(0.5, b["duration"]) for b in split_beats)
    scale = total_duration / total_beats_duration if total_beats_duration > 0 else 1.0

    curr_time = 0.0
    for idx, beat in enumerate(split_beats):
        b_dur = round(max(0.5, beat["duration"]) * scale, 3)
        b_start = round(curr_time, 3)
        b_end = round(curr_time + b_dur, 3) if idx < len(split_beats) - 1 else total_duration
        beat["start_time"] = b_start
        beat["end_time"] = b_end
        beat["duration"] = round(b_end - b_start, 3)
        curr_time = b_end

    # Assign sequential IDs and enforce varied camera shot metadata
    final_beats = []
    for idx, beat in enumerate(split_beats):
        beat["beat_id"] = f"beat_{idx+1:03d}"
        if not beat.get("camera_shot") or "wide" in beat.get("camera_shot", "").lower():
            cycle_idx = idx % len(camera_cycle)
            beat["camera_shot"] = camera_cycle[cycle_idx][0]
        final_beats.append(beat)

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
    total_duration = alignment_cache.get("total_duration", 40.0)

    fallback_beats = []
    global_offset = 0.0

    for idx, s in enumerate(scenes):
        narration = s.get("narration", "")
        s_dur = s.get("actual_duration_seconds", s.get("estimated_duration_seconds", 5.0))
        raw_vis_prompt = s.get("visual_prompt", f"Cinematic shot illustrating {script.get('topic')}")
        fooocus_spec = build_fooocus_scene_prompt(raw_vis_prompt, script.get("topic", "Historical era"))

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
            "visual_prompt": fooocus_spec["prompt"],
            "negative_prompt": fooocus_spec["negative_prompt"],
            "camera_shot": "Cinematic shot",
            "visual_transition_reason": "Script scene transition (fallback)",
            "alignment_status": "fallback_scene",
            "generation_status": "pending"
        })
        global_offset += s_dur

    return fallback_beats

def clean_visual_prompt_string(cam_shot: str, vis_concept: str, prompt_hint: str) -> str:
    """
    Constructs a clean, single-frame vertical 9:16 Fooocus visual prompt.
    Strips any split-screen, collage, or poster-text triggers to prevent AI gibberish text or multi-panel grids.
    """
    cam = cam_shot.strip().rstrip(".,:;")
    concept = vis_concept.strip()

    # Strip any split-screen or poster-text triggers
    concept = re.sub(r"(?i)\bsplit[- ]screen\b", "single-frame", concept)
    concept = re.sub(r"(?i)\bpropaganda posters?\b", "military banners without text", concept)
    concept = re.sub(r"(?i)\bposters?\b", "banners without text", concept)
    
    if not any(w in cam.lower() for w in ("wide", "panoramic", "establishing", "aerial", "landscape")):
        cam = f"Single full-bleed vertical 9:16 cinematic shot, {cam}" if cam else "Single full-bleed vertical 9:16 cinematic shot"

    cam_prefixes = (
        "cinematic wide shot of", "wide shot of", "medium shot of", "close-up shot of",
        "close-up of", "low-angle shot of", "cinematic shot of", "aerial shot of",
        "split-screen cinematic wide shot of", "split-screen of", "shot of", "close up of",
        "cinematic wide-angle documentary shot of", "cinematic wide-angle shot of"
    )
    for pfx in cam_prefixes:
        if concept.lower().startswith(pfx):
            concept = concept[len(pfx):].strip()
            break

    concept = re.sub(r'^(a\s+|an\s+|the\s+)', '', concept, flags=re.IGNORECASE)
    base = f"{cam} of {concept}" if not cam.lower().endswith("of") else f"{cam} {concept}"
    base = base.rstrip(".,:; ")
    
    detail_boosters = (
        "dramatic volumetric lighting, historically authentic wardrobe and architecture, "
        "35mm archival film grain, 8k resolution, no text, no split screen"
    )
    parts = [base]
    if prompt_hint:
        clean_hint = prompt_hint.strip().rstrip(".,; ")
        if clean_hint and clean_hint.lower() not in base.lower():
            parts.append(clean_hint)
            
    if detail_boosters.lower() not in base.lower():
        parts.append(detail_boosters)
            
    final_prompt = ", ".join(parts)
    final_prompt = re.sub(r'\s*,\s*', ', ', final_prompt)
    final_prompt = re.sub(r'\s*\.\s*', '. ', final_prompt)
    final_prompt = re.sub(r'of\s+of', 'of', final_prompt, flags=re.IGNORECASE)
    return final_prompt.strip()


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
            focal_kw = str(beat.get("focal_keyword", "")).strip().lower()
            focal_u = float(beat.get("focal_u", 0.50))
            focal_v = float(beat.get("focal_v", 0.40))
            zoom_tgt = float(beat.get("zoom_target", 1.12))

            # Clamp coordinates to safe documentary framing boundaries
            focal_u = max(0.20, min(0.80, focal_u))
            focal_v = max(0.20, min(0.65, focal_v))
            zoom_tgt = max(1.04, min(1.18, zoom_tgt))

            # Locate timestamp of focal_keyword within beat start/end
            t_hit_rel = (end_t - start_t) * 0.55
            if focal_kw:
                for w in global_timeline:
                    if w.get("global_start", 0) >= start_t - 0.1 and w.get("global_end", 0) <= end_t + 0.1:
                        if normalize_word(w.get("word", "")) == normalize_word(focal_kw) or focal_kw in normalize_word(w.get("word", "")):
                            t_hit_rel = max(0.8, w.get("global_start", start_t) - start_t)
                            break

            # Retrieve beat-specific visual evidence and anachronism rules from RAG v4
            beat_evidence = retrieve_beat_visual_evidence(evidence_packet, excerpt, vis_concept) if evidence_packet else {}
            prompt_hint = beat_evidence.get("visual_prompt_hint", "")

            enriched_prompt = clean_visual_prompt_string(cam_shot, vis_concept, prompt_hint)

            aligned_beats.append({
                "beat_id": f"beat_{idx+1:03d}",
                "start_time": start_t,
                "end_time": end_t,
                "duration": round(end_t - start_t, 3),
                "narration_text": excerpt,
                "visual_concept": vis_concept,
                "visual_prompt": enriched_prompt,
                "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
                "camera_shot": cam_shot,
                "focal_keyword": focal_kw,
                "focal_u": round(focal_u, 3),
                "focal_v": round(focal_v, 3),
                "zoom_target": round(zoom_tgt, 3),
                "t_hit": round(t_hit_rel, 3),
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
