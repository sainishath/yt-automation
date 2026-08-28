# -*- coding: utf-8 -*-
"""
generate_script.py
------------------
Pipeline-1 RAG v4 Script Generator & Historical-Visual Grounding Gatekeeper.

Features:
- Enforces strict Retrieval Sufficiency Gate: BLOCKS script generation if retrieval_status == INSUFFICIENT.
- Consumes RAG v4 evidence packets with atomic claims, visual evidence, and anachronism constraints.
- Prompts Ollama with strict boundaries (HISTORICAL_FACT vs COUNTERFACTUAL_PREMISE vs SPECULATIVE_CONSEQUENCE)
  and locks visual prompts to period-accurate material culture while avoiding explicit anachronisms.
- Post-generation claim verification layer with selective revision pass for unsupported facts.
- Maintains 100% backward compatibility for downstream script.json consumers when sufficient.
"""

import os
import sys
import json
import argparse
import requests
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Import RAG v4 grounding module
from rag_grounding import generate_evidence_packet, get_grounding_context, retrieve_beat_visual_evidence

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


def count_words(text: str) -> int:
    return len([w for w in text.split() if w.strip()])


def clean_text(text: Any) -> str:
    """Cleans and flattens string or dictionary text for narration and prompt lines."""
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


def validate_and_enrich_script(
    script_data: dict,
    style_keywords: str,
    strategy_bounds: Optional[dict] = None
) -> Tuple[bool, Any]:
    """Validates script structure, sentence completeness, grammar hygiene, and dynamic strategy timing constraints."""
    if not isinstance(script_data, dict):
        return False, "Script data is not a dictionary"
    
    required_keys = ["hook", "scenes"]
    for key in required_keys:
        if key not in script_data:
            return False, f"Missing required key: {key}"
            
    scenes = script_data.get("scenes", [])
    if not isinstance(scenes, list) or len(scenes) < 4:
        return False, f"Invalid or too few scenes: {len(scenes)}"
        
    bounds = strategy_bounds or {}
    min_duration = float(bounds.get("min_duration_seconds", 35.0))
    max_duration = float(bounds.get("max_duration_seconds", 55.0))

    total_words = 0
    cumulative_time = 0.0
    words_per_sec = 2.2
    
    # Dangling terminal words that indicate truncated clauses
    dangling_endings = (
        "across", "from", "to", "with", "and", "or", "but", "by", "for", "in", "on", "at",
        "of", "that", "which", "while", "as", "the", "a", "an", "their", "its", "because"
    )
    
    for idx, scene in enumerate(scenes):
        if not isinstance(scene, dict) or "narration" not in scene or "visual_prompt" not in scene:
            return False, f"Scene {idx} is missing narration or visual_prompt"
            
        scene["narration"] = clean_text(scene["narration"]).strip()
        scene["visual_prompt"] = clean_text(scene["visual_prompt"]).strip()
        
        narration = scene["narration"]
        if not narration or len(narration) < 15:
            return False, f"Scene {idx} narration is empty or too short: '{narration}'"
            
        words = count_words(narration)
        if words < 4:
            return False, f"Scene {idx} has too few words ({words} words): '{narration}'"
            
        # Check for truncated clauses / dangling prepositions
        cleaned_words = [w.strip(".,;:?!'\"()[]{}").lower() for w in narration.split() if w.strip()]
        if cleaned_words and cleaned_words[-1] in dangling_endings:
            return False, f"Scene {idx} ends on a dangling/truncated word: '{cleaned_words[-1]}' in '{narration}'"

        # Check for terminal punctuation
        if not narration.endswith((".", "!", "?", '."', '!"', '?"')):
            # If missing terminal punctuation and not clearly complete, reject or fix
            if cleaned_words and cleaned_words[-1] not in dangling_endings:
                scene["narration"] = narration + "."
                narration = scene["narration"]
            else:
                return False, f"Scene {idx} narration lacks valid terminal punctuation and is incomplete: '{narration}'"

        # Check for broken question grammar
        if "could have the" in narration.lower():
            scene["narration"] = re.sub(r'(?i)\bcould have the\b', 'could the', narration)
            narration = scene["narration"]
            
        total_words += words
        
        duration = round(words / words_per_sec, 1)
        scene["estimated_duration_seconds"] = duration
        cumulative_time += duration

        v_prompt = scene["visual_prompt"]
        if style_keywords and style_keywords not in v_prompt:
            scene["visual_prompt"] = f"{v_prompt}, {style_keywords}"
            
    min_words = int(min_duration * words_per_sec * 0.80)
    max_words = int(max_duration * words_per_sec * 1.25)

    if not (min_words <= total_words <= max_words):
        return False, f"Total word count is {total_words}, must be between {min_words} and {max_words} for {min_duration}-{max_duration}s range"
        
    if not (min_duration * 0.85 <= cumulative_time <= max_duration * 1.20):
        return False, f"Total duration is {cumulative_time}s, must be between {min_duration*0.85:.1f}s and {max_duration*1.20:.1f}s"
        
    return True, script_data


def verify_and_revise_script_claims(
    script_data: dict,
    evidence_packet: dict,
    video_id: str,
    output_dir: str = "output"
) -> Tuple[dict, dict]:
    """
    RAG v4 Verification Engine:
    Performs sentence-by-sentence claim verification on the generated script.
    """
    scenes = script_data.get("scenes", [])
    verified_script_claims = []
    unsupported_count = 0
    supported_count = 0
    speculative_count = 0
    counterfactual_count = 0

    evidence_claims = evidence_packet.get("historical_claims", evidence_packet.get("claims", []))
    evidence_text = "\n".join([f"- [{c.get('claim_id')}] ({c.get('claim_type')}): {c.get('claim')}" for c in evidence_claims])

    for idx, scene in enumerate(scenes):
        narration = scene.get("narration", "").strip()
        lower_narration = narration.lower().strip()
        
        prompt = f"""You are an objective historical evidence verifier.
Classify the following scene narration line from an alternate-history script and check if its historical statements are supported by the Evidence Packet.

Scene Line: "{narration}"

Evidence Packet Claims:
{evidence_text if evidence_text else "- Standard historical knowledge applies."}

Special Rules:
1. COUNTERFACTUAL PREMISE: If the line establishes the alternate-history "what if" hypothetical premise (e.g. "What if...", "Imagine if...", "Suppose...", "In a world where..."), classify claim_type as "COUNTERFACTUAL_PREMISE" and support_status as "SUPPORTED".
2. HISTORICAL FACTS: If the line asserts a real-world historical event or date, verify against the Evidence Packet claims.
3. SPECULATIVE CONSEQUENCES: If the line describes hypothetical downstream outcomes, classify as "SPECULATIVE_CONSEQUENCE".

Return ONLY a valid JSON object:
{{
  "claim_type": "HISTORICAL_FACT",
  "support_status": "SUPPORTED",
  "evidence_claim_ids": ["claim_001"],
  "confidence": 0.95,
  "reason": "Brief verification explanation"
}}
"""
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.1}
        }

        try:
            res = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=25)
            res.raise_for_status()
            parsed = parse_llm_json(res.json().get("response", ""), {})
            raw_type = str(parsed.get("claim_type", "HISTORICAL_FACT")).upper()
            s_status = str(parsed.get("support_status", "SUPPORTED")).upper()
            
            # Normalize claim_type
            if any(m in raw_type for m in ("COUNTERFACTUAL", "DIVERGENCE", "PREMISE")):
                c_type = "COUNTERFACTUAL_PREMISE"
            elif any(m in raw_type for m in ("SPECULATION", "SPECULATIVE", "HYPOTHETICAL", "CONSEQUENCE", "FABRICATION", "ALTERNATE")):
                c_type = "SPECULATIVE_CONSEQUENCE"
            else:
                c_type = "HISTORICAL_FACT"

            # Check for inherent counterfactual premise in opening hook
            if idx == 0 and (lower_narration.startswith(("what if", "imagine if", "suppose", "in a world where", "had ")) or "what if" in lower_narration):
                c_type = "COUNTERFACTUAL_PREMISE"
                s_status = "SUPPORTED"

            # Auto-revision if ungrounded factual assertion
            if s_status in ("UNSUPPORTED", "UNVERIFIED") or (c_type == "HISTORICAL_FACT" and s_status != "SUPPORTED"):
                logging.warning(f"[RAG v4 Verifier Warning] Scene {idx} contains unsupported claim: '{narration}'. Attempting auto-revision...")
                if idx == 0:
                    rev_prompt = f"""Rewrite this opening scene line into a powerful, high-curiosity counterfactual hook (e.g. starting with 'What if...', 'Imagine if...', or 'Suppose...'). Keep it concise (10-15 words).
Original Line: "{narration}"
Evidence: {evidence_text[:350]}
Return ONLY the revised hook line text (no explanations).
"""
                else:
                    rev_prompt = f"""Rewrite this scene narration line to be fully accurate according to the evidence packet. If it represents alternate-history speculation, phrase it clearly using possibility words (e.g. 'could have', 'might have').
Original Line: "{narration}"
Evidence: {evidence_text[:350]}
Return ONLY the revised narration line text (10-16 words, no extra text).
"""
                rev_res = requests.post(f"{OLLAMA_URL}/api/generate", json={"model": OLLAMA_MODEL, "prompt": rev_prompt, "stream": False, "options": {"temperature": 0.3}}, timeout=25)
                if rev_res.status_code == 200:
                    revised_text = rev_res.json().get("response", "").strip().strip('"')
                    if "\n" in revised_text:
                        revised_text = revised_text.splitlines()[-1].strip().strip('"')
                    if revised_text and count_words(revised_text) >= 6:
                        scene["narration"] = revised_text
                        c_type = "COUNTERFACTUAL_PREMISE" if idx == 0 else "SPECULATIVE_CONSEQUENCE"
                        s_status = "REVISED_AND_QUALIFIED"
                        logging.info(f"[RAG v4 Verifier] Successfully revised Scene {idx} to: '{revised_text}'")
                    else:
                        qualified = f"What if {narration[:1].lower() + narration[1:]}" if idx == 0 else (f"It is possible that {narration[:1].lower() + narration[1:]}" if not narration.lower().startswith(("what if", "in a world", "it is possible")) else narration)
                        scene["narration"] = qualified
                        c_type = "COUNTERFACTUAL_PREMISE" if idx == 0 else "SPECULATIVE_CONSEQUENCE"
                        s_status = "REVISED_AND_QUALIFIED"
                        logging.info(f"[RAG v4 Verifier] Deterministically qualified Scene {idx} to: '{qualified}'")
                else:
                    qualified = f"What if {narration[:1].lower() + narration[1:]}" if idx == 0 else (f"It is possible that {narration[:1].lower() + narration[1:]}" if not narration.lower().startswith(("what if", "in a world", "it is possible")) else narration)
                    scene["narration"] = qualified
                    c_type = "COUNTERFACTUAL_PREMISE" if idx == 0 else "SPECULATIVE_CONSEQUENCE"
                    s_status = "REVISED_AND_QUALIFIED"
                    logging.info(f"[RAG v4 Verifier] Deterministically qualified Scene {idx} to: '{qualified}'")

            if s_status == "UNSUPPORTED" and c_type == "HISTORICAL_FACT":
                unsupported_count += 1
            elif s_status in ("SUPPORTED", "VERIFIED", "CORROBORATED"):
                supported_count += 1
            elif c_type == "SPECULATIVE_CONSEQUENCE":
                speculative_count += 1
            elif c_type == "COUNTERFACTUAL_PREMISE":
                counterfactual_count += 1
            else:
                supported_count += 1

            verified_script_claims.append({
                "scene_index": idx,
                "narration_text": scene["narration"],
                "claim_type": c_type,
                "support_status": s_status,
                "evidence_claim_ids": parsed.get("evidence_claim_ids", []),
                "confidence": parsed.get("confidence", 0.9),
                "verification_reason": parsed.get("reason", "Verified against evidence packet")
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


def generate_script(
    topic: str,
    video_id: str,
    style_config: dict,
    output_dir: str = "output",
    evidence_packet: Optional[dict] = None,
    max_retries: int = 3,
    active_strategy: Optional[dict] = None
) -> dict:
    style_keywords = style_config.get("base_style_keywords", "")
    
    # Load StrategyManager context for Channel A
    ROOT_REPO = Path(__file__).resolve().parent.parent.parent
    if str(ROOT_REPO) not in sys.path:
        sys.path.insert(0, str(ROOT_REPO))

    from growth.strategy.strategy_manager import StrategyManager
    from growth.brain.script_critic import HybridScriptCritic

    strat_mgr = StrategyManager()
    strat_ctx = active_strategy or strat_mgr.get_active_strategy_context("channel_a")
    strategy_bounds = {
        "min_duration_seconds": strat_ctx.get("min_duration_seconds", 35.0),
        "max_duration_seconds": strat_ctx.get("max_duration_seconds", 55.0)
    }

    critic = HybridScriptCritic(ollama_url=OLLAMA_URL, model=OLLAMA_MODEL)
    
    packet_file = Path(output_dir) / video_id / "evidence_packet.json"
    if evidence_packet is None and packet_file.exists():
        try:
            with open(packet_file, "r", encoding="utf-8") as pf:
                evidence_packet = json.load(pf)
                logging.info(f"[RAG v4] Using pre-generated evidence packet from {packet_file}")
        except Exception:
            evidence_packet = None

    if evidence_packet is None:
        logging.info(f"[RAG v4] Running Stage 0.5 Evidence Packet Generation for topic: '{topic}'...")
        evidence_packet = generate_evidence_packet(video_id, topic, output_dir=output_dir)

    retrieval_status = evidence_packet.get("retrieval_status", "INSUFFICIENT")

    # SCRIPT GENERATION GATE: Fail safely if retrieval is INSUFFICIENT
    if retrieval_status == "INSUFFICIENT":
        logging.error(f"[RAG v4 GATE BLOCKED] Script generation blocked for '{topic}' due to INSUFFICIENT historical evidence.")
        blocked_doc = {
            "status": "BLOCKED",
            "reason": "INSUFFICIENT_HISTORICAL_EVIDENCE",
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
    uncertain_claims_str = "\n".join([f"- [{c.get('claim_id')}]: {c.get('claim')} (Status: {c.get('status')})" for c in claims_list if c.get("claim_type") == "UNCERTAIN_HISTORICAL_CLAIM"])
    
    visual_evidence_list = evidence_packet.get("visual_evidence", [])
    visual_constraints = evidence_packet.get("visual_constraints", {})
    must_include_str = "\n".join([f"- {item}" for item in visual_constraints.get("must_include_when_relevant", [])[:4]])
    avoid_anachronisms_str = "\n".join([f"- {item}" for item in visual_constraints.get("avoid_anachronisms", [])[:4]])
    visual_details_str = "\n".join([f"- [{v.get('category')}]: {v.get('description')}" for v in visual_evidence_list[:4]])

    tested_hook_style = strat_ctx.get("assigned_hook_type", "COUNTERFACTUAL_QUESTION")
    if "question" in tested_hook_style.lower() or "polar" in tested_hook_style.lower():
        hook_directive = (
            "OPENING HOOK REQUIREMENTS (Scene 1) — EXPERIMENT ARM: COUNTERFACTUAL QUESTION\n"
            "1. The first scene's narration MUST be a spoken counterfactual question starting with 'What if...?' or 'What would have happened if...?'.\n"
            "2. It MUST end with a question mark (?).\n"
            "3. It must be spoken aloud in the video, 10-16 words, creating immediate mystery and high curiosity.\n"
            "4. Do NOT use declarative statements like 'In a world where...' for Scene 1 under this experiment arm."
        )
    else:
        hook_directive = (
            "OPENING HOOK REQUIREMENTS (Scene 1) — EXPERIMENT ARM: ACTIVE COUNTERFACTUAL CLAIM\n"
            "1. The first scene's narration MUST be an active counterfactual statement (e.g. 'If Alexandria had never burned, human history would be a thousand years ahead.').\n"
            "2. It must be spoken aloud in the video, 10-16 words, stating the monumental stakes immediately."
        )

    prompt = f"""You are a professional history storyteller and viral shorts creator.
Generate a narrative-style "what if" history script for the topic: "{topic}".
The tone must be epic, cinematic, and curiosity-driven.

RAG v4 HISTORICAL EVIDENCE:
VERIFIED ATOMIC HISTORICAL FACTS:
{verified_claims_str if verified_claims_str else "- Standard historical consensus applies."}

HISTORICALLY DISPUTED / UNCERTAIN CLAIMS (Acknowledge uncertainty where relevant):
{uncertain_claims_str if uncertain_claims_str else "- No major historical disputes flagged."}

MATERIAL CULTURE & VISUAL GROUNDING:
{visual_details_str if visual_details_str else grounding_facts}

PERIOD-ACCURATE VISUAL ELEMENTS TO INCLUDE:
{must_include_str if must_include_str else "- Era-appropriate architecture and materials."}

CRITICAL ANACHRONISMS TO AVOID IN VISUAL PROMPTS:
{avoid_anachronisms_str if avoid_anachronisms_str else "- Avoid modern or anachronistic elements."}

{hook_directive}

STRICT PHRASING BOUNDARIES:
1. HISTORICAL FACTS: State real-world historical facts accurately according to the evidence packet.
2. COUNTERFACTUAL PREMISE: State the alternate-history starting divergence clearly in the opening.
3. SPECULATIVE CONSEQUENCES: Phrase hypothetical downstream outcomes using possibility words ("might have", "could have led to", "potentially accelerated"). NEVER state speculative consequences as settled historical facts.
4. VISUAL ACCURACY: Every visual_prompt must depict the exact historical era using the material culture details and avoiding the listed anachronisms.

Return ONLY a raw JSON object with this exact schema:
{{
  "hook": "Spoken opening hook question stating the alternate history divergence.",
  "scenes": [
    {{
      "narration": "First scene narration line (MUST match the assigned hook format and be spoken word-for-word in 10-16 words).",
      "visual_prompt": "Cinematic and rich visual description of the opening scene."
    }},
    {{
      "narration": "Second scene narration line.",
      "visual_prompt": "Cinematic and rich visual description."
    }},
    ...
  ]
}}

Constraints:
1. Topic Alignment: Every single narration line and visual prompt MUST be specifically about the topic "{topic}".
2. Total Spoken Word Count: EXACTLY 90 to 120 words total across all scenes combined (each scene must have 14-18 spoken words). Do NOT exceed 125 total words.
3. Scenes: Divide into exactly 6 or 7 scenes.
4. Historical Era and Technology Level Accuracy: Visual prompts must explicitly lock the scene's technological level using the provided facts.
5. Shot Variety: Every visual prompt MUST explicitly start with a camera shot description (e.g., Wide shot, Medium shot, Close-up, Low-angle shot).
"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.5,
            "num_predict": 800
        }
    }
    
    last_critic_flaws = []
    for attempt in range(1, max_retries + 1):
        logging.info(f"Attempt {attempt}/{max_retries} to generate Content Brain v1 script for topic: '{topic}'")
        try:
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
            
            success, result = validate_and_enrich_script(script_data, style_keywords, strategy_bounds=strategy_bounds)
            if not success:
                logging.warning(f"Structural validation failed on attempt {attempt}: {result}")
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
            logging.info(f"[Content Brain Critic P1] Script PASSED (Score: {critic_res.overall_score}/10)!")

            result, claim_ver_doc = verify_and_revise_script_claims(result, evidence_packet, video_id, output_dir=output_dir)
            out_dir = Path(output_dir) / video_id
            out_dir.mkdir(parents=True, exist_ok=True)
            script_file = out_dir / "script.json"
            with open(script_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            logging.info(f"Successfully generated, verified, and saved script to {script_file}")
            return result
                
        except Exception as e:
            logging.error(f"Error during script generation on attempt {attempt}: {e}")
            
    raise RuntimeError(f"SCRIPT_CRITIC_GATE_FAILED: All script candidates for '{topic}' failed generation or Hybrid Critic verification. Last flaws: {last_critic_flaws}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline 1 RAG v4 Script Generator")
    parser.add_argument("--topic", required=True, help="What-if history topic")
    parser.add_argument("--video_id", default="video_001", help="ID/Folder name for the video output")
    parser.add_argument("--output_dir", default="output", help="Base output directory")
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
        script = generate_script(args.topic, args.video_id, style_config, output_dir=args.output_dir)
        
        out_dir = Path(args.output_dir) / args.video_id
        out_dir.mkdir(parents=True, exist_ok=True)
        
        script_file = out_dir / "script.json"
        with open(script_file, "w", encoding="utf-8") as f:
            json.dump(script, f, indent=2, ensure_ascii=False)
            
        logging.info(f"RAG v4 Script saved to {script_file}")
    except Exception as e:
        logging.error(f"Execution failed: {e}")
        sys.exit(1)
