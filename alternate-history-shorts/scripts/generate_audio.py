import os
import sys
import json
import argparse
import subprocess
import logging
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

def get_audio_duration(file_path: Path) -> float:
    """Uses ffprobe to measure the actual duration of the generated audio file."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", str(file_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    metadata = json.loads(result.stdout)
    return float(metadata["format"]["duration"])

def generate_scene_audio(text: str, voice: str, out_path: Path, max_retries: int = 3) -> float:
    """Generates audio for a single scene using edge-tts, verifies it, and returns duration."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "edge-tts",
        "--text", text,
        "--voice", voice,
        "--write-media", str(out_path)
    ]
    
    for attempt in range(1, max_retries + 1):
        try:
            logging.info(f"Generating voice for scene to {out_path.name} (Attempt {attempt}/{max_retries})")
            
            # Run Edge TTS
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Verify file exists and has content
            if not out_path.exists() or out_path.stat().st_size == 0:
                raise FileNotFoundError(f"Audio file was not created or is empty: {out_path}")
                
            # Measure actual duration using ffprobe
            duration = get_audio_duration(out_path)
            if duration <= 0.0:
                raise ValueError("Measured audio duration is 0 seconds")
                
            logging.info(f"Successfully generated {out_path.name}: {duration:.2f}s")
            return round(duration, 2)
            
        except Exception as e:
            logging.warning(f"Failed attempt {attempt} to generate {out_path.name}: {e}")
            if out_path.exists():
                try:
                    out_path.unlink()
                except Exception:
                    pass
                    
    raise RuntimeError(f"Failed to generate valid audio for scene after {max_retries} attempts.")

def process_video_audio(video_id: str, output_dir: str = "output") -> dict:
    video_path = Path(output_dir) / video_id
    script_path = video_path / "script.json"
    
    if not script_path.exists():
        raise FileNotFoundError(f"script.json not found for {video_id} at {script_path}")
        
    # Load voice config
    _BASE_DIR = Path(__file__).parent.parent.resolve()
    voice_path = _BASE_DIR / "config" / "voice.json"
    if not voice_path.exists():
        voice_path = Path("config/voice.json")
    voice = "en-US-ChristopherNeural"
    if voice_path.exists():
        with open(voice_path, "r", encoding="utf-8") as f:
            voice = json.load(f).get("voice", voice)
            
    logging.info(f"Using narrator voice: {voice}")
    
    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)
        
    scenes = script.get("scenes", [])
    audio_dir = video_path / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    total_estimated = 0.0
    total_actual = 0.0
    
    print("\n==============================================")
    print(f"  Stage 2 TTS Audio Generation: {video_id} ")
    print("==============================================\n")
    print(f"{'Scene':<6} | {'Words':<5} | {'Est. (s)':<8} | {'Act. (s)':<8} | {'Delta (s)':<9}")
    print("-" * 50)
    
    for idx, scene in enumerate(scenes):
        narration = scene.get("narration", "").strip()
        words = len(narration.split())
        est_duration = scene.get("estimated_duration_seconds", 0.0)
        total_estimated += est_duration
        
        # Output file path
        out_path = audio_dir / f"scene_{idx:03d}.mp3"
        
        # Generate and measure
        actual_duration = generate_scene_audio(narration, voice, out_path)
        total_actual += actual_duration
        
        # Save actual duration back to the script data
        scene["actual_duration_seconds"] = actual_duration
        
        # Calculate delta
        delta = actual_duration - est_duration
        print(f"#{idx:<4} | {words:<5} | {est_duration:<8.1f} | {actual_duration:<8.2f} | {delta:<+9.2f}")
        
    # Save the updated script back to the folder
    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)
        
    total_delta = total_actual - total_estimated
    print("-" * 50)
    print(f"Total  | {'-':<5} | {total_estimated:<8.1f} | {total_actual:<8.2f} | {total_delta:<+9.2f}")
    print("==============================================\n")
    
    return {
        "video_id": video_id,
        "total_estimated": round(total_estimated, 2),
        "total_actual": round(total_actual, 2),
        "total_delta": round(total_delta, 2)
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video_id", required=True, help="Video folder name to process")
    parser.add_argument("--output_dir", default="output", help="Base output directory")
    args = parser.parse_args()
    
    try:
        process_video_audio(args.video_id, args.output_dir)
    except Exception as e:
        logging.error(f"TTS audio generation failed: {e}")
        sys.exit(1)
