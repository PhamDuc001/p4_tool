"""ADB wrapper to handle bundled ADB binary"""
import os
import sys
import subprocess
import shutil

def get_adb_path():
    """Get ADB executable path with fallback logic"""
    
    # 1. Try bundled ADB first (when running from PyInstaller executable)
    if hasattr(sys, '_MEIPASS'):
        bundled_adb = os.path.join(sys._MEIPASS, 'tools', 'adb.exe')
        if os.path.exists(bundled_adb):
            return bundled_adb
    
    # 2. Try local tools directory (when running from source)
    local_adb = os.path.join(os.getcwd(), 'tools', 'adb.exe')
    if os.path.exists(local_adb):
        return local_adb
    
    # 3. Try system PATH
    system_adb = shutil.which('adb')
    if system_adb:
        return system_adb
    
    # 4. Try common Android SDK locations
    common_paths = [
        os.path.expanduser("~/AppData/Local/Android/Sdk/platform-tools/adb.exe"),
        os.path.expanduser("~/AppData/Local/Android/_sdk/sdk/platform-tools/adb.exe"),
        "C:/Program Files/Android/Android Studio/sdk/platform-tools/adb.exe",
        "C:/Android/Sdk/platform-tools/adb.exe",
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    return None

def run_adb_command(args, timeout=15, log_callback=None):
    """Run ADB command with automatic path detection and error handling"""
    adb_path = get_adb_command()
    
    if not adb_path:
        error_msg = (
            "ADB not found. Please ensure:\n"
            "1. ADB files are in tools/ directory, OR\n"
            "2. Android Studio is installed with SDK Platform Tools, OR\n"
            "3. ADB is in system PATH"
        )
        if log_callback:
            log_callback(f"[ERROR] {error_msg}")
        raise RuntimeError(error_msg)
    
    if log_callback:
        log_callback(f"[ADB] Using: {adb_path}")
    
    # Ensure DLL files are in the same directory as adb.exe
    adb_dir = os.path.dirname(adb_path)
    env = os.environ.copy()
    if adb_dir not in env.get('PATH', ''):
        env['PATH'] = adb_dir + os.pathsep + env.get('PATH', '')
    
    cmd = [adb_path] + args
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)

def get_adb_command():
    """Get ADB command for subprocess calls"""
    adb_path = get_adb_path()
    if not adb_path:
        return 'adb'  # Fallback, will fail with clear error message
    return adb_path
