"""
Main entry point for the Tuning Tool application
"""
import sys
import os
from P4 import P4, P4Exception
import subprocess
# Add the current directory to Python path to enable relative imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main_gui import create_gui

def check_p4_config():
    try:
        result = subprocess.run("p4 set", capture_output=True, text=True, shell=True)
        output_lines = result.stdout.strip().split('\n')
        # print(output_lines)
        if len(output_lines) == 1 and output_lines[0] == "P4EDITOR=C:\\Windows\\system32\\Notepad.exe (set)":
            # print("P4 is not configured. Please configure it manually.")
            return True
        # print("P4 is configured.")
        return False
    except Exception:
        return False
    
def config_p4():
    try:
        # Get username
        username = os.getenv('USERNAME') or os.getenv('USER')

        # Config P4USER
        subprocess.run(f"p4 set P4USER={username}", shell=True, check=True)

        # Get workspace name
        clients_cmd = f"p4 -p 107.113.53.156:1716 -u {username} clients -u {username}"
        result = subprocess.run(clients_cmd, capture_output=True, text=True, shell=True)
        client_lines = result.stdout.splitlines()
        first_client = client_lines[0].split()
        workspace_name = first_client[1]

        # Config P4CLIENT
        subprocess.run(f"p4 set P4CLIENT={workspace_name}", shell=True, check=True)

        # Config P4PORT
        subprocess.run("p4 set P4PORT=107.113.53.156:1716", shell=True, check=True)
    except Exception as e:
        print(e)


def main():
    """Main function to start the application"""
    try:
        print("Starting Tuning Tool...")

        if check_p4_config():
            config_p4()
            
        # Start GUI
        create_gui()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

   