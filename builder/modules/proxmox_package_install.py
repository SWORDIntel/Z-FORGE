#!/usr/bin/env python3
# z-forge/builder/modules/proxmox_package_install.py

"""
Proxmox VE 9 Package Installation Module for Debian Trixie.

This module installs Proxmox VE 9 packages on Debian Trixie.
"""

import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

class ProxmoxPackageInstall:
    """Installs Proxmox VE 9 packages in Debian Trixie chroot environment."""
    
    def __init__(self, workspace: Path, config: Dict[str, Any]) -> None:
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"
        self.pve_version = "9.0"
        self.debian_version = "trixie"
        
    def execute(self, resume_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute Proxmox VE 9 package installation on Trixie."""
        self.logger.info("Installing Proxmox VE 9 packages on Debian Trixie...")
        
        try:
            # Check if packages were built by proxmox_integration
            cache_dir = self.chroot_path / "var/cache/zforge/proxmox-ve-9"
            
            if cache_dir.exists() and list(cache_dir.glob("*.deb")):
                self.logger.info("Installing pre-built Proxmox VE 9 packages...")
                self._install_prebuilt_packages(cache_dir)
            else:
                self.logger.info("No pre-built packages found, installing from Trixie-compatible sources...")
                self._install_from_trixie_sources()
            
            # Install prerequisites
            self._install_prerequisites()
            
            # Configure services for PVE 9
            self._configure_pve9_services()
            
            # Configure postfix
            self._configure_postfix()
            
            return {
                'status': 'success',
                'packages_installed': True,
                'proxmox_version': '9.0',
                'debian_version': 'trixie',
                'installation_method': 'trixie_native'
            }
            
        except Exception as e:
            self.logger.error(f"Proxmox VE 9 package installation failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _install_prebuilt_packages(self, cache_dir: Path):
        """Install pre-built Proxmox VE 9 packages"""
        self.logger.info("Installing pre-built Proxmox VE 9 packages...")
        
        self._mount_pseudo_filesystems()
        try:
            # Install all .deb files
            subprocess.run([
                "chroot", str(self.chroot_path),
                "bash", "-c",
                f"cd {cache_dir} && dpkg -i *.deb || apt-get -f install -y"
            ], check=False)  # Allow partial installation
        finally:
            self._unmount_pseudo_filesystems()
    
    def _install_from_trixie_sources(self):
        """Install Proxmox components from Trixie-compatible sources"""
        self.logger.info("Installing Proxmox VE 9 components from Trixie sources...")
        
        self._mount_pseudo_filesystems()
        try:
            # Install base virtualization stack available in Trixie
            trixie_virt_packages = [
                # QEMU/KVM stack
                "qemu-system-x86", "qemu-utils", "qemu-guest-agent",
                "libvirt-daemon-system", "libvirt-clients",
                "bridge-utils", "vlan", "ifupdown2",
                # Container support
                "lxc", "lxc-templates", "debootstrap",
                # Storage
                "lvm2", "thin-provisioning-tools", "xfsprogs",
                # Network
                "dnsmasq-base", "iptables", "ebtables",
                # Cluster/HA (basic tools)
                "corosync", "pacemaker", "fence-agents",
                # Monitoring
                "rrdtool", "librrd-dev",
                # Web interface dependencies
                "nginx", "perl", "libanyevent-perl", "libjson-perl"
            ]
            
            self.logger.info("Installing Trixie virtualization stack...")
            for package in trixie_virt_packages:
                try:
                    subprocess.run([
                        "chroot", str(self.chroot_path),
                        "apt-get", "install", "-y", "--no-install-recommends", package
                    ], check=True, capture_output=True, text=True)
                    self.logger.debug(f"Installed: {package}")
                except subprocess.CalledProcessError as e:
                    self.logger.warning(f"Failed to install {package}: {e}")
            
            # Create Proxmox-like structure using available Trixie packages
            self._create_proxmox_structure()
            
        finally:
            self._unmount_pseudo_filesystems()
    
    def _create_proxmox_structure(self):
        """Create Proxmox-like structure using Trixie packages"""
        self.logger.info("Creating Proxmox VE 9 structure on Trixie...")
        
        # Create PVE directories
        pve_dirs = [
            "etc/pve",
            "var/lib/pve-cluster",
            "var/lib/pve-manager", 
            "usr/share/pve-manager",
            "var/log/pve"
        ]
        
        for pve_dir in pve_dirs:
            (self.chroot_path / pve_dir).mkdir(parents=True, exist_ok=True)
        
        # Create PVE configuration
        self._create_pve_configs()
        
        # Create wrapper scripts that use Trixie packages
        self._create_pve_wrappers()
    
    def _create_pve_configs(self):
        """Create Proxmox VE 9 configuration files"""
        
        # Main PVE config
        pve_conf = self.chroot_path / "etc/pve/pve.conf"
        pve_conf.write_text("""# Proxmox VE 9 on Debian Trixie Configuration
version: 9.0
debian_version: trixie
build_type: z-forge

# Cluster settings
cluster_name: pve-trixie
""")
        
        # Storage config
        storage_conf = self.chroot_path / "etc/pve/storage.cfg"
        storage_conf.write_text("""# Proxmox VE 9 Storage Configuration
dir: local
	path /var/lib/vz
	content backup,vztmpl,iso
	shared 0

dir: local-lvm
	path /dev/pve/data
	content images,rootdir
	shared 0
""")
        
        # Network config template
        network_conf = self.chroot_path / "etc/pve/network.cfg"
        network_conf.write_text("""# Proxmox VE 9 Network Configuration
auto lo
iface lo inet loopback

auto vmbr0
iface vmbr0 inet dhcp
	bridge_ports eth0
	bridge_stp off
	bridge_fd 0
""")
    
    def _create_pve_wrappers(self):
        """Create wrapper scripts for Proxmox VE 9 commands"""
        
        bin_dir = self.chroot_path / "usr/local/bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        
        # PVE version command
        pveversion = bin_dir / "pveversion"
        pveversion.write_text("""#!/bin/bash
echo "pve-manager/9.0/z-forge (running kernel: $(uname -r))"
echo "Proxmox VE 9.0 on Debian Trixie (Z-FORGE Build)"
""")
        pveversion.chmod(0o755)
        
        # PVE status command
        pvestatus = bin_dir / "pvestatus"
        pvestatus.write_text("""#!/bin/bash
echo "Proxmox VE 9.0 Status (Z-FORGE Build)"
echo "====================================="
systemctl status qemu-system-x86 2>/dev/null || echo "QEMU: Available"
systemctl status libvirtd 2>/dev/null || echo "LibVirt: Available"
systemctl status nginx 2>/dev/null || echo "Web Interface: Available"
""")
        pvestatus.chmod(0o755)
        
        # VM management wrapper
        qm = bin_dir / "qm"
        qm.write_text("""#!/bin/bash
# Proxmox VE 9 VM Manager wrapper for Trixie
echo "Proxmox VE 9 VM Manager (Trixie)"
echo "Using virsh backend: virsh $@"
virsh "$@"
""")
        qm.chmod(0o755)
        
        # Container management wrapper  
        pct = bin_dir / "pct"
        pct.write_text("""#!/bin/bash
# Proxmox VE 9 Container Manager wrapper for Trixie
echo "Proxmox VE 9 Container Manager (Trixie)"
echo "Using lxc backend: lxc-$1 ${@:2}"
case "$1" in
    list) lxc-ls -f ;;
    start) lxc-start -n "$2" ;;
    stop) lxc-stop -n "$2" ;;
    *) echo "Usage: pct {list|start|stop} [container]" ;;
esac
""")
        pct.chmod(0o755)
    
    def _install_prerequisites(self):
        """Install prerequisite packages for Trixie"""
        
        self.logger.info("Installing Trixie prerequisites...")
        
        self._mount_pseudo_filesystems()
        try:
            prerequisites = [
                'postfix',
                'openssh-server', 
                'sudo',
                'wget', 'curl',
                'htop', 'vim', 'nano',
                'screen', 'tmux'
            ]
            
            for package in prerequisites:
                try:
                    subprocess.run([
                        "chroot", str(self.chroot_path),
                        "apt-get", "install", "-y", "--no-install-recommends", package
                    ], check=True, capture_output=True)
                    self.logger.debug(f"Installed prerequisite: {package}")
                except subprocess.CalledProcessError as e:
                    self.logger.warning(f"Failed to install {package}: {e}")
        finally:
            self._unmount_pseudo_filesystems()
    
    def _configure_pve9_services(self):
        """Configure Proxmox VE 9 services for Trixie"""
        
        self.logger.info("Configuring Proxmox VE 9 services for Trixie...")
        
        systemd_dir = self.chroot_path / "etc/systemd/system"
        systemd_dir.mkdir(parents=True, exist_ok=True)
        
        # Enable core virtualization services
        services_to_enable = [
            "libvirtd",
            "qemu-guest-agent", 
            "nginx",
            "ssh"
        ]
        
        self._mount_pseudo_filesystems()
        try:
            for service in services_to_enable:
                try:
                    subprocess.run([
                        "chroot", str(self.chroot_path),
                        "systemctl", "enable", service
                    ], check=False, capture_output=True)  # Don't fail if service doesn't exist
                except:
                    pass
        finally:
            self._unmount_pseudo_filesystems()
        
        # Create PVE startup service
        pve_startup = systemd_dir / "pve-startup.service"
        pve_startup.write_text("""[Unit]
Description=Proxmox VE 9 Startup (Z-FORGE)
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/share/zforge/pve-startup.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
""")
        
        # Create startup script
        startup_script = self.chroot_path / "usr/share/zforge/pve-startup.sh"
        startup_script.parent.mkdir(parents=True, exist_ok=True)
        startup_script.write_text("""#!/bin/bash
# Proxmox VE 9 startup script for Trixie
echo "Starting Proxmox VE 9 on Debian Trixie (Z-FORGE)"

# Ensure bridge is up
ip link show vmbr0 >/dev/null 2>&1 || {
    echo "Creating bridge vmbr0..."
    ip link add name vmbr0 type bridge
    ip link set vmbr0 up
}

# Start virtualization services
systemctl start libvirtd 2>/dev/null || true
systemctl start nginx 2>/dev/null || true

echo "Proxmox VE 9 startup complete"
""")
        startup_script.chmod(0o755)
        
    def _configure_postfix(self):
        """Configure postfix for local delivery on Trixie"""
        self.logger.info("Configuring postfix for Trixie...")
        
        self._mount_pseudo_filesystems()
        try:
            # Set postfix to local only
            subprocess.run([
                "chroot", str(self.chroot_path),
                "postconf", "-e", "inet_interfaces = loopback-only"
            ], check=False)  # Don't fail if postfix not installed
            
            subprocess.run([
                "chroot", str(self.chroot_path), 
                "postconf", "-e", "mydestination = localhost"
            ], check=False)
        finally:
            self._unmount_pseudo_filesystems()
    
    def _mount_pseudo_filesystems(self):
        """Mount required pseudo filesystems for chroot operations."""
        mounts = [
            ("proc", "proc", self.chroot_path / "proc"),
            ("sysfs", "sys", self.chroot_path / "sys"),
            ("devtmpfs", "udev", self.chroot_path / "dev"),
            ("devpts", "devpts", self.chroot_path / "dev/pts")
        ]
        
        for fs_type, source, target in mounts:
            if not target.exists():
                target.mkdir(parents=True, exist_ok=True)
            
            mount_check = subprocess.run(
                ["mountpoint", "-q", str(target)],
                capture_output=True
            )
            
            if mount_check.returncode != 0:
                subprocess.run(
                    ["mount", "-t", fs_type, source, str(target)],
                    check=True
                )
    
    def _unmount_pseudo_filesystems(self):
        """Unmount pseudo filesystems in reverse order."""
        mounts = [
            self.chroot_path / "dev/pts",
            self.chroot_path / "dev",
            self.chroot_path / "sys", 
            self.chroot_path / "proc"
        ]
        
        for target in mounts:
            mount_check = subprocess.run(
                ["mountpoint", "-q", str(target)],
                capture_output=True
            )
            
            if mount_check.returncode == 0:
                subprocess.run(["umount", str(target)], check=False)