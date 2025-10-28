"""
accounts_tab.py - OPTIMIZOVAN

KLJUČNE OPTIMIZACIJE:
✅ Lazy loading - ne poziva DB dok nije potrebno
✅ Async refresh - ne blokira UI
✅ Cache accounts - brži filter
"""

import customtkinter as ctk
from tkinter import messagebox
import imaplib
import threading
from wizvod.core.db import Database
from wizvod.core.crypto import encrypt_secret
from wizvod.core.logger import get_logger
from wizvod.core.email_auth_manager import EmailAuthManager

log = get_logger("accounts")


class AccountsTab:
    def __init__(self, parent, db: Database):
        self.db = db
        self.accounts_cache = []
        self.is_loading = False

        self.frame = ctk.CTkFrame(parent, fg_color="white")
        # NE PAKUJ ovdje - MainApp će to uraditi

        # Header
        header = ctk.CTkLabel(
            self.frame,
            text="📧 Email nalozi i povezivanje",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#1e3a8a"
        )
        header.pack(pady=(10, 25))

        desc = ctk.CTkLabel(
            self.frame,
            text="Povežite svoj email nalog (Gmail, Outlook, Yahoo, Custom IMAP).",
            text_color="#334155"
        )
        desc.pack(pady=(0, 15))

        # Dugmad za providere
        btn_frame = ctk.CTkFrame(self.frame, fg_color="#f8fafc", corner_radius=12)
        btn_frame.pack(pady=10, fill="x", padx=15)

        ctk.CTkButton(
            btn_frame, text="📬 Gmail (OAuth2)", fg_color="#ea4335",
            hover_color="#c5221f", command=self.connect_gmail_oauth
        ).pack(fill="x", padx=15, pady=6)

        ctk.CTkButton(
            btn_frame, text="📦 Outlook / Hotmail (OAuth2)", fg_color="#0078d4",
            hover_color="#0369a1", command=self.connect_outlook_oauth
        ).pack(fill="x", padx=15, pady=6)

        ctk.CTkButton(
            btn_frame, text="📨 Yahoo Mail (OAuth2)", fg_color="#7b0099",
            hover_color="#581c87", command=self.connect_yahoo_oauth
        ).pack(fill="x", padx=15, pady=6)

        ctk.CTkButton(
            btn_frame, text="⚙️ Custom IMAP (lozinka)", fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=lambda: self.open_custom_imap("Custom IMAP", "")
        ).pack(fill="x", padx=15, pady=6)

        # Lista naloga
        list_frame = ctk.CTkFrame(self.frame, fg_color="#f1f5f9", corner_radius=12)
        list_frame.pack(fill="both", expand=True, padx=15, pady=15)

        ctk.CTkLabel(
            list_frame, text="📋 Povezani nalozi:",
            font=ctk.CTkFont(size=16, weight="bold"), text_color="#1e293b"
        ).pack(anchor="w", padx=15, pady=(10, 5))

        # ✨ Loading label
        self.loading_label = ctk.CTkLabel(
            list_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#6b7280"
        )
        self.loading_label.pack(anchor="w", padx=15, pady=2)

        self.scroll_frame = ctk.CTkScrollableFrame(list_frame, fg_color="#f8fafc")
        self.scroll_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        ctk.CTkButton(
            list_frame, text="🔄 Osvježi listu",
            fg_color="#059669", hover_color="#047857",
            command=self.refresh_accounts_async
        ).pack(pady=(0, 15))

    def on_tab_shown(self):
        """✨ Callback kad se tab prikaže - lazy loading."""
        if not self.accounts_cache:
            self.refresh_accounts_async()

    # ================================================================
    # ⚡ ASYNC REFRESH
    # ================================================================
    def refresh_accounts_async(self):
        """Asinhrono učitavanje naloga."""
        if self.is_loading:
            return

        self.is_loading = True
        self.loading_label.configure(text="⏳ Učitavam naloge...")

        def load_thread():
            try:
                accounts = self.db.list_mail_accounts()
                self.frame.after(0, lambda: self._on_accounts_loaded(accounts))
            except Exception as e:
                log.error(f"Greška pri učitavanju naloga: {e}")
                self.frame.after(0, lambda: self._on_load_error(str(e)))

        threading.Thread(target=load_thread, daemon=True).start()

    def _on_accounts_loaded(self, accounts):
        """Callback nakon učitavanja."""
        self.accounts_cache = accounts
        self.is_loading = False
        self.loading_label.configure(text=f"✅ Učitano: {len(accounts)} naloga")
        self._render_accounts(accounts)

    def _on_load_error(self, error_msg):
        """Callback za grešku."""
        self.is_loading = False
        self.loading_label.configure(text=f"❌ Greška: {error_msg}")

    def _render_accounts(self, accounts):
        """Renderuje sve naloge."""
        for child in self.scroll_frame.winfo_children():
            child.destroy()

        if not accounts:
            ctk.CTkLabel(
                self.scroll_frame,
                text="Nema povezanih naloga.",
                text_color="#6b7280"
            ).pack(pady=10)
            return

        for acc in accounts:
            self._render_account_card(acc)

    def _render_account_card(self, acc):
        """Renderuje karticu naloga."""
        card = ctk.CTkFrame(self.scroll_frame, fg_color="#ffffff", corner_radius=10)
        card.pack(fill="x", padx=10, pady=6)

        info = (
            f"📧 {acc['email']} ({acc['provider']})\n"
            f"   Host: {acc['imap_host']}:{acc['imap_port']} | SSL: {'Da' if acc['use_ssl'] else 'Ne'}"
        )
        ctk.CTkLabel(
            card, text=info, anchor="w", justify="left", text_color="#111827"
        ).pack(side="left", padx=10, pady=10)

        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(side="right", padx=10)

        # Samo IMAP može imati UREDI
        if "IMAP" in acc["provider"].upper():
            ctk.CTkButton(
                btn_frame, text="✏️ Uredi", width=80, fg_color="#2563eb",
                hover_color="#1d4ed8",
                command=lambda a=acc: self.edit_imap_account(a)
            ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="❌ Prekini", width=90, fg_color="#dc2626",
            hover_color="#b91c1c",
            command=lambda a=acc: self.delete_account(a["id"])
        ).pack(side="left", padx=5)

    # ================================================================
    # LEGACY METODA (za kompatibilnost)
    # ================================================================
    def refresh_accounts(self):
        """Legacy sync metoda - sada poziva async."""
        self.refresh_accounts_async()

    # ================================================================
    # GMAIL / OUTLOOK / YAHOO (bez promjena)
    # ================================================================
    def connect_gmail_oauth(self):
        try:
            token = EmailAuthManager.get_auth_method("gmail", "user")[1]
            if not token:
                messagebox.showerror("Greška", "Nije moguće dobiti Gmail token.")
                return
            self.db.add_mail_account(
                provider="Gmail (OAuth2)",
                email="gmail_user@google.com",
                imap_host="imap.gmail.com",
                imap_port=993,
                use_ssl=True,
                username="gmail_user@google.com",
                secret_encrypted=encrypt_secret(token)
            )
            messagebox.showinfo("Uspjeh", "✅ Gmail nalog je uspješno povezan.")
            self.refresh_accounts_async()
        except Exception as e:
            log.error(e)
            messagebox.showerror("Greška", f"Neuspješno povezivanje sa Gmailom: {e}")

    def connect_outlook_oauth(self):
        try:
            token = EmailAuthManager.get_auth_method("outlook", "user")[1]
            if not token:
                messagebox.showerror("Greška", "Nije moguće dobiti Outlook token.")
                return
            self.db.add_mail_account(
                provider="Outlook (OAuth2)",
                email="outlook_user@outlook.com",
                imap_host="outlook.office365.com",
                imap_port=993,
                use_ssl=True,
                username="outlook_user@outlook.com",
                secret_encrypted=encrypt_secret(token)
            )
            messagebox.showinfo("Uspjeh", "✅ Outlook nalog je uspješno povezan.")
            self.refresh_accounts_async()
        except Exception as e:
            log.error(e)
            messagebox.showerror("Greška", f"Neuspješno povezivanje sa Outlookom: {e}")

    def connect_yahoo_oauth(self):
        try:
            token = EmailAuthManager.get_auth_method("yahoo", "user")[1]
            if not token:
                messagebox.showerror("Greška", "Nije moguće dobiti Yahoo token.")
                return
            self.db.add_mail_account(
                provider="Yahoo (OAuth2)",
                email="yahoo_user@yahoo.com",
                imap_host="imap.mail.yahoo.com",
                imap_port=993,
                use_ssl=True,
                username="yahoo_user@yahoo.com",
                secret_encrypted=encrypt_secret(token)
            )
            messagebox.showinfo("Uspjeh", "✅ Yahoo nalog je uspješno povezan.")
            self.refresh_accounts_async()
        except Exception as e:
            log.error(e)
            messagebox.showerror("Greška", f"Neuspješno povezivanje sa Yahoo servisom: {e}")

    # ================================================================
    # CUSTOM IMAP (bez promjena)
    # ================================================================
    def open_custom_imap(self, provider_name, default_host):
        popup = ctk.CTkToplevel()
        popup.title(f"{provider_name} IMAP povezivanje")
        popup.geometry("420x400")
        popup.resizable(False, False)
        popup.grab_set()

        frame = ctk.CTkFrame(popup, fg_color="#f8fafc", corner_radius=12)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            frame, text=f"🔐 {provider_name} IMAP podešavanje",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(10, 15))

        host_entry = ctk.CTkEntry(frame, placeholder_text="IMAP host", width=250)
        host_entry.pack(pady=5)
        if default_host:
            host_entry.insert(0, default_host)

        port_entry = ctk.CTkEntry(frame, placeholder_text="Port (npr. 993)")
        port_entry.pack(pady=5)
        port_entry.insert(0, "993")

        email_entry = ctk.CTkEntry(frame, placeholder_text="Email adresa")
        email_entry.pack(pady=5)

        password_entry = ctk.CTkEntry(frame, placeholder_text="Lozinka", show="•")
        password_entry.pack(pady=5)

        use_ssl_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(frame, text="Koristi SSL", variable=use_ssl_var).pack(pady=(5, 15))

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(pady=10)

        ctk.CTkButton(
            btn_frame, text="🔌 Testiraj konekciju",
            fg_color="#2563eb", hover_color="#1d4ed8",
            command=lambda: self.test_imap_connection(
                host_entry.get(), port_entry.get(), email_entry.get(),
                password_entry.get(), use_ssl_var.get())
        ).grid(row=0, column=0, padx=8)

        ctk.CTkButton(
            btn_frame, text="💾 Sačuvaj nalog",
            fg_color="#059669", hover_color="#047857",
            command=lambda: self.save_imap_account(
                provider_name, host_entry.get(), port_entry.get(),
                email_entry.get(), password_entry.get(),
                use_ssl_var.get(), popup)
        ).grid(row=0, column=1, padx=8)

    def test_imap_connection(self, host, port, email, password, use_ssl=True):
        if not all([host, port, email, password]):
            messagebox.showwarning("Greška", "Popunite sva polja.")
            return
        try:
            port = int(port)
            conn = imaplib.IMAP4_SSL(host, port) if use_ssl else imaplib.IMAP4(host, port)
            conn.login(email, password)
            conn.logout()
            messagebox.showinfo("Uspjeh", f"✅ Povezano sa {host}")
        except Exception as e:
            log.error(e)
            messagebox.showerror("Greška", f"❌ Neuspješno: {e}")

    def save_imap_account(self, provider, host, port, email, password, use_ssl, popup):
        if not all([provider, host, port, email, password]):
            messagebox.showwarning("Upozorenje", "Popunite sva polja prije čuvanja.")
            return
        try:
            self.db.add_mail_account(
                provider=provider,
                email=email,
                imap_host=host,
                imap_port=int(port),
                use_ssl=use_ssl,
                username=email,
                secret_encrypted=encrypt_secret(password)
            )
            messagebox.showinfo("Uspjeh", f"Nalog za {email} je uspješno dodat.")
            popup.destroy()
            self.refresh_accounts_async()
        except Exception as e:
            log.error(e)
            messagebox.showerror("Greška", f"Nije moguće sačuvati nalog: {e}")

    def edit_imap_account(self, acc):
        popup = ctk.CTkToplevel()
        popup.title(f"Uredi IMAP nalog - {acc['email']}")
        popup.geometry("420x380")
        popup.resizable(False, False)
        popup.grab_set()

        frame = ctk.CTkFrame(popup, fg_color="#f8fafc", corner_radius=12)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            frame, text="✏️ Uredi IMAP nalog",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(10, 15))

        host_entry = ctk.CTkEntry(frame, placeholder_text="IMAP host")
        host_entry.pack(pady=5)
        host_entry.insert(0, acc["imap_host"])

        port_entry = ctk.CTkEntry(frame, placeholder_text="Port (npr. 993)")
        port_entry.pack(pady=5)
        port_entry.insert(0, acc["imap_port"])

        username_entry = ctk.CTkEntry(frame, placeholder_text="Korisničko ime / email")
        username_entry.pack(pady=5)
        username_entry.insert(0, acc["username"])

        password_entry = ctk.CTkEntry(
            frame,
            placeholder_text="Nova lozinka (ostavi prazno ako ostaje ista)",
            show="•"
        )
        password_entry.pack(pady=5)

        use_ssl_var = ctk.BooleanVar(value=acc["use_ssl"])
        ctk.CTkCheckBox(frame, text="Koristi SSL", variable=use_ssl_var).pack(pady=(5, 15))

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(pady=10)

        ctk.CTkButton(
            btn_frame, text="💾 Sačuvaj izmjene",
            fg_color="#059669", hover_color="#047857",
            command=lambda: self.save_imap_changes(
                acc, host_entry.get(), port_entry.get(),
                username_entry.get(), password_entry.get(),
                use_ssl_var.get(), popup
            )
        ).grid(row=0, column=0, padx=8)

        ctk.CTkButton(
            btn_frame, text="Odustani",
            fg_color="#6b7280", hover_color="#4b5563",
            command=popup.destroy
        ).grid(row=0, column=1, padx=8)

    def save_imap_changes(self, acc, host, port, username, password, use_ssl, popup):
        try:
            secret = acc["secret_encrypted"]
            if password.strip():
                secret = encrypt_secret(password)
            self.db.update_mail_account(
                acc["id"], acc["provider"], username, host, int(port),
                use_ssl, username, secret
            )
            popup.destroy()
            self.refresh_accounts_async()
            messagebox.showinfo("Uspjeh", "Izmjene su sačuvane.")
        except Exception as e:
            log.error(e)
            messagebox.showerror("Greška", str(e))

    def delete_account(self, acc_id):
        if not messagebox.askyesno("Potvrda", "Da li želite prekinuti konekciju ovog naloga?"):
            return
        try:
            self.db.delete_mail_account(acc_id)
            self.refresh_accounts_async()
            messagebox.showinfo("Uspjeh", "Nalog je uklonjen.")
        except Exception as e:
            log.error(e)
            messagebox.showerror("Greška", str(e))