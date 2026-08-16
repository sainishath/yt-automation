# -*- coding: utf-8 -*-
"""
regenerate_asset.py
-------------------
Script to regenerate a specific segment image within a job folder using an optional prompt override.
Overwrites the existing image file and updates the script JSON.
"""

import sys
import json
import argparse
from pathlib import Path

# Add engine directory to system path
_DIR = Path(__file__).resolve().parent
sys.path.append(str(_DIR))

from media_engine import generate_fooocus_image, CFG

def regenerate_segment_image(job_id: str, segment_id: str, override_prompt: str = None) -> bool:
    """
    Finds the segment_id in the script.json for job_id, updates prompt if provided,
    and runs Fooocus to generate a new 1024x1024 image, overwriting the old one.
    """
    output_dir = (_DIR / CFG["output_dir"]).resolve()
    job_folder = output_dir / job_id
    script_path = job_folder / "script.json"
    
    if not script_path.exists():
        print(f"[Regen] Error: Job script not found at {script_path}")
        return False
        
    with open(script_path, "r", encoding="utf-8") as f:
        script_data = json.load(f)
        
    segments = script_data.get("segments", [])
    target_segment = None
    
    for seg in segments:
        if seg.get("segment_id") == segment_id:
            target_segment = seg
            break
            
    if not target_segment:
        print(f"[Regen] Error: Segment {segment_id} not found in job {job_id}")
        return False
        
    # Use override prompt if provided, else use original prompt
    prompt = override_prompt if override_prompt else target_segment.get("visual_topic_prompt")
    if override_prompt:
        target_segment["visual_topic_prompt"] = override_prompt
        # Also update the visual_topic_prompt on the individual lines inside the segment
        for line in target_segment.get("lines", []):
            line["visual_topic_prompt"] = override_prompt
            
    print(f"[Regen] Regenerating {segment_id} image for job {job_id} using prompt: {prompt}")
    
    # Save target path (overwrite old asset)
    images_dir = job_folder / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    target_image_path = images_dir / f"{segment_id}.png"
    
    success_path = generate_fooocus_image(prompt, str(target_image_path))
    
    if success_path:
        # Write modified script back to script.json
        with open(script_path, "w", encoding="utf-8") as f:
            json.dump(script_data, f, indent=2)
        print(f"[Regen] Success! Overwrote image at {target_image_path}")
        return True
    else:
        print("[Regen] Error: Fooocus generation failed.")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Regenerate a single segment image")
    parser.add_argument("--job_id", required=True, help="Job/video UUID or directory name")
    parser.add_argument("--segment_id", required=True, help="Segment ID to regenerate (e.g. segment_0)")
    parser.add_argument("--prompt", default=None, help="Optional prompt override text")
    
    args = parser.parse_args()
    
    success = regenerate_segment_image(args.job_id, args.segment_id, args.prompt)
    sys.exit(0 if success else 1)
