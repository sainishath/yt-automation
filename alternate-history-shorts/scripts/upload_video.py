# -*- coding: utf-8 -*-
"""
upload_video.py
---------------
Pipeline 1 Stage 5: Compliant YouTube Data API v3 Uploader.
Enforces:
- Category 27 (Education)
- Mandatory synthetic media disclosure (status.containsSyntheticMedia = True)
- Auto-appended RAG source citations from evidence_packet.json
- Idempotency & human-review rejection guard
"""

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path

_ROOT_REPO = Path(__file__).resolve().parent.parent.parent
if str(_ROOT_REPO) not in sys.path:
    sys.path.insert(0, str(_ROOT_REPO))

from pipeline.upload_guard import (
    append_rag_citations_to_description,
    build_youtube_insert_body,
)

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

# YouTube quota constants
_CONFIG_DIR = Path(__file__).parent.parent / "config"
QUOTA_UNITS_PER_UPLOAD = 1600
QUOTA_DAILY_LIMIT = 10000
QUOTA_TRACKER_FILE = _CONFIG_DIR / "quota_tracker.json"

# OAuth scopes required for upload and analytics
YOUTUBE_UPLOAD_SCOPE = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]
CLIENT_SECRETS_FILE = Path(os.getenv("P1_YOUTUBE_CLIENT_SECRETS", str(_CONFIG_DIR / "client_secrets.json")))
TOKEN_FILE = Path(os.getenv("P1_YOUTUBE_TOKEN", str(_CONFIG_DIR / "token.json")))

CATEGORY_EDUCATION = "27"


def load_quota_tracker() -> dict:
    """Loads today's quota usage from the tracker file."""
    today = time.strftime("%Y-%m-%d")
    if QUOTA_TRACKER_FILE.exists():
        try:
            with open(QUOTA_TRACKER_FILE, "r") as f:
                tracker = json.load(f)
            if tracker.get("date") == today:
                return tracker
        except Exception:
            pass
    return {"date": today, "units_used": 0, "uploads": []}


def save_quota_tracker(tracker: dict) -> None:
    """Saves quota usage tracker."""
    QUOTA_TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(QUOTA_TRACKER_FILE, "w") as f:
        json.dump(tracker, f, indent=2)


def get_authenticated_service(force_reauth: bool = False):
    """
    Authenticates with YouTube Data API v3.
    On first run or if force_reauth is True, opens a browser for OAuth consent and saves token.json.
    On subsequent runs, loads and refreshes token.json automatically.
    Returns an authenticated YouTube API service object.
    """
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    credentials = None

    if not force_reauth and TOKEN_FILE.exists():
        try:
            credentials = Credentials.from_authorized_user_file(
                str(TOKEN_FILE), YOUTUBE_UPLOAD_SCOPE
            )
            logging.info("Loaded existing token from config/token.json")
        except Exception as e:
            logging.warning(f"Could not load existing token: {e}. Will re-authenticate.")
            credentials = None

    if credentials and credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
            logging.info("Token refreshed successfully.")
            with open(TOKEN_FILE, "w") as f:
                f.write(credentials.to_json())
        except Exception as e:
            logging.warning(f"Token refresh failed: {e}. Will re-authenticate.")
            credentials = None

    if not credentials or not credentials.valid or force_reauth:
        if not CLIENT_SECRETS_FILE.exists():
            raise FileNotFoundError(
                f"client_secrets.json not found at {CLIENT_SECRETS_FILE}.\n"
                "Please complete Google Cloud Console OAuth setup:\n"
                "  1. Enable YouTube Data API v3\n"
                "  2. Create OAuth Client ID (Desktop app type)\n"
                "  3. Download credentials JSON -> rename to client_secrets.json\n"
                "  4. Place it in config/\n"
                "  5. Run: python scripts/upload_video.py --auth_only"
            )

        logging.info("Starting OAuth browser authentication flow...")
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CLIENT_SECRETS_FILE),
            scopes=YOUTUBE_UPLOAD_SCOPE
        )
        credentials = flow.run_local_server(port=0, prompt="select_account consent", open_browser=True)

        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_FILE, "w") as f:
            f.write(credentials.to_json())
        logging.info(f"Authentication successful. Token saved to {TOKEN_FILE}")

    youtube = build("youtube", "v3", credentials=credentials)
    return youtube


def upload_video(
    video_id: str = None,
    output_dir: str = "output",
    privacy: str = "public",
    force: bool = False,
    final_mp4: Path = None,
    title: str = None,
    description: str = None,
    tags: list = None,
    publish_at_iso: str = None
) -> dict:
    """
    Uploads a single video to YouTube with its generated metadata, RAG citations,
    and mandatory synthetic media disclosure (containsSyntheticMedia=True).
    """
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError

    if final_mp4 is None:
        video_path = Path(output_dir) / video_id
        if not video_path.exists():
            video_path = Path(__file__).parent.parent / output_dir / video_id
        final_mp4 = video_path / "final" / f"{video_id}_final.mp4"
        metadata_path = video_path / "metadata.json"
    else:
        final_mp4 = Path(final_mp4)
        video_path = final_mp4.parent.parent
        metadata_path = video_path / "metadata.json"

    if not final_mp4.exists():
        raise FileNotFoundError(
            f"Final video not found: {final_mp4}\n"
            "Run Stage 4 (assemble_video.py) first."
        )

    metadata = {}
    if metadata_path.exists():
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

    evidence_packet = None
    evidence_path = video_path / "evidence_packet.json"
    if evidence_path.exists():
        try:
            with open(evidence_path, "r", encoding="utf-8") as ef:
                evidence_packet = json.load(ef)
        except Exception:
            evidence_packet = None

    # Rejection & Scrapped Protection Guard
    manifest_path = video_path / "run_manifest.json"
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as mf:
                m_data = json.load(mf)
            if m_data.get("status") in ("REJECTED", "REJECTED_SCRAPPED", "SCRAPPED"):
                raise RuntimeError(
                    f"CANNOT_UPLOAD_SCRAPPED_VIDEO: Video '{video_id}' was rejected by human reviewer and is permanently scrapped. "
                    "All uploads to YouTube (including private/unlisted) are strictly forbidden."
                )
        except json.JSONDecodeError:
            pass

    # Idempotency / Duplicate Protection Check
    existing_yt_id = metadata.get("youtube_video_id")
    if existing_yt_id and not force:
        public_url = metadata.get("youtube_url", f"https://youtu.be/{existing_yt_id}")
        studio_url = f"https://studio.youtube.com/video/{existing_yt_id}/edit"
        logging.info(f"[IDEMPOTENCY] Video '{video_id}' has already been uploaded (YouTube ID: {existing_yt_id}). Skipping duplicate upload (use --force to re-upload).")
        return {
            "video_id": video_id,
            "youtube_video_id": existing_yt_id,
            "studio_url": studio_url,
            "public_url": public_url,
            "status": "ALREADY_UPLOADED"
        }

    if title is None:
        title = metadata.get("title", f"What If: {video_id}")
    if description is None:
        description = metadata.get("description", "")
    if tags is None:
        tags = metadata.get("tags", [])

    if "#Shorts" not in description and "#shorts" not in description:
        description += "\n\n#Shorts"

    # Auto-append RAG citations and synthetic media disclosure
    description = append_rag_citations_to_description(description, evidence_packet)

    # Check quota before uploading
    tracker = load_quota_tracker()
    units_remaining = QUOTA_DAILY_LIMIT - tracker["units_used"]
    if units_remaining < QUOTA_UNITS_PER_UPLOAD:
        raise RuntimeError(
            f"Daily quota limit approaching! "
            f"Used: {tracker['units_used']}/{QUOTA_DAILY_LIMIT} units. "
            f"Remaining: {units_remaining} (need {QUOTA_UNITS_PER_UPLOAD} per upload). "
            "Wait until tomorrow or request a quota increase."
        )

    logging.info(f"Quota check OK. Used: {tracker['units_used']}/{QUOTA_DAILY_LIMIT} units today.")

    youtube = get_authenticated_service()

    body = build_youtube_insert_body(
        title=title,
        description=description,
        tags=tags,
        category_id=CATEGORY_EDUCATION,
        publish_at_iso=publish_at_iso,
    )
    if not publish_at_iso:
        body["status"]["privacyStatus"] = privacy

    file_size_mb = final_mp4.stat().st_size / (1024 * 1024)
    logging.info(
        f"Uploading {final_mp4.name} ({file_size_mb:.1f} MB) "
        f"as '{title[:60]}...' | Privacy: {body['status']['privacyStatus']}"
    )
    print(f"\n  Uploading: {final_mp4.name} ({file_size_mb:.1f} MB)")
    print(f"  Title: {title}")
    print(f"  Privacy: {body['status']['privacyStatus']}")

    media = MediaFileUpload(
        str(final_mp4),
        mimetype="video/mp4",
        chunksize=5 * 1024 * 1024,
        resumable=True
    )

    try:
        insert_request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media
        )

        response = None
        start_time = time.time()

        while response is None:
            status, response = insert_request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                elapsed = time.time() - start_time
                print(f"\r  Upload progress: {pct}% ({elapsed:.0f}s elapsed)", end="", flush=True)

        print()

    except HttpError as e:
        error_content = json.loads(e.content.decode()) if e.content else {}
        error_msg = error_content.get("error", {}).get("message", str(e))
        if privacy == "public":
            logging.warning(f"Public upload rejected by YouTube API ({error_msg}). Falling back to 'private' privacy...")
            print(f"\n  [UPLOAD WARNING] Public upload rejected ({error_msg}). Retrying as 'private'...")
            privacy = "private"
            body["status"]["privacyStatus"] = "private"
            media = MediaFileUpload(
                str(final_mp4),
                mimetype="video/mp4",
                chunksize=5 * 1024 * 1024,
                resumable=True
            )
            insert_request = youtube.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media
            )
            response = None
            start_time = time.time()
            while response is None:
                status, response = insert_request.next_chunk()
                if status:
                    pct = int(status.progress() * 100)
                    elapsed = time.time() - start_time
                    print(f"\r  Upload progress (private fallback): {pct}% ({elapsed:.0f}s elapsed)", end="", flush=True)
            print()
        else:
            logging.error(f"YouTube API error during upload: {error_msg}")
            raise RuntimeError(f"YouTube upload failed: {error_msg}") from e

    yt_video_id = response.get("id", "")
    studio_url = f"https://studio.youtube.com/video/{yt_video_id}/edit"
    public_url = f"https://youtu.be/{yt_video_id}"

    upload_time = time.time() - start_time

    tracker["units_used"] += QUOTA_UNITS_PER_UPLOAD
    tracker["uploads"].append({
        "video_id": video_id or str(final_mp4.stem),
        "youtube_id": yt_video_id,
        "privacy": privacy,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "upload_time_seconds": round(upload_time, 1)
    })
    save_quota_tracker(tracker)

    metadata["youtube_video_id"] = yt_video_id
    metadata["youtube_url"] = public_url
    metadata["privacy"] = privacy
    if metadata_path.parent.exists():
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    logging.info(
        f"Upload successful! YouTube ID: {yt_video_id} | "
        f"Privacy: {privacy} | Time: {upload_time:.1f}s"
    )
    logging.info(f"Studio URL: {studio_url}")
    logging.info(f"Public URL: {public_url}")

    print("\n" + "=" * 60)
    print(f"  Upload Complete: {video_id or final_mp4.name}")
    print(f"  YouTube ID:  {yt_video_id}")
    print(f"  Privacy:     {privacy}")
    print(f"  Studio URL:  {studio_url}")
    print(f"  Public URL:  {public_url}")
    print(f"  Upload time: {upload_time:.1f}s")
    print(f"  Quota used:  {tracker['units_used']}/{QUOTA_DAILY_LIMIT} units today")
    print("=" * 60 + "\n")

    return {
        "video_id": video_id or str(final_mp4.stem),
        "youtube_video_id": yt_video_id,
        "studio_url": studio_url,
        "public_url": public_url,
        "privacy": privacy
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 5: Upload video to YouTube")
    parser.add_argument("--video_id", help="Video folder name to upload")
    parser.add_argument(
        "--privacy",
        choices=["private", "unlisted", "public"],
        default="public",
        help="YouTube privacy status (default: public)"
    )
    parser.add_argument(
        "--auth_only",
        action="store_true",
        help="Run OAuth authentication flow only and save token.json, then exit."
    )
    parser.add_argument("--force", action="store_true", help="Force upload even if metadata already contains a youtube_id")
    parser.add_argument("--output_dir", default="output", help="Base output directory")
    args = parser.parse_args()

    if args.auth_only:
        logging.info("Running authentication-only flow...")
        try:
            youtube = get_authenticated_service(force_reauth=True)
            logging.info("Authentication successful! token.json saved to config/.")
            print("\n  Authentication successful!")
            print(f"  token.json saved to: {TOKEN_FILE}")
            try:
                ch_res = youtube.channels().list(mine=True, part="snippet").execute()
                items = ch_res.get("items", [])
                if items:
                    ch = items[0]
                    print(f"  Authenticated Channel ID: {ch.get('id')}")
                    print(f"  Authenticated Channel Title: {ch.get('snippet', {}).get('title')}")
                    print(f"  Authenticated Channel Handle: {ch.get('snippet', {}).get('customUrl')}")
            except Exception as ce:
                print(f"  Channel query warning: {ce}")
            print("  You can now run uploads without re-authentication.")
        except Exception as e:
            logging.error(f"Authentication failed: {e}")
            sys.exit(1)
        sys.exit(0)

    if not args.video_id:
        parser.error("--video_id is required when not using --auth_only")

    try:
        result = upload_video(args.video_id, args.output_dir, args.privacy, force=args.force)
    except Exception as e:
        logging.error(f"Upload failed: {e}")
        sys.exit(1)
