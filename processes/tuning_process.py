"""
Enhanced Tuning process implementation with Delete Property support
Handles property loading, modification, and applying changes (including deletions) to files
"""
import re
from core.p4_operations import (
    validate_depot_path, map_single_depot, map_two_depots_silent, 
    sync_file_silent, create_changelist_silent, checkout_file_silent
)
from core.file_operations import (
    update_properties_in_file, create_backup, extract_properties_from_file
)
from config.p4_config import depot_to_local_path

def load_properties_for_tuning(beni_depot_path, flumen_depot_path, 
                              progress_callback=None, error_callback=None, info_callback=None):
    """Load and compare properties from BENI and FLUMEN files"""
    try:
        # Validate paths first
        process_beni = False
        process_flumen = False
        
        if beni_depot_path and beni_depot_path.startswith("//"):
            if validate_depot_path(beni_depot_path):
                process_beni = True
            else:
                if error_callback:
                    error_callback("Path Not Found", f"BENI depot path does not exist: {beni_depot_path}")
                return None
        
        if flumen_depot_path and flumen_depot_path.startswith("//"):
            if validate_depot_path(flumen_depot_path):
                process_flumen = True
            else:
                if error_callback:
                    error_callback("Path Not Found", f"FLUMEN depot path does not exist: {flumen_depot_path}")
                return None
        
        if not process_beni and not process_flumen:
            if error_callback:
                error_callback("No Valid Paths", "At least one valid depot path is required.")
            return None
        
        if progress_callback:
            progress_callback(20)
        
        # Map and sync files
        if process_beni and process_flumen:
            map_two_depots_silent(beni_depot_path, flumen_depot_path)
            sync_file_silent(beni_depot_path)
            sync_file_silent(flumen_depot_path)
        elif process_beni:
            map_single_depot(beni_depot_path)
            sync_file_silent(beni_depot_path)
        elif process_flumen:
            map_single_depot(flumen_depot_path)
            sync_file_silent(flumen_depot_path)
        
        if progress_callback:
            progress_callback(60)
        
        # Get local paths and extract properties
        properties_data = {}
        depot_paths = {}  # Store depot paths for later use
        
        if process_beni:
            beni_local = depot_to_local_path(beni_depot_path)
            beni_properties = extract_properties_from_file(beni_local)
            if not beni_properties:
                if error_callback:
                    error_callback("Properties Not Found", "BENI file does not contain LMKD or Chimera properties")
                return None
            properties_data["BENI"] = beni_properties
            depot_paths["BENI"] = beni_depot_path
        
        if process_flumen:
            flumen_local = depot_to_local_path(flumen_depot_path)
            flumen_properties = extract_properties_from_file(flumen_local)
            if not flumen_properties:
                if error_callback:
                    error_callback("Properties Not Found", "FLUMEN file does not contain LMKD or Chimera properties")
                return None
            properties_data["FLUMEN"] = flumen_properties
            depot_paths["FLUMEN"] = flumen_depot_path
        
        if progress_callback:
            progress_callback(80)
        
        # Compare properties if both files exist
        if process_beni and process_flumen:
            differences = compare_properties(properties_data["BENI"], properties_data["FLUMEN"])
            if differences:
                diff_message = "Properties differ between BENI and FLUMEN:\n\n" + "\n".join(differences)
                if info_callback:
                    info_callback("Properties Comparison", diff_message)
        
        # Return the properties from the first available file for editing
        result_properties = properties_data.get("BENI", properties_data.get("FLUMEN", {}))
        
        # Add metadata for apply functionality
        result_properties["_metadata"] = {
            "depot_paths": depot_paths,
            "original_properties": result_properties.copy()
        }
        
        if progress_callback:
            progress_callback(100)
        
        return result_properties
        
    except Exception as e:
        if error_callback:
            error_callback("Load Properties Error", str(e))
        return None

def apply_tuning_changes(current_properties, original_depot_paths, 
                        log_callback, progress_callback=None, error_callback=None):
    """Apply property changes to target files including deletions"""
    try:
        # Remove metadata if present
        properties_to_apply = {}
        for key, value in current_properties.items():
            if key != "_metadata":
                properties_to_apply[key] = value
        
        log_callback("[TUNING] Starting apply tuning changes process (including deletions)...")
        
        # Count properties for logging
        total_lmkd = len(properties_to_apply.get("LMKD", {}))
        total_chimera = len(properties_to_apply.get("Chimera", {}))
        log_callback(f"[INFO] Properties to apply: LMKD={total_lmkd}, Chimera={total_chimera}")
        
        if progress_callback:
            progress_callback(10)
        
        # Create changelist for modifications
        log_callback("[STEP 1] Creating pending changelist for tuning changes...")
        changelist_id = create_changelist_silent("Tuning - Apply property changes (including deletions)")
        log_callback(f"[OK] Created changelist {changelist_id}")
        
        if progress_callback:
            progress_callback(20)
        
        # Process each target file
        processed_files = []
        for target_name, depot_path in original_depot_paths.items():
            try:
                log_callback(f"[STEP 2] Processing {target_name} file...")
                
                # Map and sync latest version
                map_single_depot(depot_path)
                sync_file_silent(depot_path)
                log_callback(f"[OK] Synced latest version of {target_name}")
                
                if progress_callback:
                    progress_callback(30 + len(processed_files) * 30)
                
                # Checkout for editing
                checkout_file_silent(depot_path, changelist_id)
                log_callback(f"[OK] Checked out {target_name} for editing")
                
                # Get local path and apply changes
                local_path = depot_to_local_path(depot_path)
                
                # Log what will be applied (for debugging)
                log_callback(f"[DEBUG] Applying properties to {target_name}:")
                for category, props in properties_to_apply.items():
                    if props:
                        log_callback(f"[DEBUG]   {category}: {len(props)} properties")
                        for key in props.keys():
                            log_callback(f"[DEBUG]     - {key}")
                
                success, error_msg = update_properties_in_file(local_path, properties_to_apply)
                
                if success:
                    log_callback(f"[OK] Applied tuning changes to {target_name}.")
                    processed_files.append(target_name)
                else:
                    log_callback(f"[ERROR] Failed to apply changes to {target_name}: {error_msg}")
                    if error_callback:
                        error_callback("Apply Error", f"Failed to apply changes to {target_name}: {error_msg}")
                    return False
                
            except Exception as e:
                log_callback(f"[ERROR] Error processing {target_name}: {str(e)}")
                if error_callback:
                    error_callback("Processing Error", f"Error processing {target_name}: {str(e)}")
                return False
        
        if progress_callback:
            progress_callback(100)
        
        log_callback(f"[SUCCESS] Tuning changes applied successfully to: {', '.join(processed_files)}")
        log_callback(f"[INFO] Changelist {changelist_id} contains all modifications")
        log_callback(f"[INFO] Properties have been added, modified, and deleted as requested")
        
        return True
        
    except Exception as e:
        log_callback(f"[ERROR] Apply tuning changes failed: {str(e)}")
        if error_callback:
            error_callback("Apply Tuning Error", str(e))
        return False

def extract_properties_from_file(file_path):
    """Extract LMKD and Chimera properties from file"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        properties = {"LMKD": {}, "Chimera": {}}
        
        # Extract LMKD properties
        lmkd_block = extract_block(lines, "# LMKD property", ["# Chimera property", "# DHA property"])
        if not lmkd_block:
            lmkd_block = extract_block(lines, "# DHA property", ["# Chimera property"])
        
        if lmkd_block:
            lmkd_props = parse_properties_block(lmkd_block)
            properties["LMKD"] = lmkd_props
        
        # Extract Chimera properties
        chimera_block = extract_block(lines, "# Chimera property", ["# Nandswap", "#", ""])
        if chimera_block:
            chimera_props = parse_properties_block(chimera_block)
            properties["Chimera"] = chimera_props
        
        # Return None if no properties found
        if not properties["LMKD"] and not properties["Chimera"]:
            return None
        
        return properties
        
    except Exception:
        return None

def extract_block(lines, start_header, next_header_list):
    """Extract block of lines between headers"""
    start = end = None
    for idx, line in enumerate(lines):
        if line.strip() == start_header:
            start = idx
            break
    if start is None:
        return []

    for idx in range(start + 1, len(lines)):
        if lines[idx].strip() in next_header_list:
            end = idx
            break
    if end is None:
        end = len(lines)
    return lines[start:end]

def parse_properties_block(block_lines):
    """Parse property block and extract key-value pairs"""
    properties = {}
    
    for line in block_lines:
        line = line.strip()
        # Skip comments and empty lines  
        if not line or line.startswith("#"):
            continue
        
        # Skip PRODUCT_PROPERTY_OVERRIDES lines
        if "PRODUCT_PROPERTY_OVERRIDES" in line:
            continue
        
        # Look for property=value pattern
        if "=" in line:
            # Remove backslash if present
            clean_line = line.rstrip(" \\")
            
            key, value = clean_line.split("=", 1)
            key = key.strip()
            value = value.strip()
            
            # Remove any trailing comments
            if "#" in value:
                value = value.split("#")[0].strip()
            
            properties[key] = value
    
    return properties

def compare_properties(beni_props, flumen_props):
    """Compare properties between BENI and FLUMEN files"""
    differences = []
    
    # Compare LMKD properties
    beni_lmkd = beni_props.get("LMKD", {})
    flumen_lmkd = flumen_props.get("LMKD", {})
    
    lmkd_diffs = compare_property_dict(beni_lmkd, flumen_lmkd, "LMKD")
    differences.extend(lmkd_diffs)
    
    # Compare Chimera properties
    beni_chimera = beni_props.get("Chimera", {})
    flumen_chimera = flumen_props.get("Chimera", {})
    
    chimera_diffs = compare_property_dict(beni_chimera, flumen_chimera, "Chimera")
    differences.extend(chimera_diffs)
    
    return differences

def compare_property_dict(dict1, dict2, category):
    """Compare two property dictionaries"""
    differences = []
    
    all_keys = set(dict1.keys()) | set(dict2.keys())
    
    for key in all_keys:
        val1 = dict1.get(key, "<missing>")
        val2 = dict2.get(key, "<missing>")
        
        if val1 != val2:
            differences.append(f"{category}.{key}: BENI='{val1}' vs FLUMEN='{val2}'")
    
    return differences