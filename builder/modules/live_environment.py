# Enhanced LiveEnvironment module with better error handling

"""
Live Environment Module (Enhanced)
Configures the live boot environment with robust package handling
"""

import subprocess
from pathlib import Path
from typing import Dict, Optional, List
import logging
from builder.core.lockfile import BuildLockfile

class LiveEnvironment:
    """Sets up live boot environment with enhanced error handling"""

    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"

    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[BuildLockfile] = None) -> Dict:
        """
        Configure live environment with enhanced error handling
        """
        self.logger.info("Configuring live environment...")

        try:
            # Fix repositories first
            self._fix_repositories()
            
            # Install live-boot packages with fallbacks
            self._install_live_packages_enhanced()

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
            self.logger.error(f"Live environment configuration failed: {e}")
            return {'status': 'error', 'error': str(e)}

    def _fix_repositories(self):
        """Fix repository configuration to resolve package availability"""
        self.logger.info("Fixing repository configuration...")
        
        # Create proper sources.list
        sources_content = """# Debian Trixie Main Sources
deb http://deb.debian.org/debian trixie main contrib non-free non-free-firmware
deb http://deb.debian.org/debian trixie-updates main contrib non-free non-free-firmware
deb http://security.debian.org/debian-security trixie-security main contrib non-free non-free-firmware

# Source packages (commented to save bandwidth)
# deb-src http://deb.debian.org/debian trixie main contrib non-free non-free-firmware
"""
        
        sources_list = self.chroot_path / "etc/apt/sources.list"
        with open(sources_list, 'w') as f:
            f.write(sources_content)
        
        # Create APT preferences
        preferences_content = """# Prefer trixie packages
Package: *
Pin: release n=trixie
Pin-Priority: 900

# Lower priority for security updates
Package: *
Pin: release n=trixie-security
Pin-Priority: 850

# Updates
Package: *
Pin: release n=trixie-updates
Pin-Priority: 800
"""
        
        preferences_file = self.chroot_path / "etc/apt/preferences.d/01-release-priorities"
        preferences_file.parent.mkdir(parents=True, exist_ok=True)
        with open(preferences_file, 'w') as f:
            f.write(preferences_content)
        
        # Update package lists
        self.logger.info("Updating package lists...")
        result = subprocess.run(
            ["chroot", str(self.chroot_path), "apt-get", "update"],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            self.logger.warning(f"Package list update had issues: {result.stderr}")

    def _get_package_sets(self) -> Dict[str, List[str]]:
        """Get categorized package lists with priorities"""
        return {
            'critical': [
                'systemd',
                'systemd-sysv', 
                'util-linux',
                'kmod',
                'udev',
                'e2fsprogs',
                'coreutils',
                'bash',
            ],
            'live_boot': [
                'live-boot',
                'live-config', 
                'live-config-systemd',
                'initramfs-tools',
            ],
            'networking': [
                'network-manager',
                'isc-dhcp-client',
                'iputils-ping',
                'wget',
                'curl',
            ],
            'bootloader': [
                'grub-common',
                'grub-pc-bin', 
                'grub-efi-amd64-bin',
                'efibootmgr',
                'syslinux',
                'isolinux',
            ],
            'filesystem': [
                'btrfs-progs',
                'xfsprogs', 
                'dosfstools',
                'cryptsetup',
                'lvm2',
            ],
            'hardware': [
                'pciutils',
                'usbutils',
                'firmware-linux-free',
                'nvme-cli',
            ],
        }

    def _install_live_packages_enhanced(self):
        """Install packages with enhanced error handling and fallbacks"""
        self.logger.info("Installing live environment packages...")
        
        package_sets = self._get_package_sets()
        installed_count = 0
        failed_count = 0
        
        # Install by category, most critical first
        for category, packages in package_sets.items():
            self.logger.info(f"Installing {category} packages ({len(packages)} packages)...")
            
            category_installed = 0
            for package in packages:
                if self._install_single_package(package):
                    category_installed += 1
                    installed_count += 1
                else:
                    failed_count += 1
            
            self.logger.info(f"{category}: {category_installed}/{len(packages)} installed")
        
        self.logger.info(f"Package installation summary: {installed_count} installed, {failed_count} failed")
        
        # Ensure we have minimum viable system
        if installed_count < 10:
            raise Exception(f"Too few packages installed ({installed_count}). System may not be viable.")

    def _install_single_package(self, package: str, timeout: int = 120) -> bool:
        """Install a single package with error handling"""
        try:
            # First try with --fix-missing
            result = subprocess.run(
                ["chroot", str(self.chroot_path), "apt-get", "install", "-y", "--fix-missing", "--no-install-recommends", package],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                self.logger.debug(f"✅ {package}")
                return True
            else:
                # If failed, try updating package lists and retry
                self.logger.debug(f"Retrying {package} after update...")
                subprocess.run(
                    ["chroot", str(self.chroot_path), "apt-get", "update"],
                    capture_output=True,
                    timeout=30
                )
                
                # Retry installation
                retry_result = subprocess.run(
                    ["chroot", str(self.chroot_path), "apt-get", "install", "-y", "--fix-missing", "--no-install-recommends", package],
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                
                if retry_result.returncode == 0:
                    self.logger.debug(f"✅ {package} (on retry)")
                    return True
                else:
                    self.logger.debug(f"❌ {package}: {retry_result.stderr.strip()}")
                    return False
                
        except subprocess.TimeoutExpired:
            self.logger.debug(f"⏱️ {package}: timeout")
            return False
        except Exception as e:
            self.logger.debug(f"❌ {package}: {e}")
            return False

    def _configure_live_system(self):
        """Configure live system settings"""
        self.logger.info("Configuring live system...")
        
        # Create live user
        try:
            subprocess.run(
                ["chroot", str(self.chroot_path), "useradd", "-m", "-s", "/bin/bash", "user"],
                check=False,  # Don't fail if user exists
                capture_output=True
            )
            
            # Add to sudo group
            subprocess.run(
                ["chroot", str(self.chroot_path), "usermod", "-a", "-G", "sudo", "user"],
                check=False,
                capture_output=True
            )
        except Exception as e:
            self.logger.warning(f"Could not create live user: {e}")

    def _setup_networking(self):
        """Setup basic networking"""
        self.logger.info("Setting up networking...")
        
        # Create basic network configuration
        interfaces_content = """# This file describes the network interfaces available on your system
# and how to activate them. For more information, see interfaces(5).

source /etc/network/interfaces.d/*

# The loopback network interface
auto lo
iface lo inet loopback

# Allow all network interfaces to be managed by NetworkManager
"""
        
        interfaces_file = self.chroot_path / "etc/network/interfaces"
        with open(interfaces_file, 'w') as f:
            f.write(interfaces_content)

    def _configure_services(self):
        """Configure systemd services"""
        self.logger.info("Configuring services...")
        
        # Enable essential services
        essential_services = [
            'systemd-networkd',
            'systemd-resolved',
            'systemd-timesyncd',
        ]
        
        for service in essential_services:
            try:
                subprocess.run(
                    ["chroot", str(self.chroot_path), "systemctl", "enable", service],
                    check=False,
                    capture_output=True
                )
            except Exception:
                pass  # Service might not exist

    def _generate_initramfs(self):
        """Generate initramfs"""
        self.logger.info("Generating initramfs...")
        
        try:
            # Try with dracut first (if available)
            result = subprocess.run(
                ["chroot", str(self.chroot_path), "which", "dracut"],
                capture_output=True
            )
            
            if result.returncode == 0:
                self.logger.info("Generating initramfs with dracut...")
                subprocess.run(
                    ["chroot", str(self.chroot_path), "dracut", "-f", "--regenerate-all"],
                    timeout=300,
                    check=False
                )
            else:
                # Fallback to update-initramfs
                self.logger.info("Generating initramfs with update-initramfs...")
                subprocess.run(
                    ["chroot", str(self.chroot_path), "update-initramfs", "-u"],
                    timeout=300,
                    check=False
                )
                
        except Exception as e:
            self.logger.warning(f"Initramfs generation had issues: {e}")
            # Not fatal - system might still boot