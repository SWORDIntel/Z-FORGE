#!/usr/bin/env python3
# z-forge/builder/modules/proxmox_storage_config.py

"""
Proxmox VE Storage Configuration Module for Z-Forge.

This module configures ZFS storage for Proxmox VE.
"""

import subprocess
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional

class ProxmoxStorageConfig:
    """Configures storage for Proxmox VE."""
    
    def __init__(self, workspace: Path, config: Dict[str, Any]) -> None:
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"
        
    def execute(self, resume_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute Proxmox storage configuration."""
        self.logger.info("Configuring Proxmox VE storage...")
        
        try:
            # Create ZFS datasets for Proxmox
            self._create_zfs_datasets()
            
            # Configure Proxmox storage
            self._configure_storage()
            
            # Set ZFS properties for optimal performance
            self._optimize_zfs_settings()
            
            return {
                'status': 'success',
                'storage_configured': True,
                'storage_types': ['local', 'local-zfs']
            }
            
        except Exception as e:
            self.logger.error(f"Storage configuration failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
            
    def _create_zfs_datasets(self):
        """Create ZFS datasets for Proxmox storage"""
        datasets = [
            ('rpool/data', {'mountpoint': 'none'}),
            ('rpool/data/vm', {'mountpoint': 'none'}),
            ('rpool/data/ct', {'mountpoint': 'none'}),
        ]
        
        for dataset, properties in datasets:
            cmd = ["zfs", "create"]
            for key, value in properties.items():
                cmd.extend(["-o", f"{key}={value}"])
            cmd.append(dataset)
            
            self.logger.info(f"Creating dataset {dataset}")
            subprocess.run(cmd, check=False)  # May already exist
            
    def _configure_storage(self):
        """Configure Proxmox storage configuration"""
        storage_cfg = self.chroot_path / "etc/pve/storage.cfg"
        storage_cfg.parent.mkdir(parents=True, exist_ok=True)
        
        config_content = """dir: local
    path /var/lib/vz
    content iso,vztmpl,backup
    maxfiles 3

zfspool: local-zfs
    pool rpool/data
    content images,rootdir
    nodes localhost
"""
        
        with open(storage_cfg, 'w') as f:
            f.write(config_content)
            
        self.logger.info("Configured Proxmox storage")
        
    def _optimize_zfs_settings(self):
        """Optimize ZFS settings for Proxmox"""
        optimizations = {
            'rpool/data/vm': {
                'volblocksize': '16k',
                'compression': 'lz4',
                'sync': 'standard'
            },
            'rpool/data/ct': {
                'recordsize': '128k',
                'compression': 'lz4',
                'atime': 'off'
            }
        }
        
        for dataset, properties in optimizations.items():
            for key, value in properties.items():
                cmd = ["zfs", "set", f"{key}={value}", dataset]
                subprocess.run(cmd, check=False)
