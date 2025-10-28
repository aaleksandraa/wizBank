import re
from typing import Optional

def extract_statement_number(text: str) -> Optional[str]:
    head = "\n".join((text or "").splitlines()[:60])
    for pat in [
        r"Izvod\s+broj[: ]+(\d{1,6})(?!\.)",
        r"IZVOD\s+BROJ[: ]+(\d{1,6})(?!\.)",
        r"IZVOD[^0-9]{0,10}(\d{1,6})(?!\.)"
    ]:
        m = re.search(pat, head, re.IGNORECASE)
        if m:
            return m.group(1)
    return None

def extract_account_number(text: str, subject: str, filename: str) -> Optional[str]:
    for source in [subject or "", text or "", filename or ""]:
        m = re.search(r"\b(\d{16})\b", source)
        if m: return m.group(1)
        m = re.search(r"\b(\d{3}-\d{3}-\d{8}-\d{2}|\d{3}-\d{8,})\b", source)
        if m: return m.group(1)
    return None
