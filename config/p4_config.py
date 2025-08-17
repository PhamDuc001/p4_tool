"""
P4 Configuration management
Handles dynamic client name and workspace root detection
"""
import os
import subprocess
import re

# Global variables
CLIENT_NAME = None
WORKSPACE_ROOT = None

def get_p4_client_info():
    """Get P4 client name and workspace root dynamically"""
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
        
        # Extract username from client name (everything before first underscore)
        username_match = re.match(r"^([^_]+)", client_name)
        if not username_match:
            raise RuntimeError(f"Could not extract username from client name: {client_name}")
        
        username = username_match.group(1)
        workspace_root = fr"C:\Users\{username}\Perforce\{client_name}"
        
        return client_name, workspace_root
        
    except Exception as e:
        raise RuntimeError(f"Error getting P4 client info: {str(e)}")

def initialize_p4_config():
    """Initialize P4 configuration on startup"""
    global CLIENT_NAME, WORKSPACE_ROOT
    try:
        CLIENT_NAME, WORKSPACE_ROOT = get_p4_client_info()
        return True, f"P4 Config loaded: Client={CLIENT_NAME}, Workspace={WORKSPACE_ROOT}"
    except Exception as e:
        return False, str(e)

def get_client_name():
    """Get current client name"""
    return CLIENT_NAME

def get_workspace_root():
    """Get current workspace root"""
    return WORKSPACE_ROOT

def depot_to_local_path(depot_path):
    """Convert depot path to local path"""
    if not WORKSPACE_ROOT:
        raise RuntimeError("Workspace root not initialized. Please check P4 configuration.")
    return os.path.join(WORKSPACE_ROOT, depot_path[2:].replace("/", "\\"))

def is_config_initialized():
    """Check if P4 configuration is initialized"""
    return CLIENT_NAME is not None and WORKSPACE_ROOT is not None