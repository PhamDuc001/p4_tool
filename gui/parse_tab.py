"""
Parse tab implementation
Handles the parse mode UI for workspace parsing and library size calculation
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from processes.parse_process import (
    parse_multiple_workspaces, 
    refresh_adb_devices,
    connect_to_device,
    calculate_library_sizes
)


class ExportDialog:
    """Dialog for displaying exported library list"""

    def __init__(self, parent, library_list):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Export Library List")
        self.dialog.geometry("600x500")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.geometry(
            "+%d+%d" % (parent.winfo_rootx() + 100, parent.winfo_rooty() + 50)
        )

        # Main frame
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill="both", expand=True)

        # Title label
        title_label = ttk.Label(
            main_frame, 
            text=f"Library List ({len(library_list)} libraries)", 
            font=("TkDefaultFont", 10, "bold")
        )
        title_label.pack(pady=(0, 10))

        # Text widget with scrollbar
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill="both", expand=True)

        self.text_widget = tk.Text(
            text_frame,
            wrap="none",
            font=("Consolas", 9),
            bg="white",
            fg="black"
        )
        
        v_scrollbar = ttk.Scrollbar(
            text_frame, orient="vertical", command=self.text_widget.yview
        )
        h_scrollbar = ttk.Scrollbar(
            text_frame, orient="horizontal", command=self.text_widget.xview
        )
        
        self.text_widget.configure(
            yscrollcommand=v_scrollbar.set, 
            xscrollcommand=h_scrollbar.set
        )

        # Pack text widget and scrollbars
        self.text_widget.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")

        # Configure grid weights
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        # Insert library list
        library_text = "\n".join(library_list)
        self.text_widget.insert("1.0", library_text)
        self.text_widget.configure(state="normal")  # Keep editable for user convenience

        

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))

        # Select All button
        select_all_btn = ttk.Button(
            button_frame, text="Select All", command=self.select_all
        )
        select_all_btn.pack(side="left", padx=(0, 5))

        # Copy to Clipboard button
        copy_btn = ttk.Button(
            button_frame, text="Copy to Clipboard", command=self.copy_to_clipboard
        )
        copy_btn.pack(side="left", padx=5)

        # Close button
        close_btn = ttk.Button(
            button_frame, text="Close", command=self.dialog.destroy
        )
        close_btn.pack(side="right")

        # Bind Escape key to close
        self.dialog.bind("<Escape>", lambda e: self.dialog.destroy())

        # Focus on text widget
        self.text_widget.focus()

    def select_all(self):
        """Select all text in the widget"""
        self.text_widget.tag_add("sel", "1.0", "end-1c")
        self.text_widget.mark_set("insert", "1.0")
        self.text_widget.see("insert")

    def copy_to_clipboard(self):
        """Copy content to clipboard"""
        try:
            content = self.text_widget.get("1.0", "end-1c")
            self.dialog.clipboard_clear()
            self.dialog.clipboard_append(content)
            messagebox.showinfo("Success", "Library list copied to clipboard!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy to clipboard: {str(e)}")


class ParseTab:
    """Parse tab component - UI only"""

    def __init__(self, parent, gui_utils):
        self.parent = parent
        self.gui_utils = gui_utils
        
        # Create the parse frame
        self.frame = ttk.Frame(parent)
        
        # Parse mode data
        self.parse_results = {"BENI": [], "VINCE": [], "FLUMEN": []}
        
        # Library calculator data
        self.connected_devices = []
        self.selected_device = None
        self.library_sizes = {}  # {library_path: size_in_bytes}
        
        # Initialize components
        self.create_content()

    def create_content(self):
        """Create content for parse mode"""
        # Parse input section
        parse_input_frame = ttk.LabelFrame(
            self.frame, text="Workspace Parsing to file device_common path", padding=10
        )
        parse_input_frame.pack(fill="x", pady=(0, 10))

        # Create workspace input rows
        self.workspace_entries = {}
        self.result_vars = {}

        categories = ["BENI", "VINCE", "FLUMEN"]

        for i, category in enumerate(categories):
            # Category label
            ttk.Label(parse_input_frame, text=f"{category}:", width=8).grid(
                column=0, row=i, sticky="w", pady=5, padx=(0, 5)
            )

            # Workspace input (150px width)
            workspace_entry = ttk.Entry(parse_input_frame, width=20)  # ~150px
            workspace_entry.grid(column=1, row=i, sticky="w", pady=5, padx=(0, 30))
            self.workspace_entries[category] = workspace_entry

            # Result display (250px width, read-only)
            result_var = tk.StringVar()
            result_entry = ttk.Entry(
                parse_input_frame, textvariable=result_var, width=35, state="readonly"
            )  # ~250px
            result_entry.grid(column=2, row=i, sticky="ew", pady=5)
            self.result_vars[category] = result_var

        # Configure grid weights for result columns
        parse_input_frame.columnconfigure(2, weight=1)

        # Parse control frame
        parse_control_frame = ttk.Frame(parse_input_frame)
        parse_control_frame.grid(
            column=0, row=3, columnspan=3, pady=(15, 0), sticky="ew"
        )

        # Progress bar for parsing
        self.progress = ttk.Progressbar(
            parse_control_frame, length=200, mode="determinate"
        )
        self.progress.pack(side="left", padx=(0, 10))

        # Parse button
        self.parse_button = ttk.Button(
            parse_control_frame, text="Parse", command=self.on_parse_workspaces
        )
        self.parse_button.pack(side="left")

        # Clear Parse button
        clear_parse_button = ttk.Button(
            parse_control_frame, text="Clear", command=self.on_clear_parse
        )
        clear_parse_button.pack(side="left", padx=(10, 0))

        # Library Size section
        self.create_library_size_section()

        # Parse log output frame
        parse_log_frame = ttk.LabelFrame(self.frame, text="Parse Log", padding=5)
        parse_log_frame.pack(fill="x", pady=(10, 0))

        # Create text widget with scrollbar for parse log
        self.log_text = self.gui_utils.create_text_with_scrollbar(parse_log_frame, height=8)

        # Create callbacks
        self.log_callback = self.gui_utils.create_log_callback(self.log_text)
        self.progress_callback = self.gui_utils.create_progress_callback(self.progress)

    def create_library_size_section(self):
        """Create Library Size Calculation section"""
        library_frame = ttk.LabelFrame(
            self.frame, text="Library Size Calculation", padding=10
        )
        library_frame.pack(fill="both", expand=True, pady=(10, 0))

        # Device connection frame
        device_frame = ttk.Frame(library_frame)
        device_frame.pack(fill="x", pady=(0, 10))

        # Refresh devices button
        self.refresh_button = ttk.Button(
            device_frame, text="Refresh", command=self.on_refresh_devices
        )
        self.refresh_button.pack(side="left", padx=(0, 10))

        # Device selection combobox
        ttk.Label(device_frame, text="Device:").pack(side="left", padx=(0, 5))
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(
            device_frame, textvariable=self.device_var, width=30, state="readonly"
        )
        self.device_combo.pack(side="left", padx=(0, 10))

        # Connect button
        self.connect_button = ttk.Button(
            device_frame, text="Connect", command=self.on_connect_device
        )
        self.connect_button.pack(side="left")

        # Connection status label
        self.connection_status_var = tk.StringVar(value="Not connected")
        self.connection_status_label = ttk.Label(
            device_frame, textvariable=self.connection_status_var, foreground="red"
        )
        self.connection_status_label.pack(side="left", padx=(10, 0))

        # Library input frame
        input_frame = ttk.Frame(library_frame)
        input_frame.pack(fill="x", pady=(10, 0))

        ttk.Label(input_frame, text="Libraries to check (one per line):").pack(anchor="w")

        # Create text widget with scrollbar for library input
        text_frame = ttk.Frame(input_frame)
        text_frame.pack(fill="x", pady=5)

        self.library_input = tk.Text(
            text_frame,
            height=8,
            wrap="none",
            font=("Consolas", 9),
        )
        input_scrollbar = ttk.Scrollbar(
            text_frame, orient="vertical", command=self.library_input.yview
        )
        self.library_input.configure(yscrollcommand=input_scrollbar.set)

        self.library_input.pack(side="left", fill="both", expand=True)
        input_scrollbar.pack(side="right", fill="y")

        # Calculator button
        calc_button_frame = ttk.Frame(library_frame)
        calc_button_frame.pack(fill="x", pady=(5, 10))

        self.calculate_button = ttk.Button(
            calc_button_frame, text="Calculate", command=self.on_calculate_sizes,
            state="disabled"
        )
        self.calculate_button.pack(side="left")

        # Clear libraries button
        clear_lib_button = ttk.Button(
            calc_button_frame, text="Clear Libraries", command=self.on_clear_libraries
        )
        clear_lib_button.pack(side="left", padx=(10, 0))

        # Progress bar for calculation
        self.calc_progress = ttk.Progressbar(
            calc_button_frame, length=200, mode="determinate"
        )
        self.calc_progress.pack(side="left", padx=(20, 0))

        # Results table frame
        table_frame = ttk.Frame(library_frame)
        table_frame.pack(fill="both", expand=True, pady=(10, 0))

        # Create treeview for results
        columns = ("Library", "Size (KB)", "Size (MB)")
        self.results_tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", height=10
        )

        # Configure columns
        self.results_tree.heading("Library", text="Library Path")
        self.results_tree.column("Library", width=400, anchor="w")

        self.results_tree.heading("Size (KB)", text="Size (KB)")
        self.results_tree.column("Size (KB)", width=100, anchor="e")

        self.results_tree.heading("Size (MB)", text="Size (MB)")
        self.results_tree.column("Size (MB)", width=120, anchor="e")

        # Scrollbars for results table
        results_v_scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.results_tree.yview
        )
        results_h_scrollbar = ttk.Scrollbar(
            table_frame, orient="horizontal", command=self.results_tree.xview
        )
        self.results_tree.configure(
            yscrollcommand=results_v_scrollbar.set, xscrollcommand=results_h_scrollbar.set
        )

        # Pack results table
        self.results_tree.grid(row=0, column=0, sticky="nsew")
        results_v_scrollbar.grid(row=0, column=1, sticky="ns")
        results_h_scrollbar.grid(row=1, column=0, sticky="ew")

        # Configure grid weights
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # Table control buttons
        table_buttons_frame = ttk.Frame(library_frame)
        table_buttons_frame.pack(fill="x", pady=5)

        # Left side buttons
        ttk.Button(
            table_buttons_frame, text="Delete Selected", command=self.on_delete_library
        ).pack(side="left", padx=5)

        ttk.Button(
            table_buttons_frame, text="Clear Results", command=self.on_clear_results
        ).pack(side="left", padx=5)

        # Export button
        ttk.Button(
            table_buttons_frame, text="Export", command=self.on_export_library_list
        ).pack(side="left", padx=5)

        # Bind events
        self.results_tree.bind("<Double-1>", lambda e: self.on_delete_library())
        self.results_tree.bind("<Delete>", lambda e: self.on_delete_library())

    def show(self):
        """Show the parse tab"""
        self.frame.pack(fill="both", expand=True)

    def hide(self):
        """Hide the parse tab"""
        self.frame.pack_forget()

    def clear_all(self):
        """Clear all parse fields and results"""
        for category in self.workspace_entries:
            self.workspace_entries[category].delete(0, tk.END)
            self.result_vars[category].set("")

        # Clear parse log
        self.gui_utils.clear_text_widget(self.log_text)

        # Reset progress bar
        self.gui_utils.reset_progress(self.progress)

        # Reset parse results
        self.parse_results = {"BENI": [], "VINCE": [], "FLUMEN": []}

        # Clear library calculator
        self.library_input.delete("1.0", tk.END)
        self.on_clear_results()
        self.connection_status.set("Not connected")
        self.selected_device = None

        self.log_callback("[INFO] All parse fields and logs cleared.")
        self.gui_utils.update_status(
            "Mode: Parse - Enter workspace names to find device_common.mk files"
        )

    def on_clear_parse(self):
        """Clear only parse fields and results"""
        for category in self.workspace_entries:
            self.workspace_entries[category].delete(0, tk.END)
            self.result_vars[category].set("")

        # Clear parse log
        self.gui_utils.clear_text_widget(self.log_text)

        # Reset progress bar
        self.gui_utils.reset_progress(self.progress)

        # Reset parse results
        self.parse_results = {"BENI": [], "VINCE": [], "FLUMEN": []}

        self.log_callback("[INFO] Parse fields cleared.")

    # ============================================================================
    # EXPORT FUNCTIONALITY
    # ============================================================================

    def on_export_library_list(self):
        """Export library list from results table"""
        # Get current libraries from table (excluding TOTAL row and deleted items)
        library_list = []
        
        for item in self.results_tree.get_children():
            values = self.results_tree.item(item, "values")
            if len(values) >= 3 and values[0] != "TOTAL":
                library_path = values[0]
                size_mb_str = values[1]  # Lấy size MB từ cột thứ 3
                # Làm tròn size MB
                try:
                    size_mb = round(float(size_mb_str))
                    formatted_line = f"{size_mb} {library_path}"
                except (ValueError, TypeError):
                    # Nếu không parse được size, chỉ hiển thị path
                    formatted_line = library_path
                library_list.append(formatted_line)
        
        if not library_list:
            messagebox.showwarning(
                "No Libraries", 
                "No libraries found in the results table to export.\n"
                "Please calculate library sizes first."
            )
            return
        
        # Show export dialog
        try:
            ExportDialog(self.gui_utils.root, library_list)
            self.log_callback(f"[EXPORT] Exported {len(library_list)} libraries to export dialog")
        except Exception as e:
            self.log_callback(f"[ERROR] Failed to export library list: {str(e)}")
            messagebox.showerror("Export Error", f"Failed to export library list: {str(e)}")

    # ============================================================================
    # LIBRARY SIZE CALCULATOR UI HANDLERS
    # ============================================================================

    def on_refresh_devices(self):
        """Handle refresh devices button click"""
        try:
            self.log_callback("[ADB] Refreshing device list...")
            devices = refresh_adb_devices(self.log_callback)
            
            self.connected_devices = devices
            self.device_combo['values'] = devices
            
            if devices:
                self.device_combo.set(devices[0])  # Select first device by default
                self.log_callback(f"[ADB] Found {len(devices)} connected device(s): {', '.join(devices)}")
            else:
                self.device_combo.set("")
                self.log_callback("[ADB] No devices found")
                messagebox.showinfo("No Devices", "No ADB devices found. Please connect a device and try again.")

        except Exception as e:
            self.log_callback(f"[ERROR] Error refreshing devices: {str(e)}")
            messagebox.showerror("Error", f"Error refreshing devices: {str(e)}")

    def on_connect_device(self):
        """Handle connect device button click"""
        selected = self.device_var.get().strip()
        if not selected:
            messagebox.showwarning("No Device Selected", "Please select a device to connect.")
            return

        try:
            self.log_callback(f"[ADB] Connecting to device: {selected}")
            
            success = connect_to_device(selected, self.log_callback)
            
            if success:
                self.selected_device = selected
                self.connection_status_var.set(f"Connected: {selected}")
                self.connection_status_label.config(foreground="green")
                self.calculate_button.configure(state="normal")
                self.log_callback(f"[ADB] Successfully connected to {selected}")
            else:
                messagebox.showerror("Connection Failed", f"Failed to connect to device: {selected}")

        except Exception as e:
            self.log_callback(f"[ERROR] Error connecting to device: {str(e)}")
            messagebox.showerror("Error", f"Error connecting to device: {str(e)}")

    def on_calculate_sizes(self):
        """Handle calculate sizes button click"""
        if not self.selected_device:
            messagebox.showwarning("No Device", "Please connect to a device first.")
            return

        # Get libraries from input
        library_text = self.library_input.get("1.0", tk.END).strip()
        if not library_text:
            messagebox.showwarning("No Libraries", "Please enter library paths to check.")
            return

        libraries = [lib.strip() for lib in library_text.split('\n') if lib.strip()]
        if not libraries:
            messagebox.showwarning("No Libraries", "Please enter valid library paths.")
            return

        self._calculate_sizes_thread(libraries)

    def _calculate_sizes_thread(self, libraries):
        """Calculate sizes in separate thread"""
        # Clear previous results
        self.on_clear_results()
        
        # Reset progress
        self.calc_progress["value"] = 0
        
        # Disable button during processing
        self.calculate_button.configure(state="disabled")

        def calc_thread():
            try:
                total_libraries = len(libraries)
                self.gui_utils.update_status(f"Calculating sizes for {total_libraries} libraries...")
                
                # Use logic from parse_process
                results = calculate_library_sizes(
                    self.selected_device, 
                    libraries, 
                    self.log_callback,
                    lambda progress: self.gui_utils.root.after(0, lambda: self.calc_progress.configure(value=progress))
                )

                # Update UI with results
                self.gui_utils.root.after(0, lambda: self._update_results_table(results))
                self.gui_utils.root.after(0, lambda: self.gui_utils.update_status("Size calculation completed"))

            except Exception as e:
                self.gui_utils.root.after(0, lambda: self.log_callback(f"[ERROR] Calculation failed: {str(e)}"))
                self.gui_utils.root.after(0, lambda: messagebox.showerror("Calculation Error", str(e)))
            finally:
                # Re-enable button
                self.gui_utils.root.after(0, lambda: self.calculate_button.configure(state="normal"))

        # Start calculation in separate thread
        thread = threading.Thread(target=calc_thread, daemon=True)
        thread.start()

    def _update_results_table(self, results):
        """Update results table with calculated sizes"""
        # Clear existing results
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

        # Store results
        self.library_sizes = results.copy()

        total_size = 0
        
        # Add individual libraries
        for library, size_bytes in results.items():
            size_kb = size_bytes / 1024
            size_mb = size_kb / 1024
            self.results_tree.insert(
                "", "end",
                values=(library, f"{size_kb:.1f}", f"{size_mb:.2f}")
            )
            total_size += size_bytes

        # Add total row
        if results:
            total_kb = total_size / 1024
            total_mb = total_kb / 1024
            total_item = self.results_tree.insert(
                "", "end",
                values=("TOTAL", f"{total_kb:.1f}", f"{total_mb:.2f}"),
                tags=("total",)
            )
            # Configure total row style
            self.results_tree.tag_configure("total", background="#e6f3ff", font=("TkDefaultFont", 9, "bold"))

        self.log_callback(f"[CALC] Calculation completed. Total size: {total_kb:.1f} KB ({total_mb:.2f} MB)")

    def on_delete_library(self):
        """Delete selected library from results"""
        selected = self.results_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a library to delete.")
            return

        for item in selected:
            values = self.results_tree.item(item, "values")
            if len(values) >= 1 and values[0] != "TOTAL":
                library_path = values[0]
                
                # Confirm deletion
                if messagebox.askyesno("Confirm Delete", f"Delete library:\n{library_path}?"):
                    # Remove from stored results
                    if library_path in self.library_sizes:
                        del self.library_sizes[library_path]
                    
                    # Remove from table
                    self.results_tree.delete(item)
                    
                    self.log_callback(f"[DELETE] Removed library: {library_path}")

        # Recalculate total
        self._recalculate_total()

    def _recalculate_total(self):
        """Recalculate total size after deletion"""
        # Find and remove existing total row
        for item in self.results_tree.get_children():
            values = self.results_tree.item(item, "values")
            if len(values) >= 1 and values[0] == "TOTAL":
                self.results_tree.delete(item)
                break

        # Calculate new total
        total_size = 0
        for item in self.results_tree.get_children():
            values = self.results_tree.item(item, "values")
            if len(values) >= 3 and values[0] != "TOTAL":
                try:
                    size_kb = float(values[1])
                    size_bytes = size_kb * 1024
                    total_size += size_bytes
                except (ValueError, IndexError):
                    pass

        # Add new total row
        if total_size > 0:
            total_kb = total_size / 1024
            total_mb = total_kb / 1024
            self.results_tree.insert(
                "", "end",
                values=("TOTAL", f"{total_kb:.1f}", f"{total_mb:.2f}"),
                tags=("total",)
            )
            self.results_tree.tag_configure("total", background="#e6f3ff", font=("TkDefaultFont", 9, "bold"))

    def on_clear_libraries(self):
        """Clear library input text"""
        self.library_input.delete("1.0", tk.END)
        self.log_callback("[INFO] Library input cleared.")

    def on_clear_results(self):
        """Clear results table"""
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        self.library_sizes = {}
        self.calc_progress["value"] = 0

    # ============================================================================
    # WORKSPACE PARSING UI HANDLERS
    # ============================================================================

    def on_parse_workspaces(self):
        """Handle parse workspaces button click"""
        # Get workspace names from inputs
        workspace_dict = {}
        for category, entry in self.workspace_entries.items():
            workspace_name = entry.get().strip()
            workspace_dict[category] = workspace_name

        # Check if at least one workspace is provided
        if not any(ws for ws in workspace_dict.values()):
            messagebox.showwarning(
                "No Workspaces", "Please enter at least one workspace name to parse."
            )
            return

        self._run_parse_workspaces(workspace_dict)

    def _run_parse_workspaces(self, workspace_dict):
        """Run workspace parsing in separate thread"""
        # Clear parse log and reset progress
        self.gui_utils.clear_text_widget(self.log_text)
        self.gui_utils.reset_progress(self.progress)

        # Disable parse button during processing
        self.parse_button.configure(state="disabled")

        def parse_thread():
            try:
                self.gui_utils.update_status(
                    "Processing: Parsing workspaces for device_common.mk files..."
                )

                # Run the parsing process
                results = parse_multiple_workspaces(
                    workspace_dict,
                    self.log_callback,
                    self.progress_callback,
                )

                # Update UI with results in main thread
                self.gui_utils.root.after(0, lambda: self._update_parse_results(results))

            except Exception as e:
                self.gui_utils.root.after(
                    0,
                    lambda: self.log_callback(f"[ERROR] Parse failed: {str(e)}"),
                )
                self.gui_utils.root.after(0, lambda: self.gui_utils.error_callback("Parse Error", str(e)))
            finally:
                # Re-enable parse button when done
                self.gui_utils.root.after(0, lambda: self.parse_button.configure(state="normal"))
                self.gui_utils.root.after(0, lambda: self.gui_utils.update_status("Parse completed"))

        # Start parsing in separate thread
        thread = threading.Thread(target=parse_thread, daemon=True)
        thread.start()

    def _update_parse_results(self, results):
        """Update UI with parse results"""
        for category, paths in results.items():
            if paths:
                # Show only the first path in the result field (if multiple found)
                display_path = paths[0]

                # Check if this path is already displayed to avoid duplicates
                current_display = self.result_vars[category].get()
                if current_display != display_path:
                    self.result_vars[category].set(display_path)

                    # Update stored results
                    self.parse_results[category] = paths

                    self.log_callback(
                        f"[UPDATE] {category} result updated: {display_path}"
                    )

                    # If multiple paths found, log all of them
                    if len(paths) > 1:
                        self.log_callback(
                            f"[INFO] {category} has {len(paths)} paths, showing first one"
                        )
                        for i, path in enumerate(paths[1:], 2):
                            self.log_callback(f"[INFO]   Path {i}: {path}")
                else:
                    self.log_callback(
                        f"[SKIP] {category} path unchanged, no update needed"
                    )
            else:
                # Clear result if no paths found
                if self.result_vars[category].get():
                    self.result_vars[category].set("")
                    self.parse_results[category] = []
                    self.log_callback(
                        f"[UPDATE] {category} result cleared (no paths found)"
                    )