#!/usr/bin/env python3
"""
UltraThink ZFS Kernel Builder Agent

Builds ZFS 2.3.3 from within the Linux kernel source directory
to ensure proper kernel module support.
"""

import subprocess
import os
import sys
import shutil
import requests
import tarfile
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [ZFSKernelBuilder] %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'zfs_kernel_builder_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

class ZFSKernelBuilder:
    """Builds ZFS within Linux kernel source tree"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.zfs_version = "2.3.3"
        self.zfs_url = f"https://github.com/openzfs/zfs/releases/download/zfs-{self.zfs_version}/zfs-{self.zfs_version}.tar.gz"
        self.work_dir = Path("/tmp/zfs_kernel_build")
        self.output_dir = Path("/opt/github/Z-FORGE/prebuilt_packages")
        
    def find_kernel_source(self) -> Optional[Path]:
        """Find the Linux kernel source directory"""
        self.logger.info("Searching for Linux kernel source...")
        
        # Common locations for kernel source
        search_paths = [
            Path("/usr/src"),
            Path("/lib/modules"),
            Path("/tmp/zforge_workspace/chroot/usr/src"),
            Path("/tmp/zforge_workspace/chroot/lib/modules")
        ]
        
        for search_path in search_paths:
            if not search_path.exists():
                continue
                
            # Look for linux-* directories
            for item in search_path.glob("linux-*"):
                if item.is_dir():
                    # Check if it's a kernel source tree
                    if (item / "Makefile").exists() and (item / "include/linux/kernel.h").exists():
                        self.logger.info(f"Found kernel source at: {item}")
                        return item
                        
            # Also check for kernel build directories
            for item in search_path.glob("*/build"):
                if item.is_dir() and (item / "Makefile").exists():
                    self.logger.info(f"Found kernel build directory at: {item}")
                    return item
                    
        # Try to find from current kernel
        try:
            result = subprocess.run(['uname', '-r'], capture_output=True, text=True)
            if result.returncode == 0:
                kernel_version = result.stdout.strip()
                kernel_paths = [
                    Path(f"/lib/modules/{kernel_version}/build"),
                    Path(f"/usr/src/linux-headers-{kernel_version}"),
                    Path(f"/usr/src/linux-{kernel_version}")
                ]
                
                for kpath in kernel_paths:
                    if kpath.exists() and (kpath / "Makefile").exists():
                        self.logger.info(f"Found kernel source for current kernel at: {kpath}")
                        return kpath
                        
        except Exception as e:
            self.logger.warning(f"Failed to detect current kernel: {e}")
            
        return None
        
    def prepare_kernel_source(self, kernel_dir: Path) -> bool:
        """Prepare kernel source for module building"""
        self.logger.info(f"Preparing kernel source at {kernel_dir}")
        
        try:
            # Check if modules are enabled
            config_file = kernel_dir / ".config"
            if not config_file.exists():
                # Try to copy from /boot
                boot_config = Path(f"/boot/config-{self._get_kernel_version(kernel_dir)}")
                if boot_config.exists():
                    shutil.copy(boot_config, config_file)
                    self.logger.info(f"Copied config from {boot_config}")
                else:
                    self.logger.error("No kernel config found")
                    return False
                    
            # Verify CONFIG_MODULES is enabled
            with open(config_file, 'r') as f:
                config_content = f.read()
                if 'CONFIG_MODULES=y' not in config_content:
                    self.logger.error("CONFIG_MODULES not enabled in kernel config")
                    return False
                    
            # Run make modules_prepare
            self.logger.info("Running 'make modules_prepare' in kernel source...")
            result = subprocess.run(
                ['make', 'modules_prepare'],
                cwd=kernel_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.logger.error(f"make modules_prepare failed: {result.stderr}")
                return False
                
            self.logger.info("Kernel source prepared successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to prepare kernel source: {e}")
            return False
            
    def _get_kernel_version(self, kernel_dir: Path) -> str:
        """Extract kernel version from Makefile"""
        makefile = kernel_dir / "Makefile"
        if not makefile.exists():
            return "unknown"
            
        version_parts = {}
        with open(makefile, 'r') as f:
            for line in f:
                if line.startswith('VERSION'):
                    parts = line.split('=')
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        version_parts[key] = value
                        
        version = version_parts.get('VERSION', '')
        patchlevel = version_parts.get('PATCHLEVEL', '')
        sublevel = version_parts.get('SUBLEVEL', '')
        
        if version and patchlevel:
            return f"{version}.{patchlevel}.{sublevel}"
        return "unknown"
        
    def download_zfs_source(self) -> Path:
        """Download ZFS source code"""
        self.logger.info(f"Downloading ZFS {self.zfs_version} source...")
        
        self.work_dir.mkdir(parents=True, exist_ok=True)
        tarball_path = self.work_dir / f"zfs-{self.zfs_version}.tar.gz"
        
        if not tarball_path.exists():
            response = requests.get(self.zfs_url, stream=True)
            response.raise_for_status()
            
            with open(tarball_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
        # Extract
        with tarfile.open(tarball_path, 'r:gz') as tar:
            tar.extractall(self.work_dir)
            
        source_dir = self.work_dir / f"zfs-{self.zfs_version}"
        self.logger.info(f"ZFS source extracted to {source_dir}")
        return source_dir
        
    def build_zfs_with_kernel(self, zfs_source: Path, kernel_dir: Path) -> bool:
        """Build ZFS using the kernel source"""
        self.logger.info(f"Building ZFS {self.zfs_version} with kernel at {kernel_dir}")
        
        try:
            # Run autogen
            self.logger.info("Running autogen.sh...")
            result = subprocess.run(
                ['./autogen.sh'],
                cwd=zfs_source,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                self.logger.error(f"autogen.sh failed: {result.stderr}")
                return False
                
            # Configure with kernel source
            self.logger.info("Configuring ZFS build...")
            configure_cmd = [
                './configure',
                f'--with-linux={kernel_dir}',
                f'--with-linux-obj={kernel_dir}',
                '--prefix=/usr',
                '--sysconfdir=/etc',
                '--localstatedir=/var',
                '--libdir=/usr/lib/x86_64-linux-gnu',
                '--includedir=/usr/include',
                '--with-config=all',
                '--enable-systemd',
                '--enable-pyzfs'
            ]
            
            result = subprocess.run(
                configure_cmd,
                cwd=zfs_source,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                self.logger.error(f"Configure failed: {result.stderr}")
                return False
                
            # Build
            self.logger.info("Building ZFS (this may take a while)...")
            result = subprocess.run(
                ['make', '-j4'],
                cwd=zfs_source,
                capture_output=True,
                text=True,
                timeout=1800
            )
            
            if result.returncode != 0:
                self.logger.error(f"Build failed: {result.stderr}")
                return False
                
            # Build Debian packages
            self.logger.info("Building Debian packages...")
            
            # Build userspace packages
            result = subprocess.run(
                ['make', 'deb-utils'],
                cwd=zfs_source,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode != 0:
                self.logger.warning(f"deb-utils failed: {result.stderr}")
                
            # Build kernel module packages
            result = subprocess.run(
                ['make', 'deb-kmod'],
                cwd=zfs_source,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode != 0:
                self.logger.warning(f"deb-kmod failed: {result.stderr}")
                
            self.logger.info("ZFS build completed successfully")
            return True
            
        except subprocess.TimeoutExpired:
            self.logger.error("Build process timed out")
            return False
        except Exception as e:
            self.logger.error(f"Build failed with exception: {e}")
            return False
            
    def collect_packages(self, zfs_source: Path) -> List[Path]:
        """Collect built packages"""
        self.logger.info("Collecting built packages...")
        
        packages = []
        # Look for .deb files in parent directory
        for deb in zfs_source.parent.glob("*.deb"):
            packages.append(deb)
            self.logger.info(f"Found package: {deb.name}")
            
        return packages
        
    def create_installer(self, packages: List[Path]) -> None:
        """Create installation script"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy packages
        for pkg in packages:
            dest = self.output_dir / pkg.name
            shutil.copy2(pkg, dest)
            
        # Create installer script
        installer_script = self.output_dir / "install_zfs_kernel_built.sh"
        
        script_content = f'''#!/bin/bash
# ZFS Kernel-Built Package Installer
# Built from kernel source for proper module support

set -e

CHROOT_PATH="${{1:-/tmp/zforge_workspace/chroot}}"
PACKAGES_DIR="$(dirname "$0")"

echo "Installing kernel-built ZFS packages to $CHROOT_PATH"

# Copy packages
mkdir -p "$CHROOT_PATH/tmp/zfs-packages"
cp "$PACKAGES_DIR"/*.deb "$CHROOT_PATH/tmp/zfs-packages/" || true

# Install in chroot
chroot "$CHROOT_PATH" /bin/bash -c "
    cd /tmp/zfs-packages
    
    # Install all packages
    dpkg -i *.deb || apt-get install -f -y
    
    # Enable services
    systemctl enable zfs-import-cache || true
    systemctl enable zfs-mount || true
    
    # Clean up
    rm -rf /tmp/zfs-packages
"

echo "ZFS kernel-built packages installed successfully!"
'''
        
        with open(installer_script, 'w') as f:
            f.write(script_content)
            
        installer_script.chmod(0o755)
        self.logger.info(f"Created installer at {installer_script}")
        
    def execute(self) -> bool:
        """Execute the build process"""
        try:
            # Find kernel source
            kernel_dir = self.find_kernel_source()
            if not kernel_dir:
                self.logger.error("No kernel source found. Please install kernel headers or source.")
                self.logger.info("Try: sudo apt-get install linux-headers-$(uname -r)")
                return False
                
            # Prepare kernel
            if not self.prepare_kernel_source(kernel_dir):
                return False
                
            # Download ZFS source
            zfs_source = self.download_zfs_source()
            
            # Build ZFS
            if not self.build_zfs_with_kernel(zfs_source, kernel_dir):
                return False
                
            # Collect packages
            packages = self.collect_packages(zfs_source)
            if not packages:
                self.logger.error("No packages were built")
                return False
                
            # Create installer
            self.create_installer(packages)
            
            self.logger.info(f"✅ Successfully built {len(packages)} ZFS packages")
            self.logger.info(f"📦 Packages saved to: {self.output_dir}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Build process failed: {e}")
            return False

def main():
    """Main entry point"""
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║           UltraThink ZFS Kernel Builder Agent                     ║")
    print("║      Build ZFS with proper kernel module support                  ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print()
    
    if os.geteuid() != 0:
        print("❌ This script must be run as root")
        print("   sudo python3 ultrathink_zfs_kernel_builder.py")
        return 1
        
    # Check for existing packages
    output_dir = Path("/opt/github/Z-FORGE/prebuilt_packages")
    if output_dir.exists() and list(output_dir.glob("*.deb")):
        print("✅ Pre-built packages already exist")
        print(f"   Location: {output_dir}")
        print("   To rebuild, run: sudo rm -rf {output_dir}")
        return 0
        
    builder = ZFSKernelBuilder()
    
    print("🔍 Searching for kernel source...")
    print("🔨 This will build ZFS within the kernel source tree")
    print()
    
    if builder.execute():
        print()
        print("✅ ZFS kernel build completed successfully!")
        print("🚀 Z-FORGE can now use these kernel-built packages")
        return 0
    else:
        print()
        print("❌ ZFS kernel build failed")
        print("📋 Check the log for details")
        return 1

if __name__ == "__main__":
    sys.exit(main())