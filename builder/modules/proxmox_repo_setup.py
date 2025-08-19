#!/usr/bin/env python3
# z-forge/builder/modules/proxmox_repo_setup.py

"""
Proxmox VE 9 Repository Setup Module for Debian Trixie.
Sets up repositories for Proxmox VE 9 on Debian Trixie.
"""

import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional

class ProxmoxRepoSetup:
    """Sets up Proxmox VE 9 repositories for Debian Trixie."""
    
    def __init__(self, workspace: Path, config: Dict[str, Any]) -> None:
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"
        self.pve_version = "9.0"
        self.debian_version = "trixie"
        
    def execute(self, resume_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute Proxmox VE 9 repository setup for Trixie."""
        self.logger.info("Setting up Proxmox VE 9 repositories for Debian Trixie...")
        
        try:
            # Since Proxmox doesn't have official Trixie repos,
            # we'll set up source-based repos and Trixie compatibility
            self._setup_trixie_repos()
            self._setup_pve9_sources()
            self._configure_apt_preferences()
            
            return {
                'status': 'success',
                'repositories_configured': True,
                'proxmox_version': '9.0',
                'debian_version': 'trixie',
                'repo_type': 'trixie_compatible'
            }
            
        except Exception as e:
            self.logger.error(f"Proxmox VE 9 repository setup failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _setup_trixie_repos(self):
        """Setup Debian Trixie repositories"""
        self.logger.info("Configuring Debian Trixie repositories...")
        
        # Ensure Trixie main repos are properly configured
        sources_list = self.chroot_path / "etc/apt/sources.list"
        sources_content = """# Debian Trixie repositories
deb http://deb.debian.org/debian trixie main contrib non-free non-free-firmware
deb-src http://deb.debian.org/debian trixie main contrib non-free non-free-firmware

deb http://deb.debian.org/debian-security trixie-security main contrib non-free non-free-firmware
deb-src http://deb.debian.org/debian-security trixie-security main contrib non-free non-free-firmware

# Trixie Updates
deb http://deb.debian.org/debian trixie-updates main contrib non-free non-free-firmware
deb-src http://deb.debian.org/debian trixie-updates main contrib non-free non-free-firmware
"""
        sources_list.write_text(sources_content)
        
    def _setup_pve9_sources(self):
        """Setup Proxmox VE 9 source repositories"""
        self.logger.info("Setting up Proxmox VE 9 source repositories...")
        
        # Add Proxmox source repos (for building from source)
        pve_sources = self.chroot_path / "etc/apt/sources.list.d/pve-sources.list"
        pve_sources.parent.mkdir(parents=True, exist_ok=True)
        
        sources_content = """# Proxmox VE 9 Source Repositories for Trixie Build
# These are used for building Proxmox from source on Trixie
deb-src http://download.proxmox.com/debian/pve bookworm pve-no-subscription

# Additional virtualization repos compatible with Trixie
deb http://deb.debian.org/debian trixie main contrib
"""
        pve_sources.write_text(sources_content)
        
        # Add repository keys
        self._add_repository_keys()
    
    def _add_repository_keys(self):
        """Add Proxmox repository keys"""
        self.logger.info("Adding Proxmox repository keys...")
        
        trusted_dir = self.chroot_path / "etc/apt/trusted.gpg.d"
        trusted_dir.mkdir(parents=True, exist_ok=True)
        
        # Download Proxmox GPG key
        try:
            subprocess.run([
                "wget", "-O", str(trusted_dir / "proxmox-release.gpg"),
                "https://enterprise.proxmox.com/debian/proxmox-release-bookworm.gpg"
            ], check=True, timeout=60)
            
            # Set proper permissions
            (trusted_dir / "proxmox-release.gpg").chmod(0o644)
            self.logger.info("Proxmox GPG key installed")
            
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to download Proxmox GPG key: {e}")
    
    def _configure_apt_preferences(self):
        """Configure APT preferences for Trixie/PVE 9 compatibility"""
        self.logger.info("Configuring APT preferences for Trixie/PVE 9...")
        
        preferences_dir = self.chroot_path / "etc/apt/preferences.d"
        preferences_dir.mkdir(parents=True, exist_ok=True)
        
        # Prefer Trixie packages over everything
        trixie_prefs = preferences_dir / "00-trixie-priority"
        trixie_prefs.write_text("""# Prefer Trixie packages
Package: *
Pin: release n=trixie
Pin-Priority: 1000

# Lower priority for Proxmox source packages
Package: *
Pin: release o=Proxmox
Pin-Priority: 100
""")
        
        # Create PVE 9 specific preferences
        pve_prefs = preferences_dir / "50-proxmox-ve-9"
        pve_prefs.write_text("""# Proxmox VE 9 on Trixie preferences
# Prefer virtualization packages from Trixie
Package: qemu-* libvirt-* lxc-* kvm-*
Pin: release n=trixie
Pin-Priority: 1200

# Use Trixie kernel packages
Package: linux-image-* linux-headers-*
Pin: release n=trixie
Pin-Priority: 1100
""")
        
        self.logger.info("APT preferences configured for Trixie/PVE 9")