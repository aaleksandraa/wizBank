"""
settings_tab.py - SA PODRŠKOM ZA ODABIR ŠTAMPAČA
"""
import customtkinter as ctk
from tkinter import messagebox, filedialog
import threading
from wizvod.core.db import Database
from wizvod.core.logger import get_logger
from wizvod.core.license_manager import LicenseManager, get_fingerprint
from wizvod.core.pdf_printer import PDFPrinter
from wizvod.gui.themes.theme_manager import theme

log = get_logger("settings")


class SettingsTab:
    def __init__(self, parent, db: Database):
        self.db = db
        self.lic = LicenseManager(db)
        self.printer = PDFPrinter()
        self.colors = theme.colors

        # Glavni okvir
        self.frame = ctk.CTkFrame(parent, fg_color=self.colors["background"])
        self.frame.pack(fill="both", expand=True, padx=25, pady=25)

        # === HEADER ===
        header = ctk.CTkFrame(self.frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 25))

        title = ctk.CTkLabel(
            header,
            text="⚙️ Podešavanja sistema",
            font=theme.get_font("title"),
            text_color=self.colors["text"]
        )
        title.pack(anchor="w", padx=5)

        subtitle = ctk.CTkLabel(
            header,
            text="Prilagodite način rada, štampač i provjerite licencu aplikacije.",
            font=theme.get_font("body"),
            text_color=self.colors["text_secondary"]
        )
        subtitle.pack(anchor="w", padx=5)

        # === SCROLL CONTAINER ===
        scroll = ctk.CTkScrollableFrame(self.frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # ============================================================
        # SEKCIJA 1: OPŠTA PODEŠAVANJA
        # ============================================================
        section1 = ctk.CTkFrame(scroll, fg_color=self.colors["surface"], corner_radius=12)
        section1.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            section1,
            text="📧 Opšta podešavanja",
            font=theme.get_font("subtitle"),
            text_color=self.colors["text"]
        ).pack(anchor="w", padx=20, pady=(15, 10))

        form1 = ctk.CTkFrame(section1, fg_color=self.colors["background"], corner_radius=10)
        form1.pack(fill="x", padx=20, pady=(0, 20))

        # Lookback
        ctk.CTkLabel(
            form1,
            text="Pretraži emailove unazad (dana):",
            text_color=self.colors["text_secondary"],
            font=theme.get_font("body")
        ).grid(row=0, column=0, padx=10, pady=(15, 5), sticky="w")
        self.lookback_entry = ctk.CTkEntry(form1, placeholder_text="npr. 7")
        self.lookback_entry.grid(row=0, column=1, padx=10, pady=(15, 5), sticky="ew")

        # Read mode
        ctk.CTkLabel(
            form1,
            text="Način čitanja poruka:",
            text_color=self.colors["text_secondary"],
            font=theme.get_font("body")
        ).grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.read_mode = ctk.CTkOptionMenu(form1, values=["Samo nepročitane", "Sve poruke"])
        self.read_mode.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        # Checkboxi
        self.mark_read_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            form1,
            text="Označi poruku kao pročitanu",
            variable=self.mark_read_var,
            text_color=self.colors["text"]
        ).grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="w")

        self.verbose_log_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            form1,
            text="Detaljni log (svi koraci)",
            variable=self.verbose_log_var,
            text_color=self.colors["text"]
        ).grid(row=3, column=0, columnspan=2, padx=10, pady=(0, 15), sticky="w")

        form1.columnconfigure(1, weight=1)

        # ============================================================
        # SEKCIJA 2: ŠTAMPAČ
        # ============================================================
        section2 = ctk.CTkFrame(scroll, fg_color=self.colors["surface"], corner_radius=12)
        section2.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            section2,
            text="🖨️ Podešavanja štampača",
            font=theme.get_font("subtitle"),
            text_color=self.colors["text"]
        ).pack(anchor="w", padx=20, pady=(15, 10))

        printer_frame = ctk.CTkFrame(section2, fg_color=self.colors["background"], corner_radius=10)
        printer_frame.pack(fill="x", padx=20, pady=(0, 20))

        # Current printer info
        current_printer_frame = ctk.CTkFrame(printer_frame, fg_color="transparent")
        current_printer_frame.pack(fill="x", padx=15, pady=(15, 10))

        ctk.CTkLabel(
            current_printer_frame,
            text="Default štampač:",
            font=theme.get_font("body_bold"),
            text_color=self.colors["text"]
        ).pack(side="left", padx=5)

        self.current_printer_label = ctk.CTkLabel(
            current_printer_frame,
            text=self.printer.default_printer or "Nije pronađen",
            font=theme.get_font("body"),
            text_color=self.colors["primary"]
        )
        self.current_printer_label.pack(side="left", padx=10)

        # Odabir štampača
        select_frame = ctk.CTkFrame(printer_frame, fg_color="transparent")
        select_frame.pack(fill="x", padx=15, pady=(10, 15))

        ctk.CTkLabel(
            select_frame,
            text="Izaberi štampač za Wizvod:",
            text_color=self.colors["text_secondary"],
            font=theme.get_font("body")
        ).pack(anchor="w", pady=(0, 5))

        # Dropdown sa štampačima
        self.printer_dropdown = ctk.CTkOptionMenu(
            select_frame,
            values=["Učitavam..."],
            width=400
        )
        self.printer_dropdown.pack(fill="x", pady=5)

        # Dugmad
        printer_btn_frame = ctk.CTkFrame(printer_frame, fg_color="transparent")
        printer_btn_frame.pack(fill="x", padx=15, pady=(5, 15))

        ctk.CTkButton(
            printer_btn_frame,
            text="🔄 Osvježi listu",
            width=130,
            height=36,
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
            command=self.refresh_printers
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            printer_btn_frame,
            text="💾 Sačuvaj izbor",
            width=130,
            height=36,
            fg_color=self.colors["success"],
            hover_color="#047857",
            command=self.save_printer_choice
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            printer_btn_frame,
            text="🧪 Test štampanja",
            width=140,
            height=36,
            fg_color=self.colors["purple"],
            hover_color=self.colors["purple_hover"],
            command=self.test_printer
        ).pack(side="left", padx=5)

        # Status
        self.printer_status_label = ctk.CTkLabel(
            printer_frame,
            text="",
            font=theme.get_font("small"),
            text_color=self.colors["text_secondary"]
        )
        self.printer_status_label.pack(pady=(0, 10))

        # ============================================================
        # SEKCIJA 3: LICENCA
        # ============================================================
        section3 = ctk.CTkFrame(scroll, fg_color=self.colors["surface"], corner_radius=12)
        section3.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            section3,
            text="🔐 Licenca aplikacije",
            font=theme.get_font("subtitle"),
            text_color=self.colors["text"]
        ).pack(anchor="w", padx=20, pady=(15, 10))

        lic_box = ctk.CTkFrame(section3, fg_color=self.colors["background"], corner_radius=10)
        lic_box.pack(fill="x", padx=20, pady=(0, 20))

        ctk.CTkButton(
            lic_box,
            text="📂 Učitaj license.json",
            fg_color=self.colors["purple"],
            hover_color=self.colors["purple_hover"],
            height=40,
            width=200,
            command=self.import_and_check_license,
        ).pack(padx=15, pady=(15, 10))

        self.lic_status = ctk.CTkLabel(
            lic_box,
            text="Status licence: nepoznat",
            text_color=self.colors["text_secondary"],
            font=theme.get_font("body")
        )
        self.lic_status.pack(padx=15, pady=(0, 15))

        # Fingerprint
        fp_frame = ctk.CTkFrame(lic_box, fg_color="transparent")
        fp_frame.pack(fill="x", padx=15, pady=(5, 15))

        ctk.CTkLabel(
            fp_frame,
            text="Fingerprint ovog računara:",
            text_color=self.colors["text_secondary"],
            font=theme.get_font("body_bold")
        ).pack(anchor="w", pady=(0, 5))

        fp_entry_frame = ctk.CTkFrame(fp_frame, fg_color="transparent")
        fp_entry_frame.pack(fill="x")

        self.fp_entry = ctk.CTkEntry(fp_entry_frame, corner_radius=8)
        self.fp_entry.insert(0, get_fingerprint())
        self.fp_entry.configure(state="readonly")
        self.fp_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(
            fp_entry_frame,
            text="📋 Kopiraj",
            width=100,
            height=32,
            fg_color=self.colors["primary"],
            hover_color=self.colors["primary_hover"],
            command=lambda: self.frame.clipboard_append(self.fp_entry.get()),
        ).pack(side="left")

        # ============================================================
        # DUGMAD ZA ČUVANJE
        # ============================================================
        save_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        save_frame.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(
            save_frame,
            text="💾 Sačuvaj sva podešavanja",
            fg_color=self.colors["primary"],
            hover_color=self.colors["primary_hover"],
            width=220,
            height=45,
            font=theme.get_font("body_bold"),
            command=self.save_all_settings
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            save_frame,
            text="🔄 Učitaj postojeća",
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
            width=180,
            height=45,
            font=theme.get_font("body_bold"),
            command=self.load_all_settings
        ).pack(side="left", padx=5)

        # ============================================================
        # INICIJALIZACIJA
        # ============================================================
        self.load_all_settings()
        self.refresh_printers()
        self.check_license(silent=True)

    # ================================================================
    # OPŠTA PODEŠAVANJA
    # ================================================================
    def save_all_settings(self):
        """Čuva sva podešavanja odjednom."""
        lookback = self.lookback_entry.get().strip()
        read_mode = "unread" if self.read_mode.get().startswith("Samo") else "all"
        mark_read = "1" if self.mark_read_var.get() else "0"
        verbose = "1" if self.verbose_log_var.get() else "0"

        if not lookback.isdigit():
            messagebox.showwarning("Upozorenje", "Broj dana mora biti broj.")
            return

        try:
            self.db.save_setting("lookback_days", lookback)
            self.db.save_setting("read_mode", read_mode)
            self.db.save_setting("mark_as_read", mark_read)
            self.db.save_setting("verbose_log", verbose)

            # Sačuvaj i izbor štampača
            self.save_printer_choice(show_message=False)

            messagebox.showinfo("Uspjeh", "✅ Sva podešavanja su sačuvana.")
        except Exception as e:
            log.error(e)
            messagebox.showerror("Greška", str(e))

    def load_all_settings(self):
        """Učitava sva podešavanja."""
        try:
            # Email podešavanja
            lookback = self.db.get_setting("lookback_days") or "7"
            read_mode = self.db.get_setting("read_mode") or "unread"
            mark_read = self.db.get_setting("mark_as_read") == "1"
            verbose = self.db.get_setting("verbose_log") == "1"

            self.lookback_entry.delete(0, "end")
            self.lookback_entry.insert(0, lookback)
            self.read_mode.set("Samo nepročitane" if read_mode == "unread" else "Sve poruke")
            self.mark_read_var.set(mark_read)
            self.verbose_log_var.set(verbose)

            # Štampač
            saved_printer = self.db.get_setting("preferred_printer")
            if saved_printer:
                self.printer.set_printer(saved_printer)
                self.current_printer_label.configure(text=saved_printer)

        except Exception as e:
            log.error(e)
            messagebox.showerror("Greška", f"Ne mogu učitati podešavanja:\n{e}")

    # ================================================================
    # ŠTAMPAČ
    # ================================================================
    def refresh_printers(self):
        """Osvježava listu dostupnih štampača."""
        self.printer_status_label.configure(text="⏳ Učitavam štampače...", text_color=self.colors["text_secondary"])

        def load_thread():
            printers = self.printer.get_available_printers()
            self.frame.after(100, lambda: self._on_printers_loaded(printers))

        threading.Thread(target=load_thread, daemon=True).start()

    def _on_printers_loaded(self, printers: list):
        """Callback nakon učitavanja štampača."""
        if not printers:
            self.printer_dropdown.configure(values=["Nema dostupnih štampača"])
            self.printer_status_label.configure(
                text="❌ Nije pronađen nijedan štampač",
                text_color=self.colors["error"]
            )
            return

        self.printer_dropdown.configure(values=printers)

        # Postavi trenutno odabrani
        saved = self.db.get_setting("preferred_printer")
        if saved and saved in printers:
            self.printer_dropdown.set(saved)
        elif self.printer.default_printer:
            self.printer_dropdown.set(self.printer.default_printer)
        else:
            self.printer_dropdown.set(printers[0])

        self.printer_status_label.configure(
            text=f"✅ Pronađeno: {len(printers)} štampača",
            text_color=self.colors["success"]
        )

    def save_printer_choice(self, show_message: bool = True):
        """Čuva izbor štampača."""
        selected = self.printer_dropdown.get()

        if selected == "Nema dostupnih štampača" or selected == "Učitavam...":
            messagebox.showwarning("Upozorenje", "Nema odabranog štampača.")
            return

        try:
            self.printer.set_printer(selected)
            self.db.save_setting("preferred_printer", selected)
            self.current_printer_label.configure(text=selected)

            if show_message:
                messagebox.showinfo("Uspjeh", f"✅ Štampač postavljen:\n{selected}")

        except Exception as e:
            log.error(f"Greška pri čuvanju štampača: {e}")
            messagebox.showerror("Greška", str(e))

    def test_printer(self):
        """Testira odabrani štampač."""
        selected = self.printer_dropdown.get()

        if selected == "Nema dostupnih štampača" or selected == "Učitavam...":
            messagebox.showwarning("Upozorenje", "Prvo odaberite štampač.")
            return

        confirm = messagebox.askyesno(
            "Test štampanja",
            f"Testirati štampač?\n\n{selected}\n\n"
            f"Biće odštampana test stranica."
        )

        if not confirm:
            return

        self.printer_status_label.configure(text="🧪 Test u toku...", text_color=self.colors["primary"])

        def test_thread():
            success = self.printer.test_print(selected)
            self.frame.after(100, lambda: self._on_test_complete(success, selected))

        threading.Thread(target=test_thread, daemon=True).start()

    def _on_test_complete(self, success: bool, printer_name: str):
        """Callback nakon test štampanja."""
        if success:
            self.printer_status_label.configure(
                text=f"✅ Test uspješan: {printer_name}",
                text_color=self.colors["success"]
            )
            messagebox.showinfo(
                "Test uspješan",
                f"Test stranica je poslata na štampač:\n{printer_name}\n\n"
                f"Provjerite da li se stranica štampa."
            )
        else:
            self.printer_status_label.configure(
                text=f"❌ Test neuspješan: {printer_name}",
                text_color=self.colors["error"]
            )
            messagebox.showerror(
                "Test neuspješan",
                f"Nije moguće odštampati test stranicu.\n\n"
                f"Provjerite:\n"
                f"• Da li je štampač uključen\n"
                f"• Da li ima papira i tonera\n"
                f"• Da li su instalirani drajveri"
            )

    # ================================================================
    # LICENCA
    # ================================================================
    def import_and_check_license(self):
        path = filedialog.askopenfilename(
            title="Odaberi license.json",
            filetypes=[("JSON fajl", "*.json"), ("Svi fajlovi", "*.*")]
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                lic_json = f.read()
            self.lic.save(lic_json)
            self.check_license(silent=False)
        except Exception as e:
            log.error(e)
            messagebox.showerror("Greška", f"Neuspješan import license.json:\n{e}")

    def check_license(self, silent: bool = False):
        try:
            ok = self.lic.validate()
        except Exception as e:
            log.error(e)
            ok = False

        info = {}
        try:
            info = self.lic.get_license_info()
        except Exception:
            pass

        expires_at = info.get("expires_at", "")
        holder = info.get("holder", "")

        if ok:
            text = "✅ Licenca je validna"
            if holder:
                text += f" | Nosilac: {holder}"
            if expires_at:
                text += f" | Važi do: {expires_at}"
            self.lic_status.configure(text=text, text_color=self.colors["success"])
            if not silent:
                messagebox.showinfo("Licenca", text)
        else:
            self.lic_status.configure(text="❌ Licenca NIJE validna", text_color=self.colors["error"])
            if not silent:
                messagebox.showwarning(
                    "Licenca",
                    "Licenca nije validna ili je istekla. Uvezite license.json ponovo."
                )