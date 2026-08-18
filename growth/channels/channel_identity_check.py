# -*- coding: utf-8 -*-
"""
channel_identity_check.py
-------------------------
Verifies YouTube OAuth channel identity against expected channel configuration.
Enforces hard failure on channel mismatch.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

CHANNELS_DIR = Path(__file__).parent.parent.parent / "config" / "channels"


def load_channel_config(pipeline_name: str) -> Dict[str, Any]:
    """Loads non-secret channel configuration for a pipeline ('pipeline1' or 'pipeline2')."""
    cfg_file = CHANNELS_DIR / f"{pipeline_name}_channel.json"
    if not cfg_file.exists():
        raise FileNotFoundError(f"Channel configuration not found: {cfg_file}")
    with open(cfg_file, "r", encoding="utf-8") as f:
        return json.load(f)


def verify_channel_identity(
    pipeline_name: str,
    authenticated_channel_id: str,
    authenticated_channel_name: str,
    allow_placeholder: bool = True
) -> Dict[str, Any]:
    """
    Verifies that the authenticated YouTube channel matches expected channel configuration.
    Returns audit dictionary with verdict 'MATCH' or 'MISMATCH'.
    """
    cfg = load_channel_config(pipeline_name)
    expected_id = cfg.get("expected_youtube_channel_id", "")
    expected_name = cfg.get("channel_name", "")

    # In development/test mode with placeholders
    is_placeholder = expected_id.startswith("UC_CHANNEL_") and "PLACEHOLDER" in expected_id
    
    if is_placeholder and allow_placeholder:
        logging.info(f"[{pipeline_name}] Expected channel is placeholder ({expected_id}). Allowing authenticated channel: {authenticated_channel_name} ({authenticated_channel_id})")
        return {
            "pipeline": pipeline_name,
            "authenticated_channel_name": authenticated_channel_name,
            "authenticated_channel_id": authenticated_channel_id,
            "expected_channel_name": expected_name,
            "expected_channel_id": expected_id,
            "verdict": "MATCH",
            "is_placeholder": True
        }

    match = (authenticated_channel_id == expected_id)
    verdict = "MATCH" if match else "MISMATCH"

    if not match:
        logging.error(
            f"FATAL CHANNEL MISMATCH! Pipeline: '{pipeline_name}'. "
            f"Expected ID: '{expected_id}', Authenticated ID: '{authenticated_channel_id}'. "
            "Upload aborted immediately."
        )

    return {
        "pipeline": pipeline_name,
        "authenticated_channel_name": authenticated_channel_name,
        "authenticated_channel_id": authenticated_channel_id,
        "expected_channel_name": expected_name,
        "expected_channel_id": expected_id,
        "verdict": verdict,
        "is_placeholder": is_placeholder
    }


def enforce_channel_match(pipeline_name: str, authenticated_channel_id: str, authenticated_channel_name: str) -> None:
    """Raises RuntimeError if channel identity does not match expected configuration."""
    res = verify_channel_identity(pipeline_name, authenticated_channel_id, authenticated_channel_name, allow_placeholder=False)
    if res["verdict"] != "MATCH":
        raise RuntimeError(
            f"Channel Identity Mismatch for {pipeline_name}! "
            f"Expected: {res['expected_channel_id']} ({res['expected_channel_name']}), "
            f"Authenticated: {res['authenticated_channel_id']} ({res['authenticated_channel_name']})"
        )
