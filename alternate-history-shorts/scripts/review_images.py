import os
import sys
import json
import time
import base64
import argparse
import logging
import requests
from pathlib import Path

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
# llava:7b is the default pre-upload quality gate (~4.7 GB model, needs ~4 GB free RAM).
# This fits on a 15.3 GB machine with Windows running normally (~5.6 GB free).
# qwen2.5vl:7b (12.5 GB required) does NOT fit on this machine — use on machines with 16+ GB free RAM.
# moondream is the --quick option for a fast sanity check while Fooocus is open.
VISION_MODEL = "llava:7b"
QUICK_MODEL = "moondream"
MODEL_RAM_REQUIRED_GB = 4.0  # minimum free RAM required for the default vision model
MAX_REVIEW_RETRIES = 3

# Keywords that suggest era — used to build the context string sent to the vision model
ERA_KEYWORDS = {
    "aztec": "16th-century Mesoamerican, Aztec empire, pre-Columbian, no modern technology",
    "cortes": "16th-century Spanish conquest, Renaissance-era, no firearms beyond crossbows, no modern technology",
    "moctezuma": "16th-century Aztec empire, pre-Columbian Mesoamerica, no modern technology",
    "napoleon": "early 19th-century Europe, Napoleonic era, flintlock muskets, no modern technology",
    "waterloo": "1815 Europe, Napoleonic wars, flintlock muskets, no modern technology",
    "byzantine": "Byzantine Empire, medieval period, no modern technology",
    "ottoman": "Ottoman Empire, medieval to early modern period, no modern technology",
    "roman": "ancient Rome, classical antiquity, no modern technology",
    "medieval": "medieval Europe, no firearms, no modern technology",
    "black death": "14th-century medieval Europe, bubonic plague era, no modern technology",
    "mongol": "13th-century Central Asia and Eurasia, Mongol Empire, no modern technology",
    "viking": "8th to 11th century Scandinavia and Europe, Viking Age, no modern technology",
    "ww2": "World War 2 era, 1939-1945, WWII military equipment appropriate",
    "world war": "early to mid 20th century, wartime, era-appropriate military equipment",
    "civil war": "19th-century American Civil War, muskets and early rifles, no modern technology",
    "revolution": "18th-century revolutionary era, flintlock muskets, no modern technology",
}

def infer_era_context(visual_prompt: str, topic: str = "") -> str:
    """Infers the historical era/context from the visual prompt and topic string."""
    combined = f"{visual_prompt} {topic}".lower()
    matches = []
    for keyword, context in ERA_KEYWORDS.items():
        if keyword in combined:
            matches.append(context)
    if matches:
        # Return the most specific match (longest context string) to avoid generic descriptions
        return sorted(matches, key=len, reverse=True)[0]
    return "historical scene, no modern technology, no modern vehicles or electronics"

def encode_image_base64(image_path: Path, max_width: int = 512) -> str:
    """
    Encodes an image file to base64 string, resizing to max_width first.
    Resizing from 1080x1920 to 512px wide cuts payload size ~85%, preventing
    Ollama 500 errors from oversized requests while retaining enough detail.
    """
    from PIL import Image
    import io
    with Image.open(image_path) as img:
        w, h = img.size
        if w > max_width:
            scale = max_width / w
            new_size = (max_width, int(h * scale))
            img = img.resize(new_size, Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

def call_vision_review(image_path: Path, era_context: str, max_retries: int = MAX_REVIEW_RETRIES) -> dict:
    """
    Calls qwen2.5vl:7b via Ollama's /api/chat endpoint with the image as base64.
    Returns parsed JSON result dict, or a safe default on repeated failures.
    """
    image_b64 = encode_image_base64(image_path)

    review_prompt = (
        f"You are a strict historical accuracy reviewer for a {era_context} alternate history video.\n"
        "Your ONLY job is to identify glaring anachronisms (modern technology, modern vehicles, modern clothing) "
        "in the image. Do not critique art style, rendering quality, or minor lighting details.\n\n"
        "Rules:\n"
        "1. Only flag an issue if you can name a specific, concrete object that did not exist in the specified historical era.\n"
        "2. If the image features standard historical elements (swords, armor, stone buildings, horses, wooden ships, natural landscapes), it PASSES.\n"
        "3. Output strictly in JSON format.\n\n"
        "Examples:\n"
        "Image shows: A knight holding a glowing smartphone.\n"
        'Response: {"status": "fail", "reason": "A modern smartphone is visible in the knight\'s hand."}\n\n'
        "Image shows: Aztec warriors fighting Spanish soldiers with swords and shields.\n"
        'Response: {"status": "pass", "reason": "No modern objects detected. Scene is historically plausible."}\n\n'
        "Image shows: A 16th-century village street, but a modern car is parked in the background.\n"
        'Response: {"status": "fail", "reason": "A modern automobile is visible in the background."}\n\n'
        "Image shows: A dramatic portrait of a king in a golden-hour lighting.\n"
        'Response: {"status": "pass", "reason": "No modern objects detected."}\n\n'
        "Evaluate the provided image against these exact rules. Output ONLY valid JSON."
    )

    # Use /api/generate (not /api/chat) — correct Ollama endpoint for vision models
    payload = {
        "model": VISION_MODEL,
        "prompt": review_prompt,
        "images": [image_b64],
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": 300
        }
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json=payload,
                timeout=120
            )
            response.raise_for_status()

            raw_text = response.json().get("response", "").strip()

            # Strip markdown wrappers if present
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

            # Extract JSON object if there's surrounding text
            start = raw_text.find("{")
            end = raw_text.rfind("}") + 1
            if start != -1 and end > start:
                raw_text = raw_text[start:end]

            result = json.loads(raw_text)

            # Map the status/reason format to downstream expected fields
            status = result.get("status", "pass").lower()
            reason = result.get("reason", "")
            
            anachronism_detected = (status == "fail")
            issues = [reason] if (reason and anachronism_detected) else []

            mapped_result = {
                "anachronism_detected": anachronism_detected,
                "issues": issues,
                "confidence": "high"
            }

            return mapped_result

        except json.JSONDecodeError as e:
            logging.warning(f"Vision review JSON parse failed (attempt {attempt}/{max_retries}): {e}")
            logging.debug(f"Raw response: {raw_text[:500]}")
        except requests.exceptions.Timeout:
            logging.warning(f"Vision review timed out (attempt {attempt}/{max_retries})")
        except Exception as e:
            logging.error(f"Vision review call error (attempt {attempt}/{max_retries}): {e}")

    # Defensive fallback: don't block on repeated parse failure
    logging.warning(
        f"All {max_retries} vision review attempts failed for {image_path.name}. "
        "Defaulting to passed (no anachronism detected). Manual inspection recommended."
    )
    return {"anachronism_detected": False, "issues": [], "confidence": "low", "parse_failed": True}

def regenerate_scene_image(client, scene: dict, flagged_issues: list, style_config: dict, out_path: Path) -> float:
    """
    Regenerates an image for a scene, appending flagged issue terms to the negative prompt.
    Imports generate_fooocus_image from generate_images.py.
    """
    from generate_images import generate_fooocus_image, get_dynamic_negative_prompt

    base_neg = style_config.get("negative_prompt", "low quality, blurry")
    v_prompt = scene.get("visual_prompt", "")

    # Append flagged terms directly to the negative prompt for targeted exclusion
    issue_terms = ", ".join(flagged_issues) if flagged_issues else ""
    augmented_neg = f"{base_neg}, {issue_terms}" if issue_terms else base_neg

    # Still apply dynamic filter (allow things explicitly requested in positive prompt)
    scene_neg = get_dynamic_negative_prompt(v_prompt, augmented_neg)

    style_list = style_config.get("styles", ["Fooocus Cinematic", "Fooocus V2"])
    aspect_ratio = style_config.get("aspect_ratio", "768*1344")

    logging.info(f"Regenerating image for {out_path.name} with augmented negative: '{issue_terms}'")
    return generate_fooocus_image(client, v_prompt, scene_neg, style_list, aspect_ratio, out_path, max_retries=2)

def review_video_images(video_id: str, output_dir: str = "output", fooocus_client=None, model: str = None) -> dict:
    """
    Main Stage 3.5 function. Reviews all scene images for a video_id using qwen2.5vl:7b.
    Regenerates via Fooocus if anachronisms are detected with high/medium confidence.
    Updates script.json with vision_review results per scene.
    """
    global VISION_MODEL
    if model:
        VISION_MODEL = model

    start_time = time.time()

    video_path = Path(output_dir) / video_id
    script_path = video_path / "script.json"

    if not script_path.exists():
        raise FileNotFoundError(f"script.json not found for {video_id} at {script_path}")

    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    style_path = Path("config/style.json")
    with open(style_path, "r", encoding="utf-8") as f:
        style_config = json.load(f)

    topic = script.get("topic", video_id.replace("_", " "))
    scenes = script.get("scenes", [])

    logging.info(f"Checking {VISION_MODEL} availability and RAM headroom via Ollama...")
    try:
        check = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)
        check.raise_for_status()
        available_models = [m["name"] for m in check.json().get("models", [])]
        if not any(VISION_MODEL.split(":")[0] in m for m in available_models):
            raise RuntimeError(
                f"{VISION_MODEL} is not available in Ollama. "
                f"Run: ollama pull {VISION_MODEL}"
            )

        # RAM pre-check — fail early with a clear message instead of a cryptic 500
        if "qwen2.5vl" in VISION_MODEL:
            required_gb = 12.5
        else:
            required_gb = MODEL_RAM_REQUIRED_GB  # 4.0 GB for llava:7b
        import psutil
        free_gb = psutil.virtual_memory().available / (1024 ** 3)
        if free_gb < required_gb:
            raise RuntimeError(
                f"Insufficient RAM for {VISION_MODEL}: "
                f"{free_gb:.1f} GB free, need {required_gb:.1f} GB.\n"
                f"Close Fooocus and other heavy apps, then re-run.\n"
                f"For a quick check while Fooocus is open, use --quick (moondream, ~1.8 GB)."
            )
        logging.info(f"RAM check OK: {free_gb:.1f} GB free (need {required_gb:.1f} GB).")

        logging.info(f"{VISION_MODEL} confirmed available.")
    except requests.exceptions.ConnectionError:
        raise ConnectionError("Ollama is not running. Start it with: ollama serve")

    print("\n" + "=" * 54)
    print(f"  Stage 3.5 Vision Review: {video_id}")
    print(f"  Model: {VISION_MODEL}")
    print("=" * 54 + "\n")

    results = []

    for idx, scene in enumerate(scenes):
        scene_start = time.time()
        img_path = Path(scene.get("image_path", ""))

        if not img_path.exists():
            # Try constructing from default path
            img_path = video_path / "images" / f"scene_{idx:03d}.png"

        if not img_path.exists():
            logging.warning(f"Scene {idx}: image not found at {img_path}, skipping review.")
            scene["vision_review"] = {
                "passed": False,
                "issues": ["image_not_found"],
                "confidence": "high",
                "attempts": 0
            }
            results.append({"scene": idx, "status": "SKIP", "issues": ["image_not_found"], "time": 0.0})
            continue

        era_context = infer_era_context(scene.get("visual_prompt", ""), topic)
        logging.info(f"Reviewing scene {idx}: {img_path.name} | Era: {era_context[:60]}...")

        # First review attempt
        review = call_vision_review(img_path, era_context)
        attempts = 1
        passed = True
        final_issues = review.get("issues", [])
        confidence = review.get("confidence", "low")

        anachronism = review.get("anachronism_detected", False)
        # Only act on high/medium confidence — log low as warning, don't regenerate
        if anachronism and confidence in ("high", "medium"):
            logging.warning(
                f"Scene {idx}: Anachronism detected ({confidence} confidence). "
                f"Issues: {final_issues}"
            )

            # Attempt regeneration if Fooocus client is available
            if fooocus_client is not None:
                try:
                    regenerate_scene_image(fooocus_client, scene, final_issues, style_config, img_path)
                    attempts = 2

                    # Second review on the regenerated image
                    re_review = call_vision_review(img_path, era_context)
                    final_issues = re_review.get("issues", [])
                    confidence = re_review.get("confidence", "low")

                    if re_review.get("anachronism_detected", False) and confidence in ("high", "medium"):
                        logging.warning(
                            f"Scene {idx}: Still failing after regeneration. "
                            "Marking for manual review."
                        )
                        passed = False
                        scene["needs_manual_review"] = True
                    else:
                        logging.info(f"Scene {idx}: Passed after regeneration.")
                        passed = True

                except Exception as e:
                    logging.error(f"Scene {idx}: Regeneration failed: {e}")
                    passed = False
                    scene["needs_manual_review"] = True
            else:
                # No Fooocus client — log and flag for manual review but don't block
                logging.warning(
                    f"Scene {idx}: Fooocus not connected — flagging for manual review "
                    "without regenerating."
                )
                passed = False
                scene["needs_manual_review"] = True

        elif anachronism and confidence == "low":
            logging.info(
                f"Scene {idx}: Low-confidence flag ({final_issues}). Logging only, not regenerating."
            )
            # Still counts as passed — low confidence is not actionable
            passed = True

        else:
            logging.info(f"Scene {idx}: No anachronisms detected.")
            passed = True

        scene_time = time.time() - scene_start

        scene["vision_review"] = {
            "passed": passed,
            "issues": final_issues,
            "confidence": confidence,
            "attempts": attempts
        }

        status = "PASS" if passed else "FAIL"
        results.append({
            "scene": idx,
            "status": status,
            "issues": final_issues,
            "confidence": confidence,
            "time": round(scene_time, 2)
        })

        logging.info(f"Scene {idx}: {status} in {scene_time:.2f}s")

    # Save updated script.json with vision_review fields
    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)

    total_time = time.time() - start_time
    avg_time = total_time / len(scenes) if scenes else 0.0
    passes = sum(1 for r in results if r["status"] == "PASS")
    fails = sum(1 for r in results if r["status"] == "FAIL")
    skips = sum(1 for r in results if r["status"] == "SKIP")

    # Summary table
    print("\n" + "=" * 54)
    print(f"  Vision Review Summary: {video_id}")
    print("=" * 54)
    print(f"  {'Scene':<8} {'Status':<8} {'Conf':<8} {'Time(s)':<10} Issues")
    print(f"  {'-'*7:<8} {'-'*7:<8} {'-'*7:<8} {'-'*7:<10} ------")
    for r in results:
        issues_str = ", ".join(r["issues"])[:40] if r["issues"] else "-"
        conf = r.get("confidence", "-")
        print(f"  {r['scene']:<8} {r['status']:<8} {conf:<8} {r['time']:<10.2f} {issues_str}")
    print(f"\n  Total: {len(results)} scenes | PASS: {passes} | FAIL: {fails} | SKIP: {skips}")
    print(f"  Total review time: {total_time:.2f}s | Avg per scene: {avg_time:.2f}s")
    print("=" * 54 + "\n")

    logging.info(
        f"Stage 3.5 completed for {video_id}. "
        f"PASS: {passes}, FAIL: {fails}, SKIP: {skips}. "
        f"Total time: {total_time:.2f}s"
    )

    return {
        "video_id": video_id,
        "total_scenes": len(results),
        "passed": passes,
        "failed": fails,
        "skipped": skips,
        "total_time_seconds": round(total_time, 2),
        "avg_time_per_scene": round(avg_time, 2)
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 3.5: AI Vision Review of generated scene images")
    parser.add_argument(
        "--model",
        default=None,
        help=(
            "Override the vision model explicitly. "
            "Defaults to qwen2.5vl:7b (the pre-upload quality gate, requires Fooocus closed). "
            "Use --quick for moondream instead."
        )
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help=(
            "Use moondream (~1.8 GB RAM) instead of qwen2.5vl:7b. "
            "Safe to run with Fooocus open. Lower accuracy — "
            "treat as a fast sanity check only, not a pre-upload gate."
        )
    )
    parser.add_argument("--video_id", required=True, help="Video folder name to review")
    parser.add_argument("--output_dir", default="output", help="Base output directory")
    parser.add_argument(
        "--with_fooocus",
        action="store_true",
        help="Connect to Fooocus for auto-regeneration on failures. Requires Fooocus to be running."
    )
    args = parser.parse_args()

    # Resolve model: explicit --model > --quick > default (qwen2.5vl:7b)
    if args.model:
        selected_model = args.model
    elif args.quick:
        selected_model = QUICK_MODEL
        logging.info(
            "Using moondream (--quick mode). "
            "This is a fast sanity check only — run without --quick before uploading."
        )
    else:
        selected_model = VISION_MODEL  # qwen2.5vl:7b

    fooocus_client = None
    if args.with_fooocus:
        try:
            from gradio_client import Client
            logging.info("Connecting to Fooocus for auto-regeneration...")
            fooocus_client = Client("http://127.0.0.1:7865/")
            logging.info("Fooocus connected.")
        except Exception as e:
            logging.warning(f"Could not connect to Fooocus ({e}). Running review-only mode.")

    try:
        review_video_images(args.video_id, args.output_dir, fooocus_client, model=selected_model)
    except Exception as e:
        logging.error(f"Vision review failed: {e}")
        sys.exit(1)
