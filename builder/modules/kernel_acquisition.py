#!/usr/bin/env python3
# z-forge/builder/modules/kernel_acquisition.py

"""
Kernel Acquisition Module
Fetches and prepares latest stable Linux kernel for ISO environment
"""

import requests
import subprocess
import re
from pathlib import Path
from typing import Dict, Optional
import logging

class KernelAcquisition:
    """Handles acquisition of latest stable kernel"""
    
    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.kernel_api = "https://www.kernel.org/releases.json"
        
    def execute(self, resume_data: Optional[Dict] = None) -> Dict:
        """
        Fetch and install latest stable kernel
        
        Returns:
            Dict containing kernel version and paths
        """
        
        self.logger.info("Starting kernel acquisition...")
        
        try:
            # Determine target kernel version
            if self.config.get('kernel_version') == 'latest':
                kernel_version = self._get_latest_stable()
            else:
                kernel_version = self.config.get('kernel_version')
                
            self.logger.info(f"Target kernel version: {kernel_version}")
            
            # Check if already cached
            kernel_path = self._check_cache(kernel_version)
            if kernel_path:
                self.logger.info("Using cached kernel")
                return self._install_kernel(kernel_path, kernel_version)
                
            # Download kernel
            kernel_path = self._download_kernel(kernel_version)
            
            # Verify integrity
            self._verify_kernel(kernel_path, kernel_version)
            
            # Install into workspace
            result = self._install_kernel(kernel_path, kernel_version)
            
            # Generate dracut initramfs
            self._generate_dracut_initramfs()
            
            # Cache for future builds
            if self.config.get('cache_packages', True):
                self._cache_kernel(kernel_path, kernel_version)
                
            return result
            
        except Exception as e:
            self.logger.error(f"Kernel acquisition failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    # [... rest of the existing KernelAcquisition class ...]
    
    def _generate_dracut_initramfs(self):
        """Generate dracut initramfs for installed kernel"""
        
        self.logger.info("Generating dracut initramfs...")
        
        chroot_path = self.workspace / "chroot"
        
        # Find installed kernel version
        kernel_version_cmd = "ls -1 /lib/modules"
        result = subprocess.run(
            ["chroot", str(chroot
