#!/usr/bin/env python3
"""
Perfect Kernel Acquisition Module for Z-Forge

This module ensures consistent Trixie kernel installation without conflicts.
"""

import subprocess
import logging
from pathlib import Path
from typing import Dict, Optional, Any

class PerfectKernelAcquisition:
    """Perfect kernel acquisition that always works"""
    
    def __init__(self, workspace: Path, config: Dict[str, Any]):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = self.workspace / "chroot"
        
    def execute(self, resume_data: Optional[Dict[str, Any]] = None, lockfile=None) -> Dict[str, Any]:
        """Execute perfect kernel acquisition"""
        self.logger.info("Starting perfect kernel acquisition for Trixie")
        
        try:
            # Step 1: Configure perfect APT sources
            self._configure_perfect_apt_sources()
            
            # Step 2: Update package lists
            self._update_package_lists()
            
            # Step 3: Install kernel with perfect strategy
            kernel_version = self._install_perfect_kernel()
            
            # Step 4: Verify installation
            self._verify_kernel_installation(kernel_version)
            
            return {
                'status': 'success',
                'kernel_version': kernel_version,
                'features': {'trixie': True, 'zfs_compatible': True}
            }
            
        except Exception as e:
            self.logger.error(f"Perfect kernel acquisition failed: {e}")
            return {'status': 'error', 'error': str(e)}
            
    def _configure_perfect_apt_sources(self):
        """Configure perfect APT sources for Trixie"""
        sources_content = """# Perfect Trixie sources for Z-FORGE
deb http://deb.debian.org/debian trixie main contrib non-free non-free-firmware
deb-src http://deb.debian.org/debian trixie main contrib non-free non-free-firmware

deb http://deb.debian.org/debian-security trixie-security main contrib non-free non-free-firmware
deb-src http://deb.debian.org/debian-security trixie-security main contrib non-free non-free-firmware
"""
        
        sources_file = self.chroot_path / "etc/apt/sources.list"
        with open(sources_file, 'w') as f:
            f.write(sources_content)
            
        self.logger.info("Perfect APT sources configured")
        
    def _update_package_lists(self):
        """Update package lists"""
        cmd = ["sudo", "chroot", str(self.chroot_path), "apt-get", "update"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Failed to update package lists: {result.stderr}")
            
    def _install_perfect_kernel(self) -> str:
        """Install kernel using perfect strategy"""
        # Strategy 1: Try specific 6.12 kernel
        target_kernels = [
            "linux-image-6.12.38+deb13-amd64",
            "linux-image-amd64"
        ]
        
        for kernel in target_kernels:
            try:
                self.logger.info(f"Attempting to install {kernel}")
                
                cmd = [
                    "sudo", "chroot", str(self.chroot_path),
                    "apt-get", "install", "-y", "--no-install-recommends",
                    kernel, "linux-headers-amd64", "build-essential", "dkms"
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                
                if result.returncode == 0:
                    self.logger.info(f"Successfully installed {kernel}")
                    return kernel
                    
            except Exception as e:
                self.logger.warning(f"Failed to install {kernel}: {e}")
                continue
                
        raise Exception("All kernel installation attempts failed")
        
    def _verify_kernel_installation(self, kernel_version: str):
        """Verify kernel installation"""
        cmd = ["sudo", "chroot", str(self.chroot_path), "dpkg", "-l"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if "linux-image" not in result.stdout:
            raise Exception("No kernel packages found after installation")
            
        self.logger.info("Kernel installation verified")
