#!/usr/bin/env python3
"""
Fix APT repository configuration for ZFS package installation in chroot.

This script ensures that the APT sources.list in the chroot environment
includes the 'contrib' repository section required for ZFS packages on
Debian-based systems.
"""

import subprocess
import logging
from pathlib import Path
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ZFSRepoFixer')

class ZFSRepoFixer:
    def __init__(self, chroot_path="/tmp/zforge_workspace/chroot"):
        self.chroot_path = Path(chroot_path)
        self.sources_list = self.chroot_path / "etc/apt/sources.list"
        
    def check_chroot_exists(self):
        """Verify the chroot directory exists."""
        if not self.chroot_path.exists():
            logger.error(f"Chroot directory not found: {self.chroot_path}")
            return False
        return True
        
    def detect_debian_version(self):
        """Detect the Debian version in the chroot."""
        try:
            # Check for os-release
            os_release = self.chroot_path / "etc/os-release"
            if os_release.exists():
                with open(os_release, 'r') as f:
                    for line in f:
                        if line.startswith('VERSION_CODENAME='):
                            return line.split('=')[1].strip().strip('"')
            
            # Fallback to debian_version
            debian_version = self.chroot_path / "etc/debian_version"
            if debian_version.exists():
                with open(debian_version, 'r') as f:
                    version = f.read().strip()
                    # Map numeric versions to codenames
                    if '13' in version:
                        return 'trixie'
                    elif '12' in version:
                        return 'bookworm'
                    elif '11' in version:
                        return 'bullseye'
            
            # Default to trixie for Z-FORGE
            logger.warning("Could not detect Debian version, defaulting to 'trixie'")
            return 'trixie'
            
        except Exception as e:
            logger.error(f"Error detecting Debian version: {e}")
            return 'trixie'
    
    def fix_apt_sources(self):
        """Fix the APT sources.list to include contrib and non-free-firmware."""
        debian_version = self.detect_debian_version()
        logger.info(f"Detected Debian version: {debian_version}")
        
        # Create proper sources.list content
        sources_content = f"""# Debian {debian_version} repositories with contrib for ZFS
deb http://deb.debian.org/debian {debian_version} main contrib non-free-firmware
deb-src http://deb.debian.org/debian {debian_version} main contrib non-free-firmware

deb http://deb.debian.org/debian-security {debian_version}-security main contrib non-free-firmware
deb-src http://deb.debian.org/debian-security {debian_version}-security main contrib non-free-firmware

# Updates (for stable releases)
"""
        
        if debian_version not in ['trixie', 'sid', 'testing', 'unstable']:
            sources_content += f"""deb http://deb.debian.org/debian {debian_version}-updates main contrib non-free-firmware
deb-src http://deb.debian.org/debian {debian_version}-updates main contrib non-free-firmware
"""
        
        # Backup existing sources.list if it exists
        if self.sources_list.exists():
            backup_path = self.sources_list.with_suffix('.list.backup')
            try:
                subprocess.run(
                    ['sudo', 'cp', str(self.sources_list), str(backup_path)],
                    check=True,
                    capture_output=True
                )
                logger.info(f"Backed up existing sources.list to {backup_path}")
            except subprocess.CalledProcessError as e:
                logger.warning(f"Could not backup sources.list: {e}")
        
        # Write new sources.list
        try:
            # Create temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
                tmp.write(sources_content)
                tmp_path = tmp.name
            
            # Copy to chroot with sudo
            subprocess.run(
                ['sudo', 'cp', tmp_path, str(self.sources_list)],
                check=True,
                capture_output=True
            )
            
            # Clean up temp file
            Path(tmp_path).unlink()
            
            logger.info("Successfully updated sources.list with contrib repository")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to update sources.list: {e}")
            return False
    
    def update_package_index(self):
        """Update the package index in chroot."""
        logger.info("Updating package index in chroot...")
        try:
            result = subprocess.run(
                ['sudo', 'chroot', str(self.chroot_path), 'apt-get', 'update'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("Package index updated successfully")
                return True
            else:
                logger.error(f"Failed to update package index: {result.stderr}")
                return False
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Error updating package index: {e}")
            return False
    
    def check_zfs_availability(self):
        """Check if ZFS packages are available after fixing repos."""
        logger.info("Checking ZFS package availability...")
        try:
            result = subprocess.run(
                ['sudo', 'chroot', str(self.chroot_path), 'apt-cache', 'search', '^zfs'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                zfs_packages = [line for line in result.stdout.split('\n') if line]
                logger.info(f"Found {len(zfs_packages)} ZFS-related packages:")
                for pkg in zfs_packages[:10]:  # Show first 10
                    logger.info(f"  - {pkg}")
                return True
            else:
                logger.error("Could not search for ZFS packages")
                return False
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Error checking ZFS packages: {e}")
            return False
    
    def install_zfs_packages(self):
        """Attempt to install ZFS packages."""
        logger.info("Installing ZFS packages...")
        
        # Package sets to try
        package_sets = [
            ['zfsutils-linux', 'zfs-dkms'],
            ['zfsutils-linux'],
            ['zfs', 'zfs-dkms'],
            ['zfs']
        ]
        
        for packages in package_sets:
            logger.info(f"Trying to install: {packages}")
            try:
                result = subprocess.run(
                    ['sudo', 'chroot', str(self.chroot_path), 'apt-get', 'install', '-y', '--no-install-recommends'] + packages,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    logger.info(f"Successfully installed: {packages}")
                    return True
                else:
                    logger.warning(f"Failed to install {packages}: {result.stderr}")
                    
            except subprocess.CalledProcessError as e:
                logger.warning(f"Error installing {packages}: {e}")
        
        logger.error("All ZFS installation attempts failed")
        return False
    
    def run(self):
        """Run the complete fix process."""
        logger.info("Starting ZFS APT repository fix...")
        
        if not self.check_chroot_exists():
            return False
        
        if not self.fix_apt_sources():
            return False
        
        if not self.update_package_index():
            return False
        
        if not self.check_zfs_availability():
            return False
        
        if self.install_zfs_packages():
            logger.info("ZFS APT repository fix completed successfully!")
            return True
        else:
            logger.error("ZFS APT repository fix completed but package installation failed")
            return False

if __name__ == "__main__":
    fixer = ZFSRepoFixer()
    success = fixer.run()
    sys.exit(0 if success else 1)