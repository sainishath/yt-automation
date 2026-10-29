# -*- coding: utf-8 -*-
"""
pipeline/upload_guard.py
------------------------
Module C: Compliant Upload, Synthetic Disclosure, RAG Source Attribution & Env-Var Alerting.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
import requests


def send_discord_alert(message: str, is_error: bool = False) -> None:
    """Replaces hardcoded webhook URL with environment variables for review vs. error alerting."""
    env_key = "DISCORD_ERROR_WEBHOOK_URL" if is_error else "DISCORD_REVIEW_WEBHOOK_URL"
    webhook_url = os.environ.get(env_key)
    if not webhook_url:
        # Fallback to channel-specific env var if DISCORD_REVIEW_WEBHOOK_URL not explicitly set
        if not is_error:
            webhook_url = os.environ.get("DISCORD_WEBHOOK_URL_P1") or os.environ.get("DISCORD_WEBHOOK_CHANNEL_A")
        else:
            webhook_url = os.environ.get("DISCORD_ERROR_WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError(f"Missing required environment variable: {env_key}")
    requests.post(webhook_url, json={"content": message}, timeout=10).raise_for_status()


def format_rag_citations_footer(evidence_packet: Optional[Dict[str, Any]]) -> str:
    """Formats verified RAG sources into a YouTube description citation block."""
    if not evidence_packet or not isinstance(evidence_packet, dict):
        return ""
    sources = evidence_packet.get("sources", [])
    if not sources or not isinstance(sources, list):
        return ""
    lines = ["Historical Sources & References (RAG Verified):"]
    for src in sources[:4]:
        if isinstance(src, dict):
            title = src.get("title", "Historical Source").strip()
            publisher = src.get("publisher", "").strip()
            url = src.get("url", "").strip()
            citation = f"- {title}"
            if publisher:
                citation += f" ({publisher})"
            if url and not url.startswith("local://"):
                citation += f": {url}"
            lines.append(citation)
    return "\n".join(lines) if len(lines) > 1 else ""


def append_rag_citations_to_description(
    description: str, evidence_packet: Optional[Dict[str, Any]] = None
) -> str:
    """Auto-appends RAG citations and mandatory synthetic media disclosure to video descriptions."""
    desc = (description or "").strip()
    citations_block = format_rag_citations_footer(evidence_packet)
    if citations_block and "Historical Sources & References" not in desc:
        desc = f"{desc}\n\n{citations_block}".strip()
    synthetic_note = "[Altered or Synthetic Content: This video contains AI-generated visual and audio content.]"
    if synthetic_note not in desc:
        desc = f"{desc}\n\n{synthetic_note}".strip()
    return desc


def build_youtube_insert_body(
    title: str,
    description: str,
    tags: List[str],
    category_id: str = "27",
    publish_at_iso: str | None = None,
    evidence_packet: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Constructs YouTube Data API v3 videos.insert payload with mandatory synthetic media disclosure."""
    final_description = (
        append_rag_citations_to_description(description, evidence_packet)
        if evidence_packet is not None
        else description
    )
    status_block: Dict[str, Any] = {
        "privacyStatus": "private" if publish_at_iso else "public",
        "selfDeclaredMadeForKids": False,
        "containsSyntheticMedia": True,  # Mandatory YouTube disclosure for realistic AI voice/visuals
    }
    if publish_at_iso:
        status_block["publishAt"] = publish_at_iso
    return {
        "snippet": {
            "title": title[:100],
            "description": final_description,
            "tags": tags[:15],
            "categoryId": str(category_id),  # 27 = Education (higher RPM than 24 = Entertainment)
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": status_block,
    }
