#!/usr/bin/env python3
"""
Fix ZFS installation issues in kernel_acquisition.py
Updates the approach to use native Debian packages from contrib repository
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def fix_zfs_installation():
    """Fix the ZFS installation approach in kernel_acquisition.py"""
    
    kernel_acquisition_path = "builder/modules/kernel_acquisition.py"
    
    # Read the current file
    with open(kernel_acquisition_path, 'r') as f:
        content = f.read()
    
    # Fix 1: Update _add_zfs_repository to enable contrib and not add external repo
    new_add_zfs_repository = '''    def _add_zfs_repository(self) -> None:
        """Enable contrib repository for ZFS packages in Debian."""
        self.logger.info("Enabling contrib repository for ZFS packages...")
        
        try:
            # Read current sources.list
            sources_list_path = self.chroot_path / "etc/apt/sources.list"
            if sources_list_path.exists():
                with open(sources_list_path, 'r') as f:
                    sources_content = f.read()
                
                # Check if contrib is already enabled
                if 'contrib' not in sources_content:
                    self.logger.info("Adding contrib component to sources.list...")
                    
                    # Add contrib to existing lines
                    lines = sources_content.split('\\n')
                    new_lines = []
                    for line in lines:
                        if line.strip() and not line.strip().startswith('#'):
                            if 'deb ' in line and 'main' in line and 'contrib' not in line:
                                # Add contrib and non-free-firmware to the line
                                line = line.rstrip() + ' contrib non-free-firmware'
                        new_lines.append(line)
                    
                    # Write back the updated sources.list
                    with open(sources_list_path, 'w') as f:
                        f.write('\\n'.join(new_lines))
                    
                    self.logger.info("Updated sources.list with contrib repository")
                else:
                    self.logger.info("Contrib repository already enabled")
            
            # Update package lists
            self._run_chroot_command([
                "apt-get", "update"
            ])
            
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to update package lists: {e}")
            self.logger.info("Continuing with installation attempt...")
    '''
    
    # Replace the _add_zfs_repository method
    import re
    pattern = r'def _add_zfs_repository\(self\) -> None:.*?(?=\n    def|\n\nclass|\Z)'
    content = re.sub(pattern, new_add_zfs_repository.strip(), content, flags=re.DOTALL)
    
    # Fix 2: Update package installation to handle missing packages gracefully
    # Find and update the _prepare_chroot_environment method's ZFS package installation
    old_zfs_packages = 'zfs_packages = ["zfsutils-linux", "zfs-dkms"]'
    new_zfs_packages = '''zfs_packages = ["zfsutils-linux", "zfs-dkms"]
        # Alternative ZFS packages if main ones fail
        zfs_alt_packages = ["zfs-modules", "zfs-initramfs"]'''
    
    content = content.replace(old_zfs_packages, new_zfs_packages)
    
    # Fix 3: Update _install_zfs_module to be more robust
    new_install_zfs_module = '''    def _install_zfs_module(self, kernel_version: str) -> None:
        """
        Install ZFS kernel module for the specified kernel version.
        
        Args:
            kernel_version: The kernel version to install ZFS for.
        """
        self.logger.info(f"Installing ZFS module for kernel {kernel_version}...")
        
        # Enable contrib repository for Debian native ZFS packages
        self._add_zfs_repository()
        
        # Try to install ZFS packages with fallback options
        zfs_install_success = False
        
        # First attempt: Install standard ZFS packages
        try:
            self.logger.info("Installing ZFS packages from Debian repositories...")
            self._run_chroot_command([
                "apt-get", "install", "-y", "--no-install-recommends",
                "zfsutils-linux", "zfs-dkms"
            ])
            zfs_install_success = True
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Standard ZFS package installation failed: {e}")
            
            # Second attempt: Try installing with --fix-missing
            try:
                self.logger.info("Retrying with --fix-missing...")
                self._run_chroot_command([
                    "apt-get", "install", "-y", "--fix-missing", "--no-install-recommends",
                    "zfsutils-linux", "zfs-dkms"
                ])
                zfs_install_success = True
            except subprocess.CalledProcessError as e2:
                self.logger.warning(f"ZFS installation with --fix-missing failed: {e2}")
                
                # Third attempt: Install alternative packages
                try:
                    self.logger.info("Trying alternative ZFS packages...")
                    self._run_chroot_command([
                        "apt-get", "install", "-y", "--no-install-recommends",
                        "zfs-modules", "zfs-initramfs"
                    ])
                    zfs_install_success = True
                except subprocess.CalledProcessError as e3:
                    self.logger.error(f"All ZFS installation attempts failed: {e3}")
        
        if zfs_install_success:
            # Build ZFS module for the kernel using DKMS
            self._mount_pseudo_filesystems()
            
            try:
                # Check if DKMS is available and working
                dkms_check = self._run_chroot_command(["which", "dkms"], check=False)
                if dkms_check.returncode == 0:
                    # Try DKMS autoinstall
                    self.logger.info(f"Building ZFS modules with DKMS for kernel {kernel_version}...")
                    try:
                        self._run_chroot_command([
                            "dkms", "autoinstall", "-k", kernel_version
                        ])
                    except subprocess.CalledProcessError as e:
                        self.logger.warning(f"DKMS autoinstall failed: {e}")
                        # Try manual build
                        self.logger.info("Attempting manual DKMS build...")
                        # Find ZFS version
                        try:
                            zfs_version_result = self._run_chroot_command([
                                "dpkg-query", "-W", "-f='${Version}'", "zfs-dkms"
                            ])
                            zfs_version = zfs_version_result.stdout.strip().strip("'").split('-')[0]
                            self.logger.info(f"Found ZFS DKMS version: {zfs_version}")
                            
                            # Try to build manually
                            self._run_chroot_command([
                                "dkms", "build", "-m", "zfs", "-v", zfs_version, "-k", kernel_version
                            ], check=False)
                            self._run_chroot_command([
                                "dkms", "install", "-m", "zfs", "-v", zfs_version, "-k", kernel_version
                            ], check=False)
                        except:
                            self.logger.warning("Manual DKMS build also failed")
                else:
                    self.logger.warning("DKMS not available, skipping module build")
            finally:
                # Always unmount the filesystems
                self._unmount_pseudo_filesystems()
        else:
            self.logger.warning("ZFS packages could not be installed, continuing without ZFS kernel modules")
            self.logger.info("Dracut will attempt to include ZFS support if userspace tools are available")
            
        # Verify ZFS module was installed (but don't fail if not)
        self.logger.info("Checking ZFS module installation...")
        modules_path = self.chroot_path / "lib" / "modules" / kernel_version / "updates" / "dkms"
        
        if modules_path.exists():
            zfs_modules = list(modules_path.glob("*/zfs.ko*"))
            if zfs_modules:
                self.logger.info(f"Found ZFS kernel modules: {[str(m.name) for m in zfs_modules]}")
            else:
                self.logger.warning("ZFS kernel modules not found in DKMS directory")
        else:
            self.logger.warning(f"DKMS modules directory not found: {modules_path}")
            
        # Check if ZFS userspace tools are available
        zfs_check = self._run_chroot_command(["which", "zfs"], check=False)
        if zfs_check.returncode == 0:
            self.logger.info("ZFS userspace tools are available")
        else:
            self.logger.warning("ZFS userspace tools not found - ZFS support may be limited")
'''
    
    # Replace the _install_zfs_module method
    pattern = r'def _install_zfs_module\(self, kernel_version: str\) -> None:.*?(?=\n    def|\n\nclass|\Z)'
    content = re.sub(pattern, new_install_zfs_module.strip(), content, flags=re.DOTALL)
    
    # Write the updated content back
    with open(kernel_acquisition_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated {kernel_acquisition_path} with improved ZFS installation approach")
    print("\nChanges made:")
    print("1. Modified _add_zfs_repository to enable contrib repository instead of adding external repo")
    print("2. Added fallback options for ZFS package installation")
    print("3. Made _install_zfs_module more robust with multiple retry strategies")
    print("4. Added proper error handling that continues build even if ZFS modules fail")
    print("\nThis approach uses native Debian packages which is more reliable for Trixie.")

if __name__ == "__main__":
    fix_zfs_installation()