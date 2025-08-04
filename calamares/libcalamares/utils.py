#!/usr/bin/env python3
"""
Mock libcalamares.utils module
"""

def debug(message):
    """Debug logging"""
    print(f"[DEBUG] {message}")
    
def warning(message):
    """Warning logging"""
    print(f"[WARNING] {message}")
    
def error(message):
    """Error logging"""
    print(f"[ERROR] {message}")
    
def mount(device, mountpoint, fstype=None, options=None):
    """Mock mount function"""
    return True
    
def umount(mountpoint):
    """Mock umount function"""
    return True
    
def target_env_call(cmd):
    """Mock target environment call"""
    return 0

def gettext_path():
    """Get translation path"""
    return "/usr/share/calamares/lang"

def gettext_languages():
    """Get available languages"""
    return ["en", "es", "fr", "de", "it", "pt", "ru", "zh"]

def pretty_name():
    """Get pretty name for module"""
    return "Calamares Module"

def check_target_env_call(cmd):
    """Check command in target environment"""
    return 0

def target_env_process_output(cmd):
    """Get output from target environment command"""
    return "", ""

# Export common functions
__all__ = [
    'debug', 'warning', 'error',
    'mount', 'umount', 
    'target_env_call', 'check_target_env_call', 'target_env_process_output',
    'gettext_path', 'gettext_languages', 'pretty_name'
]