"""
Comparison Dialog for displaying property differences between BENI, FLUMEN, and REL
Allows user to select which path's properties to use
"""

import tkinter as tk
from tkinter import ttk, messagebox


class ComparisonDialog:
    """Dialog for comparing properties from multiple paths and selecting one"""

    def __init__(self, parent, comparison_data):
        self.parent = parent
        self.comparison_data = comparison_data
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Property Comparison - Select Source")
        self.dialog.geometry("1200x600")
        self.dialog.resizable(True, True)
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog on parent
        self.center_dialog()
        
        # Create UI
        self.create_content()
        
        # Wait for dialog to close
        self.dialog.wait_window()

    def center_dialog(self):
        """Center dialog on parent window"""
        self.dialog.update_idletasks()
        
        # Get parent window position and size
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # Get dialog size
        dialog_width = self.dialog.winfo_reqwidth()
        dialog_height = self.dialog.winfo_reqheight()
        
        # Calculate center position
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        self.dialog.geometry(f"+{x}+{y}")

    def create_content(self):
        """Create dialog content with comparison table"""
        # Main frame
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="Properties differ between paths. Select which path's properties to use:",
            font=("TkDefaultFont", 10, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        # Create comparison table
        self.create_comparison_table(main_frame)
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill="x", pady=(10, 0))
        
        # Get available paths
        available_paths = list(self.comparison_data.keys())
        
        # Create selection buttons
        for path in available_paths:
            btn = ttk.Button(
                buttons_frame,
                text=f"Use {path} Properties",
                command=lambda p=path: self.select_path(p)
            )
            btn.pack(side="left", padx=5)
        
        # Cancel button
        ttk.Button(
            buttons_frame,
            text="Cancel",
            command=self.cancel
        ).pack(side="right", padx=5)

    def create_comparison_table(self, parent):
        """Create table showing property differences"""
        # Table frame
        table_frame = ttk.LabelFrame(parent, text="Property Comparison", padding=5)
        table_frame.pack(fill="both", expand=True)
        
        # Create treeview
        available_paths = list(self.comparison_data.keys())
        columns = ["Category", "Property"] + available_paths
        
        self.comparison_tree = ttk.Treeview(
            table_frame, columns=columns, show="tree headings", height=20
        )
        
        # Configure columns
        self.comparison_tree.heading("#0", text="", anchor="w")
        self.comparison_tree.column("#0", width=0, stretch=False)
        
        self.comparison_tree.heading("Category", text="Category")
        self.comparison_tree.column("Category", width=100, anchor="w")
        
        self.comparison_tree.heading("Property", text="Property")
        self.comparison_tree.column("Property", width=300, anchor="w")
        
        # Dynamic columns for each path
        for path in available_paths:
            self.comparison_tree.heading(path, text=f"{path} Value")
            self.comparison_tree.column(path, width=200, anchor="w")
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.comparison_tree.yview
        )
        h_scrollbar = ttk.Scrollbar(
            table_frame, orient="horizontal", command=self.comparison_tree.xview
        )
        self.comparison_tree.configure(
            yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set
        )
        
        # Pack components
        self.comparison_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Configure grid weights
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Populate comparison data
        self.populate_comparison_table(available_paths)

    def populate_comparison_table(self, paths):
        """Populate the comparison table with property data"""
        # Clear existing items
        for item in self.comparison_tree.get_children():
            self.comparison_tree.delete(item)
        
        # Collect all unique properties across all paths
        all_properties = {"LMKD": set(), "Chimera": set()}
        
        for path in paths:
            path_data = self.comparison_data[path]
            if "LMKD" in path_data:
                all_properties["LMKD"].update(path_data["LMKD"].keys())
            if "Chimera" in path_data:
                all_properties["Chimera"].update(path_data["Chimera"].keys())
        
        # Add LMKD properties
        if all_properties["LMKD"]:
            lmkd_parent = self.comparison_tree.insert(
                "", "end", text="LMKD", values=["LMKD", ""] + [""] * len(paths)
            )
            
            for prop in sorted(all_properties["LMKD"]):
                values = ["LMKD", prop]
                
                # Get value from each path
                for path in paths:
                    path_data = self.comparison_data[path]
                    lmkd_data = path_data.get("LMKD", {})
                    value = lmkd_data.get(prop, "<missing>")
                    values.append(value)
                
                # Check if values differ (for highlighting)
                path_values = values[2:]  # Skip category and property columns
                all_same = len(set(v for v in path_values if v != "<missing>")) <= 1
                
                item = self.comparison_tree.insert(lmkd_parent, "end", values=values)
                
                # Highlight different values
                if not all_same:
                    self.comparison_tree.set(item, "Category", "LMKD")
        
        # Add Chimera properties
        if all_properties["Chimera"]:
            chimera_parent = self.comparison_tree.insert(
                "", "end", text="Chimera", values=["Chimera", ""] + [""] * len(paths)
            )
            
            for prop in sorted(all_properties["Chimera"]):
                values = ["Chimera", prop]
                
                # Get value from each path
                for path in paths:
                    path_data = self.comparison_data[path]
                    chimera_data = path_data.get("Chimera", {})
                    value = chimera_data.get(prop, "<missing>")
                    values.append(value)
                
                # Check if values differ (for highlighting)
                path_values = values[2:]  # Skip category and property columns
                all_same = len(set(v for v in path_values if v != "<missing>")) <= 1
                
                item = self.comparison_tree.insert(chimera_parent, "end", values=values)
                
                # Highlight different values
                if not all_same:
                    self.comparison_tree.set(item, "Category", "⚠️ Chimera")
        
        # Expand all nodes
        for item in self.comparison_tree.get_children():
            self.comparison_tree.item(item, open=True)

    def select_path(self, selected_path):
        """User selected a path - return its properties"""
        try:
            # Get properties from selected path
            selected_properties = self.comparison_data[selected_path].copy()
            
            # Add metadata for compatibility with existing code
            all_depot_paths = {}
            for path, data in self.comparison_data.items():
                if "_metadata" in data and "depot_paths" in data["_metadata"]:
                    all_depot_paths.update(data["_metadata"]["depot_paths"])
            
            selected_properties["_metadata"] = {
                "depot_paths": all_depot_paths,
                "selected_source": selected_path,
                "original_properties": selected_properties.copy()
            }
            
            # Set result
            self.result = (selected_path, selected_properties)
            
            # Close dialog
            self.dialog.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to select properties: {str(e)}")

    def cancel(self):
        """Cancel dialog"""
        self.result = None
        self.dialog.destroy()