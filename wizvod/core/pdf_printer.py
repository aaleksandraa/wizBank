"""
PDF Printer modul za Wizvod v2.1

OPTIMIZACIJE:
✅ Win32 API direktno štampanje (najsigurnije)
✅ SumatraPDF silent print
✅ GSPrint fallback (Ghostscript)
✅ Automatska detekcija i selekcija štampača
✅ Test štampanja
"""

import os
import sys
import subprocess
import tempfile
import time
from pathlib import Path
from typing import List, Optional
from wizvod.core.logger import get_logger

log = get_logger("pdf_printer")


class PDFPrinter:
    """Upravlja štampanjem PDF dokumenata."""

    def __init__(self, preferred_printer: Optional[str] = None):
        """
        Args:
            preferred_printer: Ime štampača (None = default)
        """
        self.default_printer = self._get_default_printer()
        self.preferred_printer = preferred_printer or self.default_printer
        log.info(f"PDF Printer inicijalizovan.")
        log.info(f"  Default štampač: {self.default_printer or 'Nije pronađen'}")
        log.info(f"  Koristi štampač: {self.preferred_printer or 'Nije pronađen'}")

    # ================================================================
    # DETEKCIJA ŠTAMPAČA
    # ================================================================
    def _get_default_printer(self) -> Optional[str]:
        """
        Dobija sistemski default štampač (Windows).

        Returns:
            Ime default štampača ili None
        """
        try:
            # Metoda 1: WMIC (Windows Management Instrumentation)
            result = subprocess.run(
                ["wmic", "printer", "where", "default=true", "get", "name"],
                capture_output=True,
                text=True,
                shell=False,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )

            lines = [l.strip() for l in result.stdout.splitlines() if l.strip() and l.strip() != "Name"]
            if lines:
                printer_name = lines[0]
                log.info(f"✅ Default štampač pronađen: {printer_name}")
                return printer_name

            # Metoda 2: PowerShell
            ps_cmd = "Get-WmiObject -Query \"SELECT * FROM Win32_Printer WHERE Default=$true\" | Select-Object -ExpandProperty Name"
            result = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                shell=False,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )

            name = result.stdout.strip()
            if name:
                log.info(f"✅ Default štampač pronađen (PS): {name}")
                return name

        except Exception as e:
            log.warning(f"⚠️ Ne mogu pronaći default štampač: {e}")

        # Fallback: uzmi prvi dostupni
        printers = self.get_available_printers()
        if printers:
            log.info(f"ℹ️ Koristim prvi dostupni štampač: {printers[0]}")
            return printers[0]

        return None

    def get_available_printers(self) -> List[str]:
        """
        Vraća listu svih dostupnih štampača.

        Returns:
            Lista imena štampača
        """
        printers = []

        try:
            # WMIC metoda
            result = subprocess.run(
                ["wmic", "printer", "get", "name"],
                capture_output=True,
                text=True,
                shell=False,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )

            for line in result.stdout.splitlines():
                line = line.strip()
                if line and line != "Name" and not line.startswith("\\\\"):
                    printers.append(line)

            if printers:
                log.info(f"📋 Pronađeno štampača: {len(printers)}")
                return sorted(printers)

            # PowerShell fallback
            ps_cmd = "Get-WmiObject -Query \"SELECT * FROM Win32_Printer\" | Select-Object -ExpandProperty Name"
            result = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                shell=False,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )

            for line in result.stdout.splitlines():
                line = line.strip()
                if line and not line.startswith("\\\\"):
                    printers.append(line)

        except Exception as e:
            log.error(f"Greška pri dohvatanju štampača: {e}")

        return sorted(set(printers))

    def set_printer(self, printer_name: str):
        """Postavlja željeni štampač."""
        if printer_name in self.get_available_printers():
            self.preferred_printer = printer_name
            log.info(f"✅ Štampač postavljen: {printer_name}")
            return True
        else:
            log.warning(f"⚠️ Štampač ne postoji: {printer_name}")
            return False

    # ================================================================
    # ŠTAMPANJE
    # ================================================================
    def print_pdf(self, pdf_path: str, printer: Optional[str] = None) -> bool:
        """
        Štampa jedan PDF fajl.

        Pokušava po redoslijedu:
        1. Win32 API (najdirektnije)
        2. SumatraPDF (najbolji za silent)
        3. GSPrint (Ghostscript)
        4. Adobe Acrobat Reader
        5. Shell print (fallback)

        Args:
            pdf_path: Putanja do PDF fajla
            printer: Ime štampača (None = koristi preferred)

        Returns:
            True ako je uspješno, False inače
        """
        pdf_path = str(pdf_path)

        if not Path(pdf_path).exists():
            log.error(f"❌ Fajl ne postoji: {pdf_path}")
            return False

        printer_name = printer or self.preferred_printer

        if not printer_name:
            log.error("❌ Nije pronađen nijedan štampač")
            return False

        log.info(f"🖨️ Štampam: {Path(pdf_path).name}")
        log.info(f"   Štampač: {printer_name}")

        # METODA 1: Win32 API (NAJSIGURNIJA za Windows)
        if self._print_via_win32(pdf_path, printer_name):
            return True

        # METODA 2: SumatraPDF (najbolji za silent print)
        if self._print_via_sumatra(pdf_path, printer_name):
            return True

        # METODA 3: GSPrint (Ghostscript)
        if self._print_via_gsprint(pdf_path, printer_name):
            return True

        # METODA 4: Adobe Acrobat Reader
        if self._print_via_adobe(pdf_path, printer_name):
            return True

        # METODA 5: Shell print (ZADNJI FALLBACK)
        log.warning("⚠️ Koristim shell print fallback (može otvoriti UI)")
        return self._print_via_shell(pdf_path, printer_name)

    def _print_via_win32(self, pdf_path: str, printer: str) -> bool:
        """Štampa putem Win32 API (PyWin32)."""
        try:
            import win32api
            import win32print

            log.info("🔧 Pokušavam Win32 API metodu...")

            # Otvori PDF sa ShellExecute i pošalji na štampač
            result = win32api.ShellExecute(
                0,
                "printto",
                pdf_path,
                f'"{printer}"',
                ".",
                0  # SW_HIDE - ne pokazuj prozor
            )

            # ShellExecute vraća broj > 32 ako je uspješno
            if result > 32:
                log.info("✅ Win32 API štampanje uspješno")
                return True
            else:
                log.warning(f"⚠️ Win32 API vratilo kod: {result}")
                return False

        except ImportError:
            log.debug("ℹ️ PyWin32 nije instaliran (pip install pywin32)")
            return False
        except Exception as e:
            log.warning(f"⚠️ Win32 API greška: {e}")
            return False

    def _print_via_sumatra(self, pdf_path: str, printer: str) -> bool:
        """Štampa putem SumatraPDF (silent print)."""
        sumatra_paths = [
            r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
            r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
            Path.home() / "AppData" / "Local" / "SumatraPDF" / "SumatraPDF.exe"
        ]

        for sumatra in sumatra_paths:
            sumatra_str = str(sumatra)
            if Path(sumatra_str).exists():
                try:
                    log.info("🔧 Pokušavam SumatraPDF metodu...")

                    cmd = [
                        sumatra_str,
                        "-print-to", printer,
                        "-silent",  # Bez UI
                        pdf_path
                    ]

                    result = subprocess.run(
                        cmd,
                        shell=False,
                        timeout=30,
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    )

                    if result.returncode == 0:
                        log.info("✅ SumatraPDF štampanje uspješno")
                        return True
                    else:
                        log.warning(f"⚠️ SumatraPDF exit code: {result.returncode}")

                except Exception as e:
                    log.warning(f"⚠️ SumatraPDF greška: {e}")

        log.debug("ℹ️ SumatraPDF nije pronađen")
        return False

    def _print_via_gsprint(self, pdf_path: str, printer: str) -> bool:
        """Štampa putem GSPrint (Ghostscript)."""
        gsprint_paths = [
            r"C:\Program Files\Ghostgum\gsview\gsprint.exe",
            r"C:\Program Files (x86)\Ghostgum\gsview\gsprint.exe",
            r"C:\gs\gsprint.exe"
        ]

        for gsprint in gsprint_paths:
            if Path(gsprint).exists():
                try:
                    log.info("🔧 Pokušavam GSPrint metodu...")

                    cmd = [
                        gsprint,
                        "-printer", printer,
                        "-noquery",  # Bez dijaloga
                        pdf_path
                    ]

                    result = subprocess.run(
                        cmd,
                        shell=False,
                        timeout=30,
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    )

                    if result.returncode == 0:
                        log.info("✅ GSPrint štampanje uspješno")
                        return True

                except Exception as e:
                    log.warning(f"⚠️ GSPrint greška: {e}")

        log.debug("ℹ️ GSPrint nije pronađen")
        return False

    def _print_via_adobe(self, pdf_path: str, printer: str) -> bool:
        """Štampa putem Adobe Acrobat Reader."""
        acrobat_paths = [
            r"C:\Program Files\Adobe\Acrobat DC\Acrobat\Acrobat.exe",
            r"C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
            r"C:\Program Files\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
        ]

        for acrobat in acrobat_paths:
            if Path(acrobat).exists():
                try:
                    log.info("🔧 Pokušavam Adobe Reader metodu...")

                    # Adobe parametri:
                    # /t = print to printer
                    # /h = minimized
                    cmd = [acrobat, "/t", pdf_path, printer]

                    subprocess.Popen(
                        cmd,
                        shell=False,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    )

                    # Adobe zahtijeva malo vremena da se pokrene
                    time.sleep(2)

                    log.info("✅ Adobe Reader pozvan (async)")
                    return True

                except Exception as e:
                    log.warning(f"⚠️ Adobe greška: {e}")

        log.debug("ℹ️ Adobe Reader nije pronađen")
        return False

    def _print_via_shell(self, pdf_path: str, printer: str) -> bool:
        """Shell print fallback (može otvoriti UI)."""
        try:
            log.info("🔧 Pokušavam Windows shell print...")
            os.startfile(pdf_path, "print")
            log.warning("⚠️ Shell print pozvan (može pokazati UI)")
            return True
        except Exception as e:
            log.error(f"❌ Shell print greška: {e}")
            return False

    # ================================================================
    # GRUPNO ŠTAMPANJE
    # ================================================================
    def print_multiple(self, pdf_paths: List[str], printer: Optional[str] = None) -> int:
        """
        Štampa više PDF fajlova.

        Args:
            pdf_paths: Lista putanja do PDF fajlova
            printer: Ime štampača

        Returns:
            Broj uspješno odštampanih fajlova
        """
        if not pdf_paths:
            log.warning("⚠️ Nema fajlova za štampanje")
            return 0

        log.info(f"📄 Štampam {len(pdf_paths)} dokumenata...")

        success_count = 0
        for i, pdf_path in enumerate(pdf_paths, 1):
            log.info(f"  [{i}/{len(pdf_paths)}] {Path(pdf_path).name}")

            if self.print_pdf(pdf_path, printer):
                success_count += 1
                # Pauza između štampanja (prevenira overload)
                if i < len(pdf_paths):
                    time.sleep(1)

        log.info(f"✅ Odštampano: {success_count}/{len(pdf_paths)}")
        return success_count

    def print_session(self, session_logs: List[dict], printer: Optional[str] = None) -> int:
        """
        Štampa sve izvode iz jedne sesije sinhronizacije.

        Args:
            session_logs: Lista log zapisa iz sesije
            printer: Ime štampača

        Returns:
            Broj uspješno odštampanih dokumenata
        """
        pdf_files = []

        for log_entry in session_logs:
            if log_entry.get('status') == 'ok':
                file_path = log_entry.get('file_path')
                if file_path and Path(file_path).exists():
                    pdf_files.append(file_path)
                else:
                    log.warning(f"⚠️ Fajl ne postoji: {file_path}")

        if not pdf_files:
            log.warning("⚠️ Nema uspješno preuzetih izvoda za štampanje")
            return 0

        return self.print_multiple(pdf_files, printer)

    # ================================================================
    # TEST ŠTAMPANJA
    # ================================================================
    def test_print(self, printer: Optional[str] = None) -> bool:
        """
        Testira štampač sa test PDF-om.

        Args:
            printer: Ime štampača za testiranje

        Returns:
            True ako test uspije
        """
        printer_name = printer or self.preferred_printer

        if not printer_name:
            log.error("❌ Nema štampača za testiranje")
            return False

        log.info(f"🧪 Testiram štampač: {printer_name}")

        # Kreiraj test PDF
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4

            test_pdf = Path(tempfile.gettempdir()) / "wizvod_test_print.pdf"

            c = canvas.Canvas(str(test_pdf), pagesize=A4)
            c.setFont("Helvetica-Bold", 24)
            c.drawString(100, 750, "Wizvod - Test štampanja")
            c.setFont("Helvetica", 14)
            c.drawString(100, 720, f"Štampač: {printer_name}")
            c.drawString(100, 700, f"Datum: {time.strftime('%d.%m.%Y %H:%M:%S')}")
            c.drawString(100, 670, "Ako vidite ovu stranicu, štampač radi ispravno!")
            c.save()

            # Pokušaj štampati
            result = self.print_pdf(str(test_pdf), printer_name)

            # Obriši test fajl nakon 5 sekundi
            time.sleep(5)
            try:
                test_pdf.unlink()
            except:
                pass

            return result

        except ImportError:
            log.warning("⚠️ ReportLab nije instaliran (pip install reportlab)")
            return False
        except Exception as e:
            log.error(f"❌ Test greška: {e}")
            return False

    # ================================================================
    # IZVJEŠTAJ O SESIJI
    # ================================================================
    def create_print_summary(self, session_logs: List[dict], output_path: Optional[str] = None) -> Optional[str]:
        """
        Kreira PDF izvještaj o sesiji sinhronizacije.

        Args:
            session_logs: Lista logova
            output_path: Gdje sačuvati (None = temp folder)

        Returns:
            Putanja do kreiranog PDF-a ili None ako ne uspije
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from datetime import datetime

            if not output_path:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = Path(tempfile.gettempdir()) / f"wizvod_summary_{timestamp}.pdf"
            else:
                output_path = Path(output_path)

            doc = SimpleDocTemplate(str(output_path), pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()

            # Naslov
            title = Paragraph("<b>Izvještaj o sinhronizaciji</b>", styles['Title'])
            elements.append(title)
            elements.append(Spacer(1, 12))

            # Datum
            date_str = datetime.now().strftime('%d.%m.%Y %H:%M')
            date_text = Paragraph(f"Datum: {date_str}", styles['Normal'])
            elements.append(date_text)
            elements.append(Spacer(1, 20))

            # Tabela sa rezultatima
            data = [['#', 'Klijent', 'Broj izvoda', 'Status', 'Poruka']]

            for i, log in enumerate(session_logs, 1):
                status_icon = {
                    'ok': '✔',
                    'error': '✗',
                    'skipped': '○'
                }.get(log.get('status', ''), '•')

                client_name = (log.get('client_name') or '—')[:30]
                stmt_no = log.get('statement_number') or '—'
                message = (log.get('message') or '')[:40]

                data.append([
                    str(i),
                    client_name,
                    stmt_no,
                    status_icon,
                    message
                ])

            table = Table(data, colWidths=[30, 150, 80, 50, 200])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            elements.append(table)

            # Statistika
            elements.append(Spacer(1, 20))
            total = len(session_logs)
            ok = sum(1 for l in session_logs if l.get('status') == 'ok')
            errors = sum(1 for l in session_logs if l.get('status') == 'error')
            skipped = sum(1 for l in session_logs if l.get('status') == 'skipped')

            stats_text = Paragraph(
                f"<b>Ukupno:</b> {total} | <b>Uspješno:</b> {ok} | "
                f"<b>Greške:</b> {errors} | <b>Preskočeno:</b> {skipped}",
                styles['Normal']
            )
            elements.append(stats_text)

            # Generiši PDF
            doc.build(elements)
            log.info(f"📄 Kreiran izvještaj: {output_path}")
            return str(output_path)

        except ImportError:
            log.warning("⚠️ ReportLab nije instaliran. Instaliraj: pip install reportlab")
            return None
        except Exception as e:
            log.error(f"❌ Greška pri kreiranju izvještaja: {e}")
            return None