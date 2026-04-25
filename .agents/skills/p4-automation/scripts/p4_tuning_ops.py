import sys
import os
import re
import argparse
import subprocess
from P4 import P4, P4Exception

P4_SERVER_PORT = "107.113.53.156:1716"

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

def validate_workspace_branch(workspace_name, required_branch_type="vendor"):
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


def run_cmd(cmd, input_text=None):
    """Execute command and return output"""
    result = subprocess.run(
        cmd, input=input_text, capture_output=True, text=True, shell=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\n{result.stderr}")
    return result.stdout.strip()

def get_client_name():
    output = run_cmd("p4 info")
    match = re.search(r"^Client name:\s*(.+)$", output, re.MULTILINE)
    return match.group(1).strip() if match else None

def depot_to_local_path(depot_path):
    client_name = get_client_name()
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
    result = subprocess.run("p4 client -i", input="\n".join(new_lines), capture_output=True, text=True, shell=True)

def auto_resolve_cascaded_paths(workspace_name):
    print(f"[SYSTEM] Resolving device_common.mk for: {workspace_name}")
    p4 = P4()
    p4.port = P4_SERVER_PORT
    paths = []
    first_path = None
    try:
        p4.connect()
        client_spec = p4.fetch_client(workspace_name)
        for view in client_spec.get('View', []):
            dp = view.split()[0] if isinstance(view, str) else view[0]
            if re.search(r'/device/[^/]+?_common/', dp):
                first_path = dp.rstrip('...') + "device_common.mk"
                break
    finally:
        p4.disconnect()

    if not first_path:
        raise RuntimeError("Could not find device_common.mk in workspace.")

    # Find the cascaded integration paths backwards
    cascaded = [first_path]
    current = first_path
    
    # Simple heuristic to trace integration tree depth
    # Typical branches: REL -> FLUMEN -> BENI. Maximum depth 3.
    for _ in range(3):
        res = subprocess.run(f"p4 filelog -i {current}#1", capture_output=True, text=True, shell=True)
        found = False
        for line in res.stdout.split('\n'):
            line = line.strip()
            if line.startswith("... ... branch from "):
                parent_path = line.split("from ")[1].split("#")[0].split(",")[0]
                if validate_depot_path(parent_path) and parent_path not in cascaded:
                    cascaded.append(parent_path)
                    current = parent_path
                    found = True
                    break
        if not found:
            break
            
    return cascaded

def edit_property_in_file(local_path, prop_name, prop_val, action):
    # Returns (modified: bool, found: bool, current_val: str)
    with open(local_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    modified_lines = []
    modified = False
    found = False
    val = None
    
    in_lmkd = False
    in_chimera = False
    
    for i in range(len(lines)):
        line = lines[i]
        stripped = line.strip()
        
        # Track block context
        if "# LMKD property" in stripped:
            in_lmkd = True
            in_chimera = False
        elif "# Chimera property" in stripped:
            in_chimera = True
            in_lmkd = False
        elif stripped.startswith("# ") and "property" in stripped and stripped not in ["# LMKD property", "# Chimera property"]:
            in_lmkd = False
            in_chimera = False
            
        # Target properties usually reside under these blocks or broadly
        if "=" in line and not line.startswith("#"):
            parts = line.split("=")
            key = parts[0].strip()
            # Clean PRODUCT_PROPERTY_OVERRIDES \\ notation
            key_clean = key.replace("PRODUCT_PROPERTY_OVERRIDES += \\", "").strip()
            key_clean = key_clean.replace("PRODUCT_PROPERTY_OVERRIDES+=\\", "").strip()
            
            if key_clean == prop_name:
                found = True
                raw_val = parts[1].strip()
                val = raw_val.rstrip(" \\")
                
                if action == "check":
                    modified_lines.append(line)
                elif action == "set":
                    # Reconstruct line to preserve spacing and slashes
                    slash = " \\" if line.strip().endswith("\\") else ""
                    new_line = line.split("=")[0] + "=" + prop_val + slash + "\n"
                    modified_lines.append(new_line)
                    modified = True
                elif action == "delete":
                    # Delete the property line
                    modified = True
                    continue
                continue
                
        modified_lines.append(line)
        
    # If setting a non-existing property, append to LMKD block by default
    if action == "set" and not found:
        added = False
        for i in range(len(modified_lines)):
            if "# LMKD property" in modified_lines[i] or "# Chimera property" in modified_lines[i]:
                # Append right under the header
                modified_lines.insert(i+1, f"    {prop_name}={prop_val} \\\n")
                added = True
                modified = True
                break
        if not added:
            # Fallback append to end
            modified_lines.append(f"\n# Target Prop\n    {prop_name}={prop_val}\n")
            modified = True
            
    if modified:
        with open(local_path, 'w', encoding='utf-8') as f:
            f.writelines(modified_lines)
            
    return modified, found, val

def do_check(local_path, depot_path, prop_name):
    _, found, val = edit_property_in_file(local_path, prop_name, None, "check")
    if found:
        print(f"[FOUND] {prop_name} = {val} in {depot_path}")
    else:
        print(f"[MISSING] {prop_name} not found in {depot_path}")

def get_or_create_cl(desc):
    o = run_cmd("p4 opened")
    # Quick parser
    if desc in o: # Naive, better to create one always but we will just create silently
        pass
    cl_spec = run_cmd("p4 change -o")
    cl_spec = re.sub(r"<enter description here>", desc, cl_spec)
    res = run_cmd("p4 change -i", input_text=cl_spec)
    return re.search(r"Change (\d+)", res).group(1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=["check", "set", "delete"], required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--prop_name", required=True)
    parser.add_argument("--prop_val", default="")
    args = parser.parse_args()
    
    # Validate workspace branch compatibility for Tuning mode (requires Vendor branch)
    is_valid, message = validate_workspace_branch(args.workspace, "vendor")
    if not is_valid:
        print(f"[ERROR] {message}")
        sys.exit(1)
    
    print(f"[MODE] Tuning Properties - {args.action.upper()}")
    
    if args.action == "set" and not args.prop_val:
        print("Error: --prop_val required for setting.")
        sys.exit(1)
        
    paths = auto_resolve_cascaded_paths(args.workspace)
    if not paths:
        print("Failed to resolve workspace path.")
        sys.exit(1)
        
    cl_id = None
    if args.action in ["set", "delete"]:
        cl_id = get_or_create_cl(f"Tuning - {args.action} {args.prop_name}")
        print(f"[CL] Created Changelist: {cl_id}")
        
    for dp in paths:
        map_single_depot(dp)
        run_cmd(f"p4 sync {dp}")
        local_p = depot_to_local_path(dp)
        
        if args.action == "check":
            do_check(local_p, dp, args.prop_name)
        else:
            run_cmd(f"p4 edit -c {cl_id} {dp}")
            mod, found, _ = edit_property_in_file(local_p, args.prop_name, args.prop_val, args.action)
            if mod:
                print(f"[UPDATED] Applied {args.action} on {dp}")
            else:
                if not found and args.action == "delete":
                    print(f"[SKIP] Property not found to delete in {dp}")
                    run_cmd(f"p4 revert {dp}")

if __name__ == "__main__":
    main()
