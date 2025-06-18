# z-forge/builder/modules/proxmox_integration.py

"""
Proxmox Integration Module
Prepares Proxmox VE repositories and packages for installation
"""

import subprocess
from pathlib import Path
from typing import Dict, Optional
import logging

class ProxmoxIntegration:
    """Handles Proxmox VE repository setup and package caching"""
    
    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def execute(self, resume_data: Optional[Dict] = None) -> Dict:
        """
        Configure Proxmox repositories and cache packages
        
        Returns:
            Dict with Proxmox setup status
        """
        
        self.logger.info("Starting Proxmox VE integration...")
        
        try:
            chroot_path = self.workspace / "chroot"
            
            # Add Proxmox repository keys
            self._add_repository_keys(chroot_path)
            
            # Configure Proxmox repositories
            self._setup_repositories(chroot_path)
            
            # Update package lists
            self._update_package_lists(chroot_path)
            
            # Cache Proxmox packages (but don't install)
            self._cache_packages(chroot_path)
            
            # Prepare installation scripts
            self._create_install_scripts(chroot_path)
            
            return {
                'status': 'success',
                'proxmox_version': '8.2',  # Latest stable
                'cached_packages': self._get_package_list()
            }
            
        except Exception as e:
            self.logger.error(f"Proxmox integration failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _add_repository_keys(self, chroot_path: Path):
        """Add Proxmox GPG keys"""
        
        # Download Proxmox release key
        key_url = "https://enterprise.proxmox.com/debian/proxmox-release-bookworm.gpg"
        key_path = chroot_path / "tmp/proxmox-release.gpg"
        
        subprocess.run([
            "wget", "-O", str(key_path), key_url
        ], check=True)
        
        # Import key
        subprocess.run([
            "chroot", str(chroot_path),
            "apt-key", "add", "/tmp/proxmox-release.gpg"
        ], check=True)
        
    def _setup_repositories(self, chroot_path: Path):
        """Configure Proxmox APT repositories"""
        
        # Create Proxmox sources list
        sources_content = """
# Proxmox VE No-Subscription Repository
deb http://download.proxmox.com/debian/pve bookworm pve-no-subscription

# Proxmox VE Test Repository (for latest packages)
# deb http://download.proxmox.com/debian/pve bookworm pvetest
"""
        
        sources_file = chroot_path / "etc/apt/sources.list.d/pve.list"
        sources_file.parent.mkdir(parents=True, exist_ok=True)
        sources_file.write_text(sources_content)
        
    def _cache_packages(self, chroot_path: Path):
        """Download but don't install Proxmox packages"""
        
        packages = self.config.get('proxmox_config', {}).get('include_packages', [
            'proxmox-ve',
            'pve-kernel-6.8',
            'pve-headers-6.8',
            'pve-firmware',
            'pve-manager',
            'pve-cluster',
            'pve-ha-manager',
            'lvm2',
            'thin-provisioning-tools',
            'bridge-utils',
            'numactl',
            'gdisk',
            'ksm-control-daemon'
        ])
        
        # Create package cache directory
        cache_dir = chroot_path / "var/cache/zforge/proxmox"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Download packages without installing
        download_cmd = f"""
        apt-get update
        apt-get download -o Dir::Cache::archives={cache_dir} {' '.join(packages)}
        """
        
        subprocess.run([
            "chroot", str(chroot_path),
            "bash", "-c", download_cmd
        ], check=True)
        
    def _create_install_scripts(self, chroot_path: Path):
        """Create Proxmox installation scripts for Calamares"""
        
        install_script = """#!/bin/bash
# Proxmox VE Installation Script
# To be executed by Calamares during target installation

set -e

echo "Installing Proxmox VE..."

# Configure network
cat > /etc/network/interfaces << EOF
auto lo
iface lo inet loopback

auto vmbr0
iface vmbr0 inet dhcp
    bridge-ports eth0
    bridge-stp off
    bridge-fd 0
EOF

# Install Proxmox packages from cache
cd /var/cache/zforge/proxmox
dpkg -i *.deb || apt-get -f install -y

# Configure Proxmox
pvecm create local-cluster || true

# Enable services
systemctl enable pve-cluster
systemctl enable pvedaemon
systemctl enable pveproxy
systemctl enable pvestatd

echo "Proxmox VE installation complete!"
"""
        
        script_path = chroot_path / "usr/share/zforge/scripts/install-proxmox.sh"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(install_script)
        script_path.chmod(0o755)
