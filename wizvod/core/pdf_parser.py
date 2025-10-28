"""
PDF Parser za bankovne izvode.

Koristi modularni bank_rules sistem za parsiranje specifičnih banaka.
"""

import fitz  # PyMuPDF
import re
from typing import Optional, Tuple
from wizvod.core.bank_rules import extract_statement_number, extract_account_number


def _normalize_spaces(s: str) -> str:
    """
    Normalizuje whitespace u tekstu (zamjenjuje višestruke razmake sa jednim).

    Args:
        s: Ulazni string

    Returns:
        Normalizovani string
    """
    return re.sub(r"[ \t]+", " ", s or "")


class PDFParser:
    """Parser za bankovne izvode u PDF formatu."""

    def read_text_from_pdf_bytes(self, pdf_bytes: bytes) -> str:
        """
        Čita tekst iz PDF-a koji je dat kao bytes.

        Args:
            pdf_bytes: PDF sadržaj kao bytes

        Returns:
            Ekstraktovani tekst iz svih stranica

        Raises:
            ValueError: Ako PDF ne može biti pročitan
        """
        text = ""
        try:
            with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                for page in doc:
                    page_text = page.get_text("text") or ""
                    text += page_text + "\n"
        except Exception as e:
            raise ValueError(f"Greška pri čitanju PDF-a: {e}")

        return _normalize_spaces(text)

    def extract_all(
            self,
            sender_email: str,
            subject: str,
            filename: str,
            text: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Ekstrahuje broj računa i broj izvoda iz PDF-a.

        Koristi tvoj modularni bank_rules sistem koji automatski 
        bira pravi parser na osnovu sender_email-a.

        Args:
            sender_email: Email pošiljaoca (banka)
            subject: Subject email-a
            filename: Ime PDF fajla
            text: Ekstraktovani tekst iz PDF-a

        Returns:
            Tuple (account_number, statement_number)

        Primjer:
            >>> parser = PDFParser()
            >>> text = parser.read_text_from_pdf_bytes(pdf_content)
            >>> account, statement = parser.extract_all(
            ...     "homebank@nlb-rs.ba",
            ...     "Izvod broj 123",
            ...     "izvod_123.pdf",
            ...     text
            ... )
            >>> print(f"Račun: {account}, Izvod: {statement}")
        """
        # Koristi tvoj modularni bank_rules sistem
        # On automatski bira parser na osnovu sender_email-a
        stmt_no = extract_statement_number(sender_email, text)
        acct = extract_account_number(sender_email, text, subject, filename)

        # Fallback za broj računa ako bank_rules nije našao
        if not acct:
            acct = self._fallback_extract_account(subject, text, filename)

        # Fallback za broj izvoda ako bank_rules nije našao
        if not stmt_no:
            stmt_no = self._fallback_extract_statement(text)

        return acct, stmt_no

    def _fallback_extract_account(
            self,
            subject: str,
            text: str,
            filename: str
    ) -> Optional[str]:
        """
        Generički fallback za broj računa kada bank_rules ne uspije.

        Traži:
        - 16-cifreni broj: 5676510000114506
        - Format sa crticama: 567-651-00001145-06
        - Drugi format: 567-65100001145

        Args:
            subject: Subject emaila
            text: Tekst iz PDF-a
            filename: Ime fajla

        Returns:
            Broj računa ili None
        """
        sources = [text, subject, filename]

        for source in sources:
            if not source:
                continue

            # 16-cifreni račun
            m = re.search(r"\b(\d{16})\b", source)
            if m:
                return m.group(1)

            # Format: 567-651-00001145-06
            m = re.search(r"\b(\d{3}-\d{3}-\d{8}-\d{2})\b", source)
            if m:
                return m.group(1)

            # Format: 567-65100001145
            m = re.search(r"\b(\d{3}-\d{8,})\b", source)
            if m:
                return m.group(1)

        # Dodatna pretraga u početku PDF-a (često je račun na vrhu)
        if text:
            head = "\n".join(text.splitlines()[:100])
            patterns = [
                r"Ra[čc]un[:\s]+(\d{16})",
                r"Ra[čc]un[:\s]+(\d{3}-\d{3}-\d{8}-\d{2})",
                r"Account[:\s]+(\d{16})",
                r"Konto[:\s]+(\d{16})",
                r"IBAN[:\s]*BA\d+\s*(\d{16})",  # IBAN format
            ]

            for pat in patterns:
                m = re.search(pat, head, re.IGNORECASE)
                if m:
                    return m.group(1)

        return None

    def _fallback_extract_statement(self, text: str) -> Optional[str]:
        """
        Generički fallback za broj izvoda kada bank_rules ne uspije.

        Traži na početku dokumenta (prvih 60 linija).

        Args:
            text: Tekst iz PDF-a

        Returns:
            Broj izvoda ili None
        """
        if not text:
            return None

        head = "\n".join(text.splitlines()[:60])

        patterns = [
            r"Izvod\s+broj[:\s]+(\d{1,6})(?!\d)",
            r"IZVOD\s+(?:BROJ|BR)[:\.\s]+(\d{1,6})(?!\d)",
            r"Statement\s+(?:No|Number)[:\.\s]+(\d{1,6})(?!\d)",
            r"Kontoauszug\s+Nr[:\.\s]+(\d{1,6})(?!\d)",  # Sparkasse (njemački)
            r"IZVOD[^0-9]{0,10}(\d{1,6})(?!\d)",
        ]

        for pat in patterns:
            m = re.search(pat, head, re.IGNORECASE)
            if m:
                stmt = m.group(1)
                # Filtriraj sumnjive rezultate (npr. godine 2024)
                if len(stmt) <= 6 and not stmt.startswith("20"):
                    return stmt

        return None

    def extract_date(self, text: str) -> Optional[str]:
        """
        Pokušava ekstraktovati datum izvoda.

        Args:
            text: Tekst iz PDF-a

        Returns:
            Datum u formatu YYYY-MM-DD ili None

        Primjer:
            >>> parser.extract_date(text)
            '2024-12-31'
        """
        if not text:
            return None

        head = "\n".join(text.splitlines()[:40])

        # Format: 31.12.2024, 31/12/2024, 31-12-2024
        patterns = [
            r"Datum[:\s]+(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})",
            r"Date[:\s]+(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})",
            r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})",
        ]

        for pat in patterns:
            m = re.search(pat, head, re.IGNORECASE)
            if m:
                day, month, year = m.groups()
                try:
                    # Validacija datuma
                    d = int(day)
                    mo = int(month)
                    y = int(year)
                    if 1 <= d <= 31 and 1 <= mo <= 12 and 2000 <= y <= 2100:
                        return f"{y:04d}-{mo:02d}-{d:02d}"
                except ValueError:
                    continue

        return None

    def extract_balance(self, text: str) -> Optional[float]:
        """
        Pokušava ekstraktovati krajnji balans (saldo).

        Args:
            text: Tekst iz PDF-a

        Returns:
            Balans kao float ili None

        Primjer:
            >>> parser.extract_balance(text)
            12345.67
        """
        if not text:
            return None

        # Traži u poslednjih 50 linija (često je saldo na kraju)
        tail = "\n".join(text.splitlines()[-50:])

        patterns = [
            r"Saldo[:\s]+([0-9.,]+)",
            r"Balance[:\s]+([0-9.,]+)",
            r"Stanje[:\s]+([0-9.,]+)",
            r"Novo stanje[:\s]+([0-9.,]+)",
            r"Ending Balance[:\s]+([0-9.,]+)",
        ]

        for pat in patterns:
            m = re.search(pat, tail, re.IGNORECASE)
            if m:
                amount_str = m.group(1).replace(".", "").replace(",", ".")
                try:
                    return float(amount_str)
                except ValueError:
                    continue

        return None

    def extract_currency(self, text: str) -> str:
        """
        Detektuje valutu izvoda.

        Args:
            text: Tekst iz PDF-a

        Returns:
            Kod valute (BAM, EUR, USD...) ili 'BAM' kao default

        Primjer:
            >>> parser.extract_currency(text)
            'BAM'
        """
        if not text:
            return "BAM"

        head = "\n".join(text.splitlines()[:50])

        # Najčešće valute u BiH
        currencies = ["BAM", "EUR", "USD", "CHF", "GBP", "RSD"]

        for curr in currencies:
            if re.search(rf"\b{curr}\b", head, re.IGNORECASE):
                return curr.upper()

        # Default za BiH
        return "BAM"

    def get_metadata(self, text: str) -> dict:
        """
        Ekstrahuje sve dostupne metapodatke iz PDF-a.

        Args:
            text: Tekst iz PDF-a

        Returns:
            Dictionary sa metapodacima

        Primjer:
            >>> metadata = parser.get_metadata(text)
            >>> print(metadata)
            {
                'date': '2024-12-31',
                'balance': 12345.67,
                'currency': 'BAM'
            }
        """
        return {
            'date': self.extract_date(text),
            'balance': self.extract_balance(text),
            'currency': self.extract_currency(text)
        }