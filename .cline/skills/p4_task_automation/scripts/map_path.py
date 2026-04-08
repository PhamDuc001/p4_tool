#!/usr/bin/env python3
"""
Script to map a single depot path to client spec
Mimics the logic of _map_client_depots_core function in core/p4_operations.py
"""

import sys
import subprocess
import re

def get_p4_client_info():
    """Get P4 client name and workspace root dynamically from P4 client spec"""
    try:
        # Run p4 client command to get client spec
        result = subprocess.run("p4 client -o", capture_output=True, text=True, shell=True)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to get P4 client info: {result.stderr}")
        
        client_spec = result.stdout
        
        # Find Client name from the spec
        client_match = re.search(r"^Client:\s+(.+)$", client_spec, re.MULTILINE)
        if not client_match:
            raise RuntimeError("Could not find Client name in P4 client spec")
        
        client_name = client_match.group(1).strip()
        
        return client_name
        
    except Exception as e:
        raise RuntimeError(f"Error getting P4 client info: {str(e)}")

def run_cmd(cmd, input_text=None):
    """Execute command and return output"""
    result = subprocess.run(
        cmd, input=input_text, capture_output=True, text=True, shell=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\n{result.stderr}")
    return result.stdout

def map_single_depot_path(depot_path):
    """
    Map single depot path to client spec
    Returns True if successful, False otherwise
    """
    try:
        # Get client name
        client_name = get_p4_client_info()
        if not client_name:
            raise RuntimeError("Client name not initialized. Please check P4 configuration.")
        
        # Build mapping line for the depot
        mapping_line = f"\t{depot_path}\t//{client_name}/{depot_path[2:]}"
        
        # Get current client spec
        client_spec = run_cmd("p4 client -o")
        lines = client_spec.splitlines()
        
        # Remove old mappings for the target depot
        new_lines = []
        for line in lines:
            if depot_path in line:
                continue  # Remove old mapping
            new_lines.append(line)
        
        # Add new mapping
        new_lines.append(mapping_line)
        
        # Update client spec
        new_spec = "\n".join(new_lines) + "\n"  # Add trailing newline
        run_cmd("p4 client -i", input_text=new_spec)
        
        return True
        
    except Exception as e:
        raise RuntimeError(f"Failed to map depot path: {str(e)}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python map_path.py <depot_path>", file=sys.stderr)
        sys.exit(1)
    
    depot_path = sys.argv[1].strip()
    
    # Validate depot path format
    if not depot_path.startswith("//"):
        print(f"Error: Depot path must start with '//': {depot_path}", file=sys.stderr)
        sys.exit(1)
    
    try:
        success = map_single_depot_path(depot_path)
        if success:
            print(f"Successfully mapped: {depot_path}")
            sys.exit(0)
        else:
            print(f"Failed to map: {depot_path}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()