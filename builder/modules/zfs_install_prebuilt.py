"""
ZFS Install Prebuilt Module

Installs prebuilt ZFS packages in chroot
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from builder.core.module import BaseModule
from builder.utils.logger import Logger


class ZfsInstallPrebuilt(BaseModule):
    """Install prebuilt ZFS packages"""
    
    def __init__(self, config: Dict[str, Any], chroot_path: Optional[Path] = None):
        super().__init__(config, chroot_path)
        self.logger = Logger(self.__class__.__name__)
        self.packages_dir = self.config.get('packages_dir', '/tmp/prebuilt_packages/zfs')
        
    def execute(self) -> bool:
        """Install ZFS packages in chroot"""
        try:
            self.logger.info("Installing prebuilt ZFS packages...")
            
            # Check if packages exist
            pkg_path = Path(self.packages_dir)
            if not self._path_exists_in_chroot(pkg_path):
                self.logger.error(f"Package directory not found in chroot: {pkg_path}")
                return False
                
            # Count packages
            pkg_count = len(list((self.chroot_path / pkg_path.lstrip('/')).glob("*.deb")))
            self.logger.info(f"Found {pkg_count} ZFS packages to install")
            
            if pkg_count == 0:
                self.logger.error("No ZFS packages found")
                return False
                
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
                return False
                
            # Verify installation
            verify_cmd = "dpkg -l | grep -E '^ii.*zfs' | wc -l"
            output = self._run_in_chroot_output(verify_cmd)
            
            if output and int(output.strip()) > 0:
                self.logger.success(f"Successfully installed {output.strip()} ZFS packages")
                
                # Load ZFS module
                self.logger.info("Loading ZFS kernel module...")
                self._run_in_chroot("modprobe zfs || true")
                
                # Enable ZFS services
                self.logger.info("Enabling ZFS services...")
                services = ['zfs-import-cache', 'zfs-mount', 'zfs-share', 'zfs-zed']
                for service in services:
                    self._run_in_chroot(f"systemctl enable {service} || true")
                    
                return True
            else:
                self.logger.error("ZFS packages not properly installed")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to install ZFS packages: {e}")
            return False
            
    def _path_exists_in_chroot(self, path: Path) -> bool:
        """Check if path exists in chroot"""
        chroot_path = self.chroot_path / path.lstrip('/')
        return chroot_path.exists()
        
    def validate_config(self) -> bool:
        """Validate module configuration"""
        return True