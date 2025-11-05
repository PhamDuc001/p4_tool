"""
Enhanced System process implementation
Handles the system bringup workflow for workspace-based operations with improved rscmgr handling
Enhanced to support mixed input (depot paths and workspaces)
Enhanced Samsung vendor path filtering with priority-based logic
FIXED: Now processes ALL auto-resolved targets, not just originally provided ones
NEW: Added Android.mk processing support with module definition management
"""

import os
import re
import subprocess
from P4 import P4, P4Exception
from core.p4_operations import (
    get_client_name, run_cmd, create_changelist_silent, 
    map_single_depot, sync_file_silent, checkout_file_silent,
    validate_device_common_mk_path, validate_depot_path,
    is_workspace_like, auto_resolve_missing_branches, find_device_common_mk_path
)
from config.p4_config import depot_to_local_path

def extract_model_from_rscmgr_filename(rscmgr_filename):
    """Extract model name from rscmgr filename"""
    # Extract model from rscmgr_mt6789.rc -> mt6789
    match = re.search(r'rscmgr_(.+)\.rc$', rscmgr_filename)
    if match:
        return match.group(1)
    return None

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


# Need check
#=============================
#=============================


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


def find_samsung_vendor_path_from_device_common(device_common_path, log_callback=None):
    """Construct samsung vendor path from device_common.mk path"""
    try:
        # Extract base path from device_common.mk path
        # Pattern: //depot/.../vendor/samsung/device/model_common/device_common.mk
        # Extract: //depot/.../vendor/samsung/
        match = re.search(r'^(.+/vendor/samsung/)', device_common_path)
        if match:
            samsung_path = match.group(1)
            if log_callback:
                log_callback(f"[CONSTRUCTED] Samsung vendor path: {samsung_path}")
            return samsung_path
        
        if log_callback:
            log_callback("[ERROR] Cannot extract samsung path from device_common.mk path")
        return None
    
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Error constructing samsung path: {str(e)}")
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

        # Checkout Android.mk
        checkout_file_silent(android_mk_path, changelist_id, log_callback)

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


def construct_rscmgr_file_path(samsung_path, rscmgr_filename, log_callback=None):
    """
    Construct rscmgr file path by appending system/rscmgr/{rscmgr_filename}
    """
    rscmgr_path = f"{samsung_path}system/rscmgr/{rscmgr_filename}"
    return rscmgr_path


def find_rscmgr_file_in_samsung_paths(samsung_paths, rscmgr_filename, log_callback=None):
    """
    Find rscmgr file in samsung vendor paths using new construction logic
    Returns the depot path to the rscmgr file if found
    """
    if log_callback:
        log_callback(f"[SYSTEM] Searching for {rscmgr_filename} in filtered samsung paths...")
    
    for samsung_path in samsung_paths:
        # Construct rscmgr file path
        rscmgr_path = construct_rscmgr_file_path(samsung_path, rscmgr_filename, log_callback)
        
        # Validate if file exists using p4 files command
        try:
            result = subprocess.run(
                f"p4 files {rscmgr_path}", 
                capture_output=True, 
                text=True, 
                shell=True
            )
            
            if result.returncode == 0 and "no such file" not in result.stderr.lower():
                if log_callback:
                    log_callback(f"[OK] Found rscmgr file: {rscmgr_path}")
                return rscmgr_path
                
        except Exception:
            continue
    
    if log_callback:
        log_callback(f"[WARNING] {rscmgr_filename} not found in any filtered samsung vendor paths")
    
    return None


def get_rscmgr_reference_from_device_common(device_common_path, log_callback=None):
    """
    Get rscmgr file reference from device_common.mk
    Returns the rscmgr filename if found, None otherwise
    """
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


def update_device_common_mk_rscmgr_reference(device_common_path, old_rscmgr_filename, new_rscmgr_filename, log_callback=None):
    """
    Update rscmgr file reference in device_common.mk
    """
    if log_callback:
        log_callback(f"[SYSTEM] Updating device_common.mk: {old_rscmgr_filename} → {new_rscmgr_filename}")
    
    try:
        local_path = depot_to_local_path(device_common_path)
        
        # Read current content
        with open(local_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace old rscmgr filename with new one
        updated_content = content.replace(old_rscmgr_filename, new_rscmgr_filename)
        
        # Write updated content
        with open(local_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        if log_callback:
            log_callback(f"[OK] Updated device_common.mk rscmgr reference")
            
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Failed to update device_common.mk: {str(e)}")
        raise


def add_rscmgr_reference_to_device_common(device_common_path, rscmgr_filename, log_callback=None):
    """
    Add rscmgr file reference to device_common.mk if not exists
    """
    if log_callback:
        log_callback(f"[SYSTEM] Adding rscmgr reference to device_common.mk: {rscmgr_filename}")
    
    try:
        local_path = depot_to_local_path(device_common_path)
        
        # Read current content
        with open(local_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Add rscmgr reference at the end
        lines.append('\n')  # Add empty line
        lines.append('# Rscmgr \n')
        lines.append('PRODUCT_PACKAGES += \\\n')
        lines.append(f'    {rscmgr_filename}\n')
        
        # Write updated content
        with open(local_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        if log_callback:
            log_callback(f"[OK] Added rscmgr reference to device_common.mk")
            
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Failed to add rscmgr reference: {str(e)}")
        raise


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
        
        # Read VINCE content
        vince_local = depot_to_local_path(vince_rscmgr_path)
        with open(vince_local, 'r', encoding='utf-8') as f:
            vince_content = f.read()
        
        # Create new file with VINCE content
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
        
        # Fallback: construct from device_common path
        if not samsung_path:
            if log_callback:
                log_callback("[FALLBACK] Constructing samsung path from device_common.mk path...")
            samsung_path = find_samsung_vendor_path_from_device_common(device_common_path, log_callback)
        
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
        existing_rscmgr = get_rscmgr_reference_from_device_common(device_common_path, log_callback)
        
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
        target_rscmgr_path = construct_rscmgr_file_path(samsung_path, vince_rscmgr_filename, log_callback)
        
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


def run_readahead_process(beni_input, vince_input, flumen_input, rel_input,
                      log_callback, progress_callback=None, error_callback=None):
    """
    ENHANCED: Execute system bringup process that processes ALL auto-resolved targets
    Now includes Android.mk processing with module definition management
    """
    try:
        # ============================================================================
        # STEP 1: VALIDATE AND AUTO-RESOLVE INPUTS
        # ============================================================================
        log_callback("[SYSTEM] Starting enhanced system bringup process with auto-resolve support...")
        log_callback("[SYSTEM] Will process: device_common.mk, Android.mk, rscmgr.rc")
        
        # Validate mandatory VINCE input
        if not vince_input:
            error_msg = "VINCE is mandatory for system bringup"
            log_callback(f"[ERROR] {error_msg}")
            if error_callback:
                error_callback("Missing VINCE", error_msg)
            return

        log_callback("[VALIDATION] Validating VINCE input...")
        try:
            vince_device_common_path = resolve_input_to_device_common_path(vince_input, log_callback)
        except Exception as e:
            error_msg = f"VINCE input validation failed: {str(e)}"
            log_callback(f"[ERROR] {error_msg}")
            if error_callback:
                error_callback("VINCE Validation Failed", error_msg)
            return

        if progress_callback:
            progress_callback(20)

        # ============================================================================
        # STEP 2: AUTO-RESOLVE MISSING BRANCHES
        # ============================================================================
        log_callback("\n[AUTO-RESOLVE] Attempting to auto-resolve missing branches...")
        
        try:
            resolved_beni, resolved_flumen, resolved_rel, resolved_vince = auto_resolve_missing_branches(
                vince_input, flumen_input, beni_input, rel_input, log_callback
            )
        except Exception as e:
            error_msg = f"Auto-resolve failed: {str(e)}"
            log_callback(f"[ERROR] {error_msg}")
            if error_callback:
                error_callback("Auto-resolve Failed", error_msg)
            return

        # Update final inputs with resolved values
        final_beni_input = resolved_beni if resolved_beni else beni_input
        final_vince_input = resolved_vince if resolved_vince else vince_input
        final_flumen_input = resolved_flumen if resolved_flumen else flumen_input
        final_rel_input = resolved_rel if resolved_rel else rel_input
        
        log_callback("[AUTO-RESOLVE] Final resolved inputs:")
        log_callback(f"[FINAL] VINCE: {final_vince_input}")
        log_callback(f"[FINAL] BENI: {final_beni_input if final_beni_input else '(not available)'}")
        log_callback(f"[FINAL] FLUMEN: {final_flumen_input if final_flumen_input else '(not available)'}")
        log_callback(f"[FINAL] REL: {final_rel_input if final_rel_input else '(not available)'}")

        if progress_callback:
            progress_callback(40)

        # ============================================================================
        # STEP 3: PROCESS VINCE INPUT (Master source)
        # ============================================================================
        log_callback("\n[SYSTEM] Processing VINCE input (master source)...")
        
        # Map and sync VINCE device_common.mk
        map_single_depot(vince_device_common_path, log_callback)
        sync_file_silent(vince_device_common_path)
        
        # Check readahead feature
        vince_rscmgr_filename = get_rscmgr_reference_from_device_common(vince_device_common_path, log_callback)
        if not vince_rscmgr_filename:
            error_msg = "VINCE does not have readahead feature (rscmgr*.rc not found)"
            log_callback(f"[ERROR] {error_msg}")
            if error_callback:
                error_callback("Feature Not Found", f"{error_msg}\nCannot proceed with system bringup.")
            return
        
        # Find VINCE rscmgr file
        vince_rscmgr_path = None
        
        # Try from workspace if input was workspace
        if is_workspace_like(final_vince_input):
            try:
                vince_samsung_path = find_samsung_vendor_path_from_workspace(final_vince_input, log_callback)
                if vince_samsung_path:
                    vince_rscmgr_path = construct_rscmgr_file_path(vince_samsung_path, vince_rscmgr_filename, log_callback)
                    if not validate_depot_path(vince_rscmgr_path):
                        vince_rscmgr_path = None
            except Exception as e:
                if log_callback:
                    log_callback(f"[WARNING] Workspace-based rscmgr search failed: {str(e)}")
        
        # Fallback: construct from device_common path
        if not vince_rscmgr_path:
            if log_callback:
                log_callback("[FALLBACK] Constructing VINCE rscmgr path from device_common.mk...")
            
            vince_samsung_path = find_samsung_vendor_path_from_device_common(vince_device_common_path, log_callback)
            if vince_samsung_path:
                vince_rscmgr_path = construct_rscmgr_file_path(vince_samsung_path, vince_rscmgr_filename, log_callback)
                
                # Validate constructed path
                if not validate_depot_path(vince_rscmgr_path):
                    vince_rscmgr_path = None
        
        if not vince_rscmgr_path:
            error_msg = f"VINCE {vince_rscmgr_filename} not found in vendor/samsung paths"
            log_callback(f"[ERROR] {error_msg}")
            if error_callback:
                error_callback("File Not Found", error_msg)
            return
        
        # Map and sync VINCE rscmgr file
        map_single_depot(vince_rscmgr_path, log_callback)
        sync_file_silent(vince_rscmgr_path)
        
        log_callback(f"[OK] VINCE processing completed. Master rscmgr file: {vince_rscmgr_filename}")

        if progress_callback:
            progress_callback(60)

        # ============================================================================
        # STEP 4: PROCESS ALL RESOLVED TARGETS
        # ============================================================================
        log_callback("\n[SYSTEM] Building target list from ALL resolved values...")
        
        # BUILD COMPLETE TARGET LIST from ALL resolved values
        all_resolved_targets = []
        
        # Add BENI (mandatory - must exist after auto-resolve or original input)
        if final_beni_input:
            all_resolved_targets.append(("BENI", final_beni_input))
        else:
            error_msg = "BENI is mandatory and could not be resolved"
            log_callback(f"[ERROR] {error_msg}")
            if error_callback:
                error_callback("Missing BENI", error_msg)
            return
        
        # Add FLUMEN if resolved or originally provided
        if final_flumen_input:
            all_resolved_targets.append(("FLUMEN", final_flumen_input))
        
        # Add REL if resolved or originally provided  
        if final_rel_input:
            all_resolved_targets.append(("REL", final_rel_input))
        
        log_callback(f"[TARGETS] Processing {len(all_resolved_targets)} resolved targets: {[cat for cat, _ in all_resolved_targets]}")
        
        # Process ALL resolved targets
        shared_changelist_id = None
        progress_step = 40 / len(all_resolved_targets) if all_resolved_targets else 0
        current_progress = 60
        
        for category, target_input in all_resolved_targets:
            log_callback(f"\n[SYSTEM] Processing {category} target (device_common.mk + Android.mk + rscmgr.rc)...")
            shared_changelist_id = process_target_workspace_enhanced(
                target_input, category, vince_rscmgr_filename, vince_rscmgr_path, 
                shared_changelist_id, log_callback
            )
            
            if progress_callback:
                current_progress += progress_step
                progress_callback(int(current_progress))
        
        if progress_callback:
            progress_callback(100)
        
        # ============================================================================
        # STEP 5: SUMMARY
        # ============================================================================
        processed_targets = [cat for cat, _ in all_resolved_targets]
        log_callback(f"\n[SYSTEM] Enhanced system bringup process completed successfully!")
        log_callback(f"[SUMMARY] Processed ALL resolved targets: {', '.join(processed_targets)}")
        log_callback(f"[SUMMARY] Master rscmgr file: {vince_rscmgr_filename}")
        log_callback(f"[SUMMARY] Files processed per target:")
        log_callback(f"[SUMMARY]   1. device_common.mk - rscmgr reference updated")
        log_callback(f"[SUMMARY]   2. Android.mk - rscmgr module definition ensured")
        log_callback(f"[SUMMARY]   3. rscmgr.rc - content synchronized with VINCE")
        
        if shared_changelist_id:
            log_callback(f"[SUMMARY] All modifications across {len(processed_targets)} targets are in shared changelist: {shared_changelist_id}")
        else:
            log_callback(f"[SUMMARY] No modifications were needed - all {len(processed_targets)} targets are already in sync")
        
    except Exception as e:
        log_callback(f"[ERROR] Enhanced system process failed: {str(e)}")
        if error_callback:
            error_callback("System Process Error", str(e))
        if progress_callback:
            progress_callback(0)