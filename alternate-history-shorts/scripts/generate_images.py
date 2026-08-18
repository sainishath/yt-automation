# -*- coding: utf-8 -*-
"""
generate_images.py
------------------
Pipeline-1 standalone module for generating visual beat images from scene_plan.json.

Consumes output/{video_id}/scene_plan.json and generates exactly 1 image per visual beat,
saved as images/{beat_id}.png.

Supports per-beat environment-controlled Fooocus fallback (ALLOW_FOOOCUS_FALLBACK=1).
"""

import os
import sys
import json
import time
import shutil
import random
import argparse
import logging
from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
from gradio_client import Client

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

def validate_image(image_path: Path) -> bool:
    """Verifies that the image is valid, uncorrupted, and not completely black."""
    try:
        if not image_path.exists() or image_path.stat().st_size == 0:
            logging.warning(f"Image file does not exist or is empty: {image_path}")
            return False
            
        # Check integrity
        with Image.open(image_path) as img:
            img.verify()
            
        # Check for black frame / blank frame
        with Image.open(image_path) as img:
            extrema = img.getextrema()
            is_black = True
            if isinstance(extrema[0], tuple):
                for min_val, max_val in extrema:
                    if max_val > 8:
                        is_black = False
                        break
            else:
                min_val, max_val = extrema
                if max_val > 8:
                    is_black = False
                    
            if is_black:
                logging.warning(f"Image is completely black or blank: {image_path}")
                return False
                
        return True
    except Exception as e:
        logging.warning(f"Image validation failed: {e}")
        return False

def resolve_aspect_ratio(target: str, choices: list) -> str:
    """Finds the choice string that matches the target aspect ratio prefix."""
    target_clean = target.replace("*", "×").replace("x", "×").split(" ")[0]
    for choice in choices:
        val = choice[1] if isinstance(choice, list) else choice
        if val.startswith(target_clean):
            return val
    return choices[0][1] if isinstance(choices[0], list) else choices[0]

def find_newest_png(outputs_dir: Path, since_time: float) -> Path:
    """Finds the newest PNG file created in outputs_dir since since_time."""
    png_files = list(outputs_dir.glob("**/*.png"))
    valid_files = []
    for f in png_files:
        try:
            mtime = f.stat().st_mtime
            if mtime >= since_time:
                valid_files.append((f, mtime))
        except Exception:
            pass
    if valid_files:
        valid_files.sort(key=lambda x: x[1], reverse=True)
        return valid_files[0][0]
    return None

def get_dynamic_negative_prompt(visual_prompt: str, base_neg: str) -> str:
    """Removes a negative prompt keyword if the positive visual prompt explicitly requests it."""
    neg_words = [w.strip() for w in base_neg.split(",") if w.strip()]
    visual_prompt_lower = visual_prompt.lower()
    
    filtered_neg_words = []
    for word in neg_words:
        singular_word = word.rstrip('s')
        if len(singular_word) > 2 and singular_word in visual_prompt_lower:
            logging.info(f"Removing '{word}' from negative prompt because it is requested in the positive prompt.")
            continue
        filtered_neg_words.append(word)
        
    return ", ".join(filtered_neg_words)

def generate_pillow_proof_image(beat: dict, out_path: Path, width: int = 896, height: int = 1152) -> bool:
    """
    Generates a high-contrast Pillow proof image for a specific visual beat.
    Ensures safe Unicode rendering and proper portrait dimensions.
    """
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (width, height), color=(20, 26, 38))
        draw = ImageDraw.Draw(img)

        # Draw decorative border
        draw.rectangle([20, 20, width - 20, height - 20], outline=(100, 149, 237), width=5)
        draw.rectangle([30, 30, width - 30, height - 30], outline=(70, 90, 130), width=2)

        beat_id = beat.get("beat_id", "beat_000")
        start_t = beat.get("start_time", 0.0)
        end_t = beat.get("end_time", 0.0)
        dur = beat.get("duration", round(end_t - start_t, 2))
        cam_shot = beat.get("camera_shot", "Cinematic Shot")
        concept = beat.get("visual_concept", "Visual Beat")
        narration = beat.get("narration_text", "")

        # Header banner
        draw.rectangle([40, 50, width - 40, 120], fill=(40, 60, 90))
        
        # Text rendering using default font
        font = ImageFont.load_default()

        draw.text((60, 65), f"PILLOW PROOF FALLBACK | {beat_id.upper()}", fill=(255, 215, 0), font=font)
        draw.text((60, 90), f"Timeline: {start_t:.2f}s -> {end_t:.2f}s (Duration: {dur:.2f}s)", fill=(200, 220, 255), font=font)

        # Main Info
        y = 150
        draw.text((60, y), f"Beat ID: {beat_id}", fill=(240, 240, 240), font=font); y += 30
        draw.text((60, y), f"Camera Shot: {cam_shot}", fill=(180, 230, 180), font=font); y += 40

        # Wrap visual concept text
        draw.text((60, y), "Visual Concept:", fill=(255, 200, 100), font=font); y += 25
        concept_clean = concept.encode("ascii", errors="replace").decode("ascii")
        for line in [concept_clean[i:i+60] for i in range(0, len(concept_clean), 60)][:6]:
            draw.text((80, y), line, fill=(220, 220, 220), font=font); y += 22

        y += 20
        draw.text((60, y), "Narration Excerpt:", fill=(100, 200, 255), font=font); y += 25
        narration_clean = narration.encode("ascii", errors="replace").decode("ascii")
        for line in [narration_clean[i:i+60] for i in range(0, len(narration_clean), 60)][:6]:
            draw.text((80, y), line, fill=(200, 200, 200), font=font); y += 22

        # Status Footer
        draw.rectangle([40, height - 100, width - 40, height - 40], fill=(60, 30, 30))
        draw.text((60, height - 80), "STATUS: FOOOCUS OFFLINE / FALLBACK ACTIVE", fill=(255, 120, 120), font=font)
        draw.text((60, height - 60), "Proof artifact for visual beat assembly testing", fill=(180, 180, 180), font=font)

        img.save(out_path)
        return validate_image(out_path)
    except Exception as e:
        logging.error(f"Failed to generate Pillow proof image for {beat.get('beat_id')}: {e}")
        return False

def generate_fooocus_image(
    client: Client,
    prompt_text: str,
    neg_prompt: str,
    style_list: list,
    aspect_ratio: str,
    out_path: Path,
    max_retries: int = 3
) -> float:
    """Sends generation request using two-step Gradio call, validates output, and saves it."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    ep67 = client.endpoints[67]
    dep67 = ep67.dependency
    comps = {comp['id']: comp for comp in client.config['components']}
    
    for attempt in range(1, max_retries + 1):
        try:
            start_time = time.time()
            logging.info(f"Generating Fooocus image for {out_path.name} (Attempt {attempt}/{max_retries})")
            
            # 1. Build initial args list from default values
            args = []
            for cid in dep67['inputs']:
                if cid in comps:
                    comp = comps[cid]
                    val = comp.get('value')
                    if val is None:
                        val = comp.get('props', {}).get('value')
                    args.append(val)
                else:
                    args.append(None)
                    
            # Sanitize radio lists
            for idx, (cid, ctype) in enumerate(zip(dep67['inputs'], ep67.input_component_types)):
                val = args[idx]
                if ctype == 'radio' and isinstance(val, list):
                    args[idx] = val[1] if len(val) > 1 else val[0]
                    
            # 2. Apply custom overrides
            args[0] = None  # state
            args[1] = False # generate_image_grid_for_each_batch
            args[2] = prompt_text
            args[3] = neg_prompt
            args[4] = style_list
            args[5] = "Speed"
            
            aspect_choices = comps[dep67['inputs'][6]].get('props', {}).get('choices', [])
            args[6] = resolve_aspect_ratio(aspect_ratio, aspect_choices)
            args[7] = 1  # image_number
            args[8] = "png"
            
            seed_val = random.randint(1, 1000000000)
            args[9] = str(seed_val)
            
            args[13] = "juggernautXL_v8Rundiffusion.safetensors" # base_model
            args[14] = "None"  # refiner_model
            args[15] = 0.5     # refiner_switch
            
            # Filter out state components
            filtered_args = []
            for val, ctype in zip(args, ep67.input_component_types):
                if ctype != 'state':
                    filtered_args.append(val)
                    
            # Call step 1: get_task
            client.predict(*filtered_args, fn_index=67)
            
            # Call step 2: generate_clicked
            job_start_time = time.time()
            job = client.submit(fn_index=68)
            
            while not job.done():
                time.sleep(2)
                
            # Copy generated image from Fooocus outputs
            outputs_dir = Path(os.getenv("FOOOCUS_OUTPUTS_DIR", "D:/Projects/Fooocus/outputs"))
            new_img = find_newest_png(outputs_dir, job_start_time - 5.0)
            
            if not new_img:
                import tempfile
                gradio_temp = Path(tempfile.gettempdir()) / "gradio"
                new_img = find_newest_png(gradio_temp, job_start_time - 5.0)
                
            if new_img and new_img.exists():
                shutil.copy(new_img, out_path)
                
            # Validate output image
            if validate_image(out_path):
                gen_time = time.time() - start_time
                logging.info(f"Successfully generated validated image {out_path.name} in {gen_time:.2f}s (Seed: {seed_val})")
                return gen_time
            else:
                logging.warning(f"Image validation failed for output {out_path.name}")
                if out_path.exists():
                    out_path.unlink()
                    
        except Exception as e:
            logging.error(f"Error during Fooocus generation on attempt {attempt}: {e}")
            if out_path.exists():
                try:
                    out_path.unlink()
                except Exception:
                    pass
                    
    raise RuntimeError(f"Failed to generate a valid Fooocus image after {max_retries} attempts.")

def process_video_images(
    video_id: str,
    output_dir: str = "output",
    force_rebuild: bool = False,
    allow_fallback_flag: Optional[bool] = None
) -> dict:
    """
    Consumes output/{video_id}/scene_plan.json and generates exactly 1 image per visual beat.
    Saves output to images/{beat_id}.png.
    """
    video_path = Path(output_dir) / video_id
    plan_path = video_path / "scene_plan.json"
    
    if not plan_path.exists():
        raise FileNotFoundError(
            f"scene_plan.json not found for {video_id} at {plan_path}. "
            f"Run visual_scene_planner.py first before image generation."
        )
        
    with open(plan_path, "r", encoding="utf-8") as pf:
        scene_plan = json.load(pf)
        
    visual_beats = scene_plan.get("visual_beats", [])
    if not visual_beats:
        raise ValueError(f"scene_plan.json for {video_id} contains no visual_beats.")

    # Validate beat IDs uniqueness
    beat_ids = [b.get("beat_id") for b in visual_beats if b.get("beat_id")]
    if len(beat_ids) != len(visual_beats) or len(set(beat_ids)) != len(beat_ids):
        raise ValueError(f"scene_plan.json contains invalid or duplicate beat_id values: {beat_ids}")

    # Determine fallback permission from environment or flag
    env_fallback = os.environ.get("ALLOW_FOOOCUS_FALLBACK", "").strip().lower() in ("1", "true", "yes")
    allow_fallback = env_fallback if allow_fallback_flag is None else allow_fallback_flag
    
    # Load style configuration
    _BASE_DIR = Path(__file__).parent.parent.resolve()
    style_path = _BASE_DIR / "config" / "style.json"
    if not style_path.exists():
        style_path = Path("config/style.json")
    if not style_path.exists():
        raise FileNotFoundError(f"style.json not found in config/ directory ({style_path})")
        
    with open(style_path, "r", encoding="utf-8") as sf:
        style_config = json.load(sf)
        
    aspect_ratio = style_config.get("aspect_ratio", "768*1344")
    neg_prompt = style_config.get("negative_prompt", "low quality, blurry")
    style_list = style_config.get("styles", ["Fooocus Cinematic", "Fooocus V2", "Fooocus Enhance", "Fooocus Sharp"])
    
    images_dir = video_path / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    # Attempt Gradio Client Connection
    logging.info("Connecting to Fooocus Gradio API at http://127.0.0.1:7865/ ...")
    client = None
    try:
        client = Client("http://127.0.0.1:7865/")
        logging.info("Successfully connected to local Fooocus server.")
    except Exception as ce:
        if allow_fallback:
            logging.warning(f"Fooocus offline ({ce}). ALLOW_FOOOCUS_FALLBACK=1 is active. Will generate Pillow proof images.")
        else:
            logging.error(f"Fooocus offline ({ce}) and ALLOW_FOOOCUS_FALLBACK is disabled.")

    fooocus_successes = 0
    pillow_fallbacks = 0
    failures = 0
    total_time = 0.0

    print("\n==============================================")
    print(f"  Stage 4 Image Generation: {video_id} ")
    print(f"  Visual Beats: {len(visual_beats)} | Fallback Allowed: {allow_fallback}")
    print("==============================================\n")
    print(f"{'Beat ID':<10} | {'Timeline (s)':<16} | {'Status':<35}")
    print("-" * 68)

    for idx, beat in enumerate(visual_beats):
        beat_id = beat["beat_id"]
        v_prompt = beat.get("visual_prompt", beat.get("visual_concept", "")).strip()
        start_t = beat.get("start_time", 0.0)
        end_t = beat.get("end_time", 0.0)
        time_str = f"{start_t:05.2f}s -> {end_t:05.2f}s"
        out_path = images_dir / f"{beat_id}.png"

        # Check existing valid image unless force_rebuild
        if not force_rebuild and out_path.exists() and validate_image(out_path):
            logging.info(f"[IMAGE] {beat_id} | {time_str} | Existing Valid Image")
            print(f"{beat_id:<10} | {time_str:<16} | Existing Valid Image")
            fooocus_successes += 1
            beat["image_path"] = str(out_path.as_posix())
            beat["generation_status"] = "completed"
            continue

        beat_success = False

        # 1. Attempt Fooocus Generation
        if client:
            try:
                scene_neg_prompt = get_dynamic_negative_prompt(v_prompt, neg_prompt)
                gen_time = generate_fooocus_image(client, v_prompt, scene_neg_prompt, style_list, aspect_ratio, out_path)
                total_time += gen_time
                fooocus_successes += 1
                beat_success = True
                logging.info(f"[IMAGE] {beat_id} | {time_str} | Fooocus Success ({gen_time:.2f}s)")
                print(f"{beat_id:<10} | {time_str:<16} | Fooocus Success ({gen_time:.2f}s)")
            except Exception as fe:
                logging.warning(f"[IMAGE] {beat_id} | {time_str} | FOOOCUS FAILED ({fe})")

        # 2. Fallback to Pillow proof image if Fooocus failed and fallback is allowed
        if not beat_success:
            if allow_fallback:
                proof_ok = generate_pillow_proof_image(beat, out_path)
                if proof_ok:
                    pillow_fallbacks += 1
                    beat_success = True
                    logging.info(f"[IMAGE] {beat_id} | {time_str} | FOOOCUS FAILED -> PILLOW FALLBACK")
                    print(f"{beat_id:<10} | {time_str:<16} | FOOOCUS FAILED -> PILLOW FALLBACK")
                else:
                    failures += 1
                    logging.error(f"[IMAGE] {beat_id} | {time_str} | PILLOW FALLBACK FAILED")
                    print(f"{beat_id:<10} | {time_str:<16} | PILLOW FALLBACK FAILED")
            else:
                failures += 1
                logging.error(f"[IMAGE] {beat_id} | {time_str} | FOOOCUS FAILED (Fallback Disabled)")
                print(f"{beat_id:<10} | {time_str:<16} | FOOOCUS FAILED (Fallback Disabled)")
                raise RuntimeError(
                    f"Fooocus image generation failed for beat '{beat_id}' and ALLOW_FOOOCUS_FALLBACK is disabled."
                )

        if beat_success:
            beat["image_path"] = str(out_path.as_posix())
            beat["generation_status"] = "completed"
            scene_alias = images_dir / f"scene_{idx:03d}.png"
            if not scene_alias.exists() and out_path.exists():
                try:
                    shutil.copyfile(out_path, scene_alias)
                except Exception:
                    pass

    # Save updated scene_plan.json
    with open(plan_path, "w", encoding="utf-8") as pf:
        json.dump(scene_plan, pf, indent=2, ensure_ascii=False)

    total_images = fooocus_successes + pillow_fallbacks
    print("-" * 68)
    print("  IMAGE GENERATION SUMMARY")
    print(f"  Visual beats:       {len(visual_beats)}")
    print(f"  Fooocus successes:  {fooocus_successes}")
    print(f"  Pillow fallbacks:   {pillow_fallbacks}")
    print(f"  Failures:           {failures}")
    print(f"  Total Images:       {total_images}")
    print("==============================================\n")

    return {
        "video_id": video_id,
        "visual_beats": len(visual_beats),
        "fooocus_successes": fooocus_successes,
        "pillow_fallbacks": pillow_fallbacks,
        "failures": failures,
        "total_images": total_images
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standalone Image Generator for Pipeline 1")
    parser.add_argument("--video_id", required=True, help="Video folder ID to process")
    parser.add_argument("--output_dir", default="output", help="Base output directory")
    parser.add_argument("--force", action="store_true", help="Force regenerate all images")
    parser.add_argument("--fallback", action="store_true", help="Enable Pillow proof fallback")
    args = parser.parse_args()

    # Pass fallback argument if set via CLI
    fallback_flag = True if args.fallback else None

    try:
        process_video_images(
            args.video_id,
            args.output_dir,
            force_rebuild=args.force,
            allow_fallback_flag=fallback_flag
        )
    except Exception as e:
        logging.error(f"Image generation failed: {e}")
        sys.exit(1)
