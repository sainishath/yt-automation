import os
import sys
import json
import argparse
from pathlib import Path

# Add scripts directory to path to import pipeline stages
sys.path.append(str(Path(__file__).parent))
from generate_script import generate_script
from generate_audio import process_video_audio
from generate_images import process_video_images
from review_images import review_video_images
from generate_metadata import generate_video_metadata

def run_tests(skip_images: bool = False, skip_review: bool = False, skip_upload: bool = False, privacy: str = "private"):
    topics_file = Path("config/topics.json")
    if not topics_file.exists():
        print("topics.json not found!")
        sys.exit(1)
        
    style_file = Path("config/style.json")
    if not style_file.exists():
        print("style.json not found!")
        sys.exit(1)
        
    with open(topics_file, "r", encoding="utf-8") as f:
        topics = json.load(f)
        
    with open(style_file, "r", encoding="utf-8") as f:
        style_config = json.load(f)
        
    print(f"Found {len(topics)} topics. Starting test runs...\n")
    
    for idx, topic in enumerate(topics, start=1):
        video_id = f"video_{idx:03d}"
        print(f"=== Generating Script & Audio {idx}/10: {video_id} ===")
        print(f"Topic: {topic}")
        
        try:
            script = generate_script(topic, video_id, style_config)
            
            # Save output script
            out_dir = Path("output") / video_id
            out_dir.mkdir(parents=True, exist_ok=True)
            script_file = out_dir / "script.json"
            with open(script_file, "w", encoding="utf-8") as f:
                json.dump(script, f, indent=2, ensure_ascii=False)
                
            # Perform Hook Formula Check
            scenes = script.get("scenes", [])
            hook = script.get("hook", "N/A")
            
            # Print timing info and specific hook checks
            total_duration = 0.0
            opener_scene = None
            mid_scene = None
            payoff_scene = None
            
            for s_idx, scene in enumerate(scenes):
                duration = scene.get("estimated_duration_seconds", 0.0)
                start_time = total_duration
                end_time = total_duration + duration
                total_duration = end_time
                
                # Check for 0-3s opener
                if s_idx == 0:
                    opener_scene = scene
                # Check scene nearest to 15-20s mark
                if start_time <= 17.5 <= end_time or (mid_scene is None and start_time >= 15.0):
                    mid_scene = scene
                # Check scene nearest to 40-45s mark
                if start_time <= 42.5 <= end_time or (payoff_scene is None and start_time >= 40.0):
                    payoff_scene = scene
            
            print("\n--- HOOK FORMULA VERIFICATION CHECK ---")
            print(f"OPPOSED HOOK (Overall): {hook}")
            if opener_scene:
                print(f"[0-3s] Opener (Scene 1) Narration ({opener_scene['estimated_duration_seconds']}s):")
                print(f"      \"{opener_scene['narration']}\"")
            if mid_scene:
                print(f"[15-20s] Secondary Hook Narration ({mid_scene['estimated_duration_seconds']}s):")
                print(f"      \"{mid_scene['narration']}\"")
            if payoff_scene:
                print(f"[40-45s] Payoff/Twist Narration ({payoff_scene['estimated_duration_seconds']}s):")
                print(f"      \"{payoff_scene['narration']}\"")
            print(f"Total Duration: {total_duration:.1f} seconds")
            print(f"Number of Scenes: {len(scenes)}")
            print(f"Script saved to: {script_file}\n")
            
            # Run Stage 2 TTS Generation
            process_video_audio(video_id)

            # Stage 3: Image Generation
            if not skip_images:
                process_video_images(video_id)

            # Stage 3.5: Vision Review
            if not skip_review:
                try:
                    review_video_images(video_id)
                except Exception as review_err:
                    print(f"WARNING: Vision review failed for {video_id}: {review_err}")
                    print("Continuing pipeline — review manually or re-run review_images.py.")

            # Stage 5: Metadata Generation
            if not skip_upload:
                try:
                    generate_video_metadata(video_id)
                except Exception as meta_err:
                    print(f"WARNING: Metadata generation failed for {video_id}: {meta_err}")

        except Exception as e:
            print(f"ERROR processing topic '{topic}': {e}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the full YT Shorts pipeline batch")
    parser.add_argument(
        "--skip_images", action="store_true",
        help="Skip Stage 3 image generation (useful if images already exist)"
    )
    parser.add_argument(
        "--skip_review", action="store_true",
        help="Skip Stage 3.5 vision review (faster runs, no anachronism checking)"
    )
    parser.add_argument(
        "--skip_upload", action="store_true",
        help="Skip Stage 5 metadata generation and YouTube upload"
    )
    parser.add_argument(
        "--privacy",
        choices=["private", "unlisted", "public"],
        default="private",
        help="YouTube privacy status for uploads (default: private)"
    )
    args = parser.parse_args()
    run_tests(
        skip_images=args.skip_images,
        skip_review=args.skip_review,
        skip_upload=args.skip_upload,
        privacy=args.privacy
    )

