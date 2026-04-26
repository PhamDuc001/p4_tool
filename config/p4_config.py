"""
P4 configuration helpers backed by the centralized P4 client.
"""

from __future__ import annotations

import os
import re

from config.settings import load_settings, save_settings
from core.p4_client import get_default_p4_client


CLIENT_NAME = None
WORKSPACE_ROOT = None


def get_p4_client_info():
    """Get P4 client name and workspace root from the active client spec."""
    try:
        spec = get_default_p4_client().fetch_client_spec()
        client_name = spec.get("Client")
        workspace_root = spec.get("Root")

        if not client_name:
            raise RuntimeError("Could not find Client name in P4 client spec")
        if not workspace_root:
            raise RuntimeError("Could not find Root path in P4 client spec")
        if not os.path.exists(workspace_root):
            raise RuntimeError(f"Workspace root path does not exist: {workspace_root}")

        return client_name, workspace_root
    except Exception as e:
        raise RuntimeError(f"Error getting P4 client info: {str(e)}")


def initialize_p4_config():
    """Initialize P4 configuration on startup."""
    global CLIENT_NAME, WORKSPACE_ROOT
    try:
        CLIENT_NAME, WORKSPACE_ROOT = get_p4_client_info()
        settings = load_settings()
        settings.p4client = CLIENT_NAME
        save_settings(settings)
        return True, f"P4 Config loaded: Client={CLIENT_NAME}, Workspace={WORKSPACE_ROOT}"
    except Exception as e:
        return False, str(e)


def get_client_name():
    return CLIENT_NAME


def get_workspace_root():
    return WORKSPACE_ROOT


def depot_to_local_path(depot_path):
    if not WORKSPACE_ROOT:
        raise RuntimeError("Workspace root not initialized. Please check P4 configuration.")

    if depot_path.startswith("//depot/"):
        relative_path = depot_path[8:]
    elif depot_path.startswith("//"):
        relative_path = depot_path[2:]
    else:
        relative_path = depot_path

    return os.path.join(WORKSPACE_ROOT, relative_path.replace("/", os.sep))


def is_config_initialized():
    return CLIENT_NAME is not None and WORKSPACE_ROOT is not None


def refresh_p4_config():
    global CLIENT_NAME, WORKSPACE_ROOT
    try:
        CLIENT_NAME, WORKSPACE_ROOT = get_p4_client_info()
        return True, f"P4 Config refreshed: Client={CLIENT_NAME}, Workspace={WORKSPACE_ROOT}"
    except Exception as e:
        return False, str(e)


def check_p4_login_status():
    try:
        result = get_default_p4_client().login_status()
        if result.returncode != 0:
            return False
        output = result.stdout.strip()
        return output.startswith("User")
    except Exception:
        return False


def p4_login(password):
    try:
        result = get_default_p4_client().login(password)
        if result.returncode != 0:
            return False
        output = result.stdout.strip()
        return output.endswith("logged in.")
    except Exception:
        return False


def get_p4_info_summary():
    if not is_config_initialized():
        return "P4 Configuration not initialized"
    return f"Client: {CLIENT_NAME}\nWorkspace Root: {WORKSPACE_ROOT}"


def p4_env_is_configured() -> bool:
    output = get_default_p4_client().set_output()
    names = {
        match.group(1)
        for match in re.finditer(r"^(P4[A-Z0-9_]+)=", output, flags=re.MULTILINE)
    }
    return {"P4PORT", "P4USER", "P4CLIENT"}.issubset(names)
