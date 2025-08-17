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

def run_bringup_process(beni_depot_path, vince_depot_path, flumen_depot_path, 
                       log_callback, progress_callback=None, error_callback=None):
    """Execute the complete bringup process"""
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
        
        if not process_beni and not process_flumen:
            error_msg = "Neither BENI nor FLUMEN paths are valid. At least one target path is required."
            log_callback(f"[ERROR] {error_msg}")
            if error_callback: 
                error_callback("No Valid Targets", error_msg)
            return
        
        # Get local paths
        vince_local = depot_to_local_path(vince_depot_path)
        beni_local = depot_to_local_path(beni_depot_path) if process_beni else None
        flumen_local = depot_to_local_path(flumen_depot_path) if process_flumen else None

        if progress_callback: 
            progress_callback(10)
            
        # Create changelist
        changelist_id = create_changelist(log_callback)
        
        if progress_callback: 
            progress_callback(20)
            
        # Map only valid paths
        if process_beni and process_flumen:
            map_client(beni_depot_path, vince_depot_path, flumen_depot_path, log_callback)
        elif process_beni:
            map_client_two_paths(beni_depot_path, vince_depot_path, log_callback)
        elif process_flumen:
            map_client_two_paths(flumen_depot_path, vince_depot_path, log_callback)
        
        if progress_callback: 
            progress_callback(35)
            
        # Sync valid files
        sync_file(vince_depot_path, log_callback)
        if process_beni:
            sync_file(beni_depot_path, log_callback)
        if process_flumen:
            sync_file(flumen_depot_path, log_callback)
        
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
        
        if progress_callback: 
            progress_callback(80)
            
        # Update valid target files
        if process_beni:
            update_lmkd_chimera(vince_local, beni_local, log_callback)
        if process_flumen:
            update_lmkd_chimera(vince_local, flumen_local, log_callback)
        
        if progress_callback: 
            progress_callback(100)
            
        # Summary
        processed_targets = []
        if process_beni: 
            processed_targets.append("BENI")
        if process_flumen: 
            processed_targets.append("FLUMEN")
        log_callback(f"[INFO] All steps completed successfully. Processed targets: {', '.join(processed_targets)}")
        
    except Exception as e:
        log_callback(f"[ERROR] {str(e)}")
        if error_callback: 
            error_callback("Process Error", str(e))
        if progress_callback: 
            progress_callback(0)