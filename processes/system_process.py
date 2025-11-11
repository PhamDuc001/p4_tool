"""
Enhanced System process implementation with complete integration cascading
Handles the system bringup workflow:
- VINCE: Reference branch (read-only)
- REL/FLUMEN/BENI: Target branches (sync with VINCE via integration history)

Processing flow:
1. VINCE → Read device_common.mk, rscmgr.rc content (reference)
2. User-provided branch (e.g., REL) → Process from workspace
3. Auto-resolved branches → Process via integration history (REL → FLUMEN → BENI)

Files processed per target branch:
- device_common.mk: Add/update rscmgr reference
- Android.mk: Ensure rscmgr module definition exists
- rscmgr.rc: Copy complete content from VINCE
"""

import os
import re
import subprocess
from P4 import P4, P4Exception
from core.p4_operations import (
    get_client_name, run_cmd, create_changelist_silent, 
    map_single_depot, sync_file_silent, checkout_file_silent,
    validate_device_common_mk_path, validate_depot_path,
    is_workspace_like, auto_resolve_missing_branches, 
    find_device_common_mk_path, get_integration_source_depot_path
)
from config.p4_config import depot_to_local_path


def find_samsung_vendor_path_from_workspace(workspace_name, log_callback=None):
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
            log_callback("[NOT_FOUND] No vendor/samsung path found in workspace")
        return None
    
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Error finding samsung path: {str(e)}")
        return None


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


def construct_rscmgr_file_path(samsung_path, rscmgr_filename):
    """Construct rscmgr file path from samsung base path"""
    return f"{samsung_path}system/rscmgr/{rscmgr_filename}"


def get_rscmgr_reference_from_device_common(device_common_path, log_callback=None):
    """Get rscmgr file reference from device_common.mk"""
    try:
        local_path = depot_to_local_path(device_common_path)
        
        with open(local_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for rscmgr.rc or rscmgr_{model}.rc pattern
        rscmgr_match = re.search(r'rscmgr(?:_\w+)?\.rc', content)
        
        if rscmgr_match:
            return rscmgr_match.group(0)
        
        return None
        
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Error reading device_common.mk: {str(e)}")
        return None


def read_rscmgr_content(rscmgr_path, log_callback=None):
    """Read complete content from rscmgr file"""
    try:
        local_path = depot_to_local_path(rscmgr_path)
        
        with open(local_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if log_callback:
            log_callback(f"[OK] Read rscmgr content ({len(content)} bytes)")
        
        return content
        
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Error reading rscmgr file: {str(e)}")
        raise


def update_device_common_mk_rscmgr_reference(device_common_path, old_rscmgr_filename, 
                                             new_rscmgr_filename, log_callback=None):
    """Update rscmgr file reference in device_common.mk"""
    if log_callback:
        log_callback(f"[UPDATE] Updating device_common.mk: {old_rscmgr_filename} → {new_rscmgr_filename}")
    
    try:
        local_path = depot_to_local_path(device_common_path)
        
        with open(local_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        updated_content = content.replace(old_rscmgr_filename, new_rscmgr_filename)
        
        with open(local_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        if log_callback:
            log_callback(f"[OK] Updated device_common.mk rscmgr reference")
            
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Failed to update device_common.mk: {str(e)}")
        raise


def add_rscmgr_reference_to_device_common(device_common_path, rscmgr_filename, log_callback=None):
    """Add rscmgr file reference to device_common.mk"""
    if log_callback:
        log_callback(f"[ADD] Adding rscmgr reference to device_common.mk: {rscmgr_filename}")
    
    try:
        local_path = depot_to_local_path(device_common_path)
        
        with open(local_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        lines.append('\n')
        lines.append('# Rscmgr \n')
        lines.append('PRODUCT_PACKAGES += \\\n')
        lines.append(f'    {rscmgr_filename}\n')
        
        with open(local_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        if log_callback:
            log_callback(f"[OK] Added rscmgr reference to device_common.mk")
            
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

        if check_rscmgr_in_android_mk(android_mk_path, rscmgr_filename, log_callback):
            return

        checkout_file_silent(android_mk_path, changelist_id, log_callback)

        with open(local_path, "r", encoding="utf-8") as f:
            content = f.read()

        module_block = (
            "\ninclude $(CLEAR_VARS)\n"
            f"LOCAL_MODULE := {rscmgr_filename}\n"
            "LOCAL_MODULE_TAGS := optional\n"
            "LOCAL_MODULE_CLASS := ETC\n"
            "LOCAL_MODULE_PATH := $(TARGET_OUT)/etc/init\n"
            "LOCAL_SRC_FILES := $(LOCAL_MODULE)\n"
            "include $(BUILD_PREBUILT)\n"
        )

        with open(local_path, "a", encoding="utf-8") as f:
            f.write(module_block)

        if log_callback:
            log_callback("[OK] Added rscmgr module to Android.mk")

    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Failed to add module to Android.mk: {str(e)}")
        raise


def write_rscmgr_content(rscmgr_path, content, log_callback=None):
    """Write content to rscmgr file (complete overwrite)"""
    try:
        local_path = depot_to_local_path(rscmgr_path)
        
        with open(local_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        if log_callback:
            log_callback("[OK] Wrote rscmgr content")
            
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Failed to write rscmgr content: {str(e)}")
        raise


def create_rscmgr_file(samsung_path, rscmgr_filename, vince_content, 
                      changelist_id, log_callback=None):
    """Create new rscmgr file with VINCE content"""
    if log_callback:
        log_callback(f"[CREATE] Creating new rscmgr file: {rscmgr_filename}")
    
    try:
        rscmgr_folder_path = f"{samsung_path}system/rscmgr/..."
        
        if log_callback:
            log_callback(f"[SYNC] Syncing rscmgr folder: {rscmgr_folder_path}")
        
        map_single_depot(rscmgr_folder_path, log_callback)
        sync_file_silent(rscmgr_folder_path)
        
        local_folder_path = depot_to_local_path(f"{samsung_path}system/rscmgr/")
        os.makedirs(local_folder_path, exist_ok=True)
        
        local_new_file_path = os.path.join(local_folder_path, rscmgr_filename)
        
        with open(local_new_file_path, 'w', encoding='utf-8') as f:
            f.write(vince_content)
        
        if log_callback:
            log_callback(f"[OK] Created new rscmgr file: {local_new_file_path}")
        
        new_file_depot_path = construct_rscmgr_file_path(samsung_path, rscmgr_filename)
        
        cmd = f"p4 add -c {changelist_id} {new_file_depot_path}"
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        
        if result.returncode == 0:
            if log_callback:
                log_callback(f"[OK] File added to P4 and changelist {changelist_id}")
        else:
            if log_callback:
                log_callback(f"[WARNING] p4 add result: {result.stderr}")
        
        return new_file_depot_path
        
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Failed to create rscmgr file: {str(e)}")
        raise


def process_vince_reference(vince_workspace, log_callback=None):
    """
    Process VINCE workspace as reference branch (read-only)
    Returns: (rscmgr_filename, rscmgr_content) or (None, None) if no readahead feature
    """
    if log_callback:
        log_callback("\n[VINCE] ========== Processing VINCE (Reference Branch) ==========")
    
    try:
        # Find device_common.mk
        device_common_path, _ = find_device_common_mk_path(vince_workspace, log_callback)
        if not device_common_path:
            raise RuntimeError("Cannot find device_common.mk in VINCE workspace")
        
        if log_callback:
            log_callback(f"[VINCE] device_common.mk: {device_common_path}")
        
        # Map and sync
        map_single_depot(device_common_path, log_callback)
        sync_file_silent(device_common_path)
        
        # Check rscmgr reference
        rscmgr_filename = get_rscmgr_reference_from_device_common(device_common_path, log_callback)
        
        if not rscmgr_filename:
            if log_callback:
                log_callback("[WARNING] VINCE does not have readahead feature (rscmgr not found)")
            return None, None
        
        if log_callback:
            log_callback(f"[VINCE] rscmgr filename: {rscmgr_filename}")
        
        # Find samsung vendor path
        samsung_path = find_samsung_vendor_path_from_workspace(vince_workspace, log_callback) 
        if not samsung_path:
            raise RuntimeError("Cannot find samsung vendor path in VINCE")
        
        # Find rscmgr file
        rscmgr_path = construct_rscmgr_file_path(samsung_path, rscmgr_filename)
        
        if not validate_depot_path(rscmgr_path):
            raise RuntimeError(f"VINCE rscmgr file not found: {rscmgr_path}")
        
        if log_callback:
            log_callback(f"[VINCE] rscmgr path: {rscmgr_path}")
        
        # Map and sync
        map_single_depot(rscmgr_path, log_callback)
        sync_file_silent(rscmgr_path)
        
        # Read content
        rscmgr_content = read_rscmgr_content(rscmgr_path, log_callback)
        
        if log_callback:
            log_callback("[VINCE] ========== VINCE Processing Completed ==========")
        
        return rscmgr_filename, rscmgr_content
    
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Failed to process VINCE: {str(e)}")
        raise


def process_target_branch(branch_input, branch_name, vince_rscmgr_filename, 
                         vince_rscmgr_content, changelist_id, log_callback=None):
    """
    Process target branch (REL/FLUMEN/BENI)
    
    Args:
        branch_input: Can be:
            - String (workspace name) for first user-provided branch
            - Dict {'device_common_path', 'android_mk_path'} for cascaded branches
        branch_name: Branch category name (REL/FLUMEN/BENI)
        vince_rscmgr_filename: VINCE rscmgr filename (reference)
        vince_rscmgr_content: VINCE rscmgr content (reference)
        changelist_id: Current changelist ID
    
    Returns:
        Tuple: (updated_changelist_id, device_common_path, android_mk_path)
    """
    if log_callback:
        log_callback(f"\n[{branch_name}] ========== Processing {branch_name} ==========")
    
    current_changelist_id = changelist_id
    
    try:
        # ====================================================================
        # STEP 1: Get device_common.mk and Android.mk paths
        # ====================================================================
        if isinstance(branch_input, str):
            # User-provided workspace - find paths from workspace
            if log_callback:
                log_callback(f"[{branch_name}] Finding paths from workspace: {branch_input}")
            
            device_common_path, _ = find_device_common_mk_path(branch_input, log_callback)
            if not device_common_path:
                raise RuntimeError(f"Cannot find device_common.mk in {branch_name}")
            
            # Find samsung path
            samsung_path = find_samsung_vendor_path_from_workspace(branch_input, log_callback)
     
            if not samsung_path:
                raise RuntimeError(f"Cannot find samsung vendor path in {branch_name}")
            
            # Find Android.mk
            android_mk_path = find_android_mk_from_samsung_path(samsung_path, log_callback)
            if not android_mk_path:
                raise RuntimeError(f"Cannot find Android.mk in {branch_name}")
        
        else:
            # Cascaded branch - use provided paths from integration
            if log_callback:
                log_callback(f"[{branch_name}] Using integrated paths from previous branch")
            
            device_common_path = branch_input['device_common_path']
            android_mk_path = branch_input['android_mk_path']
            
            if log_callback:
                log_callback(f"[{branch_name}] device_common.mk: {device_common_path}")
                log_callback(f"[{branch_name}] Android.mk: {android_mk_path}")
        
        # ====================================================================
        # STEP 2: Process device_common.mk
        # ====================================================================
        if log_callback:
            log_callback(f"[{branch_name}] Processing device_common.mk...")
        
        map_single_depot(device_common_path, log_callback)
        sync_file_silent(device_common_path)
        
        existing_rscmgr = get_rscmgr_reference_from_device_common(device_common_path, log_callback)
        
        device_common_needs_update = False
        
        if existing_rscmgr:
            if existing_rscmgr != vince_rscmgr_filename:
                if log_callback:
                    log_callback(f"[DIFF] {branch_name} has different rscmgr: {existing_rscmgr} ≠ {vince_rscmgr_filename}")
                device_common_needs_update = True
            else:
                if log_callback:
                    log_callback(f"[OK] {branch_name} rscmgr reference matches VINCE")
        else:
            if log_callback:
                log_callback(f"[MISSING] {branch_name} has no rscmgr reference, will add")
            device_common_needs_update = True
        
        if device_common_needs_update:
            if not current_changelist_id:
                current_changelist_id = create_changelist_silent("System bringup - Update readahead feature")
                if log_callback:
                    log_callback(f"[CL] Created pending changelist: {current_changelist_id}")
            
            checkout_file_silent(device_common_path, current_changelist_id, log_callback)
            
            if existing_rscmgr:
                update_device_common_mk_rscmgr_reference(device_common_path, existing_rscmgr, 
                                                         vince_rscmgr_filename, log_callback)
            else:
                add_rscmgr_reference_to_device_common(device_common_path, vince_rscmgr_filename, log_callback)
        
        # ====================================================================
        # STEP 3: Process Android.mk
        # ====================================================================
        if log_callback:
            log_callback(f"[{branch_name}] Processing Android.mk...")
        
        map_single_depot(android_mk_path, log_callback)
        sync_file_silent(android_mk_path)
        
        module_exists = check_rscmgr_in_android_mk(android_mk_path, vince_rscmgr_filename, log_callback)
        
        if module_exists:
            if log_callback:
                log_callback(f"[OK] {branch_name} Android.mk already has rscmgr module")
        else:
            if log_callback:
                log_callback(f"[ADD] {branch_name} Android.mk missing rscmgr module, adding...")
            
            if not current_changelist_id:
                current_changelist_id = create_changelist_silent("System bringup - Update readahead feature")
                if log_callback:
                    log_callback(f"[CL] Created pending changelist: {current_changelist_id}")
            
            add_rscmgr_module_to_android_mk(android_mk_path, vince_rscmgr_filename, 
                                           current_changelist_id, log_callback)
        
        # ====================================================================
        # STEP 4: Process rscmgr.rc
        # ====================================================================
        if log_callback:
            log_callback(f"[{branch_name}] Processing rscmgr.rc...")
        
        # Extract samsung path from Android.mk
        samsung_path = re.search(r'^(.+/vendor/samsung/)', android_mk_path)
        if not samsung_path:
            raise RuntimeError(f"Cannot extract samsung path from Android.mk: {android_mk_path}")
        
        samsung_path = samsung_path.group(1)
        rscmgr_path = construct_rscmgr_file_path(samsung_path, vince_rscmgr_filename)
        
        if validate_depot_path(rscmgr_path):
            # File exists - copy VINCE content
            if log_callback:
                log_callback(f"[FOUND] {branch_name} rscmgr file exists, copying VINCE content...")
            
            map_single_depot(rscmgr_path, log_callback)
            sync_file_silent(rscmgr_path)
            
            if not current_changelist_id:
                current_changelist_id = create_changelist_silent("System bringup - Update readahead feature")
                if log_callback:
                    log_callback(f"[CL] Created pending changelist: {current_changelist_id}")
            
            checkout_file_silent(rscmgr_path, current_changelist_id, log_callback)
            write_rscmgr_content(rscmgr_path, vince_rscmgr_content, log_callback)
        
        else:
            # File doesn't exist - create new with VINCE content
            if log_callback:
                log_callback(f"[MISSING] {branch_name} rscmgr file not found, creating new...")
            
            if not current_changelist_id:
                current_changelist_id = create_changelist_silent("System bringup - Update readahead feature")
                if log_callback:
                    log_callback(f"[CL] Created pending changelist: {current_changelist_id}")
            
            rscmgr_path = create_rscmgr_file(samsung_path, vince_rscmgr_filename, 
                                            vince_rscmgr_content, current_changelist_id, log_callback)
        
        if log_callback:
            log_callback(f"[{branch_name}] ========== {branch_name} Completed ==========")
        
        return current_changelist_id, device_common_path, android_mk_path
    
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Failed to process {branch_name}: {str(e)}")
        raise


def run_system_process(beni_input, vince_input, flumen_input, rel_input,
                      log_callback, progress_callback=None, error_callback=None):
    """
    Execute complete system bringup process with integration cascading
    
    Flow:
    1. VINCE: Read reference data (device_common.mk, rscmgr.rc content)
    2. User-provided branch: Process from workspace
    3. Auto-resolved branches: Process via integration history
    
    Cascade order: VINCE → REL → FLUMEN → BENI
    """
    try:
        log_callback("[SYSTEM] Starting system bringup process with integration cascading...")
        log_callback("[SYSTEM] Files to process: device_common.mk, Android.mk, rscmgr.rc")
        
        # ============================================================================
        # STEP 1: VALIDATE VINCE INPUT
        # ============================================================================
        if not vince_input or not vince_input.strip():
            error_msg = "VINCE workspace is mandatory for system bringup"
            log_callback(f"[ERROR] {error_msg}")
            if error_callback:
                error_callback("Missing VINCE", error_msg)
            return
        
        vince_input = vince_input.strip()
        
        if not is_workspace_like(vince_input):
            error_msg = "VINCE input must be a workspace (TEMPLATE_*)"
            log_callback(f"[ERROR] {error_msg}")
            if error_callback:
                error_callback("Invalid VINCE", error_msg)
            return
        
        if progress_callback:
            progress_callback(10)
        
        # ============================================================================
        # STEP 2: PROCESS VINCE REFERENCE
        # ============================================================================
        log_callback("\n[SYSTEM] Processing VINCE reference branch...")
        
        try:
            vince_rscmgr_filename, vince_rscmgr_content = process_vince_reference(
                vince_input, log_callback
            )
        except Exception as e:
            error_msg = f"Failed to process VINCE: {str(e)}"
            log_callback(f"[ERROR] {error_msg}")
            if error_callback:
                error_callback("VINCE Processing Failed", error_msg)
            return
        
        if not vince_rscmgr_filename:
            error_msg = "VINCE does not have readahead feature (rscmgr*.rc not found in device_common.mk)"
            log_callback(f"[ERROR] {error_msg}")
            if error_callback:
                error_callback("No Readahead Feature", f"{error_msg}\n\nCannot proceed with system bringup.")
            return
        
        log_callback(f"[OK] VINCE reference data ready: {vince_rscmgr_filename}")
        
        if progress_callback:
            progress_callback(30)
        
        # ============================================================================
        # STEP 3: DETERMINE CASCADE ORDER
        # ============================================================================
        rel_input = rel_input.strip() if rel_input else ""
        flumen_input = flumen_input.strip() if flumen_input else ""
        beni_input = beni_input.strip() if beni_input else ""
        
        log_callback("\n[SYSTEM] Analyzing input branches...")
        log_callback(f"[INPUT] REL: {rel_input if rel_input else '(not provided)'}")
        log_callback(f"[INPUT] FLUMEN: {flumen_input if flumen_input else '(not provided)'}")
        log_callback(f"[INPUT] BENI: {beni_input if beni_input else '(not provided)'}")
        
        # Determine cascade order based on user input
        cascade_branches = []
        
        if rel_input:
            cascade_branches = [("REL", rel_input), ("FLUMEN", None), ("BENI", None)]
        elif flumen_input:
            cascade_branches = [("FLUMEN", flumen_input), ("BENI", None)]
        elif beni_input:
            cascade_branches = [("BENI", beni_input)]
        else:
            error_msg = "At least one target branch (REL, FLUMEN, or BENI) is required"
            log_callback(f"[ERROR] {error_msg}")
            if error_callback:
                error_callback("Missing Target Branch", error_msg)
            return
        
        cascade_order = [name for name, _ in cascade_branches]
        log_callback(f"[CASCADE] Processing order: {' → '.join(cascade_order)}")
        
        if progress_callback:
            progress_callback(40)
        
        # ============================================================================
        # STEP 4: PROCESS CASCADE
        # ============================================================================
        shared_changelist_id = None
        current_device_common_path = None
        current_android_mk_path = None
        
        progress_step = 60 / len(cascade_branches)
        current_progress = 40
        
        for idx, (branch_name, branch_workspace) in enumerate(cascade_branches):
            try:
                if idx == 0:
                    # First branch - use provided workspace
                    if not branch_workspace:
                        error_msg = f"{branch_name} workspace is required as starting point"
                        log_callback(f"[ERROR] {error_msg}")
                        if error_callback:
                            error_callback(f"Missing {branch_name}", error_msg)
                        return
                    
                    branch_input = branch_workspace
                    
                else:
                    # Cascaded branch - get paths from integration
                    if not current_device_common_path or not current_android_mk_path:
                        error_msg = f"Cannot cascade to {branch_name}: missing previous branch paths"
                        log_callback(f"[ERROR] {error_msg}")
                        if error_callback:
                            error_callback(f"Cascade Failed", error_msg)
                        return
                    
                    log_callback(f"\n[CASCADE] Finding {branch_name} paths from integration history...")
                    
                    # Get integration sources
                    integrated_device_common = get_integration_source_depot_path(
                        current_device_common_path, log_callback
                    )
                    integrated_android_mk = get_integration_source_depot_path(
                        current_android_mk_path, log_callback
                    )
                    
                    if not integrated_device_common or not integrated_android_mk:
                        error_msg = f"Cannot find integration paths for {branch_name}"
                        log_callback(f"[ERROR] {error_msg}")
                        
                        # Ask user if want to continue with remaining branches
                        from tkinter import messagebox
                        response = messagebox.askyesno(
                            "Integration Failed",
                            f"Cannot find integration history for {branch_name}.\n\n"
                            f"Continue with remaining branches?",
                        )
                        
                        if not response:
                            if error_callback:
                                error_callback("Integration Failed", error_msg)
                            return
                        else:
                            log_callback(f"[SKIP] Skipping {branch_name} as per user choice")
                            continue
                    
                    branch_input = {
                        'device_common_path': integrated_device_common,
                        'android_mk_path': integrated_android_mk
                    }
                
                # Process this branch
                shared_changelist_id, current_device_common_path, current_android_mk_path = process_target_branch(
                    branch_input, branch_name, vince_rscmgr_filename, 
                    vince_rscmgr_content, shared_changelist_id, log_callback
                )
                
                current_progress += progress_step
                if progress_callback:
                    progress_callback(int(current_progress))
            
            except Exception as e:
                log_callback(f"[ERROR] Failed to process {branch_name}: {str(e)}")
                
                from tkinter import messagebox
                response = messagebox.askyesno(
                    "Processing Error",
                    f"Error processing {branch_name}: {str(e)}\n\n"
                    f"Continue with remaining branches?",
                )
                
                if not response:
                    if error_callback:
                        error_callback(f"{branch_name} Processing Failed", str(e))
                    return
                else:
                    log_callback(f"[SKIP] Skipping {branch_name} as per user choice")
                    continue
        
        if progress_callback:
            progress_callback(100)
        
        # ============================================================================
        # STEP 5: SUMMARY
        # ============================================================================
        processed_branches = [name for name, _ in cascade_branches]
        
        log_callback(f"\n[SYSTEM] ========== SYSTEM BRINGUP COMPLETED ==========")
        log_callback(f"[SUMMARY] Reference branch: VINCE")
        log_callback(f"[SUMMARY] Master rscmgr file: {vince_rscmgr_filename}")
        log_callback(f"[SUMMARY] Processed target branches: {', '.join(processed_branches)}")
        log_callback(f"[SUMMARY] Cascade order: {' → '.join(processed_branches)}")
        log_callback(f"[SUMMARY] Files synchronized per branch:")
        log_callback(f"[SUMMARY]   1. device_common.mk - rscmgr reference updated")
        log_callback(f"[SUMMARY]   2. Android.mk - rscmgr module definition ensured")
        log_callback(f"[SUMMARY]   3. rscmgr.rc - content copied from VINCE")
        
        if shared_changelist_id:
            log_callback(f"[SUMMARY] All modifications in shared changelist: {shared_changelist_id}")
        else:
            log_callback(f"[SUMMARY] No modifications needed - all branches already in sync with VINCE")
        
        log_callback("[SYSTEM] ========== SUCCESS ==========")
    
    except Exception as e:
        log_callback(f"[ERROR] System bringup process failed: {str(e)}")
        if error_callback:
            error_callback("System Process Error", str(e))
        if progress_callback:
            progress_callback(0)
        raise