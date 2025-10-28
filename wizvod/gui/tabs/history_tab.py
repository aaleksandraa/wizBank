"""
Napredni tab za prikaz istorije sinhronizacija sa opcijama štampanja.
"""
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from pathlib import Path
from typing import Optional
import threading

from wizvod.core.db import Database
from wizvod.core.sync_sessions import SyncSessionManager
from wizvod.core.pdf_printer import PDFPrinter
from wizvod.core.logger import get_logger
from wizvod.gui.themes.theme_manager import theme

log = get_logger("history")


class HistoryTab:
    """Tab za prikaz istorije sinhronizacija i štampanje."""

    def __init__(self, parent, db: Database):
        self.db = db
        self.session_manager = SyncSessionManager(db)
        self.printer = PDFPrinter()
        self.colors = theme.colors
        self.selected_session = None

        # Glavni okvir
        self.frame = ctk.CTkFrame(parent, fg_color=self.colors["background"])
        self.frame.pack(fill="both", expand=True, padx=25, pady=25)

        # === HEADER ===
        header = ctk.CTkFrame(self.frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))

        title = ctk.CTkLabel(
            header,
            text="📜 Istorija sinhronizacija",
            font=theme.get_font("title"),
            text_color=self.colors["text"]
        )
        title.pack(side="left", padx=5)

        subtitle = ctk.CTkLabel(
            header,
            text="Pregled i štampanje preuzetih izvoda",
            font=theme.get_font("body"),
            text_color=self.colors["text_secondary"]
        )
        subtitle.pack(side="left", padx=10)

        # === TOOLBAR ===
        toolbar = ctk.CTkFrame(self.frame, fg_color=self.colors["surface"], corner_radius=10)
        toolbar.pack(fill="x", pady=(0, 15))

        toolbar_inner = ctk.CTkFrame(toolbar, fg_color="transparent")
        toolbar_inner.pack(fill="x", padx=15, pady=12)

        ctk.CTkButton(
            toolbar_inner,
            text="🔄 Osvježi",
            width=120,
            height=36,
            fg_color=self.colors["primary"],
            hover_color=self.colors["primary_hover"],
            command=self.refresh_sessions
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            toolbar_inner,
            text="🖨️ Štampaj sve iz sesije",
            width=180,
            height=36,
            fg_color=self.colors["purple"],
            hover_color=self.colors["purple_hover"],
            command=self.print_selected_session
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            toolbar_inner,
            text="📄 Kreiraj izvještaj",
            width=160,
            height=36,
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
            command=self.create_report
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            toolbar_inner,
            text="🗑️ Obriši sesiju",
            width=140,
            height=36,
            fg_color=self.colors["error"],
            hover_color="#991b1b",
            command=self.delete_selected_session
        ).pack(side="left", padx=5)

        # Status label
        self.status_label = ctk.CTkLabel(
            toolbar_inner,
            text="",
            font=theme.get_font("body"),
            text_color=self.colors["text_secondary"]
        )
        self.status_label.pack(side="right", padx=10)

        # === DVODELNI PRIKAZ ===
        content = ctk.CTkFrame(self.frame, fg_color="transparent")
        content.pack(fill="both", expand=True)

        # LEVO: Lista sesija
        left_panel = ctk.CTkFrame(content, fg_color=self.colors["surface"], corner_radius=10)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))

        ctk.CTkLabel(
            left_panel,
            text="📅 Sesije sinhronizacije",
            font=theme.get_font("subtitle"),
            text_color=self.colors["text"]
        ).pack(anchor="w", padx=15, pady=(15, 10))

        self.sessions_scroll = ctk.CTkScrollableFrame(
            left_panel,
            fg_color=self.colors["background"]
        )
        self.sessions_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # DESNO: Detalji sesije
        right_panel = ctk.CTkFrame(content, fg_color=self.colors["surface"], corner_radius=10)
        right_panel.pack(side="right", fill="both", expand=True, padx=(10, 0))

        details_header = ctk.CTkFrame(right_panel, fg_color="transparent")
        details_header.pack(fill="x", padx=15, pady=(15, 10))

        self.details_title = ctk.CTkLabel(
            details_header,
            text="📋 Detalji sesije",
            font=theme.get_font("subtitle"),
            text_color=self.colors["text"]
        )
        self.details_title.pack(side="left")

        self.details_scroll = ctk.CTkScrollableFrame(
            right_panel,
            fg_color=self.colors["background"]
        )
        self.details_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # === FOOTER INFO ===
        footer = ctk.CTkFrame(self.frame, fg_color=self.colors["surface"], corner_radius=10)
        footer.pack(fill="x", pady=(15, 0))

        printer_info = f"🖨️ Štampač: {self.printer.default_printer or 'Nije pronađen'}"
        ctk.CTkLabel(
            footer,
            text=printer_info,
            font=theme.get_font("body"),
            text_color=self.colors["text_secondary"]
        ).pack(pady=12)

        # Inicijalno punjenje
        self.refresh_sessions()

    # =====================================================
    # SESIJE
    # =====================================================
    def refresh_sessions(self):
        """Osvježava prikaz sesija."""
        for widget in self.sessions_scroll.winfo_children():
            widget.destroy()

        sessions = self.session_manager.get_sessions(limit=100)

        if not sessions:
            ctk.CTkLabel(
                self.sessions_scroll,
                text="Nema sinhronizacija u istoriji.",
                text_color=self.colors["text_secondary"]
            ).pack(pady=20)
            return

        for session in sessions:
            self._render_session_card(session)

        self.status_label.configure(text=f"Prikazano: {len(sessions)} sesija")

    def _render_session_card(self, session: dict):
        """Renderuje karticu sesije."""
        card = ctk.CTkFrame(
            self.sessions_scroll,
            fg_color="#ffffff",
            corner_radius=8
        )
        card.pack(fill="x", pady=6, padx=5)

        # Status boja
        status_colors = {
            'completed': self.colors["success"],
            'error': self.colors["error"],
            'running': self.colors["primary"]
        }
        status_color = status_colors.get(session['status'], self.colors["text_secondary"])

        # Header sa datumom
        started = session['started_at']
        try:
            dt = datetime.fromisoformat(started)
            date_str = dt.strftime('%d.%m.%Y %H:%M:%S')
        except:
            date_str = started

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 5))

        ctk.CTkLabel(
            header,
            text=f"🕐 {date_str}",
            font=theme.get_font("body_bold"),
            text_color=self.colors["text"]
        ).pack(side="left")

        # Status badge
        status_text = {
            'completed': '✓ Završeno',
            'error': '✗ Greška',
            'running': '⟳ U toku'
        }.get(session['status'], session['status'])

        ctk.CTkLabel(
            header,
            text=status_text,
            font=theme.get_font("small"),
            text_color=status_color
        ).pack(side="right")

        # Statistika
        stats_text = (
            f"📥 Preuzeto: {session['total_downloaded']} | "
            f"⊘ Preskočeno: {session['total_skipped']} | "
            f"✗ Greške: {session['total_errors']}"
        )

        ctk.CTkLabel(
            card,
            text=stats_text,
            font=theme.get_font("small"),
            text_color=self.colors["text_secondary"]
        ).pack(anchor="w", padx=12, pady=(0, 5))

        # Session ID (manje)
        ctk.CTkLabel(
            card,
            text=f"ID: {session['session_id']}",
            font=theme.get_font("small"),
            text_color=self.colors["text_secondary"]
        ).pack(anchor="w", padx=12, pady=(0, 5))

        # Dugmad
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=(5, 10))

        ctk.CTkButton(
            btn_frame,
            text="👁️ Prikaži",
            width=100,
            height=32,
            fg_color=self.colors["primary"],
            hover_color=self.colors["primary_hover"],
            command=lambda s=session: self.show_session_details(s)
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            btn_frame,
            text="🖨️ Štampaj",
            width=100,
            height=32,
            fg_color=self.colors["purple"],
            hover_color=self.colors["purple_hover"],
            command=lambda s=session: self.print_session(s)
        ).pack(side="left", padx=3)

    # =====================================================
    # DETALJI SESIJE
    # =====================================================
    def show_session_details(self, session: dict):
        """Prikazuje detalje odabrane sesije."""
        self.selected_session = session

        # Očisti prethodni prikaz
        for widget in self.details_scroll.winfo_children():
            widget.destroy()

        # Header
        self.details_title.configure(
            text=f"📋 Sesija: {session['session_id']}"
        )

        # Dobavi logove za ovu sesiju
        logs = self.session_manager.get_session_logs(session['session_id'])

        if not logs:
            ctk.CTkLabel(
                self.details_scroll,
                text="Nema logova za ovu sesiju.",
                text_color=self.colors["text_secondary"]
            ).pack(pady=20)
            return

        # Renderuj svaki log
        for i, log_entry in enumerate(logs, 1):
            self._render_log_card(log_entry, i)

    def _render_log_card(self, log_entry: dict, index: int):
        """Renderuje karticu pojedinačnog loga."""
        card = ctk.CTkFrame(
            self.details_scroll,
            fg_color="#ffffff",
            corner_radius=8
        )
        card.pack(fill="x", pady=5, padx=5)

        # Status ikona
        status_icons = {
            'ok': '✅',
            'error': '❌',
            'skipped': '⊘'
        }
        status_icon = status_icons.get(log_entry['status'], '•')

        # Informacije
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.pack(fill="x", padx=12, pady=10)

        # Broj i klijent
        ctk.CTkLabel(
            info_frame,
            text=f"{index}. {status_icon} {log_entry['client_name']}",
            font=theme.get_font("body_bold"),
            text_color=self.colors["text"]
        ).pack(anchor="w")

        # Broj izvoda
        if log_entry.get('statement_number'):
            ctk.CTkLabel(
                info_frame,
                text=f"📄 Izvod broj: {log_entry['statement_number']}",
                font=theme.get_font("small"),
                text_color=self.colors["text_secondary"]
            ).pack(anchor="w", pady=(2, 0))

        # Putanja
        if log_entry.get('file_path'):
            file_path = log_entry['file_path']
            file_name = Path(file_path).name if Path(file_path).exists() else file_path

            ctk.CTkLabel(
                info_frame,
                text=f"📁 {file_name}",
                font=theme.get_font("small"),
                text_color=self.colors["text_secondary"]
            ).pack(anchor="w", pady=(2, 0))

        # Poruka/greška
        if log_entry.get('message'):
            msg_color = self.colors["error"] if log_entry['status'] == 'error' else self.colors["text_secondary"]
            ctk.CTkLabel(
                info_frame,
                text=f"ℹ️ {log_entry['message'][:100]}",
                font=theme.get_font("small"),
                text_color=msg_color,
                wraplength=400
            ).pack(anchor="w", pady=(2, 0))

        # Dugmad za pojedinačne akcije
        if log_entry['status'] == 'ok' and log_entry.get('file_path'):
            file_path = log_entry['file_path']
            if Path(file_path).exists():
                btn_frame = ctk.CTkFrame(card, fg_color="transparent")
                btn_frame.pack(fill="x", padx=12, pady=(5, 10))

                ctk.CTkButton(
                    btn_frame,
                    text="🖨️ Štampaj",
                    width=90,
                    height=28,
                    fg_color=self.colors["purple"],
                    hover_color=self.colors["purple_hover"],
                    command=lambda p=file_path: self.print_single_file(p)
                ).pack(side="left", padx=3)

                ctk.CTkButton(
                    btn_frame,
                    text="📂 Otvori",
                    width=90,
                    height=28,
                    fg_color=self.colors["accent"],
                    hover_color=self.colors["accent_hover"],
                    command=lambda p=file_path: self.open_file(p)
                ).pack(side="left", padx=3)

    # =====================================================
    # AKCIJE
    # =====================================================
    def print_selected_session(self):
        """Štampa sve izvode iz selektovane sesije."""
        if not self.selected_session:
            messagebox.showwarning(
                "Upozorenje",
                "Prvo odaberite sesiju iz liste."
            )
            return

        self.print_session(self.selected_session)

    def print_session(self, session: dict):
        """Štampa sve izvode iz sesije."""
        if not self.printer.default_printer:
            messagebox.showerror(
                "Greška",
                "Nije pronađen nijedan štampač u sistemu."
            )
            return

        confirm = messagebox.askyesno(
            "Potvrda",
            f"Štampati sve izvode iz sesije?\n\n"
            f"Sesija: {session['session_id']}\n"
            f"Preuzeto izvoda: {session['total_downloaded']}\n"
            f"Štampač: {self.printer.default_printer}"
        )

        if not confirm:
            return

        self.status_label.configure(text="⏳ Štampanje u toku...", text_color=self.colors["primary"])

        def print_worker():
            try:
                logs = self.session_manager.get_session_logs(session['session_id'])
                count = self.printer.print_session(logs)

                self.frame.after(100, lambda: self._on_print_complete(count, len(logs)))
            except Exception as e:
                log.error(f"Greška pri štampanju: {e}")
                self.frame.after(100, lambda: messagebox.showerror("Greška", f"Greška pri štampanju:\n{e}"))
                self.frame.after(100,
                                 lambda: self.status_label.configure(text="", text_color=self.colors["text_secondary"]))

        threading.Thread(target=print_worker, daemon=True).start()

    def _on_print_complete(self, printed: int, total: int):
        """Callback nakon završenog štampanja."""
        self.status_label.configure(
            text=f"✅ Odštampano: {printed}/{total}",
            text_color=self.colors["success"]
        )
        messagebox.showinfo(
            "Štampanje završeno",
            f"Uspješno poslato na štampač:\n{printed} od {total} dokumenata"
        )

    def print_single_file(self, file_path: str):
        """Štampa jedan PDF fajl."""
        if not self.printer.default_printer:
            messagebox.showerror("Greška", "Nije pronađen štampač.")
            return

        confirm = messagebox.askyesno(
            "Potvrda",
            f"Štampati dokument?\n\n{Path(file_path).name}"
        )

        if not confirm:
            return

        success = self.printer.print_pdf(file_path)

        if success:
            messagebox.showinfo("Uspjeh", "Dokument poslat na štampač.")
        else:
            messagebox.showerror("Greška", "Neuspješno štampanje.")

    def open_file(self, file_path: str):
        """Otvara PDF fajl u default čitaču."""
        try:
            import os
            os.startfile(file_path)
        except Exception as e:
            log.error(f"Greška pri otvaranju fajla: {e}")
            messagebox.showerror("Greška", f"Ne mogu otvoriti fajl:\n{e}")

    def create_report(self):
        """Kreira PDF izvještaj o sesiji."""
        if not self.selected_session:
            messagebox.showwarning("Upozorenje", "Prvo odaberite sesiju.")
            return

        self.status_label.configure(text="⏳ Kreiram izvještaj...", text_color=self.colors["primary"])

        def report_worker():
            try:
                logs = self.session_manager.get_session_logs(self.selected_session['session_id'])
                report_path = self.printer.create_print_summary(logs)

                if report_path:
                    self.frame.after(100, lambda: self._on_report_created(report_path))
                else:
                    self.frame.after(100, lambda: messagebox.showwarning(
                        "Upozorenje",
                        "Nije moguće kreirati izvještaj.\nInstalirati reportlab: pip install reportlab"
                    ))
                    self.frame.after(100, lambda: self.status_label.configure(text=""))
            except Exception as e:
                log.error(f"Greška pri kreiranju izvještaja: {e}")
                self.frame.after(100, lambda: messagebox.showerror("Greška", str(e)))
                self.frame.after(100, lambda: self.status_label.configure(text=""))

        threading.Thread(target=report_worker, daemon=True).start()

    def _on_report_created(self, report_path: str):
        """Callback nakon kreiranja izvještaja."""
        self.status_label.configure(text="✅ Izvještaj kreiran", text_color=self.colors["success"])

        result = messagebox.askyesnocancel(
            "Izvještaj kreiran",
            f"Izvještaj je sačuvan:\n{report_path}\n\n"
            f"Otvoriti izvještaj?"
        )

        if result:
            self.open_file(report_path)

    def delete_selected_session(self):
        """Briše odabranu sesiju."""
        if not self.selected_session:
            messagebox.showwarning("Upozorenje", "Prvo odaberite sesiju.")
            return

        confirm = messagebox.askyesno(
            "Potvrda brisanja",
            f"Obrisati sesiju i sve njene logove?\n\n"
            f"Sesija: {self.selected_session['session_id']}\n"
            f"Datum: {self.selected_session['started_at']}\n\n"
            f"Ova akcija je nepovratna!"
        )

        if not confirm:
            return

        try:
            self.session_manager.delete_session(self.selected_session['session_id'])
            messagebox.showinfo("Uspjeh", "Sesija je obrisana.")
            self.selected_session = None
            self.refresh_sessions()

            # Očisti detalje
            for widget in self.details_scroll.winfo_children():
                widget.destroy()
            self.details_title.configure(text="📋 Detalji sesije")

        except Exception as e:
            log.error(f"Greška pri brisanju sesije: {e}")
            messagebox.showerror("Greška", str(e))