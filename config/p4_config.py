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
        
        # Find Root path from the spec
        root_match = re.search(r"^Root:\s+(.+)$", client_spec, re.MULTILINE)
        if not root_match:
            raise RuntimeError("Could not find Root path in P4 client spec")
        
        workspace_root = root_match.group(1).strip()
        
        # Validate that the workspace root path exists
        if not os.path.exists(workspace_root):
            raise RuntimeError(f"Workspace root path does not exist: {workspace_root}")
        
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
    
    # Remove //depot prefix and convert forward slashes to backslashes
    if depot_path.startswith("//depot/"):
        relative_path = depot_path[8:]  # Remove "//depot/"
    elif depot_path.startswith("//"):
        relative_path = depot_path[2:]  # Remove "//" prefix
    else:
        relative_path = depot_path
    
    # Convert forward slashes to backslashes for Windows paths
    local_path = os.path.join(WORKSPACE_ROOT, relative_path.replace("/", os.sep))
    return local_path

def is_config_initialized():
    """Check if P4 configuration is initialized"""
    return CLIENT_NAME is not None and WORKSPACE_ROOT is not None

def refresh_p4_config():
    """Refresh P4 configuration (useful if client settings change)"""
    global CLIENT_NAME, WORKSPACE_ROOT
    try:
        CLIENT_NAME, WORKSPACE_ROOT = get_p4_client_info()
        return True, f"P4 Config refreshed: Client={CLIENT_NAME}, Workspace={WORKSPACE_ROOT}"
    except Exception as e:
        return False, str(e)

def check_p4_login_status():
    """Check if user is logged into P4 using 'p4 login -s' command"""
    try:
        result = subprocess.run("p4 login -s", capture_output=True, text=True, shell=True)
        
        if result.returncode != 0:
            return False
            
        output = result.stdout.strip()
        
        # If output starts with "User" -> logged in
        # If output starts with "Perforce" -> not logged in
        if output.startswith("User"):
            return True
        elif output.startswith("Perforce"):
            return False
        else:
            # Unexpected output, assume not logged in
            return False
            
    except Exception as e:
        # Error running command, assume not logged in
        return False

def p4_login(password):
    """Login to P4 with provided password"""
    try:
        # Run p4 login command with password
        result = subprocess.run(
            "p4 login", 
            input=password, 
            capture_output=True, 
            text=True, 
            shell=True
        )
        
        if result.returncode != 0:
            return False
            
        output = result.stdout.strip()
        
        # Check if login was successful
        if output.endswith("logged in."):
            return True
        elif "Authentication failed." in output:
            return False
        else:
            # Unexpected output, assume failed
            return False
            
    except Exception as e:
        # Error running command, assume failed
        return False

def get_p4_info_summary():
    """Get a summary of current P4 configuration for display purposes"""
    if not is_config_initialized():
        return "P4 Configuration not initialized"
    
    return f"Client: {CLIENT_NAME}\nWorkspace Root: {WORKSPACE_ROOT}"
