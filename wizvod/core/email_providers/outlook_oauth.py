import json
from pathlib import Path
import msal

CLIENT_ID = "your-outlook-client-id"
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPE = ["https://outlook.office.com/IMAP.AccessAsUser.All"]
TOKEN_FILE = Path.home() / ".wizvod" / "tokens" / "outlook_token.json"

def get_token(email: str):
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)

    result = None
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPE, account=accounts[0])

    if not result:
        flow = app.initiate_device_flow(scopes=SCOPE)
        print(flow["message"])
        result = app.acquire_token_by_device_flow(flow)
        with open(TOKEN_FILE, "w") as f:
            json.dump(result, f)

    return result["access_token"]
