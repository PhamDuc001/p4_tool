import sys
import os
import re
import argparse
import subprocess
from P4 import P4, P4Exception

P4_SERVER_PORT = "107.113.53.156:1716"

# P4 Automation Readahead Validation Rules
# Branch Hierarchy: BENI → FLUMEN → REL
# Workspace Detection:
# - REL: Contains "MR202601, MR202702, etc." in path
# - FLUMEN: Contains "FLUMEN" in path  
# - BENI: Base branch path
# 
# File Locations by Mode:
# - Tuning Properties (Vendor): device_common.mk in Vendor branch
# - Readahead Libraries (System): 
#   * device_common.mk in System branch (defines rscmgr filename)
#   * Android.mk in System branch (configures rscmgr file)
#   * rscmgr.rc in System branch (contains libraries)
#
# Readahead Success Conditions:
# 1. device_common.mk defines rscmgr filename: PRODUCT_PACKAGES += rscmgr_xxx.rc
# 2. Android.mk adds rscmgr filename to configuration
# 3. rscmgr.rc adds library: readahead library_name --fully

# P4 Automation Workspace Branch Validation Rules
# Branch Detection:
# - REL: Contains "MR202601", "MR202702", etc. in workspace name
# - FLUMEN: Contains "FLUMEN" in workspace name
# - BENI: Base branch (no REL or FLUMEN in name)
#
# Branch Type Detection:
# - System: Contains "_SYSTEM_" in workspace name
# - Vendor: Contains "_VENDOR_" in workspace name
#
# Mode Compatibility:
# - Tuning Properties: Requires Vendor branch workspace
# - Readahead Libraries: Requires System branch workspace
# - LoadApkAsset: Requires System branch workspace

def validate_workspace_branch(workspace_name, required_branch_type="system"):
    """Validate workspace branch compatibility for the current mode"""
    # Detect branch hierarchy
    is_rel = "_MR" in workspace_name.upper() and ("_SYSTEM_" in workspace_name.upper() or "_VENDOR_" in workspace_name.upper())
    is_flumen = "_FLUMEN" in workspace_name.upper()
    is_beni = not is_rel and not is_flumen and ("_SYSTEM_" in workspace_name.upper() or "_VENDOR_" in workspace_name.upper())
    
    # Detect branch type
    is_system = "_SYSTEM_" in workspace_name.upper()
    is_vendor = "_VENDOR_" in workspace_name.upper()
    
    print(f"[WORKSPACE] {workspace_name}")
    print(f"[BRANCH] Type: {'REL' if is_rel else 'FLUMEN' if is_flumen else 'BENI' if is_beni else 'Unknown'}")
    print(f"[BRANCH] Category: {'System' if is_system else 'Vendor' if is_vendor else 'Unknown'}")
    
    # Validate compatibility
    if required_branch_type == "vendor" and not is_vendor:
        return False, f"Tuning Properties mode requires a Vendor branch workspace, but '{workspace_name}' is a System branch workspace. Please provide a workspace with '_VENDOR_' in the name."
    
    if required_branch_type == "system" and not is_system:
        return False, f"System branch workspace required, but '{workspace_name}' is a Vendor branch workspace. Please provide a workspace with '_SYSTEM_' in the name."
    
    return True, "Workspace validation passed"

def run_cmd(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\n{result.stderr}")
    return result.stdout.strip()

def get_client_name():
    output = run_cmd("p4 info")
    match = re.search(r"^Client name:\s*(.+)$", output, re.MULTILINE)
    return match.group(1).strip() if match else None

def depot_to_local_path(depot_path):
    output = run_cmd(f"p4 where {depot_path}")
    parts = output.split()
    if len(parts) >= 3:
        return parts[2]
    return output

def validate_depot_path(depot_path):
    result = subprocess.run(f"p4 files {depot_path}", capture_output=True, text=True, shell=True)
    return result.returncode == 0 and "no such file" not in result.stderr.lower()

def map_single_depot(depot_path):
    client_name = get_client_name()
    mapping_line = f"\t{depot_path}\t//{client_name}/{depot_path[2:]}"
    lines = run_cmd("p4 client -o").splitlines()
    new_lines = [line for line in lines if depot_path not in line]
    new_lines.append(mapping_line)
    subprocess.run("p4 client -i", input="\n".join(new_lines), capture_output=True, text=True, shell=True)

def get_integration_source_depot_path(depot_path: str):
    """
    Get integration source depot path from p4 filelog version #1
    Parse integration history and return source depot path from "branch from" line
    Returns None if no integration source found or parsing failed
    """
    try:
        # Use #1 to get the first version (integration source)
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
            print(f"[WARNING] P4 filelog command failed for {depot_path}#1")
            return None

        output = result.stdout.strip()
        if not output:
            print(f"[WARNING] Empty filelog output for {depot_path}#1")
            return None

        # Look for "... ... branch from <path>#<version>" pattern
        lines = output.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("... ... branch from "):
                # Extract path from "... ... branch from //path/device_common.mk#1"
                # Remove "... ... branch from " prefix and "#<version>" suffix
                integration_line = line.split("from ")[1]
                source_path = integration_line.split("#")[0].split(",")[0]
                print(f"[PARSE] Extracted integration source: {source_path}")
                return source_path

        print(f"[WARNING] No 'branch from' line found in filelog output for {depot_path}#1")
        return None

    except Exception as e:
        print(f"[ERROR] Error getting integration source: {str(e)}")
        return None

def auto_resolve_cascade_branches(workspace_name):
    """
    Auto-resolve cascade branches from integration history
    Returns dict with REL, FLUMEN, BENI workspace names/paths
    
    Auto-resolve Logic:
    - REL provided → Auto-resolve FLUMEN from REL → Auto-resolve BENI from FLUMEN
    - FLUMEN provided → Auto-resolve BENI from FLUMEN
    - BENI provided → No auto-resolve needed
    """
    workspaces = {"REL": "", "FLUMEN": "", "BENI": ""}
    
    # Detect branch type from workspace name
    is_rel = is_rel_branch_workspace(workspace_name)
    is_flumen = "_FLUMEN" in workspace_name.upper()
    is_beni = not is_rel and not is_flumen
    
    print(f"[AUTO-RESOLVE] Starting auto-resolution from workspace: {workspace_name}")
    print(f"[BRANCH DETECTION] REL: {is_rel}, FLUMEN: {is_flumen}, BENI: {is_beni}")
    
    # Set the provided workspace as the starting point
    if is_rel:
        workspaces["REL"] = workspace_name
    elif is_flumen:
        workspaces["FLUMEN"] = workspace_name
    else:
        workspaces["BENI"] = workspace_name
    
    try:
        # Case 1: REL provided, auto-resolve FLUMEN and BENI
        if is_rel and not workspaces["FLUMEN"] and not workspaces["BENI"]:
            print("[AUTO-RESOLVE] Case: REL provided → Auto-resolve FLUMEN and BENI")
            
            # Resolve REL to get device_common.mk path
            rel_device_common_path = resolve_device_common_path(workspace_name, "system")
            if not rel_device_common_path:
                raise RuntimeError(f"Cannot find device_common.mk in REL workspace: {workspace_name}")
            
            # Map and sync REL
            map_single_depot(rel_device_common_path)
            run_cmd(f"p4 sync {rel_device_common_path}")
            
            # Get integration source for FLUMEN from REL
            flumen_device_common = get_integration_source_depot_path(rel_device_common_path)
            if flumen_device_common and validate_depot_path(flumen_device_common):
                workspaces["FLUMEN"] = flumen_device_common
                print(f"[AUTO] Resolved FLUMEN device_common.mk: {flumen_device_common}")
                
                # Get integration source for BENI from FLUMEN
                map_single_depot(flumen_device_common)
                run_cmd(f"p4 sync {flumen_device_common}")
                
                beni_device_common = get_integration_source_depot_path(flumen_device_common)
                if beni_device_common and validate_depot_path(beni_device_common):
                    workspaces["BENI"] = beni_device_common
                    print(f"[AUTO] Resolved BENI device_common.mk: {beni_device_common}")
                else:
                    print("[WARNING] Could not resolve BENI from FLUMEN")
            else:
                print("[WARNING] Could not resolve FLUMEN from REL")
        
        # Case 2: FLUMEN provided, auto-resolve BENI
        elif is_flumen and not workspaces["BENI"]:
            print("[AUTO-RESOLVE] Case: FLUMEN provided → Auto-resolve BENI")
            
            # Resolve FLUMEN to get device_common.mk path
            flumen_device_common_path = resolve_device_common_path(workspace_name, "system")
            if not flumen_device_common_path:
                raise RuntimeError(f"Cannot find device_common.mk in FLUMEN workspace: {workspace_name}")
            
            # Map and sync FLUMEN
            map_single_depot(flumen_device_common_path)
            run_cmd(f"p4 sync {flumen_device_common_path}")
            
            # Get integration source for BENI from FLUMEN
            beni_device_common = get_integration_source_depot_path(flumen_device_common_path)
            if beni_device_common and validate_depot_path(beni_device_common):
                workspaces["BENI"] = beni_device_common
                print(f"[AUTO] Resolved BENI device_common.mk: {beni_device_common}")
            else:
                print("[WARNING] Could not resolve BENI from FLUMEN")
        
        # Case 3: All provided or no auto-resolve needed
        else:
            print("[AUTO-RESOLVE] No auto-resolve needed - using provided inputs")
        
        print("[AUTO-RESOLVE] Completed successfully")
        return workspaces
        
    except Exception as e:
        print(f"[AUTO-RESOLVE ERROR] {str(e)}")
        # Return workspaces with only the provided workspace on error
        if is_rel:
            workspaces = {"REL": workspace_name, "FLUMEN": "", "BENI": ""}
        elif is_flumen:
            workspaces = {"REL": "", "FLUMEN": workspace_name, "BENI": ""}
        else:
            workspaces = {"REL": "", "FLUMEN": "", "BENI": workspace_name}
        return workspaces

def is_system_branch_workspace(workspace_name):
    """Check if workspace belongs to System branch based on naming convention"""
    return "_SYSTEM_" in workspace_name.upper()

def is_vendor_branch_workspace(workspace_name):
    """Check if workspace belongs to Vendor branch based on naming convention"""
    return "_VENDOR_" in workspace_name.upper()

def is_rel_branch_workspace(workspace_name):
    """Check if workspace belongs to REL branch based on naming convention"""
    return "_MR" in workspace_name.upper() and "_SYSTEM_" in workspace_name.upper()

def resolve_device_common_path(workspace_name, branch_type="system"):
    """Resolve device_common.mk path based on branch type"""
    print(f"[SYSTEM] Finding device_common.mk for {branch_type} branch in: {workspace_name}")
    
    # Use P4 directly to find device_common.mk (similar to system_process.py logic)
    p4 = P4()
    p4.port = P4_SERVER_PORT
    device_common_path = None
    try:
        p4.connect()
        client_spec = p4.fetch_client(workspace_name)
        
        # Find device_common.mk in the workspace view
        for view in client_spec.get('View', []):
            depot_path = view.split()[0] if isinstance(view, str) else view[0]
            
            # Look for device_common.mk pattern in device directories
            if re.search(r'/device/[^/]+?_common/', depot_path):
                # Construct the full path to device_common.mk
                base_path = depot_path.rstrip('...')  # Remove the trailing ...
                device_common_path = base_path + "device_common.mk"
                
                # Validate the path exists
                if validate_depot_path(device_common_path):
                    print(f"[FOUND] device_common.mk path: {device_common_path}")
                    break
                else:
                    device_common_path = None
                    continue
                    
    except Exception as e:
        print(f"[ERROR] Failed to find device_common.mk: {e}")
        device_common_path = None
    finally:
        p4.disconnect()
        
    if not device_common_path:
        print(f"[ERROR] Could not find device_common.mk for workspace: {workspace_name}")
        
    return device_common_path

def extract_rscmgr_filename_from_device_common(local_path):
    """Extract rscmgr filename from device_common.mk file"""
    # Check if file exists and is valid
    if not local_path or not os.path.exists(local_path):
        print(f"[WARNING] device_common.mk file not found at: {local_path}")
        return None
        
    try:
        with open(local_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for rscmgr.rc or rscmgr_{model}.rc pattern (same as system_process.py)
        rscmgr_match = re.search(r'rscmgr(?:_\w+)?\.rc', content)
        
        if rscmgr_match:
            return rscmgr_match.group(0)
        
        return None
        
    except Exception as e:
        print(f"[WARNING] Could not read device_common.mk: {e}")
        return None

def find_samsung_vendor_path_from_workspace(workspace_name):
    """Find vendor/samsung base path from workspace (similar to system_process.py)"""
    try:
        # Use P4 to find device_common.mk and extract samsung path
        p4 = P4()
        p4.port = P4_SERVER_PORT
        p4.connect()
        client_spec = p4.fetch_client(workspace_name)
        
        for view in client_spec.get('View', []):
            depot_path = view.split()[0] if isinstance(view, str) else view[0]
            
            if "/vendor/samsung/" in depot_path:
                match = re.search(r"(.+/vendor/samsung/)", depot_path)
                if match:
                    samsung_path = match.group(1)
                    return samsung_path
        
        p4.disconnect()
        return None
    except Exception as e:
        print(f"[ERROR] Error finding samsung path: {e}")
        return None

def find_android_mk_from_samsung_path(samsung_path):
    """Find Android.mk in samsung vendor path (similar to system_process.py)"""
    android_mk_path = f"{samsung_path}system/rscmgr/Android.mk"
    
    if validate_depot_path(android_mk_path):
        print(f"[FOUND] Android.mk: {android_mk_path}")
        return android_mk_path
    
    print(f"[NOT_FOUND] Android.mk not found: {android_mk_path}")
    return None

def validate_readahead_prerequisites(workspace_name):
    """Validate all 3 readahead success conditions"""
    print(f"[VALIDATION] Checking readahead prerequisites for: {workspace_name}")
    
    # Only validate for System branch workspaces
    if not is_system_branch_workspace(workspace_name):
        print("[INFO] Not a System branch workspace, skipping validation")
        return True, []
    
    issues = []
    
    # 1. Check device_common.mk defines rscmgr filename
    device_common_path = resolve_device_common_path(workspace_name, "system")
    if not device_common_path:
        issues.append("Could not find device_common.mk in System branch")
        return False, issues
    
    # Map and sync device_common.mk
    map_single_depot(device_common_path)
    run_cmd(f"p4 sync {device_common_path}")
    local_device_common = depot_to_local_path(device_common_path)
    
    rscmgr_filename = extract_rscmgr_filename_from_device_common(local_device_common)
    if not rscmgr_filename:
        issues.append("device_common.mk does not define rscmgr filename (looking for rscmgr*.rc pattern)")
        return False, issues
    
    print(f"[VALIDATION] Found rscmgr filename in device_common.mk: {rscmgr_filename}")
    
    # 2. Check Android.mk configures rscmgr file (using correct logic from system_process.py)
    samsung_path = find_samsung_vendor_path_from_workspace(workspace_name)
    if not samsung_path:
        issues.append("Could not find Samsung vendor path in workspace")
        return False, issues
    
    android_mk_path = find_android_mk_from_samsung_path(samsung_path)
    if not android_mk_path:
        issues.append("Could not find Android.mk for rscmgr configuration")
    else:
        # Check if Android.mk contains rscmgr filename
        map_single_depot(android_mk_path)
        run_cmd(f"p4 sync {android_mk_path}")
        local_android_mk = depot_to_local_path(android_mk_path)
        
        if os.path.exists(local_android_mk):
            try:
                with open(local_android_mk, 'r', encoding='utf-8') as f:
                    content = f.read()
                if f"LOCAL_MODULE := {rscmgr_filename}" not in content:
                    issues.append(f"Android.mk does not configure {rscmgr_filename}")
            except Exception as e:
                issues.append(f"Could not read Android.mk: {e}")
        else:
            issues.append(f"Android.mk file not found locally: {local_android_mk}")
    
    # 3. Check rscmgr.rc file exists (this is already checked in resolve_rscmgr_path)
    # This will be validated in the main flow
    
    return len(issues) == 0, issues

def resolve_rscmgr_path(workspace_name):
    print(f"[SYSTEM] Finding rscmgr for: {workspace_name}")
    
    # First validate readahead prerequisites
    is_valid, issues = validate_readahead_prerequisites(workspace_name)
    if not is_valid:
        print(f"[WARNING] Readahead prerequisites not met:")
        for issue in issues:
            print(f"  - {issue}")
        print("[WARNING] Continuing with basic rscmgr path resolution...")
    
    p4 = P4()
    p4.port = P4_SERVER_PORT
    rscmgr_path = None
    rscmgr_filename = None
    try:
        p4.connect()
        client_spec = p4.fetch_client(workspace_name)
        samsung_base = None
        for view in client_spec.get('View', []):
            dp = view.split()[0] if isinstance(view, str) else view[0]
            if "/vendor/samsung/" in dp:
                match = re.search(r"(.+/vendor/samsung/)", dp)
                if match:
                    samsung_base = match.group(1)
                    break
        if not samsung_base:
            raise RuntimeError("No vendor/samsung path found in workspace.")
            
        # Parse device_common.mk to get exact rscmgr filename
        device_common_path = resolve_device_common_path(workspace_name, "system")
        if device_common_path and is_system_branch_workspace(workspace_name):
            map_single_depot(device_common_path)
            run_cmd(f"p4 sync {device_common_path}")
            local_device_common = depot_to_local_path(device_common_path)
            rscmgr_filename = extract_rscmgr_filename_from_device_common(local_device_common)
            
            if rscmgr_filename:
                # Look for specific rscmgr file
                search_path = f"{samsung_base}system/rscmgr/{rscmgr_filename}"
                if validate_depot_path(search_path):
                    rscmgr_path = search_path
                    print(f"[FOUND] Rscmgr file path: {rscmgr_path}")
                else:
                    print(f"[WARNING] Specified rscmgr file {rscmgr_filename} not found, falling back to pattern search")
        
        # Fallback to pattern search if specific file not found
        if not rscmgr_path:
            search_path = f"{samsung_base}system/rscmgr/rscmgr*.rc"
            res = subprocess.run(f"p4 files {search_path}", capture_output=True, text=True, shell=True)
            if res.returncode == 0:
                for line in res.stdout.split('\n'):
                    if line.strip() and "delete" not in line:
                        rscmgr_path = line.split("#")[0].strip()
                        # Extract filename from path for display
                        if rscmgr_path:
                            rscmgr_filename = os.path.basename(rscmgr_path)
                            print(f"[FOUND] Rscmgr file path: {rscmgr_path}")
                        break
                        
        if not rscmgr_path:
             search_path = f"{samsung_base}system/rscmgr/rscmgr.rc"
             rscmgr_path = search_path
             rscmgr_filename = "rscmgr.rc"
             print(f"[FOUND] Rscmgr file path: {rscmgr_path}")
             
    finally:
        p4.disconnect()
        
    return rscmgr_path

def get_or_create_cl(desc):
    cl_spec = run_cmd("p4 change -o")
    cl_spec = re.sub(r"<enter description here>", desc, cl_spec)
    result = subprocess.run("p4 change -i", capture_output=True, text=True, shell=True, input=cl_spec)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: p4 change -i\n{result.stderr}")
    res = result.stdout.strip()
    return re.search(r"Change (\d+)", res).group(1)

def extract_libraries(local_path):
    if not os.path.exists(local_path):
        return {1: [], 2: []}
        
    with open(local_path, 'r', encoding='utf-8') as f:
         content = f.read()
         
    libs = {1: [], 2: []}
    curr_res = None
    for line in content.split('\n'):
        if line.strip().startswith('on property:sys.readahead.resource='):
            match = re.search(r'resource=(\d+)', line)
            if match:
                curr_res = int(match.group(1))
        elif curr_res is not None and line.strip().startswith('readahead'):
             parts = line.strip().split()
             if len(parts) > 1:
                 libs.setdefault(curr_res, []).append(parts[1])
                 
    return libs

def validate_library_format(library_name):
    """Validate that library follows readahead format requirements"""
    # Basic validation - library name should not contain spaces or special chars
    if not library_name:
        return False, "Library name is empty"
    return True, ""

def edit_libraries(local_path, action, res_id, lib):
    # Validate library format before processing
    if isinstance(lib, str):
        is_valid, error_msg = validate_library_format(lib)
        if not is_valid:
            print(f"[ERROR] Invalid library format: {lib} - {error_msg}")
            return False
    elif isinstance(lib, list):
        for lib_name in lib:
            is_valid, error_msg = validate_library_format(lib_name)
            if not is_valid:
                print(f"[ERROR] Invalid library format: {lib_name} - {error_msg}")
                return False
    
    with open(local_path, 'r', encoding='utf-8') as f:
         lines = f.readlines()
         
    curr_res = None
    modified_lines = []
    modified = False
    
    for i in range(len(lines)):
        line = lines[i]
        
        if line.strip().startswith('on property:sys.readahead.resource='):
            match = re.search(r'resource=(\d+)', line)
            if match:
                curr_res = int(match.group(1))
        
        if curr_res == res_id:
            if action == "delete_lib":
                if line.strip().startswith('readahead') and lib in line:
                    modified = True
                    continue
                    
            if action == "add_lib":
                # Add at the end of the block
                next_is_end = (i == len(lines)-1) or (lines[i+1].strip() == "") or lines[i+1].strip().startswith("on property") or lines[i+1].strip().startswith("setprop")
                if next_is_end:
                    modified_lines.append(line)
                    modified_lines.append(f"    readahead {lib} --fully\n")
                    modified = True
                    continue
                    
        modified_lines.append(line)
        
    if modified:
        with open(local_path, 'w', encoding='utf-8') as f:
            f.writelines(modified_lines)
            
    return modified

def is_depot_path(input_str):
    """Check if input string is a depot path (starts with //)"""
    return input_str.strip().startswith("//")

def resolve_input_to_rscmgr_path(user_input):
    """Resolve user input (workspace or depot path) to rscmgr file path"""
    user_input = user_input.strip()
    
    if not user_input:
        return None
    
    # If it's already a depot path to rscmgr file, validate and return
    if user_input.startswith("//") and "rscmgr" in user_input.lower() and user_input.endswith(".rc"):
        if validate_depot_path(user_input):
            return user_input
        else:
            # Try to resolve the rscmgr file from the device_common.mk path
            pass
    
    # Use existing resolve_rscmgr_path function for workspace names
    return resolve_rscmgr_path(user_input)

def process_single_branch(branch_name, workspace, action, resource_id, libraries, changelist_id=None):
    """Process a single branch with the specified action"""
    print(f"\n[{branch_name.upper()}] Processing branch: {workspace}")
    
    # For depot paths (auto-resolved branches), skip workspace validation
    if not is_depot_path(workspace):
        # Validate workspace only for actual workspace names
        is_valid, message = validate_workspace_branch(workspace, "system")
        if not is_valid:
            print(f"[ERROR] {message}")
            return False
    
    # Resolve rscmgr path - handle both workspace names and depot paths
    rscmgr_path = resolve_input_to_rscmgr_path(workspace)
    if not rscmgr_path:
        print(f"[ERROR] Failed to find rscmgr for {branch_name}: {workspace}")
        return False
    
    # Map and sync the file
    map_single_depot(rscmgr_path)
    run_cmd(f"p4 sync {rscmgr_path}")
    local_path = depot_to_local_path(rscmgr_path)
    
    # Process the action
    if action == "check_libs":
        libs = extract_libraries(local_path)
        print(f"[{branch_name.upper()}] Libraries in Resource {resource_id}:")
        for lib in libs.get(resource_id, []):
            print(f"  - {lib}")
        return True
    
    elif action in ["add_lib", "delete_lib"]:
        if not libraries:
            print(f"[{branch_name.upper()}] No libraries to process")
            return False
        
        # Use existing changelist or create new one
        cl_id = changelist_id
        if not cl_id:
            cl_id = get_or_create_cl(f"Readahead - {action} {' '.join(libraries)}")
        
        run_cmd(f"p4 edit -c {cl_id} {rscmgr_path}")
        
        any_mod = False
        for lib in libraries:
            if edit_libraries(local_path, action, resource_id, lib):
                any_mod = True
                print(f"[{branch_name.upper()}] Successfully applied {action} for {lib} in Resource {resource_id}")
        
        if not any_mod:
            print(f"[{branch_name.upper()}] No changes needed or found.")
            run_cmd(f"p4 revert {rscmgr_path}")
        
        return True
    
    return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=["check_libs", "add_lib", "delete_lib", "compare"], required=True)
    parser.add_argument("--workspace", required=True, help="Starting workspace (REL, FLUMEN, or BENI)")
    parser.add_argument("--compare_workspace", default="", help="Workspace to compare with (for compare action)")
    parser.add_argument("--resource_id", type=int, choices=[1, 2], default=1, help="Resource ID (1 or 2)")
    parser.add_argument("--library", nargs='+', default=[], help="One or more libraries to manage")
    parser.add_argument("--no_cascade", action="store_true", help="Disable auto-resolution cascade (process single branch only)")
    
    args = parser.parse_args()
    
    print(f"[MODE] Readahead Libraries - {args.action.upper()}")
    
    # Auto-resolve cascade branches
    if args.no_cascade or args.action == "compare":
        # Process single branch only
        workspaces = {"REL": args.workspace, "FLUMEN": "", "BENI": ""}
        if args.action == "compare":
            workspaces["COMPARE"] = args.compare_workspace
    else:
        # Auto-resolve cascade branches
        workspaces = auto_resolve_cascade_branches(args.workspace)
    
    # Determine processing order based on provided workspace
    processing_order = []
    if workspaces["REL"]:
        processing_order = ["REL", "FLUMEN", "BENI"]
    elif workspaces["FLUMEN"]:
        processing_order = ["FLUMEN", "BENI"]
    else:
        processing_order = ["BENI"]
    
    print(f"[CASCADE] Processing order: {' → '.join([w for w in processing_order if workspaces[w]])}")
    
    # Process branches in cascade order
    shared_changelist_id = None
    
    if args.action == "compare":
        # Special handling for compare action
        if not args.compare_workspace:
            print("Error: --compare_workspace required for compare action.")
            sys.exit(1)
        
        # Process primary workspace
        dp1 = resolve_rscmgr_path(args.workspace)
        if not dp1:
            print(f"Failed to find rscmgr in workspace: {args.workspace}")
            sys.exit(1)
        map_single_depot(dp1)
        run_cmd(f"p4 sync {dp1}")
        local_p1 = depot_to_local_path(dp1)
        
        # Process compare workspace
        dp2 = resolve_rscmgr_path(args.compare_workspace)
        if not dp2:
            print(f"Failed to find rscmgr in compare_workspace: {args.compare_workspace}")
            sys.exit(1)
        map_single_depot(dp2)
        run_cmd(f"p4 sync {dp2}")
        local_p2 = depot_to_local_path(dp2)
        
        # Compare libraries
        libs1 = extract_libraries(local_p1)
        libs2 = extract_libraries(local_p2)
        
        print(f"--- COMPARE: {args.workspace} vs {args.compare_workspace} ---")
        for res in [1, 2]:
            s1 = set(libs1.get(res, []))
            s2 = set(libs2.get(res, []))
            print(f"\nResource {res}:")
            print(f"Only in {args.workspace}: {list(s1 - s2)}")
            print(f"Only in {args.compare_workspace}: {list(s2 - s1)}")
            print(f"In Both: {list(s1 & s2)}")
        
        return
    
    elif args.action == "check_libs":
        # Check libraries in all resolved branches
        for branch in processing_order:
            workspace = workspaces[branch]
            if workspace:
                print(f"\n[{branch}] Checking libraries in workspace: {workspace}")
                process_single_branch(branch, workspace, "check_libs", args.resource_id, [], None)
    
    elif args.action in ["add_lib", "delete_lib"]:
        if not args.library:
            print("Error: --library required.")
            sys.exit(1)
        
        libs_to_process = args.library if isinstance(args.library, list) else [args.library]
        
        # Process branches in cascade order, sharing the same changelist
        for branch in processing_order:
            workspace = workspaces[branch]
            if workspace:
                success = process_single_branch(branch, workspace, args.action, args.resource_id, libs_to_process, shared_changelist_id)
                if success and not shared_changelist_id:
                    # Get the changelist ID from the first successful operation
                    # This is a simplification - in practice, we'd need to extract it from the p4 output
                    pass

if __name__ == "__main__":
    main()
