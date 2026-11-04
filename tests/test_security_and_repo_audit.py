# -*- coding: utf-8 -*-
"""
tests/test_security_and_repo_audit.py
-------------------------------------
Automated Security, Code Quality, Path Traversal, Secret Hygiene, and Upload Gate Audit Tests.
"""

import ast
import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent


def _get_tracked_files():
    res = subprocess.run(
        ["git", "ls-files"],
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
        check=True,
    )
    return [ROOT_DIR / line.strip() for line in res.stdout.splitlines() if line.strip()]


def test_all_tracked_python_files_parse_cleanly_without_bom():
    """Every tracked Python file must parse cleanly via ast.parse and have no UTF-8 BOM."""
    py_files = [p for p in _get_tracked_files() if p.suffix == ".py" and p.exists()]
    assert len(py_files) > 50, "Expected at least 50 tracked Python files"

    bom_files = []
    syntax_errors = []
    for pf in py_files:
        raw = pf.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            bom_files.append(str(pf.relative_to(ROOT_DIR)))
        try:
            ast.parse(raw.decode("utf-8"), filename=str(pf))
        except SyntaxError as exc:
            syntax_errors.append(f"{pf.relative_to(ROOT_DIR)}: {exc}")

    assert not bom_files, f"Files contain UTF-8 BOM (U+FEFF): {bom_files}"
    assert not syntax_errors, f"Syntax errors found: {syntax_errors}"


def test_no_unsafe_pickle_deserialization_or_eval():
    """No tracked production Python file may call pickle.load() or eval() (CWE-502 / CWE-95)."""
    py_files = [
        p for p in _get_tracked_files()
        if p.suffix == ".py" and p.exists() and "tests" not in p.parts
    ]
    violations = []
    for pf in py_files:
        tree = ast.parse(pf.read_text(encoding="utf-8"), filename=str(pf))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
                    violations.append(f"{pf.relative_to(ROOT_DIR)}:{node.lineno} calls {node.func.id}()")
                elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                    call_name = f"{node.func.value.id}.{node.func.attr}"
                    if call_name in ("pickle.load", "pickle.loads", "marshal.load", "marshal.loads"):
                        violations.append(f"{pf.relative_to(ROOT_DIR)}:{node.lineno} calls {call_name}()")

    assert not violations, f"Unsafe deserialization or code execution found: {violations}"


def test_no_hardcoded_secrets_in_tracked_files():
    """Verifies zero API keys, OAuth secrets, or live Discord webhook tokens in git-tracked files."""
    secret_patterns = [
        ("Google API Key", re.compile(r"AIzaSy[0-9A-Za-z_-]{33}")),
        ("Google OAuth Secret", re.compile(r"GOCSPX-[0-9A-Za-z_-]{20,}")),
        ("OpenAI Key", re.compile(r"sk-(?:proj-)?[0-9A-Za-z]{32,}")),
        ("GitHub Token", re.compile(r"gh[pousr]_[0-9A-Za-z]{30,}")),
        ("Private Key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
        ("Discord Webhook", re.compile(r"https://(?:ptb\.|canary\.)?discord(?:app)?\.com/api/webhooks/[0-9]{17,20}/[A-Za-z0-9_-]{50,}")),
    ]

    leaks = []
    for fpath in _get_tracked_files():
        if not fpath.exists() or fpath.suffix in (".png", ".jpg", ".jpeg", ".xlsx", ".pdf"):
            continue
        text = fpath.read_text(encoding="utf-8", errors="ignore")
        for label, pat in secret_patterns:
            for match in pat.finditer(text):
                val = match.group(0)
                if "YOUR_" in val or "EXAMPLE" in val or "xxxx" in val.lower():
                    continue
                leaks.append(f"{fpath.relative_to(ROOT_DIR)}: {label}")

    assert not leaks, f"Hardcoded secrets found in tracked files: {leaks}"


def test_sensitive_files_are_git_ignored():
    """Ensures .env, token.json, client_secrets.json, and .db/.backup files are ignored by git."""
    tracked_rel = {str(p.relative_to(ROOT_DIR)).replace("\\", "/") for p in _get_tracked_files()}
    forbidden_patterns = [
        ".env",
        "alternate-history-shorts/config/token.json",
        "alternate-history-shorts/config/client_secrets.json",
        "growth/db/growth.db",
        "growth/db/growth.db.backup_phase29",
    ]
    for fp in forbidden_patterns:
        assert fp not in tracked_rel, f"Sensitive or runtime database file '{fp}' must not be tracked in git!"


def test_review_gate_path_traversal_protection(tmp_path):
    """Verifies review_gate functions reject path traversal payloads with ValueError."""
    from longform_engine.review_gate import (
        _validate_safe_id,
        get_job_details,
        approve_and_schedule,
        reroll_single_shot,
        reject_and_scrap,
    )

    malicious_ids = ["../etc", "..\\windows", "job/../../secret", "job;rm -rf", "", "   "]
    for bad_id in malicious_ids:
        with pytest.raises(ValueError):
            _validate_safe_id(bad_id)
        with pytest.raises(ValueError):
            get_job_details(bad_id, base_dir=tmp_path)
        with pytest.raises(ValueError):
            approve_and_schedule(bad_id, base_dir=tmp_path, run_upload=False)
        with pytest.raises(ValueError):
            reject_and_scrap(bad_id, base_dir=tmp_path)
        with pytest.raises(ValueError):
            reroll_single_shot("valid_job", bad_id, base_dir=tmp_path)


def test_local_servers_hardened_auth_and_cors():
    """Verifies constant-time API key comparison and non-wildcard CORS in local servers."""
    growth_srv = (ROOT_DIR / "growth" / "server.py").read_text(encoding="utf-8")
    alt_srv = (ROOT_DIR / "alternate-history-shorts" / "server_alt_history.py").read_text(encoding="utf-8")

    assert "hmac.compare_digest" in growth_srv, "growth/server.py must use hmac.compare_digest"
    assert "hmac.compare_digest" in alt_srv, "server_alt_history.py must use hmac.compare_digest"
    assert '"Access-Control-Allow-Origin", "*"' not in growth_srv, "growth/server.py must not use wildcard CORS"
    assert 'data.get("privacy", "private")' in alt_srv, "/upload-youtube must default to private privacy"


def test_week2_longform_locked_and_upload_blocked(tmp_path):
    """Verifies Week 2 Longform is locked in PENDING_REVIEW and upload_single_video blocks pending_review uploads."""
    from longform_engine.uploader import upload_single_video

    # 1. Verify simulated pending_review file is blocked by upload_single_video
    pending_job_dir = tmp_path / "pending_review" / "test_job"
    pending_job_dir.mkdir(parents=True)
    dummy_mp4 = pending_job_dir / "master_video.mp4"
    dummy_mp4.write_bytes(b"\x00" * 1024)
    (pending_job_dir / "metadata.json").write_text(
        json.dumps({"status": "PENDING_REVIEW"}), encoding="utf-8"
    )

    with pytest.raises(PermissionError, match="HUMAN_REVIEW_GATE_REQUIRED"):
        upload_single_video(
            video_path=dummy_mp4,
            title="Test Video",
            description="Test Description",
            tags=["Test"],
            privacy="private",
        )

    # 2. If bronze_age_collapse_1177bc exists on disk, verify it is strictly locked in PENDING_REVIEW
    w2_meta = ROOT_DIR / "longform_engine" / "output" / "pending_review" / "bronze_age_collapse_1177bc" / "metadata.json"
    if w2_meta.exists():
        meta_data = json.loads(w2_meta.read_text(encoding="utf-8"))
        assert meta_data.get("status") == "PENDING_REVIEW"
        assert meta_data.get("youtube_video_id") is None
