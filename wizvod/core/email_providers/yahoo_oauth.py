import json
from pathlib import Path
from requests_oauthlib import OAuth2Session

CLIENT_ID = "your-yahoo-client-id"
CLIENT_SECRET = "your-yahoo-client-secret"
AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
REDIRECT_URI = "http://localhost:8080"
SCOPE = ["mail-w"]

TOKEN_FILE = Path.home() / ".wizvod" / "tokens" / "yahoo_token.json"

def get_token(email: str):
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    if TOKEN_FILE.exists():
        token = json.load(open(TOKEN_FILE))
        return token["access_token"]

    oauth = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPE)
    authorization_url, state = oauth.authorization_url(AUTH_URL)
    print(f"Otvori link i potvrdi pristup:\n{authorization_url}")
    redirect_response = input("Zalijepi cijeli redirect URL: ")
    token = oauth.fetch_token(TOKEN_URL, client_secret=CLIENT_SECRET, authorization_response=redirect_response)
    json.dump(token, open(TOKEN_FILE, "w"))
    return token["access_token"]
