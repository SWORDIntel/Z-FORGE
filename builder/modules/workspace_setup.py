#!/usr/bin/env python3
"""
Workspace Setup Module
Creates clean chroot environment with error recovery and validation
"""

import os
import shutil
import subprocess
import json
import stat
from pathlib import Path
from typing import Dict, Optional
import logging
from builder.core.lockfile import BuildLockfile

class WorkspaceSetup:
    """Creates clean chroot environment with error recovery and validation"""
    
    def __init__(self, workspace: Path, config: Dict):
        """
        Initialize workspace setup module
        
        Args:
            workspace: Path to workspace root
            config: Build configuration dictionary
        """
        
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"
        self.min_disk_space_gb = 15  # Minimum disk space required
        self.required_subdirs = [
            "temp", "cache", "build", "chroot", "output", "logs",
            "apt_cache", "apt_state", "iso_build", "tmp"
        ]
        
    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[BuildLockfile] = None) -> Dict:
        """
        Create workspace with resume capability and validation
        
        Args:
            resume_data: Optional checkpoint data to resume from
            lockfile: Optional BuildLockfile instance for recording versions/checksums.
                      Note: WorkspaceSetup itself may not use it much.
            
        Returns:
            Dict with status and checkpoint information
        """
        
        self.logger.info("Setting up workspace with validation...")
        
        checkpoints = {
            'disk_space_validated': False,
            'root_privileges_verified': False,
            'directories_created': False,
            'permissions_set': False,
            'mounts_prepared': False,
            'workspace_validated': False
        }
        
        # Load previous progress if resuming
        if resume_data:
            checkpoints = resume_data
            self.logger.info(f"Resuming from checkpoint: {checkpoints}")
        
        try:
            if not checkpoints.get('disk_space_validated'):
                self._validate_disk_space()
                checkpoints['disk_space_validated'] = True
                
            if not checkpoints.get('root_privileges_verified'):
                self._verify_root_privileges()
                checkpoints['root_privileges_verified'] = True
                
            if not checkpoints.get('directories_created'):
                self._create_directories()
                checkpoints['directories_created'] = True
                
            if not checkpoints.get('permissions_set'):
                self._set_permissions()
                checkpoints['permissions_set'] = True
                
            if not checkpoints.get('mounts_prepared'):
                self._prepare_mounts()
                checkpoints['mounts_prepared'] = True
                
            if not checkpoints.get('workspace_validated'):
                self._validate_workspace()
                checkpoints['workspace_validated'] = True
                
            self.logger.info(f"Workspace setup complete and validated: {self.workspace}")
            self.logger.info(f"Available disk space: {self._get_available_space_gb():.1f}GB")
            self.logger.info(f"Workspace structure: {len(self.required_subdirs)} directories created")
                
            return {
                'status': 'success',
                'workspace': str(self.workspace),
                'chroot': str(self.chroot_path),
                'available_space_gb': self._get_available_space_gb(),
                'directories_created': len(self.required_subdirs),
                'module_checkpoint_data': checkpoints,
                'version': '2.0'
            }
            
        except Exception as e:
            self.logger.error(f"Workspace setup failed: {e}")
            # Return current checkpoints state in case of failure for potential debugging
            return {
                'status': 'error',
                'error': str(e),
                'module_checkpoint_data': checkpoints,
                'module': self.__class__.__name__
            }
    
    def _validate_disk_space(self):
        """Validate available disk space meets requirements"""
        
        available_gb = self._get_available_space_gb()
        self.logger.info(f"Available disk space: {available_gb:.1f}GB")
        
        if available_gb < self.min_disk_space_gb:
            raise RuntimeError(
                f"Insufficient disk space: {available_gb:.1f}GB available, "
                f"{self.min_disk_space_gb}GB required"
            )
        
        self.logger.info(f"Disk space validation passed: {available_gb:.1f}GB available")
    
    def _verify_root_privileges(self):
        """Verify we have root privileges for workspace operations"""
        
        if os.geteuid() != 0:
            # Try to test sudo access
            try:
                subprocess.run(["sudo", "-n", "true"], check=True, capture_output=True)
                self.logger.info("Sudo privileges verified")
            except subprocess.CalledProcessError:
                raise RuntimeError(
                    "Root privileges required for workspace setup. "
                    "Please run as root or ensure sudo is configured."
                )
        else:
            self.logger.info("Running as root - privileges verified")
    
    def _get_available_space_gb(self) -> float:
        """Get available disk space in GB for workspace parent directory"""
        
        parent_path = self.workspace.parent if self.workspace.exists() else Path("/root")
        statvfs = os.statvfs(parent_path)
        available_bytes = statvfs.f_frsize * statvfs.f_bavail
        return available_bytes / (1024**3)
    
    def _create_directories(self):
        """Create workspace directory structure with robust error handling"""
        
        self.logger.info("Creating workspace directories...")
        
        # Check if workspace already exists and has content
        if self.workspace.exists() and any(self.workspace.iterdir()):
            self.logger.warning(f"Workspace {self.workspace} already exists with content!")
            self._cleanup_existing_workspace()
        
        # Create main workspace directory with sudo and full permissions
        subprocess.run(["sudo", "mkdir", "-p", str(self.workspace)], check=True)
        subprocess.run(["sudo", "chmod", "777", str(self.workspace)], check=True)
        
        # Create all required subdirectories
        for directory in self.required_subdirs:
            dir_path = self.workspace / directory
            subprocess.run(["sudo", "mkdir", "-p", str(dir_path)], check=True)
            
            # Set appropriate permissions
            if directory == "tmp":
                subprocess.run(["sudo", "chmod", "1777", str(dir_path)], check=True)  # Sticky bit
            else:
                subprocess.run(["sudo", "chmod", "777", str(dir_path)], check=True)
                
        self.logger.info(f"Created {len(self.required_subdirs)} workspace directories")
    
    def _cleanup_existing_workspace(self):
        """Clean up existing workspace safely"""
        
        self.logger.info("Cleaning up existing workspace...")
        
        try:
            # First unmount any filesystems that might be mounted
            chroot_mounts = ["dev/pts", "dev", "proc", "sys", "run"]
            for mount in chroot_mounts:
                mount_path = self.workspace / "chroot" / mount
                if mount_path.exists():
                    try:
                        subprocess.run(["sudo", "mountpoint", "-q", str(mount_path)], 
                                     capture_output=True, check=True)
                        # If mountpoint succeeds, it's mounted
                        subprocess.run(["sudo", "umount", "-l", str(mount_path)], 
                                     capture_output=True, check=False)
                        self.logger.info(f"Unmounted {mount_path}")
                    except subprocess.CalledProcessError:
                        pass  # Not mounted or error, continue
            
            # Remove the workspace contents but preserve the directory structure if possible
            for item in self.workspace.iterdir():
                if item.is_dir() and item.name in ["cache", "log", "tmp"]:
                    # Preserve cache and log directories, just clean contents
                    for subitem in item.iterdir():
                        subprocess.run(["sudo", "rm", "-rf", str(subitem)], check=False)
                else:
                    subprocess.run(["sudo", "rm", "-rf", str(item)], check=False)
                    
            self.logger.info("Successfully cleaned existing workspace")
            
        except Exception as e:
            self.logger.warning(f"Partial cleanup failure: {e}, attempting full removal")
            try:
                subprocess.run(["sudo", "rm", "-rf", str(self.workspace)], check=True)
                self.logger.info("Full workspace removal successful")
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Failed to clean existing workspace: {e}")
    
    def _set_permissions(self):
        """Set correct permissions for workspace"""
        
        self.logger.info("Setting permissions...")
        
        # Use find to set permissions while excluding special filesystems
        # This prevents errors when /proc, /sys, /dev are mounted
        find_cmd = [
            "sudo", "find", str(self.workspace),
            # Exclude special filesystem directories
            "-path", f"{self.workspace}/chroot/proc", "-prune", "-o",
            "-path", f"{self.workspace}/chroot/sys", "-prune", "-o",
            "-path", f"{self.workspace}/chroot/dev", "-prune", "-o",
            "-path", f"{self.workspace}/chroot/run", "-prune", "-o",
            # For all other files/directories, set permissions
            "-type", "d", "-exec", "chmod", "777", "{}", "+",
            "-o", "-type", "f", "-exec", "chmod", "666", "{}", "+"
        ]
        
        try:
            subprocess.run(find_cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            # If find fails, try a more aggressive approach
            self.logger.warning(f"Find command failed: {e}, trying alternative approach")
            
            # Set permissions on workspace root and direct subdirectories only
            subprocess.run(["sudo", "chmod", "777", str(self.workspace)], check=True)
            
            # Set permissions on each subdirectory individually, skipping chroot
            for item in self.workspace.iterdir():
                if item.name != "chroot" and item.is_dir():
                    subprocess.run(["sudo", "chmod", "-R", "777", str(item)], check=True)
            
            # For chroot, only set permissions on the directory itself, not recursively
            if self.chroot_path.exists():
                subprocess.run(["sudo", "chmod", "777", str(self.chroot_path)], check=True)
        
        # Specifically set sticky bit on tmp directory
        tmp_dir = self.workspace / "tmp"
        if tmp_dir.exists():
            subprocess.run(["sudo", "chmod", "1777", str(tmp_dir)], check=True)
    
    def _prepare_mounts(self):
        """Prepare mount points for chroot with validation"""
        
        self.logger.info("Preparing chroot mount points...")
        
        # Create mount points in chroot
        mount_points = [
            "dev",
            "dev/pts", 
            "proc",
            "sys",
            "run",
            "tmp"  # Add tmp mount point
        ]
        
        for mount in mount_points:
            mount_dir = self.chroot_path / mount
            subprocess.run(["sudo", "mkdir", "-p", str(mount_dir)], check=True)
            
            # Set appropriate permissions for mount points
            if mount == "tmp":
                subprocess.run(["sudo", "chmod", "1755", str(mount_dir)], check=True)
            else:
                subprocess.run(["sudo", "chmod", "755", str(mount_dir)], check=True)
                
            # Verify mount point was created
            if not mount_dir.exists():
                raise RuntimeError(f"Failed to create mount point: {mount_dir}")
                
        self.logger.info(f"Created {len(mount_points)} chroot mount points")
    
    def _validate_workspace(self):
        """Final validation of workspace structure and permissions"""
        
        self.logger.info("Performing final workspace validation...")
        
        # Check workspace root exists and is accessible
        if not self.workspace.exists():
            raise RuntimeError(f"Workspace directory missing: {self.workspace}")
            
        # Check workspace is writable
        test_file = self.workspace / ".workspace_test"
        try:
            test_file.write_text("test")
            test_file.unlink()
        except Exception as e:
            raise RuntimeError(f"Workspace not writable: {e}")
            
        # Check all required subdirectories exist
        missing_dirs = []
        for subdir in self.required_subdirs:
            dir_path = self.workspace / subdir
            if not dir_path.exists():
                missing_dirs.append(subdir)
                
        if missing_dirs:
            raise RuntimeError(f"Missing workspace directories: {missing_dirs}")
            
        # Check chroot mount points
        mount_points = ["dev", "proc", "sys", "run", "tmp"]
        missing_mounts = []
        for mount in mount_points:
            mount_path = self.chroot_path / mount
            if not mount_path.exists():
                missing_mounts.append(mount)
                
        if missing_mounts:
            raise RuntimeError(f"Missing chroot mount points: {missing_mounts}")
            
        # Log final validation results
        self.logger.info("Workspace validation successful:")
        self.logger.info(f"  - Workspace: {self.workspace} ({self._get_available_space_gb():.1f}GB available)")
        self.logger.info(f"  - Subdirectories: {len(self.required_subdirs)} created")
        self.logger.info(f"  - Mount points: {len(mount_points)} prepared")
        self.logger.info(f"  - Permissions: Validated and set correctly")
    
