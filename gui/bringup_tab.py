"""
Bringup tab implementation
Handles the bringup mode UI and functionality
Enhanced to support mixed input (depot paths and workspaces)
Updated to handle info messages for no differences scenario
Enhanced with auto-resolve cascading functionality
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from config.p4_config import get_client_name, get_workspace_root
from processes.bringup_process import run_bringup_process
from processes.system_process import run_system_process


class BringupTab:
    """Bringup tab component with Vendor and System sections supporting mixed input and auto-resolve"""

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
        # VENDOR SECTION (Enhanced to support both depot paths and workspaces)
        # ============================================================================
        vendor_frame = ttk.LabelFrame(main_container, text="Vendor", padding=10)
        vendor_frame.pack(fill="x", pady=(0, 10))

        # BENI Path/Workspace
        ttk.Label(vendor_frame, text="BENI:").grid(
            column=0, row=0, sticky="w", pady=2
        )
        self.beni_entry = ttk.Entry(vendor_frame, width=70)
        self.beni_entry.grid(column=1, row=0, padx=5, pady=2, sticky="ew")

        # VINCE Path/Workspace
        ttk.Label(vendor_frame, text="VINCE:").grid(
            column=0, row=1, sticky="w", pady=2
        )
        self.vince_entry = ttk.Entry(vendor_frame, width=70)
        self.vince_entry.grid(column=1, row=1, padx=5, pady=2, sticky="ew")

        # FLUMEN Path/Workspace
        ttk.Label(vendor_frame, text="FLUMEN:").grid(
            column=0, row=2, sticky="w", pady=2
        )
        self.flumen_entry = ttk.Entry(vendor_frame, width=70)
        self.flumen_entry.grid(column=1, row=2, padx=5, pady=2, sticky="ew")

        # REL Path/Workspace
        ttk.Label(vendor_frame, text="REL:").grid(
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
        # SYSTEM SECTION (Enhanced to support both workspaces and depot paths + Auto-resolve)
        # ============================================================================
        system_frame = ttk.LabelFrame(main_container, text="System (Auto-resolve enabled)", padding=10)
        system_frame.pack(fill="x", pady=(0, 10))

        # BENI Workspace/Path
        ttk.Label(system_frame, text="BENI:").grid(
            column=0, row=0, sticky="w", pady=2
        )
        self.beni_workspace_entry = ttk.Entry(system_frame, width=70)
        self.beni_workspace_entry.grid(column=1, row=0, padx=5, pady=2, sticky="ew")

        # VINCE Workspace/Path
        ttk.Label(system_frame, text="VINCE:").grid(
            column=0, row=1, sticky="w", pady=2
        )
        self.vince_workspace_entry = ttk.Entry(system_frame, width=70)
        self.vince_workspace_entry.grid(column=1, row=1, padx=5, pady=2, sticky="ew")

        # FLUMEN Workspace/Path
        ttk.Label(system_frame, text="FLUMEN:").grid(
            column=0, row=2, sticky="w", pady=2
        )
        self.flumen_workspace_entry = ttk.Entry(system_frame, width=70)
        self.flumen_workspace_entry.grid(column=1, row=2, padx=5, pady=2, sticky="ew")

        # REL Workspace/Path
        ttk.Label(system_frame, text="REL:").grid(
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
            "Mode: Bring up - Vendor/System: depot paths or workspaces (TEMPLATE_*)"
        )

    def _validate_vendor_input(self, user_input, field_name):
        """
        Validate vendor input (can be depot path or workspace)
        Returns (is_valid, resolved_depot_path, error_message)
        """
        if not user_input:
            return True, "", None  # Empty is OK for optional fields
        
        user_input = user_input.strip()
        
        # Check if it's a depot path
        if user_input.startswith("//"):
            from core.p4_operations import validate_depot_path
            if validate_depot_path(user_input):
                return True, user_input, None
            else:
                return False, "", f"{field_name} depot path does not exist: {user_input}"
        
        # Check if it's a workspace
        elif user_input.upper().startswith("TEMPLATE"):
            try:
                from core.p4_operations import resolve_workspace_to_device_common_path
                resolved_path = resolve_workspace_to_device_common_path(user_input)
                return True, resolved_path, None
            except Exception as e:
                return False, "", f"{field_name} workspace resolution failed: {str(e)}"
        
        else:
            return False, "", f"{field_name} must be either depot path (//depot/...) or workspace (TEMPLATE_*)"

    def _validate_system_input(self, user_input, field_name):
        """
        Validate system input (can be workspace or depot path to device_common.mk)
        Returns (is_valid, resolved_input, error_message)
        """
        if not user_input:
            return True, "", None  # Empty is OK for optional fields
        
        user_input = user_input.strip()
        
        # Check if it's a depot path
        if user_input.startswith("//"):
            from core.p4_operations import validate_device_common_mk_path
            exists, is_device_common = validate_device_common_mk_path(user_input)
            
            if not exists:
                return False, "", f"{field_name} depot path does not exist: {user_input}"
            elif not is_device_common:
                return False, "", f"{field_name} path must be a device_common.mk file: {user_input}"
            else:
                return True, user_input, None
        
        # Check if it's a workspace
        elif user_input.upper().startswith("TEMPLATE"):
            try:
                from core.p4_operations import resolve_workspace_to_device_common_path
                resolved_path = resolve_workspace_to_device_common_path(user_input)
                return True, user_input, None  # Keep original workspace for system processing
            except Exception as e:
                return False, "", f"{field_name} workspace resolution failed: {str(e)}"
        
        else:
            return False, "", f"{field_name} must be either device_common.mk depot path or workspace (TEMPLATE_*)"

    def _create_enhanced_error_callback(self):
        """Create enhanced error callback that can handle both error and info messages"""
        def error_callback(title, message, is_info=False):
            def show_dialog():
                if is_info:
                    messagebox.showinfo(title, message)
                else:
                    messagebox.showerror(title, message)
            
            # Schedule dialog to show in main thread
            self.gui_utils.root.after(0, show_dialog)
        
        return error_callback

    def on_vendor_start(self):
        """Handle vendor bringup start button click (enhanced to support mixed input)"""
        beni_input = self.beni_entry.get().strip()
        vince_input = self.vince_entry.get().strip()
        flumen_input = self.flumen_entry.get().strip()
        rel_input = self.rel_entry.get().strip()

        # Validate VINCE (mandatory)
        is_valid, vince_path, error_msg = self._validate_vendor_input(vince_input, "VINCE")
        if not is_valid or not vince_path:
            messagebox.showerror(
                "Invalid Input",
                error_msg or "VINCE is mandatory and must be depot path (//depot/...) or workspace (TEMPLATE_*)",
            )
            return

        # Validate optional targets
        valid_targets = []
        beni_path = flumen_path = rel_path = ""
        
        if beni_input:
            is_valid, beni_path, error_msg = self._validate_vendor_input(beni_input, "BENI")
            if not is_valid:
                messagebox.showerror("Invalid Input", error_msg)
                return
            if beni_path:
                valid_targets.append("BENI")

        if flumen_input:
            is_valid, flumen_path, error_msg = self._validate_vendor_input(flumen_input, "FLUMEN")
            if not is_valid:
                messagebox.showerror("Invalid Input", error_msg)
                return
            if flumen_path:
                valid_targets.append("FLUMEN")

        if rel_input:
            is_valid, rel_path, error_msg = self._validate_vendor_input(rel_input, "REL")
            if not is_valid:
                messagebox.showerror("Invalid Input", error_msg)
                return
            if rel_path:
                valid_targets.append("REL")

        if not valid_targets:
            messagebox.showerror(
                "No Valid Targets",
                "At least one target (BENI, FLUMEN, or REL) must be provided and valid",
            )
            return

        # Run vendor process
        self._run_vendor_process(beni_path, vince_path, flumen_path, rel_path)

    def on_system_start(self):
        """Handle system bringup start button click with auto-resolve functionality"""
        beni_input = self.beni_workspace_entry.get().strip()
        vince_input = self.vince_workspace_entry.get().strip()
        flumen_input = self.flumen_workspace_entry.get().strip()
        rel_input = self.rel_workspace_entry.get().strip()

        # Validate VINCE (mandatory)
        if not vince_input:
            messagebox.showerror(
                "Invalid Input",
                "VINCE is mandatory for system bringup",
            )
            return

        # Basic validation of VINCE input format
        is_valid, vince_resolved, error_msg = self._validate_system_input(vince_input, "VINCE")
        if not is_valid:
            messagebox.showerror("Invalid Input", error_msg)
            return

        # AUTO-RESOLVE MISSING BRANCHES
        try:
            from core.p4_operations import auto_resolve_missing_branches
            
            self.log_callback("[SYSTEM] Starting auto-resolve for missing branches...")
            
            # Call auto-resolve function
            resolved_beni, resolved_flumen, resolved_rel, resolved_vince = auto_resolve_missing_branches(
                vince_input, flumen_input, beni_input, rel_input, self.log_callback
            )
            
            # Update resolved inputs
            final_beni_input = resolved_beni if resolved_beni else beni_input
            final_vince_input = resolved_vince if resolved_vince else vince_input
            final_flumen_input = resolved_flumen if resolved_flumen else flumen_input
            final_rel_input = resolved_rel if resolved_rel else rel_input
            
            # Log final inputs after auto-resolve
            self.log_callback("[AUTO-RESOLVE] Using final resolved inputs for system processing:")
            self.log_callback(f"[FINAL] VINCE: {final_vince_input}")
            self.log_callback(f"[FINAL] BENI: {final_beni_input if final_beni_input else '(not provided)'}")
            self.log_callback(f"[FINAL] FLUMEN: {final_flumen_input if final_flumen_input else '(not provided)'}")
            self.log_callback(f"[FINAL] REL: {final_rel_input if final_rel_input else '(not provided)'}")
            
        except Exception as e:
            error_msg = f"Auto-resolve failed: {str(e)}"
            self.log_callback(f"[ERROR] {error_msg}")
            messagebox.showerror("Auto-resolve Failed", error_msg)
            return

        # Validate final resolved inputs
        # VINCE validation
        is_valid, vince_resolved, error_msg = self._validate_system_input(final_vince_input, "VINCE")
        if not is_valid or not vince_resolved:
            messagebox.showerror(
                "Invalid Input",
                error_msg or "VINCE validation failed after auto-resolve",
            )
            return

        # BENI validation - now may be auto-resolved so check if it exists
        final_beni_resolved = ""
        if final_beni_input:
            is_valid, final_beni_resolved, error_msg = self._validate_system_input(final_beni_input, "BENI")
            if not is_valid:
                messagebox.showerror("Invalid Input", error_msg)
                return
        
        # Check if we have either original BENI or auto-resolved BENI
        if not final_beni_input:
            messagebox.showerror(
                "Invalid Input",
                "BENI is mandatory for system bringup and could not be auto-resolved",
            )
            return

        # Validate optional resolved targets
        final_flumen_resolved = final_rel_resolved = ""
        
        if final_flumen_input:
            is_valid, final_flumen_resolved, error_msg = self._validate_system_input(final_flumen_input, "FLUMEN")
            if not is_valid:
                messagebox.showerror("Invalid Input", error_msg)
                return

        if final_rel_input:
            is_valid, final_rel_resolved, error_msg = self._validate_system_input(final_rel_input, "REL")
            if not is_valid:
                messagebox.showerror("Invalid Input", error_msg)
                return

        # Run system process with resolved inputs
        self._run_system_process(
            final_beni_input, final_vince_input, final_flumen_input, final_rel_input
        )

    def _run_vendor_process(self, beni_path, vince_path, flumen_path, rel_path):
        """Run vendor bringup process in separate thread (enhanced functionality)"""
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

        # Create enhanced error callback
        enhanced_error_callback = self._create_enhanced_error_callback()

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
                    enhanced_error_callback,  # Use enhanced callback
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

    def _run_system_process(self, beni_input, vince_input, flumen_input, rel_input):
        """Run system bringup process in separate thread with auto-resolve support"""
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
                self.gui_utils.update_status("Processing: Running system bring up operation with auto-resolve...")
                run_system_process(
                    beni_input,
                    vince_input,
                    flumen_input,
                    rel_input,
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