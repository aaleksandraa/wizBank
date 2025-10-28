import threading
import customtkinter as ctk
from datetime import datetime
from pathlib import Path
import subprocess
import ctypes
import os
import logging
import getpass


# === GLOBAL LOGGER ===
LOG_DIR = Path(Path.home() / ".wizvod" / "logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
SCHED_LOG = LOG_DIR / "scheduler.log"
logging.basicConfig(filename=SCHED_LOG, level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _hhmmtime(hh: str, mm: str) -> str:
    return f"{int(hh):02d}:{int(mm):02d}"


class SchedulerTab:
    TASK_NAME = "Wizvod_AutoSync"

    def __init__(self, parent, db=None):
        self.db = db
        self.automation_active = False

        self.frame = ctk.CTkFrame(parent, fg_color="white")
        self.frame.pack(fill="both", expand=True, padx=20, pady=20)

        # === Header ===
        ctk.CTkLabel(
            self.frame,
            text="⏰ Planiranje automatskog preuzimanja izvoda",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#1e3a8a"
        ).pack(pady=(10, 6))

        ctk.CTkLabel(
            self.frame,
            text="Wizvod može automatski preuzimati izvode dok ste prijavljeni na računar.",
            text_color="#334155"
        ).pack(pady=(0, 12))

        # === Mode ===
        outer = ctk.CTkFrame(self.frame, fg_color="#f8fafc", corner_radius=12)
        outer.pack(fill="x", padx=10, pady=(5, 15))

        ctk.CTkLabel(outer, text="Režim rasporeda:").grid(row=0, column=0, padx=10, pady=12, sticky="w")
        self.mode_menu = ctk.CTkOptionMenu(
            outer,
            values=["Jednom dnevno", "Periodični (noćni)", "Ostalo (napredno)"],
            command=lambda _: self._render_mode_area()
        )
        self.mode_menu.grid(row=0, column=1, padx=10, pady=12, sticky="ew")
        self.mode_area = ctk.CTkFrame(outer, fg_color="transparent")
        self.mode_area.grid(row=1, column=0, columnspan=2, padx=8, pady=(0, 12), sticky="ew")
        outer.columnconfigure(1, weight=1)

        # === Buttons ===
        btn_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="💾 Sačuvaj raspored",
                      fg_color="#2563eb", hover_color="#1d4ed8",
                      command=self.activate_schedule).grid(row=0, column=0, padx=10)
        ctk.CTkButton(btn_frame, text="▶ Pokreni odmah",
                      fg_color="#9333ea", hover_color="#7e22ce",
                      command=self.run_now).grid(row=0, column=1, padx=10)
        ctk.CTkButton(btn_frame, text="🛑 Prekini automatizaciju",
                      fg_color="#dc2626", hover_color="#b91c1c",
                      command=self.stop_schedule).grid(row=0, column=2, padx=10)

        # === Status ===
        self.status_label = ctk.CTkLabel(self.frame, text="Automatizacija nije aktivna.", text_color="#6b7280")
        self.status_label.pack(pady=(5, 8))

        # === Info box ===
        self.info_box = ctk.CTkTextbox(self.frame, height=220, fg_color="#f1f5f9", text_color="#111827")
        self.info_box.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        self._log("ℹ️ Status i detalji o rasporedu će se prikazati ovdje.")

        self._init_state()

    # ------------------------------------------------
    def _init_state(self):
        self.mode_menu.set("Jednom dnevno")
        self._render_mode_area()
        self._load_settings_safe()

    def _render_mode_area(self):
        for w in self.mode_area.winfo_children():
            w.destroy()
        hours = [f"{i:02d}" for i in range(24)]
        minutes = [f"{i:02d}" for i in range(0, 60, 5)]
        mode = self.mode_menu.get()
        if "Jednom" in mode:
            ctk.CTkLabel(self.mode_area, text="Vrijeme (HH:MM):").grid(row=0, column=0, padx=10, pady=6, sticky="w")
            self.once_h = ctk.CTkOptionMenu(self.mode_area, values=hours)
            self.once_m = ctk.CTkOptionMenu(self.mode_area, values=minutes)
            self.once_h.grid(row=0, column=1, padx=5, pady=6)
            self.once_m.grid(row=0, column=2, padx=5, pady=6)
            self.once_h.set("06"); self.once_m.set("00")

    # ------------------------------------------------
    def _load_settings_safe(self):
        if not self.db:
            return
        try:
            s = self.db.get_settings()
            if not s:
                return
            if s.get("once_h"): self.once_h.set(s["once_h"].zfill(2))
            if s.get("once_m"): self.once_m.set(s["once_m"].zfill(2))
        except Exception as e:
            self._log(f"⚠️ Greška pri učitavanju: {e}")

    def _save_settings(self):
        if self.db:
            self.db.save_setting("once_h", self.once_h.get())
            self.db.save_setting("once_m", self.once_m.get())

    # ------------------------------------------------
    def activate_schedule(self):
        """Pokreće kreiranje scheduler zadatka u pozadini."""
        self.status_label.configure(text="⏳ Kreiram raspored...", text_color="#2563eb")
        self._log("⏳ Kreiranje rasporeda u toku...")

        def worker():
            try:
                self._save_settings()
                bat_path = self._ensure_bat_exists()
                self._create_windows_task(bat_path)
                self.automation_active = True
                self.status_label.configure(text="🟢 Automatizacija aktivna (dok ste prijavljeni)", text_color="#059669")
                self._log("✅ Raspored sačuvan i zadatak kreiran.")
            except Exception as e:
                self.status_label.configure(text="❌ Greška pri aktivaciji", text_color="#dc2626")
                self._log(f"❌ {e}")

        threading.Thread(target=worker, daemon=True).start()

    def stop_schedule(self):
        subprocess.run(["schtasks", "/delete", "/tn", self.TASK_NAME, "/f"], shell=True)
        self.status_label.configure(text="🔴 Automatizacija prekinuta", text_color="#dc2626")
        self._log("Automatizacija prekinuta.")

    def run_now(self):
        try:
            bat_path = self._ensure_bat_exists()
            subprocess.Popen(["cmd", "/c", str(bat_path)], shell=True)
            self._log(f"▶ {datetime.now().strftime('%H:%M:%S')} - Worker pokrenut odmah.")
        except Exception as e:
            self._log(f"⚠️ {e}")

    # ------------------------------------------------
    def _log(self, text: str):
        self.info_box.insert("end", f"\n{text}\n")
        self.info_box.see("end")
        logging.info(text)

    def _ensure_bat_exists(self) -> Path:
        app_dir = Path(__file__).resolve().parents[2]
        bat_path = app_dir / "run_worker.bat"
        if not bat_path.exists():
            bat_path.write_text(
                "@echo off\n"
                "cd /d \"%~dp0\"\n"
                "if exist \".venv\\Scripts\\activate.bat\" call \".venv\\Scripts\\activate.bat\"\n"
                "start /min python -m wizvod.worker --run\n",
                encoding="utf-8"
            )
            self._log("run_worker.bat je automatski kreiran.")
        return bat_path

    # ------------------------------------------------
    def _create_windows_task(self, bat_path: Path):
        """Kreira Windows Scheduler zadatak (radi dok je korisnik prijavljen)."""
        username = getpass.getuser()
        s = self.db.get_settings() if self.db else {}
        hh = s.get("once_h", "06")
        mm = s.get("once_m", "00")
        start_time = f"{int(hh):02d}:{int(mm):02d}"

        # Obriši postojeći
        subprocess.run(["schtasks", "/delete", "/tn", self.TASK_NAME, "/f"],
                       capture_output=True, text=True, shell=True)

        base_cmd = [
            "schtasks", "/create",
            "/tn", self.TASK_NAME,
            "/tr", str(bat_path),
            "/sc", "daily", "/st", start_time,
            "/ru", username,
            "/it",  # samo dok je korisnik prijavljen
            "/f"
        ]

        res = subprocess.run(base_cmd, capture_output=True, text=True, shell=True, timeout=15)
        if res.returncode != 0:
            raise RuntimeError((res.stderr or res.stdout).strip() or "Greška pri kreiranju zadatka.")

        self._log("✅ Zadak uspješno kreiran (radi dok ste prijavljeni).")
