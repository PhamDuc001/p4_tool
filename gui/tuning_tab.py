"""
Enhanced Tuning tab implementation with REL path support and property comparison
Handles the tuning mode UI and functionality including property management for 3 paths
Updated with auto-resolve functionality
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from config.p4_config import get_client_name, get_workspace_root
from processes.tuning_process import load_properties_for_tuning_enhanced, apply_tuning_changes_enhanced
from gui.property_dialog import PropertyDialog
from gui.comparison_dialog import ComparisonDialog  # New dialog for property comparison


class TuningTab:
    """Enhanced Tuning tab component with REL path support and auto-resolve"""

    def __init__(self, parent, gui_utils):
        self.parent = parent
        self.gui_utils = gui_utils
        
        # Create the tuning frame
        self.frame = ttk.Frame(parent)
        
        # Tuning mode data
        self.loaded_properties = None
        self.original_properties = {}
        self.comparison_data = None  # Store comparison data for 3 paths
        
        # Initialize components
        self.create_content()

    def create_content(self):
        """Create content for tuning mode with REL path and enhanced comparison"""
        # Input fields frame
        input_frame = ttk.LabelFrame(
            self.frame, text="Enter the device_common.mk file path", padding=10
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

        # REL Path (NEW)
        ttk.Label(input_frame, text="REL Depot Path:").grid(
            column=0, row=2, sticky="w", pady=2
        )
        self.rel_entry = ttk.Entry(input_frame, width=70)
        self.rel_entry.grid(column=1, row=2, padx=5, pady=2, sticky="ew")

        # Configure grid weights
        input_frame.columnconfigure(1, weight=1)

        # Control frame
        control_frame = ttk.Frame(input_frame)
        control_frame.grid(column=1, row=3, pady=10, sticky="e")

        # Load Properties button
        self.load_properties_btn = ttk.Button(
            control_frame, text="Load Properties", command=self.on_load_properties
        )
        self.load_properties_btn.pack(side="left", padx=(0, 10))

        # Apply Tuning button - Enhanced with 3-path support and auto-resolve
        self.apply_tuning_btn = ttk.Button(
            control_frame,
            text="Apply to All Paths",
            command=self.on_apply_tuning,
            state="disabled",
        )
        self.apply_tuning_btn.pack(side="left", padx=(0, 10))

        # Progress bar
        self.progress = ttk.Progressbar(
            control_frame, length=200, mode="determinate"
        )
        self.progress.pack(side="left", padx=(0, 10))

        # Properties table frame - Reduced height as requested
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
        """Create properties table with treeview - Reduced height for comparison table space"""
        # Table frame with scrollbars
        table_container = ttk.Frame(parent)
        table_container.pack(fill="both", expand=True)

        # Create treeview with enhanced styling but reduced height
        columns = ("Category", "Property", "Value")
        self.properties_tree = ttk.Treeview(
            table_container, columns=columns, show="tree headings", height=12  # Reduced from 18
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

        # Table control buttons
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
        # Clear tuning input fields including REL
        self.beni_entry.delete(0, tk.END)
        self.flumen_entry.delete(0, tk.END)
        self.rel_entry.delete(0, tk.END)  # NEW

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
        self.comparison_data = None  # NEW

        # Disable Apply button
        self.apply_tuning_btn.configure(state="disabled")

        self.log_callback(
            "[INFO] All fields and data cleared. Next load will fetch fresh data from server."
        )
        self.gui_utils.update_status(
            "Mode: Tuning value - Load properties from BENI, FLUMEN, and REL paths"
        )

    def on_load_properties(self):
        """Handle load properties button click - Enhanced for 3 paths"""
        beni_path = self.beni_entry.get().strip()
        flumen_path = self.flumen_entry.get().strip()
        rel_path = self.rel_entry.get().strip()  # NEW

        # Validation - at least one path is required
        has_beni = beni_path and beni_path.startswith("//")
        has_flumen = flumen_path and flumen_path.startswith("//")
        has_rel = rel_path and rel_path.startswith("//")  # NEW

        if not has_beni and not has_flumen and not has_rel:
            messagebox.showerror(
                "No Paths",
                "At least one depot path (BENI, FLUMEN, or REL) must be provided and start with //depot/...",
            )
            return

        self._load_properties_enhanced(
            beni_path if has_beni else "", 
            flumen_path if has_flumen else "",
            rel_path if has_rel else ""  # NEW
        )

    def _load_properties_enhanced(self, beni_path, flumen_path, rel_path):
        """Load properties from 3 paths and handle comparison"""
        # Clear table and reset progress
        for item in self.properties_tree.get_children():
            self.properties_tree.delete(item)
        self.gui_utils.reset_progress(self.progress)
        self.gui_utils.clear_text_widget(self.log_text)

        # Log that we're loading from 3 paths
        self.log_callback(
            "[INFO] Loading properties from BENI, FLUMEN, and REL paths..."
        )

        # Disable buttons during processing
        self.load_properties_btn.configure(state="disabled")
        self.apply_tuning_btn.configure(state="disabled")

        def load_thread():
            try:
                self.gui_utils.update_status("Processing: Loading properties from 3 paths...")
                
                # Load properties from all 3 paths
                result = load_properties_for_tuning_enhanced(
                    beni_path,
                    flumen_path,
                    rel_path,  # NEW parameter
                    self.progress_callback,
                    self.gui_utils.error_callback,
                    self.gui_utils.info_callback,
                )

                if result:
                    comparison_data, final_properties = result
                    
                    # Store comparison data
                    self.comparison_data = comparison_data
                    
                    # Check if properties are identical across all paths
                    if self._are_properties_identical(comparison_data):
                        # Properties are identical - proceed normally
                        self.log_callback("[INFO] Properties are identical across all paths.")
                        self._finalize_properties_loading(final_properties)
                    else:
                        # Properties differ - show comparison dialog
                        self.log_callback("[INFO] Properties differ between paths. Opening comparison dialog...")
                        self.gui_utils.root.after(0, lambda: self._show_comparison_dialog(comparison_data))
                else:
                    self.gui_utils.root.after(
                        0, lambda: self.gui_utils.update_status("Failed to load properties.")
                    )

            finally:
                # Re-enable load button when done
                self.gui_utils.root.after(
                    0, lambda: self.load_properties_btn.configure(state="normal")
                )

        # Start loading in separate thread
        thread = threading.Thread(target=load_thread, daemon=True)
        thread.start()

    def _are_properties_identical(self, comparison_data):
        """Check if all paths have identical properties"""
        if not comparison_data:
            return True
            
        # Get all valid paths
        valid_paths = [path for path in ['BENI', 'FLUMEN', 'REL'] if path in comparison_data]
        
        if len(valid_paths) <= 1:
            return True
            
        # Compare first path with others
        first_path = valid_paths[0]
        first_props = comparison_data[first_path]
        
        for path in valid_paths[1:]:
            current_props = comparison_data[path]
            
            # Compare LMKD
            if first_props.get('LMKD', {}) != current_props.get('LMKD', {}):
                return False
                
            # Compare Chimera
            if first_props.get('Chimera', {}) != current_props.get('Chimera', {}):
                return False
                
        return True

    def _show_comparison_dialog(self, comparison_data):
        """Show comparison dialog for user to choose source properties"""
        dialog = ComparisonDialog(self.gui_utils.root, comparison_data)
        if dialog.result:
            chosen_path, chosen_properties = dialog.result
            self.log_callback(f"[INFO] User selected properties from {chosen_path} path.")
            self._finalize_properties_loading(chosen_properties)

    def _finalize_properties_loading(self, final_properties):
        """Finalize the properties loading process"""
        self.loaded_properties = final_properties
        
        # Store original properties (without metadata)
        self.original_properties = {}
        for key, value in self.loaded_properties.items():
            if key != "_metadata":
                self.original_properties[key] = (
                    value.copy() if isinstance(value, dict) else value
                )

        # Populate table
        self._populate_properties_table(self.loaded_properties)
        self.apply_tuning_btn.configure(state="normal")
        self.gui_utils.update_status(
            "Properties loaded successfully. You can now modify values and apply to all paths."
        )
        self.log_callback(
            "[INFO] Properties loaded and ready for modifications."
        )

    def on_apply_tuning(self):
        """Handle apply tuning button click - Enhanced for 3 paths with auto-resolve"""
        if not self.loaded_properties or "_metadata" not in self.loaded_properties:
            messagebox.showerror(
                "No Data", "Please load properties first before applying changes."
            )
            return

        # Get current properties from table
        current_properties = self._get_table_properties()

        # Check if there are any changes (including deletions)
        if self._properties_unchanged(current_properties):
            messagebox.showinfo(
                "No Changes",
                "No properties have been modified or deleted. Nothing to apply.",
            )
            return

        # Get depot paths - may need auto-resolve
        original_depot_paths = self.loaded_properties["_metadata"]["depot_paths"]
        
        # Check if we need to auto-resolve additional paths
        needs_auto_resolve = len(original_depot_paths) == 1
        
        if needs_auto_resolve:
            # Show confirmation with auto-resolve info
            single_path = list(original_depot_paths.keys())[0]
            confirm_message = f"You loaded properties from {single_path} only.\n\n"
            
            if single_path == "REL":
                confirm_message += "Auto-resolve will find FLUMEN and BENI paths using integration history.\n"
                confirm_message += "Changes will be applied to: REL → FLUMEN → BENI\n\n"
            elif single_path == "FLUMEN":
                confirm_message += "Auto-resolve will find BENI path using integration history.\n"
                confirm_message += "Changes will be applied to: FLUMEN → BENI\n\n"
            else:  # BENI
                confirm_message += "No auto-resolve needed for BENI.\n"
                confirm_message += "Changes will be applied to: BENI only\n\n"
            
            # Show changes summary
            changes_summary = self._get_changes_summary(current_properties)
            if changes_summary:
                confirm_message += f"Changes to apply:\n{changes_summary}\n\n"
            
            confirm_message += "Do you want to continue?"
            
            if not messagebox.askyesno("Confirm Apply with Auto-Resolve", confirm_message):
                return
        else:
            # Multiple paths loaded - standard confirmation
            changes_summary = self._get_changes_summary(current_properties)
            if changes_summary:
                confirm_message = (
                    f"The following changes will be applied to ALL PATHS:\n\n{changes_summary}\n\n"
                )
                confirm_message += "This will apply all property changes to BENI, FLUMEN, and REL files and create a pending changelist.\n\n"
                confirm_message += "Do you want to continue?"

                if not messagebox.askyesno("Confirm Apply Changes", confirm_message):
                    return

        self._run_apply_tuning_enhanced_with_auto_resolve(current_properties, original_depot_paths)

    def _run_apply_tuning_enhanced_with_auto_resolve(self, current_properties, original_depot_paths):
        """Run apply tuning process with auto-resolve for missing paths"""
        # Clear tuning log and reset progress
        self.gui_utils.clear_text_widget(self.log_text)
        self.gui_utils.reset_progress(self.progress)

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
                    "Processing: Applying tuning changes with auto-resolve..."
                )
                
                # Import auto-resolve function from tuning_process
                from processes.tuning_process import apply_tuning_changes_enhanced_with_auto_resolve
                
                success = apply_tuning_changes_enhanced_with_auto_resolve(
                    current_properties,
                    original_depot_paths,
                    self.log_callback,
                    self.progress_callback,
                    self.gui_utils.error_callback,
                )

                if success:
                    self.gui_utils.root.after(
                        0,
                        lambda: self.gui_utils.update_status(
                            "Tuning changes applied successfully to all paths!"
                        ),
                    )
                    self.gui_utils.root.after(
                        0,
                        lambda: messagebox.showinfo(
                            "Success",
                            "Tuning changes have been applied successfully to all paths!\n"
                            "Check the log for changelist details.",
                        ),
                    )

                    # Update original properties
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
                    f"[MODIFIED] {category}.{key}: {original_value} → {current_value}"
                )

        return changes

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
                    f"This will delete {len(children)} properties and they will be removed from ALL files when you apply changes.",
                ):
                    self.properties_tree.delete(item)
                    self.log_callback(
                        f"[INFO] Deleted all properties in {values[0]} category. Apply changes to update all files."
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
                f"This property will be removed from ALL files when you apply changes.",
            ):
                # Get parent item ID before deleting the current item
                parent = self.properties_tree.parent(item)
                
                self.properties_tree.delete(item)
                self.log_callback(
                    f"[INFO] Deleted property {values[0]}.{values[1]}. Apply changes to update all files."
                )

                # Check if parent category is now empty and remove if so
                if parent:
                    remaining_children = self.properties_tree.get_children(parent)
                    if not remaining_children:
                        # Get the category name from the parent item's values before deleting it
                        parent_category_name = self.properties_tree.item(parent, "values")[0]
                        self.properties_tree.delete(parent)
                        self.log_callback(
                            f"[INFO] Removed empty {parent_category_name} category."
                        )
                return

        # If we get here, selection is invalid
        messagebox.showwarning(
            "Invalid Selection", "Please select a valid property to delete."
        )

    def _get_table_properties(self):
        """Extract properties from the table"""
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
