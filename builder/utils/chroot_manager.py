#!/usr/bin/env python3
# z-forge/builder/utils/chroot_manager.py

"""
Centralized Chroot Manager
Provides context manager for safely mounting/unmounting filesystems in chroot
"""

import subprocess
import logging
from pathlib import Path
from typing import List, Tuple

class ChrootManager:
    """Context manager for chroot operations with automatic filesystem mounting"""
    
    def __init__(self, chroot_path: Path):
        self.chroot_path = Path(chroot_path)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.mounts = [
            ("proc", "proc", self.chroot_path / "proc"),
            ("sysfs", "sys", self.chroot_path / "sys"),
            ("devtmpfs", "udev", self.chroot_path / "dev"),
            ("devpts", "devpts", self.chroot_path / "dev/pts")
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
        for fs_type, source, target in self.mounts:
            if not target.exists():
                target.mkdir(parents=True, exist_ok=True)
            
            # Check if already mounted
            mount_check = subprocess.run(
                ["mountpoint", "-q", str(target)],
                capture_output=True
            )
            
            if mount_check.returncode != 0:
                self.logger.debug(f"Mounting {source} to {target}")
                try:
                    subprocess.run(
                        ["mount", "-t", fs_type, source, str(target)],
                        check=True
                    )
                except subprocess.CalledProcessError as e:
                    self.logger.error(f"Failed to mount {source}: {e}")
                    raise
    
    def unmount_filesystems(self):
        """Unmount pseudo filesystems in reverse order."""
        # Reverse order for unmounting
        for _, _, target in reversed(self.mounts):
            mount_check = subprocess.run(
                ["mountpoint", "-q", str(target)],
                capture_output=True
            )
            
            if mount_check.returncode == 0:
                self.logger.debug(f"Unmounting {target}")
                subprocess.run(["umount", str(target)], check=False)
    
    def run_command(self, command: List[str], **kwargs) -> subprocess.CompletedProcess:
        """Run command in chroot with filesystems mounted"""
        full_cmd = ["chroot", str(self.chroot_path)] + command
        self.logger.debug(f"Running in chroot: {' '.join(command)}")
        return subprocess.run(full_cmd, **kwargs)


# Usage example:
# from builder.utils.chroot_manager import ChrootManager
# 
# with ChrootManager(chroot_path) as chroot:
#     chroot.run_command(["apt-get", "update"], check=True)
#     chroot.run_command(["systemctl", "enable", "service"], check=True)