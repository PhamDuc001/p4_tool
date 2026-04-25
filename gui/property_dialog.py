"""
Property dialog component
Dialog for adding and editing properties in the tuning tab
Supports both flat and conditional property editing
"""

import tkinter as tk
from tkinter import ttk, messagebox


class PropertyDialog:
    """Dialog for adding/editing properties"""

    def __init__(self, parent, title, prop_name="", prop_value=""):
        self.result = None

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x200")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.geometry(
            "+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50)
        )

        # Property name
        ttk.Label(self.dialog, text="Property Name:").pack(pady=5)
        self.name_entry = ttk.Entry(self.dialog, width=50)
        self.name_entry.pack(pady=5)
        self.name_entry.insert(0, prop_name)

        # Property value
        ttk.Label(self.dialog, text="Property Value:").pack(pady=5)
        self.value_entry = ttk.Entry(self.dialog, width=50)
        self.value_entry.pack(pady=5)
        self.value_entry.insert(0, prop_value)

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=20)

        ttk.Button(button_frame, text="OK", command=self.ok_clicked).pack(
            side="left", padx=5
        )
        ttk.Button(button_frame, text="Cancel", command=self.cancel_clicked).pack(
            side="left", padx=5
        )

        # Focus on name entry
        self.name_entry.focus()

        # Bind Enter key
        self.dialog.bind("<Return>", lambda e: self.ok_clicked())
        self.dialog.bind("<Escape>", lambda e: self.cancel_clicked())

        # Wait for dialog to close
        self.dialog.wait_window()

    def ok_clicked(self):
        """Handle OK button click"""
        prop_name = self.name_entry.get().strip()
        prop_value = self.value_entry.get().strip()

        if not prop_name:
            messagebox.showerror("Invalid Input", "Property name cannot be empty.")
            return

        self.result = (prop_name, prop_value)
        self.dialog.destroy()

    def cancel_clicked(self):
        """Handle Cancel button click"""
        self.result = None
        self.dialog.destroy()


class ConditionalPropertyDialog:
    """Dialog for editing properties với conditional context awareness"""

    def __init__(self, parent, title, prop_name="", prop_values_by_context=None):
        """
        Initialize conditional property dialog
        
        Args:
            prop_values_by_context (dict): Format {
                "ifneq ($(filter usa%, $(PROJECT_REGION)), )": "value1",
                "else": "value2"
            }
        """
        self.result = None
        self.prop_name = prop_name
        self.prop_values_by_context = prop_values_by_context or {}

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x400")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.geometry(
            "+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50)
        )

        # Create main frame
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill="both", expand=True)

        # Property name (readonly)
        ttk.Label(main_frame, text="Property Name:").pack(anchor="w", pady=(0, 5))
        name_frame = ttk.Frame(main_frame)
        name_frame.pack(fill="x", pady=(0, 10))
        self.name_entry = ttk.Entry(name_frame, width=60)
        self.name_entry.pack(fill="x")
        self.name_entry.insert(0, prop_name)
        self.name_entry.config(state="readonly")

        # Conditional contexts notebook
        ttk.Label(main_frame, text="Conditional Contexts:").pack(anchor="w", pady=(10, 5))
        
        # Create notebook for multiple contexts
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True, pady=(0, 20))
        
        # Store value entries for each context
        self.context_entries = {}
        
        # Create tabs for each conditional context
        if prop_values_by_context:
            for context, value in prop_values_by_context.items():
                self._create_context_tab(context, value)
        else:
            # Single context (flat property)
            self._create_context_tab("Default", "")

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x")

        ttk.Button(button_frame, text="OK", command=self.ok_clicked).pack(
            side="right", padx=5
        )
        ttk.Button(button_frame, text="Cancel", command=self.cancel_clicked).pack(
            side="right", padx=5
        )

        # Bind Enter key
        self.dialog.bind("<Return>", lambda e: self.ok_clicked())
        self.dialog.bind("<Escape>", lambda e: self.cancel_clicked())

        # Wait for dialog to close
        self.dialog.wait_window()

    def _create_context_tab(self, context_name, value):
        """Create a tab for a conditional context"""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text=context_name[:30] + "..." if len(context_name) > 30 else context_name)
        
        # Value entry for this context
        ttk.Label(frame, text=f"Value for context:").pack(anchor="w", pady=(0, 5))
        value_entry = tk.Text(frame, height=3, width=60)
        value_entry.pack(fill="both", expand=True)
        value_entry.insert("1.0", value)
        
        # Store entry reference
        self.context_entries[context_name] = value_entry

    def ok_clicked(self):
        """Handle OK button click"""
        prop_name = self.name_entry.get().strip()
        
        if not prop_name:
            messagebox.showerror("Invalid Input", "Property name cannot be empty.")
            return

        # Collect values from all contexts
        updated_values = {}
        for context, entry in self.context_entries.items():
            value = entry.get("1.0", "end-1c").strip()
            if value:  # Only include non-empty values
                updated_values[context] = value

        self.result = {
            "name": prop_name,
            "values_by_context": updated_values
        }
        self.dialog.destroy()

    def cancel_clicked(self):
        """Handle Cancel button click"""
        self.result = None
        self.dialog.destroy()


class EnhancedConditionalPropertyDialog:
    """Enhanced dialog for editing properties với conditional context awareness và user guidance"""

    def __init__(self, parent, title, prop_name="", prop_values_by_context=None, original_context_info=None):
        """
        Initialize enhanced conditional property dialog
        
        Args:
            prop_values_by_context (dict): Format {
                "[ifneq ($(filter usa%, $(PROJECT_REGION)), )]": "1024,24,10,2550",
                "[else]": "1228,24,10,2550"
            }
            original_context_info (dict): Original context information for reference
        """
        self.result = None
        self.prop_name = prop_name
        self.prop_values_by_context = prop_values_by_context or {}
        self.original_context_info = original_context_info or {}

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("600x500")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.geometry(
            "+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50)
        )

        # Create main frame
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill="both", expand=True)

        # Property name (readonly) with enhanced display
        ttk.Label(main_frame, text="Property Name:", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))
        name_frame = ttk.Frame(main_frame)
        name_frame.pack(fill="x", pady=(0, 10))
        self.name_entry = ttk.Entry(name_frame, width=70, font=("Arial", 9))
        self.name_entry.pack(fill="x")
        self.name_entry.insert(0, prop_name)
        self.name_entry.config(state="readonly")

        # Warning/info message
        info_text = "This property has different values in different conditional contexts.\n" \
                   "Edit values in each context tab below. Empty values will not be updated."
        info_label = ttk.Label(main_frame, text=info_text, foreground="blue")
        info_label.pack(anchor="w", pady=(0, 10))

        # Conditional contexts notebook với enhanced styling
        ttk.Label(main_frame, text="Conditional Contexts:", font=("Arial", 10, "bold")).pack(anchor="w", pady=(10, 5))
        
        # Create notebook for multiple contexts
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True, pady=(0, 20))
        
        # Store value entries and context info for each context
        self.context_entries = {}
        self.context_checkbuttons = {}  # For selective updates
        self.context_vars = {}
        
        # Create tabs for each conditional context với enhanced display
        if prop_values_by_context:
            for context, value in prop_values_by_context.items():
                self._create_enhanced_context_tab(context, value)
        else:
            # Single context (flat property)
            self._create_enhanced_context_tab("Default", "")

        # Buttons with enhanced layout
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x")

        # Add "Select All" and "Clear All" buttons
        ttk.Button(button_frame, text="Select All", command=self.select_all_contexts).pack(
            side="left", padx=5
        )
        ttk.Button(button_frame, text="Clear All", command=self.clear_all_contexts).pack(
            side="left", padx=5
        )

        # Spacer
        ttk.Frame(button_frame).pack(side="left", expand=True)

        # OK/Cancel buttons
        ttk.Button(button_frame, text="OK", command=self.ok_clicked).pack(
            side="right", padx=5
        )
        ttk.Button(button_frame, text="Cancel", command=self.cancel_clicked).pack(
            side="right", padx=5
        )

        # Bind Enter key
        self.dialog.bind("<Return>", lambda e: self.ok_clicked())
        self.dialog.bind("<Escape>", lambda e: self.cancel_clicked())

        # Wait for dialog to close
        self.dialog.wait_window()

    def _create_enhanced_context_tab(self, context_name, value):
        """Create an enhanced tab for a conditional context với user guidance"""
        # Clean context name for display
        display_name = context_name
        if display_name.startswith('[') and display_name.endswith(']'):
            display_name = display_name[1:-1]
        
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text=display_name[:40] + "..." if len(display_name) > 40 else display_name)
        
        # Context info
        context_type = "Else Context" if "else" in context_name.lower() else "Conditional Context"
        ttk.Label(frame, text=f"{context_type}", font=("Arial", 9, "italic"), foreground="gray").pack(anchor="w", pady=(0, 5))
        
        # Checkbox để chọn context nào update
        var = tk.BooleanVar(value=True)  # Default checked
        self.context_vars[context_name] = var
        checkbutton = ttk.Checkbutton(frame, text="Update this context", variable=var)
        checkbutton.pack(anchor="w", pady=(0, 10))
        self.context_checkbuttons[context_name] = checkbutton
        
        # Value entry for this context với enhanced styling
        ttk.Label(frame, text="Property Value:").pack(anchor="w", pady=(0, 5))
        value_entry = tk.Text(frame, height=4, width=70, font=("Consolas", 9))
        value_entry.pack(fill="both", expand=True)
        value_entry.insert("1.0", value)
        
        # Add line numbers or context hint if needed
        if "else" in context_name.lower():
            hint_label = ttk.Label(frame, text="Else context - used when condition is false", foreground="orange")
            hint_label.pack(anchor="w", pady=(5, 0))
        
        # Store entry reference
        self.context_entries[context_name] = value_entry

    def select_all_contexts(self):
        """Select all contexts for update"""
        for var in self.context_vars.values():
            var.set(True)

    def clear_all_contexts(self):
        """Clear all contexts for update"""
        for var in self.context_vars.values():
            var.set(False)

    def ok_clicked(self):
        """Handle OK button click với enhanced validation"""
        prop_name = self.name_entry.get().strip()
        
        if not prop_name:
            messagebox.showerror("Invalid Input", "Property name cannot be empty.")
            return

        # Collect values from selected contexts only
        updated_values = {}
        for context, entry in self.context_entries.items():
            if self.context_vars[context].get():  # Only if context is selected
                value = entry.get("1.0", "end-1c").strip()
                # Only include non-empty values or explicitly cleared values
                updated_values[context] = value

        # Warn if no contexts selected
        if not updated_values:
            if not messagebox.askyesno("No Contexts Selected", 
                                     "No contexts are selected for update. This will not change any values.\n\nContinue anyway?"):
                return

        self.result = {
            "name": prop_name,
            "values_by_context": updated_values,
            "selected_contexts": [ctx for ctx, var in self.context_vars.items() if var.get()]
        }
        self.dialog.destroy()

    def cancel_clicked(self):
        """Handle Cancel button click"""
        self.result = None
        self.dialog.destroy()
