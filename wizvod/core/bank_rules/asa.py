import re
def extract_statement_number(text: str):
    m = re.search(r"IZVOD\s*(?:BROJ)?[: ]*(\d+)", text or "", re.IGNORECASE)
    return m.group(1) if m else None
def extract_account_number(text: str, subject: str, filename: str):
    m = re.search(r"Ra[cč]un[: ]*([0-9\-]+)", text or "", re.IGNORECASE)
    if m: return m.group(1)
    m = re.search(r"([0-9]{8,})", filename or "")
    return m.group(1) if m else None
