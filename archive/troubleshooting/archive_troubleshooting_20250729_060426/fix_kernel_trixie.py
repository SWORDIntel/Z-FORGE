#!/usr/bin/env python3
"""
Fix kernel installation to use Debian Trixie kernels.

This script updates the kernel acquisition process to properly use
Debian Trixie kernels instead of Bookworm kernels, ensuring compatibility
with the Trixie chroot environment and ZFS DKMS modules.
"""

import subprocess
import logging
from pathlib import Path
import re
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TrixieKernelFix')

class TrixieKernelFixer:
    def __init__(self, chroot_path="/tmp/zforge_workspace/chroot"):
        self.chroot_path = Path(chroot_path)
        self.debian_release = self._detect_debian_release()
        
    def _detect_debian_release(self):
        """Detect the Debian release in the chroot."""
        try:
            os_release = self.chroot_path / "etc/os-release"
            if os_release.exists():
                with open(os_release, 'r') as f:
                    for line in f:
                        if line.startswith('VERSION_CODENAME='):
                            return line.split('=')[1].strip().strip('"')
            
            # Default to trixie for Z-FORGE
            return 'trixie'
        except Exception as e:
            logger.error(f"Error detecting Debian release: {e}")
            return 'trixie'
    
    def fix_apt_sources_for_kernel(self):
        """Ensure APT sources are properly configured for kernel installation."""
        logger.info(f"Configuring APT sources for {self.debian_release} kernel...")
        
        # Create proper sources.list
        sources_content = f"""# Debian {self.debian_release} repositories
deb http://deb.debian.org/debian {self.debian_release} main contrib non-free-firmware
deb-src http://deb.debian.org/debian {self.debian_release} main contrib non-free-firmware

deb http://deb.debian.org/debian-security {self.debian_release}-security main contrib non-free-firmware
deb-src http://deb.debian.org/debian-security {self.debian_release}-security main contrib non-free-firmware
"""
        
        # For stable releases, add updates
        if self.debian_release not in ['trixie', 'sid', 'testing', 'unstable']:
            sources_content += f"""
deb http://deb.debian.org/debian {self.debian_release}-updates main contrib non-free-firmware
deb-src http://deb.debian.org/debian {self.debian_release}-updates main contrib non-free-firmware
"""
        
        # Write sources.list
        import tempfile
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
                tmp.write(sources_content)
                tmp_path = tmp.name
            
            subprocess.run(
                ['sudo', 'cp', tmp_path, str(self.chroot_path / "etc/apt/sources.list")],
                check=True
            )
            Path(tmp_path).unlink()
            
            logger.info("APT sources updated successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to update sources.list: {e}")
            return False
        
        # Update package index
        try:
            subprocess.run(
                ['sudo', 'chroot', str(self.chroot_path), 'apt-get', 'update'],
                check=True,
                capture_output=True
            )
            logger.info("Package index updated")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to update package index: {e}")
            return False
    
    def get_available_kernels(self):
        """Get list of available kernel packages."""
        logger.info("Checking available kernel packages...")
        
        try:
            result = subprocess.run(
                ['sudo', 'chroot', str(self.chroot_path), 
                 'apt-cache', 'search', '^linux-image-[0-9]'],
                capture_output=True,
                text=True,
                check=True
            )
            
            kernels = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    pkg_name = line.split(' - ')[0]
                    # Extract version from package name
                    match = re.match(r'linux-image-(\d+\.\d+\.\d+-\d+)-', pkg_name)
                    if match:
                        version = match.group(1)
                        kernels.append((pkg_name, version))
            
            # Sort by version (newest first)
            kernels.sort(key=lambda x: x[1], reverse=True)
            
            logger.info(f"Found {len(kernels)} available kernels")
            for pkg, ver in kernels[:5]:  # Show top 5
                logger.info(f"  - {pkg} (version {ver})")
            
            return kernels
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to search for kernels: {e}")
            return []
    
    def install_trixie_kernel(self):
        """Install the latest Trixie kernel with headers."""
        logger.info("Installing Debian Trixie kernel...")
        
        # Get available kernels
        kernels = self.get_available_kernels()
        if not kernels:
            logger.error("No kernels found!")
            return False
        
        # Use the latest kernel
        latest_kernel_pkg, latest_version = kernels[0]
        
        # Determine architecture suffix
        if '-amd64' in latest_kernel_pkg:
            arch_suffix = 'amd64'
        elif '-arm64' in latest_kernel_pkg:
            arch_suffix = 'arm64'
        else:
            arch_suffix = 'amd64'  # Default
        
        # Construct package names
        kernel_image_pkg = f"linux-image-{latest_version}-{arch_suffix}"
        kernel_headers_pkg = f"linux-headers-{latest_version}-{arch_suffix}"
        kernel_headers_common = f"linux-headers-{latest_version}-common"
        
        packages_to_install = [
            kernel_image_pkg,
            kernel_headers_pkg,
            kernel_headers_common,
            "linux-headers-generic",  # Metapackage
            "build-essential",        # For DKMS
            "dkms"                    # DKMS itself
        ]
        
        logger.info(f"Installing kernel packages: {packages_to_install}")
        
        try:
            # Install kernel and headers
            result = subprocess.run(
                ['sudo', 'chroot', str(self.chroot_path), 
                 'apt-get', 'install', '-y', '--no-install-recommends'] + packages_to_install,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to install kernel: {result.stderr}")
                # Try without the common headers package
                logger.info("Retrying without common headers package...")
                packages_to_install.remove(kernel_headers_common)
                
                result = subprocess.run(
                    ['sudo', 'chroot', str(self.chroot_path), 
                     'apt-get', 'install', '-y', '--no-install-recommends'] + packages_to_install,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    logger.error(f"Failed to install kernel on retry: {result.stderr}")
                    return False
            
            logger.info(f"Successfully installed kernel {latest_version}")
            
            # Verify installation
            vmlinuz = self.chroot_path / f"boot/vmlinuz-{latest_version}-{arch_suffix}"
            if vmlinuz.exists():
                logger.info(f"Kernel image verified at: {vmlinuz}")
            else:
                logger.warning("Kernel image not found at expected location")
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install kernel: {e}")
            return False
    
    def install_zfs_with_dkms(self):
        """Install ZFS with DKMS support for the new kernel."""
        logger.info("Installing ZFS with DKMS support...")
        
        packages = [
            "zfsutils-linux",
            "zfs-dkms",
            "zfs-dracut"  # For dracut initramfs support
        ]
        
        try:
            # Remove any conflicting packages first
            subprocess.run(
                ['sudo', 'chroot', str(self.chroot_path), 
                 'apt-get', 'remove', '-y', 'zfs-initramfs'],
                capture_output=True
            )
            
            # Install ZFS packages
            result = subprocess.run(
                ['sudo', 'chroot', str(self.chroot_path), 
                 'apt-get', 'install', '-y'] + packages,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to install ZFS: {result.stderr}")
                # Try without zfs-dracut
                logger.info("Retrying without zfs-dracut...")
                packages.remove("zfs-dracut")
                
                result = subprocess.run(
                    ['sudo', 'chroot', str(self.chroot_path), 
                     'apt-get', 'install', '-y'] + packages,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    logger.error(f"Failed to install ZFS on retry: {result.stderr}")
                    return False
            
            logger.info("ZFS packages installed successfully")
            
            # Check DKMS status
            try:
                dkms_result = subprocess.run(
                    ['sudo', 'chroot', str(self.chroot_path), 'dkms', 'status'],
                    capture_output=True,
                    text=True
                )
                logger.info("DKMS status:")
                logger.info(dkms_result.stdout)
            except:
                logger.warning("Could not check DKMS status")
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install ZFS: {e}")
            return False
    
    def run(self):
        """Run the complete Trixie kernel fix process."""
        logger.info(f"Starting Trixie kernel fix for {self.debian_release}...")
        
        if not self.chroot_path.exists():
            logger.error(f"Chroot directory not found: {self.chroot_path}")
            return False
        
        # Step 1: Fix APT sources
        if not self.fix_apt_sources_for_kernel():
            return False
        
        # Step 2: Install Trixie kernel
        if not self.install_trixie_kernel():
            return False
        
        # Step 3: Install ZFS with DKMS
        if not self.install_zfs_with_dkms():
            return False
        
        logger.info("Trixie kernel fix completed successfully!")
        return True

if __name__ == "__main__":
    fixer = TrixieKernelFixer()
    success = fixer.run()
    sys.exit(0 if success else 1)