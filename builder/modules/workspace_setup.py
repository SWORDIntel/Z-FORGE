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
        
        # Create main workspace directory
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        # Create chroot directory
        self.chroot_path.mkdir(parents=True, exist_ok=True)
        
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
            (self.workspace / directory).mkdir(parents=True, exist_ok=True)
    
    def _set_permissions(self):
        """Set correct permissions for workspace"""
        
        self.logger.info("Setting permissions...")
        
        # Set world-writable permissions for temp directories
        temp_dirs = [
            self.workspace / "tmp"
        ]
        
        for directory in temp_dirs:
            directory.chmod(0o1777)
    
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
            mount_dir.mkdir(parents=True, exist_ok=True)
    
    # def _save_checkpoint(self, checkpoints: Dict): # Removed
    #     """Save checkpoint data to file""" # Removed
          # Removed
    #     checkpoint_file = self.workspace / "workspace_checkpoint.json" # Removed
          # Removed
    #     with open(checkpoint_file, 'w') as f: # Removed
    #         json.dump(checkpoints, f) # Removed
