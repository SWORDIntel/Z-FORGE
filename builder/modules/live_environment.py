# z-forge/builder/modules/live_environment.py

"""
Live Environment Module
Configures the live boot environment and initramfs
"""

import subprocess
from pathlib import Path
from typing import Dict, Optional
import logging
from builder.core.lockfile import BuildLockfile

class LiveEnvironment:
    """Sets up live boot environment"""

    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"

    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[BuildLockfile] = None) -> Dict:
        """
        Configure live environment

        Returns:
            Dict with configuration status
        """

        self.logger.info("Configuring live environment...")

        try:
            # Install live-boot packages
            self._install_live_packages()

            # Configure live system
            self._configure_live_system()

            # Setup networking
            self._setup_networking()

            # Configure services
            self._configure_services()

            # Generate initramfs
            self._generate_initramfs()

            return {'status': 'success'}

        except Exception as e:
            self.logger.error(f"Live environment setup failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }

    def _install_live_packages(self):
        """Install packages needed for live boot"""

        packages = [
            'live-boot',
            'live-boot-initramfs-tools',
            'live-config',
            'live-config-systemd',
            'systemd-sysv',
            'network-manager',
            'firmware-linux-free',
            'firmware-linux-nonfree',
            'firmware-misc-nonfree',
            'dbus',
            'pciutils',
            'usbutils',
            'discover',
            'laptop-detect',
            'os-prober',
            'efibootmgr',
            'grub-pc-bin',
            'grub-efi-amd64-bin',
            'memtest86+',
            'rsync',
            'cryptsetup',
            'lvm2',
            'mdadm',
            'kde-standard',  # Added KDE standard packages
            'sddm',          # Added SDDM display manager
            # Essential system utilities for dracut
            'btrfs-progs',   # Btrfs filesystem support
            'xfsprogs',      # XFS filesystem support
            'e2fsprogs',     # ext2/3/4 filesystem utilities
            'kbd',           # Keyboard utilities (loadkeys, setfont)
            'systemd-timesyncd',  # Time synchronization
            'systemd-resolved',   # DNS resolution
            'systemd-boot',       # systemd-boot and systemd-repart
            'systemd-container',  # systemd-portabled
            'nvme-cli',           # NVMe utilities
            'jq',                 # JSON processor (for nvmf)
            'open-iscsi',         # iSCSI support
            'nfs-common',         # NFS support
            'cifs-utils',         # SMB/CIFS support
            'nbd-client',         # Network Block Device support
            'multipath-tools',    # Multipath I/O
            'tpm2-tools',         # TPM 2.0 support
            'pcsc-lite',          # Smart card support
            'rng-tools',          # Hardware RNG daemon
            'util-linux',         # Various system utilities
            'isc-dhcp-client',    # DHCP client for network-legacy
            'dmraid',             # Device-mapper RAID support
            'kmod',               # Kernel module utilities
            'dbus-broker',        # High-performance D-Bus message broker
            'systemd-coredump',   # Core dump management
            'biosdevname',        # Consistent network device naming
            'fcoe-utils',         # Fibre Channel over Ethernet
            'lldpad',             # Link Layer Discovery Protocol daemon
            'erofs-utils'         # Enhanced Read-Only File System tools
        ]

        # Install packages in batches to handle potential failures
        self.logger.info(f"Installing {len(packages)} packages for live environment...")
        
        # First try to install all packages
        install_cmd = f"apt-get install -y --no-install-recommends {' '.join(packages)}"
        
        result = subprocess.run(
            ["chroot", str(self.chroot_path), "bash", "-c", install_cmd],
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes for package installation
        )
        
        if result.returncode != 0:
            # If it fails, try installing packages one by one to identify which ones are missing
            self.logger.warning("Batch installation failed, trying individual packages...")
            failed_packages = []
            
            for package in packages:
                try:
                    subprocess.run(
                        ["chroot", str(self.chroot_path), "apt-get", "install", "-y", "--no-install-recommends", package],
                        check=True,
                        capture_output=True,
                        timeout=60
                    )
                    self.logger.debug(f"Successfully installed: {package}")
                except subprocess.CalledProcessError:
                    self.logger.warning(f"Failed to install: {package}")
                    failed_packages.append(package)
            
            if failed_packages:
                self.logger.warning(f"Could not install {len(failed_packages)} packages: {', '.join(failed_packages)}")
                self.logger.info("Continuing with available packages...")
        else:
            self.logger.info("All packages installed successfully")

    def _configure_live_system(self):
        """Configure live system settings"""

        # Create live system configuration
        live_config = """# Z-Forge Live Configuration

# Hostname
LIVE_HOSTNAME="zforge-live"

# User configuration
LIVE_USERNAME="root"
LIVE_USER_FULLNAME="Z-Forge Live User"
LIVE_USER_DEFAULT_GROUPS="audio cdrom dip floppy video plugdev netdev powerdev scanner bluetooth debian-tor"

# System configuration
LIVE_LOCALES="en_US.UTF-8"
LIVE_TIMEZONE="UTC"
LIVE_KEYBOARD_MODEL="pc105"
LIVE_KEYBOARD_LAYOUTS="us"

# Boot parameters
LIVE_BOOT_APPEND="quiet splash"
"""

        config_path = self.chroot_path / "etc/live/config.conf"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(live_config)

        # Create hooks for live boot
        hooks_dir = self.chroot_path / "lib/live/config"
        hooks_dir.mkdir(parents=True, exist_ok=True)

        # Custom hook to start installer
        installer_hook = """#!/bin/bash
# Z-Forge installer auto-start hook

if [ -e /proc/cmdline ] && grep -q "zforge.autoinstall" /proc/cmdline; then
    # Auto-start installer
    systemctl start lightdm
fi
"""

        hook_path = hooks_dir / "9999-zforge-installer"
        hook_path.write_text(installer_hook)
        hook_path.chmod(0o755)

    def _setup_networking(self):
        """Configure network for live environment"""

        # NetworkManager configuration
        nm_config = """[main]
plugins=ifupdown,keyfile
dhcp=dhclient

[ifupdown]
managed=false

[keyfile]
unmanaged-devices=interface-name:wlp*,interface-name:eth*
"""

        nm_path = self.chroot_path / "etc/NetworkManager/NetworkManager.conf"
        nm_path.parent.mkdir(parents=True, exist_ok=True)
        nm_path.write_text(nm_config)

        # Basic network interfaces
        interfaces = """# Network interfaces configuration
auto lo
iface lo inet loopback

# Allow NetworkManager to manage other interfaces
"""

        interfaces_path = self.chroot_path / "etc/network/interfaces"
        interfaces_path.write_text(interfaces)

    def _configure_services(self):
        """Configure systemd services for live boot"""

        # Enable necessary services
        services_to_enable = [
            'NetworkManager',
            'ssh',  # For remote debugging
            'sddm'  # Changed lightdm to sddm
        ]

        for service in services_to_enable:
            subprocess.run(
                ["chroot", self.chroot_path, "systemctl", "enable", service],
                capture_output=True
            )

        # Disable unnecessary services
        services_to_disable = [
            'apt-daily',
            'apt-daily-upgrade'
        ]

        for service in services_to_disable:
            subprocess.run(
                ["chroot", self.chroot_path, "systemctl", "disable", service],
                capture_output=True
            )

        # Create custom installer service
        # installer_service = """[Unit]
# Description=Z-Forge Installer
# After=graphical.target
#
# [Service]
# Type=oneshot
# ExecStart=/usr/bin/calamares
# RemainAfterExit=yes
#
# [Install]
# WantedBy=graphical.target
# """
        # service_path = self.chroot_path / "etc/systemd/system/zforge-installer.service"
        # service_path.write_text(installer_service)
        # Ensure the service file is removed if it exists from previous versions
        service_path = self.chroot_path / "etc/systemd/system/zforge-installer.service"
        if service_path.exists():
            service_path.unlink()
            self.logger.info(f"Removed existing service file: {service_path}")


    def _generate_initramfs(self):
        """Generate initramfs for live boot"""

        self.logger.info("Generating initramfs...")

        # Update initramfs - use dracut if available, otherwise update-initramfs
        try:
            # Check if dracut is available
            subprocess.run(
                ["chroot", self.chroot_path, "which", "dracut"],
                check=True,
                capture_output=True
            )
            # Use dracut
            subprocess.run(
                ["chroot", self.chroot_path, "dracut", "-f", "--regenerate-all"],
                check=True
            )
        except subprocess.CalledProcessError:
            # Fall back to update-initramfs
            subprocess.run(
                ["chroot", self.chroot_path, "update-initramfs", "-u", "-k", "all"],
                check=True
            )
