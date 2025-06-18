#!/usr/bin/env python3
# z-forge/builder/modules/debootstrap.py

"""
Debootstrap Module
Installs minimal Debian base into chroot with dracut
"""

import subprocess
import os
from pathlib import Path
from typing import Dict, Optional
import logging

class Debootstrap:
    """Handles Debian bootstrap into chroot"""
    
    def __init__(self, workspace: Path, config: Dict):
        """
        Initialize debootstrap module
        
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
        Bootstrap Debian into chroot
        
        Args:
            resume_data: Optional data for resuming partial execution
            
        Returns:
            Dict with debootstrap status and info
        """
        
        self.logger.info("Starting debootstrap...")
        
        try:
            # Get Debian release from config
            debian_release = self.config.get('builder_config', {}).get('debian_release', 'bookworm')
            
            # Check if bootstrap already completed
            if resume_data and resume_data.get('completed', False):
                self.logger.info("Debootstrap already completed, skipping")
                return {
                    'status': 'success',
                    'debian_release': debian_release,
                    'chroot_path': str(self.chroot_path),
                    'completed': True
                }
            
            # Run debootstrap
            self._run_debootstrap(debian_release)
            
            # Configure basic system
            self._configure_system(debian_release)
            
            # Install dracut (explicitly reinstall it)
            self._install_dracut()
            
            self.logger.info(f"Debootstrap completed: {debian_release}")
            
            return {
                'status': 'success',
                'debian_release': debian_release,
                'chroot_path': str(self.chroot_path),
                'completed': True
            }
            
        except Exception as e:
            self.logger.error(f"Debootstrap failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _run_debootstrap(self, debian_release: str):
        """Execute debootstrap to create minimal system"""
        
        self.logger.info(f"Running debootstrap for {debian_release}...")
        
        # Define install packages
        include_packages = [
            "locales",
            "linux-base",
            "sudo",
            "bash-completion",
            "apt-transport-https",
            "ca-certificates",
            "curl",
            "wget",
            "gnupg"
        ]
        
        # Run debootstrap command
        cmd = [
            "debootstrap",
            "--arch=amd64",
            f"--include={','.join(include_packages)}",
            debian_release,
            str(self.chroot_path),
            "http://deb.debian.org/debian"
        ]
        
        self.logger.info(f"Executing: {' '.join(cmd)}")
        
        subprocess.run(cmd, check=True)
    
    def _configure_system(self, debian_release: str):
        """Configure the basic system after bootstrap"""
        
        self.logger.info("Configuring basic system...")
        
        # Configure sources.list
        sources_list = f"""# Main Debian repositories
deb http://deb.debian.org/debian {debian_release} main contrib non-free non-free-firmware
deb http://deb.debian.org/debian {debian_release}-updates main contrib non-free non-free-firmware
deb http://security.debian.org/debian-security {debian_release}-security main contrib non-free non-free-firmware

# Backports
deb http://deb.debian.org/debian {debian_release}-backports main contrib non-free non-free-firmware
"""
        
        sources_path = self.chroot_path / "etc/apt/sources.list"
        with open(sources_path, 'w') as f:
            f.write(sources_list)
        
        # Configure hostname
        hostname_path = self.chroot_path / "etc/hostname"
        with open(hostname_path, 'w') as f:
            f.write("zforge\n")
        
        # Configure hosts
        hosts_content = """127.0.0.1   localhost
127.0.1.1   zforge

# The following lines are desirable for IPv6 capable hosts
::1     localhost ip6-localhost ip6-loopback
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
"""
        
        hosts_path = self.chroot_path / "etc/hosts"
        with open(hosts_path, 'w') as f:
            f.write(hosts_content)
        
        # Configure fstab
        fstab_content = """# /etc/fstab: static file system information.
# Use 'blkid' to print the universally unique identifier for a
# device; this may be used with UUID= as a more robust way to name devices
# that works even if disks are added and removed.

# <file system>  <mount point>  <type>  <options>  <dump>  <pass>
proc             /proc          proc    defaults   0       0
"""
        
        fstab_path = self.chroot_path / "etc/fstab"
        with open(fstab_path, 'w') as f:
            f.write(fstab_content)
        
        # Update packages
        self._run_chroot(["apt-get", "update"])
        self._run_chroot(["apt-get", "upgrade", "-y"])
        
        # Install essential packages
        self._run_chroot([
            "apt-get", "install", "-y",
            "build-essential", "python3", "python3-distutils", "vim",
            "nano", "less", "htop", "net-tools", "iproute2", "iputils-ping"
        ])
        
        # Generate locales
        self._run_chroot(["locale-gen", "en_US.UTF-8"])
        
        # Set timezone
        self._run_chroot(["ln", "-sf", "/usr/share/zoneinfo/UTC", "/etc/localtime"])
    
    def _install_dracut(self):
        """Install and configure dracut"""
        
        self.logger.info("Installing dracut...")
        
        # First ensure initramfs-tools is removed if present
        self._run_chroot(["apt-get", "remove", "-y", "initramfs-tools"], check=False)
        
        # Install dracut packages
        self._run_chroot([
            "apt-get", "install", "-y",
            "dracut",
            "dracut-core",
            "dracut-network",
            "dracut-squash"
        ])
        
        # Configure dracut
        dracut_conf = """# Z-Forge dracut configuration

# Compression method
compress="zstd"

# Include extra modules for ZFS support
add_dracutmodules+=" zfs "

# Include necessary filesystem modules
filesystems+=" zfs "

# Include systemd support
add_dracutmodules+=" systemd "

# Enable hostonly mode for better performance
hostonly="yes"

# Add kernel command line parameters
kernel_cmdline="root=zfs:AUTO"

# Include any additional drivers needed for NVMe
add_drivers+=" nvme "
"""
        
        dracut_conf_path = self.chroot_path / "etc/dracut.conf.d/zforge.conf"
        dracut_conf_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dracut_conf_path, 'w') as f:
            f.write(dracut_conf)
    
    def _run_chroot(self, command: list, check=True):
        """Run command in chroot environment"""
        
        cmd = ["chroot", str(self.chroot_path)] + command
        self.logger.info(f"Running in chroot: {' '.join(command)}")
        
        return subprocess.run(cmd, check=check)
