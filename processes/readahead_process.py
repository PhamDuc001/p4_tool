"""
Readahead process implementation with full integration history support
Handles cascading across REL → FLUMEN → BENI with automatic integration
Processes: device_common.mk, Android.mk, and rscmgr.rc files
"""

import os
import re
import subprocess
from typing import Dict, List, Optional, Tuple
from tkinter import messagebox, simpledialog

from core.p4_operations import (
    is_workspace_like,
    get_integration_source_depot_path,
    create_changelist_silent,
    map_single_depot,
    sync_file_silent,
    checkout_file_silent,
    validate_depot_path,
)
from processes.system_process import find_device_common_mk_path
from config.p4_config import depot_to_local_path
import tkinter as tk
from tkinter import simpledialog as sd
from tkinter import messagebox


def validate_workspace_format(workspace_name):
    """Validate if workspace has proper TEMPLATE format"""
    if not workspace_name:
        return False
    return is_workspace_like(workspace_name)


def find_rscmgr_filename_from_device_common(device_common_path, log_callback=None):
    """Find rscmgr.rc filename from device_common.mk file"""
    if log_callback:
        log_callback(f"[READAHEAD] Searching rscmgr filename in: {device_common_path}")

    try:
        local_path = depot_to_local_path(device_common_path)

        with open(local_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Look for rscmgr.rc or rscmgr_{model}.rc pattern
        rscmgr_match = re.search(r"rscmgr(?:_\w+)?\.rc", content)

        if rscmgr_match:
            rscmgr_file = rscmgr_match.group(0)
            if log_callback:
                log_callback(f"[OK] Found rscmgr filename: {rscmgr_file}")
            return rscmgr_file
        else:
            if log_callback:
                log_callback("[WARNING] No rscmgr filename found in device_common.mk")
            return None

    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Error reading device_common.mk: {str(e)}")
        return None


def prompt_for_rscmgr_filename(log_callback=None):
    """Prompt user to input rscmgr filename via dialog"""
    if log_callback:
        log_callback("[INPUT] Prompting user for rscmgr filename...")

    try:
        # Create a temporary root window for the dialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        try:
            filename = sd.askstring(
                "Rscmgr Filename",
                "Enter the rscmgr filename (e.g., rscmgr.rc or rscmgr_mt6789.rc):",
                initialvalue="rscmgr.rc",
                parent=root
            )
        finally:
            try:
                root.destroy()
            except:
                pass

        if filename:
            if log_callback:
                log_callback(f"[INPUT] User provided rscmgr filename: {filename}")
            return filename.strip()

        if log_callback:
            log_callback("[INFO] User cancelled input dialog")
        return None

    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Dialog error: {str(e)}")
        if log_callback:
            log_callback("[FALLBACK] Using default rscmgr.rc")
        return "rscmgr.rc"


def construct_rscmgr_file_path(samsung_path, rscmgr_filename):
    """Construct rscmgr file path from samsung base path"""
    return f"{samsung_path}system/rscmgr/{rscmgr_filename}"


def find_android_mk_from_samsung_path(samsung_path, log_callback=None):
    """Find Android.mk in samsung vendor path"""
    android_mk_path = f"{samsung_path}system/rscmgr/Android.mk"
    
    if validate_depot_path(android_mk_path):
        if log_callback:
            log_callback(f"[FOUND] Android.mk: {android_mk_path}")
        return android_mk_path
    
    if log_callback:
        log_callback(f"[NOT_FOUND] Android.mk not found: {android_mk_path}")
    return None


def find_samsung_vendor_path(workspace_name, log_callback=None):
    """Find vendor/samsung base path from workspace"""
    try:
        _, view_paths = find_device_common_mk_path(workspace_name, log_callback)
        
        for view_path in view_paths:
            if "/vendor/samsung/" in view_path:
                match = re.search(r"(.+/vendor/samsung/)", view_path)
                if match:
                    samsung_path = match.group(1)
                    if log_callback:
                        log_callback(f"[FOUND] Samsung vendor path: {samsung_path}")
                    return samsung_path
        
        if log_callback:
            log_callback("[NOT_FOUND] No vendor/samsung path found")
        return None
    
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Error finding samsung path: {str(e)}")
        return None


def extract_rscmgr_folder_from_android_mk(android_mk_path):
    """Extract rscmgr folder path from Android.mk path"""
    if android_mk_path and android_mk_path.endswith("Android.mk"):
        return android_mk_path.rsplit("/", 1)[0] + "/"
    return None


def add_rscmgr_to_device_common_mk(device_common_path, rscmgr_filename, changelist_id, log_callback=None):
    """
    Add rscmgr reference to device_common.mk if not already present
    Returns True if file was modified, False if already exists
    """
    try:
        local_path = depot_to_local_path(device_common_path)

        with open(local_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check if already exists
        if rscmgr_filename in content:
            if log_callback:
                log_callback("[INFO] rscmgr reference already exists in device_common.mk - no checkout needed")
            return False

        # Need to modify - checkout first
        checkout_file_silent(device_common_path, changelist_id)

        # Append to file
        lines = content.splitlines(keepends=True)
        lines.append("\n")
        lines.append("# SystemPerformance - rscmgr\n")
        lines.append("PRODUCT_PACKAGES += \\\n")
        lines.append(f"    {rscmgr_filename}\n")

        with open(local_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        if log_callback:
            log_callback("[OK] Added rscmgr reference to device_common.mk")
        
        return True

    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Failed to add rscmgr reference: {str(e)}")
        raise


def check_rscmgr_in_android_mk(android_mk_path, rscmgr_filename, log_callback=None):
    """Check if rscmgr module already exists in Android.mk"""
    try:
        local_path = depot_to_local_path(android_mk_path)

        with open(local_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for LOCAL_MODULE := rscmgr_filename
        if f"LOCAL_MODULE := {rscmgr_filename}" in content:
            if log_callback:
                log_callback("[INFO] rscmgr module already exists in Android.mk")
            return True

        return False

    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Error checking Android.mk: {str(e)}")
        return False


def add_rscmgr_module_to_android_mk(android_mk_path, rscmgr_filename, changelist_id, log_callback=None):
    """Add rscmgr module definition to Android.mk"""
    try:
        local_path = depot_to_local_path(android_mk_path)

        # Check if module already exists
        if check_rscmgr_in_android_mk(android_mk_path, rscmgr_filename, log_callback):
            return

        checkout_file_silent(android_mk_path, changelist_id)

        with open(local_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Build module block with proper formatting
        module_block = (
            "\ninclude $(CLEAR_VARS)\n"
            f"LOCAL_MODULE := {rscmgr_filename}\n"
            "LOCAL_MODULE_TAGS := optional\n"
            "LOCAL_MODULE_CLASS := ETC\n"
            "LOCAL_MODULE_PATH := $(TARGET_OUT)/etc/init\n"
            "LOCAL_SRC_FILES := $(LOCAL_MODULE)\n"
            "include $(BUILD_PREBUILT)\n"
        )

        # Append to file
        with open(local_path, "a", encoding="utf-8") as f:
            f.write(module_block)

        if log_callback:
            log_callback("[OK] Added rscmgr module to Android.mk")

    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Failed to add module to Android.mk: {str(e)}")
        raise


def copy_rscmgr_file_content(source_rscmgr_path, target_rscmgr_path, log_callback=None):
    """Copy rscmgr file content from source to target"""
    try:
        source_local = depot_to_local_path(source_rscmgr_path)
        target_local = depot_to_local_path(target_rscmgr_path)

        with open(source_local, "r", encoding="utf-8") as f:
            source_content = f.read()

        with open(target_local, "w", encoding="utf-8") as f:
            f.write(source_content)

        if log_callback:
            log_callback("[OK] Copied rscmgr file content")

    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Failed to copy rscmgr content: {str(e)}")
        raise


def create_rscmgr_file(rscmgr_folder_path, rscmgr_filename, source_rscmgr_path, 
                       changelist_id, log_callback=None):
    """Create new rscmgr file by copying from source or creating stub"""
    try:
        if log_callback:
            log_callback(f"[CREATE] Creating new rscmgr file...")

        # Map and sync the rscmgr folder
        map_single_depot(f"{rscmgr_folder_path}...")
        sync_file_silent(f"{rscmgr_folder_path}...")

        # Construct target path
        target_rscmgr_path = f"{rscmgr_folder_path}{rscmgr_filename}"
        
        # Ensure local directory exists
        target_local = depot_to_local_path(target_rscmgr_path)
        target_dir = os.path.dirname(target_local)
        os.makedirs(target_dir, exist_ok=True)

        # Create file content
        if source_rscmgr_path:
            # Copy from source
            copy_rscmgr_file_content(source_rscmgr_path, target_rscmgr_path, log_callback)
        else:
            # Create stub file
            stub_content = "# rscmgr rc file\n"
            with open(target_local, "w", encoding="utf-8") as f:
                f.write(stub_content)
            if log_callback:
                log_callback("[OK] Created stub rscmgr file")

        # Add file to P4
        cmd = f"p4 add -c {changelist_id} {target_rscmgr_path}"
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)

        if result.returncode == 0:
            if log_callback:
                log_callback(f"[OK] New rscmgr file added to changelist {changelist_id}")
        else:
            if log_callback:
                log_callback(f"[WARNING] p4 add result: {result.stderr}")
        
        return target_rscmgr_path

    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Failed to create rscmgr file: {str(e)}")
        raise


def edit_rscmgr_file(rscmgr_path, resource_num, libraries, changelist_id, log_callback=None):
    """Edit rscmgr file to add libraries to specified resource section"""
    if log_callback:
        log_callback(f"[EDIT] Adding {len(libraries)} libraries to resource={resource_num}")

    try:
        local_path = depot_to_local_path(rscmgr_path)

        with open(local_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        resource_pattern = f"sys.readahead.resource={resource_num}"
        section_start_index = None
        section_end_index = None

        # Find the resource section
        for i, line in enumerate(lines):
            if resource_pattern in line:
                section_start_index = i

                # Find end of this section
                section_end_index = len(lines)
                for j in range(i + 1, len(lines)):
                    if lines[j].strip().startswith("on property:"):
                        section_end_index = j
                        break

                break

        # If resource section not found, create it
        if section_start_index is None:
            if log_callback:
                log_callback(f"[CREATE] Creating new resource section for resource={resource_num}")

            new_section = [f"\non property:sys.readahead.resource={resource_num}\n"]
            for lib in libraries:
                new_section.append(f"    readahead {lib} --fully\n")
            new_section.append("    setprop sys.readahead.resource 0\n")

            lines.extend(new_section)
        else:
            # Resource section exists - insert libraries
            if log_callback:
                log_callback(f"[MODIFY] Modifying existing resource section")

            insert_index = section_start_index + 1

            # Skip existing readahead entries
            for j in range(section_start_index + 1, section_end_index):
                if lines[j].strip().startswith("readahead"):
                    insert_index = j + 1
                else:
                    break

            # Insert new libraries
            new_libs = [f"    readahead {lib} --fully\n" for lib in libraries]
            for idx, lib_line in enumerate(new_libs):
                lines.insert(insert_index + idx, lib_line)

        # Write updated content
        with open(local_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        if log_callback:
            log_callback(f"[OK] Added {len(libraries)} libraries to resource={resource_num}")

    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Failed to edit rscmgr file: {str(e)}")
        raise


def process_single_branch(branch_name, workspace_or_paths, rscmgr_filename, resource1_libs,
                         resource2_libs, changelist_id, source_rscmgr_path, is_first_branch, log_callback=None):
    """
    Process single branch: device_common.mk → Android.mk → rscmgr.rc
    
    Args:
        workspace_or_paths: For first branch - workspace name
                           For cascaded branches - dict with paths
        is_first_branch: True if this is the first branch in cascade (edit libraries)
    
    Returns:
        Tuple: (device_common_path, android_mk_path, rscmgr_path)
    """
    if log_callback:
        log_callback(f"\n[{branch_name}] ========== Processing {branch_name} ==========")

    try:
        # ====================================================================
        # STEP 1: Get device_common.mk path
        # ====================================================================
        if isinstance(workspace_or_paths, str):
            # First branch - get from workspace
            if log_callback:
                log_callback(f"[{branch_name}] Finding device_common.mk from workspace...")
            device_common_path, _ = find_device_common_mk_path(workspace_or_paths, log_callback)
        else:
            # Cascaded branch - use provided path
            device_common_path = workspace_or_paths.get('device_common_path')
            if log_callback:
                log_callback(f"[{branch_name}] Using integrated device_common.mk path")

        if not device_common_path:
            raise RuntimeError(f"Cannot find device_common.mk in {branch_name}")

        # Map, sync, checkout device_common.mk
        map_single_depot(device_common_path)
        sync_file_silent(device_common_path)
        
        # Add rscmgr reference (only checkout if needed)
        add_rscmgr_to_device_common_mk(device_common_path, rscmgr_filename, changelist_id, log_callback)

        if log_callback:
            log_callback(f"[{branch_name}] ✓ device_common.mk processed")

        # ====================================================================
        # STEP 2: Get Android.mk path
        # ====================================================================
        if isinstance(workspace_or_paths, str):
            # First branch - find from workspace
            if log_callback:
                log_callback(f"[{branch_name}] Finding Android.mk from workspace...")
            samsung_path = find_samsung_vendor_path(workspace_or_paths, log_callback)
            if not samsung_path:
                raise RuntimeError(f"Cannot find samsung vendor path in {branch_name}")
            android_mk_path = find_android_mk_from_samsung_path(samsung_path, log_callback)
        else:
            # Cascaded branch - use provided path
            android_mk_path = workspace_or_paths.get('android_mk_path')
            if log_callback:
                log_callback(f"[{branch_name}] Using integrated Android.mk path")

        if not android_mk_path:
            raise RuntimeError(f"Cannot find Android.mk in {branch_name}")

        # Map, sync Android.mk
        map_single_depot(android_mk_path)
        sync_file_silent(android_mk_path)
        
        # Add rscmgr module (only checkout if needed)
        add_rscmgr_module_to_android_mk(android_mk_path, rscmgr_filename, changelist_id, log_callback)

        if log_callback:
            log_callback(f"[{branch_name}] ✓ Android.mk processed")

        # ====================================================================
        # STEP 3: Process rscmgr.rc file
        # ====================================================================
        # Extract rscmgr folder from Android.mk path
        rscmgr_folder = extract_rscmgr_folder_from_android_mk(android_mk_path)
        rscmgr_path = f"{rscmgr_folder}{rscmgr_filename}"

        if log_callback:
            log_callback(f"[{branch_name}] Checking rscmgr file: {rscmgr_path}")

        rscmgr_exists = validate_depot_path(rscmgr_path)

        if rscmgr_exists:
            # File exists - need to edit
            if log_callback:
                log_callback(f"[{branch_name}] [FOUND] rscmgr file exists - will edit")
            
            map_single_depot(rscmgr_path)
            sync_file_silent(rscmgr_path)
            checkout_file_silent(rscmgr_path, changelist_id)
            
            # Always edit existing files with libraries
            if log_callback:
                log_callback(f"[{branch_name}] Editing existing rscmgr file with libraries...")
            
            if resource1_libs:
                edit_rscmgr_file(rscmgr_path, 1, resource1_libs, changelist_id, log_callback)

            if resource2_libs:
                edit_rscmgr_file(rscmgr_path, 2, resource2_libs, changelist_id, log_callback)
        else:
            # File doesn't exist - create it
            if log_callback:
                log_callback(f"[{branch_name}] [MISSING] Creating new rscmgr file...")
            
            rscmgr_path = create_rscmgr_file(rscmgr_folder, rscmgr_filename, 
                                            source_rscmgr_path, changelist_id, log_callback)
            
            # Only edit newly created files if first branch
            # (cascaded branches will have content copied from source)
            if is_first_branch:
                if log_callback:
                    log_callback(f"[{branch_name}] Editing newly created file (first branch)...")
                
                if resource1_libs:
                    edit_rscmgr_file(rscmgr_path, 1, resource1_libs, changelist_id, log_callback)

                if resource2_libs:
                    edit_rscmgr_file(rscmgr_path, 2, resource2_libs, changelist_id, log_callback)
            else:
                if log_callback:
                    log_callback(f"[{branch_name}] Skipping edit (content copied from previous branch)")

        if log_callback:
            log_callback(f"[{branch_name}] ✓ rscmgr.rc processed")
            log_callback(f"[{branch_name}] ========== {branch_name} completed ==========")

        return device_common_path, android_mk_path, rscmgr_path

    except Exception as e:
        if log_callback:
            log_callback(f"[{branch_name}] [ERROR] {str(e)}")
        raise


def get_cascaded_paths_from_integration(device_common_path, android_mk_path, 
                                       target_branch, log_callback=None):
    """
    Get integrated paths for next branch using integration history
    
    Returns:
        Dict with 'device_common_path' and 'android_mk_path'
    """
    try:
        if log_callback:
            log_callback(f"[INTEGRATION] Finding {target_branch} paths from integration history...")

        # Get integration source for device_common.mk
        integrated_device_common = get_integration_source_depot_path(device_common_path, log_callback)
        
        # Get integration source for Android.mk
        integrated_android_mk = get_integration_source_depot_path(android_mk_path, log_callback)

        if not integrated_device_common or not integrated_android_mk:
            if log_callback:
                log_callback(f"[WARNING] Could not find integration paths for {target_branch}")
            return None

        if log_callback:
            log_callback(f"[INTEGRATION] ✓ Found {target_branch} paths via integration")

        return {
            'device_common_path': integrated_device_common,
            'android_mk_path': integrated_android_mk
        }

    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Integration lookup failed: {str(e)}")
        return None


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
