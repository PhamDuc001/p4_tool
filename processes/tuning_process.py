"""
Enhanced Tuning process implementation with 3-path support (BENI, FLUMEN, REL)
Handles property loading, comparison, and applying changes to all 3 paths
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

def map_three_depots_silent(depot1, depot2, depot3):
    """Map three depots to client spec without logging"""
    from core.p4_operations import get_client_name, run_cmd
    client_name = get_client_name()
    if not client_name:
        raise RuntimeError("Client name not initialized. Please check P4 configuration.")
    
    client_spec = run_cmd("p4 client -o")
    lines = client_spec.splitlines()
    new_lines = []
    for line in lines:
        if depot1 in line or depot2 in line or depot3 in line:
            continue
        new_lines.append(line)
    new_lines.append(f"\t{depot1}\t//{client_name}/{depot1[2:]}")
    new_lines.append(f"\t{depot2}\t//{client_name}/{depot2[2:]}")
    new_lines.append(f"\t{depot3}\t//{client_name}/{depot3[2:]}")
    new_spec = "\n".join(new_lines)
    run_cmd("p4 client -i", input_text=new_spec)

def load_properties_for_tuning_enhanced(beni_depot_path, flumen_depot_path, rel_depot_path,
                                       progress_callback=None, error_callback=None, info_callback=None):
    """Load and compare properties from BENI, FLUMEN, and REL files"""
    try:
        # Validate paths first
        paths_to_process = {}
        
        if beni_depot_path and beni_depot_path.startswith("//"):
            if validate_depot_path(beni_depot_path):
                paths_to_process["BENI"] = beni_depot_path
            else:
                if error_callback:
                    error_callback("Path Not Found", f"BENI depot path does not exist: {beni_depot_path}")
                return None
        
        if flumen_depot_path and flumen_depot_path.startswith("//"):
            if validate_depot_path(flumen_depot_path):
                paths_to_process["FLUMEN"] = flumen_depot_path
            else:
                if error_callback:
                    error_callback("Path Not Found", f"FLUMEN depot path does not exist: {flumen_depot_path}")
                return None
        
        if rel_depot_path and rel_depot_path.startswith("//"):
            if validate_depot_path(rel_depot_path):
                paths_to_process["REL"] = rel_depot_path
            else:
                if error_callback:
                    error_callback("Path Not Found", f"REL depot path does not exist: {rel_depot_path}")
                return None
        
        if not paths_to_process:
            if error_callback:
                error_callback("No Valid Paths", "At least one valid depot path is required.")
            return None
        
        if progress_callback:
            progress_callback(20)
        
        # Map and sync files based on number of paths
        depot_paths_list = list(paths_to_process.values())
        if len(depot_paths_list) == 1:
            map_single_depot(depot_paths_list[0])
        elif len(depot_paths_list) == 2:
            map_two_depots_silent(depot_paths_list[0], depot_paths_list[1])
        elif len(depot_paths_list) == 3:
            map_three_depots_silent(depot_paths_list[0], depot_paths_list[1], depot_paths_list[2])
        
        # Sync all files
        for depot_path in depot_paths_list:
            sync_file_silent(depot_path)
        
        if progress_callback:
            progress_callback(60)
        
        # Extract properties from all paths
        comparison_data = {}
        all_depot_paths = {}
        
        for path_name, depot_path in paths_to_process.items():
            local_path = depot_to_local_path(depot_path)
            properties = extract_properties_from_file(local_path)
            
            if not properties:
                if error_callback:
                    error_callback("Properties Not Found", f"{path_name} file does not contain LMKD or Chimera properties")
                return None
            
            # Add metadata to each path's properties
            properties["_metadata"] = {
                "depot_paths": {path_name: depot_path},
                "original_properties": properties.copy()
            }
            
            comparison_data[path_name] = properties
            all_depot_paths[path_name] = depot_path
        
        if progress_callback:
            progress_callback(80)
        
        # Create merged properties (use first available path as base)
        first_path = list(comparison_data.keys())[0]
        merged_properties = comparison_data[first_path].copy()
        
        # Update metadata to include all depot paths
        merged_properties["_metadata"] = {
            "depot_paths": all_depot_paths,
            "original_properties": merged_properties.copy()
        }
        
        if progress_callback:
            progress_callback(100)
        
        # Return both comparison data and merged properties
        return (comparison_data, merged_properties)
        
    except Exception as e:
        if error_callback:
            error_callback("Load Properties Error", str(e))
        return None

def apply_tuning_changes_enhanced(current_properties, depot_paths_dict, 
                                 log_callback, progress_callback=None, error_callback=None):
    """Apply property changes to all target files (BENI, FLUMEN, REL)"""
    try:
        # Remove metadata if present
        properties_to_apply = {}
        for key, value in current_properties.items():
            if key != "_metadata":
                properties_to_apply[key] = value
        
        log_callback("[TUNING] Starting apply tuning changes to all paths...")
        
        # Count properties for logging
        total_lmkd = len(properties_to_apply.get("LMKD", {}))
        total_chimera = len(properties_to_apply.get("Chimera", {}))
        log_callback(f"[INFO] Properties to apply: LMKD={total_lmkd}, Chimera={total_chimera}")
        
        if progress_callback:
            progress_callback(10)
        
        # Create changelist for modifications
        log_callback("[STEP 1] Creating pending changelist for tuning changes...")
        changelist_id = create_changelist_silent("Tuning - Apply property changes to all paths")
        log_callback(f"[OK] Created changelist {changelist_id}")
        
        if progress_callback:
            progress_callback(20)
        
        # Map all depot paths
        depot_paths_list = list(depot_paths_dict.values())
        if len(depot_paths_list) == 1:
            map_single_depot(depot_paths_list[0])
        elif len(depot_paths_list) == 2:
            map_two_depots_silent(depot_paths_list[0], depot_paths_list[1])
        elif len(depot_paths_list) == 3:
            map_three_depots_silent(depot_paths_list[0], depot_paths_list[1], depot_paths_list[2])
        
        # Process each target file
        processed_files = []
        progress_step = 60 // len(depot_paths_dict)  # Divide remaining progress
        
        for i, (path_name, depot_path) in enumerate(depot_paths_dict.items()):
            try:
                log_callback(f"[STEP 2.{i+1}] Processing {path_name} file...")
                
                # Sync latest version
                sync_file_silent(depot_path)
                log_callback(f"[OK] Synced latest version of {path_name}")
                
                if progress_callback:
                    progress_callback(20 + (i + 1) * progress_step)
                
                # Checkout for editing
                checkout_file_silent(depot_path, changelist_id)
                log_callback(f"[OK] Checked out {path_name} for editing")
                
                # Get local path and apply changes
                local_path = depot_to_local_path(depot_path)
                
                # Log what will be applied
                log_callback(f"[DEBUG] Applying properties to {path_name}:")
                for category, props in properties_to_apply.items():
                    if props:
                        log_callback(f"[DEBUG]   {category}: {len(props)} properties")
                
                success, error_msg = update_properties_in_file(local_path, properties_to_apply)
                
                if success:
                    log_callback(f"[OK] Applied tuning changes to {path_name}.")
                    processed_files.append(path_name)
                else:
                    log_callback(f"[ERROR] Failed to apply changes to {path_name}: {error_msg}")
                    if error_callback:
                        error_callback("Apply Error", f"Failed to apply changes to {path_name}: {error_msg}")
                    return False
                
            except Exception as e:
                log_callback(f"[ERROR] Error processing {path_name}: {str(e)}")
                if error_callback:
                    error_callback("Processing Error", f"Error processing {path_name}: {str(e)}")
                return False
        
        if progress_callback:
            progress_callback(100)
        
        log_callback(f"[SUCCESS] Tuning changes applied successfully to: {', '.join(processed_files)}")
        log_callback(f"[INFO] Changelist {changelist_id} contains all modifications for all paths")
        log_callback(f"[INFO] All properties have been synchronized across {len(processed_files)} files")
        
        return True
        
    except Exception as e:
        log_callback(f"[ERROR] Apply tuning changes failed: {str(e)}")
        if error_callback:
            error_callback("Apply Tuning Error", str(e))
        return False

# Keep original functions for backward compatibility
def load_properties_for_tuning(beni_depot_path, flumen_depot_path, 
                              progress_callback=None, error_callback=None, info_callback=None):
    """Legacy function - load properties from BENI and FLUMEN only"""
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
        depot_paths = {}
        
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
    """Legacy function - apply changes to original depot paths"""
    return apply_tuning_changes_enhanced(current_properties, original_depot_paths, 
                                       log_callback, progress_callback, error_callback)

# Utility functions
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