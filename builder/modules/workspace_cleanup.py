#!/usr/bin/env python3
"""
Workspace Cleanup Module
Handles cleanup of the build workspace including unmounting filesystems
"""

import os
import subprocess
import shutil
import time
from pathlib import Path
from typing import Dict, Optional, List
import logging
from builder.core.lockfile import BuildLockfile

class WorkspaceCleanup:
    """Handles safe cleanup of the build workspace"""
    
    def __init__(self, workspace: Path, config: Dict):
        """
        Initialize workspace cleanup module
        
        Args:
            workspace: Path to workspace root
            config: Build configuration dictionary
        """
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"
        
    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[BuildLockfile] = None) -> Dict:
        """
        Execute workspace cleanup
        
        Args:
            resume_data: Not used for cleanup
            lockfile: Not used for cleanup
            
        Returns:
            Dict with cleanup status
        """
        
        self.logger.info("Starting workspace cleanup...")
        
        try:
            # Step 1: Unmount all filesystems
            self._unmount_all_filesystems()
            
            # Step 2: Kill any processes using the workspace
            self._kill_workspace_processes()
            
            # Step 3: Remove the workspace directory
            self._remove_workspace()
            
            self.logger.info("Workspace cleanup completed successfully")
            
            return {
                'status': 'success',
                'workspace_removed': True,
                'module': self.__class__.__name__
            }
            
        except Exception as e:
            self.logger.error(f"Workspace cleanup failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _unmount_all_filesystems(self):
        """Unmount all filesystems in the workspace"""
        
        self.logger.info("Unmounting filesystems...")
        
        # Standard mount points in chroot
        mount_points = ["dev/pts", "dev", "proc", "sys", "run"]
        
        for mount_point in mount_points:
            mount_path = self.chroot_path / mount_point
            self._safe_unmount(mount_path)
        
        # Check for any other mounts under workspace
        self._unmount_recursive(self.workspace)
    
    def _safe_unmount(self, mount_path: Path) -> bool:
        """
        Safely unmount a filesystem
        
        Args:
            mount_path: Path to unmount
            
        Returns:
            True if successful or not mounted, False otherwise
        """
        
        if not mount_path.exists():
            return True
            
        try:
            # Check if mounted
            result = subprocess.run(
                ["sudo", "mountpoint", "-q", str(mount_path)],
                capture_output=True
            )
            
            if result.returncode != 0:
                # Not mounted
                return True
            
            # Try normal unmount
            self.logger.debug(f"Unmounting {mount_path}")
            result = subprocess.run(
                ["sudo", "umount", str(mount_path)],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.logger.debug(f"Successfully unmounted {mount_path}")
                return True
            
            # Try lazy unmount as fallback
            self.logger.warning(f"Normal unmount failed for {mount_path}, trying lazy unmount")
            result = subprocess.run(
                ["sudo", "umount", "-l", str(mount_path)],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.logger.debug(f"Successfully lazy-unmounted {mount_path}")
                return True
            else:
                self.logger.error(f"Failed to unmount {mount_path}: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error unmounting {mount_path}: {e}")
            return False
    
    def _unmount_recursive(self, base_path: Path):
        """Recursively unmount all filesystems under a path"""
        
        try:
            # Get all mounts under the base path
            result = subprocess.run(
                ["mount"],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse mount output and find mounts under our workspace
            mounts = []
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 3:
                    mount_point = parts[2]
                    if mount_point.startswith(str(base_path)):
                        mounts.append(mount_point)
            
            # Sort in reverse order to unmount nested mounts first
            mounts.sort(reverse=True)
            
            for mount_point in mounts:
                self._safe_unmount(Path(mount_point))
                
        except Exception as e:
            self.logger.warning(f"Error checking mounts: {e}")
    
    def _kill_workspace_processes(self):
        """Kill any processes using the workspace"""
        
        self.logger.info("Checking for processes using workspace...")
        
        try:
            # Use lsof to find processes
            result = subprocess.run(
                ["sudo", "lsof", "+D", str(self.workspace)],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout:
                # Parse lsof output
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                pids = set()
                
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 2:
                        pids.add(parts[1])
                
                if pids:
                    self.logger.warning(f"Found {len(pids)} processes using workspace")
                    
                    # Try graceful termination first
                    for pid in pids:
                        try:
                            subprocess.run(["sudo", "kill", "-TERM", pid], check=False)
                        except:
                            pass
                    
                    # Wait a bit
                    time.sleep(2)
                    
                    # Force kill remaining processes
                    for pid in pids:
                        try:
                            subprocess.run(["sudo", "kill", "-KILL", pid], check=False)
                        except:
                            pass
                    
                    self.logger.info("Terminated processes using workspace")
            else:
                self.logger.debug("No processes found using workspace")
                
        except FileNotFoundError:
            self.logger.debug("lsof not available, skipping process check")
        except Exception as e:
            self.logger.warning(f"Error checking processes: {e}")
    
    def _remove_workspace(self):
        """Remove the workspace directory"""
        
        self.logger.info("Removing workspace directory...")
        
        if not self.workspace.exists():
            self.logger.info("Workspace does not exist, nothing to remove")
            return
        
        try:
            # Try with shutil first
            shutil.rmtree(self.workspace, ignore_errors=False)
            self.logger.info("Successfully removed workspace")
        except Exception as e:
            self.logger.warning(f"shutil.rmtree failed: {e}, trying with sudo")
            
            # Try with sudo rm -rf
            try:
                subprocess.run(
                    ["sudo", "rm", "-rf", str(self.workspace)],
                    check=True,
                    capture_output=True,
                    text=True
                )
                self.logger.info("Successfully removed workspace with sudo")
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Failed to remove workspace: {e.stderr}")
    
    def cleanup_on_error(self):
        """
        Quick cleanup method for error conditions.
        This is a best-effort cleanup that doesn't raise exceptions.
        """
        
        try:
            self.logger.info("Performing emergency cleanup...")
            
            # Try to unmount filesystems
            mount_points = ["dev/pts", "dev", "proc", "sys", "run"]
            for mount_point in mount_points:
                mount_path = self.chroot_path / mount_point
                if mount_path.exists():
                    subprocess.run(
                        ["sudo", "umount", "-l", str(mount_path)],
                        capture_output=True,
                        check=False
                    )
            
            # Don't remove workspace on error - leave for debugging
            self.logger.info("Emergency cleanup completed (workspace preserved for debugging)")
            
        except Exception as e:
            self.logger.error(f"Emergency cleanup failed: {e}")