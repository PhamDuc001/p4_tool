"""
P4 command operations
Handles all Perforce commands and validations
Enhanced with auto-resolve cascading functionality
"""
import subprocess
import re
from typing import List, Optional, Tuple
from config.p4_config import get_client_name

# Export the function for use by other modules  
__all__ = ['get_client_name', 'run_cmd', 'validate_depot_path', 'validate_device_common_mk_path',
           'create_changelist', 'create_changelist_silent', 'map_client', 'map_client_two_paths', 
           'map_single_depot', 'map_two_depots_silent', 'sync_file', 'sync_file_silent', 
           'checkout_file', 'checkout_file_silent', 'is_workspace_like', 
           'resolve_workspace_to_device_common_path', 'resolve_user_input_to_depot_path',
           'auto_resolve_missing_branches', 'get_integration_source']

def run_cmd(cmd, input_text=None):
    """Execute command and return output"""
    result = subprocess.run(cmd, input=input_text, capture_output=True, text=True, shell=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\n{result.stderr}")
    return result.stdout.strip()

def validate_depot_path(depot_path):
    """Validate if depot path exists in Perforce"""
    try:
        result = subprocess.run(f"p4 files {depot_path}", capture_output=True, text=True, shell=True)
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
        result = subprocess.run(f"p4 files {depot_path}", capture_output=True, text=True, shell=True)
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

def map_client(beni_depot, vince_depot, flumen_depot, log_callback):
    """Map multiple depots to client spec"""
    client_name = get_client_name()
    if not client_name:
        raise RuntimeError("Client name not initialized. Please check P4 configuration.")
    
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
        raise RuntimeError("Client name not initialized. Please check P4 configuration.")
    
    target_name = "BENI" if "beni" in target_depot.lower() else "FLUMEN" if "flumen" in target_depot.lower() else "TARGET"
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
        raise RuntimeError("Client name not initialized. Please check P4 configuration.")
    
    depot_name = "BENI" if "beni" in depot_path.lower() else "FLUMEN" if "flumen" in depot_path.lower() else "DEPOT"
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
        raise RuntimeError("Client name not initialized. Please check P4 configuration.")
    
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
    """Parse `p4 client -o <name>` output text and return list of left depot mappings.

    Lines under the `View:` section typically look like:
        \t//depot/path/... //clientName/depot/path/...
    This extracts the left (depot) side for all mappings.
    """
    lines = spec_text.splitlines()
    depots: List[str] = []
    in_view = False
    for line in lines:
        if not in_view:
            if line.strip().startswith("View:"):
                in_view = True
            continue
        # In view block: indented lines until a non-indented header
        if line.startswith("\t") or line.startswith("    "):
            parts = line.strip().split()
            if not parts:
                continue
            # Expect at least two columns: <//depot/...> <//client/...>
            left = parts[0]
            if left.startswith("//"):
                depots.append(left)
        else:
            # End of View section
            if in_view:
                break
    return depots

def _parse_view_left_depots_from_dict(spec: dict) -> List[str]:
    """Parse spec dict returned by P4Python fetch_client.

    spec.get('View') is usually a list of strings with two columns.
    Return the left depot paths.
    """
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
    build the device_common.mk depot file path.

    Returns the first valid depot path found, or None.
    """
    for left in left_depots:
        # Find a segment ending with /device/<model>_common/
        match = _DEVICE_COMMON_REGEX.search(left)
        if not match:
            continue
        base_vendor_dir = match.group(1)  # path before /device
        # Derive model from the last folder name of base_vendor_dir (e.g., a07_vendor -> a07)
        last_segment = base_vendor_dir.rstrip("/").split("/")[-1]
        model = last_segment.split("_")[0] if "_" in last_segment else last_segment
        candidate = f"{base_vendor_dir}/device/{model}_common/device_common.mk"
        # Validate existence quickly via p4 files
        if validate_depot_path(candidate):
            return candidate
    return None

def resolve_workspace_to_device_common_path(workspace_name: str) -> str:
    """Resolve TEMPLATE_* workspace to the depot path of device_common.mk.

    Tries P4Python first; falls back to `p4 client -o <workspace_name>` parsing.
    Raises RuntimeError if not found or invalid.
    """
    workspace_name = workspace_name.strip()
    if not workspace_name:
        raise RuntimeError("Workspace name is empty.")

    # Try P4Python if available
    try:
        from P4 import P4, P4Exception  # type: ignore
        p4 = P4()
        try:
            p4.connect()
            spec = p4.fetch_client(workspace_name)
            left_depots = _parse_view_left_depots_from_dict(spec)
            depot_path = _extract_device_common_from_depots(left_depots)
            if depot_path:
                return depot_path
        finally:
            try:
                p4.disconnect()
            except Exception:
                pass
    except Exception:
        # P4Python not available or failed; fallback to CLI
        pass

    # Fallback: CLI fetch
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
# AUTO-RESOLVE CASCADING FUNCTIONALITY
# =====================================================================================

def get_integration_source(depot_path: str) -> Optional[str]:
    """
    Get integration source from p4 filelog -i -m 1
    Parse integration history and return source depot path
    Returns None if no integration source found or parsing failed
    """
    try:
        # Run p4 filelog command to get integration history
        result = subprocess.run(
            f"p4 filelog -i -m 1 {depot_path}", 
            capture_output=True, text=True, shell=True
        )
        
        if result.returncode != 0:
            return None
        
        output = result.stdout.strip()
        if not output:
            return None
        
        # Parse integration history
        # Expected format: ... integration from //depot/path/...#version,#version
        lines = output.split('\n')
        for line in lines:
            line = line.strip()
            if 'integration from' in line:
                # Extract source path using regex
                # Pattern: integration from //depot/path/...#version,#version
                # or: integration from //depot/path/...#version
                match = re.search(r'integration from (//[^#]+)', line)
                if match:
                    source_path = match.group(1).strip()
                    return source_path
        
        return None
        
    except Exception:
        return None

def auto_resolve_missing_branches(vince_input: str, flumen_input: str, beni_input: str, 
                                 rel_input: str, log_callback) -> Tuple[str, str, str, str]:
    """
    Auto-resolve missing branches from integration history
    
    Args:
        vince_input: VINCE input (workspace or depot path) - mandatory
        flumen_input: FLUMEN input (workspace or depot path) - optional
        beni_input: BENI input (workspace or depot path) - optional  
        rel_input: REL input (workspace or depot path) - optional
        log_callback: Callback function for logging
    
    Returns:
        Tuple: (resolved_beni, resolved_flumen, resolved_rel, resolved_vince)
    
    Auto-resolve Logic Matrix:
    - VINCE + FLUMEN (BENI empty) → Auto-resolve BENI from FLUMEN
    - VINCE + REL (FLUMEN + BENI empty) → Auto-resolve FLUMEN from REL → Auto-resolve BENI from FLUMEN  
    - VINCE + FLUMEN + REL (BENI empty) → Auto-resolve BENI from FLUMEN
    - Full input (4 fields) → Process normally, no auto-resolve
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
        # Auto-resolve: REL → FLUMEN → BENI (cascading)
        if vince_input and rel_input and not flumen_input and not beni_input:
            log_callback("[AUTO-RESOLVE] Case detected: VINCE + REL → Auto-resolve FLUMEN and BENI")
            
            # Step 1: Resolve REL to depot path and sync
            rel_depot_path = resolve_user_input_to_depot_path(rel_input)
            if not validate_depot_path(rel_depot_path):
                raise RuntimeError(f"REL path does not exist: {rel_depot_path}")
            
            # Map and sync REL to get latest
            map_single_depot(rel_depot_path)
            sync_file_silent(rel_depot_path)
            
            # Step 2: Get integration source for FLUMEN from REL
            flumen_source = get_integration_source(rel_depot_path)
            if not flumen_source:
                raise RuntimeError(f"No integration history found for REL: {rel_depot_path}")
            
            # Validate FLUMEN source exists
            if not validate_depot_path(flumen_source):
                raise RuntimeError(f"Integration source does not exist: {flumen_source}")
            
            resolved_flumen = flumen_source
            log_callback(f"[AUTO] Detected FLUMEN from REL: {flumen_source}")
            
            # Step 3: Get integration source for BENI from FLUMEN
            # Map and sync FLUMEN first
            map_single_depot(flumen_source)
            sync_file_silent(flumen_source)
            
            beni_source = get_integration_source(flumen_source)
            if not beni_source:
                raise RuntimeError(f"No integration history found for FLUMEN: {flumen_source}")
            
            # Validate BENI source exists
            if not validate_depot_path(beni_source):
                raise RuntimeError(f"Integration source does not exist: {beni_source}")
            
            resolved_beni = beni_source
            log_callback(f"[AUTO] Detected BENI from FLUMEN: {beni_source}")
        
        # Case 2: VINCE + FLUMEN provided, but BENI empty (REL may or may not be provided)
        # Auto-resolve: FLUMEN → BENI
        elif vince_input and flumen_input and not beni_input:
            log_callback("[AUTO-RESOLVE] Case detected: VINCE + FLUMEN → Auto-resolve BENI")
            
            # Step 1: Resolve FLUMEN to depot path and sync
            flumen_depot_path = resolve_user_input_to_depot_path(flumen_input)
            if not validate_depot_path(flumen_depot_path):
                raise RuntimeError(f"FLUMEN path does not exist: {flumen_depot_path}")
            
            # Map and sync FLUMEN to get latest
            map_single_depot(flumen_depot_path)
            sync_file_silent(flumen_depot_path)
            
            # Step 2: Get integration source for BENI from FLUMEN
            beni_source = get_integration_source(flumen_depot_path)
            if not beni_source:
                raise RuntimeError(f"No integration history found for FLUMEN: {flumen_depot_path}")
            
            # Validate BENI source exists
            if not validate_depot_path(beni_source):
                raise RuntimeError(f"Integration source does not exist: {beni_source}")
            
            resolved_beni = beni_source
            log_callback(f"[AUTO] Detected BENI from FLUMEN: {beni_source}")
        
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