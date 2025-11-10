"""
Main window implementation for the Tuning Tool
Handles the main application window, navigation tabs, and mode switching
Updated to support enhanced 3-path tuning functionality, System bringup, Readahead mode, and LoadApkAsset mode
"""

import tkinter as tk
from tkinter import ttk, messagebox
from config.p4_config import initialize_p4_config, check_p4_login_status, p4_login
from gui.bringup_tab import BringupTab
from gui.tuning_tab import TuningTab
from gui.parse_tab import ParseTab
from gui.readahead_tab import ReadaheadTab
from gui.loadapkasset_tab import LoadApkAssetTab
from gui.gui_utils import GUIUtils
from gui.login_dialog import show_login_dialog


class BringupToolGUI:
    """Main GUI class for the Tuning Tool with Parse Mode, Enhanced Tuning, Readahead, and LoadApkAsset"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("P4 tool")
        self.root.geometry("1200x900")  # Increased size for additional modes
        self.root.minsize(800, 900)

        # Current mode
        self.current_mode = tk.StringVar(value="bringup")

        # Initialize P4 configuration silently
        initialize_p4_config()

        # Check P4 login status and handle authentication
        if not self.handle_p4_authentication():
            # If authentication failed or user cancelled, exit
            self.root.destroy()
            return

        # Initialize GUI utilities
        self.gui_utils = GUIUtils(self.root)

        # Initialize tab components
        self.bringup_tab = None
        self.tuning_tab = None
        self.parse_tab = None
        self.readahead_tab = None
        self.loadapkasset_tab = None

        # Create GUI components
        self.create_navbar()
        self.create_main_content()
        self.create_status_bar()

        # Set default mode
        self.switch_mode("bringup")

    def create_navbar(self):
        """Create navigation tabs"""
        # Create navbar frame
        navbar_frame = ttk.Frame(self.root)
        navbar_frame.pack(fill="x", padx=10, pady=(10, 0))

        # Create notebook for tabs
        self.notebook = ttk.Notebook(navbar_frame)
        self.notebook.pack(fill="x")

        # Create frames for each tab
        self.bringup_tab_frame = ttk.Frame(self.notebook)
        self.tuning_tab_frame = ttk.Frame(self.notebook)
        self.parse_tab_frame = ttk.Frame(self.notebook)
        self.readahead_tab_frame = ttk.Frame(self.notebook)
        self.loadapkasset_tab_frame = ttk.Frame(self.notebook)

        # Add tabs to notebook
        self.notebook.add(self.bringup_tab_frame, text="Bring up")
        self.notebook.add(self.tuning_tab_frame, text="Tuning value")
        self.notebook.add(self.parse_tab_frame, text="Parse")
        self.notebook.add(self.readahead_tab_frame, text="Readahead")
        self.notebook.add(self.loadapkasset_tab_frame, text="LoadApkAsset")

        # Bind tab change event
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def create_main_content(self):
        """Create main content area"""
        # Main content frame
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Initialize tab components
        self.bringup_tab = BringupTab(self.main_frame, self.gui_utils)
        self.tuning_tab = TuningTab(self.main_frame, self.gui_utils)
        self.parse_tab = ParseTab(self.main_frame, self.gui_utils)
        self.readahead_tab = ReadaheadTab(self.main_frame, self.gui_utils)
        self.loadapkasset_tab = LoadApkAssetTab(self.main_frame, self.gui_utils)

    def create_status_bar(self):
        """Create status bar"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill="x", side="bottom")

        # Status label (left side)
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(
            status_frame, textvariable=self.status_var, relief="sunken"
        )
        status_label.pack(side="left", fill="x", expand=True)

        # Clear button (right side)
        clear_btn = ttk.Button(status_frame, text="Clear", command=self.on_clear)
        clear_btn.pack(side="right", padx=5, pady=2)

        # Set status variable in GUI utils
        self.gui_utils.set_status_var(self.status_var)

    def on_tab_changed(self, event):
        """Handle tab change events"""
        selected_tab = self.notebook.select()
        tab_text = self.notebook.tab(selected_tab, "text")

        if tab_text == "Bring up":
            self.switch_mode("bringup")
        elif "Tuning value" in tab_text:  # Support both old and new tab names
            self.switch_mode("tuning")
        elif tab_text == "Parse":
            self.switch_mode("parse")
        elif tab_text == "Readahead":
            self.switch_mode("readahead")
        elif tab_text == "LoadApkAsset":
            self.switch_mode("loadapkasset")

    def switch_mode(self, mode):
        """Switch between different modes"""
        self.current_mode.set(mode)

        # Hide all frames first
        for widget in self.main_frame.winfo_children():
            widget.pack_forget()

        if mode == "bringup":
            self.bringup_tab.show()
            self.status_var.set(
                "Mode: Bring up - Vendor: depot paths | System: workspaces (TEMPLATE_*)"
            )
        elif mode == "tuning":
            self.tuning_tab.show()
            self.status_var.set(
                "Mode: Tuning value - Load properties from BENI, FLUMEN, and REL paths"
            )
        elif mode == "parse":
            self.parse_tab.show()
            self.status_var.set(
                "Mode: Parse - Calculate library size"
            )
        elif mode == "readahead":
            self.readahead_tab.show()
            self.status_var.set(
                "Mode: Readahead - Configure REL/FLUMEN/BENI workspaces and libraries for rscmgr.rc modification"
            )
        elif mode == "loadapkasset":
            self.loadapkasset_tab.show()
            self.status_var.set(
                "Mode: LoadApkAsset - Add asset apps to chipsets in ReadaheadManager.java"
            )

    def on_clear(self):
        """Clear all input fields based on current mode"""
        if self.current_mode.get() == "bringup":
            self.bringup_tab.clear_all()
        elif self.current_mode.get() == "tuning":
            self.tuning_tab.clear_all()
        elif self.current_mode.get() == "parse":
            self.parse_tab.clear_all()
        elif self.current_mode.get() == "readahead":
            self.readahead_tab.clear_all()
        elif self.current_mode.get() == "loadapkasset":
            self.loadapkasset_tab.clear_all()

    def handle_p4_authentication(self):
        """Handle P4 authentication with infinite retry logic"""
        # Check if already logged in
        if check_p4_login_status():
            return True
            
        # Infinite retry loop for login
        while True:
            # Show login dialog
            password, cancelled = show_login_dialog(self.root)
            
            # If user cancelled, exit application
            if cancelled:
                messagebox.showinfo("Application Exit", "P4 authentication is required to use this application.")
                return False
            
            # Try to login with provided password
            if p4_login(password):
                # Login successful
                return True
            else:
                # Login failed, show error and continue loop
                messagebox.showerror("Login Failed", "Authentication failed. Please check your password and try again.")

    def run(self):
        """Start the GUI main loop"""
        self.root.mainloop()


def create_gui():
    """Create and run the GUI application"""
    try:
        app = BringupToolGUI()
        app.run()
    except Exception as e:
        # Show error dialog if GUI creation fails
        root = tk.Tk()
        root.withdraw()  # Hide the empty window
        from tkinter import messagebox
        messagebox.showerror("Application Error", f"Failed to start application: {e}")
        root.destroy()
