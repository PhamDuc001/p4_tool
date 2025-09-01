"""
P4 command operations - REFACTORED VERSION
Handles all Perforce commands and validations
Enhanced with centralized utilities and reduced code duplication
"""
import subprocess
import re
from typing import List, Optional, Tuple
from config.p4_config import get_client_name
from core.core_utils import (
    get_client_mapper, get_path_validator, get_auto_resolver
)

# Export the function for use by other modules  
__all__ = ['get_client_name', 'run_cmd', 'validate_depot_path', 'validate_device_common_mk_path',
           'create_changelist', 'create_changelist_silent', 'map_client', 'map_client_two_paths', 
           'map_single_depot', 'map_two_depots_silent', 'sync_file', 'sync_file_silent', 
           'checkout_file', 'checkout_file_silent', 'is_workspace_like', 
           'resolve_workspace_to_device_common_path', 'resolve_user_input_to_depot_path',
           'auto_resolve_missing_branches', 'get_integration_source_depot_path',
           'find_device_common_mk_from_workspace']

def run_cmd(cmd, input_text=None):
    """Execute command and return output"""
    result = subprocess.run(cmd, input_text=input_text, capture_output=True, text=True, shell=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\n{result.stderr}")
    return result.stdout.strip()

# Delegate to centralized utilities
def validate_depot_path(depot_path):
    """Validate if depot path exists in Perforce"""
    return get_path_validator().validate_depot_path(depot_path)

def validate_device_common_mk_path(depot_path):
    """
    Validate if depot path exists and is a device_common.mk file
    Returns (exists, is_device_common_mk)
    """
    return get_path_validator().validate_device_common_mk_path(depot_path)

def is_workspace_like(user_input: str) -> bool:
    """Return True if the input string looks like a P4 workspace template name."""
    return get_path_validator().is_workspace_like(user_input)

# Changelist operations
def create_changelist(log_callback):
    """Create pending changelist"""
    log_callback("[STEP 1] Creating pending changelist...")
    changelist_spec = run_cmd("p4 change -o")
    new_spec = re.sub(r"<enter description here>", "Auto changelist - Sync and update LMKD/Chimera", changelist_spec)
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

# Client mapping operations - delegated to centralized mapper
def map_client(beni_depot, vince_depot, flumen_depot, log_callback):
    """Map multiple depots to client spec"""
    get_client_mapper().map_depots([beni_depot, vince_depot, flumen_depot], log_callback)

def map_client_two_paths(target_depot, vince_depot, log_callback):
    """Map two depots to client spec"""
    get_client_mapper().map_two_depots(target_depot, vince_depot, log_callback)

def map_single_depot(depot_path, log_callback=None):
    """Map single depot to client spec"""
    get_client_mapper().map_single_depot(depot_path, log_callback)

def map_two_depots_silent(depot1, depot2):
    """Map two depots to client spec without logging"""
    get_client_mapper().map_two_depots(depot1, depot2, silent=True)

# File operations
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
        log_callback(f"[WORKSPACE] Resolving workspace to device_common.mk: {workspace_name}")
    
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
            for view in client_spec.get('View', []):
                # Get depot path (left side of mapping)
                depot_path = view.split()[0] if isinstance(view, str) else view[0]
                match = pattern.search(depot_path)
                if match:
                    # Remove "..." at the end and add "device_common.mk"
                    clean_path = depot_path.rstrip('...')
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
    
    result = subprocess.run(f"p4 client -o {workspace_name}", capture_output=True, text=True, shell=True)
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
    result = subprocess.run(f"p4 client -o {workspace_name}", capture_output=True, text=True, shell=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to fetch workspace '{workspace_name}': {result.stderr.strip()}")

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
# AUTO-RESOLVE CASCADING FUNCTIONALITY - REFACTORED
# =====================================================================================

def get_integration_source_depot_path(depot_path: str, log_callback) -> Optional[str]:
    """
    Get integration source depot path from p4 filelog version #1
    Delegated to centralized auto resolver
    """
    return get_auto_resolver().get_integration_source_depot_path(depot_path, log_callback)

def auto_resolve_missing_branches(vince_input: str, flumen_input: str, beni_input: str, 
                                 rel_input: str, log_callback) -> Tuple[str, str, str, str]:
    """
    Auto-resolve missing branches from integration history - REFACTORED VERSION
    Uses centralized auto resolver for consistent behavior
    
    Args:
        vince_input: VINCE input (workspace or depot path) - mandatory
        flumen_input: FLUMEN input (workspace or depot path) - optional
        beni_input: BENI input (workspace or depot path) - optional  
        rel_input: REL input (workspace or depot path) - optional
        log_callback: Callback function for logging
    
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
    
    log_callback("[AUTO-RESOLVE] Analyzing input combination for auto-resolve...")
    log_callback(f"[INPUT] VINCE: {vince_input}")
    log_callback(f"[INPUT] FLUMEN: {flumen_input if flumen_input else '(empty)'}")
    log_callback(f"[INPUT] BENI: {beni_input if beni_input else '(empty)'}")
    log_callback(f"[INPUT] REL: {rel_input if rel_input else '(empty)'}")
    
    try:
        auto_resolver = get_auto_resolver()
        
        # Case 1: VINCE + REL provided, but FLUMEN + BENI empty
        # Auto-resolve: REL → FLUMEN → BENI (cascading)
        if vince_input and rel_input and not flumen_input and not beni_input:
            log_callback("[AUTO-RESOLVE] Case detected: VINCE + REL → Auto-resolve FLUMEN and BENI")
            
            # Resolve REL input to depot path
            rel_depot_path = resolve_user_input_to_depot_path(rel_input)
            if not validate_depot_path(rel_depot_path):
                raise RuntimeError(f"REL path does not exist: {rel_depot_path}")
            
            # Use centralized cascading resolution: REL → FLUMEN → BENI
            cascading_result = auto_resolver.resolve_cascading_branches(
                rel_depot_path, ["REL", "FLUMEN", "BENI"], log_callback
            )
            
            resolved_flumen = cascading_result.get("FLUMEN")
            resolved_beni = cascading_result.get("BENI")
        
        # Case 2: VINCE + FLUMEN provided, but BENI empty (REL may or may not be provided)
        # Auto-resolve: FLUMEN → BENI
        elif vince_input and flumen_input and not beni_input:
            log_callback("[AUTO-RESOLVE] Case detected: VINCE + FLUMEN → Auto-resolve BENI")
            
            # Resolve FLUMEN input to depot path
            flumen_depot_path = resolve_user_input_to_depot_path(flumen_input)
            if not validate_depot_path(flumen_depot_path):
                raise RuntimeError(f"FLUMEN path does not exist: {flumen_depot_path}")
            
            # Use centralized resolution: FLUMEN → BENI
            cascading_result = auto_resolver.resolve_cascading_branches(
                flumen_depot_path, ["FLUMEN", "BENI"], log_callback
            )
            
            resolved_beni = cascading_result.get("BENI")
        
        # Case 3: All fields provided or no auto-resolve needed
        else:
            log_callback("[AUTO-RESOLVE] No auto-resolve needed - processing with provided inputs")
        
        # Log final resolved values
        log_callback("[AUTO-RESOLVE] Final resolved values:")
        log_callback(f"[RESOLVED] VINCE: {resolved_vince}")
        log_callback(f"[RESOLVED] FLUMEN: {resolved_flumen if resolved_flumen else '(not provided)'}")
        log_callback(f"[RESOLVED] BENI: {resolved_beni if resolved_beni else '(not provided)'}")
        log_callback(f"[RESOLVED] REL: {resolved_rel if resolved_rel else '(not provided)'}")
        
        return resolved_beni, resolved_flumen, resolved_rel, resolved_vince
        
    except Exception as e:
        log_callback(f"[AUTO-RESOLVE ERROR] {str(e)}")
        raise RuntimeError(f"Auto-resolve failed: {str(e)}")