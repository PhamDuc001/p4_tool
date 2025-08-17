"""
Parse process implementation
Handles workspace parsing to find device_common.mk files and library size calculations
"""

import re
import subprocess
from P4 import P4, P4Exception


# ============================================================================
# WORKSPACE PARSING LOGIC
# ============================================================================

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


# ============================================================================
# ADB DEVICE MANAGEMENT LOGIC
# ============================================================================

def refresh_adb_devices(log_callback=None):
    """
    Refresh ADB devices list
    Returns list of connected device IDs
    """
    try:
        if log_callback:
            log_callback("[ADB] Running adb devices command...")
            
        result = subprocess.run(
            ["adb", "devices"], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        
        if result.returncode != 0:
            error_msg = "Failed to run adb devices command"
            if log_callback:
                log_callback(f"[ERROR] {error_msg}")
            raise RuntimeError(error_msg)

        # Parse devices output
        lines = result.stdout.strip().split('\n')
        devices = []
        
        for line in lines[1:]:  # Skip first line "List of devices attached"
            if line.strip() and '\t' in line:
                device_id, status = line.split('\t')
                if status.strip() == 'device':
                    devices.append(device_id.strip())

        if log_callback:
            if devices:
                log_callback(f"[ADB] Parsed {len(devices)} connected devices from output")
            else:
                log_callback("[ADB] No connected devices found in output")
        
        return devices

    except subprocess.TimeoutExpired:
        error_msg = "ADB devices command timed out"
        if log_callback:
            log_callback(f"[ERROR] {error_msg}")
        raise RuntimeError(error_msg)
    except FileNotFoundError:
        error_msg = "ADB command not found. Please install Android SDK and add ADB to your PATH."
        if log_callback:
            log_callback(f"[ERROR] {error_msg}")
        raise RuntimeError(error_msg)
    except Exception as e:
        error_msg = f"Error running adb devices: {str(e)}"
        if log_callback:
            log_callback(f"[ERROR] {error_msg}")
        raise RuntimeError(error_msg)


def connect_to_device(device_id, log_callback=None):
    """
    Connect to specified device and test connection
    Returns True if successful, False otherwise
    """
    try:
        if log_callback:
            log_callback(f"[ADB] Testing connection to device: {device_id}")
        
        # Test connection by running a simple command
        result = subprocess.run(
            ["adb", "-s", device_id, "shell", "echo", "test"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            if log_callback:
                log_callback(f"[ADB] Connection test successful for {device_id}")
            return True
        else:
            if log_callback:
                log_callback(f"[ERROR] Connection test failed for {device_id}: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        if log_callback:
            log_callback(f"[ERROR] Connection test timed out for {device_id}")
        return False
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Error testing connection to {device_id}: {str(e)}")
        return False


# ============================================================================
# LIBRARY SIZE CALCULATION LOGIC
# ============================================================================

def calculate_library_sizes(device_id, libraries, log_callback=None, progress_callback=None):
    """
    Calculate library sizes on connected device
    Returns dictionary: {library_path: size_in_bytes}
    """
    results = {}
    total_libraries = len(libraries)
    
    if log_callback:
        log_callback(f"[CALC] Starting size calculation for {total_libraries} libraries on {device_id}")

    for i, library in enumerate(libraries):
        try:
            if log_callback:
                log_callback(f"[CALC] Checking size of: {library}")
            
            # Run du command on device
            result = subprocess.run(
                ["adb", "-s", device_id, "shell", "du", library],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                # Parse du output (format: "size_in_kb    path")
                output = result.stdout.strip()
                if output:
                    # Extract size (first column)
                    size_kb = re.split(r'\s+', output)[0]
                    try:
                        size_kb_int = int(size_kb)
                        size_bytes = size_kb_int * 1024
                        results[library] = size_bytes
                        if log_callback:
                            log_callback(f"[OK] {library}: {size_kb} KB ({size_bytes} bytes)")
                    except ValueError:
                        if log_callback:
                            log_callback(f"[ERROR] Invalid size format for {library}: {size_kb}")
                        results[library] = 0
                else:
                    if log_callback:
                        log_callback(f"[ERROR] Empty output for {library}")
                    results[library] = 0
            else:
                if log_callback:
                    log_callback(f"[ERROR] Failed to get size for {library}: {result.stderr.strip()}")
                results[library] = 0

        except subprocess.TimeoutExpired:
            if log_callback:
                log_callback(f"[ERROR] Timeout checking {library}")
            results[library] = 0
        except Exception as e:
            if log_callback:
                log_callback(f"[ERROR] Error checking {library}: {str(e)}")
            results[library] = 0

        # Update progress
        if progress_callback:
            progress = int(((i + 1) / total_libraries) * 100)
            progress_callback(progress)

    if log_callback:
        total_size = sum(results.values())
        total_kb = total_size / 1024
        successful_libs = len([size for size in results.values() if size > 0])
        log_callback(f"[CALC] Calculation completed. Successfully calculated: {successful_libs}/{total_libraries} libraries")
        log_callback(f"[CALC] Total size: {total_kb:.1f} KB ({total_size:,} bytes)")

    return results


# Future implementation placeholder
def calculate_library_sizes_from_device_common(device_common_paths, log_callback=None):
    """
    Calculate library sizes from device_common.mk files
    This will be implemented in future updates
    """
    if log_callback:
        log_callback("[INFO] Library size calculation from device_common.mk files will be implemented in future updates")
    
    # Placeholder for future implementation
    return {}