"""
LoadApkAsset tab implementation
Handles the UI for adding asset apps to chipsets in ReadaheadManager.java
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from processes.loadapkasset_process import (
    run_loadapkasset_process,
    find_samsung_vendor_path,
    construct_readahead_manager_path,
    parse_readahead_manager_file,
    AVAILABLE_ASSETS
)
from core.p4_operations import (
    map_single_depot,
    sync_file_silent,
    validate_depot_path,
)


class LoadApkAssetTab:
    """LoadApkAsset tab component - UI only"""

    def __init__(self, parent, gui_utils):
        self.parent = parent
        self.gui_utils = gui_utils

        # Create the frame
        self.frame = ttk.Frame(parent)

        # Store chipset data
        self.chipset_data = {}  # {chipset_name: [list of current assets]}
        self.selected_chipset = None

        # Initialize components
        self.create_content()

    def create_content(self):
        """Create content for LoadApkAsset mode"""
        # Workspace input section
        workspace_frame = ttk.LabelFrame(self.frame, text="Workspace Input", padding=10)
        workspace_frame.pack(fill="x", pady=(0, 10))

        # Create workspace input rows (REL, FLUMEN, BENI)
        self.workspace_entries = {}

        # REL workspace
        row_frame = ttk.Frame(workspace_frame)
        row_frame.pack(fill="x", pady=5)
        ttk.Label(row_frame, text="REL:", width=10).pack(side="left", anchor="w")
        rel_entry = ttk.Entry(row_frame, width=40)
        rel_entry.pack(side="left", padx=(5, 0), fill="x", expand=True)
        self.workspace_entries["REL"] = rel_entry

        # FLUMEN workspace
        row_frame = ttk.Frame(workspace_frame)
        row_frame.pack(fill="x", pady=5)
        ttk.Label(row_frame, text="FLUMEN:", width=10).pack(side="left", anchor="w")
        flumen_entry = ttk.Entry(row_frame, width=40)
        flumen_entry.pack(side="left", padx=(5, 0), fill="x", expand=True)
        self.workspace_entries["FLUMEN"] = flumen_entry

        # BENI workspace
        row_frame = ttk.Frame(workspace_frame)
        row_frame.pack(fill="x", pady=5)
        ttk.Label(row_frame, text="BENI:", width=10).pack(side="left", anchor="w")
        beni_entry = ttk.Entry(row_frame, width=40)
        beni_entry.pack(side="left", padx=(5, 0), fill="x", expand=True)
        self.workspace_entries["BENI"] = beni_entry

        # Control buttons frame
        button_frame = ttk.Frame(workspace_frame)
        button_frame.pack(fill="x", pady=(10, 0))

        # Parse button
        self.parse_button = ttk.Button(
            button_frame, text="Parse", command=self.on_parse_readahead_manager
        )
        self.parse_button.pack(side="left")

        # Changelist input
        cl_label = ttk.Label(button_frame, text="CL:")
        cl_label.pack(side="left", padx=(20, 5))
        
        self.changelist_entry = ttk.Entry(button_frame, width=15)
        self.changelist_entry.pack(side="left")

        # Asset selection label
        ttk.Label(button_frame, text="Select Assets:").pack(side="left", padx=(20, 5))

        # Multiple selection for assets
        self.asset_selection_frame = ttk.Frame(button_frame)
        self.asset_selection_frame.pack(side="left", fill="x", expand=True)
        
        # Create a frame with border for the asset listbox
        asset_list_container = ttk.Frame(self.asset_selection_frame, relief="sunken", borderwidth=1)
        asset_list_container.pack(side="left", fill="both", expand=True)
        
        # Listbox for asset selection with scrollbar
        asset_scroll = ttk.Scrollbar(asset_list_container, orient="vertical")
        self.asset_listbox = tk.Listbox(
            asset_list_container,
            selectmode="multiple",
            height=3,
            yscrollcommand=asset_scroll.set,
            exportselection=False
        )
        asset_scroll.config(command=self.asset_listbox.yview)
        
        self.asset_listbox.pack(side="left", fill="both", expand=True)
        asset_scroll.pack(side="right", fill="y")

        # Populate with all available assets initially
        for asset in AVAILABLE_ASSETS:
            self.asset_listbox.insert(tk.END, asset)

        # Start button
        self.start_button = ttk.Button(
            button_frame, text="Start", command=self.on_start_loadapkasset
        )
        self.start_button.pack(side="left", padx=(10, 0))

        # Progress bar
        self.progress = ttk.Progressbar(button_frame, length=150, mode="determinate")
        self.progress.pack(side="left", padx=(20, 0))

        # ReadaheadManager path section
        readahead_mgr_frame = ttk.LabelFrame(self.frame, text="ReadaheadManager Path", padding=10)
        readahead_mgr_frame.pack(fill="x", pady=(0, 10))

        # Create ReadaheadManager path display rows
        self.readahead_mgr_entries = {}

        # REL path
        row_frame = ttk.Frame(readahead_mgr_frame)
        row_frame.pack(fill="x", pady=5)
        ttk.Label(row_frame, text="REL:", width=10).pack(side="left", anchor="w")
        rel_mgr_entry = ttk.Entry(row_frame, width=40, state="readonly")
        rel_mgr_entry.pack(side="left", padx=(5, 0), fill="x", expand=True)
        self.readahead_mgr_entries["REL"] = rel_mgr_entry

        # FLUMEN path
        row_frame = ttk.Frame(readahead_mgr_frame)
        row_frame.pack(fill="x", pady=5)
        ttk.Label(row_frame, text="FLUMEN:", width=10).pack(side="left", anchor="w")
        flumen_mgr_entry = ttk.Entry(row_frame, width=40, state="readonly")
        flumen_mgr_entry.pack(side="left", padx=(5, 0), fill="x", expand=True)
        self.readahead_mgr_entries["FLUMEN"] = flumen_mgr_entry

        # BENI path
        row_frame = ttk.Frame(readahead_mgr_frame)
        row_frame.pack(fill="x", pady=5)
        ttk.Label(row_frame, text="BENI:", width=10).pack(side="left", anchor="w")
        beni_mgr_entry = ttk.Entry(row_frame, width=40, state="readonly")
        beni_mgr_entry.pack(side="left", padx=(5, 0), fill="x", expand=True)
        self.readahead_mgr_entries["BENI"] = beni_mgr_entry

        # Chipset display section
        chipset_frame = ttk.LabelFrame(self.frame, text="Chipset Assets", padding=10)
        chipset_frame.pack(fill="both", expand=True, pady=(0, 10))

        # Create treeview for chipset display
        tree_frame = ttk.Frame(chipset_frame)
        tree_frame.pack(fill="both", expand=True)

        # Treeview with scrollbar
        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical")
        
        self.chipset_tree = ttk.Treeview(
            tree_frame,
            columns=("Chipset", "Current Assets"),
            show="headings",
            yscrollcommand=tree_scroll.set,
            selectmode="browse"
        )
        tree_scroll.config(command=self.chipset_tree.yview)

        # Define columns
        self.chipset_tree.heading("Chipset", text="Chipset")
        self.chipset_tree.heading("Current Assets", text="Current Assets")
        
        self.chipset_tree.column("Chipset", width=150, anchor="w")
        self.chipset_tree.column("Current Assets", width=600, anchor="w")

        self.chipset_tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")

        # Bind selection event
        self.chipset_tree.bind("<<TreeviewSelect>>", self.on_chipset_select)

        # Select button
        select_button_frame = ttk.Frame(chipset_frame)
        select_button_frame.pack(fill="x", pady=(10, 0))

        self.select_button = ttk.Button(
            select_button_frame, text="Select Chipset", command=self.on_select_chipset
        )
        self.select_button.pack(side="left")

        ttk.Label(select_button_frame, text="(Select a chipset from the table above)").pack(
            side="left", padx=(10, 0)
        )

        # Log output frame
        log_frame = ttk.LabelFrame(self.frame, text="LoadApkAsset Log", padding=5)
        log_frame.pack(fill="x", pady=(10, 0))

        # Create text widget with scrollbar for log
        self.log_text = self.gui_utils.create_text_with_scrollbar(log_frame, height=8)

        # Create callbacks
        self.log_callback = self.gui_utils.create_log_callback(self.log_text)
        self.progress_callback = self.gui_utils.create_progress_callback(self.progress)

    def show(self):
        """Show the LoadApkAsset tab"""
        self.frame.pack(fill="both", expand=True)

    def hide(self):
        """Hide the LoadApkAsset tab"""
        self.frame.pack_forget()

    def clear_all(self):
        """Clear all LoadApkAsset fields and results"""
        # Clear workspace entries
        for entry in self.workspace_entries.values():
            entry.delete(0, tk.END)

        # Clear changelist entry
        self.changelist_entry.delete(0, tk.END)

        # Clear ReadaheadManager path entries
        for entry in self.readahead_mgr_entries.values():
            entry.configure(state="normal")
            entry.delete(0, tk.END)
            entry.configure(state="readonly")

        # Clear chipset tree
        for item in self.chipset_tree.get_children():
            self.chipset_tree.delete(item)

        # Reset asset selection
        self.asset_listbox.selection_clear(0, tk.END)
        self.asset_listbox.delete(0, tk.END)
        for asset in AVAILABLE_ASSETS:
            self.asset_listbox.insert(tk.END, asset)

        # Clear stored data
        self.chipset_data = {}
        self.selected_chipset = None

        # Clear log
        self.gui_utils.clear_text_widget(self.log_text)

        # Reset progress bar
        self.gui_utils.reset_progress(self.progress)

        self.log_callback("[INFO] All LoadApkAsset fields and logs cleared.")
        self.gui_utils.update_status(
            "Mode: LoadApkAsset - Configure workspaces and select chipset to add asset apps"
        )

    def update_readahead_mgr_path(self, workspace_type, path):
        """Update ReadaheadManager path display for given workspace type"""
        if workspace_type in self.readahead_mgr_entries:
            entry = self.readahead_mgr_entries[workspace_type]
            entry.configure(state="normal")
            entry.delete(0, tk.END)
            entry.insert(0, path if path else "")
            entry.configure(state="readonly")

    def on_parse_readahead_manager(self):
        """Handle Parse button click to find ReadaheadManager paths and parse chipsets"""
        # Get workspace inputs
        workspace_dict = {}
        for key, entry in self.workspace_entries.items():
            workspace_dict[key] = entry.get().strip()

        # Check if at least one workspace is provided
        if not any(workspace_dict.values()):
            messagebox.showwarning("Missing Input", "At least one workspace is required for parsing.")
            return

        # Clear current data
        for entry in self.readahead_mgr_entries.values():
            entry.configure(state="normal")
            entry.delete(0, tk.END)
            entry.configure(state="readonly")

        # Clear chipset tree
        for item in self.chipset_tree.get_children():
            self.chipset_tree.delete(item)

        self.chipset_data = {}
        self.selected_chipset = None

        # Clear log and reset progress
        self.gui_utils.clear_text_widget(self.log_text)
        self.gui_utils.reset_progress(self.progress)

        # Disable parse button during processing
        self.parse_button.configure(state="disabled")

        def parse_thread():
            try:
                self.gui_utils.update_status("Processing: Parsing ReadaheadManager paths...")
                self.log_callback("[PARSE] Starting ReadaheadManager path resolution...")

                # Run parse logic
                self._parse_readahead_manager_logic(workspace_dict)

                self.gui_utils.root.after(
                    0,
                    lambda: self.gui_utils.update_status("ReadaheadManager parsing completed"),
                )

            except Exception as e:
                error_message = str(e)
                self.gui_utils.root.after(
                    0,
                    lambda: self.log_callback(f"[ERROR] Parse failed: {error_message}"),
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

    def _parse_readahead_manager_logic(self, workspaces):
        """Parse ReadaheadManager.java logic"""
        try:
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
            self.progress_callback(20)

            # Find samsung vendor path
            samsung_path = find_samsung_vendor_path(primary_workspace, self.log_callback)
            if not samsung_path:
                raise RuntimeError(f"Cannot find samsung vendor path in {workspace_type}")

            self.log_callback(f"[PARSE] Samsung vendor path: {samsung_path}")
            self.progress_callback(30)

            # Construct ReadaheadManager.java path
            readahead_mgr_path = construct_readahead_manager_path(samsung_path)
            self.log_callback(f"[PARSE] Constructed path: {readahead_mgr_path}")
            
            # Validate path exists
            if not validate_depot_path(readahead_mgr_path):
                raise RuntimeError(f"ReadaheadManager.java not found at: {readahead_mgr_path}")

            self.log_callback(f"[PARSE]  Validated ReadaheadManager.java exists")
            
            # Update UI with path
            self.gui_utils.root.after(
                0,
                lambda: self.update_readahead_mgr_path(workspace_type, readahead_mgr_path)
            )

            self.progress_callback(40)

            # Map and sync file
            self.log_callback(f"[PARSE] Mapping and syncing file...")
            map_single_depot(readahead_mgr_path)
            sync_file_silent(readahead_mgr_path)

            self.progress_callback(60)

            # Parse file to get chipset data
            self.log_callback("[PARSE] Parsing chipset data from ReadaheadManager.java...")
            chipset_data = parse_readahead_manager_file(readahead_mgr_path, self.log_callback)

            self.progress_callback(80)

            if not chipset_data:
                self.log_callback("[WARNING] No chipset data found in file")
                messagebox.showwarning(
                    "No Chipsets Found",
                    "Could not find any chipset definitions in ReadaheadManager.java"
                )
            else:
                self.log_callback(f"[PARSE] Successfully parsed {len(chipset_data)} chipsets")
                # Store chipset data
                self.chipset_data = chipset_data
                
                # Update UI tree - MUST run in main thread
                self.log_callback("[UI] Updating chipset table...")
                self.gui_utils.root.after(0, self._populate_chipset_tree)

            self.progress_callback(100)
            self.log_callback("[PARSE] ========== Parse completed successfully! ==========")

        except Exception as e:
            self.log_callback(f"[PARSE ERROR] {str(e)}")
            import traceback
            self.log_callback(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
            raise

    def _populate_chipset_tree(self):
        """Populate chipset tree with parsed data"""
        try:
            self.log_callback(f"[UI] _populate_chipset_tree called with {len(self.chipset_data)} chipsets")
            
            # Clear existing items
            for item in self.chipset_tree.get_children():
                self.chipset_tree.delete(item)
            
            self.log_callback(f"[UI] Tree cleared, now adding items...")

            # Add chipset data to tree
            count = 0
            for chipset, assets in sorted(self.chipset_data.items()):
                assets_str = ", ".join(assets) if assets else "(no assets)"
                self.chipset_tree.insert("", "end", values=(chipset, assets_str))
                count += 1
                self.log_callback(f"[UI] Added: {chipset} -> {assets_str}")

            self.log_callback(f"[UI]  Successfully displayed {count} chipsets in table")
            
            # Force tree update
            self.chipset_tree.update_idletasks()
            
        except Exception as e:
            self.log_callback(f"[UI ERROR] Failed to populate tree: {str(e)}")
            import traceback
            self.log_callback(f"[UI ERROR] Traceback: {traceback.format_exc()}")

    def on_chipset_select(self, event):
        """Handle chipset selection in tree"""
        selection = self.chipset_tree.selection()
        if selection:
            item = selection[0]
            values = self.chipset_tree.item(item, "values")
            if values:
                chipset_name = values[0]
                self.log_callback(f"[SELECT] Selected chipset: {chipset_name}")

    def on_select_chipset(self):
        """Handle Select Chipset button click"""
        selection = self.chipset_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a chipset from the table.")
            return

        item = selection[0]
        values = self.chipset_tree.item(item, "values")
        chipset_name = values[0]
        current_assets = self.chipset_data.get(chipset_name, [])

        # Confirm selection
        response = messagebox.askyesno(
            "Confirm Selection",
            f"Add asset apps to chipset: {chipset_name}?\n\nCurrent assets: {', '.join(current_assets) if current_assets else '(none)'}"
        )

        if not response:
            return

        self.selected_chipset = chipset_name
        self.log_callback(f"[CONFIRMED] Will add assets to chipset: {chipset_name}")

        # Update asset listbox - remove already existing assets
        self.asset_listbox.delete(0, tk.END)
        available_to_add = [asset for asset in AVAILABLE_ASSETS if asset not in current_assets]
        
        for asset in available_to_add:
            self.asset_listbox.insert(tk.END, asset)

        if not available_to_add:
            messagebox.showinfo(
                "All Assets Added",
                f"Chipset {chipset_name} already has all available assets."
            )
        else:
            self.log_callback(f"[UI] Updated asset selection - {len(available_to_add)} assets available to add")

    def validate_inputs(self):
        """Validate LoadApkAsset inputs"""
        # Check if chipset is selected
        if not self.selected_chipset:
            messagebox.showwarning("No Chipset Selected", "Please select a chipset first using the 'Select Chipset' button.")
            return None

        # Get selected assets from listbox
        selected_indices = self.asset_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Assets Selected", "Please select at least one asset app to add.")
            return None

        selected_assets = [self.asset_listbox.get(i) for i in selected_indices]

        # Get workspace inputs
        workspace_dict = {}
        for key, entry in self.workspace_entries.items():
            workspace_dict[key] = entry.get().strip()

        # Validate at least one workspace
        if not any(workspace_dict.values()):
            messagebox.showwarning("Missing Input", "At least one workspace is required.")
            return None

        # Get changelist input
        changelist_input = self.changelist_entry.get().strip()

        # Validate changelist format if provided
        if changelist_input:
            if not changelist_input.isdigit():
                messagebox.showwarning("Invalid Changelist", "Changelist ID must be a number.")
                return None

        return {
            "workspaces": workspace_dict,
            "chipset_name": self.selected_chipset,
            "selected_assets": selected_assets,
            "changelist_id": changelist_input if changelist_input else None,
        }

    def on_start_loadapkasset(self):
        """Handle start LoadApkAsset button click"""
        # Validate inputs
        inputs = self.validate_inputs()
        if not inputs:
            return

        self._run_loadapkasset_process(inputs)

    def _run_loadapkasset_process(self, inputs):
        """Run LoadApkAsset process in separate thread"""
        # Clear log and reset progress
        self.gui_utils.clear_text_widget(self.log_text)
        self.gui_utils.reset_progress(self.progress)

        # Disable start button during processing
        self.start_button.configure(state="disabled")

        def loadapkasset_thread():
            try:
                self.gui_utils.update_status("Processing: Running LoadApkAsset process...")

                # Run the LoadApkAsset process
                run_loadapkasset_process(
                    inputs["workspaces"],
                    inputs["chipset_name"],
                    inputs["selected_assets"],
                    inputs["changelist_id"],
                    self.log_callback,
                    self.progress_callback,
                    self.gui_utils.error_callback,
                )

                self.gui_utils.root.after(
                    0,
                    lambda: self.gui_utils.update_status("LoadApkAsset process completed"),
                )

            except Exception as e:
                error_message = str(e)
                self.gui_utils.root.after(
                    0,
                    lambda: self.log_callback(f"[ERROR] LoadApkAsset process failed: {error_message}"),
                )
                self.gui_utils.root.after(
                    0, lambda: self.gui_utils.error_callback("LoadApkAsset Error", error_message)
                )
            finally:
                # Re-enable start button when done
                self.gui_utils.root.after(
                    0, lambda: self.start_button.configure(state="normal")
                )

        # Start process in separate thread
        thread = threading.Thread(target=loadapkasset_thread, daemon=True)
        thread.start()
