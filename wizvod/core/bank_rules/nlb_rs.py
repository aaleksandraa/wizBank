import re
from typing import Optional

def extract_account_number(text: str, subject: str, filename: str) -> Optional[str]:
    m = re.search(r"partiju\s+([0-9\-]+)", subject or "", re.IGNORECASE)
    if m:
        return m.group(1)
    for src in [subject or "", text or "", filename or ""]:
        m = re.search(r"\b(\d{16})\b", src)
        if m: return m.group(1)
    return None

def extract_statement_number(text: str) -> Optional[str]:
    m = re.search(r"Customer advice number[: ]+(\d{1,6})(?!\.)", text or "", re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"\bIzvod[: ]+(\d{1,6})(?!\.)", text or "", re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"IZVOD\s+broj[: ]+(\d{1,6})(?!\.)", text or "", re.IGNORECASE)
    if m:
        return m.group(1)
    return None
