"""
Property dialog component
Dialog for adding and editing properties in the tuning tab
"""

import tkinter as tk
from tkinter import ttk, messagebox


class PropertyDialog:
    """Dialog for adding/editing properties"""

    def __init__(self, parent, title, prop_name="", prop_value=""):
        self.result = None

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x200")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.geometry(
            "+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50)
        )

        # Property name
        ttk.Label(self.dialog, text="Property Name:").pack(pady=5)
        self.name_entry = ttk.Entry(self.dialog, width=50)
        self.name_entry.pack(pady=5)
        self.name_entry.insert(0, prop_name)

        # Property value
        ttk.Label(self.dialog, text="Property Value:").pack(pady=5)
        self.value_entry = ttk.Entry(self.dialog, width=50)
        self.value_entry.pack(pady=5)
        self.value_entry.insert(0, prop_value)

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=20)

        ttk.Button(button_frame, text="OK", command=self.ok_clicked).pack(
            side="left", padx=5
        )
        ttk.Button(button_frame, text="Cancel", command=self.cancel_clicked).pack(
            side="left", padx=5
        )

        # Focus on name entry
        self.name_entry.focus()

        # Bind Enter key
        self.dialog.bind("<Return>", lambda e: self.ok_clicked())
        self.dialog.bind("<Escape>", lambda e: self.cancel_clicked())

        # Wait for dialog to close
        self.dialog.wait_window()

    def ok_clicked(self):
        """Handle OK button click"""
        prop_name = self.name_entry.get().strip()
        prop_value = self.value_entry.get().strip()

        if not prop_name:
            messagebox.showerror("Invalid Input", "Property name cannot be empty.")
            return

        self.result = (prop_name, prop_value)
        self.dialog.destroy()

    def cancel_clicked(self):
        """Handle Cancel button click"""
        self.result = None
        self.dialog.destroy()