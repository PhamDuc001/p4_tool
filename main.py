"""
Main entry point for the Tuning Tool application
"""
import sys
import os

# Add the current directory to Python path to enable relative imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main_gui import create_gui

def main():
    """Main function to start the application"""
    try:
        print("Starting Tuning Tool...")
        create_gui()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()