import imaplib
import email
from email.message import Message
from email.header import decode_header, make_header
from datetime import datetime
from typing import List, Tuple, Optional
from wizvod.core.logger import get_logger
from wizvod.core.crypto import decrypt_secret

log = get_logger("imap")


class EmailFetcher:
    def __init__(self):
        self.imap = None

    def connect_imap(self, account_row: dict):
        """Povezivanje na IMAP server koristeći podatke iz baze (lozinka ili OAuth2 token)."""
        host = account_row["imap_host"]
        port = int(account_row["imap_port"])
        use_ssl = bool(account_row["use_ssl"])
        username = account_row["username"] or account_row["email"]

        # 👉 Novi dio: pokušaj detektovati da li koristimo OAuth2 token
        try:
            from wizvod.core.email_auth_manager import EmailAuthManager
            auth_type, token = EmailAuthManager.get_auth_method(account_row["provider"], username)
        except Exception as e:
            log.warning(f"EmailAuthManager nije dostupan: {e}")
            auth_type, token = ("password", None)

        log.info(f"Povezivanje na {host}:{port} ({'SSL' if use_ssl else 'plain'}) kao {username} ({auth_type})")

        # Kreiraj IMAP konekciju
        if use_ssl:
            self.imap = imaplib.IMAP4_SSL(host, port)
        else:
            self.imap = imaplib.IMAP4(host, port)

        # Autentifikacija
        if auth_type == "xoauth2" and token:
            try:
                auth_string = f"user={username}\1auth=Bearer {token}\1\1"
                self.imap.authenticate("XOAUTH2", lambda x: auth_string.encode("utf-8"))
                log.info("Uspješna XOAUTH2 autentifikacija.")
            except Exception as e:
                log.error(f"Neuspješna XOAUTH2 autentifikacija: {e}")
                raise
        else:
            password = decrypt_secret(account_row["secret_encrypted"] or b"")
            self.imap.login(username, password)

        self.imap.select("INBOX")

    def search_messages(self, since: datetime, from_sender: Optional[str], unread_only: bool) -> List[Message]:
        """Pretraga poruka po datumu, pošiljaocu i statusu pročitanosti."""
        criteria = []
        if from_sender:
            # makni eventualni naziv i razmake, i ne koristi navodnike
            sender_clean = from_sender.strip().lower().replace("<", "").replace(">", "")
            criteria += ["FROM", sender_clean]
        criteria += ["SINCE", since.strftime("%d-%b-%Y")]
        if unread_only:
            criteria += ["UNSEEN"]

        status, data = self.imap.search(None, *criteria)
        if status != "OK":
            log.warning("IMAP search nije vratio rezultate.")
            return []

        ids = data[0].split()
        messages = []

        for uid in ids:
            status, msg_data = self.imap.fetch(uid, "(RFC822)")
            if status != "OK":
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            msg._wiz_uid = uid  # čuvamo UID za kasnije označavanje
            messages.append(msg)

        log.info(f"Pronađeno {len(messages)} poruka.")
        if not messages:
            log.warning(f"Nema poruka za pošiljaoca {from_sender} od {since.strftime('%d-%b-%Y')}.")
        return messages

    def extract_attachments(self, msg: Message) -> List[Tuple[str, bytes]]:
        """Ekstrahuje PDF priloge iz poruke."""
        items = []
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_disposition() == "attachment":
                    filename = part.get_filename()
                    if filename:
                        try:
                            filename = str(make_header(decode_header(filename)))
                        except Exception:
                            pass
                        payload = part.get_payload(decode=True)
                        if payload:
                            items.append((filename, payload))
        else:
            if msg.get_content_type() == "application/pdf":
                payload = msg.get_payload(decode=True)
                if payload:
                    items.append(("attachment.pdf", payload))
        return items

    def get_subject(self, msg: Message) -> str:
        """Dekodira subject iz emaila (UTF-8, ISO-8859-2 itd)."""
        subj = msg.get("Subject", "")
        try:
            subj = str(make_header(decode_header(subj)))
        except Exception:
            pass
        return subj.strip()

    def mark_as_read(self, msg: Message):
        """Označava poruku kao pročitanu (\\Seen)."""
        uid = getattr(msg, "_wiz_uid", None)
        if uid:
            try:
                self.imap.store(uid, "+FLAGS", "\\Seen")
            except Exception as e:
                log.warning(f"Neuspješno označavanje poruke: {e}")

    def close(self):
        """Sigurno zatvaranje IMAP konekcije."""
        try:
            self.imap.close()
        except Exception:
            pass
        try:
            self.imap.logout()
        except Exception:
            pass
