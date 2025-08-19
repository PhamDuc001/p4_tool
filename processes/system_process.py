"""
Enhanced System process implementation
Handles the system bringup workflow for workspace-based operations with improved rscmgr handling
"""

import os
import re
import subprocess
from P4 import P4, P4Exception
from core.p4_operations import (
    get_client_name, run_cmd, create_changelist_silent, 
    map_single_depot, sync_file_silent, checkout_file_silent
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
    valid_prefixes = ["//PROD_VINCE", "//MODEL", "//BENI"]
    
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
        lines.append('#Rscmgr file\n')
        lines.append('Property add +/\n')
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


def process_target_workspace_enhanced(workspace_name, category, vince_rscmgr_filename, vince_rscmgr_path, 
                                    changelist_id, log_callback=None):
    """
    Enhanced processing of target workspace (BENI, FLUMEN, or REL) with improved rscmgr handling
    Returns updated changelist_id (may create new one if none provided)
    """
    if log_callback:
        log_callback(f"\n[SYSTEM] Processing {category} workspace: {workspace_name}")
    
    current_changelist_id = changelist_id
    
    try:
        # Find device_common.mk path
        device_common_path, all_view_paths = find_device_common_mk_path(workspace_name, log_callback)
        if not device_common_path:
            if log_callback:
                log_callback(f"[ERROR] No device_common.mk found in {category} workspace")
            return current_changelist_id
        
        # Map and sync device_common.mk
        map_single_depot(device_common_path, log_callback)
        sync_file_silent(device_common_path)
        
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
            log_callback(f"[ERROR] Failed to process {category} workspace: {str(e)}")
        return current_changelist_id


def run_system_process(beni_workspace, vince_workspace, flumen_workspace, rel_workspace,
                      log_callback, progress_callback=None, error_callback=None):
    """
    Execute the enhanced system bringup process for workspace-based operations
    """
    try:
        # ============================================================================
        # STEP 1: VALIDATE WORKSPACES
        # ============================================================================
        log_callback("[SYSTEM] Starting enhanced system bringup process...")
        
        # Validate mandatory workspaces
        log_callback("[VALIDATION] Validating VINCE workspace...")
        success, msg = validate_workspace_exists(vince_workspace)
        if not success:
            error_msg = f"VINCE workspace validation failed: {msg}"
            log_callback(f"[ERROR] {error_msg}")
            if error_callback:
                error_callback("Workspace Not Found", error_msg)
            return
        log_callback(f"[OK] {msg}")
        
        log_callback("[VALIDATION] Validating BENI workspace...")
        success, msg = validate_workspace_exists(beni_workspace)
        if not success:
            error_msg = f"BENI workspace validation failed: {msg}"
            log_callback(f"[ERROR] {error_msg}")
            if error_callback:
                error_callback("Workspace Not Found", error_msg)
            return
        log_callback(f"[OK] {msg}")
        
        # Validate optional workspaces
        valid_targets = []
        if flumen_workspace:
            log_callback("[VALIDATION] Validating FLUMEN workspace...")
            success, msg = validate_workspace_exists(flumen_workspace)
            if success:
                log_callback(f"[OK] {msg}")
                valid_targets.append(("FLUMEN", flumen_workspace))
            else:
                log_callback(f"[WARNING] FLUMEN workspace validation failed: {msg}")
        
        if rel_workspace:
            log_callback("[VALIDATION] Validating REL workspace...")
            success, msg = validate_workspace_exists(rel_workspace)
            if success:
                log_callback(f"[OK] {msg}")
                valid_targets.append(("REL", rel_workspace))
            else:
                log_callback(f"[WARNING] REL workspace validation failed: {msg}")

        if progress_callback:
            progress_callback(20)

        # ============================================================================
        # STEP 2: PROCESS VINCE WORKSPACE (Master source) - ENHANCED
        # ============================================================================
        log_callback("\n[SYSTEM] Processing VINCE workspace (master source)...")
        
        # Find device_common.mk path in VINCE
        vince_device_common_path, vince_all_paths = find_device_common_mk_path(vince_workspace, log_callback)
        if not vince_device_common_path:
            error_msg = "No device_common.mk found in VINCE workspace"
            log_callback(f"[ERROR] {error_msg}")
            if error_callback:
                error_callback("File Not Found", error_msg)
            return
        
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
        
        # Find filtered samsung vendor paths in VINCE (ENHANCED)
        vince_samsung_paths = find_filtered_samsung_vendor_paths(vince_all_paths, log_callback)
        
        # Find VINCE rscmgr file using enhanced logic
        vince_rscmgr_path = find_rscmgr_file_in_samsung_paths(vince_samsung_paths, vince_rscmgr_filename, log_callback)
        if not vince_rscmgr_path:
            error_msg = f"VINCE {vince_rscmgr_filename} not found in filtered samsung vendor paths"
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
        # STEP 3: PROCESS TARGET WORKSPACES WITH ENHANCED LOGIC
        # ============================================================================
        shared_changelist_id = None  # Will be created when first needed
        
        # Process BENI workspace (Mandatory target) - ENHANCED
        log_callback(f"\n[SYSTEM] Processing BENI workspace with enhanced logic...")
        shared_changelist_id = process_target_workspace_enhanced(
            beni_workspace, "BENI", vince_rscmgr_filename, vince_rscmgr_path, 
            shared_changelist_id, log_callback
        )

        if progress_callback:
            progress_callback(75)

        # Process optional target workspaces - ENHANCED
        for category, workspace in valid_targets:
            log_callback(f"\n[SYSTEM] Processing {category} workspace with enhanced logic...")
            shared_changelist_id = process_target_workspace_enhanced(
                workspace, category, vince_rscmgr_filename, vince_rscmgr_path, 
                shared_changelist_id, log_callback
            )

        if progress_callback:
            progress_callback(100)

        # ============================================================================
        # STEP 4: SUMMARY - ENHANCED
        # ============================================================================
        processed_targets = ["BENI"] + [cat for cat, _ in valid_targets]
        log_callback(f"\n[SYSTEM] Enhanced system bringup process completed successfully!")
        log_callback(f"[SUMMARY] Processed workspaces: {', '.join(processed_targets)}")
        log_callback(f"[SUMMARY] Master rscmgr file: {vince_rscmgr_filename}")
        
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