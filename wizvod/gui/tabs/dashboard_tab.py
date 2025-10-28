import customtkinter as ctk
from tkinter import messagebox
import threading
import datetime
from wizvod.core.db import Database
from wizvod.worker import run_worker as run_once
from wizvod.core.logger import get_logger
from wizvod.gui.themes.theme_manager import theme

log = get_logger("dashboard")


class DashboardTab:
    def __init__(self, parent, db: Database):
        self.db = db
        self.is_syncing = False
        self.colors = theme.colors

        # Glavni okvir
        self.frame = ctk.CTkFrame(parent, fg_color=self.colors["background"])
        self.frame.pack(fill="both", expand=True, padx=25, pady=25)

        # === HEADER ===
        header = ctk.CTkFrame(self.frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 25))

        title = ctk.CTkLabel(
            header,
            text="Wizvod Dashboard",
            font=theme.get_font("title"),
            text_color=self.colors["text"]
        )
        title.pack(side="left", padx=10)

        subtitle = ctk.CTkLabel(
            header,
            text="Pregled aktivnosti i sinhronizacija",
            font=theme.get_font("body"),
            text_color=self.colors["text_secondary"]
        )
        subtitle.pack(side="left", padx=10)

        # === STAT KARTICE ===
        cards_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        cards_frame.pack(fill="x", pady=(0, 25))

        self.clients_card = self._create_stat_card(cards_frame, "Klijenti", "0")
        self.clients_card.pack(side="left", expand=True, padx=8)

        self.accounts_card = self._create_stat_card(cards_frame, "Email nalozi", "0")
        self.accounts_card.pack(side="left", expand=True, padx=8)

        self.today_card = self._create_stat_card(cards_frame, "Danas preuzetih", "0")
        self.today_card.pack(side="left", expand=True, padx=8)

        # === SINHRONIZACIJA ===
        sync_frame = ctk.CTkFrame(self.frame, fg_color=self.colors["surface"], corner_radius=12)
        sync_frame.pack(fill="x", pady=(0, 25))

        ctk.CTkLabel(
            sync_frame,
            text="🔄 Sinhronizacija",
            font=theme.get_font("subtitle"),
            text_color=self.colors["text"]
        ).pack(pady=(15, 10))

        # Dugmad
        btn_container = ctk.CTkFrame(sync_frame, fg_color="transparent")
        btn_container.pack(pady=(0, 20))

        self.sync_button = ctk.CTkButton(
            btn_container,
            text="🔄 Sinhronizuj sada",
            height=48,
            width=200,
            font=theme.get_font("body_bold"),
            fg_color=self.colors["primary"],
            hover_color=self.colors["primary_hover"],
            command=self.start_sync
        )
        self.sync_button.pack(side="left", padx=10)

        self.sync_print_button = ctk.CTkButton(
            btn_container,
            text="🖨️ Sinhronizuj i štampaj",
            height=48,
            width=220,
            font=theme.get_font("body_bold"),
            fg_color=self.colors["purple"],
            hover_color=self.colors["purple_hover"],
            command=self.start_sync_and_print
        )
        self.sync_print_button.pack(side="left", padx=10)

        # Info sekcija
        info_inner = ctk.CTkFrame(sync_frame, fg_color=self.colors["background"], corner_radius=10)
        info_inner.pack(fill="x", padx=20, pady=(0, 20))

        self.last_sync_label = ctk.CTkLabel(
            info_inner,
            text="⏱ Zadnja sinhronizacija: —",
            anchor="w",
            font=theme.get_font("body"),
            text_color=self.colors["text"]
        )
        self.last_sync_label.pack(fill="x", padx=15, pady=(10, 2))

        self.sync_status_label = ctk.CTkLabel(
            info_inner,
            text="Status: Čeka pokretanje...",
            anchor="w",
            font=theme.get_font("body"),
            text_color=self.colors["text_secondary"]
        )
        self.sync_status_label.pack(fill="x", padx=15, pady=(0, 10))

        # === LOGOVI ===
        self.recent_label = ctk.CTkLabel(
            self.frame,
            text="Zadnjih 15 logova",
            font=theme.get_font("subtitle"),
            text_color=self.colors["text"]
        )
        self.recent_label.pack(anchor="w", padx=5, pady=(10, 8))

        logs_container = ctk.CTkFrame(self.frame, fg_color=self.colors["surface"], corner_radius=10)
        logs_container.pack(fill="both", expand=True, padx=5, pady=(0, 15))

        self.log_box = ctk.CTkTextbox(
            logs_container,
            height=250,
            fg_color=self.colors["background"],
            text_color=self.colors["text"],
            font=theme.get_font("body")
        )
        self.log_box.pack(fill="both", expand=True, padx=15, pady=15)

        # === Brisanje logova ===
        reset_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        reset_frame.pack(fill="x", pady=(0, 10))

        self.clear_button = ctk.CTkButton(
            reset_frame,
            text="🗑 Obriši logove",
            fg_color="#dc2626",
            hover_color="#b91c1c",
            font=theme.get_font("body"),
            width=200,
            height=38,
            command=self.confirm_clear_logs
        )
        self.clear_button.pack(side="right", padx=15)

        # === Footer ===
        footer = ctk.CTkLabel(
            self.frame,
            text="Wizvod © 2025 — Automatizovano preuzimanje bankovnih izvoda",
            font=theme.get_font("small"),
            text_color=self.colors["text_secondary"]
        )
        footer.pack(side="bottom", pady=(10, 0))

        # Inicijalno osvježavanje
        self.refresh_stats()
        self.refresh_logs()

    # -----------------------------------------------------
    # 🧱 Stat Card
    # -----------------------------------------------------
    def _create_stat_card(self, parent, title, value):
        card = ctk.CTkFrame(
            parent,
            fg_color=self.colors["surface"],
            corner_radius=12,
            height=110
        )
        ctk.CTkLabel(
            card, text=title,
            font=theme.get_font("body"),
            text_color=self.colors["text_secondary"]
        ).pack(pady=(15, 5))
        value_label = ctk.CTkLabel(
            card, text=value,
            font=theme.get_font("title"),
            text_color=self.colors["primary"]
        )
        value_label.pack(pady=(0, 15))
        card.value_label = value_label
        return card

    # -----------------------------------------------------
    # 🔁 Sinhronizacija
    # -----------------------------------------------------
    def start_sync(self):
        if self.is_syncing:
            messagebox.showwarning("Upozorenje", "Sinhronizacija je već u toku!")
            return
        if not self.db.list_mail_accounts():
            messagebox.showwarning("Nedostaje konfiguracija", "Prvo dodajte email nalog.")
            return
        if not self.db.list_clients():
            messagebox.showwarning("Nedostaje konfiguracija", "Prvo dodajte klijente.")
            return

        self.is_syncing = True
        self.sync_button.configure(state="disabled", text="⏳ Sinhronizacija u toku...")
        self.sync_status_label.configure(text="Status: Pokrenuto...")

        threading.Thread(target=self._run_sync_thread, daemon=True).start()

    def _run_sync_thread(self):
        try:
            log.info("Dashboard: Pokrenuta manualna sinhronizacija")
            run_once()
            status_text = "✅ Uspješno završeno"
            status_color = "#059669"
        except Exception as e:
            log.exception("Greška u sinhronizaciji:")
            status_text = f"❌ Greška: {str(e)[:80]}"
            status_color = "#dc2626"
        self.frame.after(100, lambda: self._on_sync_complete(status_text, status_color))

    def _on_sync_complete(self, status_text: str, status_color: str):
        self.is_syncing = False
        self.sync_button.configure(state="normal", text="🔄 Sinhronizuj sada")

        now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        self.last_sync_label.configure(text=f"⏱ Zadnja sinhronizacija: {now}")
        self.sync_status_label.configure(text=f"Status: {status_text}", text_color=status_color)

        self.log_box.insert("end", f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {status_text}\n")
        self.log_box.insert("end", f"{'=' * 60}\n\n")
        self.log_box.see("end")

        self.refresh_stats()
        self.refresh_logs()

    # -----------------------------------------------------
    # 🖨️ Sinhronizacija i štampanje
    # -----------------------------------------------------
    def start_sync_and_print(self):
        if self.is_syncing:
            messagebox.showwarning("Upozorenje", "Sinhronizacija je već u toku!")
            return
        if not self.db.list_mail_accounts():
            messagebox.showwarning("Nedostaje konfiguracija", "Prvo dodajte email nalog.")
            return
        if not self.db.list_clients():
            messagebox.showwarning("Nedostaje konfiguracija", "Prvo dodajte klijente.")
            return

        from wizvod.core.pdf_printer import PDFPrinter
        printer = PDFPrinter()
        if not printer.default_printer:
            messagebox.showerror(
                "Greška",
                "Nije pronađen nijedan štampač u sistemu.\nSinhronizacija će se izvršiti bez štampanja."
            )
            self.start_sync()
            return

        confirm = messagebox.askyesno(
            "Potvrda",
            f"Sinhronizovati i automatski odštampati sve preuzete izvode?\n\n"
            f"Štampač: {printer.default_printer}\n\n"
            f"Napomena: Štampanje će početi nakon završetka sinhronizacije."
        )
        if not confirm:
            return

        self.is_syncing = True
        self.sync_button.configure(state="disabled")
        self.sync_print_button.configure(state="disabled", text="⏳ U toku...")
        self.sync_status_label.configure(text="Status: Sinhronizacija i priprema za štampanje...")

        threading.Thread(target=self._run_sync_and_print_thread, daemon=True).start()

    def _run_sync_and_print_thread(self):
        session_id = None
        try:
            log.info("Dashboard: Pokrenuta 'Sinhronizuj i štampaj' funkcija")
            from wizvod.worker import run_worker
            from wizvod.core.sync_sessions import SyncSessionManager

            run_worker()

            session_mgr = SyncSessionManager(self.db)
            sessions = session_mgr.get_sessions(limit=1)
            if not sessions:
                raise Exception("Nije pronađena sesija sinhronizacije")

            session_id = sessions[0]["session_id"]
            session_logs = session_mgr.get_session_logs(session_id)
            successful_logs = [l for l in session_logs if l["status"] == "ok"]

            if not successful_logs:
                self.frame.after(100, lambda: self._on_sync_print_complete(
                    "✓ Sinhronizacija završena (nema novih izvoda za štampanje)",
                    "#f59e0b", 0, 0
                ))
                return

            from wizvod.core.pdf_printer import PDFPrinter
            printer = PDFPrinter()
            log.info(f"🖨️ Pokrećem štampanje {len(successful_logs)} izvoda...")
            printed_count = printer.print_session(session_logs)

            self.frame.after(100, lambda: self._on_sync_print_complete(
                f"✅ Uspješno: {len(successful_logs)} preuzeto, {printed_count} poslato na štampač",
                "#059669", len(successful_logs), printed_count
            ))

        except Exception as e:
            log.exception("Greška u sinhronizaciji i štampanju:")
            err_msg = str(e)[:80]
            self.frame.after(100, lambda msg=err_msg: self._on_sync_print_complete(
                f"❌ Greška: {msg}", "#dc2626", 0, 0
            ))

    def _on_sync_print_complete(self, status_text, status_color, synced, printed):
        import datetime
        self.is_syncing = False
        self.sync_button.configure(state="normal")
        self.sync_print_button.configure(state="normal", text="🖨️ Sinhronizuj i štampaj")

        now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        self.last_sync_label.configure(text=f"⏱ Zadnja sinhronizacija: {now}")
        self.sync_status_label.configure(text=f"Status: {status_text}", text_color=status_color)

        self.log_box.insert("end", f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {status_text}\n")
        self.log_box.insert("end", f"{'=' * 60}\n\n")
        self.log_box.see("end")

        self.refresh_stats()
        self.refresh_logs()

        if synced > 0:
            result_msg = (
                f"Sinhronizacija i štampanje završeno!\n\n"
                f"📥 Preuzeto izvoda: {synced}\n"
                f"🖨️ Poslato na štampač: {printed}\n\n"
            )
            result_msg += (
                "⚠️ Neki dokumenti nisu odštampani. Provjerite štampač."
                if printed < synced else "✅ Svi dokumenti su uspješno poslati na štampač."
            )
            messagebox.showinfo("Završeno", result_msg)

    # -----------------------------------------------------
    # 🧹 Brisanje logova
    # -----------------------------------------------------
    def confirm_clear_logs(self):
        if messagebox.askyesno("Potvrda", "Da li ste sigurni da želite obrisati sve logove sinhronizacije?"):
            try:
                self.db.clear_logs()
                messagebox.showinfo("Uspjeh", "Log sinhronizacije je uspješno obrisan.")
                self.refresh_logs()
                self.refresh_stats()
            except Exception as e:
                log.error(f"Greška pri brisanju logova: {e}")
                messagebox.showerror("Greška", f"Neuspješno brisanje logova:\n{e}")

    # -----------------------------------------------------
    # 📊 Statistika i logovi
    # -----------------------------------------------------
    def refresh_stats(self):
        try:
            clients_count = len(self.db.list_clients())
            accounts_count = len(self.db.list_mail_accounts())
            today = datetime.date.today().strftime("%Y-%m-%d")
            logs = self.db.list_logs(limit=1000)
            today_count = sum(
                1 for log in logs
                if log["status"] == "ok" and log.get("created_at", "").startswith(today)
            )

            self.clients_card.value_label.configure(text=str(clients_count))
            self.accounts_card.value_label.configure(text=str(accounts_count))
            self.today_card.value_label.configure(text=str(today_count))
        except Exception as e:
            log.error(f"Greška pri osvježavanju statistike: {e}")

    def refresh_logs(self):
        self.log_box.delete("1.0", "end")
        try:
            rows = self.db.list_logs(limit=15)
            if not rows:
                self.log_box.insert("end", "Nema prethodnih zapisa.\n")
                return
            for r in rows:
                status_icon = {"ok": "✓", "skipped": "⊘", "error": "✗"}.get(r["status"], "•")
                timestamp = r.get("created_at", "")
                if timestamp:
                    try:
                        dt = datetime.datetime.fromisoformat(timestamp)
                        timestamp = dt.strftime("%d.%m. %H:%M")
                    except Exception:
                        pass
                client = r.get("client") or r.get("client_name") or "—"
                stmt = r.get("statement_no") or r.get("statement_number") or "—"
                error = r.get("error_message") or r.get("message") or ""
                line = f"[{timestamp}] {status_icon} {client} | Izvod: {stmt}"
                if error and r["status"] != "ok":
                    line += f" | {error[:50]}"
                line += "\n"
                self.log_box.insert("end", line)
        except Exception as e:
            log.error(f"Greška pri učitavanju logova: {e}")
            self.log_box.insert("end", f"Greška pri učitavanju logova: {e}\n")
