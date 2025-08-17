"""
Parse process implementation
Handles workspace parsing to find device_common.mk files and library size calculations
"""

import re
from P4 import P4, P4Exception


def find_device_common_mk_from_workspace(workspace_name, log_callback=None):
    """
    Find device_common.mk path from workspace name
    Returns the complete path to device_common.mk file
    """
    if log_callback:
        log_callback(f"[PARSE] Searching device_common.mk in workspace: {workspace_name}")
    
    p4 = P4()
    try:
        p4.connect()
        
        # Get client spec information
        if log_callback:
            log_callback(f"[PARSE] Fetching client spec for: {workspace_name}")
        
        client_spec = p4.fetch_client("-o", workspace_name)
        
        # Regex pattern to find device_common.mk paths
        # Pattern looks for: //depot_name/*/device/*_common/
        pattern = re.compile(r"(^[^.]+?/)device/[^/]+?_common/")
        
        # Search in View mappings
        found_paths = []
        for view in client_spec.get('View', []):
            # Get depot path (left side of mapping)
            depot_path = view.split()[0] if isinstance(view, str) else view[0]
            match = pattern.search(depot_path)
            if match:
                # Remove "..." at the end and add "device_common.mk"
                clean_path = depot_path.rstrip('...')
                complete_path = clean_path + "device_common.mk"
                found_paths.append(complete_path)
        
        # Remove duplicates while preserving order
        unique_paths = []
        for path in found_paths:
            if path not in unique_paths:
                unique_paths.append(path)
        
        if log_callback:
            if unique_paths:
                log_callback(f"[OK] Found {len(unique_paths)} device_common.mk path(s)")
                for path in unique_paths:
                    log_callback(f"[RESULT] {path}")
            else:
                log_callback("[WARNING] No device_common.mk paths found in workspace")
        
        return unique_paths
        
    except P4Exception as e:
        error_msg = f"P4 Error: {str(e)}"
        if log_callback:
            log_callback(f"[ERROR] {error_msg}")
        raise RuntimeError(error_msg)
    except Exception as e:
        error_msg = f"Error connecting to P4 or parsing workspace: {str(e)}"
        if log_callback:
            log_callback(f"[ERROR] {error_msg}")
        raise RuntimeError(error_msg)
    finally:
        try:
            p4.disconnect()
        except:
            pass  # Ignore disconnect errors


def parse_multiple_workspaces(workspace_dict, log_callback=None, progress_callback=None):
    """
    Parse multiple workspaces to find device_common.mk files
    workspace_dict: {"BENI": "workspace1", "VINCE": "workspace2", "FLUMEN": "workspace3"}
    Returns: {"BENI": ["path1", "path2"], "VINCE": ["path3"], "FLUMEN": []}
    """
    results = {}
    total_workspaces = len([ws for ws in workspace_dict.values() if ws.strip()])
    current_count = 0
    
    if log_callback:
        log_callback("[PARSE] Starting workspace parsing process...")
    
    for category, workspace in workspace_dict.items():
        workspace = workspace.strip()
        if not workspace:
            results[category] = []
            if log_callback:
                log_callback(f"[SKIP] {category} workspace is empty")
            continue
        
        try:
            if log_callback:
                log_callback(f"\n[PARSE] Processing {category} workspace: {workspace}")
            
            paths = find_device_common_mk_from_workspace(workspace, log_callback)
            results[category] = paths
            
            current_count += 1
            if progress_callback:
                progress = int((current_count / total_workspaces) * 100)
                progress_callback(progress)
                
        except Exception as e:
            if log_callback:
                log_callback(f"[ERROR] Failed to parse {category} workspace '{workspace}': {str(e)}")
            results[category] = []
    
    if log_callback:
        log_callback(f"\n[PARSE] Workspace parsing completed.")
        total_found = sum(len(paths) for paths in results.values())
        log_callback(f"[SUMMARY] Total device_common.mk files found: {total_found}")
    
    return results


def validate_workspace_exists(workspace_name):
    """
    Validate if workspace exists in P4
    Returns (success: bool, message: str)
    """
    if not workspace_name.strip():
        return False, "Workspace name is empty"
    
    p4 = P4()
    try:
        p4.connect()
        
        # Try to fetch client spec
        client_spec = p4.fetch_client("-o", workspace_name.strip())
        
        # Check if client exists (has Client field)
        if 'Client' in client_spec and client_spec['Client']:
            return True, f"Workspace '{workspace_name}' exists"
        else:
            return False, f"Workspace '{workspace_name}' does not exist"
            
    except P4Exception as e:
        return False, f"P4 Error: {str(e)}"
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        try:
            p4.disconnect()
        except:
            pass


# Future implementation for library size calculation
def calculate_library_sizes(device_common_paths, log_callback=None):
    """
    Calculate library sizes from device_common.mk files
    This will be implemented in future updates
    """
    if log_callback:
        log_callback("[INFO] Library size calculation feature will be implemented in future updates")
    
    # Placeholder for future implementation
    return {}