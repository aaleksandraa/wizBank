import json
import hashlib
import os
import getpass
from datetime import datetime
from typing import Optional, Tuple
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization, hashes

from wizvod.core.db import Database
from wizvod.core.logger import get_logger

log = get_logger("license")

# 🔐 Ugrađeni javni ključ (public_key.pem)
# Zamijeni ovo svojim stvarnim javnim RSA ključem koji dobiješ iz generate_license.py
PUBLIC_KEY_PEM = """
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAsB56mH1C51UVh6rgAP9M
MNuYIbUfBIioriwijcOPtoW8dLS2YFhQQHuwJiEzRaDJZ4qyTEybj9Yh8JKk92YR
5npjD8xP0/tjJbirhJuIko+oI6Up66KTe5HU1qmHn/3aQhWs4O8hUkTUAtkiyz4P
OMBYMEht3hCw0vilORKc0MMqyCWGOErjVf2szy10txgwhsWaA5ITZVLO02cqm0+Y
gzRT1aeeNSOY+DmytD5cu14qC8NTAa4l0dfX/k4ijlhAHWnNMOgaezC6+xKPzjx5
enCuyq8dBVLQK9vohPd9sOc/pw1LU4rUau9tq8BfWPoiaMNBXfJIWE2/gUHSA+hU
AQIDAQAB
-----END PUBLIC KEY-----
"""


def get_fingerprint() -> str:
    """Jedinstveni ID računara (os + host + korisnik)."""
    uname = os.name
    host = os.getenv("COMPUTERNAME") or os.getenv("HOSTNAME") or ""
    try:
        user = getpass.getuser()
    except Exception:
        user = os.getenv("USERNAME") or os.getenv("USER") or ""
    ident = f"{uname}|{host}|{user}"
    return hashlib.sha256(ident.encode("utf-8")).hexdigest()


class LicenseManager:
    """Upravlja validacijom licence (bez posebnog public_key.pem)."""

    def __init__(self, db: Database):
        self.db = db

    def load(self) -> Optional[str]:
        """Učitava license.json iz baze."""
        lic_json, _ = self.db.get_license()
        return lic_json

    def save(self, license_json: str):
        """Sprema licencu u bazu (public_key se više ne koristi)."""
        self.db.save_license(license_json, "")  # samo JSON
        log.info("Licenca je sačuvana u bazu.")

    def _verify_signature(self, lic: dict, signature_hex: str) -> bool:
        try:
            signature = bytes.fromhex(signature_hex)
        except ValueError:
            log.error("Potpis nije validan hex.")
            return False

        try:
            payload = json.dumps(
                {k: v for k, v in lic.items() if k != "signature"},
                sort_keys=True,
                ensure_ascii=False,
            ).encode("utf-8")
        except Exception as e:
            log.error(f"Greška pri pripremi podataka za provjeru potpisa: {e}")
            return False

        try:
            pub = serialization.load_pem_public_key(PUBLIC_KEY_PEM.encode("utf-8"))
            pub.verify(signature, payload, padding.PKCS1v15(), hashes.SHA256())
            return True
        except Exception as e:
            log.error(f"Potpis nije validan: {e}")
            return False

    def validate(self) -> bool:
        license_json = self.load()
        if not license_json:
            log.error("Licenca nije učitana. (Nema license.json u bazi.)")
            return False

        try:
            lic = json.loads(license_json)
        except Exception as e:
            log.error(f"Greška: license.json nije validan JSON ({e})")
            return False

        signature = lic.get("signature")
        if not signature:
            log.error("Nedostaje 'signature' u licenci.")
            return False

        # ✅ Provjera potpisa
        if not self._verify_signature(lic, signature):
            return False

        # ✅ Provjera fingerprinta
        real_fp = get_fingerprint()
        if lic.get("fingerprint") != real_fp:
            log.error("Fingerprint se ne poklapa sa ovim računarom.")
            return False

        # ✅ Provjera isteka
        exp = lic.get("expires_at")
        if exp:
            try:
                if datetime.fromisoformat(exp) < datetime.now():
                    log.error("Licenca je istekla.")
                    return False
            except Exception:
                log.error("Polje 'expires_at' nije validan ISO datetime.")
                return False

        log.info("Licenca je validna.")
        return True

    def ensure_valid_or_exit(self):
        if not self.validate():
            raise SystemExit("❌ Licenca nije validna. Uvezite license.json u Podešavanja ▸ Licenca.")
