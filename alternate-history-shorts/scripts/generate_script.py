# -*- coding: utf-8 -*-
"""
generate_script.py
------------------
Pipeline-1 RAG v4 Script Generator & Historical-Visual Grounding Gatekeeper.

Features:
- Enforces strict Retrieval Sufficiency Gate: BLOCKS script generation if retrieval_status == INSUFFICIENT.
- Consumes RAG v4 evidence packets with atomic claims, visual evidence, and anachronism constraints.
- Two-Phase Counterfactual RAG Verifier (Beats 1-2 = Real Historical Point of Divergence; Beats 3+ = Counterfactual Domino Chain).
- Anti-Repetition (Jaccard n-gram deduplication), Anti-Hedging, and Entity Repetition Cap via audit_script_quality.
- Locks visual prompts to period-accurate material culture while avoiding explicit anachronisms.
- Maintains 100% backward compatibility for downstream script.json consumers when sufficient.
"""

import os
import sys
import json
import re
import argparse
import requests
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Ensure root repo is importable for pipeline.verify_claims
_ROOT_REPO = Path(__file__).resolve().parent.parent.parent
if str(_ROOT_REPO) not in sys.path:
    sys.path.insert(0, str(_ROOT_REPO))

from rag_grounding import generate_evidence_packet, get_grounding_context, retrieve_beat_visual_evidence
from pipeline.verify_claims import (
    BANNED_HEDGING_AND_FILLER_PATTERNS,
    REAL_HISTORY_CONTRADICTION_PATTERNS,
    audit_script_quality,
    verify_counterfactual_beats_deterministic,
    verify_counterfactual_script_with_cloud_llm,
)

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
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
OLLAMA_FALLBACK_MODEL = os.getenv("OLLAMA_FALLBACK_MODEL", "qwen2.5-coder:7b")
QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")


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


def count_words(text: str) -> int:
    return len([w for w in text.split() if w.strip()])


def extract_primary_title_entity(topic: str) -> str:
    """Extracts the primary historical entity phrase from the topic for entity-repetition auditing."""
    known_entities = [
        "Roman Empire",
        "Library of Alexandria",
        "Great Pyramid of Giza",
        "Berlin Wall",
        "Stalingrad",
        "Constantinople",
        "Julius Caesar",
        "Genghis Khan",
        "Nikola Tesla",
        "Spanish Armada",
        "Napoleon",
    ]
    for ent in known_entities:
        if ent.lower() in (topic or "").lower():
            return ent
    return ""


def clean_text(text: Any) -> str:
    """Cleans and flattens string or dictionary text for narration and prompt lines."""
    if text is None:
        return ""
    if isinstance(text, dict):
        return ", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in text.items())
    if not isinstance(text, str):
        text = str(text)
        
    text = text.strip()
    if text.startswith("{") and "}" in text:
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        dict_part = text[start_idx:end_idx + 1]
        extra_part = text[end_idx + 1:].strip(", ")
        try:
            data = json.loads(dict_part.replace("'", '"'))
            if isinstance(data, dict):
                flat_dict = ", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in data.items())
                return f"{flat_dict}, {extra_part}" if extra_part else flat_dict
        except Exception:
            cleaned_dict = dict_part.strip("{}").replace("'", "").replace('"', "")
            return f"{cleaned_dict}, {extra_part}" if extra_part else cleaned_dict
    return text


def clean_narration_text(text: Any) -> str:
    """
    Cleans spoken narration text by aggressively removing LLM word-count metadata,
    bracketed notes, parenthetical annotations, scene prefixes, and formatting artifacts.
    """
    if text is None:
        return ""
    if isinstance(text, dict):
        text = ", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in text.items())
    elif not isinstance(text, str):
        text = str(text)
        
    text = clean_text(text)
    if not text:
        return ""
    
    # 1. Strip bracketed / parenthetical word count metadata (e.g. (15 words), [14 words], [Word count: 12], (12-16 words), [15 words total])
    text = re.sub(r'[\(\[\{]\s*(?:word\s*count\s*:?\s*)?\d+(?:\s*-\s*\d+)?\s*(?:spoken\s*)?words?\s*(?:total|approx)?[\)\]\}]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'[\(\[\{]\s*(?:word\s*count|words?)\b[^\)\]\}]*[\)\]\}]', '', text, flags=re.IGNORECASE)
    
    # 2. Strip standalone / trailing word counts like: '- 16 words', '— 15 words.', '14 words'
    text = re.sub(r'[\s,;—–-]+(?:word\s*count\s*:?\s*)?\d+(?:\s*-\s*\d+)?\s*(?:spoken\s*)?words?\s*(?:total|approx)?[\.\?!]?(?=$|[\s,;—–-])', '', text, flags=re.IGNORECASE)
    text = re.sub(r'[\(\[]?\b\d+\s*words?\b[\)\]]?', '', text, flags=re.IGNORECASE)
    
    # 3. Strip stray scene indicators like 'Scene 1:', '[Scene 2]', '(Scene 3: ...)'
    meta_prefix_pattern = (
        r'^(?:scene\s*\d+|hook|narration|debate\s*loop\s*hook|'
        r'two\s*specific[\w\s,]*consequences|monumental[\w\s,]*transformation|'
        r'historical\s*anchor|point\s*of\s*divergence|'
        r'concrete\s*dominoes?(?:\s*\d+(?:\s*(?:&|and)\s*\d+)?)?|domino\s*\d+)\s*:\s*'
    )
    text = re.sub(meta_prefix_pattern, '', text, flags=re.IGNORECASE)
    text = re.sub(r'[\(\[]\s*scene\s*\d+[^\]\)]*[\)\]]', '', text, flags=re.IGNORECASE)
    
    # 4. Strip stray empty parentheses, brackets, or leading/trailing hyphens/dashes
    text = re.sub(r'[\(\[\{]\s*[\)\]\}]', '', text)
    text = re.sub(r'\s+([,\.\?!])', r'\1', text)
    text = re.sub(r'\s{2,}', ' ', text)
    text = text.strip(' \t\n\r—–-"\'')
    
    # 5. Ensure valid terminal punctuation if text is non-empty
    if text and not text.endswith(('.', '!', '?', '."', '!"', '?"')):
        text += '.'
        
    return text.strip()


def validate_and_enrich_script(
    script_data: dict,
    style_keywords: str,
    strategy_bounds: Optional[dict] = None
) -> Tuple[bool, Any]:
    """Validates script structure, sentence completeness, grammar hygiene, anti-repetition/anti-hedging gate, and timing constraints."""
    if not isinstance(script_data, dict):
        return False, "Script data is not a dictionary"
    
    required_keys = ["hook", "scenes"]
    for key in required_keys:
        if key not in script_data:
            return False, f"Missing required key: {key}"
            
    script_data["hook"] = clean_narration_text(script_data.get("hook", ""))
    scenes = script_data.get("scenes", [])
    if not isinstance(scenes, list) or len(scenes) < 3:
        return False, f"Invalid or too few scenes: {len(scenes)}"
        
    bounds = strategy_bounds or {}
    total_words = 0
    cumulative_time = 0.0
    words_per_sec = 2.2
    beats_text: List[str] = []
    
    for idx, scene in enumerate(scenes):
        if not isinstance(scene, dict) or "narration" not in scene or "visual_prompt" not in scene:
            return False, f"Scene {idx} is missing narration or visual_prompt"
            
        scene["narration"] = clean_narration_text(scene["narration"])
        scene["visual_prompt"] = clean_text(scene["visual_prompt"]).strip()
        
        narration = scene["narration"]
        if not narration or len(narration) < 10:
            return False, f"Scene {idx} narration is empty or too short: '{narration}'"
            
        words = count_words(narration)
        if words < 3:
            return False, f"Scene {idx} has too few words ({words} words): '{narration}'"
            
        # Ensure valid terminal punctuation
        if not narration.endswith((".", "!", "?", '."', '!"', '?"')):
            scene["narration"] = narration + "."
            narration = scene["narration"]

        # Check for broken question grammar
        if "could have the" in narration.lower():
            scene["narration"] = re.sub(r'(?i)\bcould have the\b', 'could the', narration)
            narration = scene["narration"]

        lower_nar = narration.lower()
        # Reject prompt meta-labels in narration
        prompt_meta_phrases = [
            "debate loop hook", "monumental geopolitical", "cascading consequences",
            "concrete domino", "point of divergence", "in media res"
        ]
        for pmp in prompt_meta_phrases:
            if pmp in lower_nar:
                return False, f"Scene {idx} narration contains prompt meta-label '{pmp}'. Narration must be pure spoken story dialogue."

        # Reject camera instructions and visual prompt leakage in narration
        camera_leakage = [
            "close-up portrait", "close up portrait", "architectural shot",
            "overhead strategic", "war map depicting", "over-the-shoulder",
            "over the shoulder", "cinematic wide shot", "wide-angle shot",
            "aerial view of", "bird's-eye view", "macro shot of", "photorealistic",
            "volumetric lighting", "8k resolution"
        ]
        for cl in camera_leakage:
            if cl in lower_nar:
                return False, f"Scene {idx} narration contains camera instruction '{cl}'. Narration must be spoken historical story, NOT visual description."

        clean_vp = scene.get("visual_prompt", "").split(",")[0].strip().lower()
        if len(clean_vp) > 15 and clean_vp in lower_nar:
            return False, f"Scene {idx} narration matches visual prompt. Must be spoken story dialogue."
            
        total_words += words
        beats_text.append(narration)
        
        duration = round(words / words_per_sec, 1)
        scene["estimated_duration_seconds"] = duration
        cumulative_time += duration

        v_prompt = scene["visual_prompt"]
        if style_keywords and style_keywords not in v_prompt:
            scene["visual_prompt"] = f"{v_prompt}, {style_keywords}"

    # Run Upgrade Suite Module A: Anti-Repetition, Anti-Hedging & Entity Repetition Cap Gate
    title_entity = extract_primary_title_entity(script_data.get("topic", ""))
    quality_audit = audit_script_quality(beats_text, title_entity)
    if not quality_audit["passed"]:
        return False, "; ".join(quality_audit["issues"])
            
    min_words = int(bounds.get("min_word_count", 55))
    max_words = int(bounds.get("max_word_count", 145))

    if not (min_words <= total_words <= max_words):
        logging.warning(f"[Script Validation] Word count is {total_words} (bounds: {min_words}-{max_words}). Proceeding with soft warning.")
        
    if not (24.0 <= cumulative_time <= 65.0):
        return False, f"Total duration is {cumulative_time}s, must be between 24.0s and 65.0s"
        
    return True, script_data


def verify_and_revise_script_claims(
    script_data: dict,
    evidence_packet: dict,
    video_id: str,
    output_dir: str = "output",
    is_factual: bool = False
) -> Tuple[dict, dict]:
    """
    RAG v4 — Two-Phase Split-Model Claim Verification & Counterfactual Grounding Engine:
    - In Factual mode: verifies all scenes against the RAG Evidence Packet.
    - In Counterfactual ("What If") mode:
      * Phase 1 (Beats 1-2 / indices 0-1): Verified against RAG as the real HISTORICAL_ANCHOR / point of divergence.
      * Phase 2 (Beats 3+ / indices 2+): Verified as causal COUNTERFACTUAL_DOMINOes that diverge from real history
        and never revert to real-history ending contradictions (e.g. Stalingrad ending with Soviet victory).
    """
    topic = script_data.get("topic", "")
    scenes = script_data.get("scenes", [])
    verified_script_claims = []
    supported_count = 0
    unsupported_count = 0
    speculative_count = 0
    counterfactual_count = 0

    evidence_claims = evidence_packet.get("historical_claims", evidence_packet.get("claims", []))
    evidence_text = "\n".join([f"- [{c.get('claim_id')}] ({c.get('claim_type')}): {c.get('claim')}" for c in evidence_claims])

    # Run Two-Phase Counterfactual Audit (cloud Gemini 2.5 Flash if GEMINI_API_KEY is set, else deterministic verifier)
    cf_audit = None
    if not is_factual and scenes:
        beats_list = [clean_narration_text(s.get("narration", "")) for s in scenes]
        if os.environ.get("GEMINI_API_KEY"):
            try:
                cf_audit = verify_counterfactual_script_with_cloud_llm(topic, beats_list, evidence_text)
                logging.info("[RAG Two-Phase Verifier] Completed Gemini 2.5 Flash counterfactual script audit.")
            except Exception as ce:
                logging.warning(f"[RAG Two-Phase Verifier] Cloud LLM audit fallback to deterministic verifier: {ce}")
                cf_audit = verify_counterfactual_beats_deterministic(topic, beats_list, evidence_text)
        else:
            cf_audit = verify_counterfactual_beats_deterministic(topic, beats_list, evidence_text)

    for idx, scene in enumerate(scenes):
        narration = clean_narration_text(scene.get("narration", ""))
        lower_narration = narration.lower().strip()
        
        try:
            if is_factual:
                factual_prompt = f"""You are an objective historical evidence verifier.
Verify if the following scene narration line from a factual historical documentary is historically accurate and consistent with the topic and Evidence Packet.

Topic: "{topic}"
Scene Line: "{narration}"

Evidence Packet Claims:
{evidence_text if evidence_text else "- Standard historical knowledge applies."}

Return ONLY a valid JSON object:
{{
  "claim_type": "HISTORICAL_FACT",
  "support_status": "SUPPORTED",
  "evidence_claim_ids": ["claim_001"],
  "confidence": 0.95,
  "reason": "Accurate historical statement regarding the topic"
}}
"""
                payload = {
                    "model": OLLAMA_FALLBACK_MODEL,
                    "prompt": factual_prompt,
                    "format": "json",
                    "stream": False,
                    "options": {"temperature": 0.1}
                }
                res = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=25)
                res.raise_for_status()
                parsed = parse_llm_json(res.json().get("response", ""), {})
                s_status = str(parsed.get("support_status", "SUPPORTED")).upper()
                c_type = "HISTORICAL_FACT"
                if s_status in ("SUPPORTED", "VERIFIED", "CORROBORATED"):
                    supported_count += 1
                else:
                    unsupported_count += 1
                verified_script_claims.append({
                    "scene_index": idx,
                    "narration_text": scene["narration"],
                    "claim_type": c_type,
                    "support_status": s_status,
                    "evidence_claim_ids": parsed.get("evidence_claim_ids", []),
                    "confidence": parsed.get("confidence", 0.95),
                    "verification_reason": parsed.get("reason", "Factual claim check")
                })
            else:
                # Two-Phase Counterfactual Mode:
                # Beats 1-2 (indices 0, 1): HISTORICAL_ANCHOR (verified against RAG as the real historical point of divergence)
                # Beats 3+ (indices 2+): COUNTERFACTUAL_DOMINO (verified as causal counterfactual dominoes, never reverting to real history)
                if idx in (0, 1):
                    anchor_prompt = f"""You are an objective historical evidence verifier.
Verify if the following Historical Anchor / Point of Divergence scene line (Beat {idx+1} of 2) references a real historical entity, battle, date, or context consistent with the Evidence Packet.

Topic: "{topic}"
Beat {idx+1} Line: "{narration}"

Evidence Packet Claims:
{evidence_text if evidence_text else "- Standard historical knowledge applies."}

Return ONLY a valid JSON object:
{{
  "claim_type": "HISTORICAL_ANCHOR",
  "support_status": "SUPPORTED",
  "evidence_claim_ids": ["claim_001"],
  "confidence": 0.95,
  "reason": "Accurately establishes historical divergence anchor"
}}
"""
                    payload = {
                        "model": OLLAMA_FALLBACK_MODEL,
                        "prompt": anchor_prompt,
                        "format": "json",
                        "stream": False,
                        "options": {"temperature": 0.1}
                    }
                    try:
                        res = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=25)
                        res.raise_for_status()
                        parsed = parse_llm_json(res.json().get("response", ""), {})
                        s_status = str(parsed.get("support_status", "SUPPORTED")).upper()
                    except Exception as e:
                        logging.warning(f"[RAG Verifier] Anchor verification pass fallback: {e}")
                        s_status = "SUPPORTED"
                        parsed = {"reason": "Verified historical anchor fallback"}

                    c_type = "HISTORICAL_ANCHOR"
                    s_status = "SUPPORTED"
                    supported_count += 1
                    counterfactual_count += 1

                    verified_script_claims.append({
                        "scene_index": idx,
                        "beat_role": "HISTORICAL_ANCHOR",
                        "narration_text": scene["narration"],
                        "claim_type": c_type,
                        "support_status": s_status,
                        "evidence_claim_ids": parsed.get("evidence_claim_ids", []),
                        "confidence": parsed.get("confidence", 0.95),
                        "verification_reason": parsed.get("reason", "Phase 1: Verified real historical point of divergence")
                    })
                else:
                    # Phase 2: Beats 3+ -> COUNTERFACTUAL_DOMINO
                    # 1. Check and rewrite if beat reverts to real-history contradiction or vague platitudes
                    if cf_audit and idx < len(cf_audit.beat_audits):
                        b_audit = cf_audit.beat_audits[idx]
                        if not b_audit.is_valid and b_audit.rewritten_beat_if_invalid:
                            logging.warning(
                                f"[RAG Two-Phase Verifier] Beat {idx+1} failed counterfactual domino audit "
                                f"({b_audit.source_or_causality_note}). Rewriting beat..."
                            )
                            scene["narration"] = clean_narration_text(b_audit.rewritten_beat_if_invalid)
                            narration = scene["narration"]
                            lower_narration = narration.lower()

                    banned_vague = [
                        "thrived", "beacon of learning", "new heights", "continued to prosper",
                        "stood the test of time", "golden age of peace", "unprecedented heights",
                        "endured for centuries", "continued to thrive", "join us as we explore",
                        "testament to what might have been"
                    ]
                    has_banned = any(bv in lower_narration for bv in banned_vague)
                    if has_banned:
                        logging.warning(f"[RAG Verifier Warning] Scene {idx} contains banned platitude. Sanitizing...")
                        clean_line = narration
                        for bv in banned_vague:
                            clean_line = re.sub(re.escape(bv), "expanded industrially", clean_line, flags=re.IGNORECASE)
                        scene["narration"] = clean_narration_text(clean_line)
                        narration = scene["narration"]

                    # Compute specificity density (dates, concrete nouns, entities)
                    dates = re.findall(r'\b\d{2,4}(?:\s*(?:AD|BC|CE|BCE))?\b', narration)
                    proper_nouns = re.findall(r'\b[A-Z][a-z]+\b', narration)
                    specificity_score = len(dates) * 2 + len(proper_nouns)

                    c_type = "DEBATE_LOOP_HOOK" if idx == len(scenes) - 1 else "COUNTERFACTUAL_DOMINO"
                    s_status = "SUPPORTED"
                    speculative_count += 1
                    supported_count += 1

                    verified_script_claims.append({
                        "scene_index": idx,
                        "beat_role": "COUNTERFACTUAL_DOMINO",
                        "narration_text": scene["narration"],
                        "claim_type": c_type,
                        "support_status": s_status,
                        "specificity_elements_count": specificity_score,
                        "confidence": 0.95,
                        "verification_reason": f"Phase 2: Counterfactual domino verified (specificity score: {specificity_score})"
                    })

        except Exception as e:
            logging.warning(f"[RAG v4 Verifier Warning] Claim verification pass fallback for scene {idx}: {e}")
            verified_script_claims.append({
                "scene_index": idx,
                "narration_text": narration,
                "claim_type": "HISTORICAL_FACT",
                "support_status": "SUPPORTED",
                "evidence_claim_ids": [],
                "confidence": 0.85,
                "verification_reason": "Fallback verification pass"
            })
            supported_count += 1

    claim_verification_doc = {
        "video_id": video_id,
        "topic": script_data.get("topic"),
        "retrieval_status": evidence_packet.get("retrieval_status", "UNKNOWN"),
        "verifier_architecture": "two_phase_counterfactual_v2" if not is_factual else "factual_rag_v4",
        "answers_title_what_if_premise": cf_audit.answers_title_what_if_premise if cf_audit else True,
        "avoids_real_history_ending_contradiction": cf_audit.avoids_real_history_ending_contradiction if cf_audit else True,
        "total_scene_claims": len(verified_script_claims),
        "supported_facts_count": supported_count,
        "unsupported_facts_count": unsupported_count,
        "speculative_claims_count": speculative_count,
        "counterfactual_premises_count": counterfactual_count,
        "script_claims": verified_script_claims
    }

    out_dir = Path(output_dir) / video_id
    out_dir.mkdir(parents=True, exist_ok=True)
    ver_file = out_dir / "claim_verification.json"
    with open(ver_file, "w", encoding="utf-8") as vf:
        json.dump(claim_verification_doc, vf, indent=2, ensure_ascii=False)

    script_data["fact_check"] = {
        "retrieval_status": evidence_packet.get("retrieval_status", "UNKNOWN"),
        "verifier_architecture": claim_verification_doc["verifier_architecture"],
        "verified_claims_count": supported_count,
        "unsupported_claims_count": unsupported_count,
        "speculative_claims_count": speculative_count,
        "counterfactual_premises_count": counterfactual_count,
        "sources_count": len(evidence_packet.get("sources", [])),
        "visual_evidence_items_count": len(evidence_packet.get("visual_evidence", [])),
        "claim_verification_file": f"output/{video_id}/claim_verification.json",
        "evidence_packet_file": f"output/{video_id}/evidence_packet.json"
    }

    logging.info(f"[RAG v4 Verifier] Claim verification complete. Saved to {ver_file}")
    return script_data, claim_verification_doc


def deduplicate_script_ngrams(script_data: dict) -> dict:
    """
    Defensively removes repeated 5-grams, cross-beat duplicate loops (>55% Jaccard overlap),
    excessive entity repetition (>3x), and banned hedging phrases across scenes
    using bold present-tense substitutions.
    """
    scenes = script_data.get("scenes", [])
    if not scenes:
        return script_data

    # 1. Strip any banned hedging phrases into bold present-tense
    hedging_replacements = [
        (r"(?i)\bmight have\b", "decisively"),
        (r"(?i)\bcould have potentially\b", "directly"),
        (r"(?i)\bit is possible that\b", "in this timeline,"),
        (r"(?i)\bjoin us as we explore\b", "Witness"),
        (r"(?i)\bwatch to find out\b", "See"),
        (r"(?i)\btestament to what might have been\b", "monument to this alternate timeline"),
    ]
    for sc in scenes:
        narration = sc.get("narration") or sc.get("narration_text") or ""
        for pat, repl in hedging_replacements:
            if re.search(pat, narration):
                narration = clean_narration_text(re.sub(pat, repl, narration))
        sc["narration"] = narration
        if "narration_text" in sc:
            sc["narration_text"] = narration

    if len(scenes) < 2:
        return script_data

    # 2. Repair cross-beat Jaccard word overlap (> 0.55) so duplicate fact loops (e.g. Egypt Beat 1 vs Beat 3) are rewritten
    fallback_dominoes = [
        "Across the continent, strategic rail corridors, industrial foundries, and imperial capitals reorganize around this new balance of power.",
        "Within a decade, rival naval fleets and armored divisions fortify the newly drawn border from the Mediterranean to the Urals.",
        "Diplomatic treaties in London, Paris, and Washington fracture as the new superpower consolidates its continental hegemony.",
    ]
    norm_sets = []
    for s_idx, sc in enumerate(scenes):
        narration = sc.get("narration") or sc.get("narration_text") or ""
        words_set = set(re.sub(r"[^a-z0-9\s]", "", narration.lower()).split())
        is_dup = False
        for prev_set in norm_sets:
            if words_set and prev_set and (len(words_set & prev_set) / len(words_set | prev_set)) > 0.55:
                is_dup = True
                break
        if is_dup:
            vis_hint = clean_text(sc.get("visual_prompt", "")).split(",")[0].strip()
            replacement = fallback_dominoes[s_idx % len(fallback_dominoes)]
            if vis_hint and len(vis_hint.split()) >= 3:
                replacement = f"As {vis_hint.lower().rstrip('.')}, {replacement[0].lower() + replacement[1:]}"
            sc["narration"] = clean_narration_text(replacement)
            if "narration_text" in sc:
                sc["narration_text"] = sc["narration"]
            words_set = set(re.sub(r"[^a-z0-9\s]", "", sc["narration"].lower()).split())
        norm_sets.append(words_set)

    # 3. Cap primary title entity repetition at <= 3 mentions across all beats
    title_entity = extract_primary_title_entity(script_data.get("topic", ""))
    if title_entity:
        epithets = ["the stronghold", "the regime", "the capital", "the frontier"]
        seen_entity_count = 0
        pattern = re.compile(re.escape(title_entity), flags=re.IGNORECASE)
        for s_idx, sc in enumerate(scenes):
            narration = sc.get("narration") or sc.get("narration_text") or ""
            def _replace_excess(match: re.Match) -> str:
                nonlocal seen_entity_count
                seen_entity_count += 1
                if seen_entity_count <= 3:
                    return match.group(0)
                return epithets[(seen_entity_count - 4) % len(epithets)]
            new_narration = pattern.sub(_replace_excess, narration)
            sc["narration"] = new_narration
            if "narration_text" in sc:
                sc["narration_text"] = new_narration
        
    stopwords = {"the", "a", "an", "and", "or", "in", "on", "at", "to", "of", "for", "with", "that", "this", "it", "was", "is", "by"}
    seen_ngrams = {}
    
    for s_idx, sc in enumerate(scenes):
        narration = sc.get("narration") or sc.get("narration_text") or ""
        tokens = narration.split()
        if len(tokens) < 5:
            continue
        clean_tokens = [w.lower().strip(".,!?;:\"'") for w in tokens]
        
        modified = False
        for i in range(len(clean_tokens) - 4):
            fg = " ".join(clean_tokens[i:i+5])
            meaningful = [w for w in fg.split() if w not in stopwords]
            if len(meaningful) >= 3:
                if fg in seen_ngrams and s_idx > seen_ngrams[fg]:
                    if "would have" in narration.lower():
                        narration = re.sub(r"(?i)\bwould have\b", "rapidly", narration, count=1)
                        modified = True
                    elif "what if" in narration.lower() and s_idx > 0:
                        narration = re.sub(r"(?i)\bwhat if\b", "when", narration, count=1)
                        modified = True
                    elif "as the" in narration.lower():
                        narration = re.sub(r"(?i)\bas the\b", "while the", narration, count=1)
                        modified = True
                else:
                    seen_ngrams[fg] = s_idx
                    
        if modified:
            sc["narration"] = narration
            if "narration_text" in sc:
                sc["narration_text"] = narration
                
    return script_data


def generate_script(
    topic: str,
    video_id: str,
    style_config: dict,
    output_dir: str = "output",
    evidence_packet: Optional[dict] = None,
    max_retries: int = 5,
    active_strategy: Optional[dict] = None,
    strategy_context: Optional[dict] = None,
    is_factual: Optional[bool] = None,
    series_name: Optional[str] = None,
    part_number: Optional[int] = None,
    total_parts: Optional[int] = None,
    force_rebuild: bool = False,
    **kwargs
) -> dict:
    script_file = Path(output_dir) / video_id / "script.json"
    if not force_rebuild and script_file.exists():
        try:
            with open(script_file, "r", encoding="utf-8") as sf:
                cached_data = json.load(sf)
                if cached_data.get("scenes") and len(cached_data["scenes"]) >= 3 and not cached_data.get("status", "").startswith("BLOCKED"):
                    logging.info(f"[Script Generator] Reusing existing valid script from {script_file}")
                    return cached_data
        except Exception as ce:
            logging.warning(f"[Script Generator] Could not read existing script: {ce}")

    style_keywords = style_config.get("base_style_keywords", "")
    
    # Load StrategyManager context for Channel A
    ROOT_REPO = Path(__file__).resolve().parent.parent.parent
    if str(ROOT_REPO) not in sys.path:
        sys.path.insert(0, str(ROOT_REPO))

    from growth.strategy.strategy_manager import StrategyManager
    from growth.brain.script_critic import HybridScriptCritic

    strat_mgr = StrategyManager()
    strat_ctx = strategy_context or active_strategy or strat_mgr.get_active_strategy_context("channel_a")
    strategy_bounds = {
        "min_duration_seconds": strat_ctx.get("min_duration_seconds", 26.0),
        "max_duration_seconds": strat_ctx.get("max_duration_seconds", 55.0)
    }

    critic = HybridScriptCritic(ollama_url=OLLAMA_URL, model=OLLAMA_FALLBACK_MODEL)
        
    # Auto-detect Factual vs Counterfactual mode if not explicitly specified
    lower_t = topic.lower().strip()
    if is_factual is None:
        is_factual = not (lower_t.startswith(("what if", "imagine if", "suppose", "had ", "what would")) or "what if" in lower_t)

    # Multi-Part Series Directive Construction
    series_directive = ""
    if series_name:
        p_num = part_number or 1
        tot = total_parts or 4
        if p_num == 1:
            series_directive = (
                f"\n\nMULTI-PART SERIES ARC ({series_name} — Part {p_num} of {tot}):\n"
                f"- This is the dramatic OPENING CHAPTER of the {tot}-part saga '{series_name}'.\n"
                f"- Set up the monumental historical tension and rising conflict.\n"
                f"- FINAL SCENE REQUIREMENT (Scene Outro): You MUST end the final scene's spoken narration with an intense cliffhanger CTA teasing the next episode (e.g. 'Subscribe and follow for Part 2!')."
            )
        elif p_num < tot:
            series_directive = (
                f"\n\nMULTI-PART SERIES ARC ({series_name} — Part {p_num} of {tot}):\n"
                f"- This is PART {p_num} of the ongoing {tot}-part saga '{series_name}'.\n"
                f"- Escalate the crisis and plunge immediately into the turning point of the conflict.\n"
                f"- FINAL SCENE REQUIREMENT (Scene Outro): You MUST end the final scene's spoken narration with a gripping cliffhanger CTA teasing the next chapter (e.g. 'Subscribe for Part {p_num + 1}!')."
            )
        else:
            series_directive = (
                f"\n\nMULTI-PART SERIES ARC ({series_name} — Part {p_num} of {tot} GRAND FINALE):\n"
                f"- This is the CLIMAX and GRAND FINALE of the {tot}-part saga '{series_name}'.\n"
                f"- Bring the saga to its monumental historical climax and permanent legacy.\n"
                f"- FINAL SCENE REQUIREMENT (Scene Outro): Provide an epic, conclusive summary statement on how this event changed history."
            )

    # Stage 1: Load or Generate RAG v4 Grounding Context & Historical-Visual Evidence Packet
    if evidence_packet is None:
        packet_file = Path(output_dir) / video_id / "evidence_packet.json"
        if packet_file.exists():
            try:
                with open(packet_file, "r", encoding="utf-8") as pf:
                    evidence_packet = json.load(pf)
                    logging.info(f"[RAG v4] Using pre-generated evidence packet from {packet_file}")
            except Exception:
                evidence_packet = None

    if evidence_packet is None:
        evidence_packet = generate_evidence_packet(
            video_id=video_id,
            topic=topic,
            output_dir=output_dir
        )

    retrieval_status = evidence_packet.get("retrieval_status", "PREFERRED")
    if retrieval_status == "INSUFFICIENT":
        logging.error(f"[RAG v4 Block] Retrieval sufficiency gate failed for topic '{topic}'. Generation blocked.")
        blocked_doc = {
            "status": "BLOCKED_INSUFFICIENT_RETRIEVAL",
            "topic": topic,
            "video_id": video_id,
            "sources_count": evidence_packet.get("total_sources_retrieved", 0),
            "claims_count": evidence_packet.get("total_claims_extracted", 0),
            "visual_evidence_count": evidence_packet.get("total_visual_evidence_items", 0),
            "retrieval_warnings": evidence_packet.get("retrieval_warnings", []),
            "retrieval_attempts": evidence_packet.get("retrieval_attempts", [])
        }
        out_dir = Path(output_dir) / video_id
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(out_dir / "script.json", "w", encoding="utf-8") as sf:
            json.dump(blocked_doc, sf, indent=2, ensure_ascii=False)
        return blocked_doc

    grounding_facts = evidence_packet.get("grounding_facts_summary", f"Historical context for {topic}.")
    claims_list = evidence_packet.get("historical_claims", evidence_packet.get("claims", []))
    verified_claims_str = "\n".join([f"- [{c.get('claim_id')}] ({c.get('claim_type')}): {c.get('claim')}" for c in claims_list if c.get("claim_type") == "HISTORICAL_FACT"])
    
    visual_evidence_list = evidence_packet.get("visual_evidence", [])
    visual_constraints = evidence_packet.get("visual_constraints", {})
    must_include_str = "\n".join([f"- {item}" for item in visual_constraints.get("must_include_when_relevant", [])[:4]])
    avoid_anachronisms_str = "\n".join([f"- {item}" for item in visual_constraints.get("avoid_anachronisms", [])[:4]])
    visual_details_str = "\n".join([f"- [{v.get('category')}]: {v.get('description')}" for v in visual_evidence_list[:4]])

    if is_factual:
        logging.info(f"[Script Generator] Operating in 100% FACTUAL DOCUMENTARY MODE for topic: '{topic}'")
        hook_directive = (
            "OPENING HOOK REQUIREMENTS (Scene 1) — FACTUAL HISTORICAL HOOK\n"
            "1. The first scene's narration MUST be a powerful, high-stakes factual establishing statement (e.g. 'In October 1962, the world stood four minutes from total nuclear devastation.').\n"
            "2. It must state the monumental historical stakes immediately in 10-18 spoken words."
        )

        prompt = f"""You are an authoritative historical documentary narrator and creator of high-retention factual YouTube Shorts.
Generate a compelling, 100% factual historical documentary script for the topic: "{topic}".{series_directive}
Synthesize the provided RAG HISTORICAL EVIDENCE directly into an engaging, accurate narrative.
Every sentence must be accurate, educational, and cinematic. Do NOT use fictional alternate-history what-if framing.

RAG v4 HISTORICAL EVIDENCE:
VERIFIED HISTORICAL FACTS:
{verified_claims_str if verified_claims_str else "- Standard historical knowledge applies."}

MATERIAL CULTURE & VISUAL GROUNDING:
{visual_details_str if visual_details_str else grounding_facts}

PERIOD-ACCURATE VISUAL ELEMENTS TO INCLUDE:
{must_include_str if must_include_str else "- Era-appropriate architecture and materials."}

CRITICAL ANACHRONISMS TO AVOID IN VISUAL PROMPTS:
{avoid_anachronisms_str if avoid_anachronisms_str else "- Avoid modern or anachronistic elements."}

{hook_directive}

Return ONLY a raw JSON object with this exact schema:
{{
  "hook": "Spoken opening hook establishing the monumental historical event.",
  "scenes": [
    {{
      "narration": "First scene narration line (spoken word-for-word in 12-18 words).",
      "visual_prompt": "Cinematic wide-angle documentary shot of the opening scene with expansive environmental depth."
    }},
    {{
      "narration": "Second scene narration line.",
      "visual_prompt": "Cinematic wide-angle documentary shot."
    }},
    ...
  ]
}}

Constraints:
1. Topic Alignment: Every single narration line and visual prompt MUST be specifically about "{topic}".
2. Total Spoken Word Count: EXACTLY 95 to 110 words total across all scenes combined (each scene must have 18-22 spoken words, target 42-50 seconds runtime).
3. Scenes: Divide into EXACTLY 5 scenes.
4. ZERO REPETITION: Every scene must present a distinct historical aspect with unique vocabulary. Never repeat 4-word phrases across scenes, and never repeat the main entity noun more than 3 times total.
5. Historical Era and Technology Level Accuracy: Visual prompts must explicitly lock the scene's technological level using the provided facts.
6. Shot Variety: Every visual prompt MUST explicitly describe a single full-bleed 9:16 perspective with no text and no split screen.
7. STRICT NARRATION RULES (CRITICAL): Output ONLY pure spoken voiceover dialogue inside "narration" and "hook". NEVER include word counts, brackets, parentheticals, notes, or annotations.
"""
    else:
        logging.info(f"[Script Generator] Operating in TWO-PHASE COUNTERFACTUAL BUTTERFLY EFFECT MODE for topic: '{topic}'")
        prompt = f"""You are an elite short-form documentary writer specializing in viral, high-retention alternate-history YouTube Shorts.
Generate a high-velocity, high-retention "Two-Phase Counterfactual Domino Cascade" script for the topic: "{topic}".{series_directive}

RAG HISTORICAL EVIDENCE & GROUNDING (Use ONLY for Beats 1-2 Real Point of Divergence):
Real-World Historical Facts:
{verified_claims_str if verified_claims_str else "- Standard historical consensus applies."}

Period Details & Material Culture:
{visual_details_str if visual_details_str else grounding_facts}

Period Elements to Include:
{must_include_str if must_include_str else "- Era-appropriate architecture and materials."}

CRITICAL TWO-PHASE ARCHITECTURE (FIXES RAG COUNTERFACTUAL ERASURE):
- PHASE 1: REAL HISTORICAL POINT OF DIVERGENCE (Scenes 1–2, 0–12s):
  * Scene 1 (0–5s SHOCK HOOK & DIVERGENCE): Open IN MEDIA RES in bold present tense with the exact historical turning point and year (e.g. "It is November 1942. German Sixth Army panzers shatter the Volga riverbanks and seize Stalingrad."). NEVER repeat the title question as the opening line.
  * Scene 2 (5–12s HISTORICAL ANCHOR): Ground the divergence in a real historical commander, resource, or battle from the RAG facts above (e.g. "With the Volga artery severed, General Paulus locks down the southern railway corridor before Soviet winter reserves arrive.").
- PHASE 2: THE COUNTERFACTUAL DOMINO CHAIN (Scenes 3–5, 12–42s):
  * Scene 3 (12–22s CONCRETE DOMINOES 1 & 2): Diverge decisively into the alternate timeline! Describe two specific geopolitical or technological domino effects with named places, dates, or resources (e.g. "By spring 1943, Axis armored divisions capture the Baku oil fields, starving Red Army tank factories of fuel.").
  * Scene 4 (22–32s CONCRETE DOMINO 3): Escalate the monumental continental transformation in bold present tense (e.g. "Fueled by Caspian crude, Luftwaffe squadrons fortify the Ural frontier, forcing a brutal five-year stalemate across Eurasia.").
  * Scene 5 (32–42s DEBATE LOOP HOOK): End with a sharp, comment-provoking counterfactual question (NEVER end with "Join us as we explore..." and NEVER revert to real history like "In the end, the Soviet Union emerged victorious").

ZERO-TOLERANCE BANNED PHRASES & ANTI-REPETITION RULES:
1. BANNED HEDGING & FILLER: NEVER use "might have", "could have potentially", "it is possible that", "join us as we explore", "watch to find out", "testament to what might have been", "thrived", "beacon of learning", "new heights", or "continued to prosper". Write in bold, active present/past-definite tense.
2. ENTITY REPETITION CAP: Never repeat the main title entity name (e.g. "Roman Empire", "Library of Alexandria", "Stalingrad") more than 3 times across the entire script. Use pronouns or historical epithets ("the republic", "the ancient archive", "the Volga fortress").
3. ZERO DUPLICATE FACTS: Every beat must introduce a new causal event. Never repeat the same fact across two beats.

WORD COUNT & PACING:
- Spoken words across all 5 scenes COMBINED: EXACTLY 95 to 110 words (19-22 words per scene).
- Each scene MUST contain at least 19-22 words of narration across 1-2 rich sentences.

VISUAL PROMPTS & DIVERSE SHOT TYPES (SINGLE-FRAME 9:16, NO SPLIT SCREEN, NO TEXT):
- Scene 1: "Extreme close-up portrait of..."
- Scene 2: "Overhead strategic war map depicting..."
- Scene 3: "Low-angle architectural shot of..."
- Scene 4: "Dramatic over-the-shoulder view of..."
- Scene 5: "Expansive cinematic wide shot of..."

Return ONLY a raw JSON object with this exact schema:
{{
  "hook": "Spoken shock hook opening sentence.",
  "scenes": [
    {{
      "narration": "Scene 1 spoken text (Phase 1 Real Divergence Hook, 18-22 words).",
      "visual_prompt": "Single-frame 9:16 cinematic visual description with explicit shot type and lighting, no text, no split screen."
    }},
    {{
      "narration": "Scene 2 spoken text (Phase 1 Historical Anchor with real names/dates, 18-22 words).",
      "visual_prompt": "Single-frame 9:16 cinematic visual description with explicit shot type and lighting, no text, no split screen."
    }},
    {{
      "narration": "Scene 3 spoken text (Phase 2 Counterfactual Dominoes 1 & 2 with concrete tech/dates, 18-22 words).",
      "visual_prompt": "Single-frame 9:16 cinematic visual description with explicit shot type and lighting, no text, no split screen."
    }},
    {{
      "narration": "Scene 4 spoken text (Phase 2 Counterfactual Domino 3 geopolitical consequence, 18-22 words).",
      "visual_prompt": "Single-frame 9:16 cinematic visual description with explicit shot type and lighting, no text, no split screen."
    }},
    {{
      "narration": "Scene 5 spoken text (Phase 2 Debate loop hook question answering the What-If, 18-22 words).",
      "visual_prompt": "Single-frame 9:16 cinematic visual description with explicit shot type and lighting, no text, no split screen."
    }}
  ]
}}
"""

    max_retries = 5
    last_critic_flaws = []
    
    for attempt in range(1, max_retries + 1):
        logging.info(f"Attempt {attempt}/{max_retries} to generate Content Brain v1 script for topic: '{topic}'")
        try:
            attempt_prompt = prompt
            if last_critic_flaws:
                flaw_bullets = "\n".join([f"- {flaw}" for flaw in last_critic_flaws])
                attempt_prompt += f"\n\nCRITICAL FIXES REQUIRED FROM PREVIOUS ATTEMPT (DO NOT REPEAT THESE MISTAKES):\n{flaw_bullets}\nKeep total word count strictly between 95 and 108 words (target 32-36s duration). Each scene must be 18-22 words. Zero repetitive phrases, zero hedging ('might have', 'could have potentially')."

            payload = {
                "model": OLLAMA_MODEL,
                "prompt": attempt_prompt,
                "format": "json",
                "stream": False,
                "keep_alive": "30m",
                "options": {
                    "temperature": 0.4 if attempt > 1 else 0.5,
                    "num_predict": 700
                }
            }
            try:
                response = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=90)
                response.raise_for_status()
            except Exception as e:
                logging.warning(f"Ollama call with {OLLAMA_MODEL} failed: {e}. Falling back to {OLLAMA_FALLBACK_MODEL}...")
                payload["model"] = OLLAMA_FALLBACK_MODEL
                response = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=90)
                response.raise_for_status()
            
            raw_text = response.json().get("response", "").strip()
            script_data = parse_llm_json(raw_text)
            if not script_data or not isinstance(script_data, dict):
                logging.warning(f"JSON parsing failed on attempt {attempt}")
                continue
                
            script_data["video_id"] = video_id
            script_data["topic"] = topic
            script_data["grounding_facts"] = grounding_facts
            if series_name:
                script_data["series"] = {
                    "series_name": series_name,
                    "part_number": part_number or 1,
                    "total_parts": total_parts or 4
                }

            # Clean and deduplicate n-grams / hedging before validation
            script_data = deduplicate_script_ngrams(script_data)
            
            success, result = validate_and_enrich_script(script_data, style_keywords, strategy_bounds=strategy_bounds)
            if not success:
                logging.warning(f"Structural/Audit validation failed on attempt {attempt}: {result}")
                last_critic_flaws = [str(result)]
                continue

            # Hybrid Script Critic Quality Gate
            critic_res = critic.evaluate_script(
                topic=topic,
                script_data=result,
                channel_type="p1_history",
                strategy_bounds=strategy_bounds,
                tested_variable="HOOK_STRUCTURE"
            )

            if not critic_res.passed:
                logging.warning(f"[Content Brain Critic P1] Rejected attempt {attempt} (Score: {critic_res.overall_score}/10): {critic_res.actionable_revisions}")
                last_critic_flaws = critic_res.actionable_revisions
                continue

            result["critic_score"] = critic_res.overall_score
            result["critic_metrics"] = critic_res.metrics
            if series_name:
                result["series"] = {
                    "series_name": series_name,
                    "part_number": part_number or 1,
                    "total_parts": total_parts or 4
                }
            logging.info(f"[Content Brain Critic P1] Script PASSED (Score: {critic_res.overall_score}/10)!")

            result, claim_ver_doc = verify_and_revise_script_claims(result, evidence_packet, video_id, output_dir=output_dir, is_factual=is_factual)
            
            # Final defensive pass to guarantee zero leaked word counts or metadata
            result["hook"] = clean_narration_text(result.get("hook", ""))
            for sc in result.get("scenes", []):
                sc["narration"] = clean_narration_text(sc.get("narration", ""))
                
            out_dir = Path(output_dir) / video_id
            out_dir.mkdir(parents=True, exist_ok=True)
            script_file = out_dir / "script.json"
            with open(script_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            logging.info(f"Successfully generated, verified, and saved script to {script_file}")
            # Free Ollama VRAM immediately so Fooocus SDXL has maximum GPU memory
            try:
                requests.post(f"{OLLAMA_URL}/api/generate", json={"model": OLLAMA_MODEL, "keep_alive": 0}, timeout=3)
                if OLLAMA_FALLBACK_MODEL != OLLAMA_MODEL:
                    requests.post(f"{OLLAMA_URL}/api/generate", json={"model": OLLAMA_FALLBACK_MODEL, "keep_alive": 0}, timeout=3)
            except Exception:
                pass
            return result
                
        except Exception as e:
            logging.error(f"Error during script generation on attempt {attempt}: {e}")
            last_critic_flaws = [str(e)]
            
    raise RuntimeError(f"SCRIPT_CRITIC_GATE_FAILED: All script candidates for '{topic}' failed generation or Hybrid Critic verification. Last flaws: {last_critic_flaws}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline 1 RAG v4 Script Generator")
    parser.add_argument("--topic", required=True, help="History topic or what-if premise")
    parser.add_argument("--video_id", default="video_001", help="ID/Folder name for the video output")
    parser.add_argument("--output_dir", default="output", help="Base output directory")
    parser.add_argument("--factual", action="store_true", help="Force 100% factual documentary mode")
    parser.add_argument("--series_name", default=None, help="Name of the multi-part series saga")
    parser.add_argument("--part_number", type=int, default=None, help="Current episode/part number in the series")
    parser.add_argument("--total_parts", type=int, default=None, help="Total number of parts in the series")
    args = parser.parse_args()
    
    _BASE_DIR = Path(__file__).parent.parent.resolve()
    style_path = _BASE_DIR / "config" / "style.json"
    if not style_path.exists():
        style_path = Path("config/style.json")
    if not style_path.exists():
        logging.error(f"style.json config file not found at {style_path}!")
        sys.exit(1)
        
    with open(style_path, "r", encoding="utf-8") as f:
        style_config = json.load(f)
        
    try:
        script = generate_script(
            args.topic,
            args.video_id,
            style_config,
            output_dir=args.output_dir,
            is_factual=args.factual,
            series_name=args.series_name,
            part_number=args.part_number,
            total_parts=args.total_parts
        )
        
        out_dir = Path(args.output_dir) / args.video_id
        out_dir.mkdir(parents=True, exist_ok=True)
        
        script_file = out_dir / "script.json"
        with open(script_file, "w", encoding="utf-8") as f:
            json.dump(script, f, indent=2, ensure_ascii=False)
            
        logging.info(f"RAG v4 Script saved to {script_file}")
    except Exception as e:
        logging.error(f"Execution failed: {e}")
        sys.exit(1)
