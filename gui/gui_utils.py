"""
GUI utilities and shared callback functions
Handles thread-safe GUI operations, logging, and error dialogs
"""

import tkinter as tk
from tkinter import messagebox


class GUIUtils:
    """Utility class for GUI operations and callbacks"""

    def __init__(self, root):
        self.root = root
        self.status_var = None

    def set_status_var(self, status_var):
        """Set the status variable for status updates"""
        self.status_var = status_var

    def create_log_callback(self, log_text_widget):
        """Create a thread-safe logging callback for a text widget"""
        def log_callback(msg):
            def update_log():
                log_text_widget.insert(tk.END, msg + "\n")
                log_text_widget.see(tk.END)
                self.root.update_idletasks()
            self.root.after(0, update_log)
        return log_callback

    def create_progress_callback(self, progress_widget):
        """Create a thread-safe progress update callback"""
        def progress_callback(value):
            def update_progress():
                progress_widget["value"] = value
                self.root.update_idletasks()
            self.root.after(0, update_progress)
        return progress_callback

    def error_callback(self, title, message):
        """Thread-safe error dialog"""
        def show_error():
            messagebox.showerror(title, message)
        self.root.after(0, show_error)

    def info_callback(self, title, message):
        """Thread-safe info dialog"""
        def show_info():
            messagebox.showinfo(title, message)
        self.root.after(0, show_info)

    def update_status(self, message):
        """Update status bar message"""
        if self.status_var:
            self.status_var.set(message)

    def clear_text_widget(self, text_widget):
        """Clear a text widget"""
        text_widget.delete("1.0", tk.END)

    def reset_progress(self, progress_widget):
        """Reset progress bar to 0"""
        progress_widget["value"] = 0

    def create_text_with_scrollbar(self, parent, height=20, bg="#1e1e1e", fg="#00ff88"):
        """Create a text widget with scrollbar"""
        text_frame = ttk.Frame(parent)
        text_frame.pack(fill="both", expand=True)

        text_widget = tk.Text(
            text_frame,
            height=height,
            wrap="word",
            bg=bg,
            fg=fg,
            font=("Consolas", 9),
        )
        scrollbar = ttk.Scrollbar(
            text_frame, orient="vertical", command=text_widget.yview
        )
        text_widget.configure(yscrollcommand=scrollbar.set)

        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        return text_widget


# Import ttk for the create_text_with_scrollbar method
from tkinter import ttk