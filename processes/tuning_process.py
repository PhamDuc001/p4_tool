"""
Enhanced Tuning process implementation - REFACTORED VERSION
Handles property loading, comparison, and applying changes to all 3 paths
Updated with centralized utilities and reduced code duplication
"""
from core.p4_operations import (
    validate_depot_path, create_changelist_silent, 
    sync_file_silent, checkout_file_silent
)
from core.file_operations import update_properties_in_file
from core.core_utils import (
    get_client_mapper, get_property_manager, get_auto_resolver
)
from config.p4_config import depot_to_local_path

def load_properties_for_tuning_enhanced(beni_depot_path, flumen_depot_path, rel_depot_path,
                                       progress_callback=None, error_callback=None, info_callback=None):
    """Load and compare properties from BENI, FLUMEN, and REL files - REFACTORED"""
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
        
        # Map and sync files using centralized mapper
        depot_paths_list = list(paths_to_process.values())
        mapper = get_client_mapper()
        mapper.map_depots(depot_paths_list, silent=True)
        
        # Sync all files
        for depot_path in depot_paths_list:
            sync_file_silent(depot_path)
        
        if progress_callback:
            progress_callback(60)
        
        # Extract properties from all paths using centralized property manager
        property_manager = get_property_manager()
        comparison_data = {}
        all_depot_paths = {}
        
        for path_name, depot_path in paths_to_process.items():
            local_path = depot_to_local_path(depot_path)
            properties = property_manager.extract_properties_from_file(local_path)
            
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

def apply_tuning_changes_enhanced_with_auto_resolve(current_properties, original_depot_paths, 
                                                   log_callback, progress_callback=None, error_callback=None):
    """Apply property changes to all target files with auto-resolve for missing paths - REFACTORED"""
    try:
        # Remove metadata if present
        properties_to_apply = {}
        for key, value in current_properties.items():
            if key != "_metadata":
                properties_to_apply[key] = value
        
        log_callback("[TUNING] Starting apply tuning changes with auto-resolve...")
        
        # Count properties for logging
        total_lmkd = len(properties_to_apply.get("LMKD", {}))
        total_chimera = len(properties_to_apply.get("Chimera", {}))
        log_callback(f"[INFO] Properties to apply: LMKD={total_lmkd}, Chimera={total_chimera}")
        
        if progress_callback:
            progress_callback(5)
        
        # Auto-resolve missing paths if only one path provided using centralized resolver
        if len(original_depot_paths) == 1:
            log_callback("[AUTO-RESOLVE] Single path detected - performing auto-resolve...")
            
            # Use centralized auto resolver
            auto_resolver = get_auto_resolver()
            provided_path_name = list(original_depot_paths.keys())[0]
            provided_depot_path = original_depot_paths[provided_path_name]
            
            # Define branch order based on provided path
            if provided_path_name == "REL":
                branch_order = ["REL", "FLUMEN", "BENI"]
            elif provided_path_name == "FLUMEN":
                branch_order = ["FLUMEN", "BENI"]
            elif provided_path_name == "BENI":
                branch_order = ["BENI"]  # No resolution needed
            else:
                raise RuntimeError(f"Unknown branch type: {provided_path_name}")
            
            # Perform cascading resolution
            if len(branch_order) > 1:
                cascading_result = auto_resolver.resolve_cascading_branches(
                    provided_depot_path, branch_order, log_callback
                )
                resolved_depot_paths = cascading_result
            else:
                resolved_depot_paths = original_depot_paths
        else:
            log_callback("[INFO] Multiple paths provided - skipping auto-resolve")
            resolved_depot_paths = original_depot_paths
        
        if progress_callback:
            progress_callback(15)
        
        # Create changelist for modifications
        log_callback("[STEP 1] Creating pending changelist for tuning changes...")
        changelist_id = create_changelist_silent("Tuning - Apply property changes to all paths")
        log_callback(f"[OK] Created changelist {changelist_id}")
        
        if progress_callback:
            progress_callback(25)
        
        # Map all depot paths using centralized mapper
        depot_paths_list = list(resolved_depot_paths.values())
        mapper = get_client_mapper()
        mapper.map_depots(depot_paths_list, silent=True)
        
        # Process each target file
        processed_files = []
        progress_step = 60 // len(resolved_depot_paths)  # Divide remaining progress
        
        for i, (path_name, depot_path) in enumerate(resolved_depot_paths.items()):
            try:
                log_callback(f"[STEP 2.{i+1}] Processing {path_name} file...")
                
                # Sync latest version
                sync_file_silent(depot_path)
                log_callback(f"[OK] Synced latest version of {path_name}")
                
                if progress_callback:
                    progress_callback(25 + (i + 1) * progress_step)
                
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
        
        # Log auto-resolve summary if it was used
        if len(original_depot_paths) == 1:
            original_path = list(original_depot_paths.keys())[0]
            log_callback(f"[SUMMARY] Auto-resolved from {original_path} to {len(processed_files)} files")
        
        log_callback(f"[INFO] All properties have been synchronized across {len(processed_files)} files")
        
        return True
        
    except Exception as e:
        log_callback(f"[ERROR] Apply tuning changes failed: {str(e)}")
        if error_callback:
            error_callback("Apply Tuning Error", str(e))
        return False

# Legacy functions for backward compatibility
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
        
        # Map and sync files using centralized utilities
        depot_paths = []
        if process_beni:
            depot_paths.append(beni_depot_path)
        if process_flumen:
            depot_paths.append(flumen_depot_path)
        
        mapper = get_client_mapper()
        mapper.map_depots(depot_paths, silent=True)
        
        for depot_path in depot_paths:
            sync_file_silent(depot_path)
        
        if progress_callback:
            progress_callback(60)
        
        # Get local paths and extract properties using centralized property manager
        property_manager = get_property_manager()
        properties_data = {}
        depot_paths_dict = {}
        
        if process_beni:
            beni_local = depot_to_local_path(beni_depot_path)
            beni_properties = property_manager.extract_properties_from_file(beni_local)
            if not beni_properties:
                if error_callback:
                    error_callback("Properties Not Found", "BENI file does not contain LMKD or Chimera properties")
                return None
            properties_data["BENI"] = beni_properties
            depot_paths_dict["BENI"] = beni_depot_path
        
        if process_flumen:
            flumen_local = depot_to_local_path(flumen_depot_path)
            flumen_properties = property_manager.extract_properties_from_file(flumen_local)
            if not flumen_properties:
                if error_callback:
                    error_callback("Properties Not Found", "FLUMEN file does not contain LMKD or Chimera properties")
                return None
            properties_data["FLUMEN"] = flumen_properties
            depot_paths_dict["FLUMEN"] = flumen_depot_path
        
        if progress_callback:
            progress_callback(80)
        
        # Compare properties if both files exist using centralized property manager
        if process_beni and process_flumen:
            differences = property_manager.compare_properties(
                properties_data["BENI"], properties_data["FLUMEN"]
            )
            if differences:
                diff_message = "Properties differ between BENI and FLUMEN:\n\n" + "\n".join(differences)
                if info_callback:
                    info_callback("Properties Comparison", diff_message)
        
        # Return the properties from the first available file for editing
        result_properties = properties_data.get("BENI", properties_data.get("FLUMEN", {}))
        
        # Add metadata for apply functionality
        result_properties["_metadata"] = {
            "depot_paths": depot_paths_dict,
            "original_properties": result_properties.copy()
        }
        
        if progress_callback:
            progress_callback(100)
        
        return result_properties
        
    except Exception as e:
        if error_callback:
            error_callback("Load Properties Error", str(e))
        return None

def apply_tuning_changes_enhanced(current_properties, depot_paths_dict, 
                                 log_callback, progress_callback=None, error_callback=None):
    """Apply property changes to all target files - legacy function"""
    return apply_tuning_changes_enhanced_with_auto_resolve(current_properties, depot_paths_dict, 
                                                          log_callback, progress_callback, error_callback)

def apply_tuning_changes(current_properties, original_depot_paths, 
                        log_callback, progress_callback=None, error_callback=None):
    """Legacy function - apply changes to original depot paths"""
    return apply_tuning_changes_enhanced_with_auto_resolve(current_properties, original_depot_paths, 
                                                          log_callback, progress_callback, error_callback)