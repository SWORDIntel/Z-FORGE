#!/usr/bin/env python3
# z-forge/builder/modules/proxmox_repo_setup.py

"""
Proxmox VE Repository Setup Module for Z-Forge.

This module configures Proxmox VE repositories and installs the repository key.
"""

import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional

class ProxmoxRepoSetup:
    """Sets up Proxmox VE repositories in the chroot environment."""
    
    def __init__(self, workspace: Path, config: Dict[str, Any]) -> None:
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"
        
    def execute(self, resume_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute Proxmox repository setup."""
        self.logger.info("Setting up Proxmox VE repositories...")
        
        try:
            # Add Proxmox repository key
            self._add_repository_key()
            
            # Configure repositories
            self._configure_repositories()
            
            # Update package lists
            self._update_package_lists()
            
            return {
                'status': 'success',
                'repositories_configured': True,
                'repository_type': self.config.get('proxmox_config', {}).get('repository', 'no-subscription')
            }
            
        except Exception as e:
            self.logger.error(f"Repository setup failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
            
    def _add_repository_key(self):
        """Add Proxmox repository key"""
        # Use Trixie repository for Proxmox VE 9.0 compatibility
        key_url = "https://enterprise.proxmox.com/debian/proxmox-release-trixie.gpg"
        key_path = self.chroot_path / "etc/apt/trusted.gpg.d/proxmox-release-trixie.gpg"
        
        self.logger.info("Downloading Proxmox repository key...")
        subprocess.run([
            "wget", "-O", str(key_path), key_url
        ], check=True)
        
    def _configure_repositories(self):
        """Configure Proxmox repositories"""
        repo_type = self.config.get('proxmox_config', {}).get('repository', 'no-subscription')
        
        sources_list = self.chroot_path / "etc/apt/sources.list.d/pve.list"
        
        # Updated for Proxmox VE 9.0 on Debian Trixie
        if repo_type == 'enterprise':
            repo_line = "deb https://enterprise.proxmox.com/debian/pve trixie pve-enterprise\n"
        elif repo_type == 'test':
            repo_line = "deb http://download.proxmox.com/debian/pve trixie pvetest\n"
        else:  # no-subscription
            repo_line = "deb http://download.proxmox.com/debian/pve trixie pve-no-subscription\n"
            
        with open(sources_list, 'w') as f:
            f.write(repo_line)
            
        self.logger.info(f"Configured {repo_type} repository")
        
    def _update_package_lists(self):
        """Update package lists"""
        self.logger.info("Updating package lists...")
        subprocess.run([
            "chroot", str(self.chroot_path),
            "apt-get", "update"
        ], check=True)
