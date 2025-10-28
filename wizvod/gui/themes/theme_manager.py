import customtkinter as ctk

# 🎨 Tailwind-inspirisana paleta boja
COLORS = {
    "light": {
        "background": "#ffffff",        # Glavna pozadina
        "surface": "#f8fafc",           # Površine (kartice, boxovi)
        "primary": "#2563eb",           # Glavna plava
        "primary_hover": "#1e40af",     # Hover plava
        "accent": "#06b6d4",            # Tirkizna (cyan)
        "accent_hover": "#0891b2",
        "purple": "#9333ea",            # Ljubičasta za licence
        "purple_hover": "#7e22ce",
        "success": "#059669",           # Zelena
        "error": "#dc2626",             # Crvena
        "warning": "#f59e0b",           # Žuta
        "text": "#0f172a",              # Glavni tekst
        "text_secondary": "#475569",    # Sekundarni tekst
        "border": "#e2e8f0",            # Obrubi i linije
    },
    "dark": {
        "background": "#0b0f19",        # Glavna tamna pozadina
        "surface": "#111827",           # Površine
        "primary": "#3b82f6",           # Svjetlija plava
        "primary_hover": "#60a5fa",     # Hover u tamnoj temi
        "accent": "#06b6d4",
        "accent_hover": "#0891b2",
        "purple": "#a855f7",
        "purple_hover": "#9333ea",
        "success": "#10b981",
        "error": "#ef4444",
        "warning": "#fbbf24",
        "text": "#f1f5f9",
        "text_secondary": "#94a3b8",
        "border": "#1e293b",
    }
}

# ⚙️ Layout sistem
SPACING = {
    "padding": 20,
    "radius": 10,
    "gap": 15
}


class ThemeManager:
    """Centralizovano upravljanje stilovima i temama."""

    def __init__(self):
        self.mode = "light"
        self.colors = COLORS[self.mode]

    # -----------------------------
    # 🌗 Tema: light / dark
    # -----------------------------
    def set_mode(self, mode: str):
        """Postavi temu (light / dark)."""
        self.mode = mode.lower()
        ctk.set_appearance_mode(self.mode)
        self.colors = COLORS[self.mode]
        return self.colors

    # -----------------------------
    # 🎨 Boje
    # -----------------------------
    def get_color(self, name: str):
        """Vrati hex vrijednost boje prema nazivu."""
        return self.colors.get(name, "#ffffff")

    # -----------------------------
    # 🖋️ Fontovi
    # -----------------------------
    def get_font(self, name: str):
        """Centralizovani fontovi."""
        fonts = {
            "title": ctk.CTkFont(size=26, weight="bold"),
            "subtitle": ctk.CTkFont(size=18, weight="bold"),
            "body": ctk.CTkFont(size=13),
            "body_bold": ctk.CTkFont(size=13, weight="bold"),
            "button": ctk.CTkFont(size=13, weight="bold"),
            "small": ctk.CTkFont(size=11),
        }
        return fonts.get(name, fonts["body"])

    # -----------------------------
    # 📏 Layout
    # -----------------------------
    def get_spacing(self, key: str):
        """Vrati vrijednost paddinga, radiusa, itd."""
        return SPACING.get(key, 10)

    # -----------------------------
    # 🌈 Stilizovanje komponenti
    # -----------------------------
    def apply_surface_style(self, frame: ctk.CTkFrame):
        """Stilizuje kartice, kontejnere, boxeve."""
        frame.configure(
            fg_color=self.get_color("surface"),
            corner_radius=self.get_spacing("radius")
        )

    def apply_entry_style(self, entry: ctk.CTkEntry):
        """Stilizuje polja za unos."""
        entry.configure(
            corner_radius=self.get_spacing("radius"),
            border_width=1,
            border_color=self.get_color("border"),
            font=self.get_font("body"),
            text_color=self.get_color("text"),
        )

    def apply_label_style(self, label: ctk.CTkLabel, kind="body"):
        """Stilizuje tekstualne labele."""
        font = self.get_font("body" if kind == "body" else "body_bold")
        label.configure(
            font=font,
            text_color=self.get_color("text")
        )

    def apply_button_style(self, widget, style="primary"):
        """Primijeni standardni stil na CTkButton ili CTkOptionMenu."""
        color_map = {
            "primary": self.get_color("primary"),
            "accent": self.get_color("accent"),
            "success": self.get_color("success"),
            "error": self.get_color("error"),
        }

        fg = color_map.get(style, self.get_color("primary"))
        hover = (
            self.get_color("primary_hover")
            if style == "primary"
            else self.get_color("text_secondary")
        )

        # 🟦 CTkButton
        if isinstance(widget, ctk.CTkButton):
            widget.configure(
                fg_color=fg,
                hover_color=hover,
                corner_radius=self.get_spacing("radius"),
                font=self.get_font("button"),
                text_color="#ffffff"
            )

        # 🟣 CTkOptionMenu (nema hover_color)
        elif isinstance(widget, ctk.CTkOptionMenu):
            widget.configure(
                fg_color=fg,
                button_color=fg,
                corner_radius=self.get_spacing("radius"),
                font=self.get_font("button"),
                text_color="#ffffff"
            )

        # 🔹 fallback za druge widgete
        else:
            try:
                widget.configure(fg_color=fg)
            except Exception:
                pass

    def apply_scrollable_style(self, scroll_frame: ctk.CTkScrollableFrame):
        """Blago prilagodjen scroll izgled."""
        scroll_frame.configure(fg_color=self.get_color("background"))


# 🔄 Globalna instanca
theme = ThemeManager()
