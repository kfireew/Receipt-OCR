"""
Clean, functional theme for Receipt OCR GUI.
"""

import tkinter as tk
from tkinter import ttk


class CuteTheme:
    """Simple, working theme with tk.Button instead of ttk for better control."""

    def __init__(self):
        # Clean color scheme
        self.CLR_BG = '#f8fafc'  # Light background
        self.CLR_SURFACE = '#ffffff'  # White surface
        self.CLR_ACCENT = '#3b82f6'  # Blue accent
        self.CLR_SUCCESS = '#10b981'  # Green success
        self.CLR_SUCCESS_LIGHT = '#d1fae5'  # Light green
        self.CLR_WARNING = '#f59e0b'  # Amber warning
        self.CLR_WARNING_LIGHT = '#fef3c7'  # Light amber
        self.CLR_ERROR = '#ef4444'  # Red error
        self.CLR_ERROR_LIGHT = '#fee2e2'  # Light red
        self.CLR_TEXT = '#1e293b'  # Dark text
        self.CLR_SUBTEXT = '#64748b'  # Gray subtext
        self.CLR_BORDER = '#e2e8f0'  # Light border
        self.CLR_HOVER = '#f1f5f9'  # Hover color
        self.CLR_SELECTION = '#dbeafe'  # Selection blue

        # Emojis
        self.EMOJI_RECEIPT = '🧾'
        self.EMOJI_UPLOAD = '📤'
        self.EMOJI_SAVE = '💾'
        self.EMOJI_ADD = '➕'
        self.EMOJI_CACHE = '📁'
        self.EMOJI_REVIEW = '🔍'
        self.EMOJI_SCHEMA = '📋'
        self.EMOJI_SPINNER = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.EMOJI_SUCCESS = '✅'
        self.EMOJI_ERROR = '❌'
        self.EMOJI_WARNING = '⚠️'
        self.EMOJI_INFO = 'ℹ️'

        # Fonts
        self.FONT_TITLE = ("Segoe UI", 14, "bold")
        self.FONT_SUBTITLE = ("Segoe UI", 11)
        self.FONT_BODY = ("Segoe UI", 10)
        self.FONT_SMALL = ("Segoe UI", 9)
        self.FONT_MONO = ("Consolas", 10)
        self.FONT_BUTTON = ("Segoe UI", 10)

    def configure_styles(self, root):
        """Configure ttk styles (minimal)."""
        style = ttk.Style()
        style.theme_use("clam")

        # Basic styles
        style.configure(".", font=self.FONT_BODY)
        style.configure("TFrame", background=self.CLR_BG)
        style.configure("TLabel", background=self.CLR_BG, foreground=self.CLR_TEXT)

        # Scrollbar
        style.configure("Vertical.TScrollbar",
                       background=self.CLR_BORDER,
                       troughcolor=self.CLR_BG,
                       bordercolor=self.CLR_BORDER)

        # Progress bar
        style.configure("Horizontal.TProgressbar",
                       background=self.CLR_ACCENT,
                       troughcolor=self.CLR_BORDER)

        # Treeview
        style.configure("Treeview",
                       background=self.CLR_SURFACE,
                       foreground=self.CLR_TEXT,
                       fieldbackground=self.CLR_SURFACE,
                       borderwidth=1)

        style.configure("Treeview.Heading",
                       background=self.CLR_BG,
                       foreground=self.CLR_TEXT,
                       relief="flat")

        # Configure root window
        root.configure(bg=self.CLR_BG)

    def create_button(self, parent, text, command, style="primary", emoji=None):
        """Create a tk.Button with consistent styling."""
        if emoji:
            text = f"{emoji} {text}"

        # Determine button style
        if style == "primary":
            bg = self.CLR_ACCENT
            fg = "white"
            hover_bg = "#2563eb"
            padx, pady = 12, 6
            border = 0
        elif style == "secondary":
            bg = self.CLR_SURFACE
            fg = self.CLR_TEXT
            hover_bg = self.CLR_HOVER
            padx, pady = 10, 4
            border = 1
        elif style == "success":
            bg = self.CLR_SUCCESS
            fg = "white"
            hover_bg = "#0da271"
            padx, pady = 12, 6
            border = 0
        elif style == "warning":
            bg = self.CLR_WARNING
            fg = "white"
            hover_bg = "#d97706"
            padx, pady = 12, 6
            border = 0
        elif style == "error":
            bg = self.CLR_ERROR
            fg = "white"
            hover_bg = "#dc2626"
            padx, pady = 12, 6
            border = 0
        else:
            bg = self.CLR_SURFACE
            fg = self.CLR_TEXT
            hover_bg = self.CLR_HOVER
            padx, pady = 10, 4
            border = 1

        # Create button
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=self.FONT_BUTTON,
            bg=bg,
            fg=fg,
            relief="raised" if border else "flat",
            borderwidth=border,
            padx=padx,
            pady=pady,
            cursor="hand2",
            activebackground=hover_bg,
            activeforeground=fg
        )

        # Add hover effect
        def on_enter(e):
            btn.config(bg=hover_bg)

        def on_leave(e):
            btn.config(bg=bg)

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)

        return btn

    def create_label(self, parent, text, font=None, fg=None, bg=None, emoji=None, justify=None):
        """Create a label with optional emoji."""
        if emoji:
            text = f"{emoji} {text}"

        if font is None:
            font = self.FONT_BODY
        if fg is None:
            fg = self.CLR_TEXT
        if bg is None:
            bg = self.CLR_BG

        return tk.Label(parent, text=text, font=font, fg=fg, bg=bg, justify=justify)

    def create_frame(self, parent, bg=None, padx=0, pady=0):
        """Create a frame."""
        if bg is None:
            bg = self.CLR_BG
        return tk.Frame(parent, bg=bg, padx=padx, pady=pady)

    def create_entry(self, parent, width=30, font=None):
        """Create an entry field."""
        if font is None:
            font = self.FONT_BODY
        return tk.Entry(parent, font=font, width=width, bg=self.CLR_SURFACE, fg=self.CLR_TEXT,
                       relief=tk.SOLID, borderwidth=1, highlightthickness=0,
                       insertbackground=self.CLR_ACCENT)

    def create_text_area(self, parent, wrap=tk.WORD):
        """Create a text area with scrollbar."""
        text = tk.Text(
            parent, wrap=wrap, bg=self.CLR_SURFACE,
            fg=self.CLR_TEXT, font=self.FONT_MONO,
            insertbackground=self.CLR_TEXT,
            selectbackground=self.CLR_SELECTION,
            relief=tk.FLAT, padx=10, pady=10,
            borderwidth=1
        )

        # Add scrollbar
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)

        return text, scrollbar


# Global theme instance
theme = CuteTheme()