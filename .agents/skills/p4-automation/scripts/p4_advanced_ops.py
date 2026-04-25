import sys
import subprocess
import re
import argparse
from P4 import P4, P4Exception

P4_SERVER_PORT = "107.113.53.156:1716"

def run_cmd(cmd, input_text=None):
    """Execute command and return output"""
    result = subprocess.run(
        cmd, input=input_text, capture_output=True, text=True, shell=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\n{result.stderr}")
    return result.stdout.strip()

def get_client_name():
    try:
        output = run_cmd("p4 info")
        match = re.search(r"^Client name:\s*(.+)$", output, re.MULTILINE)
        if match:
            return match.group(1).strip()
        print("Warning: Could not find client name in p4 info.")
        return None
    except Exception as e:
        print(f"Error getting p4 info: {e}")
        return None

def map_single_depot(depot_path):
    client_name = get_client_name()
    if not client_name:
        raise RuntimeError("Client name not initialized.")
    mapping_line = f"\t{depot_path}\t//{client_name}/{depot_path[2:]}"
    client_spec = run_cmd("p4 client -o")
    lines = client_spec.splitlines()
    new_lines = []
    for line in lines:
        if depot_path in line:
            continue
        new_lines.append(line)
    new_lines.append(mapping_line)
    run_cmd("p4 client -i", input_text="\n".join(new_lines))
    print(f"[OK] Mapped {depot_path} to client spec.")

def sync_file_silent(depot_path):
    run_cmd(f"p4 sync {depot_path}")
    print(f"[OK] Synced {depot_path}")

def validate_depot_path(depot_path):
    try:
        result = subprocess.run(f"p4 files {depot_path}", capture_output=True, text=True, shell=True)
        if result.returncode != 0 or "no such file" in result.stderr.lower():
            return False
        return True
    except:
        return False

def is_workspace_like(user_input: str) -> bool:
    if not user_input:
        return False
    return user_input.strip().upper().startswith("TEMPLATE")

def find_device_common_mk_path(workspace_name):
    print(f"[SYSTEM] Searching device_common.mk in workspace: {workspace_name}")
    p4 = P4()
    p4.port = P4_SERVER_PORT
    try:
        p4.connect()
        client_spec = p4.fetch_client(workspace_name)
        device_common_paths = []
        for view in client_spec.get('View', []):
            depot_path = view.split()[0] if isinstance(view, str) else view[0]
            if re.search(r'/device/[^/]+?_common/', depot_path):
                clean_path = depot_path.rstrip('...')
                device_common_paths.append(clean_path + "device_common.mk")
        
        if device_common_paths:
            print(f"[OK] Found device_common.mk path: {device_common_paths[0]}")
            return device_common_paths[0]
        else:
            print("[WARNING] No device_common.mk path found in workspace")
            return None
    except P4Exception as e:
        print(f"[ERROR] P4 Error: {str(e)}")
        raise RuntimeError(f"P4 Error: {str(e)}")
    finally:
        try:
            p4.disconnect()
        except:
            pass

def get_integration_source_depot_path(depot_path: str) -> str:
    try:
        cmd = f"p4 filelog -i {depot_path}#1"
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', shell=True)
        if result.returncode != 0:
            print(f"[WARNING] P4 filelog command failed for {depot_path}#1")
            return None
        output = result.stdout.strip()
        if not output:
            return None

        lines = output.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("... ... branch from "):
                integration_line = line.split("from ")[1]
                source_path = integration_line.split("#")[0].split(",")[0]
                print(f"[PARSE] Extracted integration source: {source_path}")
                return source_path
                
        print(f"[WARNING] No 'branch from' line found in filelog output for {depot_path}#1")
        return None
    except Exception as e:
        print(f"[ERROR] Error getting integration source: {str(e)}")
        return None

def resolve_vendor_input(user_input):
    user_input = user_input.strip()
    if not user_input:
        return ""
    if user_input.startswith("//"):
        if validate_depot_path(user_input):
            return user_input
        else:
            raise RuntimeError(f"Depot path does not exist: {user_input}")
    elif is_workspace_like(user_input):
        resolved_path = find_device_common_mk_path(user_input)
        if resolved_path:
            return resolved_path
        raise RuntimeError(f"Workspace resolution returned None")
    else:
        raise RuntimeError(f"Input must be either depot path or workspace: {user_input}")

def auto_resolve_vendor_branches(vince_input, beni_input, flumen_input, rel_input):
    vince_input = vince_input.strip() if vince_input else ""
    beni_input = beni_input.strip() if beni_input else ""
    flumen_input = flumen_input.strip() if flumen_input else ""
    rel_input = rel_input.strip() if rel_input else ""

    resolved_vince = vince_input
    resolved_beni = beni_input
    resolved_flumen = flumen_input
    resolved_rel = rel_input

    if not vince_input:
        raise RuntimeError("VINCE is mandatory and cannot be empty")

    print("[VENDOR AUTO-RESOLVE] Analyzing input combination for auto-resolve...")

    try:
        if rel_input and vince_input and not flumen_input and not beni_input:
            print("[AUTO-RESOLVE] REL + VINCE -> FLUMEN and BENI")
            rel_depot_path = resolve_vendor_input(rel_input)
            map_single_depot(rel_depot_path)
            sync_file_silent(rel_depot_path)
            
            flumen_source = get_integration_source_depot_path(rel_depot_path)
            if flumen_source and validate_depot_path(flumen_source):
                resolved_flumen = flumen_source
                print(f"[AUTO] Successfully resolved FLUMEN from REL: {flumen_source}")
                map_single_depot(flumen_source)
                sync_file_silent(flumen_source)
                beni_source = get_integration_source_depot_path(flumen_source)
                if beni_source and validate_depot_path(beni_source):
                    resolved_beni = beni_source
                    print(f"[AUTO] Successfully resolved BENI from FLUMEN: {beni_source}")

        elif flumen_input and vince_input and not beni_input:
            print("[AUTO-RESOLVE] FLUMEN + VINCE -> BENI")
            flumen_depot_path = resolve_vendor_input(flumen_input)
            map_single_depot(flumen_depot_path)
            sync_file_silent(flumen_depot_path)
            beni_source = get_integration_source_depot_path(flumen_depot_path)
            if beni_source and validate_depot_path(beni_source):
                resolved_beni = beni_source
                print(f"[AUTO] Successfully resolved BENI from FLUMEN: {beni_source}")

        elif flumen_input and rel_input and vince_input and not beni_input:
            print("[AUTO-RESOLVE] FLUMEN + REL + VINCE -> BENI from FLUMEN")
            flumen_depot_path = resolve_vendor_input(flumen_input)
            map_single_depot(flumen_depot_path)
            sync_file_silent(flumen_depot_path)
            beni_source = get_integration_source_depot_path(flumen_depot_path)
            if beni_source and validate_depot_path(beni_source):
                resolved_beni = beni_source
                print(f"[AUTO] Successfully resolved BENI from FLUMEN: {beni_source}")
        else:
            print("[AUTO-RESOLVE] No auto-resolve needed or matched")

        return resolved_beni, resolved_vince, resolved_flumen, resolved_rel

    except Exception as e:
        print(f"[AUTO-RESOLVE ERROR] {str(e)}")
        return beni_input, vince_input, flumen_input, rel_input

def command_find_device(args):
    print(f"Resolving workspace: {args.workspace_name}")
    try:
        path = find_device_common_mk_path(args.workspace_name)
        if path:
            print(f"RESOLVED_PATH: {path}")
        else:
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def command_auto_resolve(args):
    print("Running cascading auto-resolve logic...")
    try:
        resolved_beni, resolved_vince, resolved_flumen, resolved_rel = auto_resolve_vendor_branches(
            vince_input=args.vince,
            beni_input=args.beni,
            flumen_input=args.flumen,
            rel_input=args.rel
        )
        print("\n--- RESOLUTION RESULTS ---")
        print(f"VINCE:  {resolved_vince}")
        print(f"REL:    {resolved_rel if resolved_rel else 'None'}")
        print(f"FLUMEN: {resolved_flumen if resolved_flumen else 'None'}")
        print(f"BENI:   {resolved_beni if resolved_beni else 'None'}")
    except Exception as e:
        print(f"Auto-resolve failed: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Standalone P4 Advanced Reasoning AI Wrapper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_find = subparsers.add_parser("find-device", help="Resolve TEMPLATE_* workspace to device_common.mk path")
    parser_find.add_argument("--workspace_name", required=True, help="E.g. TEMPLATE_XYZ_1")

    parser_resolve = subparsers.add_parser("auto-resolve", help="Auto-resolve branching history missing entries")
    parser_resolve.add_argument("--vince", required=True, help="Mandatory Primary target string (workspace or path)")
    parser_resolve.add_argument("--rel", default="", help="Optional REL branch string")
    parser_resolve.add_argument("--flumen", default="", help="Optional FLUMEN branch string")
    parser_resolve.add_argument("--beni", default="", help="Optional BENI branch string")

    args = parser.parse_args()

    if args.command == "find-device":
        command_find_device(args)
    elif args.command == "auto-resolve":
        command_auto_resolve(args)

if __name__ == "__main__":
    main()
