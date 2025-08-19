"""
Bringup tab implementation
Handles the bringup mode UI and functionality
Updated to include System workspace section
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from config.p4_config import get_client_name, get_workspace_root
from processes.bringup_process import run_bringup_process
from processes.system_process import run_system_process


class BringupTab:
    """Bringup tab component with Vendor and System sections"""

    def __init__(self, parent, gui_utils):
        self.parent = parent
        self.gui_utils = gui_utils
        
        # Create the bringup frame
        self.frame = ttk.Frame(parent)
        
        # Initialize components
        self.create_content()

    def create_content(self):
        """Create content for bringup mode with both Vendor and System sections"""
        # Create main container with scrollable frame
        main_container = ttk.Frame(self.frame)
        main_container.pack(fill="both", expand=True)
        
        # ============================================================================
        # VENDOR SECTION (Original functionality)
        # ============================================================================
        vendor_frame = ttk.LabelFrame(main_container, text="Vendor", padding=10)
        vendor_frame.pack(fill="x", pady=(0, 10))

        # BENI Path
        ttk.Label(vendor_frame, text="BENI Depot Path:").grid(
            column=0, row=0, sticky="w", pady=2
        )
        self.beni_entry = ttk.Entry(vendor_frame, width=70)
        self.beni_entry.grid(column=1, row=0, padx=5, pady=2, sticky="ew")

        # VINCE Path
        ttk.Label(vendor_frame, text="VINCE Depot Path:").grid(
            column=0, row=1, sticky="w", pady=2
        )
        self.vince_entry = ttk.Entry(vendor_frame, width=70)
        self.vince_entry.grid(column=1, row=1, padx=5, pady=2, sticky="ew")

        # FLUMEN Path
        ttk.Label(vendor_frame, text="FLUMEN Depot Path:").grid(
            column=0, row=2, sticky="w", pady=2
        )
        self.flumen_entry = ttk.Entry(vendor_frame, width=70)
        self.flumen_entry.grid(column=1, row=2, padx=5, pady=2, sticky="ew")

        # REL Path
        ttk.Label(vendor_frame, text="REL Depot Path:").grid(
            column=0, row=3, sticky="w", pady=2
        )
        self.rel_entry = ttk.Entry(vendor_frame, width=70)
        self.rel_entry.grid(column=1, row=3, padx=5, pady=2, sticky="ew")

        # Configure grid weights for vendor frame
        vendor_frame.columnconfigure(1, weight=1)

        # Vendor control frame
        vendor_control_frame = ttk.Frame(vendor_frame)
        vendor_control_frame.grid(column=1, row=4, pady=10, sticky="e")

        # Vendor progress bar
        self.vendor_progress = ttk.Progressbar(
            vendor_control_frame, length=200, mode="determinate"
        )
        self.vendor_progress.pack(side="left", padx=(0, 10))

        # Vendor start button
        self.vendor_start_btn = ttk.Button(
            vendor_control_frame, text="Start Bring up", command=self.on_vendor_start
        )
        self.vendor_start_btn.pack(side="right")

        # ============================================================================
        # SYSTEM SECTION (New functionality for workspaces)
        # ============================================================================
        system_frame = ttk.LabelFrame(main_container, text="System", padding=10)
        system_frame.pack(fill="x", pady=(0, 10))

        # BENI Workspace
        ttk.Label(system_frame, text="BENI Workspace:").grid(
            column=0, row=0, sticky="w", pady=2
        )
        self.beni_workspace_entry = ttk.Entry(system_frame, width=70)
        self.beni_workspace_entry.grid(column=1, row=0, padx=5, pady=2, sticky="ew")

        # VINCE Workspace
        ttk.Label(system_frame, text="VINCE Workspace:").grid(
            column=0, row=1, sticky="w", pady=2
        )
        self.vince_workspace_entry = ttk.Entry(system_frame, width=70)
        self.vince_workspace_entry.grid(column=1, row=1, padx=5, pady=2, sticky="ew")

        # FLUMEN Workspace
        ttk.Label(system_frame, text="FLUMEN Workspace:").grid(
            column=0, row=2, sticky="w", pady=2
        )
        self.flumen_workspace_entry = ttk.Entry(system_frame, width=70)
        self.flumen_workspace_entry.grid(column=1, row=2, padx=5, pady=2, sticky="ew")

        # REL Workspace
        ttk.Label(system_frame, text="REL Workspace:").grid(
            column=0, row=3, sticky="w", pady=2
        )
        self.rel_workspace_entry = ttk.Entry(system_frame, width=70)
        self.rel_workspace_entry.grid(column=1, row=3, padx=5, pady=2, sticky="ew")

        # Configure grid weights for system frame
        system_frame.columnconfigure(1, weight=1)

        # System control frame
        system_control_frame = ttk.Frame(system_frame)
        system_control_frame.grid(column=1, row=4, pady=10, sticky="e")

        # System progress bar
        self.system_progress = ttk.Progressbar(
            system_control_frame, length=200, mode="determinate"
        )
        self.system_progress.pack(side="left", padx=(0, 10))

        # System start button
        self.system_start_btn = ttk.Button(
            system_control_frame, text="Start Bring up", command=self.on_system_start
        )
        self.system_start_btn.pack(side="right")

        # ============================================================================
        # LOG OUTPUT SECTION (Reduced height)
        # ============================================================================
        log_frame = ttk.LabelFrame(main_container, text="Process Log", padding=5)
        log_frame.pack(fill="both", expand=True)

        # Create text widget with scrollbar - Reduced height from 12 to 8
        self.log_text = self.gui_utils.create_text_with_scrollbar(log_frame, height=8)

        # Create callbacks
        self.log_callback = self.gui_utils.create_log_callback(self.log_text)
        self.vendor_progress_callback = self.gui_utils.create_progress_callback(self.vendor_progress)
        self.system_progress_callback = self.gui_utils.create_progress_callback(self.system_progress)

    def show(self):
        """Show the bringup tab"""
        self.frame.pack(fill="both", expand=True)

    def hide(self):
        """Hide the bringup tab"""
        self.frame.pack_forget()

    def clear_all(self):
        """Clear all input fields and logs"""
        # Clear vendor input fields
        self.beni_entry.delete(0, tk.END)
        self.vince_entry.delete(0, tk.END)
        self.flumen_entry.delete(0, tk.END)
        self.rel_entry.delete(0, tk.END)

        # Clear system input fields
        self.beni_workspace_entry.delete(0, tk.END)
        self.vince_workspace_entry.delete(0, tk.END)
        self.flumen_workspace_entry.delete(0, tk.END)
        self.rel_workspace_entry.delete(0, tk.END)

        # Clear log output
        self.gui_utils.clear_text_widget(self.log_text)

        # Reset progress bars
        self.gui_utils.reset_progress(self.vendor_progress)
        self.gui_utils.reset_progress(self.system_progress)

        self.log_callback("[INFO] All fields and logs cleared.")
        self.gui_utils.update_status(
            "Mode: Bring up - Vendor: depot paths | System: workspaces (TEMPLATE_*)"
        )

    def on_vendor_start(self):
        """Handle vendor bringup start button click (original functionality)"""
        beni_path = self.beni_entry.get().strip()
        vince_path = self.vince_entry.get().strip()
        flumen_path = self.flumen_entry.get().strip()
        rel_path = self.rel_entry.get().strip()

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
        has_rel = rel_path and rel_path.startswith("//")

        if not has_beni and not has_flumen and not has_rel:
            messagebox.showerror(
                "No Target Paths",
                "At least one target path (BENI, FLUMEN, or REL) must be provided and start with //depot/...",
            )
            return

        # Run vendor process
        self._run_vendor_process(beni_path, vince_path, flumen_path, rel_path)

    def on_system_start(self):
        """Handle system bringup start button click (new workspace functionality)"""
        beni_workspace = self.beni_workspace_entry.get().strip()
        vince_workspace = self.vince_workspace_entry.get().strip()
        flumen_workspace = self.flumen_workspace_entry.get().strip()
        rel_workspace = self.rel_workspace_entry.get().strip()

        # Validation - VINCE and BENI are mandatory for System
        if not vince_workspace.upper().startswith("TEMPLATE"):
            messagebox.showerror(
                "Invalid Workspace",
                "VINCE workspace is mandatory and must start with TEMPLATE",
            )
            return

        if not beni_workspace.upper().startswith("TEMPLATE"):
            messagebox.showerror(
                "Invalid Workspace",
                "BENI workspace is mandatory and must start with TEMPLATE",
            )
            return

        # Validate optional workspaces if provided
        if flumen_workspace and not flumen_workspace.upper().startswith("TEMPLATE"):
            messagebox.showerror(
                "Invalid Workspace",
                "FLUMEN workspace must start with TEMPLATE if provided",
            )
            return

        if rel_workspace and not rel_workspace.upper().startswith("TEMPLATE"):
            messagebox.showerror(
                "Invalid Workspace",
                "REL workspace must start with TEMPLATE if provided",
            )
            return

        # Run system process
        self._run_system_process(beni_workspace, vince_workspace, flumen_workspace, rel_workspace)

    def _run_vendor_process(self, beni_path, vince_path, flumen_path, rel_path):
        """Run vendor bringup process in separate thread (original functionality)"""
        # Clear log and reset progress
        self.gui_utils.clear_text_widget(self.log_text)
        self.gui_utils.reset_progress(self.vendor_progress)

        # Log P4 configuration info
        client_name = get_client_name()
        workspace_root = get_workspace_root()
        if client_name and workspace_root:
            self.log_callback(f"[CONFIG] Using P4 Client: {client_name}")
            self.log_callback(f"[CONFIG] Using Workspace: {workspace_root}")

        # Disable start button during processing
        self.vendor_start_btn.configure(state="disabled")

        def run_process_thread():
            try:
                self.gui_utils.update_status("Processing: Running vendor bring up operation...")
                run_bringup_process(
                    beni_path,
                    vince_path,
                    flumen_path,
                    rel_path,
                    self.log_callback,
                    self.vendor_progress_callback,
                    self.gui_utils.error_callback,
                )
            finally:
                # Re-enable button when done
                self.gui_utils.root.after(
                    0, lambda: self.vendor_start_btn.configure(state="normal")
                )
                self.gui_utils.root.after(
                    0,
                    lambda: self.gui_utils.update_status("Mode: Bring up - Vendor operation completed"),
                )

        # Start the process in a separate thread
        thread = threading.Thread(target=run_process_thread, daemon=True)
        thread.start()

    def _run_system_process(self, beni_workspace, vince_workspace, flumen_workspace, rel_workspace):
        """Run system bringup process in separate thread (new workspace functionality)"""
        # Clear log and reset progress
        self.gui_utils.clear_text_widget(self.log_text)
        self.gui_utils.reset_progress(self.system_progress)

        # Log P4 configuration info
        client_name = get_client_name()
        workspace_root = get_workspace_root()
        if client_name and workspace_root:
            self.log_callback(f"[CONFIG] Using P4 Client: {client_name}")
            self.log_callback(f"[CONFIG] Using Workspace: {workspace_root}")

        # Disable start button during processing
        self.system_start_btn.configure(state="disabled")

        def run_process_thread():
            try:
                self.gui_utils.update_status("Processing: Running system bring up operation...")
                run_system_process(
                    beni_workspace,
                    vince_workspace,
                    flumen_workspace,
                    rel_workspace,
                    self.log_callback,
                    self.system_progress_callback,
                    self.gui_utils.error_callback,
                )
            finally:
                # Re-enable button when done
                self.gui_utils.root.after(
                    0, lambda: self.system_start_btn.configure(state="normal")
                )
                self.gui_utils.root.after(
                    0,
                    lambda: self.gui_utils.update_status("Mode: Bring up - System operation completed"),
                )

        # Start the process in a separate thread
        thread = threading.Thread(target=run_process_thread, daemon=True)
        thread.start()