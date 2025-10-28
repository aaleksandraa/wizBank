import re

def extract_statement_number(text: str):
    """
    Izvlači broj izvoda iz Atos bank PDF-a.
    Primjeri:
      "IZVOD BR. 205"
      "Izvod br. 12"
    """
    m = re.search(r"\bIZVOD\s*BR\.?\s*(\d+)", text or "", re.IGNORECASE)
    return m.group(1) if m else None


def extract_account_number(text: str, subject: str, filename: str):
    """
    Izvlači broj računa (npr. 5675431100009685)
    Traži u subjectu, tekstu ili imenu fajla.
    """
    # pokušaj u subjectu
    m = re.search(r"(\d{8,})", subject or "")
    if m:
        return m.group(1)

    # pokušaj u tekstu PDF-a
    m = re.search(r"\b\d{8,}\b", text or "")
    if m:
        return m.group(1)

    # pokušaj u imenu fajla
    m = re.search(r"(\d{8,})", filename or "")
    if m:
        return m.group(1)

    return None
