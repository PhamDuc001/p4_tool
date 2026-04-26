"""
Enhanced Tuning tab implementation with REL path support and property comparison
Handles the tuning mode UI and functionality including property management for 3 paths
Updated with auto-resolve functionality
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from config.p4_config import get_client_name, get_workspace_root
from gui.property_dialog import PropertyDialog
from gui.comparison_dialog import ComparisonDialog  # New dialog for property comparison
from services.tuning_service import TuningService


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
        self.tuning_service = TuningService()
        
        # Initialize components
        self.create_content()

    def create_content(self):
        """Create content for tuning mode with REL path and enhanced comparison"""
        # Input fields frame
        input_frame = ttk.LabelFrame(
            self.frame, text="Enter workspace or device_common.mk depot path", padding=10
        )
        input_frame.pack(fill="x", pady=(0, 10))

        # BENI Path
        ttk.Label(input_frame, text="BENI (Workspace or Depot Path):").grid(
            column=0, row=0, sticky="w", pady=2
        )
        self.beni_entry = ttk.Entry(input_frame, width=70)
        self.beni_entry.grid(column=1, row=0, padx=5, pady=2, sticky="ew")

        # FLUMEN Path
        ttk.Label(input_frame, text="FLUMEN (Workspace or Depot Path):").grid(
            column=0, row=1, sticky="w", pady=2
        )
        self.flumen_entry = ttk.Entry(input_frame, width=70)
        self.flumen_entry.grid(column=1, row=1, padx=5, pady=2, sticky="ew")

        # REL Path (NEW)
        ttk.Label(input_frame, text="REL (Workspace or Depot Path):").grid(
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
        """Handle load properties button click - Enhanced for 3 paths with workspace support"""
        beni_input = self.beni_entry.get().strip()
        flumen_input = self.flumen_entry.get().strip()
        rel_input = self.rel_entry.get().strip()

        # Validation - at least one valid input is required (workspace or depot path)
        has_beni = beni_input and (beni_input.startswith("//") or beni_input.upper().startswith("TEMPLATE"))
        has_flumen = flumen_input and (flumen_input.startswith("//") or flumen_input.upper().startswith("TEMPLATE"))
        has_rel = rel_input and (rel_input.startswith("//") or rel_input.upper().startswith("TEMPLATE"))

        if not has_beni and not has_flumen and not has_rel:
            messagebox.showerror(
                "No Valid Inputs",
                "At least one valid input (workspace name starting with TEMPLATE_* or depot path starting with //depot/...) is required."
            )
            return

        self._load_properties_enhanced(beni_input, flumen_input, rel_input)

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
                
                result = self.tuning_service.load_properties(
                    beni_path,
                    flumen_path,
                    rel_path,
                    progress_callback=self.progress_callback,
                    log_callback=self.log_callback,
                )

                if result:
                    comparison_data = result.comparison_data
                    final_properties = result.merged_properties
                    
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

            except Exception as exc:
                self.gui_utils.error_callback("Load Properties Error", str(exc))
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
        return self.tuning_service.properties_are_identical(comparison_data)

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

        # Store original properties (without metadata) and preserve full conditional structure.
        self.original_properties = {}
        for key, value in self.loaded_properties.items():
            if key != "_metadata":
                if isinstance(value, dict):
                    import copy
                    self.original_properties[key] = copy.deepcopy(value)
                else:
                    self.original_properties[key] = value

        # Populate table with conditional-aware display
        self._populate_properties_table_v2(self.loaded_properties)
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
        confirmation = self.tuning_service.build_apply_confirmation(
            original_depot_paths,
            current_properties,
            self.original_properties,
        )
        if not messagebox.askyesno(confirmation.title, confirmation.message):
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
                
                result = self.tuning_service.apply_changes(
                    current_properties,
                    original_depot_paths,
                    log_callback=self.log_callback,
                    progress_callback=self.progress_callback,
                    original_properties=self.original_properties,
                    confirm_reopen_callback=self._confirm_reopen_checkout,
                )

                if result.success:
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
                    self.gui_utils.error_callback("Apply Tuning Error", result.message)
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

    def _confirm_reopen_checkout(self, depot_path, current_changelist, target_changelist):
        """Ask whether an already-opened file should move to the new changelist."""
        title = "File Already Opened"
        message = (
            f"File is currently opened in changelist {current_changelist}.\n\n"
            f"Do you want to move it to changelist {target_changelist}?\n\n"
            f"File: {depot_path}"
        )
        return self.gui_utils.ask_yes_no_threadsafe(title, message)

    def _update_original_properties_after_apply(self, applied_properties):
        """Update original properties to match applied state"""
        for key, value in applied_properties.items():
            if key != "_metadata":
                self.original_properties[key] = (
                    value.copy() if isinstance(value, dict) else value
                )

    def _properties_unchanged(self, current_properties):
        """Check if properties have been modified or deleted (supports v2 conditional structure)"""
        return self.tuning_service.properties_unchanged(
            self.original_properties,
            current_properties,
        )

    def _get_changes_summary(self, current_properties):
        """Get summary of changes including additions, modifications, and deletions (v2 aware)"""
        return self.tuning_service.summarize_changes(
            self.original_properties,
            current_properties,
        )

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
                    f"[MODIFIED] {category}.{key}: {original_value} -> {current_value}"
                )

        return changes

    def _populate_properties_table(self, properties_data):
        """Populate the properties table with loaded data (v2 conditional structure)"""
        self._populate_properties_table_v2(properties_data)

    def _populate_properties_table_v2(self, properties_data):
        """
        Populate the properties table using the v2 conditional-aware structure.
        Each category is displayed with:
          - Flat properties as direct children of the category node
          - Each conditional block as a sub-group with [if] and [else] nodes
        """
        # Clear existing items
        for item in self.properties_tree.get_children():
            self.properties_tree.delete(item)

        for category in ("LMKD", "Chimera"):
            cat_data = properties_data.get(category)
            if not cat_data:
                continue

            # Support both v2 dict and legacy flat dict
            if isinstance(cat_data, dict) and '_flat' in cat_data:
                flat_props = cat_data.get('_flat', {})
                conditional_blocks = cat_data.get('_conditional', [])
            else:
                # Legacy: cat_data is a flat {prop: value} dict
                flat_props = cat_data if isinstance(cat_data, dict) else {}
                conditional_blocks = []

            # Skip if empty
            if not flat_props and not conditional_blocks:
                continue

            # Category parent node
            cat_parent = self.properties_tree.insert(
                "", "end", text=category, values=(category, "", ""), tags=("category",)
            )

            # --- Conditional blocks first (before flat, matching file order) ---
            for i, block in enumerate(conditional_blocks):
                condition = block.get('condition', f'block_{i}')
                if_props = block.get('if_props', {})
                else_props = block.get('else_props')

                # Condition group header
                short_cond = condition[:60] + ('...' if len(condition) > 60 else '')
                cond_node = self.properties_tree.insert(
                    cat_parent, "end",
                    text=f"[{short_cond}]",
                    values=(category, f"[cond:{i}]", condition),
                    tags=("condition_group", f"block_{i}")
                )

                # if-block properties
                for prop, value in if_props.items():
                    self.properties_tree.insert(
                        cond_node, "end",
                        values=(category, prop, value),
                        tags=("conditional_property", "if_block", f"block_{i}_if")
                    )

                # else node + else properties
                if else_props is not None:
                    else_node = self.properties_tree.insert(
                        cond_node, "end",
                        text="[else]",
                        values=(category, "[else]", ""),
                        tags=("else_group", f"block_{i}")
                    )
                    for prop, value in else_props.items():
                        self.properties_tree.insert(
                            else_node, "end",
                            values=(category, prop, value),
                            tags=("conditional_property", "else_block", f"block_{i}_else")
                        )
                    self.properties_tree.item(else_node, open=True)

                self.properties_tree.item(cond_node, open=True)

            # --- Flat properties ---
            for prop, value in flat_props.items():
                self.properties_tree.insert(
                    cat_parent, "end",
                    values=(category, prop, value),
                    tags=("property",)
                )

            self.properties_tree.item(cat_parent, open=True)

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
        tags = self.properties_tree.item(item, "tags")

        # Don't edit category headers
        if len(values) < 3 or not values[1]:
            return

        category, prop_name, prop_value = values

        # Don't edit condition group headers or else group headers
        if not prop_name or prop_name.startswith("[cond:") or prop_name == "[else]":
            return

        # For conditional properties (if/else block items), edit the value directly.
                    # The user clicked exactly one context node; edit that specific value.
        if "conditional_property" in tags:
            ctx_label = "if" if "if_block" in tags else "else"
            dialog = PropertyDialog(
                self.gui_utils.root,
                f"Edit {category} Property  [{ctx_label} context]",
                prop_name, prop_value
            )
            if dialog.result:
                _, new_prop_value = dialog.result
                self.properties_tree.item(item, values=(category, prop_name, new_prop_value))
        else:
            # Flat property editing
            dialog = PropertyDialog(
                self.gui_utils.root, f"Edit {category} Property", prop_name, prop_value
            )
            if dialog.result:
                new_prop_name, new_prop_value = dialog.result
                self.properties_tree.item(
                    item, values=(category, new_prop_name, new_prop_value)
                )


    def _edit_conditional_property(self, item, category, prop_name, prop_value, tags):
        """Edit conditional property vá»›i ENHANCED context awareness"""
        # Get all contexts for this property name
        context_info = self._get_all_contexts_for_property(prop_name, category)
        
        # If multiple contexts exist, use enhanced dialog
        if context_info and len(context_info.get('contexts', [])) > 1:
            # Show enhanced conditional property dialog
            from gui.property_dialog import EnhancedConditionalPropertyDialog
            
            # Prepare context values for dialog
            prop_values_by_context = {}
            for context in context_info['contexts']:
                context_name = context['name']
                context_value = context['value']
                prop_values_by_context[context_name] = context_value
            
            dialog = EnhancedConditionalPropertyDialog(
                self.gui_utils.root, 
                f"Edit {category} Property - Conditional Contexts", 
                prop_name, 
                prop_values_by_context
            )
            
            if dialog.result:
                # Handle enhanced conditional property update
                self._update_enhanced_conditional_property_values(item, dialog.result, category)
        else:
            # Simple edit for single context or flat property
            dialog = PropertyDialog(
                self.gui_utils.root, f"Edit {category} Property", prop_name, prop_value
            )
            if dialog.result:
                new_prop_name, new_prop_value = dialog.result
                self.properties_tree.item(
                    item, values=(category, new_prop_name, new_prop_value)
                )

    def _get_all_contexts_for_property(self, prop_name, category):
        """Get all contexts for a specific property name"""
        contexts = []
        
        # Find all instances of this property in different contexts
        for parent in self.properties_tree.get_children():
            parent_values = self.properties_tree.item(parent, "values")
            if parent_values[0] == category:
                # Check direct children (flat properties)
                for child in self.properties_tree.get_children(parent):
                    child_values = self.properties_tree.item(child, "values")
                    if len(child_values) >= 3 and child_values[1] == prop_name:
                        contexts.append({
                            'name': 'default',
                            'value': child_values[2],
                            'item': child,
                            'type': 'flat'
                        })
                
                # Check conditional context children
                for context_parent in self.properties_tree.get_children(parent):
                    context_values = self.properties_tree.item(context_parent, "values")
                    if len(context_values) >= 2 and context_values[1].startswith('['):
                        # This is a conditional context
                        context_name = context_values[1]
                        for prop_item in self.properties_tree.get_children(context_parent):
                            prop_values = self.properties_tree.item(prop_item, "values")
                            if len(prop_values) >= 3 and prop_values[1] == prop_name:
                                contexts.append({
                                    'name': context_name,
                                    'value': prop_values[2],
                                    'item': prop_item,
                                    'type': 'conditional'
                                })
        
        return {
            'property': prop_name,
            'category': category,
            'contexts': contexts
        }

    def _update_enhanced_conditional_property_values(self, original_item, dialog_result, category):
        """Update property values trong cÃ¡c contexts Ä‘Æ°á»£c chá»n"""
        prop_name = dialog_result['name']
        values_by_context = dialog_result['values_by_context']
        selected_contexts = dialog_result.get('selected_contexts', list(values_by_context.keys()))
        
        # Update values trong tá»«ng context Ä‘Æ°á»£c chá»n
        for parent in self.properties_tree.get_children():
            parent_values = self.properties_tree.item(parent, "values")
            if parent_values[0] == category:
                # Update trong conditional contexts
                for context_parent in self.properties_tree.get_children(parent):
                    context_values = self.properties_tree.item(context_parent, "values")
                    if len(context_values) >= 2 and context_values[1] in selected_contexts:
                        # Update properties trong context nÃ y
                        for prop_item in self.properties_tree.get_children(context_parent):
                            prop_values = self.properties_tree.item(prop_item, "values")
                            if len(prop_values) >= 3 and prop_values[1] == prop_name:
                                context_name = context_values[1]
                                if context_name in values_by_context:
                                    new_value = values_by_context[context_name]
                                    self.properties_tree.item(
                                        prop_item, values=(category, prop_name, new_value)
                                    )
                
                # Update flat properties náº¿u cÃ³
                for child in self.properties_tree.get_children(parent):
                    child_values = self.properties_tree.item(child, "values")
                    if len(child_values) >= 3 and child_values[1] == prop_name:
                        # Náº¿u context 'default' Ä‘Æ°á»£c chá»n, update flat property
                        if 'default' in selected_contexts and 'default' in values_by_context:
                            new_value = values_by_context['default']
                            self.properties_tree.item(
                                child, values=(category, prop_name, new_value)
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
        """
        Extract properties from the table.
        Returns v2 conditional-aware structure:
        {
          "LMKD": {"_flat": {...}, "_conditional": [{condition, if_props, else_props}, ...]},
          "Chimera": { ... }
        }
        """
        properties = {
            "LMKD": {"_flat": {}, "_conditional": []},
            "Chimera": {"_flat": {}, "_conditional": []}
        }

        for cat_item in self.properties_tree.get_children():
            cat_values = self.properties_tree.item(cat_item, "values")
            category = cat_values[0] if cat_values else None
            if category not in properties:
                continue

            # Rebuild the conditional block list from tree structure ---
            # We rebuild from original_properties to keep condition strings intact,
            # then patch in the values the user edited in the tree.
            orig_conditionals = self.original_properties.get(category, {}).get('_conditional', [])
            import copy
            rebuilt_conditionals = copy.deepcopy(orig_conditionals)

            for child in self.properties_tree.get_children(cat_item):
                child_values = self.properties_tree.item(child, "values")
                child_tags = self.properties_tree.item(child, "tags")

                if "condition_group" in child_tags:
                    # This is a conditional group node; get block index from tag.
                    block_idx = None
                    for tag in child_tags:
                        if tag.startswith("block_") and not tag.endswith("_if") and not tag.endswith("_else"):
                            try:
                                block_idx = int(tag.split("_")[1])
                            except (IndexError, ValueError):
                                pass

                    if block_idx is None or block_idx >= len(rebuilt_conditionals):
                        continue

                    # Clear existing props for this block; they will be refilled from the tree.
                    rebuilt_conditionals[block_idx]['if_props'] = {}

                    for cond_child in self.properties_tree.get_children(child):
                        cc_values = self.properties_tree.item(cond_child, "values")
                        cc_tags = self.properties_tree.item(cond_child, "tags")

                        if "else_group" in cc_tags:
                            # else sub-group
                            rebuilt_conditionals[block_idx]['else_props'] = {}
                            for else_child in self.properties_tree.get_children(cond_child):
                                ec_v = self.properties_tree.item(else_child, "values")
                                if len(ec_v) >= 3 and ec_v[1] and ec_v[1] != '[else]':
                                    rebuilt_conditionals[block_idx]['else_props'][ec_v[1]] = ec_v[2]

                        elif "if_block" in cc_tags:
                            if len(cc_values) >= 3 and cc_values[1]:
                                rebuilt_conditionals[block_idx]['if_props'][cc_values[1]] = cc_values[2]

                elif not child_tags or "property" in child_tags:
                    # Flat property (direct child of category)
                    if len(child_values) >= 3 and child_values[1]:
                        properties[category]['_flat'][child_values[1]] = child_values[2]

            properties[category]['_conditional'] = rebuilt_conditionals

        return properties

    def _get_conditional_table_properties(self):
        """Extract properties tá»« table vá»›i conditional context information"""
        properties = {"LMKD": {}, "Chimera": {}}
        conditional_properties = {"LMKD": {}, "Chimera": {}}

        # Duyá»‡t qua táº¥t cáº£ items trong tree
        for item in self.properties_tree.get_children():
            self._extract_properties_from_item(item, properties, conditional_properties)

        return properties, conditional_properties

    def _extract_properties_from_item(self, item, properties, conditional_properties, parent_context=None):
        """Recursive helper Ä‘á»ƒ extract properties tá»« tree items"""
        values = self.properties_tree.item(item, "values")
        tags = self.properties_tree.item(item, "tags")
        
        # Náº¿u lÃ  property item (cÃ³ Ä‘á»§ 3 values vÃ  cÃ³ property name)
        if len(values) >= 3 and values[1]:
            category = values[0]
            prop_name = values[1]
            prop_value = values[2]
            
            # Check náº¿u lÃ  conditional property
            if "conditional_property" in tags:
                # XÃ¡c Ä‘á»‹nh conditional context tá»« parent
                context = self._get_conditional_context(item)
                if context:
                    if category not in conditional_properties:
                        conditional_properties[category] = {}
                    if prop_name not in conditional_properties[category]:
                        conditional_properties[category][prop_name] = {}
                    
                    conditional_properties[category][prop_name][context] = prop_value
            else:
                # Flat property
                if category in properties:
                    properties[category][prop_name] = prop_value
        
        # Recursively process children
        for child in self.properties_tree.get_children(item):
            self._extract_properties_from_item(child, properties, conditional_properties, item)

    def _get_conditional_context(self, item):
        """Get conditional context cho má»™t property item"""
        # Get parent chain Ä‘á»ƒ xÃ¡c Ä‘á»‹nh context
        parent = self.properties_tree.parent(item)
        if parent:
            parent_values = self.properties_tree.item(parent, "values")
            if len(parent_values) >= 2 and parent_values[1]:
                context_text = parent_values[1]
                if context_text.startswith('[') and context_text.endswith(']'):
                    return context_text[1:-1]  # Remove brackets
                elif context_text == '[else]':
                    return 'else'
        return 'default'

    # ============================================================================
    # CONDITIONAL STRUCTURE DISPLAY FUNCTIONS (NEW)
    # ============================================================================

    def _load_conditional_properties_for_display(self, file_path):
        """Load properties vá»›i conditional context information cho GUI display"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            from core.file_operations import analyze_conditional_structure
            conditional_analysis = analyze_conditional_structure(file_content)
            
            # Structure data cho GUI display
            display_data = {}
            
            for section_name, section_data in conditional_analysis.items():
                display_data[section_name] = {
                    'conditional_blocks': [],
                    'flat_properties': {}  # For backward compatibility
                }
                
                # Process conditional blocks
                for block in section_data['blocks']:
                    block_info = {
                        'condition': block['condition'],
                        'properties': {},
                        'else_properties': {}
                    }
                    
                    # Add properties from if block
                    for prop in block['properties']:
                        block_info['properties'][prop['key']] = prop['value']
                        display_data[section_name]['flat_properties'][prop['key']] = prop['value']
                    
                    # Add properties from else block
                    if block['else_properties']:
                        for prop in block['else_properties']:
                            block_info['else_properties'][prop['key']] = prop['value']
                            # Note: Trong flat view, else value sáº½ override if value
                            display_data[section_name]['flat_properties'][prop['key']] = prop['value']
                    
                    display_data[section_name]['conditional_blocks'].append(block_info)
            
            return display_data
            
        except Exception as e:
            self.log_callback(f"[ERROR] Failed to load conditional properties: {str(e)}")
            return None

    def _populate_properties_table_conditional(self, properties_data, file_path=None):
        """Populate the properties table vá»›i conditional structure display - ENHANCED"""
        # Clear existing items
        for item in self.properties_tree.get_children():
            self.properties_tree.delete(item)

        # Add LMKD properties (giá»¯ nguyÃªn Ä‘á»ƒ backward compatibility)
        if "LMKD" in properties_data and properties_data["LMKD"]:
            lmkd_parent = self.properties_tree.insert(
                "", "end", text="LMKD", values=("LMKD", "", ""), tags=("category",)
            )
            for prop, value in properties_data["LMKD"].items():
                self.properties_tree.insert(
                    lmkd_parent, "end", values=("LMKD", prop, value), tags=("property",)
                )

        # Add Chimera properties vá»›i ENHANCED conditional structure display
        if "Chimera" in properties_data and properties_data["Chimera"]:
            if file_path:
                # Try to load conditional structure for detailed display
                conditional_data = self._load_conditional_properties_for_display(file_path)
                if conditional_data and "Chimera" in conditional_data:
                    self._populate_enhanced_conditional_chimera_section(conditional_data["Chimera"])
                else:
                    # Fallback to flat display
                    self._populate_flat_chimera_section(properties_data["Chimera"])
            else:
                # Fallback to flat display
                self._populate_flat_chimera_section(properties_data["Chimera"])

        # Expand all nodes
        for item in self.properties_tree.get_children():
            self.properties_tree.item(item, open=True)

    def _populate_enhanced_conditional_chimera_section(self, conditional_data):
        """Populate Chimera section vá»›i ENHANCED conditional structure display"""
        chimera_parent = self.properties_tree.insert(
            "", "end", text="Chimera", values=("Chimera", "", ""), tags=("category",)
        )
        
        # Add conditional blocks vá»›i ENHANCED display
        for i, block in enumerate(conditional_data['conditional_blocks']):
            # Create ENHANCED condition header vá»›i context information
            condition_text = block['condition']
            condition_display = f"[{condition_text}]" if not condition_text.startswith('else') else "[else]"
            
            condition_parent = self.properties_tree.insert(
                chimera_parent, "end", 
                text=condition_display,
                values=("Chimera", condition_display, f"Conditional Context {i+1}"),
                tags=("condition", "conditional_context")
            )
            
            # Add properties from if block vá»›i context awareness
            for prop in block['properties']:
                prop_key = prop['key']
                prop_value = prop['value']
                prop_line = prop.get('line_number', 'N/A')
                
                display_text = f"{prop_key} = {prop_value}"
                self.properties_tree.insert(
                    condition_parent, "end",
                    text=display_text,
                    values=("Chimera", prop_key, prop_value),
                    tags=("conditional_property", "if_block", f"context_{i}_if")
                )
            
            # Add properties from else block if exists vá»›i context awareness
            if block['else_properties']:
                else_parent = self.properties_tree.insert(
                    chimera_parent, "end",
                    text="[else]",
                    values=("Chimera", "[else]", "Else Context"),
                    tags=("condition", "else_block", "conditional_context")
                )
                
                for prop in block['else_properties']:
                    prop_key = prop['key']
                    prop_value = prop['value']
                    prop_line = prop.get('line_number', 'N/A')
                    
                    display_text = f"{prop_key} = {prop_value}"
                    self.properties_tree.insert(
                        else_parent, "end",
                        text=display_text,
                        values=("Chimera", prop_key, prop_value),
                        tags=("conditional_property", "else_block", f"context_{i}_else")
                    )

        # Add info about conditional structure for user awareness
        info_parent = self.properties_tree.insert(
            chimera_parent, "end",
            text="Conditional Structure Info",
            values=("Chimera", "Info", "Click to see all contexts"),
            tags=("info", "conditional_info")
        )

    def _populate_conditional_chimera_section(self, conditional_data):
        """Populate Chimera section vá»›i conditional structure"""
        chimera_parent = self.properties_tree.insert(
            "", "end", text="Chimera", values=("Chimera", "", ""), tags=("category",)
        )
        
        # Add conditional blocks
        for i, block in enumerate(conditional_data['conditional_blocks']):
            # Create condition header
            condition_text = block['condition']
            if condition_text.startswith('ifneq') or condition_text.startswith('ifdef') or condition_text.startswith('ifndef'):
                condition_display = f"[{condition_text}]"
            else:
                condition_display = f"[{condition_text}]"
                
            condition_parent = self.properties_tree.insert(
                chimera_parent, "end", 
                text=condition_display,
                values=("Chimera", condition_display, ""),
                tags=("condition",)
            )
            
            # Add properties from if block
            for prop_key, prop_value in block['properties'].items():
                display_value = prop_value
                self.properties_tree.insert(
                    condition_parent, "end",
                    values=("Chimera", prop_key, display_value),
                    tags=("conditional_property", "if_block")
                )
            
            # Add properties from else block if exists
            if block['else_properties']:
                else_parent = self.properties_tree.insert(
                    chimera_parent, "end",
                    text="[else]",
                    values=("Chimera", "[else]", ""),
                    tags=("condition", "else_block")
                )
                
                for prop_key, prop_value in block['else_properties'].items():
                    display_value = prop_value
                    self.properties_tree.insert(
                        else_parent, "end",
                        values=("Chimera", prop_key, display_value),
                        tags=("conditional_property", "else_block")
                    )

    def _populate_flat_chimera_section(self, properties):
        """Populate Chimera section theo cÃ¡ch flat (backward compatibility)"""
        chimera_parent = self.properties_tree.insert(
            "", "end", text="Chimera", values=("Chimera", "", ""), tags=("category",)
        )
        for prop, value in properties.items():
            self.properties_tree.insert(
                chimera_parent, "end", values=("Chimera", prop, value), tags=("property",)
            )
