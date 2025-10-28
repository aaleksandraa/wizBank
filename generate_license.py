# ============================================================
# 🔐 WIZVOD License Generator
# ============================================================
import json
from datetime import datetime, timedelta
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes


BASE_DIR = Path(__file__).parent


# ------------------------------------------------------------
# 1️⃣ GENERISANJE NOVIH RSA KLJUČEVA (radiš SAMO JEDNOM!)
# ------------------------------------------------------------
def generate_keys():
    """Generiši novi par RSA ključeva (2048-bit)."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    with open(BASE_DIR / "private_key.pem", "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ))

    with open(BASE_DIR / "public_key.pem", "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ))

    print("✅ Ključevi su generisani: private_key.pem + public_key.pem")
    print("⚠️  private_key.pem čuvaj SAMO za sebe (ne šalji nikome).")


# ------------------------------------------------------------
# 2️⃣ GENERISANJE LICENCE ZA KLIJENTA
# ------------------------------------------------------------
def generate_license(fingerprint: str, holder: str, plan="Pro", valid_days=365):
    """Generiši license.json fajl za konkretnog klijenta."""
    priv_key_path = BASE_DIR / "private_key.pem"
    if not priv_key_path.exists():
        print("❌ Greška: nema private_key.pem — prvo pokreni opciju 1.")
        return

    private_key = serialization.load_pem_private_key(
        priv_key_path.read_bytes(),
        password=None
    )

    license_data = {
        "fingerprint": fingerprint.strip(),
        "holder": holder.strip(),
        "plan": plan,
        "issued_at": datetime.now().isoformat(timespec="seconds"),
        "expires_at": (datetime.now() + timedelta(days=valid_days)).isoformat(timespec="seconds"),
    }

    # JSON bez potpisa
    payload = json.dumps(license_data, sort_keys=True, ensure_ascii=False).encode("utf-8")

    # Digitalni potpis privatnim ključem
    signature = private_key.sign(payload, padding.PKCS1v15(), hashes.SHA256())
    license_data["signature"] = signature.hex()

    filename = f"license_{holder.replace(' ', '_')}.json"
    path = BASE_DIR / filename
    path.write_text(json.dumps(license_data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"✅ Licenca je kreirana: {filename}")
    print(f"📅 Važi do: {license_data['expires_at']}")
    print(f"👤 Klijent: {holder}")
    print(f"🧩 Fingerprint: {fingerprint[:16]}...")


# ------------------------------------------------------------
# 3️⃣ GLAVNI MENI
# ------------------------------------------------------------
if __name__ == "__main__":
    print("=== WIZVOD LICENSE GENERATOR ===")
    print("1. Generiši nove RSA ključeve")
    print("2. Kreiraj licencu za klijenta")

    izbor = input("Odaberi opciju (1/2): ").strip()

    if izbor == "1":
        generate_keys()
    elif izbor == "2":
        fp = input("Unesi fingerprint klijenta: ").strip()
        holder = input("Unesi ime firme/korisnika: ").strip()
        plan = input("Plan (default 'Pro'): ").strip() or "Pro"
        days = input("Broj dana važenja (default 365): ").strip()
        valid_days = int(days) if days.isdigit() else 365
        generate_license(fp, holder, plan, valid_days)
    else:
        print("❌ Nepoznata opcija.")
