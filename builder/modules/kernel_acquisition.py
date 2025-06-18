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
    
    def _get_latest_stable(self) -> str:
        """Fetch latest stable kernel version from kernel.org"""
        
        try:
            response = requests.get(self.kernel_api, timeout=30)
            response.raise_for_status()
            
            releases = response.json()
            
            # Find latest stable (not RC)
            for release in releases['releases']:
                if release['moniker'] == 'stable' and 'rc' not in release['version']:
                    return release['version']
                    
            raise Exception("No stable kernel found")
            
        except Exception as e:
            self.logger.error(f"Failed to fetch kernel info: {e}")
            # Fallback to known good version
            return "6.8.12"
    
    def _download_kernel(self, version: str) -> Path:
        """Download kernel package from Debian repositories"""
        
        self.logger.info(f"Downloading kernel {version}...")
        
        # For latest kernels, we'll use Debian experimental or backports
        major_version = version.split('.')[0] + '.' + version.split('.')[1]
        
        # Construct package names
        packages = [
            f"linux-image-{major_version}-amd64",
            f"linux-headers-{major_version}-amd64"
        ]
        
        # Download using apt in download-only mode
        download_dir = self.workspace / "kernel_downloads"
        download_dir.mkdir(parents=True, exist_ok=True)
        
        # Add experimental repo temporarily
        sources_list = f"""
        deb http://deb.debian.org/debian experimental main
        deb http://deb.debian.org/debian bookworm-backports main
        """
        
        sources_file = self.workspace / "kernel.list"
        sources_file.write_text(sources_list)
        
        cmd = [
            "apt-get", "update",
            "-o", f"Dir::Etc::sourcelist={sources_file}",
            "-o", f"Dir::Cache={self.workspace / 'apt_cache'}",
            "-o", f"Dir::State={self.workspace / 'apt_state'}"
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Download packages
        for package in packages:
            cmd = [
                "apt-get", "download",
                "-o", f"Dir::Cache={download_dir}",
                package
            ]
            subprocess.run(cmd, check=True, cwd=download_dir)
            
        return download_dir
    
    def _install_kernel(self, kernel_path: Path, version: str) -> Dict:
        """Install kernel into chroot environment"""
        
        chroot_path = self.workspace / "chroot"
        
        # Copy kernel packages
        kernel_dest = chroot_path / "tmp/kernel_packages"
        kernel_dest.mkdir(parents=True, exist_ok=True)
        
        subprocess.run([
            "cp", "-r", 
            str(kernel_path) + "/.", 
            str(kernel_dest)
        ], check=True)
        
        # Install in chroot
        install_script = f"""#!/bin/bash
        set -e
        cd /tmp/kernel_packages
        dpkg -i linux-image-*.deb linux-headers-*.deb || apt-get -f install -y
        update-initramfs -u
        """
        
        script_path = chroot_path / "tmp/install_kernel.sh"
        script_path.write_text(install_script)
        script_path.chmod(0o755)
        
        subprocess.run([
            "chroot", str(chroot_path),
            "/tmp/install_kernel.sh"
        ], check=True)
        
        return {
            'status': 'success',
            'kernel_version': version,
            'kernel_path': str(kernel_dest)
        }
