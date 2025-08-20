"""
Enhanced System process implementation
Handles the system bringup workflow for workspace-based operations with improved rscmgr handling
Enhanced to support mixed input (depot paths and workspaces)
"""

import os
import re
import subprocess
from P4 import P4, P4Exception
from core.p4_operations import (
    get_client_name, run_cmd, create_changelist_silent, 
    map_single_depot, sync_file_silent, checkout_file_silent,
    validate_device_common_mk_path, resolve_workspace_to_device_common_path,
    is_workspace_like
)
from config.p4_config import depot_to_local_path
from processes.parse_process import validate_workspace_exists


def extract_model_from_rscmgr_filename(rscmgr_filename):
    """Extract model name from rscmgr filename"""
    # Extract model from rscmgr_mt6789.rc -> mt6789
    match = re.search(r'rscmgr_(.+)\.rc$', rscmgr_filename)
    if match:
        return match.group(1)
    return None


def find_device_common_mk_path(workspace_name, log_callback=None):
    """
    Find device_common.mk path from workspace using P4Python
    Returns the complete depot path to device_common.mk file and all view paths
    """
    if log_callback:
        log_callback(f"[SYSTEM] Searching device_common.mk in workspace: {workspace_name}")
    
    p4 = P4()
    try:
        p4.connect()
        
        # Get client spec information
        client_spec = p4.fetch_client(workspace_name)
        
        # Search in View mappings for device_common.mk pattern
        device_common_paths = []
        all_view_paths = []  # Store all paths for later use
        
        for view in client_spec.get('View', []):
            # Get depot path (left side of mapping)
            depot_path = view.split()[0] if isinstance(view, str) else view[0]
            all_view_paths.append(depot_path)
            
            # Look for device/*_common/ pattern
            if re.search(r'/device/[^/]+?_common/', depot_path):
                # Remove "..." and add "device_common.mk"
                clean_path = depot_path.rstrip('...')
                device_common_path = clean_path + "device_common.mk"
                device_common_paths.append(device_common_path)
        
        if log_callback:
            if device_common_paths:
                log_callback(f"[OK] Found device_common.mk path: {device_common_paths[0]}")
            else:
                log_callback("[WARNING] No device_common.mk path found in workspace")
        
        return device_common_paths[0] if device_common_paths else None, all_view_paths
        
    except P4Exception as e:
        error_msg = f"P4 Error: {str(e)}"
        if log_callback:
            log_callback(f"[ERROR] {error_msg}")
        raise RuntimeError(error_msg)
    finally:
        try:
            p4.disconnect()
        except:
            pass


def resolve_input_to_device_common_path(user_input, log_callback=None):
    """
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
        
        if log_callback:
            log_callback(f"[OK] Valid device_common.mk path: {user_input}")
        
        return user_input
    
    # If it's a workspace
    elif is_workspace_like(user_input):
        if log_callback:
            log_callback(f"[INPUT] Detected workspace: {user_input}")
        
        try:
            resolved_path = resolve_workspace_to_device_common_path(user_input)
            if log_callback:
                log_callback(f"[OK] Resolved workspace to: {resolved_path}")
            return resolved_path
        except Exception as e:
            raise RuntimeError(f"Workspace resolution failed: {str(e)}")
    
    else:
        raise RuntimeError(f"Input must be either device_common.mk depot path (//depot/...) or workspace (TEMPLATE_*): {user_input}")


def check_readahead_feature(device_common_path, log_callback=None):
    """
    Check if device_common.mk contains readahead feature (rscmgr.rc)
    Returns the rscmgr file name if found, None otherwise
    """
    if log_callback:
        log_callback(f"[SYSTEM] Checking readahead feature in: {device_common_path}")
    
    try:
        local_path = depot_to_local_path(device_common_path)
        
        with open(local_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for rscmgr.rc or rscmgr_{model}.rc pattern
        rscmgr_match = re.search(r'rscmgr(?:_\w+)?\.rc', content)
        
        if rscmgr_match:
            rscmgr_file = rscmgr_match.group(0)
            if log_callback:
                log_callback(f"[OK] Found readahead feature file: {rscmgr_file}")
            return rscmgr_file
        else:
            if log_callback:
                log_callback("[WARNING] No readahead feature found (rscmgr*.rc)")
            return None
            
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Error checking readahead feature: {str(e)}")
        return None


def find_filtered_samsung_vendor_paths(all_view_paths, log_callback=None):
    """
    Find vendor/samsung paths with specific prefixes: //PROD_VINCE, //MODEL, //BENI
    Returns list of matching depot paths
    """
    if log_callback:
        log_callback("[SYSTEM] Searching for filtered vendor/samsung paths...")
    
    samsung_paths = []
    valid_prefixes = ["//PROD_VINCE", "//MODEL", "//BENI", "//PROD_BENI", "//VINCE"]
    
    for path in all_view_paths:
        # Check if path starts with valid prefixes
        path_starts_with_valid_prefix = any(path.startswith(prefix) for prefix in valid_prefixes)
        
        if path_starts_with_valid_prefix and re.search(r'/vendor/samsung/', path):
            clean_path = path.rstrip('...')
            samsung_paths.append(clean_path)
    
    if log_callback:
        if samsung_paths:
            log_callback(f"[OK] Found {len(samsung_paths)} filtered vendor/samsung paths")
            for path in samsung_paths:
                log_callback(f"[RESULT] {path}")
        else:
            log_callback("[WARNING] No filtered vendor/samsung paths found")
    
    return samsung_paths


def construct_rscmgr_file_path(samsung_path, rscmgr_filename, log_callback=None):
    """
    Construct rscmgr file path by appending system/rscmgr/{rscmgr_filename}
    """
    rscmgr_path = f"{samsung_path}system/rscmgr/{rscmgr_filename}"
    if log_callback:
        log_callback(f"[CONSTRUCT] Built rscmgr path: {rscmgr_path}")
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


def create_rscmgr_file(samsung_path, rscmgr_filename, vince_rscmgr_path, log_callback=None):
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
        
        # Return depot path for the new file
        new_file_depot_path = construct_rscmgr_file_path(samsung_path, rscmgr_filename)
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
    Enhanced processing of target workspace/path (BENI, FLUMEN, or REL) with improved rscmgr handling
    Now supports both workspace and depot path input
    Returns updated changelist_id (may create new one if none provided)
    """
    if log_callback:
        log_callback(f"\n[SYSTEM] Processing {category} input: {workspace_or_path}")
    
    current_changelist_id = changelist_id
    
    try:
        # Resolve input to device_common.mk path
        device_common_path = resolve_input_to_device_common_path(workspace_or_path, log_callback)
        if not device_common_path:
            if log_callback:
                log_callback(f"[ERROR] Failed to resolve {category} input to device_common.mk")
            return current_changelist_id
        
        # Map and sync device_common.mk
        map_single_depot(device_common_path, log_callback)
        sync_file_silent(device_common_path)
        
        # Get all view paths - need to handle both workspace and depot path cases
        all_view_paths = []
        
        # If input was workspace, get view paths from workspace
        if is_workspace_like(workspace_or_path):
            try:
                _, all_view_paths = find_device_common_mk_path(workspace_or_path, log_callback)
            except Exception as e:
                if log_callback:
                    log_callback(f"[WARNING] Could not get view paths from workspace: {str(e)}")
                # For depot path input, we'll need to construct samsung paths differently
                all_view_paths = []
        
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
            checkout_file_silent(device_common_path, current_changelist_id)
            
            # Update or add rscmgr reference
            if existing_rscmgr:
                update_device_common_mk_rscmgr_reference(device_common_path, existing_rscmgr, vince_rscmgr_filename, log_callback)
            else:
                add_rscmgr_reference_to_device_common(device_common_path, vince_rscmgr_filename, log_callback)
        
        # Find filtered samsung vendor paths
        samsung_paths = find_filtered_samsung_vendor_paths(all_view_paths, log_callback)
        
        # If no samsung paths found from workspace (e.g., depot path input), try to construct from device_common path
        if not samsung_paths and device_common_path:
            if log_callback:
                log_callback("[FALLBACK] Attempting to construct samsung paths from device_common.mk path...")
            
            # Extract base path from device_common.mk path
            # e.g., //depot/vendor/samsung/... -> //depot/vendor/samsung/
            base_path_match = re.search(r'^(.+/vendor/samsung/)', device_common_path)
            if base_path_match:
                base_samsung_path = base_path_match.group(1)
                samsung_paths = [base_samsung_path]
                if log_callback:
                    log_callback(f"[FALLBACK] Constructed samsung path: {base_samsung_path}")
        
        # Find rscmgr file in samsung paths
        target_rscmgr_path = find_rscmgr_file_in_samsung_paths(samsung_paths, vince_rscmgr_filename, log_callback)
        
        if target_rscmgr_path:
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
                checkout_file_silent(target_rscmgr_path, current_changelist_id)
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
            
            # Find a samsung path to create the file
            if samsung_paths:
                samsung_path = samsung_paths[0]  # Use first available path
                
                # Create new rscmgr file
                new_rscmgr_path = create_rscmgr_file(samsung_path, vince_rscmgr_filename, vince_rscmgr_path, log_callback)
                
                # Add new file to P4 and changelist
                add_file_to_p4(new_rscmgr_path, current_changelist_id, log_callback)
            else:
                if log_callback:
                    log_callback(f"[WARNING] No filtered samsung paths found in {category}, cannot create rscmgr file")
        
        return current_changelist_id
        
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Failed to process {category} input: {str(e)}")
        return current_changelist_id


def run_system_process(beni_input, vince_input, flumen_input, rel_input,
                      log_callback, progress_callback=None, error_callback=None):
    """
    Execute the enhanced system bringup process for mixed input operations (workspace and depot paths)
    """
    try:
        # ============================================================================
        # STEP 1: VALIDATE INPUTS - ENHANCED FOR MIXED INPUT
        # ============================================================================
        log_callback("[SYSTEM] Starting enhanced system bringup process (mixed input support)...")
        
        # Validate mandatory VINCE input
        log_callback("[VALIDATION] Validating VINCE input...")
        try:
            vince_device_common_path = resolve_input_to_device_common_path(vince_input, log_callback)
        except Exception as e:
            error_msg = f"VINCE input validation failed: {str(e)}"
            log_callback(f"[ERROR] {error_msg}")
            if error_callback:
                error_callback("VINCE Validation Failed", error_msg)
            return
        
        # Validate mandatory BENI input
        log_callback("[VALIDATION] Validating BENI input...")
        try:
            beni_device_common_path = resolve_input_to_device_common_path(beni_input, log_callback)
        except Exception as e:
            error_msg = f"BENI input validation failed: {str(e)}"
            log_callback(f"[ERROR] {error_msg}")
            if error_callback:
                error_callback("BENI Validation Failed", error_msg)
            return
        
        # Validate optional inputs
        valid_targets = []
        if flumen_input:
            log_callback("[VALIDATION] Validating FLUMEN input...")
            try:
                flumen_device_common_path = resolve_input_to_device_common_path(flumen_input, log_callback)
                valid_targets.append(("FLUMEN", flumen_input))
                log_callback("[OK] FLUMEN input validated successfully")
            except Exception as e:
                log_callback(f"[WARNING] FLUMEN input validation failed: {str(e)}")
        
        if rel_input:
            log_callback("[VALIDATION] Validating REL input...")
            try:
                rel_device_common_path = resolve_input_to_device_common_path(rel_input, log_callback)
                valid_targets.append(("REL", rel_input))
                log_callback("[OK] REL input validated successfully")
            except Exception as e:
                log_callback(f"[WARNING] REL input validation failed: {str(e)}")

        if progress_callback:
            progress_callback(20)

        # ============================================================================
        # STEP 2: PROCESS VINCE INPUT (Master source) - ENHANCED FOR MIXED INPUT
        # ============================================================================
        log_callback("\n[SYSTEM] Processing VINCE input (master source)...")
        
        # Map and sync VINCE device_common.mk
        map_single_depot(vince_device_common_path, log_callback)
        sync_file_silent(vince_device_common_path)
        
        # Check readahead feature
        vince_rscmgr_filename = check_readahead_feature(vince_device_common_path, log_callback)
        if not vince_rscmgr_filename:
            error_msg = "VINCE does not have readahead feature (rscmgr*.rc not found)"
            log_callback(f"[ERROR] {error_msg}")
            if error_callback:
                error_callback("Feature Not Found", f"{error_msg}\nCannot proceed with system bringup.")
            return
        
        if progress_callback:
            progress_callback(40)
        
        # Find VINCE rscmgr file - need to handle both workspace and depot path input
        vince_rscmgr_path = None
        
        # If VINCE input was workspace, use workspace logic
        if is_workspace_like(vince_input):
            # Find filtered samsung vendor paths in VINCE
            try:
                _, vince_all_paths = find_device_common_mk_path(vince_input, log_callback)
                vince_samsung_paths = find_filtered_samsung_vendor_paths(vince_all_paths, log_callback)
                vince_rscmgr_path = find_rscmgr_file_in_samsung_paths(vince_samsung_paths, vince_rscmgr_filename, log_callback)
            except Exception as e:
                if log_callback:
                    log_callback(f"[WARNING] Workspace-based rscmgr search failed: {str(e)}")
        
        # If not found or depot path input, try path-based construction
        if not vince_rscmgr_path:
            if log_callback:
                log_callback("[FALLBACK] Attempting path-based rscmgr file construction...")
            
            # Extract base path from device_common.mk path and construct rscmgr path
            base_path_match = re.search(r'^(.+/vendor/samsung/)', vince_device_common_path)
            if base_path_match:
                base_samsung_path = base_path_match.group(1)
                vince_rscmgr_path = construct_rscmgr_file_path(base_samsung_path, vince_rscmgr_filename, log_callback)
                
                # Validate constructed path
                try:
                    result = subprocess.run(f"p4 files {vince_rscmgr_path}", capture_output=True, text=True, shell=True)
                    if result.returncode != 0 or "no such file" in result.stderr.lower():
                        vince_rscmgr_path = None
                except:
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
        # STEP 3: PROCESS TARGET INPUTS WITH ENHANCED MIXED INPUT LOGIC
        # ============================================================================
        shared_changelist_id = None  # Will be created when first needed
        
        # Process BENI input (Mandatory target) - ENHANCED FOR MIXED INPUT
        log_callback(f"\n[SYSTEM] Processing BENI input with enhanced mixed input logic...")
        shared_changelist_id = process_target_workspace_enhanced(
            beni_input, "BENI", vince_rscmgr_filename, vince_rscmgr_path, 
            shared_changelist_id, log_callback
        )

        if progress_callback:
            progress_callback(75)

        # Process optional target inputs - ENHANCED FOR MIXED INPUT
        for category, input_value in valid_targets:
            log_callback(f"\n[SYSTEM] Processing {category} input with enhanced mixed input logic...")
            shared_changelist_id = process_target_workspace_enhanced(
                input_value, category, vince_rscmgr_filename, vince_rscmgr_path, 
                shared_changelist_id, log_callback
            )

        if progress_callback:
            progress_callback(100)

        # ============================================================================
        # STEP 4: SUMMARY - ENHANCED
        # ============================================================================
        processed_targets = ["BENI"] + [cat for cat, _ in valid_targets]
        log_callback(f"\n[SYSTEM] Enhanced system bringup process completed successfully!")
        log_callback(f"[SUMMARY] Processed inputs: {', '.join(processed_targets)}")
        log_callback(f"[SUMMARY] Master rscmgr file: {vince_rscmgr_filename}")
        log_callback(f"[SUMMARY] Mixed input support: depot paths and workspaces accepted")
        
        if shared_changelist_id:
            log_callback(f"[SUMMARY] All modifications are in shared changelist: {shared_changelist_id}")
        else:
            log_callback(f"[SUMMARY] No modifications were needed - all targets are already in sync")
        
    except Exception as e:
        log_callback(f"[ERROR] Enhanced system process failed: {str(e)}")
        if error_callback:
            error_callback("System Process Error", str(e))
        if progress_callback:
            progress_callback(0)