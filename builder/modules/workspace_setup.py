#!/usr/bin/env python3
"""
Workspace Setup Module
Creates clean chroot environment with error recovery
"""

import os
import shutil
import subprocess
import json
from pathlib import Path
from typing import Dict, Optional
import logging
from builder.core.lockfile import BuildLockfile

class WorkspaceSetup:
    """Creates clean chroot environment with error recovery"""
    
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
        
    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[BuildLockfile] = None) -> Dict:
        """
        Create workspace with resume capability
        
        Args:
            resume_data: Optional checkpoint data to resume from
            lockfile: Optional BuildLockfile instance for recording versions/checksums.
                      Note: WorkspaceSetup itself may not use it much.
            
        Returns:
            Dict with status and checkpoint information
        """
        
        self.logger.info("Setting up workspace...")
        
        checkpoints = {
            'directories_created': False,
            'permissions_set': False,
            'mounts_prepared': False
        }
        
        # Load previous progress if resuming
        if resume_data: # resume_data is now the checkpoints dict itself
            checkpoints = resume_data
            self.logger.info(f"Resuming from checkpoint: {checkpoints}")
        
        try:
            if not checkpoints.get('directories_created'): # Use .get for safety on first run
                self._create_directories()
                checkpoints['directories_created'] = True
                # self._save_checkpoint(checkpoints) # Removed: ZForgeBuilder handles persistence
                
            if not checkpoints.get('permissions_set'):
                self._set_permissions()
                checkpoints['permissions_set'] = True
                # self._save_checkpoint(checkpoints) # Removed
                
            if not checkpoints.get('mounts_prepared'):
                self._prepare_mounts()
                checkpoints['mounts_prepared'] = True
                # self._save_checkpoint(checkpoints) # Removed
                
            self.logger.info(f"Workspace setup complete: {self.workspace}")
                
            return {
                'status': 'success',
                'workspace': str(self.workspace),
                'chroot': str(self.chroot_path),
                'module_checkpoint_data': checkpoints, # Adhere to the new contract
                'version': '1.0' # Keep module version
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
    
    def _create_directories(self):
        """Create workspace directory structure"""
        
        self.logger.info("Creating directories...")
        
        # Check if workspace already exists and has content
        if self.workspace.exists() and any(self.workspace.iterdir()):
            self.logger.warning(f"Workspace {self.workspace} already exists with content!")
            # Try to clean it up
            self.logger.info("Attempting to clean existing workspace...")
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
                            subprocess.run(["sudo", "umount", str(mount_path)], 
                                         capture_output=True, check=False)
                        except:
                            pass  # Not mounted or error, continue
                
                # Remove the workspace
                subprocess.run(["sudo", "rm", "-rf", str(self.workspace)], check=True)
                self.logger.info("Successfully cleaned existing workspace")
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Failed to clean existing workspace: {e}")
        
        # Create main workspace directory with sudo and full permissions
        subprocess.run(["sudo", "mkdir", "-p", str(self.workspace)], check=True)
        subprocess.run(["sudo", "chmod", "777", str(self.workspace)], check=True)
        
        # Create chroot directory with full permissions
        subprocess.run(["sudo", "mkdir", "-p", str(self.chroot_path)], check=True)
        subprocess.run(["sudo", "chmod", "777", str(self.chroot_path)], check=True)
        
        # Create additional workspace directories
        dirs = [
            "apt_cache",
            "apt_state",
            "cache",
            "iso_build",
            "log",
            "tmp"
        ]
        
        for directory in dirs:
            dir_path = self.workspace / directory
            subprocess.run(["sudo", "mkdir", "-p", str(dir_path)], check=True)
            subprocess.run(["sudo", "chmod", "777", str(dir_path)], check=True)
    
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
        """Prepare mount points for chroot"""
        
        self.logger.info("Preparing mounts...")
        
        # Create mount points in chroot
        mount_points = [
            "dev",
            "dev/pts",
            "proc",
            "sys",
            "run"
        ]
        
        for mount in mount_points:
            mount_dir = self.chroot_path / mount
            subprocess.run(["sudo", "mkdir", "-p", str(mount_dir)], check=True)
            subprocess.run(["sudo", "chmod", "755", str(mount_dir)], check=True)
    
    # def _save_checkpoint(self, checkpoints: Dict): # Removed
    #     """Save checkpoint data to file""" # Removed
          # Removed
    #     checkpoint_file = self.workspace / "workspace_checkpoint.json" # Removed
          # Removed
    #     with open(checkpoint_file, 'w') as f: # Removed
    #         json.dump(checkpoints, f) # Removed
