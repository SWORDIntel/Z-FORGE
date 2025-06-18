# z-forge/builder/modules/zfs_build.py

"""
ZFS Build Module
Compiles and installs latest OpenZFS with DKMS support
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional
import logging

class ZFSBuild:
    """Handles OpenZFS compilation and installation"""
    
    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.zfs_repo = "https://github.com/openzfs/zfs.git"
        
    def execute(self, resume_data: Optional[Dict] = None) -> Dict:
        """
        Build and install OpenZFS from source
        
        Returns:
            Dict containing ZFS version and installation status
        """
        
        self.logger.info("Starting ZFS build process...")
        
        try:
            chroot_path = self.workspace / "chroot"
            
            # Install build dependencies
            self._install_build_deps(chroot_path)
            
            # Clone ZFS repository
            if self.config.get('zfs_config', {}).get('version') == 'latest':
                zfs_version = self._get_latest_release()
            else:
                zfs_version = self.config.get('zfs_config', {}).get('version', '2.2.4')
            
            # Build ZFS
            self._build_zfs(chroot_path, zfs_version)
            
            # Configure DKMS
            self._configure_dkms(chroot_path)
            
            # Set up ZFS services
            self._setup_services(chroot_path)
            
            return {
                'status': 'success',
                'zfs_version': zfs_version,
                'features': {
                    'encryption': True,
                    'compression': 'lz4',
                    'dkms': True
                }
            }
            
        except Exception as e:
            self.logger.error(f"ZFS build failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _install_build_deps(self, chroot_path: Path):
        """Install ZFS build dependencies in chroot"""
        
        deps = [
            'build-essential',
            'autoconf',
            'automake',
            'libtool',
            'gawk',
            'alien',
            'fakeroot',
            'dkms',
            'libblkid-dev',
            'uuid-dev',
            'libudev-dev',
            'libssl-dev',
            'zlib1g-dev',
            'libaio-dev',
            'libattr1-dev',
            'libelf-dev',
            'python3',
            'python3-dev',
            'python3-setuptools',
            'python3-cffi',
            'libffi-dev',
            'git'
        ]
        
        install_cmd = f"apt-get update && apt-get install -y {' '.join(deps)}"
        
        subprocess.run([
            "chroot", str(chroot_path),
            "bash", "-c", install_cmd
        ], check=True)
        
    def _get_latest_release(self) -> str:
        """Get latest stable ZFS release tag"""
        
        cmd = [
            "git", "ls-remote", "--tags", "--refs", self.zfs_repo,
            "| grep -E 'refs/tags/zfs-[0-9]+\\.[0-9]+\\.[0-9]+$'",
            "| tail -1",
            "| sed 's/.*refs\\/tags\\/zfs-//'"
        ]
        
        result = subprocess.run(
            " ".join(cmd),
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return "2.2.4"  # Fallback version
            
    def _build_zfs(self, chroot_path: Path, version: str):
        """Build ZFS from source in chroot"""
        
        build_script = f"""#!/bin/bash
        set -e
        
        # Clone repository
        cd /usr/src
        git clone --depth 1 --branch zfs-{version} {self.zfs_repo}
        cd zfs
        
        # Configure build
        ./autogen.sh
        ./configure \\
            --prefix=/usr \\
            --with-linux=/usr/src/linux-headers-$(uname -r) \\
            --enable-systemd \\
            --enable-pyzfs \\
            --with-python=3
            
        # Build
        make -j$(nproc)
        
        # Install
        make install
        
        # Install DKMS modules
        make deb-dkms
        dpkg -i *.deb || apt-get -f install -y
        """
        
        script_path = chroot_path / "tmp/build_zfs.sh"
        script_path.write_text(build_script)
        script_path.chmod(0o755)
        
        subprocess.run([
            "chroot", str(chroot_path),
            "/tmp/build_zfs.sh"
        ], check=True)
