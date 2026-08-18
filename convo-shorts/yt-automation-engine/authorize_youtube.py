"""
YouTube OAuth - manual URL flow.
Prints the auth URL for you to open in your browser,
then waits for Google to redirect back to localhost:8090.
"""
import os
import pickle
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CREDENTIALS_FILE = str(Path(__file__).parent / "youtube_credentials.json")
TOKEN_FILE = str(Path(__file__).parent / "youtube_token.pickle")

flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)

# Run but don't open browser - just print the URL
creds = flow.run_local_server(
    port=8090,
    open_browser=False,   # <-- do NOT try to open browser
    prompt="consent",
    access_type="offline",
)

with open(TOKEN_FILE, "wb") as f:
    pickle.dump(creds, f)

print("\n✅ Authorization complete! Token saved.")
print("Your pipeline is ready to upload to YouTube.")
