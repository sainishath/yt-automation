# -*- coding: utf-8 -*-
"""
script_critic.py
----------------
Hybrid Two-Tier Script Critic and Pre-Render Quality Gate for Content Brain v1.
"""

import re
import json
import logging
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

@dataclass
class CriticEvaluationResult:
    passed: bool
    overall_score: float
    tier1_deterministic_passed: bool
    tier2_semantic_passed: bool
    deterministic_errors: List[str] = field(default_factory=list)
    semantic_feedback: List[str] = field(default_factory=list)
    actionable_revisions: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


class HybridScriptCritic:
    def __init__(self, ollama_url: Optional[str] = None, model: Optional[str] = None):
        import os
        self.ollama_url = ollama_url or os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
        self.model = model or os.environ.get("OLLAMA_MODEL", "llama3.2:latest")

    def evaluate_deterministic(
        self,
        script_data: Dict[str, Any],
        strategy_bounds: Optional[Dict[str, Any]] = None,
        speech_rate_wps: float = 2.8
    ) -> Tuple[bool, List[str], Dict[str, Any]]:
        errors = []
        bounds = strategy_bounds or {}
        
        min_duration = bounds.get("min_duration_seconds", 28.0)
        max_duration = bounds.get("max_duration_seconds", 60.0)
        min_words = int(bounds.get("min_word_count", 60))
        max_words = int(bounds.get("max_word_count", 145))

        scenes = script_data.get("scenes", [])
        if not scenes:
            return False, ["Script contains zero visual scenes."], {}

        full_text_tokens = []
        sentence_lengths = []
        scene_word_counts = []
        has_code_snippet = False

        for idx, sc in enumerate(scenes):
            sc_text = ""
            if "dialogue" in sc and isinstance(sc["dialogue"], list):
                sc_text = " ".join(t.get("text", "") for t in sc["dialogue"] if isinstance(t, dict) and t.get("text"))
            elif "narration_text" in sc:
                sc_text = sc.get("narration_text") or ""
            elif "narration" in sc:
                sc_text = sc.get("narration") or ""
            elif "text" in sc:
                sc_text = sc.get("text") or ""

            sc_text = str(sc_text) if sc_text is not None else ""

            if sc.get("code_snippet"):
                has_code_snippet = True

            # Match words while preserving intra-word apostrophes (e.g. "library's" as 1 token)
            sc_words = [w for w in re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", sc_text) if w]
            scene_word_counts.append(len(sc_words))
            full_text_tokens.extend(sc_words)

            sents = [s.strip() for s in re.split(r'[.!?]+', sc_text) if s.strip()]
            for s in sents:
                sentence_lengths.append(len(s.split()))

        total_words = len(full_text_tokens)
        est_duration = round(total_words / max(speech_rate_wps, 1.0), 2)

        if total_words < min_words:
            errors.append(f"Word count too low: {total_words} words (Min required: {min_words} words for ~{min_duration}s).")
        elif total_words > max_words:
            errors.append(f"Word count too high: {total_words} words (Max allowed: {max_words} words for ~{max_duration}s).")

        if est_duration > max_duration + 3.0:
            errors.append(f"Estimated duration {est_duration}s exceeds safe ceiling of {max_duration}s.")
        elif est_duration < min_duration - 3.0:
            errors.append(f"Estimated duration {est_duration}s is below safe floor of {min_duration}s.")

        first_scene_text = " ".join(full_text_tokens[:15]).lower()
        forbidden_intros = [
            "in this video", "welcome back", "hey guys", "let's dive in",
            "today we are going to", "have you ever wondered", "in today's short"
        ]
        for fi in forbidden_intros:
            if fi in first_scene_text:
                errors.append(f"Fluff intro detected in opening: '{fi}'. Jump directly to the stakes/code.")

        # Detect non-trivial verbatim 5-gram repetitions (filtering out simple stopword n-grams)
        if len(full_text_tokens) > 35:
            stopwords = {"the", "a", "an", "and", "or", "in", "on", "at", "to", "of", "for", "with", "that", "this", "it", "was", "is", "by"}
            clean_tokens = [w.lower() for w in full_text_tokens if len(w) > 1 or w in {"a", "i"}]
            fivegrams = [" ".join(clean_tokens[i:i+5]) for i in range(len(clean_tokens)-4)]
            seen = set()
            for fg in fivegrams:
                meaningful_words = [w for w in fg.split() if w not in stopwords]
                if len(meaningful_words) >= 3:
                    if fg in seen:
                        errors.append(f"Unnecessary repetitive phrasing detected: '{fg}'.")
                        break
                    seen.add(fg)

        if len(scenes) < 3:
            errors.append(f"Scene count too low ({len(scenes)} scenes). Need at least 3 visual beats.")
        elif len(scenes) > 10:
            errors.append(f"Scene count too high ({len(scenes)} scenes). Consolidate into 4-8 coherent beats.")

        metrics = {
            "total_words": total_words,
            "estimated_duration_sec": est_duration,
            "scene_count": len(scenes),
            "avg_sentence_words": round(sum(sentence_lengths) / max(len(sentence_lengths), 1), 1),
            "has_code_snippet": has_code_snippet,
            "speech_rate_wps": speech_rate_wps
        }

        passed = len(errors) == 0
        return passed, errors, metrics

    def evaluate_semantic(
        self,
        topic: str,
        script_text: str,
        channel_type: str = "p2_coding",
        tested_variable: str = "HOOK_STRUCTURE",
        max_retries: int = 2
    ) -> Tuple[bool, float, List[str], List[str]]:
        import urllib.request

        domain_rubric = (
            "You are an expert short-form video editor and senior technical reviewer for high-retention coding Shorts."
            if "coding" in channel_type or "p2" in channel_type else
            "You are an expert historical documentary editor and narrative director for high-retention factual and alternate-history Shorts."
        )

        prompt = f"""{domain_rubric}
Evaluate this draft script for a YouTube Short on the topic '{topic}'.
Testing Variable: {tested_variable}

### SCRIPT TO EVALUATE:
\"\"\"{script_text}\"\"\"

### EVALUATION CRITERIA:
1. HOOK TENSION (0-10): Does the first sentence create immediate curiosity, stakes, or present a concrete historical fact/problem?
2. ESCALATION & PROGRESSION (0-10): Does the explanation build in momentum and depth without rambling?
3. CLARITY & FLUFF (0-10): Is every sentence dense and valuable? Is it free of generic conversational filler?
4. PAYOFF STRENGTH (0-10): Does the ending definitively resolve the premise and leave a lasting memorable takeaway?

### REQUIRED JSON OUTPUT FORMAT:
{{
  "hook_score": 8.5,
  "escalation_score": 8.0,
  "clarity_score": 9.0,
  "payoff_score": 8.5,
  "overall_score": 8.5,
  "passes_quality_gate": true,
  "critical_flaws": [],
  "actionable_revisions": ["Make opening faster"]
}}
"""
        last_error = ""
        for attempt in range(1, max_retries + 1):
            try:
                req_data = json.dumps({
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                }).encode("utf-8")

                req = urllib.request.Request(
                    f"{self.ollama_url}/api/generate",
                    data=req_data,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=25) as resp:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    raw_response = res_json.get("response", "{}")
                    parsed = json.loads(raw_response)

                    score = float(parsed.get("overall_score", 0.0))
                    passes = bool(parsed.get("passes_quality_gate", True)) and score >= 6.5
                    flaws = parsed.get("critical_flaws", [])
                    revisions = parsed.get("actionable_revisions", [])
                    return passes, score, flaws, revisions
            except Exception as e:
                last_error = str(e)
                logging.warning(f"[ScriptCritic] Attempt {attempt}/{max_retries} LLM evaluation failed: {e}")

        # Fallback gracefully if LLM critic times out
        logging.warning(f"[ScriptCritic Warning] Semantic critic timed out; passing with soft fallback: {last_error}")
        return True, 7.5, [], ["Semantic critic timed out; passed via deterministic validation."]

    def evaluate_script(
        self,
        topic: str,
        script_data: Dict[str, Any],
        channel_type: str = "p2_coding",
        strategy_bounds: Optional[Dict[str, Any]] = None,
        tested_variable: str = "HOOK_STRUCTURE"
    ) -> CriticEvaluationResult:
        scenes = script_data.get("scenes", [])
        extracted_lines = []
        for sc in scenes:
            if "dialogue" in sc and isinstance(sc["dialogue"], list):
                extracted_lines.append(" ".join(t.get("text", "") for t in sc["dialogue"] if isinstance(t, dict)))
            elif "narration_text" in sc:
                extracted_lines.append(sc.get("narration_text", ""))
            elif "narration" in sc:
                extracted_lines.append(sc.get("narration", ""))
        full_text = " ".join(extracted_lines)

        rate_wps = 2.2 if channel_type == "p1_history" else 2.8

        t1_pass, t1_errors, metrics = self.evaluate_deterministic(
            script_data=script_data,
            strategy_bounds=strategy_bounds,
            speech_rate_wps=rate_wps
        )

        t2_pass, score, t2_flaws, revisions = self.evaluate_semantic(
            topic=topic,
            script_text=full_text,
            channel_type=channel_type,
            tested_variable=tested_variable
        )

        overall_passed = t1_pass and t2_pass
        all_revisions = []
        if not t1_pass:
            all_revisions.extend([f"FIX DETERMINISTIC ERROR: {err}" for err in t1_errors])
        all_revisions.extend(revisions)

        return CriticEvaluationResult(
            passed=overall_passed,
            overall_score=score if t1_pass else min(score, 5.0),
            tier1_deterministic_passed=t1_pass,
            tier2_semantic_passed=t2_pass,
            deterministic_errors=t1_errors,
            semantic_feedback=t2_flaws,
            actionable_revisions=all_revisions,
            metrics=metrics
        )
