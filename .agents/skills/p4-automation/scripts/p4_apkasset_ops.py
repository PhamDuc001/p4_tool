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
    output = run_cmd(f"p4 where {depot_path}")
    parts = output.split()
    if len(parts) >= 3:
        return parts[2]
    return output

def map_single_depot(depot_path):
    client_name = get_client_name()
    mapping_line = f"\t{depot_path}\t//{client_name}/{depot_path[2:]}"
    lines = run_cmd("p4 client -o").splitlines()
    new_lines = [line for line in lines if depot_path not in line]
    new_lines.append(mapping_line)
    subprocess.run("p4 client -i", input="\n".join(new_lines), capture_output=True, text=True, shell=True)

def validate_depot_path(depot_path):
    result = subprocess.run(f"p4 files {depot_path}", capture_output=True, text=True, shell=True)
    return result.returncode == 0 and "no such file" not in result.stderr.lower()

def resolve_java_paths(workspace_name):
    # Cascades backward through integration for ReadaheadManager.java
    p4 = P4()
    p4.port = P4_SERVER_PORT
    first_path = None
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
        if samsung_base:
            first_path = f"{samsung_base}frameworks/sdhms/java/com/sec/android/sdhms/performance/module/readahead/ReadaheadManager.java"
    finally:
        p4.disconnect()
        
    if not first_path:
        raise RuntimeError("Failed to resolve ReadaheadManager.java path from workspace")

    cascaded = [first_path]
    current = first_path
    
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

def edit_assets(local_path, action, chipset, asset):
    with open(local_path, "r", encoding="utf-8") as f:
        content = f.read()

    chip_pattern = rf'(if\s*\(\s*PerformanceFeature\.CHIP_{chipset}\s*\)\s*\{{[^}}]*)(mReadahead\.updateAssetKey\(([^)]+)\))([^}}]*\}})'
    match = re.search(chip_pattern, content, re.DOTALL)
    
    if not match:
        if action == "check_assets":
            return False, []
        raise RuntimeError(f"Chipset {chipset} not found in {local_path}")
        
    prefix = match.group(1)
    old_update_call = match.group(2)
    current_assets_str = match.group(3)
    suffix = match.group(4)
    
    current_assets = re.findall(r'ASSET_\w+', current_assets_str)
    
    if action == "check_assets":
        return False, current_assets
        
    modified = False
    new_assets = list(current_assets)
    
    if action == "add_asset":
        for a in asset:
            if a not in new_assets:
                new_assets.append(a)
                modified = True
    elif action == "delete_asset":
        for a in asset:
            if a in new_assets:
                new_assets.remove(a)
                modified = True
            
    if modified:
        new_assets_str = " | ".join(new_assets) if new_assets else ""
        if new_assets_str:
            new_update_call = f"mReadahead.updateAssetKey({new_assets_str})"
        else:
             new_update_call = "// mReadahead.updateAssetKey() removed (no assets)"
        new_block = prefix + new_update_call + suffix
        old_block = prefix + old_update_call + suffix
        new_content = content.replace(old_block, new_block)
        
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(new_content)
            
    return modified, new_assets

def get_or_create_cl(desc):
    cl_spec = run_cmd("p4 change -o")
    cl_spec = re.sub(r"<enter description here>", desc, cl_spec)
    res = run_cmd("p4 change -i", input_text=cl_spec)
    return re.search(r"Change (\d+)", res).group(1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=["check_assets", "add_asset", "delete_asset"], required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--chipset", required=True, help="e.g. MT6789")
    parser.add_argument("--asset", nargs='+', default=[], help="e.g. ASSET_CAMERA ASSET_GALLERY")
    args = parser.parse_args()
    
    # Validate workspace branch compatibility for ApkAsset mode (requires System branch)
    is_valid, message = validate_workspace_branch(args.workspace, "system")
    if not is_valid:
        print(f"[ERROR] {message}")
        sys.exit(1)
    
    print(f"[MODE] LoadApkAsset - {args.action.upper()}")
    
    paths = resolve_java_paths(args.workspace)
    
    cl_id = None
    if args.action in ["add_asset", "delete_asset"]:
        cl_id = get_or_create_cl(f"ApkAsset - {args.action} for {args.chipset}")
        
    for dp in paths:
        map_single_depot(dp)
        run_cmd(f"p4 sync {dp}")
        local_p = depot_to_local_path(dp)
        
        if args.action == "check_assets":
            _, assets = edit_assets(local_p, "check_assets", args.chipset, None)
            print(f"[FETCH] Assets for {args.chipset} in {dp}: {', '.join(assets) if assets else '(none)'}")
        else:
            if not args.asset:
                print("Error: --asset required for modifications.")
                sys.exit(1)
            
            assets_to_process = args.asset if isinstance(args.asset, list) else [args.asset]
            run_cmd(f"p4 edit -c {cl_id} {dp}")
            mod, _ = edit_assets(local_p, args.action, args.chipset, assets_to_process)
            
            if mod:
                print(f"[UPDATED] Applied {args.action} {' '.join(assets_to_process)} to {args.chipset} in {dp}")
            else:
                print(f"[SKIP] No change required for {dp}")
                run_cmd(f"p4 revert {dp}")

if __name__ == "__main__":
    main()
