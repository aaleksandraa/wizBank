import os, json
from pathlib import Path
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

SCOPES = ["https://mail.google.com/"]
APP_DIR = Path.home() / ".wizvod" / "tokens"
APP_DIR.mkdir(parents=True, exist_ok=True)
TOKEN_FILE = APP_DIR / "gmail_token.json"
CLIENT_FILE = Path(__file__).resolve().parent / "google_client_secret.json"

def get_token(email: str):
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return creds.token
