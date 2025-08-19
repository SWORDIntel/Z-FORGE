#!/usr/bin/env python3
# z-forge/builder/modules/proxmox_storage_config.py

"""
Proxmox VE 9 Storage Configuration Module for Debian Trixie.
Configures ZFS and LVM storage for Proxmox VE 9 on Trixie.
"""

import subprocess
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional

class ProxmoxStorageConfig:
    """Configures Proxmox VE 9 storage for Debian Trixie."""
    
    def __init__(self, workspace: Path, config: Dict[str, Any]) -> None:
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"
        self.pve_version = "9.0"
        self.debian_version = "trixie"
        
    def execute(self, resume_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute Proxmox VE 9 storage configuration for Trixie."""
        self.logger.info("Configuring Proxmox VE 9 storage for Debian Trixie...")
        
        try:
            self._configure_zfs_storage()
            self._configure_lvm_storage()
            self._create_storage_config()
            
            return {
                'status': 'success',
                'storage_configured': True,
                'zfs_configured': True,
                'lvm_configured': True,
                'proxmox_version': '9.0',
                'debian_version': 'trixie'
            }
            
        except Exception as e:
            self.logger.error(f"Storage configuration failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _configure_zfs_storage(self):
        """Configure ZFS storage for Proxmox VE 9"""
        self.logger.info("Configuring ZFS storage...")
        
        # Create ZFS storage configuration directory
        zfs_dir = self.chroot_path / "etc/pve/storage"
        zfs_dir.mkdir(parents=True, exist_ok=True)
        
        # ZFS configuration for Trixie
        zfs_config = self.chroot_path / "etc/pve/storage.cfg"
        storage_config = """# Proxmox VE 9 Storage Configuration for Trixie

# Local directory storage
dir: local
	path /var/lib/vz
	content backup,vztmpl,iso,snippets
	shared 0

# ZFS storage pool
zfspool: zfs-pool
	pool rpool/data
	content images,rootdir
	sparse 1

# ZFS for VM images
zfspool: vm-storage
	pool rpool/vm-data
	content images
	sparse 1
	
# Directory for ISO files
dir: iso-storage
	path /var/lib/vz/template/iso
	content iso
	shared 0
"""
        zfs_config.write_text(storage_config)
        
        # Create ZFS mount points
        zfs_paths = [
            "var/lib/vz",
            "var/lib/vz/template",
            "var/lib/vz/template/iso",
            "var/lib/vz/dump",
            "var/lib/vz/snippets"
        ]
        
        for zfs_path in zfs_paths:
            (self.chroot_path / zfs_path).mkdir(parents=True, exist_ok=True)
    
    def _configure_lvm_storage(self):
        """Configure LVM storage for Proxmox VE 9"""
        self.logger.info("Configuring LVM storage...")
        
        # LVM configuration
        lvm_config = self.chroot_path / "etc/lvm/lvm.conf.d/pve.conf"
        lvm_config.parent.mkdir(parents=True, exist_ok=True)
        
        lvm_content = """# Proxmox VE 9 LVM Configuration for Trixie
# Enable thin provisioning
activation {
    thin_pool_autoextend_threshold = 80
    thin_pool_autoextend_percent = 20
}

# Filter for Proxmox
devices {
    filter = [ "a|/dev/sd.*|", "r|.*|" ]
    obtain_device_list_from_udev = 1
}
"""
        lvm_config.write_text(lvm_content)
        
        # Create LVM storage directories
        lvm_paths = [
            "dev/pve",
            "etc/lvm/backup",
            "etc/lvm/archive"
        ]
        
        for lvm_path in lvm_paths:
            (self.chroot_path / lvm_path).mkdir(parents=True, exist_ok=True)
    
    def _create_storage_config(self):
        """Create Proxmox VE 9 storage configuration"""
        self.logger.info("Creating storage configuration...")
        
        # Main storage config
        storage_cfg = self.chroot_path / "etc/pve/storage.cfg"
        if not storage_cfg.exists():
            storage_content = """# Proxmox VE 9 Storage Configuration for Trixie

# Local directory storage
dir: local
	path /var/lib/vz
	content backup,vztmpl,iso,snippets
	shared 0
	maxfiles 3

# Local LVM storage
lvm: local-lvm
	vgname pve
	content images,rootdir
	shared 0

# ZFS pool (if available)
zfspool: local-zfs
	pool rpool/data
	content images,rootdir
	sparse 1
	mountpoint /rpool/data
"""
            storage_cfg.write_text(storage_content)
        
        # Create storage status script
        status_script = self.chroot_path / "usr/share/zforge/storage-status.sh"
        status_script.parent.mkdir(parents=True, exist_ok=True)
        
        status_script.write_text("""#!/bin/bash
# Proxmox VE 9 Storage Status for Trixie

echo "Proxmox VE 9 Storage Status (Trixie)"
echo "===================================="

# Check ZFS
if command -v zfs >/dev/null 2>&1; then
    echo "ZFS Status:"
    zpool status 2>/dev/null || echo "  No ZFS pools found"
    echo
fi

# Check LVM
if command -v lvs >/dev/null 2>&1; then
    echo "LVM Status:"
    vgs 2>/dev/null || echo "  No LVM volume groups found" 
    echo
fi

# Check disk space
echo "Disk Usage:"
df -h /var/lib/vz 2>/dev/null || echo "  Storage not mounted"
""")
        status_script.chmod(0o755)
        
        self.logger.info("Storage configuration created")