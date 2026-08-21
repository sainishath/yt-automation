# -*- coding: utf-8 -*-
"""
youtube_observer.py
-------------------
Legitimate public YouTube Data API v3 collector for analog channels and public Short assets.
Collects public video metadata, views, likes, comments, and durations with strict provenance tagging.
"""

import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from growth.external_intelligence.schemas import (
    ExternalVideoModel,
    ExternalChannelModel,
    ProvenanceSource
)


def parse_iso_duration(duration_str: str) -> float:
    """Parses ISO 8601 duration string (e.g. PT45S, PT1M15S, PT1H2M) into seconds without external dependencies."""
    if not duration_str:
        return 0.0
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", duration_str, re.IGNORECASE)
    if not match:
        return 0.0
    hours = float(match.group(1) or 0)
    minutes = float(match.group(2) or 0)
    seconds = float(match.group(3) or 0)
    return hours * 3600.0 + minutes * 60.0 + seconds


class YouTubePublicObserver:
    def __init__(self, token_path: Optional[Path] = None, dry_run: bool = False):
        if token_path is None:
            # Auto-discover default OAuth tokens if present on disk
            default_p1 = Path(__file__).parent.parent.parent / "alternate-history-shorts" / "config" / "token.json"
            default_p2 = Path(__file__).parent.parent.parent / "convo-shorts" / "yt-automation-engine" / "youtube_token.pickle"
            if default_p1.exists():
                token_path = default_p1
            elif default_p2.exists():
                token_path = default_p2

        self.token_path = token_path
        self.dry_run = dry_run

    def _get_youtube_service(self) -> Optional[Any]:
        """Loads YouTube Data API client if credentials are valid."""
        if self.dry_run or not self.token_path or not self.token_path.exists():
            return None

        import pickle
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        try:
            if str(self.token_path).endswith(".pickle"):
                with open(self.token_path, "rb") as f:
                    creds = pickle.load(f)
            else:
                creds = Credentials.from_authorized_user_file(str(self.token_path))

            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())

            return build("youtube", "v3", credentials=creds)
        except Exception as e:
            logging.warning(f"[YouTube Observer] Could not build YouTube service: {e}")
            return None

    def fetch_channel_public_profile(self, channel_id_or_handle: str) -> Dict[str, Any]:
        """Fetches public channel statistics and metadata from YouTube."""
        yt = self._get_youtube_service()
        if not yt:
            return {
                "status": "UNAVAILABLE",
                "is_simulation": True,
                "source_type": ProvenanceSource.SIMULATION.value,
                "subscriber_count": 0,
                "video_count": 0
            }

        try:
            if channel_id_or_handle.startswith("@"):
                res = yt.channels().list(part="snippet,statistics", forHandle=channel_id_or_handle).execute()
            else:
                res = yt.channels().list(part="snippet,statistics", id=channel_id_or_handle).execute()

            items = res.get("items", [])
            if not items:
                return {"status": "NOT_FOUND", "is_simulation": False, "source_type": ProvenanceSource.PUBLIC_YOUTUBE.value}

            item = items[0]
            stats = item.get("statistics", {})
            return {
                "status": "SUCCESS",
                "youtube_channel_id": item.get("id"),
                "channel_title": item.get("snippet", {}).get("title"),
                "subscriber_count": int(stats.get("subscriberCount", 0)),
                "video_count": int(stats.get("videoCount", 0)),
                "view_count": int(stats.get("viewCount", 0)),
                "is_simulation": False,
                "source_type": ProvenanceSource.PUBLIC_YOUTUBE.value
            }
        except Exception as e:
            logging.error(f"[YouTube Observer] API Error fetching channel {channel_id_or_handle}: {e}")
            return {"status": "ERROR", "error": str(e), "is_simulation": False, "source_type": ProvenanceSource.PUBLIC_YOUTUBE.value}

    def fetch_recent_public_videos(self, channel_id: str, max_results: int = 10) -> List[ExternalVideoModel]:
        """Fetches recent public video metadata for an analog channel via playlistItems or search API."""
        yt = self._get_youtube_service()
        if not yt:
            return []

        video_ids = []

        # Strategy 1: Efficient 1-unit quota fetch via uploads playlist (UU...)
        if channel_id.startswith("UC"):
            uploads_pl_id = "UU" + channel_id[2:]
            try:
                pl_res = yt.playlistItems().list(
                    part="snippet",
                    playlistId=uploads_pl_id,
                    maxResults=max_results
                ).execute()
                video_ids = [
                    item["snippet"]["resourceId"]["videoId"]
                    for item in pl_res.get("items", [])
                    if "resourceId" in item.get("snippet", {}) and "videoId" in item["snippet"]["resourceId"]
                ]
            except Exception as pe:
                logging.debug(f"[YouTube Observer] playlistItems fetch failed for {uploads_pl_id}: {pe}")

        # Strategy 2: Fallback to search.list if playlistItems produced no video IDs
        if not video_ids:
            try:
                search_res = yt.search().list(
                    part="snippet",
                    channelId=channel_id,
                    order="date",
                    type="video",
                    maxResults=max_results
                ).execute()
                video_ids = [
                    item["id"]["videoId"]
                    for item in search_res.get("items", [])
                    if "videoId" in item.get("id", {})
                ]
            except Exception as se:
                logging.error(f"[YouTube Observer] Search API failed for {channel_id}: {se}")

        if not video_ids:
            return []

        try:
            vids_res = yt.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(video_ids)
            ).execute()

            videos = []
            for item in vids_res.get("items", []):
                vid_id = item["id"]
                snippet = item.get("snippet", {})
                stats = item.get("statistics", {})
                content = item.get("contentDetails", {})

                # Parse duration
                dur_iso = content.get("duration", "PT0S")
                try:
                    dur_sec = parse_iso_duration(dur_iso)
                except Exception:
                    dur_sec = 0.0

                is_short = dur_sec > 0 and dur_sec <= 60.0

                vid_model = ExternalVideoModel(
                    external_video_id=f"ext_vid_{vid_id}",
                    external_channel_id=f"ext_ch_{channel_id}",
                    youtube_video_id=vid_id,
                    title=snippet.get("title", ""),
                    url=f"https://www.youtube.com/shorts/{vid_id}" if is_short else f"https://www.youtube.com/watch?v={vid_id}",
                    published_at=snippet.get("publishedAt"),
                    duration_seconds=dur_sec,
                    is_short=is_short,
                    views=int(stats.get("viewCount", 0)),
                    likes=int(stats.get("likeCount", 0)),
                    comments=int(stats.get("commentCount", 0)),
                    relative_view_multiplier=1.0,
                    is_simulation=False,
                    source_type=ProvenanceSource.PUBLIC_YOUTUBE
                )
                videos.append(vid_model)

            return videos
        except Exception as e:
            logging.error(f"[YouTube Observer] Failed to fetch public videos for {channel_id}: {e}")
            return []
