import customtkinter as ctk
from wizvod.core.db import Database
from wizvod.gui.tabs.dashboard_tab import DashboardTab
from wizvod.gui.tabs.clients_tab import ClientsTab
from wizvod.gui.tabs.accounts_tab import AccountsTab
from wizvod.gui.tabs.history_tab import HistoryTab
from wizvod.gui.tabs.scheduler_tab import SchedulerTab
from wizvod.gui.tabs.settings_tab import SettingsTab
from wizvod.gui.themes.theme_manager import theme


class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window setup
        self.title("Wizvod - Automatsko preuzimanje bankovnih izvoda")
        self.geometry("1400x900")

        # Theme
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        # Database
        self.db = Database()

        # ✨ CACHE ZA TABOVE - kreira se samo jednom!
        self.tabs_cache = {}
        self.current_tab = None

        # Layout
        self._create_sidebar()
        self._create_main_area()

        # Prikaži Dashboard (lazy load)
        self.show_dashboard()

    def _create_sidebar(self):
        """Kreira sidebar sa navigacijom."""
        self.sidebar = ctk.CTkFrame(
            self,
            width=250,
            corner_radius=0,
            fg_color=theme.colors["surface"]
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Logo/Header
        header = ctk.CTkFrame(
            self.sidebar,
            fg_color=theme.colors["primary"],
            corner_radius=0,
            height=100
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="🏦 Wizvod",
            font=theme.get_font("title"),
            text_color="white"
        ).pack(expand=True)

        # Navigation buttons
        nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_frame.pack(fill="both", expand=True, padx=15, pady=20)

        self.nav_buttons = {}

        buttons = [
            ("📊 Dashboard", "dashboard"),
            ("🏢 Klijenti", "clients"),
            ("📧 Email nalozi", "accounts"),
            ("📜 Istorija", "history"),
            ("⏰ Scheduler", "scheduler"),
            ("⚙️ Podešavanja", "settings"),
        ]

        for text, tab_id in buttons:
            btn = ctk.CTkButton(
                nav_frame,
                text=text,
                command=lambda tid=tab_id: self._show_tab(tid),
                height=45,
                corner_radius=8,
                fg_color="transparent",
                text_color=theme.colors["text"],
                hover_color=theme.colors["primary_hover"],
                anchor="w",
                font=theme.get_font("body")
            )
            btn.pack(fill="x", pady=5)
            self.nav_buttons[tab_id] = btn

        # Footer
        footer = ctk.CTkLabel(
            self.sidebar,
            text="v2.0 © 2025",
            font=theme.get_font("small"),
            text_color=theme.colors["text_secondary"]
        )
        footer.pack(side="bottom", pady=15)

    def _create_main_area(self):
        """Kreira glavni radni prostor."""
        self.main_area = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color=theme.colors["background"]
        )
        self.main_area.pack(side="right", fill="both", expand=True)

    # ================================================================
    # ⚡ OPTIMIZOVANO SWITCHANJE TABOVA
    # ================================================================
    def _show_tab(self, tab_id: str):
        """
        Prikazuje tab sa cachingom.

        OPTIMIZACIJA:
        - Tab se kreira samo prvi put
        - Sledeći put samo hide/show
        - 10x brže od destroy/create
        """
        # Sakrij trenutni tab
        if self.current_tab:
            if self.current_tab in self.tabs_cache:
                current = self.tabs_cache[self.current_tab]
                if hasattr(current, "frame"):
                    current.frame.pack_forget()
                else:
                    current.pack_forget()

        # Učitaj tab iz cache ili kreiraj novi
        if tab_id not in self.tabs_cache:
            self._create_tab(tab_id)

        # Prikaži tab
        if tab_id in self.tabs_cache:
            tab = self.tabs_cache[tab_id]

            # ako klasa ima frame (kao DashboardTab)
            if hasattr(tab, "frame"):
                tab.frame.pack(fill="both", expand=True)
            else:
                tab.pack(fill="both", expand=True)

            # Refresh ako postoji
            if hasattr(tab, "on_tab_shown"):
                tab.on_tab_shown()

            # Refresh podataka (asinhrono ako je moguće)
            if hasattr(tab, 'on_tab_shown'):
                tab.on_tab_shown()

        self.current_tab = tab_id
        self._highlight_button(tab_id)

    def _create_tab(self, tab_id: str):
        """Kreira tab i dodaje ga u cache."""
        tab_classes = {
            'dashboard': DashboardTab,
            'clients': ClientsTab,
            'accounts': AccountsTab,
            'history': HistoryTab,
            'scheduler': SchedulerTab,
            'settings': SettingsTab,
        }

        if tab_id in tab_classes:
            tab_class = tab_classes[tab_id]
            tab_instance = tab_class(self.main_area, self.db)
            self.tabs_cache[tab_id] = tab_instance

    def _highlight_button(self, tab_id: str):
        """Highlightuje aktivno dugme."""
        for tid, btn in self.nav_buttons.items():
            if tid == tab_id:
                btn.configure(
                    fg_color=theme.colors["primary"],
                    text_color="white"
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=theme.colors["text"]
                )

    # ================================================================
    # JAVNI API (za kompatibilnost)
    # ================================================================
    def show_dashboard(self):
        self._show_tab('dashboard')

    def show_clients(self):
        self._show_tab('clients')

    def show_accounts(self):
        self._show_tab('accounts')

    def show_history(self):
        self._show_tab('history')

    def show_scheduler(self):
        self._show_tab('scheduler')

    def show_settings(self):
        self._show_tab('settings')

    def refresh_current_tab(self):
        """Osvježava trenutno prikazan tab."""
        if self.current_tab and self.current_tab in self.tabs_cache:
            tab = self.tabs_cache[self.current_tab]
            if hasattr(tab, 'refresh'):
                tab.refresh()

    def invalidate_tab(self, tab_id: str):
        """
        Uklanja tab iz cache-a (forsira ponovno kreiranje).

        Koristi nakon velikih promjena u podacima.
        """
        if tab_id in self.tabs_cache:
            tab = self.tabs_cache[tab_id]
            if hasattr(tab, 'frame'):
                tab.frame.destroy()
            del self.tabs_cache[tab_id]

    def on_closing(self):
        """Cleanup pri zatvaranju."""
        try:
            # Očisti cache
            for tab in self.tabs_cache.values():
                if hasattr(tab, 'cleanup'):
                    tab.cleanup()

            self.db.close()
        except:
            pass

        self.destroy()


# ---------------------------
# 🚀 Pokretanje aplikacije
# ---------------------------
def run_app():
    """Pokreće glavnu Wizvod GUI aplikaciju."""
    app = MainApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    run_app()
