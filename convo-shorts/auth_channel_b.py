# -*- coding: utf-8 -*-
"""
auth_channel_b.py
-----------------
Standalone authentication runner for Channel B (Debate Protocol).
"""

import os
import sys
import pickle
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

BASE_DIR = Path(__file__).parent
CREDENTIALS_FILE = BASE_DIR / "yt-automation-engine" / "youtube_credentials.json"
TOKEN_FILE = BASE_DIR / "yt-automation-engine" / "youtube_token.pickle"
AUTH_PORT = 8090

print("=" * 60, flush=True)
print("  CHANNEL B (DEBATE PROTOCOL) OAUTH AUTHENTICATION", flush=True)
print("=" * 60, flush=True)

if not CREDENTIALS_FILE.exists():
    print(f"ERROR: Credentials file not found at {CREDENTIALS_FILE}", flush=True)
    sys.exit(1)

flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
creds = flow.run_local_server(port=AUTH_PORT, prompt="consent", open_browser=True)

with open(TOKEN_FILE, "wb") as f:
    pickle.dump(creds, f)

print("\nSUCCESS: Token saved to:", TOKEN_FILE, flush=True)

try:
    youtube = build("youtube", "v3", credentials=creds)
    ch_res = youtube.channels().list(mine=True, part="snippet").execute()
    items = ch_res.get("items", [])
    if items:
        ch = items[0]
        print(f"Authenticated Channel ID: {ch.get('id')}", flush=True)
        print(f"Authenticated Channel Title: {ch.get('snippet', {}).get('title')}", flush=True)
        print(f"Authenticated Channel Handle: {ch.get('snippet', {}).get('customUrl')}", flush=True)
except Exception as e:
    print(f"Warning: Could not query channel info: {e}", flush=True)
