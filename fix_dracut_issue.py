#!/usr/bin/env python3
"""
Fix for dracut kernel version issue
"""
import subprocess
import sys
from pathlib import Path

def check_dracut_issue():
    """Check and fix dracut issues in the chroot"""
    chroot_path = Path("/tmp/zforge_workspace/chroot")
    
    if not chroot_path.exists():
        print("Chroot path not found. Build may not have started yet.")
        return
    
    print("Checking dracut installation and kernel modules...")
    
    # Check installed kernels
    try:
        result = subprocess.run(
            ["chroot", str(chroot_path), "ls", "-la", "/lib/modules/"],
            capture_output=True, text=True
        )
        print("Installed kernel modules:")
        print(result.stdout)
    except Exception as e:
        print(f"Error checking modules: {e}")
    
    # Check dracut installation
    try:
        result = subprocess.run(
            ["chroot", str(chroot_path), "which", "dracut"],
            capture_output=True, text=True
        )
        print(f"Dracut location: {result.stdout.strip()}")
    except Exception as e:
        print(f"Error checking dracut: {e}")
    
    # Check for dracut modules
    try:
        result = subprocess.run(
            ["chroot", str(chroot_path), "ls", "-la", "/usr/lib/dracut/modules.d/"],
            capture_output=True, text=True
        )
        print("Dracut modules available:")
        zfs_modules = [line for line in result.stdout.split('\n') if 'zfs' in line.lower()]
        if zfs_modules:
            print("ZFS modules found:")
            for mod in zfs_modules:
                print(f"  {mod}")
        else:
            print("WARNING: No ZFS dracut modules found!")
    except Exception as e:
        print(f"Error checking dracut modules: {e}")
    
    # Test dracut with the problematic kernel version
    kernel_version = "6.12.35+deb13-amd64"
    print(f"\nTesting dracut with kernel version: {kernel_version}")
    
    # Try to run dracut in test mode
    try:
        result = subprocess.run(
            ["chroot", str(chroot_path), "dracut", "--list-modules"],
            capture_output=True, text=True
        )
        if "zfs" in result.stdout:
            print("ZFS module is available in dracut")
        else:
            print("WARNING: ZFS module not listed in dracut modules")
    except Exception as e:
        print(f"Error listing dracut modules: {e}")
    
    # Check kernel config
    kernel_config = chroot_path / "boot" / f"config-{kernel_version}"
    if kernel_config.exists():
        print(f"Kernel config exists: {kernel_config}")
    else:
        print(f"WARNING: Kernel config not found for {kernel_version}")
    
    # Suggest fix
    print("\nSuggested fixes:")
    print("1. The '+' character in kernel version might need escaping")
    print("2. ZFS dracut module might be missing")
    print("3. Try running dracut without --kver option")
    print("4. Check if kernel modules are properly installed")

if __name__ == "__main__":
    check_dracut_issue()