"""
Tuning tab implementation
Handles the tuning mode UI and functionality including property management
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from config.p4_config import get_client_name, get_workspace_root
from processes.tuning_process import load_properties_for_tuning, apply_tuning_changes
from gui.property_dialog import PropertyDialog


class TuningTab:
    """Tuning tab component"""

    def __init__(self, parent, gui_utils):
        self.parent = parent
        self.gui_utils = gui_utils
        
        # Create the tuning frame
        self.frame = ttk.Frame(parent)
        
        # Tuning mode data
        self.loaded_properties = None
        self.original_properties = {}
        
        # Initialize components
        self.create_content()

    def create_content(self):
        """Create content for tuning mode with Apply functionality"""
        # Input fields frame
        input_frame = ttk.LabelFrame(
            self.frame, text="Configuration", padding=10
        )
        input_frame.pack(fill="x", pady=(0, 10))

        # BENI Path
        ttk.Label(input_frame, text="BENI Depot Path:").grid(
            column=0, row=0, sticky="w", pady=2
        )
        self.beni_entry = ttk.Entry(input_frame, width=70)
        self.beni_entry.grid(column=1, row=0, padx=5, pady=2, sticky="ew")

        # FLUMEN Path
        ttk.Label(input_frame, text="FLUMEN Depot Path:").grid(
            column=0, row=1, sticky="w", pady=2
        )
        self.flumen_entry = ttk.Entry(input_frame, width=70)
        self.flumen_entry.grid(column=1, row=1, padx=5, pady=2, sticky="ew")

        # Configure grid weights
        input_frame.columnconfigure(1, weight=1)

        # Control frame
        control_frame = ttk.Frame(input_frame)
        control_frame.grid(column=1, row=2, pady=10, sticky="e")

        # Load Properties button
        self.load_properties_btn = ttk.Button(
            control_frame, text="Load Properties", command=self.on_load_properties
        )
        self.load_properties_btn.pack(side="left", padx=(0, 10))

        # Apply Tuning button - Enhanced with delete support
        self.apply_tuning_btn = ttk.Button(
            control_frame,
            text="Apply Tuning",
            command=self.on_apply_tuning,
            state="disabled",
        )
        self.apply_tuning_btn.pack(side="left", padx=(0, 10))

        # Progress bar
        self.progress = ttk.Progressbar(
            control_frame, length=200, mode="determinate"
        )
        self.progress.pack(side="left", padx=(0, 10))

        # Properties table frame - Expanded height
        table_frame = ttk.LabelFrame(
            self.frame, text="LMKD & Chimera Properties", padding=5
        )
        table_frame.pack(fill="both", expand=True)

        # Create treeview for properties table
        self.create_properties_table(table_frame)

        # Log output frame for tuning operations - Reduced height
        log_frame = ttk.LabelFrame(self.frame, text="Tuning Log", padding=5)
        log_frame.pack(fill="x", pady=(10, 0))

        # Create text widget with scrollbar for tuning log
        self.log_text = self.gui_utils.create_text_with_scrollbar(log_frame, height=6)

        # Create callbacks
        self.log_callback = self.gui_utils.create_log_callback(self.log_text)
        self.progress_callback = self.gui_utils.create_progress_callback(self.progress)

    def create_properties_table(self, parent):
        """Create properties table with treeview - Enhanced with grid lines and wider table"""
        # Table frame with scrollbars
        table_container = ttk.Frame(parent)
        table_container.pack(fill="both", expand=True)

        # Create treeview with enhanced styling
        columns = ("Category", "Property", "Value")
        self.properties_tree = ttk.Treeview(
            table_container, columns=columns, show="tree headings", height=18
        )

        # Configure columns with wider widths
        self.properties_tree.heading("#0", text="", anchor="w")
        self.properties_tree.column("#0", width=0, stretch=False)

        self.properties_tree.heading("Category", text="Category")
        self.properties_tree.column("Category", width=120, anchor="w")

        self.properties_tree.heading("Property", text="Property")
        self.properties_tree.column("Property", width=400, anchor="w")

        self.properties_tree.heading("Value", text="Value")
        self.properties_tree.column("Value", width=300, anchor="w")

        # Configure treeview styling for grid lines
        style = ttk.Style()
        style.configure(
            "Treeview", fieldbackground="white", borderwidth=1, relief="solid"
        )
        style.configure("Treeview.Heading", borderwidth=1, relief="solid")

        # Scrollbars
        v_scrollbar = ttk.Scrollbar(
            table_container, orient="vertical", command=self.properties_tree.yview
        )
        h_scrollbar = ttk.Scrollbar(
            table_container, orient="horizontal", command=self.properties_tree.xview
        )
        self.properties_tree.configure(
            yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set
        )

        # Pack treeview and scrollbars
        self.properties_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")

        # Configure grid weights
        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)

        # Buttons frame
        buttons_frame = ttk.Frame(parent)
        buttons_frame.pack(fill="x", pady=5)

        # Table control buttons - Removed Export Properties button
        ttk.Button(
            buttons_frame,
            text="Add LMKD Property",
            command=lambda: self.add_property("LMKD"),
        ).pack(side="left", padx=5)
        ttk.Button(
            buttons_frame,
            text="Add Chimera Property",
            command=lambda: self.add_property("Chimera"),
        ).pack(side="left", padx=5)
        ttk.Button(
            buttons_frame, text="Edit Selected", command=self.edit_property
        ).pack(side="left", padx=5)
        ttk.Button(
            buttons_frame, text="Delete Selected", command=self.delete_property
        ).pack(side="left", padx=5)

        # Bind double-click to edit
        self.properties_tree.bind("<Double-1>", lambda e: self.edit_property())

    def show(self):
        """Show the tuning tab"""
        self.frame.pack(fill="both", expand=True)

    def hide(self):
        """Hide the tuning tab"""
        self.frame.pack_forget()

    def clear_all(self):
        """Clear all input fields and data"""
        # Clear tuning input fields
        self.beni_entry.delete(0, tk.END)
        self.flumen_entry.delete(0, tk.END)

        # Clear properties table
        for item in self.properties_tree.get_children():
            self.properties_tree.delete(item)

        # Clear tuning log
        self.gui_utils.clear_text_widget(self.log_text)

        # Reset progress bar
        self.gui_utils.reset_progress(self.progress)

        # IMPORTANT: Reset all cached data to force fresh load
        self.original_properties = {}
        self.loaded_properties = None

        # Disable Apply button
        self.apply_tuning_btn.configure(state="disabled")

        self.log_callback(
            "[INFO] All fields and data cleared. Next load will fetch fresh data from server."
        )
        self.gui_utils.update_status(
            "Mode: Tuning value - Load properties first, then modify and apply changes"
        )

    def on_load_properties(self):
        """Handle load properties button click - Enhanced to force fresh load"""
        beni_path = self.beni_entry.get().strip()
        flumen_path = self.flumen_entry.get().strip()

        # Validation - at least one path is required
        has_beni = beni_path and beni_path.startswith("//")
        has_flumen = flumen_path and flumen_path.startswith("//")

        if not has_beni and not has_flumen:
            messagebox.showerror(
                "No Paths",
                "At least one depot path (BENI or FLUMEN) must be provided and start with //depot/...",
            )
            return

        self._load_properties(
            beni_path if has_beni else "", flumen_path if has_flumen else ""
        )

    def _load_properties(self, beni_path, flumen_path):
        """Load properties in separate thread - Enhanced to always fetch fresh data"""
        # Clear table and reset progress
        for item in self.properties_tree.get_children():
            self.properties_tree.delete(item)
        self.gui_utils.reset_progress(self.progress)
        self.gui_utils.clear_text_widget(self.log_text)

        # Log that we're forcing fresh load
        self.log_callback(
            "[INFO] Loading fresh properties from server (ignoring local cache)..."
        )

        # Disable buttons during processing
        self.load_properties_btn.configure(state="disabled")
        self.apply_tuning_btn.configure(state="disabled")

        def load_thread():
            try:
                self.gui_utils.update_status("Processing: Loading properties from server...")
                # The load_properties_for_tuning function will automatically sync latest version
                self.loaded_properties = load_properties_for_tuning(
                    beni_path,
                    flumen_path,
                    self.progress_callback,
                    self.gui_utils.error_callback,
                    self.gui_utils.info_callback,
                )

                if self.loaded_properties:
                    # Store original properties (without metadata)
                    self.original_properties = {}
                    for key, value in self.loaded_properties.items():
                        if key != "_metadata":
                            self.original_properties[key] = (
                                value.copy() if isinstance(value, dict) else value
                            )

                    # Populate table
                    self.gui_utils.root.after(
                        0,
                        lambda: self._populate_properties_table(self.loaded_properties),
                    )
                    self.gui_utils.root.after(
                        0, lambda: self.apply_tuning_btn.configure(state="normal")
                    )
                    self.gui_utils.root.after(
                        0,
                        lambda: self.gui_utils.update_status(
                            "Properties loaded successfully. You can now modify values and apply changes."
                        ),
                    )
                    self.gui_utils.root.after(
                        0,
                        lambda: self.log_callback(
                            "[INFO] Fresh properties loaded from server. Ready for modifications."
                        ),
                    )
                else:
                    self.gui_utils.root.after(
                        0, lambda: self.gui_utils.update_status("Failed to load properties.")
                    )
                    self.gui_utils.root.after(
                        0,
                        lambda: self.log_callback(
                            "[ERROR] Failed to load properties."
                        ),
                    )

            finally:
                # Re-enable load button when done
                self.gui_utils.root.after(
                    0, lambda: self.load_properties_btn.configure(state="normal")
                )

        # Start loading in separate thread
        thread = threading.Thread(target=load_thread, daemon=True)
        thread.start()

    def on_apply_tuning(self):
        """Handle apply tuning button click with delete support"""
        if not self.loaded_properties or "_metadata" not in self.loaded_properties:
            messagebox.showerror(
                "No Data", "Please load properties first before applying changes."
            )
            return

        # Get current properties from table (this will only include existing properties)
        current_properties = self._get_table_properties()

        # Check if there are any changes (including deletions)
        if self._properties_unchanged(current_properties):
            messagebox.showinfo(
                "No Changes",
                "No properties have been modified or deleted. Nothing to apply.",
            )
            return

        # Show changes summary including deletions
        changes_summary = self._get_changes_summary(current_properties)
        if changes_summary:
            confirm_message = (
                f"The following changes will be applied:\n\n{changes_summary}\n\n"
            )
            confirm_message += "This will apply all property changes to the target files and create a pending changelist.\n\n"
            confirm_message += "Do you want to continue?"

            if not messagebox.askyesno("Confirm Apply Changes", confirm_message):
                return

        self._run_apply_tuning(current_properties)

    def _get_changes_summary(self, current_properties):
        """Get summary of changes including additions, modifications, and deletions"""
        changes = []

        # Compare LMKD properties
        original_lmkd = self.original_properties.get("LMKD", {})
        current_lmkd = current_properties.get("LMKD", {})
        lmkd_changes = self._compare_property_categories(
            original_lmkd, current_lmkd, "LMKD"
        )
        changes.extend(lmkd_changes)

        # Compare Chimera properties
        original_chimera = self.original_properties.get("Chimera", {})
        current_chimera = current_properties.get("Chimera", {})
        chimera_changes = self._compare_property_categories(
            original_chimera, current_chimera, "Chimera"
        )
        changes.extend(chimera_changes)

        return "\n".join(changes) if changes else ""

    def _compare_property_categories(self, original_dict, current_dict, category):
        """Compare two property dictionaries and return list of changes"""
        changes = []

        all_keys = set(original_dict.keys()) | set(current_dict.keys())

        for key in all_keys:
            original_value = original_dict.get(key)
            current_value = current_dict.get(key)

            if original_value is None and current_value is not None:
                # Added
                changes.append(f"[ADDED] {category}.{key} = {current_value}")
            elif original_value is not None and current_value is None:
                # Deleted
                changes.append(f"[DELETED] {category}.{key} (was: {original_value})")
            elif original_value != current_value:
                # Modified
                changes.append(
                    f"[MODIFIED] {category}.{key}: {original_value} â†’ {current_value}"
                )

        return changes

    def _run_apply_tuning(self, current_properties):
        """Run apply tuning process in separate thread"""
        # Clear tuning log and reset progress
        self.gui_utils.clear_text_widget(self.log_text)
        self.gui_utils.reset_progress(self.progress)

        # Get depot paths from metadata
        depot_paths = self.loaded_properties["_metadata"]["depot_paths"]

        # Log P4 configuration info
        client_name = get_client_name()
        workspace_root = get_workspace_root()
        if client_name and workspace_root:
            self.log_callback(f"[CONFIG] Using P4 Client: {client_name}")
            self.log_callback(f"[CONFIG] Using Workspace: {workspace_root}")

        # Disable buttons during processing
        self.apply_tuning_btn.configure(state="disabled")
        self.load_properties_btn.configure(state="disabled")

        def apply_thread():
            try:
                self.gui_utils.update_status(
                    "Processing: Applying tuning changes (including deletions)..."
                )
                success = apply_tuning_changes(
                    current_properties,
                    depot_paths,
                    self.log_callback,
                    self.progress_callback,
                    self.gui_utils.error_callback,
                )

                if success:
                    self.gui_utils.root.after(
                        0,
                        lambda: self.gui_utils.update_status(
                            "Tuning changes applied successfully!"
                        ),
                    )
                    self.gui_utils.root.after(
                        0,
                        lambda: messagebox.showinfo(
                            "Success",
                            "Tuning changes have been applied successfully!\n"
                            "Check the log for changelist details.",
                        ),
                    )

                    # Update original properties to reflect current state
                    self.gui_utils.root.after(
                        0,
                        lambda: self._update_original_properties_after_apply(
                            current_properties
                        ),
                    )
                else:
                    self.gui_utils.root.after(
                        0,
                        lambda: self.gui_utils.update_status("Failed to apply tuning changes."),
                    )

            finally:
                # Re-enable buttons when done
                self.gui_utils.root.after(
                    0, lambda: self.apply_tuning_btn.configure(state="normal")
                )
                self.gui_utils.root.after(
                    0, lambda: self.load_properties_btn.configure(state="normal")
                )

        # Start apply process in separate thread
        thread = threading.Thread(target=apply_thread, daemon=True)
        thread.start()

    def _update_original_properties_after_apply(self, applied_properties):
        """Update original properties to match applied state"""
        for key, value in applied_properties.items():
            if key != "_metadata":
                self.original_properties[key] = (
                    value.copy() if isinstance(value, dict) else value
                )

    def _properties_unchanged(self, current_properties):
        """Check if properties have been modified or deleted"""
        if not self.original_properties:
            return True

        # Compare LMKD properties
        original_lmkd = self.original_properties.get("LMKD", {})
        current_lmkd = current_properties.get("LMKD", {})
        if original_lmkd != current_lmkd:
            return False

        # Compare Chimera properties
        original_chimera = self.original_properties.get("Chimera", {})
        current_chimera = current_properties.get("Chimera", {})
        if original_chimera != current_chimera:
            return False

        return True

    def _populate_properties_table(self, properties_data):
        """Populate the properties table with loaded data"""
        # Clear existing items
        for item in self.properties_tree.get_children():
            self.properties_tree.delete(item)

        # Add LMKD properties
        if "LMKD" in properties_data and properties_data["LMKD"]:
            lmkd_parent = self.properties_tree.insert(
                "", "end", text="LMKD", values=("LMKD", "", "")
            )
            for prop, value in properties_data["LMKD"].items():
                self.properties_tree.insert(
                    lmkd_parent, "end", values=("LMKD", prop, value)
                )

        # Add Chimera properties
        if "Chimera" in properties_data and properties_data["Chimera"]:
            chimera_parent = self.properties_tree.insert(
                "", "end", text="Chimera", values=("Chimera", "", "")
            )
            for prop, value in properties_data["Chimera"].items():
                self.properties_tree.insert(
                    chimera_parent, "end", values=("Chimera", prop, value)
                )

        # Expand all nodes
        for item in self.properties_tree.get_children():
            self.properties_tree.item(item, open=True)

    def add_property(self, category):
        """Add new property to the table"""
        dialog = PropertyDialog(self.gui_utils.root, f"Add {category} Property", "", "")
        if dialog.result:
            prop_name, prop_value = dialog.result

            # Find or create category parent
            parent_item = None
            for item in self.properties_tree.get_children():
                if self.properties_tree.item(item, "values")[0] == category:
                    parent_item = item
                    break

            if not parent_item:
                parent_item = self.properties_tree.insert(
                    "", "end", text=category, values=(category, "", "")
                )
                self.properties_tree.item(parent_item, open=True)

            # Add new property
            self.properties_tree.insert(
                parent_item, "end", values=(category, prop_name, prop_value)
            )

            # Enable Apply button if properties are loaded
            if self.loaded_properties:
                self.apply_tuning_btn.configure(state="normal")

    def edit_property(self):
        """Edit selected property"""
        selected = self.properties_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a property to edit.")
            return

        item = selected[0]
        values = self.properties_tree.item(item, "values")

        # Don't edit category headers
        if len(values) < 3 or not values[1]:
            return

        category, prop_name, prop_value = values
        dialog = PropertyDialog(
            self.gui_utils.root, f"Edit {category} Property", prop_name, prop_value
        )
        if dialog.result:
            new_prop_name, new_prop_value = dialog.result
            self.properties_tree.item(
                item, values=(category, new_prop_name, new_prop_value)
            )

    def delete_property(self):
        """Delete selected property with enhanced logic"""
        selected = self.properties_tree.selection()
        if not selected:
            messagebox.showwarning(
                "No Selection", "Please select a property to delete."
            )
            return

        item = selected[0]
        values = self.properties_tree.item(item, "values")

        # Check if it's a category header
        if (
            len(values) >= 3 and values[0] and not values[1]
        ):  # Category header has category but no property name
            # Check if category has children
            children = self.properties_tree.get_children(item)
            if children:
                # Ask user if they want to delete all properties in this category
                if messagebox.askyesno(
                    "Confirm Delete Category",
                    f"Are you sure you want to delete all properties in '{values[0]}' category?\n\n"
                    f"This will delete {len(children)} properties and they will be removed from the file when you apply changes.",
                ):
                    self.properties_tree.delete(item)
                    self.log_callback(
                        f"[INFO] Deleted all properties in {values[0]} category. Apply changes to update files."
                    )
                return
            else:
                # Empty category can be deleted
                if messagebox.askyesno(
                    "Confirm Delete",
                    f"Are you sure you want to delete the empty '{values[0]}' category?",
                ):
                    self.properties_tree.delete(item)
                return

        # Check if it's a property (has both category and property name)
        if len(values) >= 3 and values[1]:
            if messagebox.askyesno(
                "Confirm Delete Property",
                f"Are you sure you want to delete property '{values[1]}'?\n\n"
                f"This property will be removed from the file when you apply changes.",
            ):
                self.properties_tree.delete(item)
                self.log_callback(
                    f"[INFO] Deleted property {values[0]}.{values[1]}. Apply changes to update files."
                )

                # Check if parent category is now empty and remove if so
                parent = self.properties_tree.parent(item)
                if parent:
                    remaining_children = self.properties_tree.get_children(parent)
                    if not remaining_children:
                        self.properties_tree.delete(parent)
                        self.log_callback(
                            f"[INFO] Removed empty {values[0]} category."
                        )
                return

        # If we get here, selection is invalid
        messagebox.showwarning(
            "Invalid Selection", "Please select a valid property to delete."
        )

    def _get_table_properties(self):
        """Extract properties from the table (only includes existing properties, excludes deleted ones)"""
        properties = {"LMKD": {}, "Chimera": {}}

        for parent in self.properties_tree.get_children():
            parent_values = self.properties_tree.item(parent, "values")
            category = parent_values[0]

            if category in properties:
                for child in self.properties_tree.get_children(parent):
                    child_values = self.properties_tree.item(child, "values")
                    if len(child_values) >= 3 and child_values[1]:
                        properties[category][child_values[1]] = child_values[2]

        return properties