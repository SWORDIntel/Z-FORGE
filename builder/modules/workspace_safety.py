#!/usr/bin/env python3
"""
Workspace Safety Module for Z-FORGE
CRITICAL: Ensures all mounts are cleaned up to prevent system damage
"""

import subprocess
import logging
import atexit
import signal
import sys
from pathlib import Path
from typing import Dict, Set, Optional, Any

class WorkspaceSafety:
    """
    CRITICAL MODULE: Ensures workspace is ALWAYS safely cleaned up
    Prevents /dev/ptmx and other system issues
    """
    
    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"
        self.mounted_paths: Set[str] = set()
        
        # CRITICAL: Register cleanup on ANY exit
        atexit.register(self._emergency_unmount_all)
        signal.signal(signal.SIGTERM, self._signal_cleanup)
        signal.signal(signal.SIGINT, self._signal_cleanup)
        signal.signal(signal.SIGHUP, self._signal_cleanup)
        
    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[Any] = None) -> Dict:
        """Track all mounts for safe cleanup"""
        self.logger.info("Initializing workspace safety module...")
        
        # Check for existing mounts
        self._detect_existing_mounts()
        
        # Log current mount state
        self.logger.info(f"Tracking {len(self.mounted_paths)} existing mounts")
        
        return {
            'status': 'success',
            'tracked_mounts': list(self.mounted_paths)
        }
    
    def _detect_existing_mounts(self):
        """Detect any existing mounts in workspace"""
        try:
            result = subprocess.run(
                ["mount"], 
                capture_output=True, 
                text=True
            )
            
            for line in result.stdout.splitlines():
                if str(self.workspace) in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        mount_point = parts[2]
                        self.mounted_paths.add(mount_point)
                        self.logger.warning(f"Found existing mount: {mount_point}")
                        
        except Exception as e:
            self.logger.error(f"Failed to detect mounts: {e}")
    
    def unmount_all(self):
        """Safely unmount all tracked paths"""
        if not self.mounted_paths:
            return
            
        self.logger.info("=== CRITICAL: Unmounting workspace filesystems ===")
        
        # Sort in reverse order (deepest paths first)
        sorted_mounts = sorted(self.mounted_paths, reverse=True)
        
        for mount_path in sorted_mounts:
            self._safe_unmount(mount_path)
            
        # Double-check nothing remains
        self._verify_no_mounts()
        
    def _safe_unmount(self, mount_path: str) -> bool:
        """Safely unmount a single path with retries"""
        self.logger.info(f"Unmounting: {mount_path}")
        
        # Try normal unmount first
        try:
            subprocess.run(
                ["sudo", "umount", mount_path],
                check=True,
                capture_output=True
            )
            self.logger.info(f"  ✓ Successfully unmounted {mount_path}")
            self.mounted_paths.discard(mount_path)
            return True
        except subprocess.CalledProcessError:
            pass
            
        # Try lazy unmount if normal fails
        self.logger.warning(f"  Normal unmount failed, trying lazy unmount...")
        try:
            subprocess.run(
                ["sudo", "umount", "-l", mount_path],
                check=True,
                capture_output=True
            )
            self.logger.info(f"  ✓ Lazy unmount successful for {mount_path}")
            self.mounted_paths.discard(mount_path)
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"  ✗ Failed to unmount {mount_path}: {e}")
            return False
            
    def _verify_no_mounts(self):
        """Verify no mounts remain in workspace"""
        try:
            result = subprocess.run(
                ["mount", "|", "grep", str(self.workspace)],
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.stdout.strip():
                self.logger.error("=== CRITICAL WARNING ===")
                self.logger.error("Mounts still exist in workspace:")
                self.logger.error(result.stdout)
                self.logger.error("MANUAL INTERVENTION REQUIRED!")
                self.logger.error("Run: sudo umount -l <mount_path> for each mount")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to verify mounts: {e}")
            
        return True
        
    def _emergency_unmount_all(self):
        """EMERGENCY: Unmount everything on exit"""
        try:
            # Critical unmount sequence
            critical_mounts = [
                self.chroot_path / "dev/pts",
                self.chroot_path / "dev",
                self.chroot_path / "sys",
                self.chroot_path / "proc"
            ]
            
            for mount in critical_mounts:
                if mount.exists():
                    try:
                        subprocess.run(
                            ["sudo", "umount", "-l", str(mount)],
                            stderr=subprocess.DEVNULL
                        )
                    except:
                        pass
                        
            # Also unmount any tracked paths
            for mount_path in list(self.mounted_paths):
                try:
                    subprocess.run(
                        ["sudo", "umount", "-l", mount_path],
                        stderr=subprocess.DEVNULL
                    )
                except:
                    pass
                    
        except:
            # Silent fail - this is emergency cleanup
            pass
            
    def _signal_cleanup(self, signum, frame):
        """Handle signals with cleanup"""
        self.logger.critical(f"Received signal {signum} - EMERGENCY CLEANUP")
        self._emergency_unmount_all()
        sys.exit(1)
        
    def register_mount(self, mount_path: str):
        """Register a new mount for tracking"""
        self.mounted_paths.add(mount_path)
        self.logger.debug(f"Registered mount: {mount_path}")
        
    def __del__(self):
        """Destructor - last chance cleanup"""
        try:
            self._emergency_unmount_all()
        except:
            pass