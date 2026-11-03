# -*- coding: utf-8 -*-
"""
tests/test_review_gate.py
-------------------------
Unit tests verifying the Human-in-the-Loop (HITL) Review Staging Gate:
1. Directory staging in assemble_longform.py & short_splitter.py
2. Job discovery, packaging inspection, and formatted review checklist
3. State transitions:
   - PENDING_REVIEW -> APPROVED (with --privacy private or scheduled)
   - PENDING_REVIEW -> REJECTED_SCRAPPED (with permanent upload scrap lock)
4. Single-shot re-roll logic (updates target shot without re-rendering other shots)
5. Default private upload and approval enforcement in upload_video.py
"""

import os
import sys
import json
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from longform_engine.review_gate import (
    list_pending_jobs,
    get_job_details,
    approve_and_schedule,
    reroll_single_shot,
    reject_and_scrap,
    CHECKLIST_ITEMS,
    get_staging_paths,
)
from longform_engine.assemble_longform import generate_thumbnail
from longform_engine.short_splitter import split_master_into_shorts


@pytest.fixture
def temp_staging(tmp_path):
    """Creates an isolated pending_review / approved / scrapped directory tree."""
    pending_dir = tmp_path / "pending_review"
    approved_dir = tmp_path / "approved"
    scrapped_dir = tmp_path / "scrapped"
    pending_dir.mkdir(parents=True, exist_ok=True)
    approved_dir.mkdir(parents=True, exist_ok=True)
    scrapped_dir.mkdir(parents=True, exist_ok=True)
    return tmp_path, pending_dir, approved_dir, scrapped_dir


@pytest.fixture
def mock_job(temp_staging):
    """Creates a realistic staged documentary job in pending_review/."""
    tmp_path, pending_dir, _, _ = temp_staging
    job_id = "test_doc_1453"
    job_dir = pending_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # 1. Master video
    master_video = job_dir / "master_video.mp4"
    master_video.write_bytes(b"FAKE_MP4_MASTER_CONTENT_BYTES")

    # 2. Thumbnail
    thumbnail = job_dir / "thumbnail.png"
    thumbnail.write_bytes(b"FAKE_PNG_THUMBNAIL_BYTES")

    # 3. Draft script
    draft_file = tmp_path / "test_draft_80shots.json"
    draft_data = {
        "video_id": job_id,
        "video_title": "The Fall of Constantinople Test",
        "total_word_count": 1420,
        "acts": [
            {
                "act_number": 1,
                "title": "Act 1: The Gathering Storm",
                "script": "The massive walls stood tall.",
                "shots": [
                    {
                        "shot_id": "act01_shot01",
                        "prompt": "Cinematic wide shot of Constantinople walls",
                        "narration": "The massive walls stood tall.",
                        "motion": "push_in",
                    },
                    {
                        "shot_id": "act01_shot02",
                        "prompt": "Close up of Ottoman war tent",
                        "narration": "Inside the tent, plans were drawn.",
                        "motion": "pan_right",
                    },
                ],
            }
        ],
        "derived_shorts": [
            {
                "short_id": "test_short_01",
                "title": "The 27-Foot Cannon",
                "start_sec": 0.0,
                "duration_sec": 45.0,
                "hook_script": "Did you know a cannon broke these walls?",
            }
        ],
    }
    with open(draft_file, "w", encoding="utf-8") as df:
        json.dump(draft_data, df, indent=2)

    # 4. Metadata JSON
    metadata = {
        "video_id": job_id,
        "title": "The Fall of Constantinople Test",
        "runtime": 533.6,
        "duration_sec": 533.6,
        "word_count": 1420,
        "scheduled_publish_slot": "2026-11-04T07:30:00Z",
        "publish_at_iso": "2026-11-04T07:30:00Z",
        "status": "PENDING_REVIEW",
        "description": "Historical documentary description test.\n\n#History",
        "tags": ["History", "Constantinople", "Documentary"],
        "timestamps": [{"start_sec": 0.0, "title": "Intro"}],
        "master_video": "master_video.mp4",
        "thumbnail": "thumbnail.png",
        "draft_path": str(draft_file),
    }
    with open(job_dir / "metadata.json", "w", encoding="utf-8") as mf:
        json.dump(metadata, mf, indent=2)

    # 5. Shorts directory with 5 mock shorts
    shorts_dir = job_dir / "shorts"
    shorts_dir.mkdir(parents=True, exist_ok=True)
    for i in range(1, 6):
        s_mp4 = shorts_dir / f"w1_short_{i:02d}.mp4"
        s_mp4.write_bytes(b"FAKE_SHORT_MP4_CONTENT")
        s_meta = shorts_dir / f"w1_short_{i:02d}_meta.json"
        with open(s_meta, "w", encoding="utf-8") as sm:
            json.dump({"short_id": f"w1_short_{i:02d}", "title": f"Short {i}"}, sm)

    # 6. Temp dir with mock clip cache
    temp_dir = job_dir / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    images_dir = temp_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    (images_dir / "act01_shot01.png").write_bytes(b"OLD_IMAGE_BYTES")
    (temp_dir / "clip_act01_shot01_synced.mp4").write_bytes(b"OLD_CLIP_BYTES")
    (temp_dir / "clip_act01_shot02_synced.mp4").write_bytes(b"UNTOUCHED_CLIP_BYTES")

    return tmp_path, job_id, job_dir


# ── Test Suite ────────────────────────────────────────────────────────────────

def test_job_listing_and_formatted_checklist(mock_job):
    """Verifies pending jobs are discovered with runtime, word count, and checklist."""
    tmp_path, job_id, job_dir = mock_job

    jobs = list_pending_jobs(base_dir=tmp_path)
    assert len(jobs) == 1
    j = jobs[0]
    assert j["job_id"] == job_id
    assert j["title"] == "The Fall of Constantinople Test"
    assert j["runtime"] == 533.6
    assert j["word_count"] == 1420
    assert j["shorts_count"] == 5
    assert j["has_master"] is True
    assert j["has_thumbnail"] is True
    assert j["status"] == "PENDING_REVIEW"

    details = get_job_details(job_id, base_dir=tmp_path)
    assert details["job_id"] == job_id
    assert len(details["checklist"]) == 4
    for item in CHECKLIST_ITEMS:
        assert item in details["checklist"]
        assert item in details["formatted_checklist"]


def test_approve_and_schedule_state_transition(mock_job):
    """Verifies PENDING_REVIEW -> APPROVED moves files and updates metadata."""
    tmp_path, job_id, job_dir = mock_job
    pending_dir, approved_dir, _ = get_staging_paths(tmp_path)

    # Execute approve_and_schedule without triggering live upload
    res = approve_and_schedule(
        job_id=job_id,
        privacy="scheduled",
        base_dir=tmp_path,
        run_upload=False,
        publish_at_iso="2026-11-04T07:30:00Z"
    )

    assert res["status"] == "APPROVED"
    assert res["privacy"] == "scheduled"

    # Verify folder moved out of pending_review
    assert not (pending_dir / job_id).exists()
    assert (approved_dir / job_id).exists()

    # Verify all artifacts preserved in approved/
    approved_job = approved_dir / job_id
    assert (approved_job / "master_video.mp4").exists()
    assert (approved_job / "thumbnail.png").exists()
    assert len(list((approved_job / "shorts").glob("*.mp4"))) == 5

    # Verify metadata status transition
    meta_path = approved_job / "metadata.json"
    with open(meta_path, "r", encoding="utf-8") as mf:
        updated_meta = json.load(mf)
    assert updated_meta["status"] == "APPROVED"
    assert updated_meta["approved_privacy"] == "scheduled"
    assert "approved_at" in updated_meta

    # Verify run_manifest.json approval
    manifest_path = approved_job / "run_manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as mf:
        manifest = json.load(mf)
    assert manifest["status"] == "APPROVED"
    assert manifest["reviewed_by"] == "HUMAN_OPERATOR"


def test_reject_and_scrap_state_transition(mock_job):
    """Verifies PENDING_REVIEW -> REJECTED_SCRAPPED moves files and locks upload."""
    tmp_path, job_id, job_dir = mock_job
    pending_dir, _, scrapped_dir = get_staging_paths(tmp_path)

    res = reject_and_scrap(
        job_id=job_id,
        reason="Deformed anatomical hands in scene 3 and historical inaccuracy.",
        base_dir=tmp_path,
    )

    assert res["status"] == "REJECTED_SCRAPPED"
    assert "Deformed anatomical hands" in res["reason"]

    # Verify folder moved out of pending_review and into scrapped/
    assert not (pending_dir / job_id).exists()
    scrapped_job = scrapped_dir / job_id
    assert scrapped_job.exists()

    # Verify metadata status
    with open(scrapped_job / "metadata.json", "r", encoding="utf-8") as mf:
        updated_meta = json.load(mf)
    assert updated_meta["status"] == "REJECTED_SCRAPPED"
    assert updated_meta["rejection_reason"] == res["reason"]
    assert "rejected_at" in updated_meta

    # Verify run_manifest.json scrap lock
    with open(scrapped_job / "run_manifest.json", "r", encoding="utf-8") as mf:
        manifest = json.load(mf)
    assert manifest["status"] == "REJECTED_SCRAPPED"
    assert manifest["lock"] == "PERMANENT_SCRAP_LOCK"


def test_single_shot_reroll_logic(mock_job):
    """
    Verifies that reroll_single_shot re-renders ONLY the specified shot
    (e.g. act01_shot01) while leaving other shots (act01_shot02) untouched.
    """
    tmp_path, job_id, job_dir = mock_job
    temp_dir = job_dir / "temp"
    untouched_clip = temp_dir / "clip_act01_shot02_synced.mp4"
    untouched_mtime_before = untouched_clip.stat().st_mtime

    with patch("longform_engine.assemble_longform.generate_16x9_visual") as mock_gen_img, \
         patch("longform_engine.assemble_longform.render_cinematic_shot") as mock_render_shot, \
         patch("subprocess.run") as mock_subproc:

        # Mock image generation creating new image bytes
        def fake_gen(prompt, negative_prompt, output_path, **kwargs):
            Path(output_path).write_bytes(b"NEW_RE_ROLLED_IMAGE_BYTES")
        mock_gen_img.side_effect = fake_gen

        # Mock ffmpeg subprocesses
        mock_subproc.return_value = MagicMock(returncode=0)

        res = reroll_single_shot(
            job_id=job_id,
            shot_id="act01_shot01",
            base_dir=tmp_path,
            allow_proxies=True,
        )

        assert res["status"] == "REROLLED"
        assert res["shot_id"] == "act01_shot01"

        # Verify image generator was called for act01_shot01 prompt
        mock_gen_img.assert_called_once()
        called_prompt = mock_gen_img.call_args[1]["prompt"]
        assert "Constantinople walls" in called_prompt

        # Verify image was replaced
        new_img = temp_dir / "images" / "act01_shot01.png"
        assert new_img.read_bytes() == b"NEW_RE_ROLLED_IMAGE_BYTES"

        # Verify other shot was NOT touched
        assert untouched_clip.stat().st_mtime == untouched_mtime_before
        assert untouched_clip.read_bytes() == b"UNTOUCHED_CLIP_BYTES"

        # Verify reroll audit trail in metadata.json
        with open(job_dir / "metadata.json", "r", encoding="utf-8") as mf:
            meta = json.load(mf)
        assert len(meta.get("rerolls", [])) == 1
        assert meta["rerolls"][0]["shot_id"] == "act01_shot01"


def get_upload_video_module():
    """Dynamically loads alternate-history-shorts/scripts/upload_video.py."""
    import importlib.util
    upload_script = _ROOT / "alternate-history-shorts" / "scripts" / "upload_video.py"
    spec = importlib.util.spec_from_file_location("upload_video", str(upload_script))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_upload_video_default_privacy_is_private():
    """Verifies upload_video.py enforces default privacy='private'."""
    upload_mod = get_upload_video_module()
    upload_video = upload_mod.upload_video
    import inspect

    # Inspect function default argument
    sig = inspect.signature(upload_video)
    assert sig.parameters["privacy"].default == "private"


def test_upload_video_blocks_scrapped_and_unapproved(tmp_path):
    """
    Verifies upload_video strictly forbids:
    1. Uploading permanently scrapped videos.
    2. Uploading public videos without explicit human review approval.
    """
    upload_mod = get_upload_video_module()
    upload_video = upload_mod.upload_video

    test_video_dir = tmp_path / "test_scrapped_video"
    test_video_dir.mkdir(parents=True, exist_ok=True)
    fake_mp4 = test_video_dir / "master_video.mp4"
    fake_mp4.write_bytes(b"FAKE_VIDEO")

    # 1. Scrapped video test
    manifest_file = test_video_dir / "run_manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as mf:
        json.dump({"status": "REJECTED_SCRAPPED"}, mf)

    with pytest.raises(RuntimeError) as exc_info:
        upload_video(video_id="test_scrapped_video", output_dir=str(tmp_path), privacy="private")
    assert "CANNOT_UPLOAD_SCRAPPED_VIDEO" in str(exc_info.value)

    # 2. Unapproved video public upload test
    test_unapproved_dir = tmp_path / "test_unapproved_video"
    test_unapproved_dir.mkdir(parents=True, exist_ok=True)
    fake_mp4_2 = test_unapproved_dir / "master_video.mp4"
    fake_mp4_2.write_bytes(b"FAKE_VIDEO_2")
    meta_file = test_unapproved_dir / "metadata.json"
    with open(meta_file, "w", encoding="utf-8") as mf:
        json.dump({"status": "PENDING_REVIEW"}, mf)

    with pytest.raises(PermissionError) as exc_info:
        upload_video(video_id="test_unapproved_video", output_dir=str(tmp_path), privacy="public")
    assert "HUMAN_REVIEW_GATE_REQUIRED" in str(exc_info.value)


def test_thumbnail_generation_fallback(tmp_path):
    """Verifies generate_thumbnail creates valid thumbnail from video or fallback image."""
    thumb_out = tmp_path / "thumbnail.png"
    fallback_img = tmp_path / "fallback.png"

    from PIL import Image
    im = Image.new("RGB", (1920, 1080), color=(10, 20, 30))
    im.save(str(fallback_img))

    result = generate_thumbnail(
        video_path=tmp_path / "nonexistent.mp4",
        output_thumbnail=thumb_out,
        fallback_image=fallback_img,
    )
    assert result.exists()
    assert result.stat().st_size > 500


def test_short_splitter_default_output_dir(tmp_path):
    """Verifies split_master_into_shorts defaults to master_path.parent / 'shorts'."""
    master_file = tmp_path / "master_video.mp4"
    master_file.write_bytes(b"FAKE_MASTER")

    with patch("longform_engine.short_splitter.extract_act_slice") as mock_slice, \
         patch("longform_engine.short_splitter.generate_safe_short_ass") as mock_ass:
        mock_slice.return_value = tmp_path / "shorts" / "short_01.mp4"

        manifest_file = tmp_path / "manifest.json"
        manifest_data = {
            "title": "Test Title",
            "derived_shorts": [
                {
                    "short_id": "w1_short_01",
                    "title": "Short 1",
                    "source_act": 1,
                    "start_sec": 0.0,
                    "duration_sec": 45.0,
                    "hook_script": "Hook text",
                }
            ],
        }
        with open(manifest_file, "w", encoding="utf-8") as mf:
            json.dump(manifest_data, mf)

        results = split_master_into_shorts(master_video_path=master_file, manifest_path=manifest_file)
        assert len(results) == 1
        expected_shorts_dir = tmp_path / "shorts"
        assert (expected_shorts_dir / "w1_short_01_metadata.json").exists()
