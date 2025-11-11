"""
Readahead tab implementation
Handles the readahead mode UI for workspace processing and library modification
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from processes.readahead_process import run_readahead_process


class ReadaheadTab:
    """Readahead tab component - UI only"""

    def __init__(self, parent, gui_utils):
        self.parent = parent
        self.gui_utils = gui_utils

        # Create the readahead frame
        self.frame = ttk.Frame(parent)

        # Initialize components
        self.create_content()

    def create_content(self):
        """Create content for readahead mode"""
        # Workspace input section
        workspace_frame = ttk.LabelFrame(self.frame, text="Workspace Input", padding=10)
        workspace_frame.pack(fill="x", pady=(0, 10))

        # Create workspace input rows
        self.workspace_entries = {}

        # BENI workspace
        row_frame = ttk.Frame(workspace_frame)
        row_frame.pack(fill="x", pady=5)
        ttk.Label(row_frame, text="BENI:", width=10).pack(side="left", anchor="w")
        beni_entry = ttk.Entry(row_frame, width=40)
        beni_entry.pack(side="left", padx=(5, 0), fill="x", expand=True)
        self.workspace_entries["BENI"] = beni_entry

        # FLUMEN workspace
        row_frame = ttk.Frame(workspace_frame)
        row_frame.pack(fill="x", pady=5)
        ttk.Label(row_frame, text="FLUMEN:", width=10).pack(side="left", anchor="w")
        flumen_entry = ttk.Entry(row_frame, width=40)
        flumen_entry.pack(side="left", padx=(5, 0), fill="x", expand=True)
        self.workspace_entries["FLUMEN"] = flumen_entry

        # REL workspace
        row_frame = ttk.Frame(workspace_frame)
        row_frame.pack(fill="x", pady=5)
        ttk.Label(row_frame, text="REL:", width=10).pack(side="left", anchor="w")
        rel_entry = ttk.Entry(row_frame, width=40)
        rel_entry.pack(side="left", padx=(5, 0), fill="x", expand=True)
        self.workspace_entries["REL"] = rel_entry

        # Start button, CL input, Parse button and Progress bar frame
        button_frame = ttk.Frame(workspace_frame)
        button_frame.pack(fill="x", pady=(10, 0))

        self.start_button = ttk.Button(
            button_frame, text="Start", command=self.on_start_readahead
        )
        self.start_button.pack(side="left")

        # Changelist input (optional) - moved to button_frame
        cl_label = ttk.Label(button_frame, text="CL:")
        cl_label.pack(side="left", padx=(20, 5)) # Added some padding
        
        self.changelist_entry = ttk.Entry(button_frame, width=27) # Approx 200 chars for default font
        self.changelist_entry.pack(side="left")

        # Parse button
        self.parse_button = ttk.Button(
            button_frame, text="Parse", command=self.on_parse_rscmgr_paths
        )
        self.parse_button.pack(side="left", padx=(20, 0))

        # Progress bar
        self.progress = ttk.Progressbar(button_frame, length=200, mode="determinate")
        self.progress.pack(side="left", padx=(20, 0))

        # Rscmgr path section
        rscmgr_frame = ttk.LabelFrame(self.frame, text="Rscmgr path", padding=10)
        rscmgr_frame.pack(fill="x", pady=(0, 10))

        # Create rscmgr path display rows
        self.rscmgr_entries = {}

        # BENI rscmgr path
        row_frame = ttk.Frame(rscmgr_frame)
        row_frame.pack(fill="x", pady=5)
        ttk.Label(row_frame, text="BENI:", width=10).pack(side="left", anchor="w")
        beni_rscmgr_entry = ttk.Entry(row_frame, width=40, state="readonly")
        beni_rscmgr_entry.pack(side="left", padx=(5, 0), fill="x", expand=True)
        self.rscmgr_entries["BENI"] = beni_rscmgr_entry

        # FLUMEN rscmgr path
        row_frame = ttk.Frame(rscmgr_frame)
        row_frame.pack(fill="x", pady=5)
        ttk.Label(row_frame, text="FLUMEN:", width=10).pack(side="left", anchor="w")
        flumen_rscmgr_entry = ttk.Entry(row_frame, width=40, state="readonly")
        flumen_rscmgr_entry.pack(side="left", padx=(5, 0), fill="x", expand=True)
        self.rscmgr_entries["FLUMEN"] = flumen_rscmgr_entry

        # REL rscmgr path
        row_frame = ttk.Frame(rscmgr_frame)
        row_frame.pack(fill="x", pady=5)
        ttk.Label(row_frame, text="REL:", width=10).pack(side="left", anchor="w")
        rel_rscmgr_entry = ttk.Entry(row_frame, width=40, state="readonly")
        rel_rscmgr_entry.pack(side="left", padx=(5, 0), fill="x", expand=True)
        self.rscmgr_entries["REL"] = rel_rscmgr_entry

        # Library input section (reduced height)
        library_frame = ttk.LabelFrame(self.frame, text="Library Input", padding=10)
        library_frame.pack(fill="both", expand=True, pady=(10, 0))

        # Create two columns for Resource=1 and Resource=2
        columns_frame = ttk.Frame(library_frame)
        columns_frame.pack(fill="both", expand=True)

        # Resource=1 column
        resource1_frame = ttk.Frame(columns_frame)
        resource1_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        ttk.Label(
            resource1_frame, text="Resource=1", font=("TkDefaultFont", 10, "bold")
        ).pack(anchor="w")

        # Resource=1 text area with scrollbar (reduced height)
        resource1_text_frame = ttk.Frame(resource1_frame)
        resource1_text_frame.pack(fill="both", expand=True, pady=5)

        self.resource1_text = tk.Text(
            resource1_text_frame,
            height=10,  # Reduced from 15 to 10
            wrap="none",
            font=("Consolas", 9),
        )
        resource1_scrollbar = ttk.Scrollbar(
            resource1_text_frame, orient="vertical", command=self.resource1_text.yview
        )
        self.resource1_text.configure(yscrollcommand=resource1_scrollbar.set)

        self.resource1_text.pack(side="left", fill="both", expand=True)
        resource1_scrollbar.pack(side="right", fill="y")

        # Resource=2 column
        resource2_frame = ttk.Frame(columns_frame)
        resource2_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))

        ttk.Label(
            resource2_frame, text="Resource=2", font=("TkDefaultFont", 10, "bold")
        ).pack(anchor="w")

        # Resource=2 text area with scrollbar (reduced height)
        resource2_text_frame = ttk.Frame(resource2_frame)
        resource2_text_frame.pack(fill="both", expand=True, pady=5)

        self.resource2_text = tk.Text(
            resource2_text_frame,
            height=10,  # Reduced from 15 to 10
            wrap="none",
            font=("Consolas", 9),
        )
        resource2_scrollbar = ttk.Scrollbar(
            resource2_text_frame, orient="vertical", command=self.resource2_text.yview
        )
        self.resource2_text.configure(yscrollcommand=resource2_scrollbar.set)

        self.resource2_text.pack(side="left", fill="both", expand=True)
        resource2_scrollbar.pack(side="right", fill="y")

        # Log output frame
        log_frame = ttk.LabelFrame(self.frame, text="Readahead Log", padding=5)
        log_frame.pack(fill="x", pady=(10, 0))

        # Create text widget with scrollbar for log
        self.log_text = self.gui_utils.create_text_with_scrollbar(log_frame, height=10)

        # Create callbacks
        self.log_callback = self.gui_utils.create_log_callback(self.log_text)
        self.progress_callback = self.gui_utils.create_progress_callback(self.progress)

    def show(self):
        """Show the readahead tab"""
        self.frame.pack(fill="both", expand=True)

    def hide(self):
        """Hide the readahead tab"""
        self.frame.pack_forget()

    def clear_all(self):
        """Clear all readahead fields and results"""
        # Clear workspace entries
        for entry in self.workspace_entries.values():
            entry.delete(0, tk.END)

        # Clear changelist entry
        self.changelist_entry.delete(0, tk.END)

        # Clear rscmgr path entries
        for entry in self.rscmgr_entries.values():
            entry.configure(state="normal")
            entry.delete(0, tk.END)
            entry.configure(state="readonly")

        # Clear library text areas
        self.resource1_text.delete("1.0", tk.END)
        self.resource2_text.delete("1.0", tk.END)

        # Clear log
        self.gui_utils.clear_text_widget(self.log_text)

        # Reset progress bar
        self.gui_utils.reset_progress(self.progress)

        self.log_callback("[INFO] All readahead fields and logs cleared.")
        self.gui_utils.update_status(
            "Mode: Readahead - Configure workspaces and libraries for rscmgr.rc modification"
        )

    def update_rscmgr_path(self, workspace_type, path):
        """Update rscmgr path display for given workspace type"""
        if workspace_type in self.rscmgr_entries:
            entry = self.rscmgr_entries[workspace_type]
            entry.configure(state="normal")
            entry.delete(0, tk.END)
            entry.insert(0, path if path else "")
            entry.configure(state="readonly")

    def on_parse_rscmgr_paths(self):
        """Handle Parse button click to find rscmgr paths"""
        # Get workspace inputs
        workspace_dict = {}
        for key, entry in self.workspace_entries.items():
            workspace_dict[key] = entry.get().strip()

        # Check if at least one workspace is provided
        if not any(workspace_dict.values()):
            messagebox.showwarning("Missing Input", "At least one workspace is required for parsing.")
            return

        # Clear current rscmgr paths
        for entry in self.rscmgr_entries.values():
            entry.configure(state="normal")
            entry.delete(0, tk.END)
            entry.configure(state="readonly")

        # Clear log and reset progress
        self.gui_utils.clear_text_widget(self.log_text)
        self.gui_utils.reset_progress(self.progress)

        # Disable parse button during processing
        self.parse_button.configure(state="disabled")

        def parse_thread():
            try:
                self.gui_utils.update_status("Processing: Parsing rscmgr paths...")
                self.log_callback("[PARSE] Starting rscmgr path resolution...")

                # Run parse logic in separate thread
                self._parse_rscmgr_paths_logic(workspace_dict)

                self.gui_utils.root.after(
                    0,
                    lambda: self.gui_utils.update_status("Rscmgr path parsing completed"),
                )

            except Exception as e:
                error_message = str(e)
                self.gui_utils.root.after(
                    0,
                    lambda: self.log_callback(
                        f"[ERROR] Parse failed: {error_message}"
                    ),
                )
                self.gui_utils.root.after(
                    0, lambda: self.gui_utils.error_callback("Parse Error", error_message)
                )
            finally:
                # Re-enable parse button when done
                self.gui_utils.root.after(
                    0, lambda: self.parse_button.configure(state="normal")
                )

        # Start process in separate thread
        thread = threading.Thread(target=parse_thread, daemon=True)
        thread.start()

    def _parse_rscmgr_paths_logic(self, workspaces):
        """Parse rscmgr paths logic - simple validation only"""
        from processes.readahead_process import (
            get_rscmgr_reference_from_device_common,
            find_rscmgr_file_path,
            prompt_for_rscmgr_filename,
        )
        from core.p4_operations import (
            map_single_depot,
            sync_file_silent,
            validate_depot_path,
            find_device_common_mk_path
        )

        try:
            # Step 1: Find rscmgr filename from primary workspace
            self.log_callback("[PARSE] Finding rscmgr filename...")
            
            # Determine primary workspace (priority: REL > FLUMEN > BENI)
            primary_workspace = None
            workspace_type = None
            
            if workspaces.get("REL", "").strip():
                primary_workspace = workspaces["REL"].strip()
                workspace_type = "REL"
            elif workspaces.get("FLUMEN", "").strip():
                primary_workspace = workspaces["FLUMEN"].strip()
                workspace_type = "FLUMEN"
            elif workspaces.get("BENI", "").strip():
                primary_workspace = workspaces["BENI"].strip()
                workspace_type = "BENI"

            if not primary_workspace:
                raise RuntimeError("No valid workspace provided")

            self.log_callback(f"[PARSE] Using {workspace_type} as primary workspace")

            # Find device_common.mk
            device_common_path, _ = find_device_common_mk_path(
                primary_workspace, self.log_callback
            )
            if not device_common_path:
                raise RuntimeError(
                    f"Cannot find device_common.mk in {workspace_type} workspace"
                )

            # Map and sync device_common.mk
            map_single_depot(device_common_path)
            sync_file_silent(device_common_path)

            # Find rscmgr filename
            rscmgr_filename = get_rscmgr_reference_from_device_common(
                device_common_path, self.log_callback
            )
            
            if not rscmgr_filename:
                self.log_callback("[PARSE] No rscmgr filename found, prompting user...")
                # Prompt user - need to run in main thread
                self.gui_utils.root.after(
                    0, lambda: self._prompt_and_continue_parse(workspaces)
                )
                return

            self.log_callback(f"[PARSE] Found rscmgr filename: {rscmgr_filename}")
            self.progress_callback(30)

            # Step 2: Find and validate rscmgr paths for each workspace
            self._find_and_validate_paths(workspaces, rscmgr_filename)

            self.progress_callback(100)
            self.log_callback("[PARSE] Parse completed successfully!")

        except Exception as e:
            self.log_callback(f"[PARSE ERROR] {str(e)}")
            raise


    def _find_and_validate_paths(self, workspaces, rscmgr_filename):
        """Find and validate rscmgr paths for all provided workspaces"""
        from processes.readahead_process import find_rscmgr_file_path
        from core.p4_operations import validate_depot_path

        for workspace_key in ["REL", "FLUMEN", "BENI"]:
            workspace = workspaces.get(workspace_key, "").strip()
            if not workspace:
                continue

            self.log_callback(
                f"[PARSE] Processing {workspace_key}: {workspace}"
            )

            # Find rscmgr path
            rscmgr_path = find_rscmgr_file_path(
                workspace, rscmgr_filename, self.log_callback
            )

            if not rscmgr_path:
                self.log_callback(
                    f"[WARNING] Could not construct rscmgr path for {workspace_key}"
                )
                continue

            # Validate if file exists
            if validate_depot_path(rscmgr_path):
                self.log_callback(f"[OK] {workspace_key} rscmgr exists: {rscmgr_path}")
                # Update UI
                self.gui_utils.root.after(
                    0,
                    lambda key=workspace_key, path=rscmgr_path: self.update_rscmgr_path(
                        key, path
                    ),
                )
            else:
                self.log_callback(
                    f"[WARNING] {workspace_key} rscmgr file does not exist: {rscmgr_path}"
                )


    def _prompt_and_continue_parse(self, workspaces):
        """Prompt for rscmgr filename and continue parse"""
        from processes.readahead_process import prompt_for_rscmgr_filename

        rscmgr_filename = prompt_for_rscmgr_filename(self.log_callback)
        
        if not rscmgr_filename:
            self.log_callback("[PARSE] Cancelled - rscmgr filename required")
            self.parse_button.configure(state="normal")
            return

        self.log_callback(f"[PARSE] Using user-provided filename: {rscmgr_filename}")

        # Continue in background thread
        def continue_thread():
            try:
                self._find_and_validate_paths(workspaces, rscmgr_filename)
                self.progress_callback(100)
                self.log_callback("[PARSE] Parse completed successfully!")
            except Exception as e:
                self.log_callback(f"[PARSE ERROR] {str(e)}")
            finally:
                self.gui_utils.root.after(
                    0, lambda: self.parse_button.configure(state="normal")
                )

        import threading
        thread = threading.Thread(target=continue_thread, daemon=True)
        thread.start()

    def _prompt_rscmgr_filename_async(self, workspaces):
        """Handle rscmgr filename prompt in main thread"""
        from processes.readahead_process import prompt_for_rscmgr_filename
        
        rscmgr_filename = prompt_for_rscmgr_filename(self.log_callback)
        if rscmgr_filename:
            # Continue parsing with user-provided filename
            def continue_parse():
                try:
                    self._parse_with_filename(workspaces, rscmgr_filename)
                except Exception as e:
                    self.log_callback(f"[ERROR] Parse failed: {str(e)}")
                finally:
                    self.parse_button.configure(state="normal")
            
            thread = threading.Thread(target=continue_parse, daemon=True)
            thread.start()
        else:
            self.log_callback("[PARSE] Parse cancelled - rscmgr filename required")
            self.parse_button.configure(state="normal")

    def _parse_with_filename(self, workspaces, rscmgr_filename):
        """Continue parsing with user-provided rscmgr filename"""
        from processes.readahead_process import (
            find_rscmgr_file_path,
            auto_resolve_missing_branches_readahead,
        )

        try:
            self.log_callback(f"[PARSE] Using rscmgr filename: {rscmgr_filename}")

            # Find rscmgr paths for provided workspaces
            rscmgr_paths = {}
            for workspace_key in ["REL", "FLUMEN", "BENI"]:
                workspace = workspaces.get(workspace_key, "").strip()
                if workspace:
                    self.log_callback(f"[PARSE] Finding rscmgr path for {workspace_key}: {workspace}")
                    rscmgr_path = find_rscmgr_file_path(workspace, rscmgr_filename, self.log_callback)
                    if rscmgr_path:
                        rscmgr_paths[workspace_key] = rscmgr_path
                        self.log_callback(f"[PARSE] Found {workspace_key} rscmgr: {rscmgr_path}")
                        # Update UI
                        self.gui_utils.root.after(0, lambda key=workspace_key, path=rscmgr_path: self.update_rscmgr_path(key, path))

            # Auto-resolve missing branches
            if len(rscmgr_paths) > 0:
                self.log_callback("[PARSE] Starting auto-resolution for missing branches...")
                
                resolve_workspaces = {}
                for key in ["REL", "FLUMEN", "BENI"]:
                    if key in rscmgr_paths:
                        resolve_workspaces[key] = rscmgr_paths[key]
                    else:
                        resolve_workspaces[key] = ""

                resolved_workspaces = auto_resolve_missing_branches_readahead(
                    resolve_workspaces, rscmgr_filename, self.log_callback
                )

                # Update UI with resolved paths
                for workspace_key in ["REL", "FLUMEN", "BENI"]:
                    resolved_path = resolved_workspaces.get(workspace_key, "").strip()
                    if resolved_path and resolved_path not in rscmgr_paths.values():
                        self.log_callback(f"[PARSE] Auto-resolved {workspace_key}: {resolved_path}")
                        self.gui_utils.root.after(0, lambda key=workspace_key, path=resolved_path: self.update_rscmgr_path(key, path))

            self.progress_callback(100)
            self.log_callback("[PARSE] Rscmgr path parsing completed successfully!")

        except Exception as e:
            self.log_callback(f"[PARSE ERROR] {str(e)}")
            raise

    def validate_inputs(self):
        """Validate readahead inputs"""
        # Get workspace inputs
        workspace_dict = {}
        for key, entry in self.workspace_entries.items():
            workspace_dict[key] = entry.get().strip()

        # Get changelist input
        changelist_input = self.changelist_entry.get().strip()

        
        # Validate at least one workspace is provided
        if not any(workspace_dict[key] for key in ["REL", "FLUMEN", "BENI"]):
            messagebox.showwarning("Missing Input", "At least one workspace (REL, FLUMEN, or BENI) is required.")
            return None

        # Validate at least one other workspace (BENI/FLUMEN/REL)
        other_workspaces = [
            workspace_dict[key]
            for key in ["BENI", "FLUMEN", "REL"]
            if workspace_dict[key]
        ]
        if not other_workspaces:
            messagebox.showwarning(
                "Missing Input",
                "At least one workspace from BENI, FLUMEN, or REL is required.",
            )
            return None

        # Validate changelist format if provided
        if changelist_input:
            if not changelist_input.isdigit():
                messagebox.showwarning(
                    "Invalid Changelist", "Changelist ID must be a number."
                )
                return None

        # Get library inputs
        resource1_libs = []
        resource1_text = self.resource1_text.get("1.0", tk.END).strip()
        if resource1_text:
            resource1_libs = [
                lib.strip() for lib in resource1_text.split("\n") if lib.strip()
            ]

        resource2_libs = []
        resource2_text = self.resource2_text.get("1.0", tk.END).strip()
        if resource2_text:
            resource2_libs = [
                lib.strip() for lib in resource2_text.split("\n") if lib.strip()
            ]

        # At least one library must be provided
        if not resource1_libs and not resource2_libs:
            messagebox.showwarning(
                "Missing Libraries",
                "At least one library must be provided in Resource=1 or Resource=2.",
            )
            return None

        return {
            "workspaces": workspace_dict,
            "changelist_id": changelist_input if changelist_input else None,
            "resource1_libs": resource1_libs,
            "resource2_libs": resource2_libs,
        }

    def on_start_readahead(self):
        """Handle start readahead button click"""
        # Validate inputs
        inputs = self.validate_inputs()
        if not inputs:
            return

        self._run_readahead_process(inputs)

    def _run_readahead_process(self, inputs):
        """Run readahead process in separate thread"""
        # Clear log and reset progress
        self.gui_utils.clear_text_widget(self.log_text)
        self.gui_utils.reset_progress(self.progress)

        # Disable start button during processing
        self.start_button.configure(state="disabled")

        def readahead_thread():
            try:
                self.gui_utils.update_status("Processing: Running readahead process...")

                # Run the readahead process
                run_readahead_process(
                    inputs["workspaces"],
                    inputs["resource1_libs"],
                    inputs["resource2_libs"],
                    inputs["changelist_id"],
                    self.log_callback,
                    self.progress_callback,
                    self.gui_utils.error_callback,
                )

                self.gui_utils.root.after(
                    0,
                    lambda: self.gui_utils.update_status("Readahead process completed"),
                )

            except Exception as e:
                error_message = str(e)
                self.gui_utils.root.after(
                    0,
                    lambda: self.log_callback(
                        f"[ERROR] Readahead process failed: {error_message}"
                    ),
                )
                self.gui_utils.root.after(
                    0, lambda: self.gui_utils.error_callback("Readahead Error", error_message)
                )
            finally:
                # Re-enable start button when done
                self.gui_utils.root.after(
                    0, lambda: self.start_button.configure(state="normal")
                )

        # Start process in separate thread
        thread = threading.Thread(target=readahead_thread, daemon=True)
        thread.start()
