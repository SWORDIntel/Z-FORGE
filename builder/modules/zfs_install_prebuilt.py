"""
ZFS Install Prebuilt Module

Installs prebuilt ZFS packages in chroot
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import logging


class ZfsInstallPrebuilt:
    """Install prebuilt ZFS packages"""
    
    def __init__(self, workspace: Path, config: Dict[str, Any]):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"
        self.packages_dir = self.config.get('packages_dir', 'prebuilt_packages/zfs')
        
    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[Any] = None) -> Dict:
        """Install ZFS packages in chroot"""
        try:
            self.logger.info("Installing prebuilt ZFS packages...")
            
            # Check if packages exist
            # packages_dir is relative to chroot
            chroot_pkg_path = self.chroot_path / self.packages_dir
            
            if not chroot_pkg_path.exists():
                self.logger.error(f"Package directory not found in chroot: {chroot_pkg_path}")
                return {
                    'status': 'error',
                    'error': f'Package directory not found: {chroot_pkg_path}',
                    'module': self.__class__.__name__
                }
                
            # Count packages
            pkg_count = len(list(chroot_pkg_path.glob("*.deb")))
            self.logger.info(f"Found {pkg_count} ZFS packages to install")
            
            if pkg_count == 0:
                self.logger.error("No ZFS packages found")
                return {
                    'status': 'error',
                    'error': 'No ZFS packages found',
                    'module': self.__class__.__name__
                }
                
            # Install packages
            install_cmd = f"""
                cd {self.packages_dir}
                # Install ZFS packages in correct order
                dpkg -i libnvpair*.deb libuutil*.deb libzfs*.deb libzpool*.deb || true
                dpkg -i zfs-dkms*.deb || true
                dpkg -i zfs-initramfs*.deb zfs-zed*.deb zfsutils-linux*.deb || true
                # Fix dependencies
                apt-get -f install -y
            """
            
            result = self._run_in_chroot(install_cmd)
            if not result:
                self.logger.error("Failed to install ZFS packages")
                return {
                    'status': 'error',
                    'error': 'Failed to install ZFS packages',
                    'module': self.__class__.__name__
                }
                
            # Verify installation
            verify_cmd = "dpkg -l | grep -E '^ii.*zfs' | wc -l"
            output = self._run_in_chroot_output(verify_cmd)
            
            if output and int(output.strip()) > 0:
                self.logger.info(f"Successfully installed {output.strip()} ZFS packages")
                
                # Load ZFS module
                self.logger.info("Loading ZFS kernel module...")
                self._run_in_chroot("modprobe zfs || true")
                
                # Enable ZFS services
                self.logger.info("Enabling ZFS services...")
                services = ['zfs-import-cache', 'zfs-mount', 'zfs-share', 'zfs-zed']
                enabled_services = 0
                for service in services:
                    if self._run_in_chroot(f"systemctl enable {service} || true"):
                        enabled_services += 1
                    
                return {
                    'status': 'success',
                    'packages_installed': int(output.strip()),
                    'total_packages': pkg_count,
                    'services_enabled': enabled_services
                }
            else:
                self.logger.error("ZFS packages not properly installed")
                return {
                    'status': 'error',
                    'error': 'ZFS packages not properly installed',
                    'module': self.__class__.__name__
                }
                
        except Exception as e:
            self.logger.error(f"Failed to install ZFS packages: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
            
    def _run_in_chroot(self, command: str) -> bool:
        """Run command in chroot environment"""
        try:
            full_cmd = f"chroot {self.chroot_path} /bin/bash -c '{command}'"
            result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.warning(f"Command failed: {command}")
                return False
            return True
        except Exception as e:
            self.logger.error(f"Failed to run command in chroot: {e}")
            return False
            
    def _run_in_chroot_output(self, command: str) -> str:
        """Run command in chroot and return output"""
        try:
            full_cmd = f"chroot {self.chroot_path} /bin/bash -c '{command}'"
            result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
            return result.stdout.strip() if result.returncode == 0 else ""
        except Exception as e:
            self.logger.error(f"Failed to run command in chroot: {e}")
            return ""
            
    def validate_config(self) -> bool:
        """Validate module configuration"""
        return True