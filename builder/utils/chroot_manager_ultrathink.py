#!/usr/bin/env python3
# z-forge/builder/utils/chroot_manager_ultrathink.py

"""
Enhanced Chroot Manager using Ultrathink Solution
This provides backward compatibility with the existing ChrootManager
while using the robust Ultrathink implementation underneath.
"""

import sys
import subprocess
import logging
from pathlib import Path
from typing import List

# Import the ultrathink solution
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from ultrathink_chroot_solution import ChrootManager as UltrathinkChroot, UltrathinkChrootError


class ChrootManager:
    """
    Drop-in replacement for the original ChrootManager that uses
    the Ultrathink solution for enhanced reliability.
    
    This maintains the same API as the original but provides:
    - arch-chroot instead of regular chroot
    - Better mount handling including /run
    - dpkg diversion to prevent initramfs issues
    - Enhanced cleanup and error handling
    """
    
    def __init__(self, chroot_path: Path):
        self.chroot_path = Path(chroot_path)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Create ultrathink manager
        self._ultrathink = UltrathinkChroot(self.chroot_path, self.logger)
        
        # Legacy compatibility attributes
        self.mounts = [
            ("proc", "proc", self.chroot_path / "proc"),
            ("sysfs", "sys", self.chroot_path / "sys"),
            ("devtmpfs", "udev", self.chroot_path / "dev"),
            ("devpts", "devpts", self.chroot_path / "dev/pts"),
            ("tmpfs", "run", self.chroot_path / "run")  # Added /run
        ]
    
    def __enter__(self):
        """Mount filesystems on entry"""
        self.mount_filesystems()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Unmount filesystems on exit"""
        self.unmount_filesystems()
    
    def mount_filesystems(self):
        """Mount required pseudo filesystems for chroot operations."""
        try:
            self._ultrathink.prepare()
        except UltrathinkChrootError as e:
            self.logger.error(f"Failed to prepare chroot: {e}")
            raise
    
    def unmount_filesystems(self):
        """Unmount pseudo filesystems in reverse order."""
        try:
            self._ultrathink.cleanup()
        except Exception as e:
            self.logger.error(f"Failed to cleanup chroot: {e}")
    
    def run_command(self, command: List[str], **kwargs) -> subprocess.CompletedProcess:
        """
        Run command in chroot with filesystems mounted.
        
        This method maintains compatibility with the original API
        while using arch-chroot underneath.
        """
        try:
            # Convert legacy kwargs to ultrathink format
            if 'check' not in kwargs:
                kwargs['check'] = True
                
            return self._ultrathink.run(command, **kwargs)
            
        except subprocess.CalledProcessError as e:
            # Re-raise with original error for compatibility
            raise e
        except UltrathinkChrootError as e:
            # Convert to CalledProcessError for compatibility
            raise subprocess.CalledProcessError(1, command, stderr=str(e))
    
    # Additional convenience methods for enhanced functionality
    def run_bash_script(self, script: str, **kwargs) -> subprocess.CompletedProcess:
        """Run a bash script in the chroot"""
        return self._ultrathink.run_bash(script, **kwargs)
    
    def has_arch_chroot(self) -> bool:
        """Check if arch-chroot is available"""
        return self._ultrathink._arch_chroot_available
    
    def force_cleanup(self):
        """Force cleanup of all mounts"""
        self._ultrathink.cleanup()


# Provide alias for drop-in replacement
def get_chroot_manager(chroot_path: Path) -> ChrootManager:
    """
    Factory function to get a chroot manager.
    This allows easy switching between implementations.
    """
    return ChrootManager(chroot_path)


# Usage example showing compatibility:
# from builder.utils.chroot_manager_ultrathink import ChrootManager
# 
# # Works exactly like the original
# with ChrootManager(chroot_path) as chroot:
#     chroot.run_command(["apt-get", "update"], check=True)
#     chroot.run_command(["systemctl", "enable", "service"], check=True)
#
# # But also provides enhanced features:
# with ChrootManager(chroot_path) as chroot:
#     # Run bash script
#     chroot.run_bash_script("apt-get update && apt-get upgrade -y")
#     
#     # Check if using arch-chroot
#     if chroot.has_arch_chroot():
#         print("Using arch-chroot for enhanced reliability!")