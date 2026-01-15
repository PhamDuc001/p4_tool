"""
P4 command operations
Handles all Perforce commands and validations
Enhanced with auto-resolve cascading functionality - FIXED VERSION
"""

import subprocess
import re
from typing import List, Optional, Tuple
from config.p4_config import get_client_name
from P4 import P4, P4Exception

# Export the function for use by other modules
__all__ = [
    "get_client_name",
    "run_cmd",
    "validate_depot_path",
    "validate_device_common_mk_path",
    "create_changelist_silent",
    "map_client_two_paths",
    "map_single_depot",
    "map_two_depots_silent",
    "sync_file_silent",
    "checkout_file_silent",
    "is_workspace_like",
    "resolve_user_input_to_depot_path",
    "auto_resolve_missing_branches",
    "get_integration_source_depot_path",
    "find_device_common_mk_path"
]


def find_device_common_mk_path(workspace_name, log_callback=None):
    """
    Find device_common.mk path from workspace using P4Python
    Returns the complete depot path to device_common.mk file and all view paths
    """
    if log_callback:
        log_callback(f"[SYSTEM] Searching device_common.mk in workspace: {workspace_name}")
    
    p4 = P4()
    P4_SERVER_PORT = "107.113.53.156:1716"
    p4.port = P4_SERVER_PORT
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

def run_cmd(cmd, input_text=None):
    """Execute command and return output"""
    result = subprocess.run(
        cmd, input=input_text, capture_output=True, text=True, shell=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\n{result.stderr}")
    return result.stdout.strip()


def validate_depot_path(depot_path):
    """Validate if depot path exists in Perforce"""
    try:
        result = subprocess.run(
            f"p4 files {depot_path}", capture_output=True, text=True, shell=True
        )
        if result.returncode != 0 or "no such file" in result.stderr.lower():
            return False
        return True
    except:
        return False


def validate_device_common_mk_path(depot_path):
    """
    Validate if depot path exists and is a device_common.mk file
    Returns (exists, is_device_common_mk)
    """
    try:
        # Check if path exists
        result = subprocess.run(
            f"p4 files {depot_path}", capture_output=True, text=True, shell=True
        )
        if result.returncode != 0 or "no such file" in result.stderr.lower():
            return False, False

        # Check if it's a device_common.mk file
        is_device_common = depot_path.endswith("/device_common.mk")

        return True, is_device_common

    except:
        return False, False




def create_changelist_silent(description="Auto changelist"):
    """Create pending changelist without logging"""
    changelist_spec = run_cmd("p4 change -o")
    new_spec = re.sub(r"<enter description here>", description, changelist_spec)
    changelist_result = run_cmd("p4 change -i", input_text=new_spec)
    changelist_id = re.search(r"Change (\d+)", changelist_result).group(1)
    return changelist_id


def _map_client_depots_core(depot_paths, log_callback=None, silent=False):
    """
    Core function for client depot mapping - INTERNAL USE ONLY
    
    Args:
        depot_paths: List of depot paths to map
        log_callback: Optional callback for logging
        silent: If True, force silent mode regardless of log_callback
    
    Returns:
        None
    """
    client_name = get_client_name()
    if not client_name:
        raise RuntimeError("Client name not initialized. Please check P4 configuration.")
    
    # Build mapping line for each depot
    mapping_lines = []
    for depot_path in depot_paths:
        mapping_lines.append(f"\t{depot_path}\t//{client_name}/{depot_path[2:]}")
    
    # Get current client spec
    client_spec = run_cmd("p4 client -o")
    lines = client_spec.splitlines()
    
    # Remove old mappings for any target depot
    new_lines = []
    for line in lines:
        if any(depot in line for depot in depot_paths):
            continue  # Remove old mapping
        new_lines.append(line)
    
    # Add new mappings
    new_lines.extend(mapping_lines)
    
    # Update client spec
    new_spec = "\n".join(new_lines)
    run_cmd("p4 client -i", input_text=new_spec)
    
    # Logging only if not silent
    if not silent and log_callback:
        if len(depot_paths) == 1:
            depot_name = "BENI" if "beni" in depot_paths[0].lower() else "FLUMEN" if "flumen" in depot_paths[0].lower() else "DEPOT"
            log_callback(f"[MAPPING] Mapping {depot_name} to client spec...")
        elif len(depot_paths) == 2:
            target_name = "BENI" if "beni" in depot_paths[0].lower() else "FLUMEN" if "flumen" in depot_paths[0].lower() else "TARGET"
            log_callback(f"[STEP 2] Mapping {target_name} and VINCE to client spec...")
        elif len(depot_paths) == 4:
            log_callback("[STEP 2] Mapping BENI, VINCE, FLUMEN and REL to client spec...")
        
        log_callback("[OK] Mapping completed.")


def map_client_two_paths(target_depot, vince_depot, log_callback):
    """Map two depots to client spec - WRAPPER for backward compatibility"""
    _map_client_depots_core([target_depot, vince_depot], log_callback)


def map_single_depot(depot_path, log_callback=None):
    """Map single depot to client spec - WRAPPER for backward compatibility"""
    _map_client_depots_core([depot_path], log_callback)


def map_two_depots_silent(depot1, depot2):
    """Map two depots to client spec without logging - WRAPPER for backward compatibility"""
    _map_client_depots_core([depot1, depot2], silent=True)


def sync_file_silent(depot_path):
    """Sync file from depot without logging"""
    run_cmd(f"p4 sync {depot_path}")

def checkout_file_silent(depot_path, changelist_id, log_callback=None):
    """
    Checkout file for editing with smart CL management
    Checks if file is already opened and handles CL conflicts
    
    Args:
        depot_path: Depot path to checkout
        changelist_id: Target changelist ID
        log_callback: Optional callback for logging
    """
    try:
        # Step 1: Check if file is already opened
        check_cmd = f"p4 opened {depot_path}"
        result = subprocess.run(
            check_cmd, 
            capture_output=True, 
            text=True, 
            shell=True
        )
        
        # Case 1: File not opened yet
        if result.returncode != 0 or "not opened on this client" in result.stdout:
            if log_callback:
                log_callback(f"[CHECKOUT] File not opened, checking out to CL {changelist_id}")
            
            # Normal checkout
            run_cmd(f"p4 edit -c {changelist_id} {depot_path}")
            
            if log_callback:
                log_callback(f"[OK] Checked out to CL {changelist_id}")
            return
        
        # Case 2: File is already opened
        # Parse output: //path/file#6 - edit change 32339139 (text)
        output = result.stdout.strip()
        
        # Extract current CL number
        cl_match = re.search(r'change (\d+)', output)
        if not cl_match:
            # File is opened but can't parse CL - try checkout anyway
            if log_callback:
                log_callback(f"[WARNING] File opened but CL not detected, attempting checkout")
            run_cmd(f"p4 edit -c {changelist_id} {depot_path}")
            return
        
        current_cl = cl_match.group(1)
        
        # Case 2a: File already in target CL - skip
        if current_cl == str(changelist_id):
            if log_callback:
                log_callback(f"[INFO] File already in target CL {changelist_id}, skipping")
            return
        
        # Case 2b: File in different CL - ask user
        if log_callback:
            log_callback(f"[WARNING] File is already opened in CL {current_cl}")
        
        # Show confirmation dialog
        from tkinter import messagebox
        response = messagebox.askyesno(
            "File Already Opened",
            f"File is currently opened in changelist {current_cl}.\n\n"
            f"Do you want to move it to changelist {changelist_id}?\n\n"
            f"File: {depot_path}"
        )
        
        if response:
            # User chose Yes - reopen to new CL
            if log_callback:
                log_callback(f"[REOPEN] Moving file from CL {current_cl} to CL {changelist_id}")
            
            reopen_cmd = f"p4 reopen -c {changelist_id} {depot_path}"
            run_cmd(reopen_cmd)
            
            if log_callback:
                log_callback(f"[OK] File moved to CL {changelist_id}")
        else:
            # User chose No - keep in old CL
            if log_callback:
                log_callback(f"[INFO] File kept in original CL {current_cl} as per user choice")
    
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Checkout operation failed: {str(e)}")
        raise

# =====================================================================================
# Workspace helpers (accept TEMPLATE_* workspace name and resolve to depot file path)
# =====================================================================================

_DEVICE_COMMON_REGEX = re.compile(r"^(.+?)/device/([^/]+?)_common/", re.IGNORECASE)


def is_workspace_like(user_input: str) -> bool:
    """Return True if the input string looks like a P4 workspace template name."""
    if not user_input:
        return False
    return user_input.strip().upper().startswith("TEMPLATE")

def _extract_device_common_from_depots(left_depots: List[str]) -> Optional[str]:
    """From a list of left depot mappings, find a `device/<model>_common/` segment and
    build the device_common.mk depot file path."""
    for left in left_depots:
        match = _DEVICE_COMMON_REGEX.search(left)
        if not match:
            continue
        base_vendor_dir = match.group(1)
        last_segment = base_vendor_dir.rstrip("/").split("/")[-1]
        model = last_segment.split("_")[0] if "_" in last_segment else last_segment
        candidate = f"{base_vendor_dir}/device/{model}_common/device_common.mk"
        if validate_depot_path(candidate):
            return candidate
    return None

def resolve_user_input_to_depot_path(user_input: str) -> str:
    """Normalize user input: if it's a depot path, return as-is; if it's a workspace,
    resolve to device_common.mk depot path.
    """
    if not user_input:
        return user_input
    text = user_input.strip()
    if text.startswith("//"):
        return text
    if is_workspace_like(text):
        return find_device_common_mk_path(text)
    return text


# =====================================================================================
# AUTO-RESOLVE CASCADING FUNCTIONALITY - FIXED IMPLEMENTATION
# =====================================================================================


def get_integration_source_depot_path(depot_path: str, log_callback) -> Optional[str]:
    """
    FIXED: Get integration source depot path from p4 filelog version #1
    Parse integration history and return source depot path from "branch from" line
    Returns None if no integration source found or parsing failed
    """
    try:
        # FIXED COMMAND: Use #1 to get the first version (integration source)
        cmd = f"p4 filelog -i {depot_path}#1"
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            encoding='utf-8',
            errors='replace',
            shell=True
            )

        if result.returncode != 0:
            if log_callback:
                log_callback(f"[WARNING] P4 filelog command failed for {depot_path}#1")
            return None

        output = result.stdout.strip()
        if not output:
            if log_callback:
                log_callback(f"[WARNING] Empty filelog output for {depot_path}#1")
            return None

        # FIXED PARSING: Look for "... ... branch from <path>#<version>" pattern
        lines = output.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("... ... branch from "):
                # Extract path from "... ... branch from //path/device_common.mk#1"
                # Remove "... ... branch from " prefix and "#<version>" suffix
                integration_line = line.split("from ")[1]
                source_path = integration_line.split("#")[0].split(",")[0]
                if log_callback:
                    log_callback(f"[PARSE] Extracted integration source: {source_path}")
                return source_path

        if log_callback:
            log_callback(
                f"[WARNING] No 'branch from' line found in filelog output for {depot_path}#1"
            )
        return None

    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Error getting integration source: {str(e)}")
        return None

def auto_resolve_vendor_branches(
    vince_input, beni_input, flumen_input, rel_input, log_callback
    ):
    """
    Auto-resolve missing vendor branches from integration history

    Args:
        vince_input: VINCE input (workspace or depot path) - mandatory
        beni_input: BENI input (workspace or depot path) - optional
        flumen_input: FLUMEN input (workspace or depot path) - optional
        rel_input: REL input (workspace or depot path) - optional
        log_callback: Callback function for logging

    Returns:
        Tuple: (resolved_beni, resolved_vince, resolved_flumen, resolved_rel)

    Auto-resolve Logic:
    - VINCE is always mandatory (reference file)
    - REL + VINCE → Auto-resolve FLUMEN from REL → Auto-resolve BENI from FLUMEN
    - FLUMEN + VINCE → Auto-resolve BENI from FLUMEN
    - BENI + VINCE → No auto-resolve needed
    - If both FLUMEN and REL provided → Auto-resolve BENI from FLUMEN
    """

    # Normalize inputs
    vince_input = vince_input.strip() if vince_input else ""
    beni_input = beni_input.strip() if beni_input else ""
    flumen_input = flumen_input.strip() if flumen_input else ""
    rel_input = rel_input.strip() if rel_input else ""

    # Initialize resolved values with original inputs
    resolved_vince = vince_input
    resolved_beni = beni_input
    resolved_flumen = flumen_input
    resolved_rel = rel_input

    # VINCE is always mandatory - validate it exists
    if not vince_input:
        raise RuntimeError("VINCE is mandatory and cannot be empty")

    log_callback(
        "[VENDOR AUTO-RESOLVE] Analyzing input combination for auto-resolve..."
    )
    log_callback(f"[INPUT] VINCE: {vince_input}")
    log_callback(f"[INPUT] BENI: {beni_input if beni_input else '(empty)'}")
    log_callback(f"[INPUT] FLUMEN: {flumen_input if flumen_input else '(empty)'}")
    log_callback(f"[INPUT] REL: {rel_input if rel_input else '(empty)'}")

    def resolve_vendor_input_to_depot_path_local(user_input, log_callback=None):
        """Local helper function to resolve vendor input"""
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
                    log_callback(
                        f"[OK] Resolved workspace to device_common.mk: {resolved_path}"
                    )
                return resolved_path
            except Exception as e:
                raise RuntimeError(f"Workspace resolution failed: {str(e)}")

        else:
            raise RuntimeError(
                f"Input must be either depot path (//depot/...) or workspace (TEMPLATE_*): {user_input}"
            )

    try:
        # Case 1: REL + VINCE provided, but FLUMEN + BENI empty
        # Auto-resolve: REL → FLUMEN → BENI (cascading)
        if rel_input and vince_input and not flumen_input and not beni_input:
            log_callback(
                "[AUTO-RESOLVE] Case detected: REL + VINCE → Auto-resolve FLUMEN and BENI"
            )

            # Step 1: Resolve REL to depot path and sync
            rel_depot_path, _ = find_device_common_mk_path(
                rel_input, log_callback
            )
            if not validate_depot_path(rel_depot_path):
                raise RuntimeError(f"REL path does not existt: {rel_depot_path}")

            # Map and sync REL to get latest
            map_single_depot(rel_depot_path)
            sync_file_silent(rel_depot_path)

            # Step 2: Get integration source for FLUMEN from REL
            flumen_source = get_integration_source_depot_path(
                rel_depot_path, log_callback
            )
            if flumen_source:
                # Validate FLUMEN source exists
                if validate_depot_path(flumen_source):
                    resolved_flumen = flumen_source
                    log_callback(
                        f"[AUTO] Successfully resolved FLUMEN from REL: {flumen_source}"
                    )

                    # Step 3: Get integration source for BENI from FLUMEN
                    # Map and sync FLUMEN first
                    map_single_depot(flumen_source)
                    sync_file_silent(flumen_source)

                    beni_source = get_integration_source_depot_path(
                        flumen_source, log_callback
                    )
                    if beni_source:
                        # Validate BENI source exists
                        if validate_depot_path(beni_source):
                            resolved_beni = beni_source
                            log_callback(
                                f"[AUTO] Successfully resolved BENI from FLUMEN: {beni_source}"
                            )
                        else:
                            log_callback(
                                f"[WARNING] BENI integration source does not exist: {beni_source}"
                            )
                    else:
                        log_callback(
                            f"[WARNING] No integration history found for FLUMEN: {flumen_source}"
                        )
                else:
                    log_callback(
                        f"[WARNING] FLUMEN integration source does not exist: {flumen_source}"
                    )
            else:
                log_callback(
                    f"[WARNING] No integration history found for REL: {rel_depot_path}"
                )

        # Case 2: FLUMEN + VINCE provided, but BENI empty (REL may or may not be provided)
        # Auto-resolve: FLUMEN → BENI
        elif flumen_input and vince_input and not beni_input:
            log_callback(
                "[AUTO-RESOLVE] Case detected: FLUMEN + VINCE → Auto-resolve BENI"
            )

            # Step 1: Resolve FLUMEN to depot path and sync
            flumen_depot_path = resolve_vendor_input_to_depot_path_local(
                flumen_input, log_callback
            )
            if not validate_depot_path(flumen_depot_path):
                raise RuntimeError(f"FLUMEN path does not exist: {flumen_depot_path}")

            # Map and sync FLUMEN to get latest
            map_single_depot(flumen_depot_path)
            sync_file_silent(flumen_depot_path)

            # Step 2: Get integration source for BENI from FLUMEN
            beni_source = get_integration_source_depot_path(
                flumen_depot_path, log_callback
            )
            if beni_source:
                # Validate BENI source exists
                if validate_depot_path(beni_source):
                    resolved_beni = beni_source
                    log_callback(
                        f"[AUTO] Successfully resolved BENI from FLUMEN: {beni_source}"
                    )
                else:
                    log_callback(
                        f"[WARNING] BENI integration source does not exist: {beni_source}"
                    )
            else:
                log_callback(
                    f"[WARNING] No integration history found for FLUMEN: {flumen_depot_path}"
                )

        # Case 3: Both FLUMEN and REL provided + VINCE, but BENI empty
        # Auto-resolve: FLUMEN → BENI (prefer FLUMEN over REL for BENI resolution)
        elif flumen_input and rel_input and vince_input and not beni_input:
            log_callback(
                "[AUTO-RESOLVE] Case detected: FLUMEN + REL + VINCE → Auto-resolve BENI from FLUMEN"
            )

            # Step 1: Resolve FLUMEN to depot path and sync
            flumen_depot_path = resolve_vendor_input_to_depot_path_local(
                flumen_input, log_callback
            )
            if not validate_depot_path(flumen_depot_path):
                raise RuntimeError(f"FLUMEN path does not exist: {flumen_depot_path}")

            # Map and sync FLUMEN to get latest
            map_single_depot(flumen_depot_path)
            sync_file_silent(flumen_depot_path)

            # Step 2: Get integration source for BENI from FLUMEN
            beni_source = get_integration_source_depot_path(
                flumen_depot_path, log_callback
            )
            if beni_source:
                # Validate BENI source exists
                if validate_depot_path(beni_source):
                    resolved_beni = beni_source
                    log_callback(
                        f"[AUTO] Successfully resolved BENI from FLUMEN: {beni_source}"
                    )
                else:
                    log_callback(
                        f"[WARNING] BENI integration source does not exist: {beni_source}"
                    )
            else:
                log_callback(
                    f"[WARNING] No integration history found for FLUMEN: {flumen_depot_path}"
                )

        # Case 4: All fields provided or only BENI + VINCE
        else:
            log_callback(
                "[AUTO-RESOLVE] No auto-resolve needed - processing with provided inputs"
            )

        # Log final resolved values
        log_callback("[AUTO-RESOLVE] Final resolved values:")
        log_callback(f"[RESOLVED] VINCE: {resolved_vince}")
        log_callback(
            f"[RESOLVED] BENI: {resolved_beni if resolved_beni else '(not provided)'}"
        )
        log_callback(
            f"[RESOLVED] FLUMEN: {resolved_flumen if resolved_flumen else '(not provided)'}"
        )
        log_callback(
            f"[RESOLVED] REL: {resolved_rel if resolved_rel else '(not provided)'}"
        )

        return resolved_beni, resolved_vince, resolved_flumen, resolved_rel

    except Exception as e:
        log_callback(f"[AUTO-RESOLVE ERROR] {str(e)}")
        # Continue with original inputs instead of failing completely
        log_callback("[AUTO-RESOLVE] Continuing with original inputs due to error")
        return beni_input, vince_input, flumen_input, rel_input


# Update the __all__ export list to include the new function
__all__.append("auto_resolve_vendor_branches")


def auto_resolve_missing_branches(
    vince_input: str, flumen_input: str, beni_input: str, rel_input: str, log_callback
) -> Tuple[str, str, str, str]:
    """
    Auto-resolve missing branches from integration history with FIXED parsing logic
    Returns:
        Tuple: (resolved_beni, resolved_flumen, resolved_rel, resolved_vince)
    """

    # Normalize inputs
    vince_input = vince_input.strip() if vince_input else ""
    flumen_input = flumen_input.strip() if flumen_input else ""
    beni_input = beni_input.strip() if beni_input else ""
    rel_input = rel_input.strip() if rel_input else ""

    # Initialize resolved values with original inputs
    resolved_vince = vince_input
    resolved_flumen = flumen_input
    resolved_beni = beni_input
    resolved_rel = rel_input

    # VINCE is always mandatory - validate it exists
    if not vince_input:
        raise RuntimeError("VINCE is mandatory and cannot be empty")

    try:
        # Case 1: VINCE + REL provided, but FLUMEN + BENI empty
        # Auto-resolve: REL → FLUMEN → BENI (cascading)
        if vince_input and rel_input and not flumen_input and not beni_input:
            log_callback(
                "[AUTO-RESOLVE] Case detected: VINCE + REL → Auto-resolve FLUMEN and BENI"
            )

            # Step 1: Resolve REL to depot path and sync
            rel_depot_path, _ = find_device_common_mk_path(rel_input)
            if not validate_depot_path(rel_depot_path):
                raise RuntimeError(f"REL path does not existtt: {rel_depot_path}")

            # Map and sync REL to get latest
            map_single_depot(rel_depot_path)
            sync_file_silent(rel_depot_path)

            # Step 2: Get integration source for FLUMEN from REL
            flumen_source = get_integration_source_depot_path(
                rel_depot_path, log_callback
            )
            if not flumen_source:
                raise RuntimeError(
                    f"No integration history found for REL: {rel_depot_path}"
                )

            # Validate FLUMEN source exists
            if not validate_depot_path(flumen_source):
                raise RuntimeError(
                    f"Integration source does not exist: {flumen_source}"
                )

            resolved_flumen = flumen_source
            log_callback(f"[AUTO] Detected FLUMEN from REL: {flumen_source}")

            # Step 3: Get integration source for BENI from FLUMEN
            # Map and sync FLUMEN first
            map_single_depot(flumen_source)
            sync_file_silent(flumen_source)

            beni_source = get_integration_source_depot_path(flumen_source, log_callback)
            if not beni_source:
                raise RuntimeError(
                    f"No integration history found for FLUMEN: {flumen_source}"
                )

            # Validate BENI source exists
            if not validate_depot_path(beni_source):
                raise RuntimeError(f"Integration source does not exist: {beni_source}")

            resolved_beni = beni_source
            log_callback(f"[AUTO] Detected BENI from FLUMEN: {beni_source}")

        # Case 2: VINCE + FLUMEN provided, but BENI empty (REL may or may not be provided)
        # Auto-resolve: FLUMEN → BENI
        elif vince_input and flumen_input and not beni_input:
            log_callback(
                "[AUTO-RESOLVE] Case detected: VINCE + FLUMEN → Auto-resolve BENI"
            )

            # Step 1: Resolve FLUMEN to depot path and sync
            flumen_depot_path, _= find_device_common_mk_path(flumen_input)
            if not validate_depot_path(flumen_depot_path):
                raise RuntimeError(f"FLUMEN path does not exist: {flumen_depot_path}")

            # Map and sync FLUMEN to get latest
            map_single_depot(flumen_depot_path)
            sync_file_silent(flumen_depot_path)

            # Step 2: Get integration source for BENI from FLUMEN
            beni_source = get_integration_source_depot_path(
                flumen_depot_path, log_callback
            )
            if not beni_source:
                raise RuntimeError(
                    f"No integration history found for FLUMEN: {flumen_depot_path}"
                )

            # Validate BENI source exists
            if not validate_depot_path(beni_source):
                raise RuntimeError(f"Integration source does not exist: {beni_source}")

            resolved_beni = beni_source
            log_callback(f"[AUTO] Detected BENI from FLUMEN: {beni_source}")

        # Case 3: All fields provided or no auto-resolve needed
        else:
            log_callback(
                "[AUTO-RESOLVE] No auto-resolve needed - processing with provided inputs"
            )

        return resolved_beni, resolved_flumen, resolved_rel, resolved_vince

    except Exception as e:
        log_callback(f"[AUTO-RESOLVE ERROR] {str(e)}")
        raise RuntimeError(f"Auto-resolve failed: {str(e)}")
