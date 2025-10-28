import customtkinter as ctk
from wizvod.core.db import Database

class LogsTab:
    def __init__(self, parent, db: Database):
        self.db = db
        self.frame = ctk.CTkFrame(parent)
        self.frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.text = ctk.CTkTextbox(self.frame)
        self.text.pack(fill="both", expand=True)

        ctk.CTkButton(self.frame, text="Osvježi", command=self.refresh).pack(pady=8)
        self.refresh()

    def refresh(self):
        self.text.delete("1.0", "end")
        rows = self.db.list_logs(limit=300)
        if not rows:
            self.text.insert("end", "Nema logova.\n")
            return

        for row in rows:
            created = row.get("created_at", "")
            client = row.get("client") or row.get("client_name") or "—"
            stmt = row.get("statement_no") or row.get("statement_number") or "—"
            status = row.get("status", "")
            saved_path = row.get("saved_path", "") or row.get("file_path", "") or ""
            err = row.get("error_message", "") or row.get("message", "") or ""

            self.text.insert(
                "end",
                f"[{created}] {client} | Izvod:{stmt} | {status} | {saved_path} | {err}\n"
            )
