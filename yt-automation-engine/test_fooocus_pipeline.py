import os
import sys
import time
import shutil
import random
import requests
import subprocess
from pathlib import Path
from gradio_client import Client

def test_fooocus_api():
    out_image = Path("data/assets/test_image.png")
    out_image.parent.mkdir(parents=True, exist_ok=True)
    
    prompt = "A glowing neon cyberpunk smartphone, highly detailed, 8k"
    print(f"[TEST] Testing Fooocus generation for prompt: '{prompt}'...")
    
    from media_engine import generate_fooocus_image, validate_image, check_fooocus_online
    
    if not check_fooocus_online():
        print("[TEST ERROR] Fooocus is not reachable on http://127.0.0.1:7865/. Start Fooocus with --port 7865 first.")
        return None
        
    result_path = generate_fooocus_image(prompt, str(out_image))
    
    if result_path and Path(result_path).exists() and validate_image(result_path):
        print(f"[TEST SUCCESS] Fooocus image successfully generated and validated at {result_path}")
        return result_path
    else:
        print(f"[TEST ERROR] Fooocus generation failed or returned invalid image.")
        return None

def test_ffmpeg_overlay(image_path):
    bg_video = "data/assets/raw_gameplay.mp4"
    out_video = "data/assets/test_output.mp4"
    
    if not os.path.exists(bg_video):
        print(f"[FFMPEG ERROR] Base video missing from disk: {bg_video}")
        return
        
    bg_f = bg_video.replace("\\", "/")
    img_f = image_path.replace("\\", "/")
    out_f = out_video.replace("\\", "/")
    
    filter_complex = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[bg];"
        "[1:v]scale=w=960:h=860:force_original_aspect_ratio=decrease[img0];"
        "[bg][img0]overlay=x=(W-w)/2:y=(1920/2 - h)/2:enable='between(t,0,5)'[final_v]"
    )
    
    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", bg_f,
        "-loop", "1", "-i", img_f,
        "-t", "5",
        "-filter_complex", filter_complex,
        "-map", "[final_v]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        out_f
    ]
    
    print(f"[FFMPEG] Compiling test overlay to {out_video}...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        print("[FFMPEG SUCCESS] Video overlay successfully compiled.")
    else:
        print(f"[FFMPEG ERROR] Compilation failed: {res.stderr}")

if __name__ == "__main__":
    img_path = test_fooocus_api()
    if img_path and os.path.exists(img_path):
        test_ffmpeg_overlay(img_path)
    else:
        print("[PIPELINE INFO] Skipping overlay compilation because image generation failed.")
