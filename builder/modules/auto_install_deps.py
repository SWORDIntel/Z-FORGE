#!/usr/bin/env python3
"""
Auto Install Dependencies Module for Z-FORGE
Automatically installs missing system dependencies
"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

class AutoInstallDeps:
    """Automatically install missing dependencies"""
    
    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Package mapping for different tools
        self.package_map = {
            'debootstrap': 'debootstrap',
            'mkisofs': 'genisoimage',
            'xorriso': 'xorriso',
            'mksquashfs': 'squashfs-tools',
            'git': 'git',
            'wget': 'wget',
            'curl': 'curl',
            'gpg': 'gnupg',
            'gcc': 'build-essential',
            'make': 'build-essential',
            'mkfs.vfat': 'dosfstools',
            'mkfs.ext4': 'e2fsprogs',
            'parted': 'parted',
            'rsync': 'rsync',
            'chroot': 'coreutils',
            'ar': 'binutils',
            'unsquashfs': 'squashfs-tools',
            'isohybrid': 'syslinux-utils',
            'fdisk': 'fdisk',
            'blkid': 'util-linux'
        }
        
    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[Any] = None) -> Dict:
        """Check and install missing dependencies"""
        try:
            self.logger.info("Checking for missing dependencies...")
            
            # Check what's missing
            missing_commands = self._check_missing_commands()
            
            if not missing_commands:
                self.logger.info("All dependencies are already installed")
                return {'status': 'success', 'installed': []}
            
            self.logger.info(f"Missing commands: {', '.join(missing_commands)}")
            
            # Get packages to install
            packages_to_install = self._get_packages_for_commands(missing_commands)
            
            if not packages_to_install:
                self.logger.warning("No packages found for missing commands")
                return {
                    'status': 'warning',
                    'missing_commands': missing_commands,
                    'message': 'Could not determine packages to install'
                }
            
            # Check if we can use apt
            if not self._check_apt_available():
                return {
                    'status': 'error',
                    'error': 'APT package manager not available',
                    'missing_commands': missing_commands
                }
            
            # Update package list
            self.logger.info("Updating package list...")
            self._run_apt_update()
            
            # Install packages
            self.logger.info(f"Installing packages: {', '.join(packages_to_install)}")
            installed = self._install_packages(packages_to_install)
            
            # Verify installation
            still_missing = self._check_missing_commands()
            
            if still_missing:
                self.logger.warning(f"Some commands still missing after installation: {', '.join(still_missing)}")
                return {
                    'status': 'partial',
                    'installed': installed,
                    'still_missing': still_missing
                }
            
            self.logger.info("All dependencies installed successfully!")
            return {
                'status': 'success',
                'installed': installed
            }
            
        except Exception as e:
            self.logger.error(f"Failed to install dependencies: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _check_missing_commands(self) -> List[str]:
        """Check which commands are missing"""
        all_commands = list(self.package_map.keys())
        missing = []
        
        for cmd in all_commands:
            if not shutil.which(cmd):
                missing.append(cmd)
                
        return missing
    
    def _get_packages_for_commands(self, commands: List[str]) -> List[str]:
        """Get unique packages needed for commands"""
        packages = set()
        
        for cmd in commands:
            if cmd in self.package_map:
                packages.add(self.package_map[cmd])
                
        return list(packages)
    
    def _check_apt_available(self) -> bool:
        """Check if apt is available"""
        return shutil.which('apt-get') is not None
    
    def _run_apt_update(self):
        """Run apt update"""
        try:
            subprocess.run(
                ['sudo', 'apt-get', 'update'],
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"apt update failed: {e}")
    
    def _install_packages(self, packages: List[str]) -> List[str]:
        """Install packages using apt"""
        installed = []
        
        for package in packages:
            try:
                self.logger.info(f"Installing {package}...")
                result = subprocess.run(
                    ['sudo', 'apt-get', 'install', '-y', package],
                    check=True,
                    capture_output=True,
                    text=True
                )
                installed.append(package)
                self.logger.info(f"Successfully installed {package}")
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Failed to install {package}: {e}")
                
        return installed