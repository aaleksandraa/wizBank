import re
from typing import Optional

def extract_statement_number(text: str) -> Optional[str]:
    m = re.search(r"Izvod za komitenta broj[: ]+(\d{1,6})(?!\.)", text or "", re.IGNORECASE)
    return m.group(1) if m else None

def extract_account_number(text: str, subject: str, filename: str) -> Optional[str]:
    for src in [filename or "", subject or "", text or ""]:
        m = re.search(r"\b(\d{16})\b", src)
        if m: return m.group(1)
    return None
