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
        
    def execute(self, resume_data: Optional[Dict] = None) -> Dict:
        """
        Create workspace with resume capability
        
        Args:
            resume_point: Optional checkpoint data to resume from
            
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
        if resume_data and 'checkpoints' in resume_data:
            checkpoints = resume_data['checkpoints']
            self.logger.info(f"Resuming from checkpoint: {checkpoints}")
        
        try:
            if not checkpoints['directories_created']:
                self._create_directories()
                checkpoints['directories_created'] = True
                self._save_checkpoint(checkpoints)
                
            if not checkpoints['permissions_set']:
                self._set_permissions()
                checkpoints['permissions_set'] = True
                self._save_checkpoint(checkpoints)
                
            if not checkpoints['mounts_prepared']:
                self._prepare_mounts()
                checkpoints['mounts_prepared'] = True
                self._save_checkpoint(checkpoints)
                
            self.logger.info(f"Workspace setup complete: {self.workspace}")
                
            return {
                'status': 'success',
                'workspace': str(self.workspace),
                'chroot': str(self.chroot_path),
                'checkpoints': checkpoints,
                'version': '1.0'
            }
            
        except Exception as e:
            self.logger.error(f"Workspace setup failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'checkpoint': checkpoints,
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
    
    def _save_checkpoint(self, checkpoints: Dict):
        """Save checkpoint data to file"""
        
        checkpoint_file = self.workspace / "workspace_checkpoint.json"
        
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoints, f)
