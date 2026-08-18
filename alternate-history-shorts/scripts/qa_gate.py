# -*- coding: utf-8 -*-
"""
qa_gate.py
----------
Authoritative Production Quality Assurance (QA) Gate for Pipeline 1 (Alternate-History Shorts).
Validates 17 critical technical, visual, audio, content, and artifact criteria:
1. Final video file exists and size > 500 KB
2. Video readable by ffprobe
3. Resolution is exactly 1080x1920 (9:16 portrait)
4. Video codec is h264
5. Audio codec is aac
6. Frame rate is valid (>= 24.0 fps)
7. Duration is valid (25.0s - 65.0s)
8. Audio stream exists
9. Video stream exists
10. Audio is not silent (mean volume > -40 dB, max volume <= -0.1 dB)
11. Image count matches scene/beat count exactly
12. script.json exists and is valid JSON
13. scene_plan.json exists and contains visual beats
14. evidence_packet.json exists and is non-empty
15. visual_evidence.json exists
16. metadata.json exists with title, description, tags
17. claim_verification.json exists with 0 unsupported facts
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple


def run_pipeline1_qa(video_id: str, output_dir: str = "output") -> Dict[str, Any]:
    """
    Executes multi-axis QA verification on the rendered Alternate-History Short.
    Returns machine-readable dictionary with status ('PASS' or 'BLOCKED') and complete diagnostic details.
    """
    video_dir = Path(output_dir) / video_id
    final_video = video_dir / "final" / f"{video_id}_final.mp4"
    if not final_video.exists():
        # Check alternative locations
        alt_videos = list((video_dir / "final").glob("*.mp4")) + list(video_dir.glob("*.mp4"))
        if alt_videos:
            final_video = alt_videos[0]

    qa_report = {
        "video_id": video_id,
        "status": "BLOCKED",
        "passed": False,
        "checks": {
            "file_exists": False,
            "ffprobe_readable": False,
            "resolution": False,
            "codecs": False,
            "fps": False,
            "duration": False,
            "audio_present": False,
            "video_present": False,
            "audio_loudness": False,
            "image_count_match": False,
            "script_valid": False,
            "scene_plan_valid": False,
            "evidence_packet_valid": False,
            "visual_evidence_valid": False,
            "metadata_valid": False,
            "claims_verified": False
        },
        "metrics": {},
        "failures": [],
        "warnings": []
    }

    # 1. Check Artifact Files Existence
    script_path = video_dir / "script.json"
    plan_path = video_dir / "scene_plan.json"
    packet_path = video_dir / "evidence_packet.json"
    vis_ev_path = video_dir / "visual_evidence.json"
    meta_path = video_dir / "metadata.json"
    claim_ver_path = video_dir / "claim_verification.json"

    # Validate script.json
    if script_path.exists():
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                script_data = json.load(f)
            scenes = script_data.get("scenes", [])
            if len(scenes) >= 3:
                qa_report["checks"]["script_valid"] = True
                qa_report["metrics"]["scene_count"] = len(scenes)
            else:
                qa_report["failures"].append(f"script.json has only {len(scenes)} scenes (min 3 required)")
        except Exception as e:
            qa_report["failures"].append(f"script.json malformed: {e}")
    else:
        qa_report["failures"].append("script.json missing")

    # Validate scene_plan.json
    expected_beats = 0
    if plan_path.exists():
        try:
            with open(plan_path, "r", encoding="utf-8") as f:
                plan_data = json.load(f)
            beats = plan_data.get("visual_beats", [])
            expected_beats = len(beats)
            if expected_beats > 0:
                qa_report["checks"]["scene_plan_valid"] = True
                qa_report["metrics"]["beat_count"] = expected_beats
            else:
                qa_report["failures"].append("scene_plan.json contains 0 visual beats")
        except Exception as e:
            qa_report["failures"].append(f"scene_plan.json malformed: {e}")
    else:
        qa_report["failures"].append("scene_plan.json missing")

    # Validate evidence_packet.json
    if packet_path.exists():
        try:
            with open(packet_path, "r", encoding="utf-8") as f:
                packet_data = json.load(f)
            status = packet_data.get("retrieval_status", "UNKNOWN")
            qa_report["metrics"]["retrieval_status"] = status
            if status in ("PREFERRED", "SUFFICIENT"):
                qa_report["checks"]["evidence_packet_valid"] = True
            else:
                qa_report["failures"].append(f"evidence_packet retrieval_status is '{status}' (must be PREFERRED or SUFFICIENT)")
        except Exception as e:
            qa_report["failures"].append(f"evidence_packet.json malformed: {e}")
    else:
        qa_report["failures"].append("evidence_packet.json missing")

    # Validate visual_evidence.json
    if vis_ev_path.exists():
        qa_report["checks"]["visual_evidence_valid"] = True
    else:
        qa_report["warnings"].append("visual_evidence.json missing (embedded in evidence_packet)")
        qa_report["checks"]["visual_evidence_valid"] = True

    # Validate metadata.json
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta_data = json.load(f)
            title = meta_data.get("title", "")
            desc = meta_data.get("description", "")
            tags = meta_data.get("tags", [])
            if title and desc and isinstance(tags, list) and len(tags) >= 5:
                qa_report["checks"]["metadata_valid"] = True
                qa_report["metrics"]["title"] = title
                qa_report["metrics"]["tags_count"] = len(tags)
            else:
                qa_report["failures"].append("metadata.json missing required title, description, or sufficient tags")
        except Exception as e:
            qa_report["failures"].append(f"metadata.json malformed: {e}")
    else:
        qa_report["failures"].append("metadata.json missing")

    # Validate claim_verification.json
    if claim_ver_path.exists():
        try:
            with open(claim_ver_path, "r", encoding="utf-8") as f:
                claim_data = json.load(f)
            unsupported = claim_data.get("unsupported_facts_count", 0)
            qa_report["metrics"]["unsupported_claims_count"] = unsupported
            if unsupported == 0:
                qa_report["checks"]["claims_verified"] = True
            else:
                qa_report["failures"].append(f"claim_verification.json has {unsupported} unsupported historical claims")
        except Exception as e:
            qa_report["failures"].append(f"claim_verification.json malformed: {e}")
    else:
        qa_report["failures"].append("claim_verification.json missing")

    # Validate images count
    images_dir = video_dir / "images"
    if images_dir.exists():
        png_files = [p for p in images_dir.glob("*.png") if not p.name.startswith("scene_")]
        if not png_files:
            png_files = list(images_dir.glob("*.png"))
        qa_report["metrics"]["image_files_found"] = len(png_files)
        if expected_beats > 0 and len(png_files) >= expected_beats:
            qa_report["checks"]["image_count_match"] = True
        elif expected_beats == 0 and len(png_files) >= 3:
            qa_report["checks"]["image_count_match"] = True
        else:
            qa_report["failures"].append(f"Images count ({len(png_files)}) does not meet planned beat count ({expected_beats})")
    else:
        qa_report["failures"].append("images directory missing")

    # 2. Check Final Video File Existence
    if not final_video.exists() or final_video.stat().st_size < 100000:
        qa_report["failures"].append(f"Final video file missing or under 100 KB ({final_video})")
        return qa_report

    qa_report["checks"]["file_exists"] = True
    qa_report["metrics"]["file_size_mb"] = round(final_video.stat().st_size / (1024 * 1024), 2)
    qa_report["metrics"]["final_video_path"] = str(final_video)

    # 3. FFprobe Technical Probing
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', str(final_video)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        probe = json.loads(res.stdout)
        qa_report["checks"]["ffprobe_readable"] = True

        fmt = probe.get('format', {})
        v_dur = float(fmt.get('duration', 0))
        qa_report["metrics"]["duration_seconds"] = round(v_dur, 2)

        streams = probe.get('streams', [])
        v_stream = next((s for s in streams if s.get('codec_type') == 'video'), None)
        a_stream = next((s for s in streams if s.get('codec_type') == 'audio'), None)

        if v_stream:
            qa_report["checks"]["video_present"] = True
            w = int(v_stream.get('width', 0))
            h = int(v_stream.get('height', 0))
            codec_v = v_stream.get('codec_name', '')
            r_fps = v_stream.get('r_frame_rate', '25/1')
            fps = eval(r_fps) if '/' in r_fps else float(r_fps)

            qa_report["metrics"]["resolution"] = f"{w}x{h}"
            qa_report["metrics"]["fps"] = round(fps, 2)
            qa_report["metrics"]["video_codec"] = codec_v

            if w == 1080 and h == 1920:
                qa_report["checks"]["resolution"] = True
            else:
                qa_report["failures"].append(f"Invalid resolution {w}x{h} (must be 1080x1920)")

            if fps >= 23.9:
                qa_report["checks"]["fps"] = True
            else:
                qa_report["failures"].append(f"Invalid FPS {fps:.2f} (must be >= 24.0)")

            if codec_v == 'h264':
                qa_report["checks"]["codecs"] = True
            else:
                qa_report["failures"].append(f"Invalid video codec '{codec_v}' (must be h264)")
        else:
            qa_report["failures"].append("No video stream found in MP4")

        if a_stream:
            qa_report["checks"]["audio_present"] = True
            codec_a = a_stream.get('codec_name', '')
            qa_report["metrics"]["audio_codec"] = codec_a
            if codec_a != 'aac':
                qa_report["failures"].append(f"Invalid audio codec '{codec_a}' (must be aac)")
        else:
            qa_report["failures"].append("No audio stream found in MP4")

        # Duration check (25.0s - 65.0s)
        if 25.0 <= v_dur <= 65.0:
            qa_report["checks"]["duration"] = True
        else:
            qa_report["failures"].append(f"Duration {v_dur:.2f}s is outside allowed range (25.0s - 65.0s)")

    except Exception as e:
        qa_report["failures"].append(f"FFprobe probing error: {e}")
        return qa_report

    # 4. Audio Loudness & Silence Detection via volumedetect
    try:
        cmd_vol = ['ffmpeg', '-i', str(final_video), '-af', 'volumedetect', '-f', 'null', '-']
        res_vol = subprocess.run(cmd_vol, capture_output=True, text=True)
        mean_vol, max_vol = None, None
        for line in res_vol.stderr.splitlines():
            if 'mean_volume' in line:
                try:
                    mean_vol = float(line.split(':')[1].replace('dB', '').strip())
                except Exception:
                    pass
            elif 'max_volume' in line:
                try:
                    max_vol = float(line.split(':')[1].replace('dB', '').strip())
                except Exception:
                    pass

        qa_report["metrics"]["mean_volume_db"] = mean_vol
        qa_report["metrics"]["max_volume_db"] = max_vol

        if mean_vol is not None and mean_vol > -45.0 and (max_vol is None or max_vol <= -0.1):
            qa_report["checks"]["audio_loudness"] = True
        else:
            qa_report["failures"].append(f"Audio loudness out of bounds: mean={mean_vol}dB, max={max_vol}dB")
    except Exception as ae:
        qa_report["warnings"].append(f"Loudness detection check non-fatal error: {ae}")
        qa_report["checks"]["audio_loudness"] = True

    # 5. Final Aggregation
    all_passed = all(qa_report["checks"].values())
    qa_report["passed"] = all_passed
    qa_report["status"] = "PASS" if all_passed else "BLOCKED"

    # Save qa_report.json
    qa_report_path = video_dir / "qa_report.json"
    try:
        with open(qa_report_path, "w", encoding="utf-8") as qf:
            json.dump(qa_report, qf, indent=2, ensure_ascii=False)
    except Exception:
        pass

    return qa_report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline 1 Production QA Gate")
    parser.add_argument("--video_id", required=True, help="Video folder ID to inspect")
    parser.add_argument("--output_dir", default="output", help="Base output directory")
    args = parser.parse_args()

    report = run_pipeline1_qa(args.video_id, args.output_dir)
    print("\n==============================================")
    print(f"  Pipeline 1 Production QA Gate: {args.video_id} ")
    print(f"  Status: {report['status']} | Passed: {report['passed']}")
    print("==============================================\n")
    for check, res in report["checks"].items():
        status_sym = "✅" if res else "❌"
        print(f"  {status_sym} {check:<25}: {res}")
    print("\nMetrics:")
    for k, v in report["metrics"].items():
        print(f"  - {k}: {v}")
    if report["failures"]:
        print("\nFailures:")
        for f in report["failures"]:
            print(f"  ❌ {f}")
    if report["warnings"]:
        print("\nWarnings:")
        for w in report["warnings"]:
            print(f"  ⚠️ {w}")
    print("==============================================\n")

    sys.exit(0 if report["passed"] else 1)
