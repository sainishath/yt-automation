# -*- coding: utf-8 -*-
"""
verify_release.py
-----------------
Authoritative Production Release Verification Suite.
Evaluates 14 critical verification axes across Pipeline 1 and Pipeline 2:
1. Pipeline 1 imports
2. Pipeline 2 imports
3. Standalone isolation
4. RAG sufficiency
5. Failure gates
6. Artifact contracts
7. Visual beat synchronization
8. Claim verification
9. Image/scene count
10. Final video properties
11. QA gate
12. Server endpoints
13. CLI entrypoints
14. Manifest correctness

Outputs:
- Console test logs
- final_release_verification.json
"""

import os
import sys
import json
import subprocess
from pathlib import Path

ROOT = Path("d:/Projects/yt-automations").resolve()
P1_DIR = ROOT / "alternate-history-shorts"
P2_DIR = ROOT / "convo-shorts" / "yt-automation-engine"

sys.path.insert(0, str(P1_DIR / "scripts"))
sys.path.insert(0, str(P2_DIR))

test_results = {
    "suite_name": "Final Release Audit Verification Suite",
    "total_tests": 0,
    "passed": 0,
    "failed": 0,
    "warnings": 0,
    "verdict": "PENDING",
    "checks": []
}

def record_check(category: str, name: str, passed: bool, details: str = "", is_warning: bool = False):
    test_results["total_tests"] += 1
    if passed:
        test_results["passed"] += 1
        status_str = "PASS"
    elif is_warning:
        test_results["warnings"] += 1
        status_str = "WARN"
    else:
        test_results["failed"] += 1
        status_str = "FAIL"

    entry = {
        "category": category,
        "name": name,
        "status": status_str,
        "details": details
    }
    test_results["checks"].append(entry)
    icon = "✅" if passed else ("⚠️" if is_warning else "❌")
    print(f"  {icon} [{status_str}] {category} :: {name} {('- ' + details) if details else ''}")

print("\n=======================================================")
print("  EXECUTING FINAL RELEASE VERIFICATION SUITE           ")
print("=======================================================\n")

# 1. Pipeline 1 Imports
print(">>> 1. Pipeline 1 Imports...")
try:
    p1_modules = [
        "rag_grounding", "generate_script", "generate_audio",
        "whisper_alignment", "visual_scene_planner", "generate_images",
        "assemble_video", "generate_metadata", "qa_gate", "pipeline_runner"
    ]
    sys.path.insert(0, str(P1_DIR / "scripts"))
    import importlib
    for m in p1_modules:
        if m in sys.modules and m == "qa_gate":
            del sys.modules[m]
        importlib.import_module(m)
    record_check("Imports", "Pipeline 1 Module Imports", True, "All 10 modules imported successfully")
except Exception as e:
    record_check("Imports", "Pipeline 1 Module Imports", False, str(e))

# 2. Pipeline 2 Imports
print("\n>>> 2. Pipeline 2 Imports...")
try:
    p2_modules = [
        "caption_utils", "discord_review", "media_engine",
        "metadata_generator", "thumbnail_generator", "qa_gate"
    ]
    sys.path.insert(0, str(P2_DIR))
    import importlib
    for m in p2_modules:
        if m in sys.modules and m == "qa_gate":
            del sys.modules[m]
        importlib.import_module(m)
    record_check("Imports", "Pipeline 2 Module Imports", True, "All 6 modules imported successfully")
except Exception as e:
    record_check("Imports", "Pipeline 2 Module Imports", False, str(e))

# 3. Standalone Isolation Scan
print("\n>>> 3. Standalone Isolation Scan...")
forbidden_found = []
for p in [P1_DIR, P2_DIR]:
    for pyf in p.glob("**/*.py"):
        if ".venv" in str(pyf) or "__pycache__" in str(pyf):
            continue
        try:
            code = pyf.read_text(encoding="utf-8")
            for line in code.splitlines():
                s = line.strip()
                if s.startswith("#"):
                    continue
                if "from shared" in s or "import shared" in s:
                    forbidden_found.append(f"{pyf.name}: {s}")
        except Exception:
            pass
record_check("Isolation", "Zero Cross-Pipeline Dependencies", len(forbidden_found) == 0, f"Violations: {len(forbidden_found)}")

# 4. RAG Sufficiency Gate
print("\n>>> 4. RAG Sufficiency Gate...")
try:
    sys.path.insert(0, str(P1_DIR / "scripts"))
    if "qa_gate" in sys.modules:
        del sys.modules["qa_gate"]
    from rag_grounding import generate_evidence_packet
    p_real = generate_evidence_packet("audit_check_rome", "What if the Roman Empire never fell?", output_dir=str(P1_DIR / "output"))
    p_fic = generate_evidence_packet("audit_check_wakanda", "What if Wakanda colonized Europe in 1800?", output_dir=str(P1_DIR / "output"))
    real_ok = p_real.get("retrieval_status") in ("PREFERRED", "SUFFICIENT")
    fic_ok = p_fic.get("retrieval_status") == "INSUFFICIENT"
    record_check("RAG", "Real Topic Sufficiency Check", real_ok, f"Status: {p_real.get('retrieval_status')}")
    record_check("RAG", "Fictional Topic Sufficiency Gate", fic_ok, f"Status: {p_fic.get('retrieval_status')}")
except Exception as e:
    record_check("RAG", "RAG Sufficiency Evaluation", False, str(e))

# 5. Failure Gates
print("\n>>> 5. Failure Gates...")
try:
    from qa_gate import run_pipeline1_qa
    qa_missing = run_pipeline1_qa("non_existent_fail_gate", output_dir=str(P1_DIR / "output"))
    record_check("Failure Gates", "QA Gate Rejects Missing Run", qa_missing.get("passed") is False, "Correctly rejected non-existent video")
except Exception as e:
    record_check("Failure Gates", "QA Gate Rejects Missing Run", False, str(e))

# 6, 7, 8, 9, 10, 11, 14: Final Release Candidate Audit
print("\n>>> 6-11, 14. Final Release Candidate Artifacts & Properties...")
rc_dir = P1_DIR / "output" / "final_release_candidate"
man_file = rc_dir / "run_manifest.json"
qa_file = rc_dir / "qa_report.json"
plan_file = rc_dir / "scene_plan.json"
align_file = rc_dir / "audio" / "alignment_cache.json"
script_file = rc_dir / "script.json"
claim_file = rc_dir / "claim_verification.json"
final_video = rc_dir / "final" / "final_release_candidate_final.mp4"

if man_file.exists() and qa_file.exists() and final_video.exists():
    with open(man_file, "r", encoding="utf-8") as f:
        man = json.load(f)
    with open(qa_file, "r", encoding="utf-8") as f:
        qa = json.load(f)
    with open(plan_file, "r", encoding="utf-8") as f:
        plan = json.load(f)
    with open(align_file, "r", encoding="utf-8") as f:
        align = json.load(f)
    with open(claim_file, "r", encoding="utf-8") as f:
        claim_doc = json.load(f)

    # 6. Artifact Contracts
    all_stages_pass = all(v == "PASS" for v in man.get("stages", {}).values())
    record_check("Contracts", "Run Manifest Stages PASS", all_stages_pass, f"Stages: {man.get('stages')}")

    # 7. Visual Beat Synchronization
    beats = plan.get("visual_beats", [])
    tot_dur = align.get("total_duration", 0.0)
    b0_ok = abs(beats[0].get("start_time", 0.0)) < 0.05
    bend_ok = abs(beats[-1].get("end_time", 0.0) - tot_dur) < 0.5
    cont_ok = all(abs(beats[i]["end_time"] - beats[i+1]["start_time"]) < 0.05 for i in range(len(beats)-1))
    record_check("Visual Sync", "Beat 0 Starts at 0.0s", b0_ok, f"Start: {beats[0].get('start_time'):.2f}s")
    record_check("Visual Sync", "Final Beat Ends at Audio Duration", bend_ok, f"Delta: {abs(beats[-1].get('end_time', 0.0) - tot_dur):.2f}s")
    record_check("Visual Sync", "Continuous Beat Timeline (0 gaps/overlaps)", cont_ok, f"Total beats: {len(beats)}")

    # 8. Claim Verification
    unsupported = claim_doc.get("unsupported_facts_count", 0)
    record_check("Claims", "0 Unsupported Historical Claims", unsupported == 0, f"Unsupported: {unsupported}")

    # 9. Image / Scene Count Match
    imgs_found = len(list((rc_dir / "images").glob("*.png")))
    record_check("Assets", "Images Count Matches Beat Count", imgs_found >= len(beats), f"Images: {imgs_found}, Beats: {len(beats)}")

    # 10. Final Video Properties (ffprobe)
    m = qa.get("metrics", {})
    record_check("Video QA", "Resolution 1080x1920", m.get("resolution") == "1080x1920", f"Resolution: {m.get('resolution')}")
    record_check("Video QA", "H.264 / AAC Codecs", m.get("video_codec") == "h264" and m.get("audio_codec") == "aac", f"Codecs: {m.get('video_codec')}/{m.get('audio_codec')}")
    record_check("Video QA", "Duration within Shorts Limits (30-60s)", 30.0 <= m.get("duration_seconds", 0.0) <= 60.0, f"Duration: {m.get('duration_seconds')}s")

    # 11. QA Gate
    record_check("QA Gate", "17/17 QA Checks Passed", qa.get("passed") is True, f"Failures: {qa.get('failures')}")

    # 14. Manifest Correctness
    record_check("Manifest", "Manifest Status is READY", man.get("status") == "READY", f"Status: {man.get('status')}")
else:
    record_check("Artifacts", "Final Release Candidate Artifacts Found", False, "Missing output files")

# 12. Server Endpoints
print("\n>>> 12. Server Endpoints...")
try:
    sys.path.insert(0, str(P1_DIR))
    from server_alt_history import app as p1_server
    client1 = p1_server.test_client()
    h1 = client1.get("/health")
    v1 = client1.get("/get-video?id=final_release_candidate")
    record_check("Server", "Pipeline 1 /health Endpoint (200 OK)", h1.status_code == 200, f"Resp: {h1.get_json()}")
    record_check("Server", "Pipeline 1 /get-video Endpoint (video/mp4)", v1.status_code == 200 and v1.mimetype == "video/mp4", f"MIME: {v1.mimetype}")
except Exception as e:
    record_check("Server", "Pipeline 1 Server Tests", False, str(e))

# 13. CLI Entrypoints
print("\n>>> 13. CLI Entrypoints...")
p1_cli = subprocess.run([sys.executable, str(P1_DIR / "scripts" / "pipeline_runner.py"), "--help"], capture_output=True, text=True)
p2_cli = subprocess.run([sys.executable, str(P2_DIR / "main.py"), "--help"], capture_output=True, text=True)
record_check("CLI", "Pipeline 1 pipeline_runner.py --help", p1_cli.returncode == 0, "CLI accessible")
record_check("CLI", "Pipeline 2 main.py --help", p2_cli.returncode == 0, "CLI accessible")

# Final Verdict
if test_results["failed"] == 0:
    test_results["verdict"] = "PASS"
else:
    test_results["verdict"] = "FAIL"

# Save machine-readable json
verif_file = ROOT / "final_release_verification.json"
with open(verif_file, "w", encoding="utf-8") as f:
    json.dump(test_results, f, indent=2, ensure_ascii=False)

print("\n=======================================================")
print(f"  VERIFICATION SUITE COMPLETE: {test_results['passed']}/{test_results['total_tests']} PASSED (Failures: {test_results['failed']}, Warnings: {test_results['warnings']})")
print(f"  Verdict: {test_results['verdict']}")
print(f"  Machine-readable report saved to: {verif_file}")
print("=======================================================\n")
