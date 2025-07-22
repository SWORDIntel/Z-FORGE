# z-forge/builder/modules/proxmox_integration.py

"""
Proxmox Integration Module
Prepares Proxmox VE repositories and packages for installation
"""

import subprocess
from pathlib import Path
from typing import Dict, Optional
import logging
import os
from builder.core.lockfile import BuildLockfile

class ProxmoxIntegration:
    """Handles Proxmox VE repository setup and package caching"""
    
    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.proxmox_config = config.get('proxmox_config', {})
        self.build_from_source = self.proxmox_config.get('build_from_source', False)
        self.use_beta_iso = self.proxmox_config.get('use_beta_iso', False)
        
    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[BuildLockfile] = None) -> Dict:
        """
        Configure Proxmox repositories and cache packages
        
        Returns:
            Dict with Proxmox setup status
        """
        
        self.logger.info("Starting Proxmox VE integration...")
        
        try:
            chroot_path = self.workspace / "chroot"
            
            if self.build_from_source:
                # Build Proxmox from source
                self.logger.info("Building Proxmox VE from source...")
                self._build_from_source(chroot_path)
            elif self.use_beta_iso:
                # Extract packages from Proxmox VE 9.0 BETA ISO
                self.logger.info("Using Proxmox VE 9.0 BETA ISO as base...")
                self._extract_from_iso(chroot_path)
            else:
                # Standard APT repository approach
                self.logger.info("Using Proxmox APT repositories...")
                
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
        
        # Import key (requires mounted filesystems)
        self._mount_pseudo_filesystems(chroot_path)
        try:
            subprocess.run([
                "chroot", str(chroot_path),
                "apt-key", "add", "/tmp/proxmox-release.gpg"
            ], check=True)
        finally:
            self._unmount_pseudo_filesystems(chroot_path)
        
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
        
        # Download packages without installing (requires mounted filesystems)
        download_cmd = f"""
        apt-get update
        apt-get download -o Dir::Cache::archives={cache_dir} {' '.join(packages)}
        """
        
        self._mount_pseudo_filesystems(chroot_path)
        try:
            subprocess.run([
                "chroot", str(chroot_path),
                "bash", "-c", download_cmd
            ], check=True)
        finally:
            self._unmount_pseudo_filesystems(chroot_path)
        
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
    
    def _build_from_source(self, chroot_path: Path):
        """Build Proxmox VE from source repositories"""
        
        # Create build directory
        build_dir = self.workspace / "proxmox-build"
        build_dir.mkdir(exist_ok=True)
        
        # List of core Proxmox repositories to clone
        repos = [
            "pve-common",
            "pve-access-control", 
            "pve-storage",
            "pve-cluster",
            "pve-manager",
            "pve-kernel",
            "pve-qemu",
            "pve-container",
            "pve-firewall",
            "pve-ha-manager",
            "proxmox-backup",
            "proxmox-widget-toolkit"
        ]
        
        # Clone repositories
        for repo in repos:
            repo_url = f"git://git.proxmox.com/{repo}.git"
            repo_path = build_dir / repo
            
            if not repo_path.exists():
                self.logger.info(f"Cloning {repo}...")
                subprocess.run([
                    "git", "clone", repo_url, str(repo_path)
                ], check=True)
        
        # Install build dependencies in chroot
        build_deps = [
            "build-essential",
            "debhelper",
            "dh-systemd",
            "libpve-common-perl",
            "libpve-access-control",
            "libpve-storage-perl",
            "libpve-http-server-perl",
            "libjson-perl",
            "libanyevent-perl",
            "libio-multiplex-perl",
            "libnet-ssleay-perl",
            "libcrypt-ssleay-perl",
            "liblwp-protocol-https-perl",
            "libfilesys-df-perl",
            "libfile-readbackwards-perl",
            "libfile-sync-perl",
            "libnet-ldap-perl",
            "libauthen-pam-perl",
            "libtterm-readline-perl",
            "libterm-readline-gnu-perl",
            "libnet-dns-perl",
            "libnet-ip-perl",
            "libdigest-hmac-perl",
            "libhtml-parser-perl",
            "libxml-libxml-perl",
            "libjson-xs-perl",
            "libdbi-perl",
            "libdbd-sqlite3-perl",
            "libcrypt-openssl-rsa-perl",
            "libcrypt-openssl-random-perl",
            "libuuid-perl",
            "libmime-base32-perl",
            "liburi-perl",
            "libwww-perl"
        ]
        
        self.logger.info("Installing build dependencies...")
        self._mount_pseudo_filesystems(chroot_path)
        try:
            subprocess.run([
                "chroot", str(chroot_path),
                "apt-get", "install", "-y"
            ] + build_deps, check=True)
        finally:
            self._unmount_pseudo_filesystems(chroot_path)
        
        # Build each component
        for repo in repos:
            repo_path = build_dir / repo
            if (repo_path / "Makefile").exists():
                self.logger.info(f"Building {repo}...")
                
                # Copy to chroot for building
                chroot_build_path = chroot_path / f"usr/src/{repo}"
                subprocess.run([
                    "cp", "-r", str(repo_path), str(chroot_build_path)
                ], check=True)
                
                # Build in chroot
                subprocess.run([
                    "chroot", str(chroot_path),
                    "bash", "-c", f"cd /usr/src/{repo} && make deb"
                ], check=True)
                
                # Copy built packages to cache
                cache_dir = chroot_path / "var/cache/zforge/proxmox"
                cache_dir.mkdir(parents=True, exist_ok=True)
                
                subprocess.run([
                    "bash", "-c",
                    f"cp {chroot_path}/usr/src/{repo}/*.deb {cache_dir}/"
                ], check=True)
    
    def _extract_from_iso(self, chroot_path: Path):
        """Extract packages from Proxmox VE 9.0 BETA ISO"""
        
        iso_url = "https://enterprise.proxmox.com/iso/proxmox-ve_9.0-BETA-1.iso"
        iso_path = self.workspace / "proxmox-ve-9.0-beta.iso"
        
        # Download ISO if not present
        if not iso_path.exists():
            self.logger.info("Downloading Proxmox VE 9.0 BETA ISO...")
            subprocess.run([
                "wget", "-O", str(iso_path), iso_url
            ], check=True)
        
        # Mount ISO
        mount_point = self.workspace / "iso-mount"
        mount_point.mkdir(exist_ok=True)
        
        subprocess.run([
            "mount", "-o", "loop", str(iso_path), str(mount_point)
        ], check=True)
        
        try:
            # Extract packages from ISO
            packages_dir = mount_point / "proxmox/packages"
            if packages_dir.exists():
                cache_dir = chroot_path / "var/cache/zforge/proxmox"
                cache_dir.mkdir(parents=True, exist_ok=True)
                
                self.logger.info("Copying packages from ISO...")
                subprocess.run([
                    "cp", "-r", f"{packages_dir}/*.deb", str(cache_dir)
                ], check=True)
            
            # Also extract any configuration templates
            templates_dir = mount_point / "proxmox/templates"
            if templates_dir.exists():
                config_dir = chroot_path / "usr/share/zforge/proxmox-config"
                config_dir.mkdir(parents=True, exist_ok=True)
                
                subprocess.run([
                    "cp", "-r", str(templates_dir), str(config_dir)
                ], check=True)
                
        finally:
            # Always unmount
            subprocess.run(["umount", str(mount_point)], check=False)
    
    def _mount_pseudo_filesystems(self, chroot_path: Path):
        """Mount required pseudo filesystems for chroot operations."""
        mounts = [
            ("proc", "proc", chroot_path / "proc"),
            ("sysfs", "sys", chroot_path / "sys"),
            ("devtmpfs", "udev", chroot_path / "dev"),
            ("devpts", "devpts", chroot_path / "dev/pts")
        ]
        
        for fs_type, source, target in mounts:
            if not target.exists():
                target.mkdir(parents=True, exist_ok=True)
            
            # Check if already mounted
            mount_check = subprocess.run(
                ["mountpoint", "-q", str(target)],
                capture_output=True
            )
            
            if mount_check.returncode != 0:
                self.logger.debug(f"Mounting {source} to {target}")
                subprocess.run(
                    ["mount", "-t", fs_type, source, str(target)],
                    check=True
                )
    
    def _unmount_pseudo_filesystems(self, chroot_path: Path):
        """Unmount pseudo filesystems in reverse order."""
        mounts = [
            chroot_path / "dev/pts",
            chroot_path / "dev",
            chroot_path / "sys",
            chroot_path / "proc"
        ]
        
        for target in mounts:
            mount_check = subprocess.run(
                ["mountpoint", "-q", str(target)],
                capture_output=True
            )
            
            if mount_check.returncode == 0:
                self.logger.debug(f"Unmounting {target}")
                subprocess.run(["umount", str(target)], check=False)
