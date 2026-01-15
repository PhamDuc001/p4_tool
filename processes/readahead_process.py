"""
Readahead process implementation
Handles the readahead workflow for workspace-based operations with library processing
Enhanced to support mixed input (depot paths and workspaces)
Enhanced Samsung vendor path filtering with priority-based logic
NEW: Added library processing support for Resource=1 and Resource=2
"""

import os
import re
import subprocess
import tkinter as tk
from tkinter import simpledialog, messagebox
from P4 import P4, P4Exception
from core.p4_operations import (
    get_client_name, run_cmd, create_changelist_silent, 
    map_single_depot, sync_file_silent, checkout_file_silent,
    validate_device_common_mk_path, validate_depot_path,
    is_workspace_like, auto_resolve_missing_branches, find_device_common_mk_path,
    get_integration_source_depot_path
)
from processes.system_process import (
    get_rscmgr_reference_from_device_common as find_rscmgr_filename_from_device_common,
    find_samsung_vendor_path_from_workspace,
    add_rscmgr_reference_to_device_common,
    find_android_mk_from_samsung_path,
    check_rscmgr_in_android_mk,
    add_rscmgr_module_to_android_mk,
    construct_rscmgr_file_path,
    update_device_common_mk_rscmgr_reference,
    read_rscmgr_content,
    write_rscmgr_content,
    create_rscmgr_file
)
from config.p4_config import depot_to_local_path


def prompt_for_rscmgr_filename(log_callback=None):
    """
    Prompt user to input rscmgr filename when automatic detection fails
    
    Args:
        log_callback: Function to log messages
        
    Returns:
        str: User-provided rscmgr filename, or None if cancelled
    """
    if log_callback:
        log_callback("[PROMPT] Rscmgr filename not found automatically, prompting user...")
    
    # Create a simple dialog to get user input
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    root.attributes('-topmost', True)  # Bring dialog to front
    
    try:
        filename = simpledialog.askstring(
            "Rscmgr Filename Required",
            "Could not find rscmgr reference automatically.\n\n"
            "Please enter the rscmgr filename (e.g., rscmgr.rc or rscmgr_vince.rc):",
            initialvalue="rscmgr.rc",
            parent=root
        )
        
        if filename:
            filename = filename.strip()
            
            # Validate the filename format
            if not filename.endswith('.rc'):
                if log_callback:
                    log_callback(f"[ERROR] Invalid filename format: {filename} (must end with .rc)")
                messagebox.showerror(
                    "Invalid Filename",
                    f"Filename must end with '.rc'\nGot: {filename}"
                )
                return prompt_for_rscmgr_filename(log_callback)  # Retry
            
            # Validate filename pattern (rscmgr*.rc)
            if not re.match(r'^rscmgr.*\.rc$', filename):
                if log_callback:
                    log_callback(f"[ERROR] Invalid filename pattern: {filename} (should start with 'rscmgr')")
                messagebox.showerror(
                    "Invalid Filename", 
                    f"Filename should start with 'rscmgr' and end with '.rc'\nGot: {filename}"
                )
                return prompt_for_rscmgr_filename(log_callback)  # Retry
            
            if log_callback:
                log_callback(f"[OK] User provided rscmgr filename: {filename}")
            
            return filename
        else:
            if log_callback:
                log_callback("[CANCELLED] User cancelled rscmgr filename input")
            return None
            
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Failed to prompt for rscmgr filename: {str(e)}")
        messagebox.showerror("Error", f"Failed to get input: {str(e)}")
        return None
    finally:
        root.destroy()


def resolve_input_to_device_common_path(user_input, log_callback=None):
    """
    ENHANCED: Use parse_process.py approach for workspace resolution
    Resolve user input (depot path or workspace) to device_common.mk depot path
    Returns the resolved device_common.mk path
    """
    user_input = user_input.strip()
    
    if not user_input:
        return None
    
    # If it's a depot path
    if user_input.startswith("//"):
        if log_callback:
            log_callback(f"[INPUT] Detected depot path: {user_input}")
        
        # Validate path exists and is device_common.mk
        exists, is_device_common = validate_device_common_mk_path(user_input)
        
        if not exists:
            raise RuntimeError(f"Depot path does not exist: {user_input}")
        
        if not is_device_common:
            raise RuntimeError(f"Path must be a device_common.mk file: {user_input}")
        
        return user_input
    
    # If it's a workspace
    elif is_workspace_like(user_input):
        if log_callback:
            log_callback(f"[INPUT] Detected workspace: {user_input}")
        
        try:
            # Use enhanced workspace resolution like parse_process.py
            resolved_path, _ = find_device_common_mk_path(user_input, log_callback)
            if resolved_path:
                if log_callback:
                    log_callback(f"[OK] Resolved workspace to: {resolved_path}")
                return resolved_path
            else:
                raise RuntimeError(f"Could not resolve workspace to device_common.mk: {user_input}")
        except Exception as e:
            raise RuntimeError(f"Workspace resolution failed: {str(e)}")
    
    else:
        raise RuntimeError(f"Input must be either device_common.mk depot path (//depot/...) or workspace (TEMPLATE_*): {user_input}")


def find_rscmgr_file_path(workspace, rscmgr_filename, log_callback=None):
    samsung_path = find_samsung_vendor_path_from_workspace(workspace)
    if not samsung_path:
        if(log_callback):
            log_callback(f"[ERROR] Could not find Samsung vendor path for workspace: {workspace}")
        return None
    rscmgr_path = construct_rscmgr_file_path(samsung_path, rscmgr_filename)
    return rscmgr_path
    

def copy_rscmgr_content(source_path, target_path, log_callback=None):
    """
    Copy content from source rscmgr file to target rscmgr file
    """
    if log_callback:
        log_callback(f"[SYSTEM] Copying rscmgr content from VINCE to target...")
    
    try:
        source_local = depot_to_local_path(source_path)
        target_local = depot_to_local_path(target_path)
        
        # Read source content
        with open(source_local, 'r', encoding='utf-8') as f:
            source_content = f.read()
        
        # Write to target (overwrite completely)
        with open(target_local, 'w', encoding='utf-8') as f:
            f.write(source_content)
        
        if log_callback:
            log_callback("[OK] Rscmgr content copied successfully")
            
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Failed to copy rscmgr content: {str(e)}")
        raise


def create_rscmgr_file(samsung_path, rscmgr_filename, vince_rscmgr_path, changelist_id, log_callback=None):
    """
    Create new rscmgr file by syncing folder and creating file with VINCE content
    """
    if log_callback:
        log_callback(f"[SYSTEM] Creating new rscmgr file: {rscmgr_filename}")
    
    try:
        # Construct rscmgr folder path
        rscmgr_folder_path = f"{samsung_path}system/rscmgr/..."
        
        # Map and sync the rscmgr folder
        if log_callback:
            log_callback(f"[SYNC] Syncing rscmgr folder: {rscmgr_folder_path}")
        
        map_single_depot(rscmgr_folder_path, log_callback)
        sync_file_silent(rscmgr_folder_path)
        
        # Get local folder path
        local_folder_path = depot_to_local_path(f"{samsung_path}system/rscmgr/")
        
        # Ensure directory exists
        os.makedirs(local_folder_path, exist_ok=True)
        
        # Create new file path
        local_new_file_path = os.path.join(local_folder_path, rscmgr_filename)
        
        # Read VINCE content if provided, otherwise create empty file
        if vince_rscmgr_path:
            vince_local = depot_to_local_path(vince_rscmgr_path)
            with open(vince_local, 'r', encoding='utf-8') as f:
                vince_content = f.read()
        else:
            # Create basic rscmgr content with clean structure - NO setprop initially
            vince_content = """# rscmgr rc file
service rscmgr /system/bin/rscmgr
    class core
    user system
    group system readahead

"""
        
        # Create new file with content
        with open(local_new_file_path, 'w', encoding='utf-8') as f:
            f.write(vince_content)
        
        if log_callback:
            log_callback(f"[OK] Created new rscmgr file: {local_new_file_path}")
        
        # Add file to P4
        new_file_depot_path = construct_rscmgr_file_path(samsung_path, rscmgr_filename)
        add_file_to_p4(new_file_depot_path, changelist_id, log_callback)
        
        # Return depot path for the new file
        return new_file_depot_path
        
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Failed to create rscmgr file: {str(e)}")
        raise


def get_file_line_count(file_path):
    """Get number of lines in a file"""
    try:
        local_path = depot_to_local_path(file_path)
        with open(local_path, 'r', encoding='utf-8') as f:
            return len(f.readlines())
    except:
        return 0


def add_file_to_p4(file_depot_path, changelist_id, log_callback=None):
    """
    Add new file to P4 and changelist
    """
    try:
        if log_callback:
            log_callback(f"[P4] Adding new file to P4: {file_depot_path}")
        
        # Add file to P4
        cmd = f"p4 add -c {changelist_id} {file_depot_path}"
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        
        if result.returncode == 0:
            if log_callback:
                log_callback(f"[OK] File added to P4 and changelist {changelist_id}")
        else:
            if log_callback:
                log_callback(f"[ERROR] Failed to add file to P4: {result.stderr}")
            raise RuntimeError(f"Failed to add file to P4: {result.stderr}")
            
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Error adding file to P4: {str(e)}")
        raise


def process_target_workspace_enhanced(workspace_or_path, category, vince_rscmgr_filename, vince_rscmgr_path, 
                                    changelist_id, log_callback=None):
    """
    ENHANCED: Now processes device_common.mk, Android.mk, and rscmgr.rc
    Returns updated changelist_id (may create new one if none provided)
    """
    if log_callback:
        log_callback(f"\n[SYSTEM] Processing {category} input: {workspace_or_path}")
    
    current_changelist_id = changelist_id
    
    try:
        # ========================================================================
        # STEP 1: RESOLVE INPUT TO device_common.mk PATH
        # ========================================================================
        device_common_path = resolve_input_to_device_common_path(workspace_or_path, log_callback)
        if not device_common_path:
            if log_callback:
                log_callback(f"[ERROR] Failed to resolve {category} input to device_common.mk")
            return current_changelist_id
        
        # Map and sync device_common.mk
        map_single_depot(device_common_path, log_callback)
        sync_file_silent(device_common_path)
        
        # ========================================================================
        # STEP 2: FIND SAMSUNG VENDOR PATH
        # ========================================================================
        samsung_path = None
        
        # Try to get from workspace first (if input was workspace)
        if is_workspace_like(workspace_or_path):
            samsung_path = find_samsung_vendor_path_from_workspace(workspace_or_path, log_callback)
        
        
        
        if not samsung_path:
            if log_callback:
                log_callback(f"[ERROR] Cannot find samsung vendor path for {category}")
            return current_changelist_id
        
        # ========================================================================
        # STEP 3: PROCESS device_common.mk
        # ========================================================================
        if log_callback:
            log_callback(f"[{category}] Processing device_common.mk...")
        
        # Check existing rscmgr reference in device_common.mk
        existing_rscmgr = find_rscmgr_filename_from_device_common(device_common_path, log_callback)
        
        device_common_needs_update = False
        
        if existing_rscmgr:
            if log_callback:
                log_callback(f"[INFO] {category} device_common.mk has existing rscmgr reference: {existing_rscmgr}")
            
            # Compare with VINCE rscmgr filename
            if existing_rscmgr != vince_rscmgr_filename:
                if log_callback:
                    log_callback(f"[DIFF] {category} rscmgr reference differs from VINCE: {existing_rscmgr} ≠ {vince_rscmgr_filename}")
                device_common_needs_update = True
            else:
                if log_callback:
                    log_callback(f"[OK] {category} rscmgr reference matches VINCE: {existing_rscmgr}")
        else:
            if log_callback:
                log_callback(f"[INFO] {category} device_common.mk has no rscmgr reference, will add: {vince_rscmgr_filename}")
            device_common_needs_update = True
        
        # Update device_common.mk if needed
        if device_common_needs_update:
            # Create changelist if not exists
            if not current_changelist_id:
                current_changelist_id = create_changelist_silent("System bringup - Update readahead feature")
                if log_callback:
                    log_callback(f"[CL] Created pending changelist: {current_changelist_id}")
            
            # Checkout device_common.mk
            checkout_file_silent(device_common_path, current_changelist_id, log_callback)
            
            # Update or add rscmgr reference
            if existing_rscmgr:
                update_device_common_mk_rscmgr_reference(device_common_path, existing_rscmgr, vince_rscmgr_filename, log_callback)
            else:
                add_rscmgr_reference_to_device_common(device_common_path, vince_rscmgr_filename, log_callback)
        
        # ========================================================================
        # STEP 4: PROCESS Android.mk (NEW)
        # ========================================================================
        if log_callback:
            log_callback(f"[{category}] Processing Android.mk...")
        
        # Find Android.mk
        android_mk_path = find_android_mk_from_samsung_path(samsung_path, log_callback)
        
        if not android_mk_path:
            if log_callback:
                log_callback(f"[WARNING] Android.mk not found for {category}, skipping...")
        else:
            # Map and sync Android.mk
            map_single_depot(android_mk_path, log_callback)
            sync_file_silent(android_mk_path)
            
            # Check if rscmgr module exists
            module_exists = check_rscmgr_in_android_mk(android_mk_path, vince_rscmgr_filename, log_callback)
            
            if module_exists:
                if log_callback:
                    log_callback(f"[OK] {category} Android.mk already has rscmgr module: {vince_rscmgr_filename}")
            else:
                if log_callback:
                    log_callback(f"[ADD] {category} Android.mk missing rscmgr module, adding...")
                
                # Create changelist if not exists
                if not current_changelist_id:
                    current_changelist_id = create_changelist_silent("System bringup - Update readahead feature")
                    if log_callback:
                        log_callback(f"[CL] Created pending changelist: {current_changelist_id}")
                
                # Add module to Android.mk
                add_rscmgr_module_to_android_mk(android_mk_path, vince_rscmgr_filename, current_changelist_id, log_callback)
        
        # ========================================================================
        # STEP 5: PROCESS rscmgr.rc
        # ========================================================================
        if log_callback:
            log_callback(f"[{category}] Processing rscmgr.rc...")
        
        # Find rscmgr file path
        target_rscmgr_path = construct_rscmgr_file_path(samsung_path, vince_rscmgr_filename)
        
        if validate_depot_path(target_rscmgr_path):
            # File exists - check content
            if log_callback:
                log_callback(f"[FOUND] {category} rscmgr file exists: {target_rscmgr_path}")
            
            # Map and sync rscmgr file
            map_single_depot(target_rscmgr_path, log_callback)
            sync_file_silent(target_rscmgr_path)
            
            # Compare line counts
            vince_lines = get_file_line_count(vince_rscmgr_path)
            target_lines = get_file_line_count(target_rscmgr_path)
            
            if log_callback:
                log_callback(f"[COMPARISON] VINCE {vince_rscmgr_filename}: {vince_lines} lines")
                log_callback(f"[COMPARISON] {category} {vince_rscmgr_filename}: {target_lines} lines")
            
            if target_lines == vince_lines:
                if log_callback:
                    log_callback(f"[OK] {category} {vince_rscmgr_filename} has same line count as VINCE - content identical")
            else:
                if log_callback:
                    log_callback(f"[DIFF] {category} {vince_rscmgr_filename} differs from VINCE, updating content...")
                
                # Create changelist if not exists
                if not current_changelist_id:
                    current_changelist_id = create_changelist_silent("System bringup - Update readahead feature")
                    if log_callback:
                        log_callback(f"[CL] Created pending changelist: {current_changelist_id}")
                
                # Checkout and update content
                checkout_file_silent(target_rscmgr_path, current_changelist_id, log_callback)
                copy_rscmgr_content(vince_rscmgr_path, target_rscmgr_path, log_callback)
        else:
            # File doesn't exist - create new one
            if log_callback:
                log_callback(f"[MISSING] {category} rscmgr file not found, creating new one...")
            
            # Create changelist if not exists
            if not current_changelist_id:
                current_changelist_id = create_changelist_silent("System bringup - Update readahead feature")
                if log_callback:
                    log_callback(f"[CL] Created pending changelist: {current_changelist_id}")
            
            # Create new rscmgr file
            new_rscmgr_path = create_rscmgr_file(samsung_path, vince_rscmgr_filename, vince_rscmgr_path, current_changelist_id, log_callback)
            
            if log_callback:
                log_callback(f"[OK] {category} rscmgr file created: {new_rscmgr_path}")
        
        if log_callback:
            log_callback(f"[{category}] Processing completed successfully")
        
        return current_changelist_id
        
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Failed to process {category} input: {str(e)}")
        return current_changelist_id


def run_readahead_process(workspaces, resource1_libs, resource2_libs, changelist_id,
                         log_callback, progress_callback=None, error_callback=None):
    """
    Execute readahead process with full integration history support
    Cascades across REL → FLUMEN → BENI automatically
    """
    try:
        if log_callback:
            log_callback("[READAHEAD] Starting readahead process with integration cascading...")

        # ============================================================================
        # STEP 0: DETERMINE PROCESSING ORDER
        # ============================================================================
        rel_ws = workspaces.get("REL", "").strip()
        flumen_ws = workspaces.get("FLUMEN", "").strip()
        beni_ws = workspaces.get("BENI", "").strip()

        if log_callback:
            log_callback("[VALIDATION] Checking provided workspaces...")
            log_callback(f"[INPUT] REL: {rel_ws if rel_ws else '(not provided)'}")
            log_callback(f"[INPUT] FLUMEN: {flumen_ws if flumen_ws else '(not provided)'}")
            log_callback(f"[INPUT] BENI: {beni_ws if beni_ws else '(not provided)'}")

        # Validate at least one workspace
        if not rel_ws and not flumen_ws and not beni_ws:
            raise RuntimeError("At least one workspace from REL, FLUMEN, or BENI is required")

        # Determine cascade order
        cascade_branches = []
        if rel_ws:
            cascade_branches = ["REL", "FLUMEN", "BENI"]
        elif flumen_ws:
            cascade_branches = ["FLUMEN", "BENI"]
        elif beni_ws:
            cascade_branches = ["BENI"]

        if log_callback:
            log_callback(f"[CASCADE] Processing order: {' → '.join(cascade_branches)}")

        if progress_callback:
            progress_callback(10)

        # ============================================================================
        # STEP 1: FIND RSCMGR FILENAME
        # ============================================================================
        primary_branch = cascade_branches[0]
        primary_workspace = workspaces[primary_branch]

        if log_callback:
            log_callback(f"[PRIORITY] Using {primary_branch} to find rscmgr filename...")

        device_common_path, _ = find_device_common_mk_path(primary_workspace, log_callback)
        if not device_common_path:
            raise RuntimeError(f"Cannot find device_common.mk in {primary_branch}")

        map_single_depot(device_common_path)
        sync_file_silent(device_common_path)

        rscmgr_filename = find_rscmgr_filename_from_device_common(device_common_path, log_callback)

        if not rscmgr_filename:
            rscmgr_filename = prompt_for_rscmgr_filename(log_callback)
            if not rscmgr_filename:
                raise RuntimeError("rscmgr filename is required")

        if log_callback:
            log_callback(f"[OK] Using rscmgr filename: {rscmgr_filename}")

        if progress_callback:
            progress_callback(20)

        # ============================================================================
        # STEP 2: CREATE/GET SHARED CHANGELIST
        # ============================================================================
        if changelist_id:
            if log_callback:
                log_callback(f"[CL] Using provided changelist: {changelist_id}")
        else:
            changelist_id = create_changelist_silent("Readahead - Update rscmgr files across branches")
            if log_callback:
                log_callback(f"[CL] Created new changelist: {changelist_id}")

        if progress_callback:
            progress_callback(30)

        # ============================================================================
        # STEP 3: PROCESS BRANCHES WITH CASCADING
        # ============================================================================
        source_rscmgr_path = None
        current_device_common_path = None
        current_android_mk_path = None

        progress_step = 70 / len(cascade_branches)
        current_progress = 30

        for idx, branch in enumerate(cascade_branches):
            try:
                # Determine if this is the first branch (for library editing)
                is_first_branch = (idx == 0)

                # Determine input for this branch
                if idx == 0:
                    # First branch - use workspace name
                    branch_input = workspaces[branch]
                else:
                    # Cascaded branch - get paths from integration
                    if log_callback:
                        log_callback(f"\n[CASCADE] Finding {branch} paths from integration...")

                    branch_paths = get_cascaded_paths_from_integration(
                        current_device_common_path, current_android_mk_path,
                        branch, log_callback
                    )

                    if not branch_paths:
                        if log_callback:
                            log_callback(f"[WARNING] Could not cascade to {branch}, skipping...")
                        continue

                    branch_input = branch_paths

                # Process this branch
                device_common_path, android_mk_path, rscmgr_path = process_single_branch(
                    branch, branch_input, rscmgr_filename, resource1_libs, resource2_libs,
                    changelist_id, source_rscmgr_path, is_first_branch, log_callback
                )

                # Save paths for next cascade
                current_device_common_path = device_common_path
                current_android_mk_path = android_mk_path
                source_rscmgr_path = rscmgr_path

                current_progress += progress_step
                if progress_callback:
                    progress_callback(int(current_progress))

            except Exception as e:
                if log_callback:
                    log_callback(f"[ERROR] Failed to process {branch}: {str(e)}")

                response = messagebox.askyesno(
                    "Processing Error",
                    f"Error processing {branch}: {str(e)}\n\nContinue with remaining branches?",
                )

                if not response:
                    raise

        if progress_callback:
            progress_callback(100)

        # ============================================================================
        # STEP 4: SUMMARY
        # ============================================================================
        if log_callback:
            log_callback("\n[READAHEAD] ========== PROCESS COMPLETED SUCCESSFULLY ==========")
            log_callback(f"[SUMMARY] Rscmgr filename: {rscmgr_filename}")
            log_callback(f"[SUMMARY] Resource=1 libraries: {len(resource1_libs)}")
            log_callback(f"[SUMMARY] Resource=2 libraries: {len(resource2_libs)}")
            log_callback(f"[SUMMARY] Changelist: {changelist_id}")
            log_callback(f"[SUMMARY] Cascaded branches: {' → '.join(cascade_branches)}")

    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Readahead process failed: {str(e)}")
        if error_callback:
            error_callback("Readahead Process Error", str(e))
        if progress_callback:
            progress_callback(0)
        raise


def get_cascaded_paths_from_integration(current_device_common_path, current_android_mk_path, branch, log_callback=None):
    """Get paths for cascaded branch from integration history"""
    try:
        if log_callback:
            log_callback(f"[CASCADE] Getting integration paths for {branch}...")
        
        integrated_device_common = get_integration_source_depot_path(current_device_common_path, log_callback)
        integrated_android_mk = get_integration_source_depot_path(current_android_mk_path, log_callback)
        
        if not integrated_device_common or not integrated_android_mk:
            if log_callback:
                log_callback(f"[WARNING] No integration paths found for {branch}")
            return None
            
        if log_callback:
            log_callback(f"[OK] Found integration paths for {branch}")
            log_callback(f"[INTEGRATION] device_common: {integrated_device_common}")
            log_callback(f"[INTEGRATION] android_mk: {integrated_android_mk}")
            
        return {
            'device_common_path': integrated_device_common,
            'android_mk_path': integrated_android_mk
        }
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Failed to get cascaded paths for {branch}: {str(e)}")
        return None


def update_libraries_in_rscmgr(rscmgr_path, resource1_libs, resource2_libs, log_callback=None):
    """Update library entries in rscmgr file with multi-resource support - preserve structure"""
    try:
        if not resource1_libs and not resource2_libs:
            if log_callback:
                log_callback("[INFO] No libraries to update")
            return
            
        local_path = depot_to_local_path(rscmgr_path)
        
        with open(local_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse existing content and preserve ALL resources
        lines = content.split('\n')
        final_content = []
        resource_sections = {}  # Store all resource sections
        current_section = None
        current_resource_num = None
        highest_resource = 0
        
        # Parse existing content - preserve ALL resources and structure
        for line in lines:
            if line.strip().startswith('on property:sys.readahead.resource='):
                # Extract resource number
                import re
                match = re.search(r'on property:sys\.readahead\.resource=(\d+)', line.strip())
                if match:
                    current_resource_num = int(match.group(1))
                    current_section = current_resource_num
                    resource_sections[current_resource_num] = []
                    highest_resource = max(highest_resource, current_resource_num)
                    final_content.append(line)
                    if log_callback:
                        log_callback(f"[PARSE] Found resource={current_resource_num}")
                else:
                    final_content.append(line)
            elif line.strip().startswith('setprop sys.readahead.resource 0'):
                # Skip setprop lines - will add clean single one later at highest resource
                current_section = None
                continue
            elif current_section is not None and line.strip().startswith('readahead '):
                # Add readahead line to current resource section
                resource_sections[current_resource_num].append(line)
            else:
                if current_section is None:
                    final_content.append(line)
                else:
                    # This is a readahead line or empty line within a section
                    if line.strip() or not line.strip():  # Keep empty lines for structure
                        if line.strip().startswith('readahead '):
                            resource_sections[current_resource_num].append(line)
                        else:
                            # Empty line or other content - add to final content
                            final_content.append(line)
        
        # Add new libraries to appropriate sections
        updated_libs = 0
        
        # Process Resource=1 libraries
        if 1 in resource_sections or resource1_libs:
            if 1 not in resource_sections:
                resource_sections[1] = []
            
            for lib in resource1_libs:
                lib_entry = f"    readahead {lib} --fully"
                # Check if library already exists
                existing = any(lib_entry in line for line in resource_sections[1])
                if not existing:
                    resource_sections[1].append(lib_entry)
                    updated_libs += 1
                    if log_callback:
                        log_callback(f"[LIBRARY] Added Resource=1 library: {lib}")
        
        # Process Resource=2 libraries  
        if 2 in resource_sections or resource2_libs:
            if 2 not in resource_sections:
                resource_sections[2] = []
            
            for lib in resource2_libs:
                lib_entry = f"    readahead {lib} --fully"
                # Check if library already exists
                existing = any(lib_entry in line for line in resource_sections[2])
                if not existing:
                    resource_sections[2].append(lib_entry)
                    updated_libs += 1
                    if log_callback:
                        log_callback(f"[LIBRARY] Added Resource=2 library: {lib}")
        
        # Rebuild content preserving structure and adding libraries
        rebuilt_content = []
        i = 0
        while i < len(final_content):
            line = final_content[i]
            
            if line.strip().startswith('on property:sys.readahead.resource='):
                # Extract resource number
                import re
                match = re.search(r'on property:sys\.readahead\.resource=(\d+)', line.strip())
                if match:
                    resource_num = int(match.group(1))
                    rebuilt_content.append(line)
                    
                    # Add libraries for this resource if they exist
                    if resource_num in resource_sections and resource_sections[resource_num]:
                        for lib_line in resource_sections[resource_num]:
                            rebuilt_content.append(lib_line)
                    
                    # Add setprop if this is the highest resource
                    if resource_num == highest_resource:
                        rebuilt_content.append('    setprop sys.readahead.resource 0')
                        if log_callback:
                            log_callback(f"[CLEAN] Setprop added at resource={resource_num} (highest resource)")
                else:
                    rebuilt_content.append(line)
            else:
                rebuilt_content.append(line)
            i += 1
        
        # Write updated content
        with open(local_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(rebuilt_content))
            
        if log_callback:
            log_callback(f"[OK] Updated {updated_libs} libraries in rscmgr file with multi-resource support")
            if updated_libs > 0:
                log_callback(f"[LIBRARIES] Resource=1: {len(resource1_libs)}, Resource=2: {len(resource2_libs)}")
                log_callback(f"[STRUCTURE] Preserved all resources (1-{highest_resource}), setprop at resource={highest_resource}")
            
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Failed to update libraries: {str(e)}")
        raise


def process_single_branch(branch, branch_input, rscmgr_filename, resource1_libs, resource2_libs, 
                        changelist_id, source_rscmgr_path, is_first_branch, log_callback=None):
    """Process single branch with library support"""
    try:
        if log_callback:
            log_callback(f"\n[{branch}] ========== Processing {branch} ==========")
        
        # Get paths for this branch
        if isinstance(branch_input, str):
            # First branch - process from workspace
            if log_callback:
                log_callback(f"[{branch}] Finding paths from workspace: {branch_input}")
            
            device_common_path, _ = find_device_common_mk_path(branch_input, log_callback)
            if not device_common_path:
                raise RuntimeError(f"Cannot find device_common.mk in {branch}")
            
            samsung_path = find_samsung_vendor_path_from_workspace(branch_input, log_callback)
            if not samsung_path:
                raise RuntimeError(f"Cannot find samsung vendor path in {branch}")
            
            android_mk_path = find_android_mk_from_samsung_path(samsung_path, log_callback)
            if not android_mk_path:
                raise RuntimeError(f"Cannot find Android.mk in {branch}")
        else:
            # Cascaded branch - use provided paths
            if log_callback:
                log_callback(f"[{branch}] Using integrated paths from previous branch")
            
            device_common_path = branch_input['device_common_path']
            android_mk_path = branch_input['android_mk_path']
            
            if log_callback:
                log_callback(f"[{branch}] device_common.mk: {device_common_path}")
                log_callback(f"[{branch}] Android.mk: {android_mk_path}")
        
        # Map and sync files
        map_single_depot(device_common_path, log_callback)
        sync_file_silent(device_common_path)
        
        map_single_depot(android_mk_path, log_callback)
        sync_file_silent(android_mk_path)
        
        # Process device_common.mk - add rscmgr reference if needed
        existing_rscmgr = find_rscmgr_filename_from_device_common(device_common_path, log_callback)
        if not existing_rscmgr:
            if log_callback:
                log_callback(f"[{branch}] Adding rscmgr reference to device_common.mk...")
            
            checkout_file_silent(device_common_path, changelist_id, log_callback)
            add_rscmgr_reference_to_device_common(device_common_path, rscmgr_filename, log_callback)
        elif existing_rscmgr != rscmgr_filename:
            if log_callback:
                log_callback(f"[{branch}] Updating rscmgr reference in device_common.mk: {existing_rscmgr} → {rscmgr_filename}")
            
            checkout_file_silent(device_common_path, changelist_id, log_callback)
            update_device_common_mk_rscmgr_reference(device_common_path, existing_rscmgr, rscmgr_filename, log_callback)
        
        # Process Android.mk - ensure rscmgr module exists
        module_exists = check_rscmgr_in_android_mk(android_mk_path, rscmgr_filename, log_callback)
        if not module_exists:
            if log_callback:
                log_callback(f"[{branch}] Adding rscmgr module to Android.mk...")
            
            add_rscmgr_module_to_android_mk(android_mk_path, rscmgr_filename, changelist_id, log_callback)
        
        # Process rscmgr file
        samsung_path_match = re.search(r'(.+/vendor/samsung/)', android_mk_path)
        if not samsung_path_match:
            raise RuntimeError(f"Cannot extract samsung path from Android.mk: {android_mk_path}")
        
        samsung_path = samsung_path_match.group(1)
        rscmgr_path = construct_rscmgr_file_path(samsung_path, rscmgr_filename)
        
        if validate_depot_path(rscmgr_path):
            # File exists - map and sync
            if log_callback:
                log_callback(f"[{branch}] Found existing rscmgr file: {rscmgr_path}")
            
            map_single_depot(rscmgr_path, log_callback)
            sync_file_silent(rscmgr_path)
            
            # Update libraries for ALL branches (not just first branch)
            if resource1_libs or resource2_libs:
                checkout_file_silent(rscmgr_path, changelist_id, log_callback)
                update_libraries_in_rscmgr(rscmgr_path, resource1_libs, resource2_libs, log_callback)
                if log_callback:
                    log_callback(f"[{branch}] Updated libraries in rscmgr file")
        else:
            # File doesn't exist - create new
            if log_callback:
                log_callback(f"[{branch}] Creating new rscmgr file: {rscmgr_path}")
            
            # Create with empty content first, then update libraries if needed
            create_rscmgr_file(samsung_path, rscmgr_filename, "", changelist_id, log_callback)
            
            # Update libraries for ALL branches (not just first branch)
            if resource1_libs or resource2_libs:
                update_libraries_in_rscmgr(rscmgr_path, resource1_libs, resource2_libs, log_callback)
                if log_callback:
                    log_callback(f"[{branch}] Updated libraries in rscmgr file")
        
        if log_callback:
            log_callback(f"[{branch}] ========== {branch} Completed ==========")
        
        return device_common_path, android_mk_path, rscmgr_path
        
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Failed to process {branch}: {str(e)}")
        raise
