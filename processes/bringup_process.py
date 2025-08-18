"""
Bringup process implementation
Main logic for the bringup workflow
"""
from core.p4_operations import (
    validate_depot_path, create_changelist, map_client, 
    map_client_two_paths, sync_file, checkout_file
)
from core.file_operations import validate_properties_exist, update_lmkd_chimera
from config.p4_config import depot_to_local_path

def map_client_four_paths(beni_depot, vince_depot, flumen_depot, rel_depot, log_callback):
    """Map four depots to client spec"""
    from core.p4_operations import get_client_name, run_cmd
    client_name = get_client_name()
    if not client_name:
        raise RuntimeError("Client name not initialized. Please check P4 configuration.")
    
    log_callback("[STEP 2] Mapping BENI, VINCE, FLUMEN and REL to client spec...")
    client_spec = run_cmd("p4 client -o")
    lines = client_spec.splitlines()
    new_lines = []
    for line in lines:
        if beni_depot in line or vince_depot in line or flumen_depot in line or rel_depot in line:
            continue
        new_lines.append(line)
    new_lines.append(f"\t{beni_depot}\t//{client_name}/{beni_depot[2:]}")
    new_lines.append(f"\t{vince_depot}\t//{client_name}/{vince_depot[2:]}")
    new_lines.append(f"\t{flumen_depot}\t//{client_name}/{flumen_depot[2:]}")
    new_lines.append(f"\t{rel_depot}\t//{client_name}/{rel_depot[2:]}")
    new_spec = "\n".join(new_lines)
    run_cmd("p4 client -i", input_text=new_spec)
    log_callback("[OK] Mapping completed.")

def map_client_three_paths(depot1, vince_depot, depot2, log_callback):
    """Map three depots to client spec"""
    from core.p4_operations import get_client_name, run_cmd
    client_name = get_client_name()
    if not client_name:
        raise RuntimeError("Client name not initialized. Please check P4 configuration.")
    
    depot1_name = "BENI" if "beni" in depot1.lower() else "FLUMEN" if "flumen" in depot1.lower() else "REL" if "rel" in depot1.lower() else "DEPOT1"
    depot2_name = "BENI" if "beni" in depot2.lower() else "FLUMEN" if "flumen" in depot2.lower() else "REL" if "rel" in depot2.lower() else "DEPOT2"
    
    log_callback(f"[STEP 2] Mapping {depot1_name}, VINCE and {depot2_name} to client spec...")
    client_spec = run_cmd("p4 client -o")
    lines = client_spec.splitlines()
    new_lines = []
    for line in lines:
        if depot1 in line or vince_depot in line or depot2 in line:
            continue
        new_lines.append(line)
    new_lines.append(f"\t{depot1}\t//{client_name}/{depot1[2:]}")
    new_lines.append(f"\t{vince_depot}\t//{client_name}/{vince_depot[2:]}")
    new_lines.append(f"\t{depot2}\t//{client_name}/{depot2[2:]}")
    new_spec = "\n".join(new_lines)
    run_cmd("p4 client -i", input_text=new_spec)
    log_callback("[OK] Mapping completed.")

def run_bringup_process(beni_depot_path, vince_depot_path, flumen_depot_path, rel_depot_path,
                       log_callback, progress_callback=None, error_callback=None):
    """Execute the complete bringup process - Enhanced to support REL path"""
    try:
        # Validate VINCE path first (mandatory)
        log_callback("[VALIDATION] Checking if VINCE depot path exists...")
        if not validate_depot_path(vince_depot_path):
            error_msg = f"VINCE depot path does not exist: {vince_depot_path}\nVINCE path is mandatory for the operation."
            log_callback(f"[ERROR] {error_msg}")
            if error_callback: 
                error_callback("Path Not Found", error_msg)
            return
        
        log_callback("[OK] VINCE depot path validated successfully.")
        
        # Check which optional paths are provided and valid
        valid_paths = [vince_depot_path]  # VINCE is always included
        process_beni = False
        process_flumen = False
        process_rel = False  # NEW
        
        if beni_depot_path and beni_depot_path.startswith("//"):
            if validate_depot_path(beni_depot_path):
                valid_paths.append(beni_depot_path)
                process_beni = True
                log_callback("[OK] BENI depot path validated successfully.")
            else:
                log_callback(f"[WARNING] BENI depot path does not exist: {beni_depot_path}. Skipping BENI processing.")
        else:
            log_callback("[INFO] BENI depot path not provided. Skipping BENI processing.")
            
        if flumen_depot_path and flumen_depot_path.startswith("//"):
            if validate_depot_path(flumen_depot_path):
                valid_paths.append(flumen_depot_path)
                process_flumen = True
                log_callback("[OK] FLUMEN depot path validated successfully.")
            else:
                log_callback(f"[WARNING] FLUMEN depot path does not exist: {flumen_depot_path}. Skipping FLUMEN processing.")
        else:
            log_callback("[INFO] FLUMEN depot path not provided. Skipping FLUMEN processing.")
        
        # NEW: REL path validation
        if rel_depot_path and rel_depot_path.startswith("//"):
            if validate_depot_path(rel_depot_path):
                valid_paths.append(rel_depot_path)
                process_rel = True
                log_callback("[OK] REL depot path validated successfully.")
            else:
                log_callback(f"[WARNING] REL depot path does not exist: {rel_depot_path}. Skipping REL processing.")
        else:
            log_callback("[INFO] REL depot path not provided. Skipping REL processing.")
        
        if not process_beni and not process_flumen and not process_rel:  # Updated condition
            error_msg = "None of BENI, FLUMEN, or REL paths are valid. At least one target path is required."
            log_callback(f"[ERROR] {error_msg}")
            if error_callback: 
                error_callback("No Valid Targets", error_msg)
            return
        
        # Get local paths
        vince_local = depot_to_local_path(vince_depot_path)
        beni_local = depot_to_local_path(beni_depot_path) if process_beni else None
        flumen_local = depot_to_local_path(flumen_depot_path) if process_flumen else None
        rel_local = depot_to_local_path(rel_depot_path) if process_rel else None  # NEW

        if progress_callback: 
            progress_callback(10)
            
        # Create changelist
        changelist_id = create_changelist(log_callback)
        
        if progress_callback: 
            progress_callback(20)
            
        # Map valid paths - Enhanced logic for 4 paths
        valid_target_paths = []
        if process_beni:
            valid_target_paths.append(beni_depot_path)
        if process_flumen:
            valid_target_paths.append(flumen_depot_path)
        if process_rel:
            valid_target_paths.append(rel_depot_path)
        
        # Choose appropriate mapping function based on number of target paths
        if len(valid_target_paths) == 3:
            # All three target paths are valid
            map_client_four_paths(beni_depot_path, vince_depot_path, flumen_depot_path, rel_depot_path, log_callback)
        elif len(valid_target_paths) == 2:
            # Two target paths are valid
            map_client_three_paths(valid_target_paths[0], vince_depot_path, valid_target_paths[1], log_callback)
        elif len(valid_target_paths) == 1:
            # One target path is valid
            map_client_two_paths(valid_target_paths[0], vince_depot_path, log_callback)
        
        if progress_callback: 
            progress_callback(35)
            
        # Sync valid files
        sync_file(vince_depot_path, log_callback)
        if process_beni:
            sync_file(beni_depot_path, log_callback)
        if process_flumen:
            sync_file(flumen_depot_path, log_callback)
        if process_rel:  # NEW
            sync_file(rel_depot_path, log_callback)
        
        # Validate properties exist after sync
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
            progress_callback(60)
            
        # Checkout valid target files
        if process_beni:
            checkout_file(beni_depot_path, changelist_id, log_callback)
        if process_flumen:
            checkout_file(flumen_depot_path, changelist_id, log_callback)
        if process_rel:  # NEW
            checkout_file(rel_depot_path, changelist_id, log_callback)
        
        if progress_callback: 
            progress_callback(80)
            
        # Update valid target files
        if process_beni:
            update_lmkd_chimera(vince_local, beni_local, log_callback)
        if process_flumen:
            update_lmkd_chimera(vince_local, flumen_local, log_callback)
        if process_rel:  # NEW
            update_lmkd_chimera(vince_local, rel_local, log_callback)
        
        if progress_callback: 
            progress_callback(100)
            
        # Summary - Updated to include REL
        processed_targets = []
        if process_beni: 
            processed_targets.append("BENI")
        if process_flumen: 
            processed_targets.append("FLUMEN")
        if process_rel:  # NEW
            processed_targets.append("REL")
        log_callback(f"[INFO] All steps completed successfully. Processed targets: {', '.join(processed_targets)}")
        
    except Exception as e:
        log_callback(f"[ERROR] {str(e)}")
        if error_callback: 
            error_callback("Process Error", str(e))
        if progress_callback: 
            progress_callback(0)