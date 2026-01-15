"""
Login dialog for P4 authentication
Provides password input dialog with error handling
"""
import tkinter as tk
from tkinter import ttk, messagebox


class LoginDialog:
    """Dialog for P4 password authentication"""
    
    def __init__(self, parent):
        self.parent = parent
        self.password = None
        self.cancelled = False
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("P4 Login Required")
        self.dialog.geometry("400x200")
        self.dialog.resizable(False, False)
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog relative to parent
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (200 // 2)
        self.dialog.geometry(f"400x200+{x}+{y}")
        
        self.create_widgets()
        
        # Focus on password entry
        self.password_entry.focus_set()
        
        # Handle window close
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_cancel)
        
    def create_widgets(self):
        """Create dialog widgets"""
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # Title label
        title_label = ttk.Label(
            main_frame, 
            text="P4 Authentication Required", 
            font=("Arial", 12, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        # Instruction label
        instruction_label = ttk.Label(
            main_frame, 
            text="Please enter your P4 password:"
        )
        instruction_label.pack(pady=(0, 10))
        
        # Password entry frame
        password_frame = ttk.Frame(main_frame)
        password_frame.pack(fill="x", pady=(0, 20))
        
        ttk.Label(password_frame, text="Password:").pack(anchor="w")
        
        self.password_entry = ttk.Entry(
            password_frame, 
            show="*", 
            width=30
        )
        self.password_entry.pack(fill="x", pady=(5, 0))
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x")
        
        # OK button
        ok_button = ttk.Button(
            button_frame, 
            text="OK", 
            command=self.on_ok,
            width=10
        )
        ok_button.pack(side="right", padx=(5, 0))
        
        # Cancel button
        cancel_button = ttk.Button(
            button_frame, 
            text="Cancel", 
            command=self.on_cancel,
            width=10
        )
        cancel_button.pack(side="right")
        
        # Bind Enter key to OK
        self.password_entry.bind("<Return>", lambda event: self.on_ok())
        self.dialog.bind("<Return>", lambda event: self.on_ok())
        
        # Bind Escape key to Cancel
        self.dialog.bind("<Escape>", lambda event: self.on_cancel())
        
    def on_ok(self):
        """Handle OK button click"""
        password = self.password_entry.get().strip()
        
        if not password:
            messagebox.showerror("Error", "Password cannot be empty")
            return
            
        self.password = password
        self.dialog.destroy()
        
    def on_cancel(self):
        """Handle Cancel button click or window close"""
        self.cancelled = True
        self.dialog.destroy()
        
    def show_error(self, message):
        """Show error message in the dialog"""
        messagebox.showerror("Login Failed", message)
        # Clear password entry and focus back
        self.password_entry.delete(0, tk.END)
        self.password_entry.focus_set()
        
    def get_password(self):
        """Get the entered password (returns None if cancelled)"""
        return self.password
        
    def was_cancelled(self):
        """Check if user cancelled the dialog"""
        return self.cancelled


def show_login_dialog(parent, error_message=None):
    """
    Convenience function to show login dialog
    
    Args:
        parent: Parent window
        error_message: Optional error message to display
        
    Returns:
        tuple: (password, cancelled) where password is string or None, cancelled is bool
    """
    dialog = LoginDialog(parent)
    
    # Show error message if provided (after dialog is displayed)
    if error_message:
        dialog.dialog.after(100, lambda: dialog.show_error(error_message))
    
    # Wait for dialog to close
    dialog.dialog.wait_window()
    
    return dialog.get_password(), dialog.was_cancelled()
