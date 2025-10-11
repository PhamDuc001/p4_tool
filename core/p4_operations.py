"""
P4 command operations
Handles all Perforce commands and validations
Enhanced with auto-resolve cascading functionality - FIXED VERSION
"""

import subprocess
import re
from typing import List, Optional, Tuple
from config.p4_config import get_client_name

# Export the function for use by other modules
__all__ = [
    "get_client_name",
    "run_cmd",
    "validate_depot_path",
    "validate_device_common_mk_path",
    "create_changelist",
    "create_changelist_silent",
    "map_client",
    "map_client_two_paths",
    "map_single_depot",
    "map_two_depots_silent",
    "sync_file",
    "sync_file_silent",
    "checkout_file",
    "checkout_file_silent",
    "is_workspace_like",
    "resolve_workspace_to_device_common_path",
    "resolve_user_input_to_depot_path",
    "auto_resolve_missing_branches",
    "get_integration_source_depot_path",
    "find_device_common_mk_from_workspace",
]


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


def create_changelist(log_callback):
    """Create pending changelist"""
    log_callback("[STEP 1] Creating pending changelist...")
    changelist_spec = run_cmd("p4 change -o")
    new_spec = re.sub(
        r"<enter description here>",
        "Auto changelist - Sync and update LMKD/Chimera",
        changelist_spec,
    )
    changelist_result = run_cmd("p4 change -i", input_text=new_spec)
    changelist_id = re.search(r"Change (\d+)", changelist_result).group(1)
    log_callback(f"[OK] Created changelist {changelist_id}")
    return changelist_id


def create_changelist_silent(description="Auto changelist"):
    """Create pending changelist without logging"""
    changelist_spec = run_cmd("p4 change -o")
    new_spec = re.sub(r"<enter description here>", description, changelist_spec)
    changelist_result = run_cmd("p4 change -i", input_text=new_spec)
    changelist_id = re.search(r"Change (\d+)", changelist_result).group(1)
    return changelist_id


def map_client(beni_depot, vince_depot, flumen_depot, log_callback):
    """Map multiple depots to client spec"""
    client_name = get_client_name()
    if not client_name:
        raise RuntimeError(
            "Client name not initialized. Please check P4 configuration."
        )

    log_callback("[STEP 2] Mapping BENI, VINCE and FLUMEN to client spec...")
    client_spec = run_cmd("p4 client -o")
    lines = client_spec.splitlines()
    new_lines = []
    for line in lines:
        if beni_depot in line or vince_depot in line or flumen_depot in line:
            continue
        new_lines.append(line)
    new_lines.append(f"\t{beni_depot}\t//{client_name}/{beni_depot[2:]}")
    new_lines.append(f"\t{vince_depot}\t//{client_name}/{vince_depot[2:]}")
    new_lines.append(f"\t{flumen_depot}\t//{client_name}/{flumen_depot[2:]}")
    new_spec = "\n".join(new_lines)
    run_cmd("p4 client -i", input_text=new_spec)
    log_callback("[OK] Mapping completed.")


def map_client_two_paths(target_depot, vince_depot, log_callback):
    """Map two depots to client spec"""
    client_name = get_client_name()
    if not client_name:
        raise RuntimeError(
            "Client name not initialized. Please check P4 configuration."
        )

    target_name = (
        "BENI"
        if "beni" in target_depot.lower()
        else "FLUMEN" if "flumen" in target_depot.lower() else "TARGET"
    )
    log_callback(f"[STEP 2] Mapping {target_name} and VINCE to client spec...")
    client_spec = run_cmd("p4 client -o")
    lines = client_spec.splitlines()
    new_lines = []
    for line in lines:
        if target_depot in line or vince_depot in line:
            continue
        new_lines.append(line)
    new_lines.append(f"\t{target_depot}\t//{client_name}/{target_depot[2:]}")
    new_lines.append(f"\t{vince_depot}\t//{client_name}/{vince_depot[2:]}")
    new_spec = "\n".join(new_lines)
    run_cmd("p4 client -i", input_text=new_spec)
    log_callback("[OK] Mapping completed.")


def map_single_depot(depot_path, log_callback=None):
    """Map single depot to client spec"""
    client_name = get_client_name()
    if not client_name:
        raise RuntimeError(
            "Client name not initialized. Please check P4 configuration."
        )

    depot_name = (
        "BENI"
        if "beni" in depot_path.lower()
        else "FLUMEN" if "flumen" in depot_path.lower() else "DEPOT"
    )
    if log_callback:
        log_callback(f"[MAPPING] Mapping {depot_name} to client spec...")

    client_spec = run_cmd("p4 client -o")
    lines = client_spec.splitlines()
    new_lines = []
    for line in lines:
        if depot_path in line:
            continue
        new_lines.append(line)
    new_lines.append(f"\t{depot_path}\t//{client_name}/{depot_path[2:]}")
    new_spec = "\n".join(new_lines)
    run_cmd("p4 client -i", input_text=new_spec)

    if log_callback:
        log_callback("[OK] Mapping completed.")


def map_two_depots_silent(depot1, depot2):
    """Map two depots to client spec without logging"""
    client_name = get_client_name()
    if not client_name:
        raise RuntimeError(
            "Client name not initialized. Please check P4 configuration."
        )

    client_spec = run_cmd("p4 client -o")
    lines = client_spec.splitlines()
    new_lines = []
    for line in lines:
        if depot1 in line or depot2 in line:
            continue
        new_lines.append(line)
    new_lines.append(f"\t{depot1}\t//{client_name}/{depot1[2:]}")
    new_lines.append(f"\t{depot2}\t//{client_name}/{depot2[2:]}")
    new_spec = "\n".join(new_lines)
    run_cmd("p4 client -i", input_text=new_spec)


def sync_file(depot_path, log_callback):
    """Sync file from depot"""
    log_callback(f"[SYNC] Syncing {depot_path}...")
    run_cmd(f"p4 sync {depot_path}")
    log_callback("[OK] Synced.")


def sync_file_silent(depot_path):
    """Sync file from depot without logging"""
    run_cmd(f"p4 sync {depot_path}")


def checkout_file(depot_path, changelist_id, log_callback):
    """Checkout file for editing"""
    log_callback(f"[CHECKOUT] Checking out {depot_path}...")
    run_cmd(f"p4 edit -c {changelist_id} {depot_path}")
    log_callback("[OK] Checked out.")


def checkout_file_silent(depot_path, changelist_id):
    """Checkout file for editing without logging"""
    run_cmd(f"p4 edit -c {changelist_id} {depot_path}")


# =====================================================================================
# Workspace helpers (accept TEMPLATE_* workspace name and resolve to depot file path)
# =====================================================================================

_DEVICE_COMMON_REGEX = re.compile(r"^(.+?)/device/([^/]+?)_common/", re.IGNORECASE)


def is_workspace_like(user_input: str) -> bool:
    """Return True if the input string looks like a P4 workspace template name."""
    if not user_input:
        return False
    return user_input.strip().upper().startswith("TEMPLATE")


def _parse_view_left_depots_from_text(spec_text: str) -> List[str]:
    """Parse `p4 client -o <name>` output text and return list of left depot mappings."""
    lines = spec_text.splitlines()
    depots: List[str] = []
    in_view = False
    for line in lines:
        if not in_view:
            if line.strip().startswith("View:"):
                in_view = True
            continue
        if line.startswith("\t") or line.startswith("    "):
            parts = line.strip().split()
            if not parts:
                continue
            left = parts[0]
            if left.startswith("//"):
                depots.append(left)
        else:
            if in_view:
                break
    return depots


def _parse_view_left_depots_from_dict(spec: dict) -> List[str]:
    """Parse spec dict returned by P4Python fetch_client."""
    depots: List[str] = []
    view = spec.get("View")
    if isinstance(view, list):
        for entry in view:
            if not entry:
                continue
            if isinstance(entry, str):
                parts = entry.strip().split()
                if parts and parts[0].startswith("//"):
                    depots.append(parts[0])
    return depots


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


def find_device_common_mk_from_workspace(workspace_name, log_callback=None):
    """
    Enhanced workspace resolution using parse_process.py approach
    Find device_common.mk path from workspace name using P4Python
    """
    if log_callback:
        log_callback(
            f"[WORKSPACE] Resolving workspace to device_common.mk: {workspace_name}"
        )

    try:
        from P4 import P4, P4Exception

        p4 = P4()
        try:
            p4.connect()

            # Get client spec information
            client_spec = p4.fetch_client("-o", workspace_name)

            # Regex pattern to find device_common.mk paths
            # Pattern looks for: //depot_name/*/device/*_common/
            pattern = re.compile(r"(^[^.]+?/)device/[^/]+?_common/")

            # Search in View mappings
            found_paths = []
            for view in client_spec.get("View", []):
                # Get depot path (left side of mapping)
                depot_path = view.split()[0] if isinstance(view, str) else view[0]
                match = pattern.search(depot_path)
                if match:
                    # Remove "..." at the end and add "device_common.mk"
                    clean_path = depot_path.rstrip("...")
                    complete_path = clean_path + "device_common.mk"
                    found_paths.append(complete_path)

            # Return first valid path
            if found_paths:
                result_path = found_paths[0]
                if validate_depot_path(result_path):
                    if log_callback:
                        log_callback(f"[OK] Resolved workspace to: {result_path}")
                    return result_path

            return None

        finally:
            try:
                p4.disconnect()
            except:
                pass
    except Exception:
        pass

    # Fallback to CLI approach if P4Python fails
    if log_callback:
        log_callback("[FALLBACK] Using CLI approach for workspace resolution...")

    result = subprocess.run(
        f"p4 client -o {workspace_name}", capture_output=True, text=True, shell=True
    )
    if result.returncode != 0:
        return None

    left_depots = _parse_view_left_depots_from_text(result.stdout)
    depot_path = _extract_device_common_from_depots(left_depots)
    return depot_path


def resolve_workspace_to_device_common_path(workspace_name: str) -> str:
    """
    Enhanced: Use parse_process.py approach for workspace resolution
    Resolve TEMPLATE_* workspace to the depot path of device_common.mk.
    """
    workspace_name = workspace_name.strip()
    if not workspace_name:
        raise RuntimeError("Workspace name is empty.")

    # Try enhanced P4Python approach first
    try:
        result_path = find_device_common_mk_from_workspace(workspace_name)
        if result_path and validate_depot_path(result_path):
            return result_path
    except Exception:
        pass

    # Fallback to CLI approach
    result = subprocess.run(
        f"p4 client -o {workspace_name}", capture_output=True, text=True, shell=True
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to fetch workspace '{workspace_name}': {result.stderr.strip()}"
        )

    left_depots = _parse_view_left_depots_from_text(result.stdout)
    depot_path = _extract_device_common_from_depots(left_depots)
    if not depot_path:
        raise RuntimeError(
            "Could not locate device_common.mk from workspace View. "
            "Ensure the View contains a 'device/<model>_common/' mapping."
        )
    return depot_path


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
        return resolve_workspace_to_device_common_path(text)
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


def _resolve_integration_chain(depot_path, target_name, log_callback):
    """
    Helper function to resolve integration source from a depot path
    
    Returns:
        Optional[str]: Integration source depot path, or None if not found
    """
    # Map vÃ  sync depot path
    map_single_depot(depot_path)
    sync_file_silent(depot_path)
    
    # Get integration source
    source = get_integration_source_depot_path(depot_path, log_callback)
    
    if source and validate_depot_path(source):
        log_callback(f"[AUTO] Successfully resolved {target_name}: {source}")
        return source
    else:
        if source:
            log_callback(f"[WARNING] {target_name} integration source does not exist: {source}")
        else:
            log_callback(f"[WARNING] No integration history found for: {depot_path}")
        return None

def _resolve_cascading_from_rel(rel_input, log_callback, raise_on_error=False):
    """
    Resolve FLUMEN and BENI cascading from REL
    
    Args:
        rel_input: REL input (workspace or depot path)
        log_callback: Logging callback
        raise_on_error: If True, raise error; if False, return None on error
        
    Returns:
        Tuple[Optional[str], Optional[str]]: (resolved_flumen, resolved_beni)
    """
    try:
        # Resolve REL to depot path
        rel_depot_path = resolve_user_input_to_depot_path(rel_input)
        
        if not validate_depot_path(rel_depot_path):
            msg = f"REL path does not exist: {rel_depot_path}"
            if raise_on_error:
                raise RuntimeError(msg)
            log_callback(f"[WARNING] {msg}")
            return None, None
        
        # Resolve FLUMEN from REL
        flumen_source = _resolve_integration_chain(rel_depot_path, "FLUMEN from REL", log_callback)
        
        if not flumen_source:
            msg = f"No integration history found for REL: {rel_depot_path}"
            if raise_on_error:
                raise RuntimeError(msg)
            return None, None
        
        # Resolve BENI from FLUMEN
        beni_source = _resolve_integration_chain(flumen_source, "BENI from FLUMEN", log_callback)
        
        if not beni_source:
            msg = f"No integration history found for FLUMEN: {flumen_source}"
            if raise_on_error:
                raise RuntimeError(msg)
            return flumen_source, None
        
        return flumen_source, beni_source
        
    except Exception as e:
        if raise_on_error:
            raise
        log_callback(f"[WARNING] Error in cascading resolution: {str(e)}")
        return None, None

def _resolve_beni_from_flumen(flumen_input, log_callback, raise_on_error=False):
    """
    Resolve BENI from FLUMEN
    
    Args:
        flumen_input: FLUMEN input (workspace or depot path)
        log_callback: Logging callback
        raise_on_error: If True, raise error; if False, return None on error
        
    Returns:
        Optional[str]: resolved_beni or None
    """
    try:
        # Resolve FLUMEN to depot path
        flumen_depot_path = resolve_user_input_to_depot_path(flumen_input)
        
        if not validate_depot_path(flumen_depot_path):
            msg = f"FLUMEN path does not exist: {flumen_depot_path}"
            if raise_on_error:
                raise RuntimeError(msg)
            log_callback(f"[WARNING] {msg}")
            return None
        
        # Resolve BENI from FLUMEN
        beni_source = _resolve_integration_chain(flumen_depot_path, "BENI from FLUMEN", log_callback)
        
        if not beni_source:
            msg = f"No integration history found for FLUMEN: {flumen_depot_path}"
            if raise_on_error:
                raise RuntimeError(msg)
        
        return beni_source
        
    except Exception as e:
        if raise_on_error:
            raise
        log_callback(f"[WARNING] Error resolving BENI from FLUMEN: {str(e)}")
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
    - REL + VINCE â†’ Auto-resolve FLUMEN from REL â†’ Auto-resolve BENI from FLUMEN
    - FLUMEN + VINCE â†’ Auto-resolve BENI from FLUMEN
    - BENI + VINCE â†’ No auto-resolve needed
    - If both FLUMEN and REL provided â†’ Auto-resolve BENI from FLUMEN
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
        

    try:
        # Case 1: REL + VINCE provided, but FLUMEN + BENI empty
        # Auto-resolve: REL â†’ FLUMEN â†’ BENI (cascading)
        if rel_input and vince_input and not flumen_input and not beni_input:
            flumen_source, beni_source = _resolve_cascading_from_rel(rel_input, log_callback, raise_on_error=False)
            if flumen_source:
                resolved_flumen = flumen_source
            if beni_source:
                resolved_beni = beni_source

        # Case 2: FLUMEN + VINCE provided, but BENI empty (REL may or may not be provided)
        # Auto-resolve: FLUMEN â†’ BENI
        elif flumen_input and vince_input and not beni_input:
            beni_source = _resolve_beni_from_flumen(flumen_input, log_callback, raise_on_error=False)
            if beni_source:
                resolved_beni = beni_source

        # Case 3: Both FLUMEN and REL provided + VINCE, but BENI empty
        # Auto-resolve: FLUMEN â†’ BENI (prefer FLUMEN over REL for BENI resolution)
        

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

    Args:
        vince_input: VINCE input (workspace or depot path) - mandatory
        flumen_input: FLUMEN input (workspace or depot path) - optional
        beni_input: BENI input (workspace or depot path) - optional
        rel_input: REL input (workspace or depot path) - optional
        log_callback: Callback function for logging

    Returns:
        Tuple: (resolved_beni, resolved_flumen, resolved_rel, resolved_vince)

    Auto-resolve Logic Matrix:
    - VINCE + FLUMEN (BENI empty) â†’ Auto-resolve BENI from FLUMEN
    - VINCE + REL (FLUMEN + BENI empty) â†’ Auto-resolve FLUMEN from REL â†’ Auto-resolve BENI from FLUMEN
    - VINCE + FLUMEN + REL (BENI empty) â†’ Auto-resolve BENI from FLUMEN
    - Full input (4 fields) â†’ Process normally, no auto-resolve
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

    log_callback("[AUTO-RESOLVE] Analyzing input combination for auto-resolve...")
    log_callback(f"[INPUT] VINCE: {vince_input}")
    log_callback(f"[INPUT] FLUMEN: {flumen_input if flumen_input else '(empty)'}")
    log_callback(f"[INPUT] BENI: {beni_input if beni_input else '(empty)'}")
    log_callback(f"[INPUT] REL: {rel_input if rel_input else '(empty)'}")

    try:
        # Case 1: VINCE + REL provided, but FLUMEN + BENI empty
        # Auto-resolve: REL â†’ FLUMEN â†’ BENI (cascading)
        if vince_input and rel_input and not flumen_input and not beni_input:
            resolved_flumen, resolved_beni = _resolve_cascading_from_rel(rel_input, log_callback, raise_on_error=True)

        # Case 2: VINCE + FLUMEN provided, but BENI empty (REL may or may not be provided)
        # Auto-resolve: FLUMEN â†’ BENI
        elif vince_input and flumen_input and not beni_input:
            resolved_beni = _resolve_beni_from_flumen(flumen_input, log_callback, raise_on_error=True)

        # Case 3: All fields provided or no auto-resolve needed
        else:
            log_callback(
                "[AUTO-RESOLVE] No auto-resolve needed - processing with provided inputs"
            )

        # Log final resolved values
        log_callback("[AUTO-RESOLVE] Final resolved values:")
        log_callback(f"[RESOLVED] VINCE: {resolved_vince}")
        log_callback(
            f"[RESOLVED] FLUMEN: {resolved_flumen if resolved_flumen else '(not provided)'}"
        )
        log_callback(
            f"[RESOLVED] BENI: {resolved_beni if resolved_beni else '(not provided)'}"
        )
        log_callback(
            f"[RESOLVED] REL: {resolved_rel if resolved_rel else '(not provided)'}"
        )

        return resolved_beni, resolved_flumen, resolved_rel, resolved_vince

    except Exception as e:
        log_callback(f"[AUTO-RESOLVE ERROR] {str(e)}")
        raise RuntimeError(f"Auto-resolve failed: {str(e)}")