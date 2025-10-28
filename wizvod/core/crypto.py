import os
import base64
import hashlib
import hmac
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# ENV varijable:
# 1) WIZVOD_KEY_B64  -> urlsafe base64-encoded 32-byte key ZA FERNET (preporučeno)
# 2) WIZVOD_KEY_PASSPHRASE -> ljudski čitljiv passphrase; derivira se key (ako nema #1)
# Ako nema ni #1 ni #2 -> rad bez enkripcije (plain, kompatibilno sa ranijim ponašanjem)

_ENV_KEY_B64 = "WIZVOD_KEY_B64"
_ENV_PASSPHRASE = "WIZVOD_KEY_PASSPHRASE"
# Salt je fiksan u appu (možeš promijeniti po izdanju); cilj je imati deterministički key iz passphrase
_KDF_SALT = b"wizvod-kdf-salt-v1"
_KDF_ITER = 200_000


def _derive_key_from_passphrase(passphrase: str) -> bytes:
    """PBKDF2-HMAC-SHA256 -> 32B, zatim urlsafe-base64 za Fernet."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_KDF_SALT,
        iterations=_KDF_ITER,
    )
    raw = kdf.derive(passphrase.encode("utf-8"))
    return base64.urlsafe_b64encode(raw)


def _load_fernet_key() -> Optional[bytes]:
    """
    Vraća validan Fernet ključ (urlsafe base64 encoded 32B) ili None ako ne postoji konfiguracija.
    Prioritet:
      1) WIZVOD_KEY_B64 (mora biti validan base64 i dužine)
      2) WIZVOD_KEY_PASSPHRASE -> KDF -> B64
      3) None (bez enkripcije)
    """
    k_b64 = os.getenv(_ENV_KEY_B64)
    if k_b64:
        try:
            key_bytes = k_b64.encode("utf-8")
            # Validacija: dekodiraj i provjeri dužinu
            raw = base64.urlsafe_b64decode(key_bytes)
            if len(raw) != 32:
                # pogrešna dužina — odbaci
                return None
            return key_bytes
        except Exception:
            return None

    passphrase = os.getenv(_ENV_PASSPHRASE)
    if passphrase:
        try:
            return _derive_key_from_passphrase(passphrase)
        except Exception:
            return None

    return None  # bez enkripcije


_FERNET_KEY = _load_fernet_key()
_FERNET: Optional[Fernet] = Fernet(_FERNET_KEY) if _FERNET_KEY else None


def encrypt_secret(plaintext: str) -> bytes:
    """
    Enkriptuj lozinku/tajnu. Ako nema konfigurisanog ključa, vrati plaintext kao bytes (fallback).
    """
    if not isinstance(plaintext, str):
        plaintext = str(plaintext)
    data = plaintext.encode("utf-8")

    if _FERNET is None:
        return data  # bez enkripcije, kompatibilno sa starim ponašanjem

    try:
        return _FERNET.encrypt(data)
    except Exception:
        # u krajnjem slučaju: vrati plaintext (ne ruši app)
        return data


def decrypt_secret(cipher: bytes) -> str:
    """
    Dešifruj tajnu. Podržava:
    - Enkriptovano (Fernet) ako je ključ podešen.
    - Plaintext fallback (kad je app radila bez enkripcije).
    """
    if cipher is None:
        return ""

    if _FERNET is None:
        # nema enkripcije — očekujemo plain
        try:
            return cipher.decode("utf-8")
        except Exception:
            return ""

    # Probaj prvo kao Fernet
    try:
        dec = _FERNET.decrypt(cipher)
        return dec.decode("utf-8")
    except InvalidToken:
        # vjerovatno plain spremljeno bez enkripcije
        try:
            return cipher.decode("utf-8")
        except Exception:
            return ""
    except Exception:
        # i u slučaju greške — pokušaj kao plain
        try:
            return cipher.decode("utf-8")
        except Exception:
            return ""
