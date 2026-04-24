"""
Shared UI components for Receipt OCR GUI.
"""

import tkinter as tk
from tkinter import ttk

# Import theme with fallback
import sys
from pathlib import Path

# Add gui directory to path if not already there
gui_dir = Path(__file__).parent
if str(gui_dir) not in sys.path:
    sys.path.insert(0, str(gui_dir))

try:
    from theme import theme
except ImportError as e:
    print(f"FATAL: Could not import theme in components.py: {e}")
    raise


class DropZone:
    """Drag and drop zone component."""

    def __init__(self, parent, on_drop_callback, has_dnd=True):
        self.parent = parent
        self.on_drop_callback = on_drop_callback
        self.has_dnd = has_dnd

        # Create modern drop zone frame
        self.frame = tk.Frame(parent, bg=theme.CLR_SURFACE, relief=tk.SOLID,
                             bd=1, height=120, highlightbackground=theme.CLR_BORDER)
        self.frame.pack(fill=tk.X, padx=24, pady=12)
        self.frame.pack_propagate(False)

        # Create label with icon
        self.label = theme.create_label(
            self.frame,
            text="📎 Drag & drop image / PDF here\nor click Browse above",
            font=("Arial", 11),
            fg=theme.CLR_SUBTEXT,
            bg=theme.CLR_SURFACE
        )
        self.label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Add subtle instructions
        self.sub_label = theme.create_label(
            self.frame,
            text="Supports: .jpg, .png, .pdf",
            font=("Arial", 9),
            fg=theme.CLR_SUBTEXT,
            bg=theme.CLR_SURFACE
        )
        self.sub_label.place(relx=0.5, rely=0.8, anchor=tk.CENTER)

        # Setup drag and drop if available
        if has_dnd:
            self._setup_drag_drop()

        # Add hover effect
        self.frame.bind("<Enter>", lambda e: self.frame.config(bg=theme.CLR_HOVER))
        self.frame.bind("<Leave>", lambda e: self.frame.config(bg=theme.CLR_SURFACE))

    def _setup_drag_drop(self):
        """Setup drag and drop functionality - simpler version."""
        try:
            from tkinterdnd2 import DND_FILES
            # Make the frame a drop target
            self.frame.drop_target_register(DND_FILES)
            self.frame.dnd_bind("<<Drop>>", self._on_drop)
            print("Drag & drop enabled on drop zone")
        except Exception as e:
            print(f"Drag & drop setup error: {e}")
            self.has_dnd = False

    def _on_drop(self, event):
        """Handle file drop - simpler version following previous GUI.py pattern."""
        # Extract file path from event data
        # The format depends on tkinterdnd2 version
        try:
            # Try to split the file list
            if hasattr(event, 'data'):
                files = self.parent.tk.splitlist(event.data)
                if files:
                    self.on_drop_callback(files[0])
        except Exception as e:
            print(f"Error processing drop: {e}")
            print(f"Event data: {event.data if hasattr(event, 'data') else 'No data'}")

    def enable(self):
        """Enable the drop zone."""
        self.frame.config(state=tk.NORMAL)

    def disable(self):
        """Disable the drop zone."""
        self.frame.config(state=tk.DISABLED)


class ProcessingSpinner:
    """Cute processing spinner component."""

    def __init__(self, parent, status_label):
        self.parent = parent
        self.status_label = status_label
        self.is_spinning = False
        self.spin_var = tk.IntVar(value=0)
        self.spin_frames = theme.EMOJI_SPINNER

    def start(self):
        """Start the spinner animation."""
        self.is_spinning = True
        self._animate()

    def stop(self, message="Ready"):
        """Stop the spinner animation."""
        self.is_spinning = False
        self.status_label.config(text=message)

    def _animate(self):
        """Animate the spinner."""
        if self.is_spinning:
            idx = self.spin_var.get()
            self.status_label.config(text=self.spin_frames[idx])
            self.spin_var.set((idx + 1) % len(self.spin_frames))
            self.parent.after(120, self._animate)


class ResultDisplay:
    """Result display component with text area, scrollbar, and drag & drop support."""

    def __init__(self, parent, on_drop_callback=None):
        self.parent = parent
        self.text_out = None
        self.scrollbar = None
        self.on_drop_callback = on_drop_callback
        self._build()

    def _build(self):
        """Build the result display area."""
        # Frame for result display
        frame = theme.create_frame(self.parent, bg=theme.CLR_BG)
        frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 12))
        frame.pack_propagate(False)

        # Text area with scrollbar
        self.text_out, self.scrollbar = theme.create_text_area(frame)
        self.text_out.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Setup drag and drop on text widget
        self._setup_drag_drop()

        # Setup mouse wheel scrolling
        self._setup_mouse_wheel()

    def _setup_drag_drop(self):
        """Setup drag and drop on the text widget."""
        if self.on_drop_callback:
            try:
                from tkinterdnd2 import DND_FILES
                self.text_out.drop_target_register(DND_FILES)
                self.text_out.dnd_bind('<<Drop>>', self._on_drop)
            except Exception as e:
                print(f"ResultDisplay DnD setup error: {e}")

    def _setup_mouse_wheel(self):
        """Setup mouse wheel scrolling for the text widget."""
        # Bind mouse wheel to scroll the text widget
        self.text_out.bind("<MouseWheel>", self._on_mouse_wheel)
        self.text_out.bind("<Button-4>", self._on_mouse_wheel)  # Linux scroll up
        self.text_out.bind("<Button-5>", self._on_mouse_wheel)  # Linux scroll down

        # Also bind to the parent frame for better coverage
        self.text_out.master.bind("<MouseWheel>", self._on_mouse_wheel)
        self.text_out.master.bind("<Button-4>", self._on_mouse_wheel)
        self.text_out.master.bind("<Button-5>", self._on_mouse_wheel)

    def _on_mouse_wheel(self, event):
        """Handle mouse wheel scrolling for text widget."""
        # Windows and Mac: event.delta
        # Linux: event.num (4=up, 5=down)
        if event.num == 4:  # Linux scroll up
            self.text_out.yview_scroll(-1, "units")
        elif event.num == 5:  # Linux scroll down
            self.text_out.yview_scroll(1, "units")
        elif hasattr(event, 'delta'):
            # Windows/Mac: negative delta = scroll down, positive = scroll up
            # Standardize: scroll down = move down in content
            # On Windows, delta is typically 120 or -120
            if event.delta > 0:
                self.text_out.yview_scroll(-1, "units")
            else:
                self.text_out.yview_scroll(1, "units")
        return "break"

    def _on_drop(self, event):
        """Handle file drop on text widget."""
        if self.on_drop_callback:
            try:
                files = self.parent.tk.splitlist(event.data)
                if files:
                    self.on_drop_callback(files[0])
            except Exception as e:
                print(f"Error processing drop on text widget: {e}")

    def log(self, message):
        """Add a message to the display."""
        self.text_out.config(state=tk.NORMAL)
        self.text_out.insert(tk.END, message + "\n")
        self.text_out.see(tk.END)
        self.text_out.config(state=tk.NORMAL)

    def clear(self):
        """Clear the display."""
        self.text_out.config(state=tk.NORMAL)
        self.text_out.delete(1.0, tk.END)

    def set_content(self, content):
        """Set the content of the display."""
        self.clear()
        self.log(content)


class ConfidenceMeter:
    """Confidence score display component."""

    def __init__(self, parent, label_text="Confidence:"):
        self.parent = parent
        self.score = 0.0
        self.frame = None
        self.label = None
        self.meter = None
        self.score_label = None
        self._build(label_text)

    def _build(self, label_text):
        """Build the confidence meter."""
        self.frame = theme.create_frame(self.parent)
        self.frame.pack(fill=tk.X, padx=24, pady=(8, 0))

        # Label
        self.label = theme.create_label(
            self.frame,
            text=f"📊 {label_text}",
            font=("Arial", 10, "bold"),
            fg=theme.CLR_TEXT
        )
        self.label.pack(side=tk.LEFT, padx=(0, 12))

        # Meter (progress bar)
        self.meter = ttk.Progressbar(
            self.frame,
            length=180,
            mode='determinate',
            style="Horizontal.TProgressbar"
        )
        self.meter.pack(side=tk.LEFT, padx=(0, 12))

        # Score label with colored badge
        self.score_label = tk.Label(
            self.frame,
            text="0.0",
            font=("Arial", 10, "bold"),
            bg=theme.CLR_SURFACE,
            fg=theme.CLR_SUBTEXT,
            padx=8,
            pady=2,
            relief=tk.SOLID,
            bd=1,
            borderwidth=1
        )
        self.score_label.pack(side=tk.LEFT)

    def update(self, score):
        """Update the confidence score display."""
        # Validate score input
        try:
            score = float(score)
        except (ValueError, TypeError):
            print(f"WARNING: Invalid confidence score: {score}, defaulting to 0.0")
            score = 0.0

        # Clamp score between 0.0 and 1.0
        score = max(0.0, min(1.0, score))

        self.score = score
        self.meter['value'] = score * 100

        # Update color based on score
        if score >= 0.8:
            color = theme.CLR_SUCCESS
            bg_color = theme.CLR_SUCCESS_LIGHT
            text = f"{score:.1f} ✅"
        elif score >= 0.6:
            color = theme.CLR_WARNING
            bg_color = theme.CLR_WARNING_LIGHT
            text = f"{score:.1f} ⚠️"
        else:
            color = theme.CLR_ERROR
            bg_color = theme.CLR_ERROR_LIGHT
            text = f"{score:.1f} ❌"

        self.score_label.config(text=text, fg=color, bg=bg_color)

    def get_score(self):
        """Get the current confidence score."""
        return self.score


class CacheStatusDisplay:
    """Vendor cache status display component."""

    def __init__(self, parent):
        self.parent = parent
        self.vendor_name = None
        self.trust_score = 0.0
        self.cache_hit = False
        self.frame = None
        self._build()

    def _build(self):
        """Build the cache status display."""
        self.frame = theme.create_frame(self.parent)
        self.frame.pack(fill=tk.X, padx=24, pady=(5, 0))

        # Status label
        self.status_label = theme.create_label(
            self.frame,
            text="Cache: Not used",
            font=theme.FONT_SMALL,
            fg=theme.CLR_SUBTEXT
        )
        self.status_label.pack(side=tk.LEFT)

        # Improve cache button (hidden by default)
        self.improve_button = theme.create_button(
            self.frame,
            text="Improve Cache",
            command=self._on_improve_cache,
            style="warning",
            emoji=theme.EMOJI_WARNING
        )
        self.improve_button.pack(side=tk.RIGHT)
        self.improve_button.pack_forget()  # Hide initially

    def update(self, vendor_name=None, trust_score=0.0, cache_hit=False):
        """Update the cache status display."""
        self.vendor_name = vendor_name
        self.trust_score = trust_score
        self.cache_hit = cache_hit

        if cache_hit and vendor_name:
            status_text = f"Cache: {vendor_name} (score: {trust_score:.1f})"
            if trust_score >= 0.8:
                self.status_label.config(text=status_text + " ✅", fg=theme.CLR_SUCCESS)
                self.improve_button.pack_forget()
            elif trust_score >= 0.6:
                self.status_label.config(text=status_text + " ⚠️", fg=theme.CLR_WARNING)
                self.improve_button.pack(side=tk.RIGHT)
            else:
                self.status_label.config(text=status_text + " ❌", fg=theme.CLR_ERROR)
                self.improve_button.pack(side=tk.RIGHT)
        else:
            self.status_label.config(text="Cache: Not used", fg=theme.CLR_SUBTEXT)
            self.improve_button.pack_forget()

    def _on_improve_cache(self):
        """Handle improve cache button click."""
        # This will be connected to the main app's cache improvement function
        print(f"Improve cache for vendor: {self.vendor_name}")

    def set_improve_callback(self, callback):
        """Set callback for improve cache button."""
        self.improve_button.config(command=callback)