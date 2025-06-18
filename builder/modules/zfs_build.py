#!/usr/bin/env python3
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
            
            # Set up ZFS dracut module
            self._setup_dracut_zfs(chroot_path)
            
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
    
    # [... rest of the existing ZFSBuild class ...]
    
    def _setup_dracut_zfs(self, chroot_path: Path):
        """Configure dracut for ZFS support"""
        
        self.logger.info("Setting up dracut ZFS module...")
        
        # Ensure dracut is installed
        subprocess.run([
            "chroot", str(chroot_path),
            "apt-get", "install", "-y", "dracut", "dracut-network"
        ], check=True)
        
        # Create ZFS dracut config
        dracut_zfs_conf = """# ZFS dracut configuration
# Load ZFS modules
add_dracutmodules+=" zfs "

# Include necessary filesystems
filesystems+=" zfs "

# Enable ZFS hostid support
install_optional_items+=" /etc/hostid /etc/zfs/zpool.cache "

# Include ZFS commands
install_items+=" /usr/bin/zfs /usr/bin/zpool "
"""
        
        dracut_conf_path = chroot_path / "etc/dracut.conf.d/zfs.conf"
        dracut_conf_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dracut_conf_path, 'w') as f:
            f.write(dracut_zfs_conf)
        
        # Create hostid
        subprocess.run([
            "chroot", str(chroot_path),
            "bash", "-c", "zgenhostid $(hexdump -n 4 -e '\"0x%08x\"' /dev/urandom)"
        ], check=True)
        
        # Regenerate dracut
        subprocess.run([
            "chroot", str(chroot_path),
            "dracut", "-f", "--regenerate-all"
        ], check=True)
