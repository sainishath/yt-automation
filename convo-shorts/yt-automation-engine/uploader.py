"""
uploader.py
-----------
Handles the final upload payload for YouTube.

RULE: hashtags (e.g. #Shorts #DeepLearning) MUST appear
      - at the end of the description string
      - in the tags list as individual strings with the # prefix

OAUTH FLOW:
  First run: call GET /auth-youtube on the Flask server (port 5001) in your browser.
  This spins up a temporary local server on port 8090, opens Google's consent screen,
  waits for you to authorize, then saves youtube_token.pickle and shuts down.
  All subsequent calls auto-refresh the token silently.
"""

import os
import pickle
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ── OAuth config ──────────────────────────────────────────────────────────────
SCOPES           = ["https://www.googleapis.com/auth/youtube.upload"]
CREDENTIALS_FILE = os.getenv("P2_YOUTUBE_CLIENT_SECRETS", str(Path(__file__).parent / "youtube_credentials.json"))
TOKEN_FILE       = os.getenv("P2_YOUTUBE_TOKEN", str(Path(__file__).parent / "youtube_token.pickle"))
AUTH_PORT        = int(os.getenv("P2_YOUTUBE_AUTH_PORT", "8090"))   # Local port for OAuth callback

# YouTube category IDs
CATEGORY_EDUCATION    = "27"
CATEGORY_ENTERTAINMENT = "24"


def is_authorized() -> bool:
    """Check if a valid saved token already exists."""
    if not os.path.exists(TOKEN_FILE):
        return False
    try:
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
        return creds and (creds.valid or (creds.expired and creds.refresh_token))
    except Exception:
        return False


def run_auth_flow() -> bool:
    """
    Run the one-time OAuth authorization flow.
    Opens a browser window, waits for user consent, saves the token.
    Called from /auth-youtube Flask endpoint — runs in a background thread.
    Returns True on success.
    """
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(
            f"youtube_credentials.json not found at {CREDENTIALS_FILE}."
        )
    flow  = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=AUTH_PORT, open_browser=True)
    with open(TOKEN_FILE, "wb") as f:
        pickle.dump(creds, f)
    return True


def _get_youtube_service():
    """Authenticate with YouTube Data API v3 using saved OAuth2 token."""
    creds = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save refreshed token
            with open(TOKEN_FILE, "wb") as f:
                pickle.dump(creds, f)
        else:
            raise RuntimeError(
                "YouTube not authorized. Visit http://localhost:5001/auth-youtube "
                "in your browser to complete one-time OAuth setup."
            )

    return build("youtube", "v3", credentials=creds)


def upload_to_youtube(
    video_path: str,
    title: str,
    description: str,
    hashtags: list,
    category_id: str = CATEGORY_EDUCATION,
    privacy_status: str = "public",
    thumbnail_path: str = None
) -> dict:
    """
    Upload `video_path` to YouTube as a Short with Public visibility by default.

    Args:
        video_path:     Absolute path to the final MP4.
        title:          Video title — will have #Shorts appended if missing.
        description:    Main description text. Hashtags are appended automatically.
        hashtags:       List of hashtag strings WITH the # sign.
        category_id:    YouTube category ID string (default: "27" = Education).
        privacy_status: "public" (default), "unlisted", or "private".
        thumbnail_path: Optional path to custom thumbnail JPEG image.

    Returns:
        {"status": "success", "video_id": str, "url": str, "privacy_status": str, "thumbnail_uploaded": bool}
        or
        {"status": "error",   "error": str}
    """
    import json
    
    # ── check for existing upload in manifest (idempotency safety) ──────────────
    manifest_p = Path(video_path).with_suffix(".manifest.json")
    if manifest_p.exists():
        try:
            with open(manifest_p, "r", encoding="utf-8") as mf:
                mdata = json.load(mf)
            yt_data = mdata.get("youtube_deployment", {})
            if yt_data.get("uploaded") and yt_data.get("video_id"):
                vid_id = yt_data["video_id"]
                url = f"https://www.youtube.com/shorts/{vid_id}"
                print(f"[Upload] Video already uploaded to YouTube (ID: {vid_id}). Skipping re-upload.")
                return {
                    "status": "success",
                    "video_id": vid_id,
                    "url": url,
                    "privacy_status": yt_data.get("privacy_status", privacy_status),
                    "thumbnail_uploaded": yt_data.get("thumbnail_uploaded", False)
                }
        except Exception as me:
            print(f"[Upload Warning] Could not parse manifest for idempotency check: {me}")

    # ── enforce #Shorts in title ──────────────────────────────────────────────
    if "#Shorts" not in title and "#shorts" not in title:
        title = title + " #Shorts"

    # ── enforce hashtags in description ──────────────────────────────────────
    tag_block = " ".join(hashtags)
    if tag_block not in description:
        description = description.rstrip() + "\n\n" + tag_block

    # ── enforce #Shorts in tags ───────────────────────────────────────────────
    if "#Shorts" not in hashtags:
        hashtags = ["#Shorts"] + hashtags

    # ── synthetic media disclosure note ───────────────────────────────────────
    synthetic_note = "\n\n[Altered or Synthetic Content: This video contains AI-generated visual and audio content.]"
    if synthetic_note not in description:
        description += synthetic_note

    try:
        youtube = _get_youtube_service()

        body = {
            "snippet": {
                "title":           title,
                "description":     description,
                "tags":            hashtags,
                "categoryId":      category_id,
                "defaultLanguage": "en",
            },
            "status": {
                "privacyStatus":           privacy_status,
                "madeForKids":             False,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=5 * 1024 * 1024,   # 5 MB chunks
        )

        insert_request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = None
        while response is None:
            status, response = insert_request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print(f"[Upload] {pct}% ...")

        vid_id = response["id"]
        url    = f"https://www.youtube.com/shorts/{vid_id}"
        print(f"[Upload] OK Uploaded ({privacy_status}) -> {url}")

        # Upload custom thumbnail if available or generated
        thumb_uploaded = False
        target_thumb = thumbnail_path or str(Path(video_path).with_suffix(".jpg"))
        if not Path(target_thumb).exists():
            try:
                from thumbnail_generator import generate_debate_thumbnail
                generate_debate_thumbnail(title, target_thumb)
            except Exception as tg_err:
                print(f"[Upload Warning] Could not generate thumbnail: {tg_err}")

        if Path(target_thumb).exists():
            try:
                youtube.thumbnails().set(
                    videoId=vid_id,
                    media_body=MediaFileUpload(target_thumb, mimetype="image/jpeg")
                ).execute()
                thumb_uploaded = True
                print(f"[Upload] OK Uploaded thumbnail: {target_thumb}")
            except Exception as th_err:
                print(f"[Upload Warning] Thumbnail upload to YouTube failed: {th_err}")

        # Update or create manifest (guarantees upload idempotency)
        import time
        mdata = {}
        if manifest_p.exists():
            try:
                with open(manifest_p, "r", encoding="utf-8") as mf:
                    mdata = json.load(mf)
            except Exception as me:
                print(f"[Upload Warning] Could not parse existing manifest: {me}")

        mdata["youtube_deployment"] = {
            "privacy_status": privacy_status,
            "uploaded": True,
            "video_id": vid_id,
            "url": url,
            "thumbnail_path": target_thumb if Path(target_thumb).exists() else None,
            "thumbnail_uploaded": thumb_uploaded,
            "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        try:
            with open(manifest_p, "w", encoding="utf-8") as mf:
                json.dump(mdata, mf, indent=2)
            print(f"[Upload] Saved/Updated manifest at {manifest_p.name} with YouTube video ID: {vid_id}")
        except Exception as me:
            print(f"[Upload Warning] Could not write manifest with video ID: {me}")

        return {
            "status": "success",
            "video_id": vid_id,
            "url": url,
            "privacy_status": privacy_status,
            "thumbnail_uploaded": thumb_uploaded
        }

    except Exception as e:
        print(f"[Upload] FAIL: {e}")
        return {"status": "error", "error": str(e)}

    except Exception as e:
        print(f"[Upload] FAIL: {e}")
        return {"status": "error", "error": str(e)}
