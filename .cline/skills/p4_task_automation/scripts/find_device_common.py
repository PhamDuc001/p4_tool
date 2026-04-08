#!/usr/bin/env python3
"""
Script to find device_common.mk path from workspace name
Mimics the logic of find_device_common_mk_path function in core/p4_operations.py
"""

import sys
import subprocess
import re
from typing import List, Optional, Tuple
from P4 import P4, P4Exception

def find_device_common_mk_path_cli(workspace_name):
    """
    Find device_common.mk path from workspace using P4Python
    Returns the complete depot path to device_common.mk file and all view paths
    """
    p4 = P4()
    P4_SERVER_PORT = "107.113.53.156:1716"
    p4.port = P4_SERVER_PORT
    try:
        p4.connect()
        
        # Get client spec information
        client_spec = p4.fetch_client(workspace_name)
        
        # Search in View mappings for device_common.mk pattern
        device_common_paths = []
        
        for view in client_spec.get('View', []):
            # Get depot path (left side of mapping)
            depot_path = view.split()[0] if isinstance(view, str) else view[0]
            
            # Look for device/*_common/ pattern
            if re.search(r'/device/[^/]+?_common/', depot_path):
                # Remove "..." and add "device_common.mk"
                clean_path = depot_path.rstrip('...')
                device_common_path = clean_path + "device_common.mk"
                device_common_paths.append(device_common_path)
        
        
        return device_common_paths[0] if device_common_paths else None
        
    except P4Exception as e:
        error_msg = f"P4 Error: {str(e)}"
        raise RuntimeError(error_msg)
    finally:
        try:
            p4.disconnect()
        except:
            pass

def main():
    if len(sys.argv) != 2:
        print("Usage: python find_device_common.py <workspace_name>", file=sys.stderr)
        sys.exit(1)
    
    workspace_name = sys.argv[1]
    device_common_path = find_device_common_mk_path_cli(workspace_name)
    
    if device_common_path:
        print(device_common_path)
    # If not found, print nothing (empty output)

if __name__ == "__main__":
    main()