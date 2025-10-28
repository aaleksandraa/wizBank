from wizvod.core.email_providers import gmail_oauth, outlook_oauth, yahoo_oauth

class EmailAuthManager:
    """
    Bira način autentifikacije na osnovu provider-a:
    - gmail -> OAuth2
    - outlook/hotmail -> OAuth2
    - yahoo -> OAuth2
    - sve ostalo -> klasični IMAP login
    """
    @staticmethod
    def get_auth_method(provider: str, email: str):
        p = (provider or "").lower()

        if "gmail" in p:
            token = gmail_oauth.get_token(email)
            return ("xoauth2", token)
        elif "outlook" in p or "hotmail" in p or "live" in p:
            token = outlook_oauth.get_token(email)
            return ("xoauth2", token)
        elif "yahoo" in p:
            token = yahoo_oauth.get_token(email)
            return ("xoauth2", token)
        else:
            return ("password", None)
