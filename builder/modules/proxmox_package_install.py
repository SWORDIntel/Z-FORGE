#!/usr/bin/env python3
# z-forge/builder/modules/proxmox_package_install.py

"""
Proxmox VE Package Installation Module for Z-Forge.

This module installs Proxmox VE packages and dependencies.
"""

import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

class ProxmoxPackageInstall:
    """Installs Proxmox VE packages in the chroot environment."""
    
    def __init__(self, workspace: Path, config: Dict[str, Any]) -> None:
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"
        
    def execute(self, resume_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute Proxmox package installation."""
        self.logger.info("Installing Proxmox VE packages...")
        
        try:
            # Install prerequisites
            self._install_prerequisites()
            
            # Install Proxmox VE
            self._install_proxmox_ve()
            
            # Configure postfix
            self._configure_postfix()
            
            return {
                'status': 'success',
                'packages_installed': True,
                'proxmox_version': self._get_proxmox_version()
            }
            
        except Exception as e:
            self.logger.error(f"Package installation failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
            
    def _install_prerequisites(self):
        """Install prerequisite packages"""
        prerequisites = [
            'postfix',
            'bridge-utils',
            'ifupdown2',
            'openssh-server',
            'xfsprogs',
            'thin-provisioning-tools',
            'lvm2'
        ]
        
        self.logger.info("Installing prerequisites...")
        subprocess.run([
            "chroot", str(self.chroot_path),
            "apt-get", "install", "-y"
        ] + prerequisites, check=True)
        
    def _install_proxmox_ve(self):
        """Install Proxmox VE packages"""
        # First install the kernel
        self.logger.info("Installing Proxmox kernel...")
        subprocess.run([
            "chroot", str(self.chroot_path),
            "apt-get", "install", "-y", "pve-kernel-6.8"
        ], check=True)
        
        # Then install Proxmox VE
        self.logger.info("Installing Proxmox VE...")
        subprocess.run([
            "chroot", str(self.chroot_path),
            "apt-get", "install", "-y", "proxmox-ve"
        ], check=True)
        
    def _configure_postfix(self):
        """Configure postfix for local delivery"""
        self.logger.info("Configuring postfix...")
        # Set postfix to local only
        subprocess.run([
            "chroot", str(self.chroot_path),
            "postconf", "-e", "inet_interfaces = loopback-only"
        ], check=True)
        
    def _get_proxmox_version(self) -> str:
        """Get installed Proxmox version"""
        try:
            result = subprocess.run([
                "chroot", str(self.chroot_path),
                "pveversion"
            ], capture_output=True, text=True)
            return result.stdout.strip()
        except:
            return "unknown"
