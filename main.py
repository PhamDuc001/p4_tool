"""
Main entry point for the P4 Tool application.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.p4_config import p4_env_is_configured
from config.settings import load_settings, save_settings
from config.version import __version__
from core.p4_client import get_default_p4_client
from gui.main_gui import create_gui


def check_p4_config():
    return not p4_env_is_configured()


def config_p4():
    username = os.getenv("USERNAME") or os.getenv("USER")
    if not username:
        raise RuntimeError("Unable to determine current username for P4 configuration")

    client = get_default_p4_client()
    settings = load_settings()

    client.set_variable("P4USER", username)
    settings.p4user = username

    clients_output = client.list_clients_for_user(username, port=settings.p4port)
    client_lines = [line for line in clients_output.splitlines() if line.strip()]
    if not client_lines:
        raise RuntimeError(f"No P4 clients found for user {username}")

    workspace_name = client_lines[0].split()[1]
    client.set_variable("P4CLIENT", workspace_name)
    client.set_variable("P4PORT", settings.p4port)

    settings.p4client = workspace_name
    save_settings(settings)


def main():
    try:
        print(f"Starting P4 Tool {__version__}...")
        if check_p4_config():
            config_p4()
        create_gui()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
