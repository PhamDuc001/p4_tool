"""
Bringup tab implementation
Handles the bringup mode UI and functionality
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from config.p4_config import get_client_name, get_workspace_root
from processes.bringup_process import run_bringup_process


class BringupTab:
    """Bringup tab component"""

    def __init__(self, parent, gui_utils):
        self.parent = parent
        self.gui_utils = gui_utils
        
        # Create the bringup frame
        self.frame = ttk.Frame(parent)
        
        # Initialize components
        self.create_content()

    def create_content(self):
        """Create content for bringup mode"""
        # Input fields frame - Changed from "Configuration" to "Vendor"
        input_frame = ttk.LabelFrame(
            self.frame, text="Vendor", padding=10
        )
        input_frame.pack(fill="x", pady=(0, 10))

        # BENI Path
        ttk.Label(input_frame, text="BENI Depot Path:").grid(
            column=0, row=0, sticky="w", pady=2
        )
        self.beni_entry = ttk.Entry(input_frame, width=70)
        self.beni_entry.grid(column=1, row=0, padx=5, pady=2, sticky="ew")

        # VINCE Path
        ttk.Label(input_frame, text="VINCE Depot Path:").grid(
            column=0, row=1, sticky="w", pady=2
        )
        self.vince_entry = ttk.Entry(input_frame, width=70)
        self.vince_entry.grid(column=1, row=1, padx=5, pady=2, sticky="ew")

        # FLUMEN Path
        ttk.Label(input_frame, text="FLUMEN Depot Path:").grid(
            column=0, row=2, sticky="w", pady=2
        )
        self.flumen_entry = ttk.Entry(input_frame, width=70)
        self.flumen_entry.grid(column=1, row=2, padx=5, pady=2, sticky="ew")

        # REL Path - NEW addition
        ttk.Label(input_frame, text="REL Depot Path:").grid(
            column=0, row=3, sticky="w", pady=2
        )
        self.rel_entry = ttk.Entry(input_frame, width=70)
        self.rel_entry.grid(column=1, row=3, padx=5, pady=2, sticky="ew")

        # Configure grid weights
        input_frame.columnconfigure(1, weight=1)

        # Control frame - Updated row position due to new REL field
        control_frame = ttk.Frame(input_frame)
        control_frame.grid(column=1, row=4, pady=10, sticky="e")

        # Progress bar
        self.progress = ttk.Progressbar(
            control_frame, length=200, mode="determinate"
        )
        self.progress.pack(side="left", padx=(0, 10))

        # Start button
        self.start_btn = ttk.Button(
            control_frame, text="Start Bring up", command=self.on_start
        )
        self.start_btn.pack(side="right")

        # Log output frame - Reduced height as requested
        log_frame = ttk.LabelFrame(self.frame, text="Process Log", padding=5)
        log_frame.pack(fill="both", expand=True)

        # Create text widget with scrollbar - Reduced height from 20 to 12
        self.log_text = self.gui_utils.create_text_with_scrollbar(log_frame, height=12)

        # Create callbacks
        self.log_callback = self.gui_utils.create_log_callback(self.log_text)
        self.progress_callback = self.gui_utils.create_progress_callback(self.progress)

    def show(self):
        """Show the bringup tab"""
        self.frame.pack(fill="both", expand=True)

    def hide(self):
        """Hide the bringup tab"""
        self.frame.pack_forget()

    def clear_all(self):
        """Clear all input fields and logs"""
        # Clear input fields - Added REL field
        self.beni_entry.delete(0, tk.END)
        self.vince_entry.delete(0, tk.END)
        self.flumen_entry.delete(0, tk.END)
        self.rel_entry.delete(0, tk.END)  # NEW

        # Clear log output
        self.gui_utils.clear_text_widget(self.log_text)

        # Reset progress bar
        self.gui_utils.reset_progress(self.progress)

        self.log_callback("[INFO] All fields and logs cleared.")
        # Updated status message to include REL
        self.gui_utils.update_status(
            "Mode: Bring up - VINCE is mandatory, BENI, FLUMEN and REL are optional"
        )

    def on_start(self):
        """Handle bringup start button click"""
        beni_path = self.beni_entry.get().strip()
        vince_path = self.vince_entry.get().strip()
        flumen_path = self.flumen_entry.get().strip()
        rel_path = self.rel_entry.get().strip()  # NEW

        # Validation - VINCE is mandatory
        if not vince_path.startswith("//"):
            messagebox.showerror(
                "Invalid Path",
                "VINCE depot path is mandatory and must start with //depot/...",
            )
            return

        # Check if at least one target (BENI, FLUMEN, or REL) is provided
        has_beni = beni_path and beni_path.startswith("//")
        has_flumen = flumen_path and flumen_path.startswith("//")
        has_rel = rel_path and rel_path.startswith("//")  # NEW

        if not has_beni and not has_flumen and not has_rel:  # Updated condition
            messagebox.showerror(
                "No Target Paths",
                "At least one target path (BENI, FLUMEN, or REL) must be provided and start with //depot/...",
            )
            return

        # Pass REL path to process function
        self._run_process(beni_path, vince_path, flumen_path, rel_path)

    def _run_process(self, beni_path, vince_path, flumen_path, rel_path):  # Added rel_path parameter
        """Run bringup process in separate thread"""
        # Clear log and reset progress
        self.gui_utils.clear_text_widget(self.log_text)
        self.gui_utils.reset_progress(self.progress)

        # Log P4 configuration info
        client_name = get_client_name()
        workspace_root = get_workspace_root()
        if client_name and workspace_root:
            self.log_callback(f"[CONFIG] Using P4 Client: {client_name}")
            self.log_callback(f"[CONFIG] Using Workspace: {workspace_root}")

        # Disable start button during processing
        self.start_btn.configure(state="disabled")

        def run_process_thread():
            try:
                self.gui_utils.update_status("Processing: Running bring up operation...")
                # Updated function call to include rel_path
                run_bringup_process(
                    beni_path,
                    vince_path,
                    flumen_path,
                    rel_path,  # NEW parameter
                    self.log_callback,
                    self.progress_callback,
                    self.gui_utils.error_callback,
                )
            finally:
                # Re-enable button when done
                self.gui_utils.root.after(
                    0, lambda: self.start_btn.configure(state="normal")
                )
                self.gui_utils.root.after(
                    0,
                    lambda: self.gui_utils.update_status("Mode: Bring up - Operation completed"),
                )

        # Start the process in a separate thread
        thread = threading.Thread(target=run_process_thread, daemon=True)
        thread.start()