# -*- coding: utf-8 -*-
"""
raw_validator.py
----------------
Strict validator for human/Gemini-researched tabular datasets.
Maps raw column aliases, verifies YouTube URLs/IDs, numeric values, and transcript integrity.
Quarantines malformed records and enforces public data boundaries (zero private analytics).
"""

import re
import math
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from growth.external_intelligence.ingestion.ingestion_schemas import (
    TranscriptStatus,
    PerformanceClass,
    ValidatedExternalVideoRecord
)

# Allowed header aliases mapping to canonical field names
COLUMN_ALIASES = {
    # Channel Name
    "channel_name": "channel_name",
    "channel": "channel_name",
    "channel_title": "channel_name",
    "creator": "channel_name",

    # Channel URL / Handle
    "channel_url": "channel_url",
    "channel_link": "channel_url",
    "handle": "channel_url",
    "channel_handle": "channel_url",

    # Public Subscribers
    "public_subscriber_count": "public_subscriber_count",
    "subscribers": "public_subscriber_count",
    "subs": "public_subscriber_count",
    "subscriber_count": "public_subscriber_count",
    "public_subs": "public_subscriber_count",

    # Video Title
    "video_title": "video_title",
    "title": "video_title",
    "short_title": "video_title",

    # YouTube URL
    "youtube_url": "youtube_url",
    "url": "youtube_url",
    "video_url": "youtube_url",
    "link": "youtube_url",

    # Video ID
    "video_id": "video_id",
    "youtube_video_id": "video_id",
    "yt_id": "video_id",
    "id": "video_id",

    # Published Date
    "published_at": "published_at",
    "publish_date": "published_at",
    "published_date": "published_at",
    "upload_date": "published_at",
    "date": "published_at",

    # Duration
    "duration_seconds": "duration_seconds",
    "duration": "duration_seconds",
    "duration_sec": "duration_seconds",
    "length": "duration_seconds",
    "length_seconds": "duration_seconds",

    # Public Views
    "views": "views",
    "public_views": "views",
    "view_count": "views",
    "total_views": "views",

    # Public Likes
    "likes": "likes",
    "public_likes": "likes",
    "like_count": "likes",

    # Public Comments
    "comments": "comments",
    "public_comments": "comments",
    "comment_count": "comments",

    # Transcript Status
    "transcript_status": "transcript_status",
    "caption_status": "transcript_status",
    "transcript_type": "transcript_status",

    # Transcript Text
    "transcript": "transcript",
    "transcript_text": "transcript",
    "captions": "transcript",
    "text": "transcript",

    # Performance Class
    "performance_class": "performance_class",
    "performance_tier": "performance_class",
    "performance": "performance_class",
    "class": "performance_class",

    # Relative Performance (Claimed by researcher)
    "relative_performance": "relative_performance",
    "relative_views": "relative_performance",
    "view_multiplier": "relative_performance",
    "multiplier": "relative_performance",

    # Selection Reason
    "selection_reason": "selection_reason",
    "reason": "selection_reason",
    "notes": "selection_reason",

    # Uncertainties
    "uncertainties": "uncertainties",
    "uncertainty": "uncertainties",
    "caveats": "uncertainties"
}

# Forbidden private YouTube analytics headers
FORBIDDEN_PRIVATE_COLUMNS = {
    "retention", "avg_percentage_viewed", "apv", "ctr", "click_through_rate",
    "swipe_away", "swipe_away_rate", "impressions", "subscribers_gained",
    "traffic_source", "traffic_sources", "rpm", "cpm", "revenue"
}

YOUTUBE_URL_REGEX = re.compile(
    r"(?:https?://)?(?:www\.|m\.)?(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)([a-zA-Z0-9_-]{11})(?:[?&#/].*|$)"
)


def extract_video_id(url_or_id: str) -> Optional[str]:
    """Extracts clean 11-character YouTube video ID from URL or bare ID."""
    if not url_or_id:
        return None
    val = str(url_or_id).strip()
    if re.match(r"^[a-zA-Z0-9_-]{11}$", val):
        return val
    match = YOUTUBE_URL_REGEX.search(val)
    if match:
        return match.group(1)
    return None


def normalize_row_keys(row: Dict[str, Any]) -> Dict[str, Any]:
    """Resolves header aliases to canonical names while flagging forbidden fields."""
    normalized = {}
    for raw_k, v in row.items():
        if not raw_k:
            continue
        clean_k = str(raw_k).strip().lower().replace(" ", "_").replace("-", "_")
        if clean_k in FORBIDDEN_PRIVATE_COLUMNS:
            # We record a flag to drop or reject private metric fabrication
            normalized["_has_forbidden_private_metric"] = clean_k
            continue
        canonical_k = COLUMN_ALIASES.get(clean_k, clean_k)
        normalized[canonical_k] = v
    return normalized


def parse_int_or_none(val: Any) -> Optional[int]:
    """Safely converts string or number to integer, returning None if missing or invalid."""
    if val is None or str(val).strip() == "" or str(val).lower() in ("null", "none", "nan", "unavailable", "n/a"):
        return None
    try:
        if isinstance(val, (int, float)):
            if math.isnan(val):
                return None
            return int(val)
        cleaned = re.sub(r"[^\d]", "", str(val))
        return int(cleaned) if cleaned else None
    except Exception:
        return None


def parse_float_or_none(val: Any) -> Optional[float]:
    """Safely converts string or number to float."""
    if val is None or str(val).strip() == "" or str(val).lower() in ("null", "none", "nan", "unavailable", "n/a"):
        return None
    try:
        if isinstance(val, (int, float)):
            if math.isnan(val):
                return None
            return float(val)
        cleaned = str(val).replace(",", "").strip()
        match = re.search(r"[-+]?\d*\.?\d+", cleaned)
        return float(match.group(0)) if match else None
    except Exception:
        return None


def validate_record(
    row_index: int,
    raw_row: Dict[str, Any],
    dataset_id: str
) -> ValidatedExternalVideoRecord:
    """
    Validates a single raw row against strict research ingestion rules.
    Returns ValidatedExternalVideoRecord with is_valid status and detailed validation_errors.
    """
    row = normalize_row_keys(raw_row)
    errors: List[str] = []

    if "_has_forbidden_private_metric" in row:
        errors.append(f"Forbidden private metric detected: '{row['_has_forbidden_private_metric']}' (Fabricated Analytics Prohibited)")

    # 1. Video Title
    title = str(row.get("video_title") or "").strip()
    if not title:
        errors.append("Missing required field: 'video_title'")

    # 2. YouTube URL and Video ID
    raw_url = str(row.get("youtube_url") or "").strip()
    raw_vid_id = str(row.get("video_id") or "").strip()
    vid_id = extract_video_id(raw_vid_id) or extract_video_id(raw_url)

    if not vid_id:
        errors.append("Invalid or missing YouTube Video ID (must be valid 11-char ID or YouTube URL)")
    else:
        if not raw_url:
            raw_url = f"https://www.youtube.com/shorts/{vid_id}"

    # 3. Channel Name and URL
    channel_name = str(row.get("channel_name") or "").strip()
    if not channel_name:
        errors.append("Missing required field: 'channel_name'")

    channel_url = str(row.get("channel_url") or "").strip()
    if not channel_url:
        # Fallback to handle format if channel name provided
        clean_handle = re.sub(r"[^a-zA-Z0-9_]", "", channel_name)
        channel_url = f"https://www.youtube.com/@{clean_handle}"

    # 4. Public Metrics
    views_val = parse_int_or_none(row.get("views"))
    if views_val is None or views_val < 0:
        errors.append("Missing or invalid required public numeric field: 'views'")
        views = 0
    else:
        views = views_val

    likes = parse_int_or_none(row.get("likes"))
    comments = parse_int_or_none(row.get("comments"))
    subs = parse_int_or_none(row.get("public_subscriber_count"))

    # 5. Duration
    duration_val = parse_float_or_none(row.get("duration_seconds"))
    if duration_val is None or duration_val <= 0:
        # Default fallback for Short if unspecified
        duration = 45.0
    else:
        duration = round(duration_val, 1)

    # 6. Transcript Status and Content
    raw_status = str(row.get("transcript_status") or "").strip().upper()
    transcript_text = str(row.get("transcript") or "").strip() or None

    if raw_status in ("OFFICIAL_CAPTIONS", "OFFICIAL", "CAPTIONS"):
        transcript_status = TranscriptStatus.OFFICIAL_CAPTIONS
    elif raw_status in ("AUTO_GENERATED", "AUTO", "AUTOMATIC"):
        transcript_status = TranscriptStatus.AUTO_GENERATED
    elif raw_status in ("CREATOR_PROVIDED", "CREATOR", "MANUAL"):
        transcript_status = TranscriptStatus.CREATOR_PROVIDED
    elif raw_status in ("UNAVAILABLE", "NONE", "MISSING", "N/A", ""):
        transcript_status = TranscriptStatus.UNAVAILABLE
        transcript_text = None
    else:
        transcript_status = TranscriptStatus.UNAVAILABLE
        errors.append(f"Unrecognized transcript_status '{raw_status}'. Allowed: OFFICIAL_CAPTIONS, AUTO_GENERATED, CREATOR_PROVIDED, UNAVAILABLE")

    if transcript_status != TranscriptStatus.UNAVAILABLE and not transcript_text:
        # If status says captions exist but text is empty, mark unavailable
        transcript_status = TranscriptStatus.UNAVAILABLE

    # 7. Performance Classification (Researcher Claim)
    raw_perf = str(row.get("performance_class") or "").strip().upper()
    if "HIGH" in raw_perf or "TOP" in raw_perf or "VIRAL" in raw_perf:
        researcher_class = PerformanceClass.HIGH_PERFORMER
    elif "LOW" in raw_perf or "POOR" in raw_perf or "WEAK" in raw_perf:
        researcher_class = PerformanceClass.LOW_PERFORMER
    elif "NORMAL" in raw_perf or "AVERAGE" in raw_perf or "MEDIAN" in raw_perf or "BENCHMARK" in raw_perf:
        researcher_class = PerformanceClass.NORMAL_PERFORMER
    else:
        researcher_class = PerformanceClass.UNCLASSIFIED

    rel_perf = parse_float_or_none(row.get("relative_performance"))

    # 8. Publication Date
    pub_at = str(row.get("published_at") or "").strip() or None

    # 9. Uncertainties & Reasons
    selection_reason = str(row.get("selection_reason") or "").strip() or None
    raw_uncertainties = row.get("uncertainties")
    uncertainties_list: List[str] = []
    if raw_uncertainties:
        if isinstance(raw_uncertainties, list):
            uncertainties_list = [str(u).strip() for u in raw_uncertainties if u]
        elif isinstance(raw_uncertainties, str):
            uncertainties_list = [u.strip() for u in raw_uncertainties.split(";") if u.strip()]

    is_valid = len(errors) == 0

    return ValidatedExternalVideoRecord(
        row_index=row_index,
        channel_name=channel_name,
        channel_url=channel_url,
        public_subscriber_count=subs,
        video_title=title,
        youtube_url=raw_url,
        video_id=vid_id or f"invalid_{row_index}",
        published_at=pub_at,
        duration_seconds=duration,
        views=views,
        likes=likes,
        comments=comments,
        transcript_status=transcript_status,
        transcript_text=transcript_text,
        transcript_path=None,
        researcher_classification=researcher_class,
        researcher_relative_performance=rel_perf,
        computed_classification=PerformanceClass.UNCLASSIFIED,
        computed_relative_views=1.0,
        selection_reason=selection_reason,
        uncertainties=uncertainties_list,
        dataset_id=dataset_id,
        source_type="PUBLIC_YOUTUBE",
        is_valid=is_valid,
        validation_errors=errors
    )
