"""
Bringup process implementation
Main logic for the bringup workflow
Enhanced to support mixed input (depot paths and workspaces)
Updated logic: Compare properties first, then create changelist only when needed
"""
from core.p4_operations import (
    validate_depot_path,
    map_client_two_paths, checkout_file_silent,
    is_workspace_like, sync_file_silent, create_changelist_silent,
    find_device_common_mk_path
)
from core.file_operations import (
    validate_properties_exist, update_lmkd_chimera,
    compare_properties_between_files
)
from config.p4_config import depot_to_local_path

def map_client_four_paths(beni_depot, vince_depot, flumen_depot, rel_depot, log_callback):
    """Map four depots to client spec - WRAPPER for backward compatibility"""
    from core.p4_operations import _map_client_depots_core
    _map_client_depots_core([beni_depot, vince_depot, flumen_depot, rel_depot], log_callback)

def map_client_three_paths(depot1, vince_depot, depot2, log_callback):
    """Map three depots to client spec - WRAPPER for backward compatibility"""
    from core.p4_operations import _map_client_depots_core
    _map_client_depots_core([depot1, vince_depot, depot2], log_callback)

def resolve_vendor_input_to_depot_path(user_input, log_callback=None):
    """
    Resolve vendor input (depot path or workspace) to depot path
    For vendor, we need the actual depot path, not necessarily device_common.mk
    """
    user_input = user_input.strip()
    
    if not user_input:
        return ""
    
    # If it's already a depot path, validate and return
    if user_input.startswith("//"):
        if log_callback:
            log_callback(f"[VENDOR] Detected depot path: {user_input}")
        
        if validate_depot_path(user_input):
            if log_callback:
                log_callback(f"[OK] Valid depot path: {user_input}")
            return user_input
        else:
            raise RuntimeError(f"Depot path does not exist: {user_input}")
    
    # If it's a workspace, resolve to device_common.mk path
    elif is_workspace_like(user_input):
        if log_callback:
            log_callback(f"[VENDOR] Detected workspace: {user_input}")
        
        try:
            resolved_path, _ = find_device_common_mk_path(user_input)
            if log_callback:
                log_callback(f"[OK] Resolved workspace to device_common.mk: {resolved_path}")
            return resolved_path
        except Exception as e:
            raise RuntimeError(f"Workspace resolution failed: {str(e)}")
    
    else:
        raise RuntimeError(f"Input must be either depot path (//depot/...) or workspace (TEMPLATE_*): {user_input}")

def compare_target_with_vince(vince_local_path, target_local_path, target_name, log_callback):
    """
    Compare properties between VINCE and target file
    Returns True if files are different, False if identical
    """
    log_callback(f"[COMPARE] Comparing {target_name} properties with VINCE...")
    
    try:
        differences = compare_properties_between_files(vince_local_path, target_local_path)
        
        if differences is None:
            log_callback(f"[ERROR] Failed to compare properties between VINCE and {target_name}")
            return False  # Assume no difference if comparison fails
        
        if not differences:
            log_callback(f"[OK] {target_name} properties are identical to VINCE")
            return False  # No differences
        else:
            log_callback(f"[DIFF] {target_name} has {len(differences)} property differences:")
            for diff in differences[:3]:  # Show first 3 differences
                log_callback(f"  - {diff}")
            if len(differences) > 3:
                log_callback(f"  - ... and {len(differences) - 3} more differences")
            return True  # Has differences
            
    except Exception as e:
        log_callback(f"[ERROR] Error comparing {target_name} with VINCE: {str(e)}")
        return False  # Assume no difference if comparison fails

def run_bringup_process(beni_input, vince_input, flumen_input, rel_input,
                       log_callback, progress_callback=None, error_callback=None):
    """Execute the complete bringup process - Enhanced with new logic: compare first, then create changelist"""
    try:
        # ============================================================================
        # STEP 1: VALIDATE INPUTS
        # ============================================================================
        log_callback("[VALIDATION] Validating inputs...")
        
        # Validate VINCE input first (mandatory)
        try:
            vince_depot_path = resolve_vendor_input_to_depot_path(vince_input, log_callback)
        except Exception as e:
            error_msg = f"VINCE input validation failed: {str(e)}\nVINCE is mandatory for the operation."
            log_callback(f"[ERROR] {error_msg}")
            if error_callback: 
                error_callback("VINCE Validation Failed", error_msg)
            return
        
        if not vince_depot_path:
            error_msg = "VINCE is mandatory and must be depot path (//depot/...) or workspace (TEMPLATE_*)"
            log_callback(f"[ERROR] {error_msg}")
            if error_callback: 
                error_callback("VINCE Required", error_msg)
            return
        
        log_callback("[OK] VINCE input validated successfully.")
        
        # Check which optional inputs are provided and valid
        valid_targets = []  # List of tuples: (name, depot_path, local_path)
        
        if beni_input:
            try:
                beni_depot_path = resolve_vendor_input_to_depot_path(beni_input, log_callback)
                if beni_depot_path:
                    beni_local = depot_to_local_path(beni_depot_path)
                    valid_targets.append(("BENI", beni_depot_path, beni_local))
                    log_callback("[OK] BENI input validated successfully.")
            except Exception as e:
                log_callback(f"[WARNING] BENI input validation failed: {str(e)}. Skipping BENI processing.")
        else:
            log_callback("[INFO] BENI input not provided. Skipping BENI processing.")
            
        if flumen_input:
            try:
                flumen_depot_path = resolve_vendor_input_to_depot_path(flumen_input, log_callback)
                if flumen_depot_path:
                    flumen_local = depot_to_local_path(flumen_depot_path)
                    valid_targets.append(("FLUMEN", flumen_depot_path, flumen_local))
                    log_callback("[OK] FLUMEN input validated successfully.")
            except Exception as e:
                log_callback(f"[WARNING] FLUMEN input validation failed: {str(e)}. Skipping FLUMEN processing.")
        else:
            log_callback("[INFO] FLUMEN input not provided. Skipping FLUMEN processing.")
        
        if rel_input:
            try:
                rel_depot_path = resolve_vendor_input_to_depot_path(rel_input, log_callback)
                if rel_depot_path:
                    rel_local = depot_to_local_path(rel_depot_path)
                    valid_targets.append(("REL", rel_depot_path, rel_local))
                    log_callback("[OK] REL input validated successfully.")
            except Exception as e:
                log_callback(f"[WARNING] REL input validation failed: {str(e)}. Skipping REL processing.")
        else:
            log_callback("[INFO] REL input not provided. Skipping REL processing.")
        
        if not valid_targets:
            error_msg = "None of BENI, FLUMEN, or REL inputs are valid. At least one target input is required."
            log_callback(f"[ERROR] {error_msg}")
            if error_callback: 
                error_callback("No Valid Targets", error_msg)
            return
        
        # Get VINCE local path
        vince_local = depot_to_local_path(vince_depot_path)

        if progress_callback: 
            progress_callback(10)
        
        # ============================================================================
        # STEP 2: MAP ALL VALID PATHS
        # ============================================================================
        target_depot_paths = [target[1] for target in valid_targets]
        all_depot_paths = [vince_depot_path] + target_depot_paths
        
        # Choose appropriate mapping function based on number of paths
        if len(all_depot_paths) == 4:  # VINCE + 3 targets
            map_client_four_paths(target_depot_paths[0], vince_depot_path, 
                                target_depot_paths[1], target_depot_paths[2], log_callback)
        elif len(all_depot_paths) == 3:  # VINCE + 2 targets
            map_client_three_paths(target_depot_paths[0], vince_depot_path, 
                                 target_depot_paths[1], log_callback)
        elif len(all_depot_paths) == 2:  # VINCE + 1 target
            map_client_two_paths(target_depot_paths[0], vince_depot_path, log_callback)
        
        if progress_callback: 
            progress_callback(25)
        
        # ============================================================================
        # STEP 3: SYNC ALL FILES (NO CHECKOUT YET)
        # ============================================================================
        log_callback("[STEP 3] Syncing latest versions of all files...")
        
        # Sync VINCE first
        try:
            sync_file_silent(vince_depot_path)
            log_callback(f"[OK] Synced VINCE: {vince_depot_path}")
        except Exception as e:
            log_callback(f"[ERROR] Failed to sync VINCE: {str(e)}")
            if error_callback:
                error_callback("Sync Error", f"Failed to sync VINCE: {str(e)}")
            return
        
        # Sync all target files
        for target_name, target_depot, target_local in valid_targets:
            try:
                sync_file_silent(target_depot)
                log_callback(f"[OK] Synced {target_name}: {target_depot}")
            except Exception as e:
                log_callback(f"[ERROR] Failed to sync {target_name}: {str(e)}")
                # Continue with other files even if one fails
        
        if progress_callback: 
            progress_callback(40)
        
        # ============================================================================
        # STEP 4: VALIDATE PROPERTIES EXIST IN VINCE
        # ============================================================================
        log_callback("[VALIDATION] Checking if LMKD and Chimera properties exist in VINCE...")
        has_lmkd, has_chimera = validate_properties_exist(vince_local)
        if not has_lmkd and not has_chimera:
            error_msg = "VINCE file does not contain LMKD or Chimera properties"
            log_callback(f"[ERROR] {error_msg}")
            if error_callback: 
                error_callback("Properties Not Found", error_msg)
            return
        elif not has_lmkd:
            log_callback(f"[WARNING] VINCE file does not contain LMKD property")
        elif not has_chimera:
            log_callback(f"[WARNING] VINCE file does not contain Chimera property")
        else:
            log_callback("[OK] LMKD and Chimera properties found in VINCE file.")
        
        if progress_callback: 
            progress_callback(55)
        
        # ============================================================================
        # STEP 5: COMPARE PROPERTIES - NEW LOGIC
        # ============================================================================
        log_callback("[STEP 5] Comparing properties between VINCE and target files...")
        
        files_need_update = []  # List of tuples: (target_name, target_depot, target_local)
        
        for target_name, target_depot, target_local in valid_targets:
            # Check if target has properties to compare
            has_target_lmkd, has_target_chimera = validate_properties_exist(target_local)
            if not has_target_lmkd and not has_target_chimera:
                log_callback(f"[WARNING] {target_name} file does not contain LMKD or Chimera properties - will be updated")
                files_need_update.append((target_name, target_depot, target_local))
                continue
            
            # Compare properties
            has_differences = compare_target_with_vince(vince_local, target_local, target_name, log_callback)
            if has_differences:
                files_need_update.append((target_name, target_depot, target_local))
        
        if progress_callback: 
            progress_callback(70)
        
        # ============================================================================
        # STEP 6: HANDLE RESULTS BASED ON COMPARISON
        # ============================================================================
        if not files_need_update:
            # No files need update - show popup and complete
            success_msg = "All target files are already in sync with VINCE properties. No changes needed."
            log_callback(f"[SUCCESS] {success_msg}")
            
            if error_callback:
                error_callback("No Changes Needed", success_msg, is_info=True)
            
            if progress_callback: 
                progress_callback(100)
            
            log_callback(f"[INFO] Process completed successfully - no modifications required")
            return
        
        # ============================================================================
        # STEP 7: CREATE SHARED CHANGELIST AND UPDATE FILES
        # ============================================================================
        log_callback(f"[STEP 7] Found {len(files_need_update)} files that need updates: {', '.join([f[0] for f in files_need_update])}")
        
        # Create single changelist for all updates
        changelist_id = create_changelist_silent("Create Changelist for Bringup Process")
        
        if progress_callback: 
            progress_callback(80)
        
        # Checkout and update all files that need changes
        for target_name, target_depot, target_local in files_need_update:
            try:
                # Checkout file
                checkout_file_silent(target_depot, changelist_id, log_callback)
                
                # Update properties
                update_lmkd_chimera(vince_local, target_local, log_callback)
                
            except Exception as e:
                log_callback(f"[ERROR] Failed to update {target_name}: {str(e)}")
                # Continue with other files even if one fails
        
        if progress_callback: 
            progress_callback(100)
        
        # ============================================================================
        # STEP 8: SUMMARY
        # ============================================================================
        updated_targets = [f[0] for f in files_need_update]
        log_callback(f"[SUCCESS] Bringup process completed successfully!")
        log_callback(f"[SUMMARY] Updated targets: {', '.join(updated_targets)}")
        log_callback(f"[SUMMARY] All changes are in shared changelist: {changelist_id}")
        log_callback(f"[SUMMARY] Mixed input support: depot paths and workspaces accepted")
        
    except Exception as e:
        log_callback(f"[ERROR] {str(e)}")
        if error_callback: 
            error_callback("Process Error", str(e))
        if progress_callback: 
            progress_callback(0)
