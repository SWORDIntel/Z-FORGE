#!/usr/bin/env python3
# z-forge/builder/modules/dracut_config.py

"""
Dracut Configuration Module
Ensures dracut is properly installed and configured for ZFS
"""

import subprocess
import shutil
from pathlib import Path
from typing import Dict, Optional, Any
import logging
from builder.core.lockfile import BuildLockfile

class DracutConfig:
    """Handles dracut installation and configuration"""
    
    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"
        
    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[BuildLockfile] = None) -> Dict:
        """
        Install and configure dracut
        
        Returns:
            Dict with configuration status
        """
        
        self.logger.info("Starting dracut configuration...")
        
        try:
            # FIRST: Ensure pseudo-filesystems are mounted (critical for package operations)
            self.logger.info("Ensuring pseudo-filesystems are mounted in chroot...")
            self._ensure_pseudo_filesystems_mounted()
            
            # Remove initramfs-tools
            self._remove_initramfs_tools()
            
            # Install dracut packages
            self._install_dracut()
            
            # Install custom toram module (if available) first
            toram_module_installed = self._install_toram_module()
            
            # Configure dracut with knowledge of toram module availability
            self._configure_dracut(toram_module_installed)
            
            # Generate initramfs with dracut
            self._generate_initramfs(toram_module_installed)
            
            return {
                'status': 'success',
                'dracut_version': self._get_dracut_version()
            }
            
        except Exception as e:
            self.logger.error(f"Dracut configuration failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _ensure_pseudo_filesystems_mounted(self):
        """Ensure /proc, /sys, /dev are mounted in chroot"""
        mounts = [
            ("proc", "proc", self.chroot_path / "proc"),
            ("sysfs", "sys", self.chroot_path / "sys"),
            ("devtmpfs", "dev", self.chroot_path / "dev"),
            ("devpts", "dev/pts", self.chroot_path / "dev/pts"),
        ]
        
        for fs_type, target, mount_point in mounts:
            # Check if already mounted
            check_cmd = ["mountpoint", "-q", str(mount_point)]
            result = subprocess.run(check_cmd, capture_output=True)
            
            if result.returncode != 0:
                # Not mounted, mount it
                self.logger.debug(f"Mounting {fs_type} at {mount_point}")
                # Ensure mount point exists
                mount_point.mkdir(parents=True, exist_ok=True)
                mount_cmd = ["sudo", "mount", "-t", fs_type, fs_type, str(mount_point)]
                subprocess.run(mount_cmd, check=True)
    
    def _remove_initramfs_tools(self):
        """Remove initramfs-tools if installed"""
        
        self.logger.info("Removing initramfs-tools...")
        
        # First check if it's installed
        check_cmd = [
            "chroot", str(self.chroot_path),
            "dpkg", "-l", "initramfs-tools"
        ]
        check_result = subprocess.run(check_cmd, capture_output=True, text=True)
        
        if "ii  initramfs-tools" in check_result.stdout:
            cmd = [
                "chroot", str(self.chroot_path),
                "apt-get", "remove", "--purge", "-y", 
                "initramfs-tools", "initramfs-tools-core", "initramfs-tools-bin"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info("initramfs-tools removed successfully")
                # Clean up any leftover config
                subprocess.run([
                    "chroot", str(self.chroot_path),
                    "apt-get", "autoremove", "--purge", "-y"
                ], capture_output=True)
            else:
                self.logger.warning(f"Failed to remove initramfs-tools: {result.stderr}")
        else:
            self.logger.info("initramfs-tools not installed or already removed")
    
    def _install_dracut(self):
        """Install dracut and required packages"""
        
        self.logger.info("Installing dracut packages...")
        
        # First configure DEBIAN_FRONTEND to prevent interactive prompts
        self.logger.info("Configuring non-interactive installation...")
        try:
            # Set debconf to noninteractive mode
            subprocess.run([
                "chroot", str(self.chroot_path),
                "bash", "-c", "echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections"
            ], check=True, timeout=30)
            
            # Set keyboard configuration to prevent prompts
            subprocess.run([
                "chroot", str(self.chroot_path),
                "bash", "-c", "echo 'keyboard-configuration keyboard-configuration/layout select English (US)' | debconf-set-selections"
            ], check=True, timeout=30)
            
            subprocess.run([
                "chroot", str(self.chroot_path),
                "bash", "-c", "echo 'keyboard-configuration keyboard-configuration/variant select English (US)' | debconf-set-selections"
            ], check=True, timeout=30)
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to configure debconf: {e}")
        
        # Update package lists to ensure we have latest versions
        self.logger.info("Updating package lists...")
        try:
            subprocess.run([
                "chroot", str(self.chroot_path),
                "env", "DEBIAN_FRONTEND=noninteractive",
                "apt-get", "update"
            ], check=True, timeout=120)
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to update package lists: {e}")
        
        # Core essential packages only - avoid version conflicts
        essential_packages = [
            "dracut-core",  # Start with core only
            "binutils",     # For lsinitrd  
            "squashfs-tools", # For live systems
            "util-linux",   # Essential utilities
            "systemd",      # Base systemd
        ]
        
        # Install essential packages first
        self.logger.info("Installing essential dracut packages...")
        for pkg in essential_packages:
            try:
                cmd = [
                    "chroot", str(self.chroot_path),
                    "env", "DEBIAN_FRONTEND=noninteractive",
                    "apt-get", "install", "-y", "--no-install-recommends",
                    "--allow-downgrades", pkg
                ]
                subprocess.run(cmd, check=True, timeout=120)
                self.logger.info(f"Successfully installed: {pkg}")
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Failed to install essential package {pkg}: {e}")
                raise Exception(f"Cannot proceed without {pkg}")
        
        # Try to install full dracut after core is working
        self.logger.info("Installing full dracut package...")
        try:
            cmd = [
                "chroot", str(self.chroot_path),
                "env", "DEBIAN_FRONTEND=noninteractive",
                "apt-get", "install", "-y", "--no-install-recommends",
                "--allow-downgrades", "dracut"
            ]
            subprocess.run(cmd, check=True, timeout=120)
            self.logger.info("Full dracut package installed successfully")
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Full dracut install failed: {e}")
            self.logger.info("Continuing with dracut-core only...")
        
        # Optional packages - install if available, don't fail if not
        optional_packages = [
            "dracut-network",
            "pigz",
            "dmsetup",
            "kpartx",
            "kbd",
            "cryptsetup",
            "lvm2",
            "mdadm",
            "nvme-cli",
            "jq"
        ]
        
        self.logger.info("Installing optional packages...")
        for pkg in optional_packages:
            try:
                cmd = [
                    "chroot", str(self.chroot_path),
                    "env", "DEBIAN_FRONTEND=noninteractive",
                    "apt-get", "install", "-y", "--no-install-recommends", pkg
                ]
                subprocess.run(cmd, check=True, timeout=60)
                self.logger.info(f"Installed optional package: {pkg}")
            except subprocess.CalledProcessError:
                self.logger.warning(f"Optional package not available or failed: {pkg}")
        
        # Verify dracut is working
        try:
            result = subprocess.run([
                "chroot", str(self.chroot_path),
                "dracut", "--version"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                self.logger.info(f"Dracut installed successfully: {result.stdout.strip()}")
            else:
                raise Exception("Dracut command not working")
                
        except Exception as e:
            self.logger.error(f"Dracut verification failed: {e}")
            raise Exception("Dracut installation failed verification")
    
    def _get_available_kernel_modules(self):
        """Get list of available kernel modules"""
        try:
            # Get the kernel version
            result = subprocess.run([
                "chroot", str(self.chroot_path),
                "ls", "-1", "/lib/modules"
            ], capture_output=True, text=True, check=True)
            
            kernel_versions = result.stdout.strip().split('\n')
            if not kernel_versions or not kernel_versions[0]:
                return []
                
            kernel_version = kernel_versions[-1]  # Use latest
            self.logger.info(f"Checking available modules for kernel {kernel_version}")
            
            # Get available modules
            modules_dir = f"/lib/modules/{kernel_version}/kernel"
            result = subprocess.run([
                "chroot", str(self.chroot_path),
                "find", modules_dir, "-name", "*.ko", "-type", "f"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                modules = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        module_name = Path(line).stem
                        modules.append(module_name)
                return modules
            else:
                self.logger.warning("Could not list kernel modules")
                return []
                
        except Exception as e:
            self.logger.warning(f"Failed to get kernel modules: {e}")
            return []

    def _configure_dracut(self, toram_module_available=False):
        """Configure dracut for ZFS boot"""
        
        self.logger.info("Configuring dracut...")
        
        # Get available kernel modules
        available_modules = self._get_available_kernel_modules()
        self.logger.info(f"Found {len(available_modules)} kernel modules available")
        
        # Create main dracut configuration
        dracut_conf = """# Z-Forge dracut configuration

# Compression (zstd offers good balance)
compress="zstd"

# Don't include host-specific files by default
hostonly="no"

# Ensure early microcode loading
early_microcode="yes"

# Add essential modules
add_dracutmodules+=" base systemd systemd-initrd kernel-modules rootfs-block terminfo udev-rules "
add_dracutmodules+=" dracut-systemd fs-lib shutdown "

# ZFS support (make sure it's available)
add_dracutmodules+=" zfs "

# Live system support (if available)
# Note: dmsquash-live may not be available in all dracut installations
"""
        
        # Check which dracut modules are actually available
        self.logger.info("Checking available dracut modules...")
        try:
            result = subprocess.run([
                "chroot", str(self.chroot_path),
                "dracut", "--list-modules"
            ], capture_output=True, text=True, timeout=30)
            
            available_dracut_modules = []
            if result.returncode == 0:
                available_dracut_modules = result.stdout.strip().split('\n')
                self.logger.info(f"Found {len(available_dracut_modules)} dracut modules")
                
                # Add live system support if available
                live_modules = ["dmsquash-live", "dmsquash-live-autooverlay", "livenet"]
                available_live = [mod for mod in live_modules if mod in available_dracut_modules]
                if available_live:
                    self.logger.info(f"Adding live system modules: {' '.join(available_live)}")
                    dracut_conf += f'\n# Live system support\nadd_dracutmodules+=" {" ".join(available_live)} "\n'
                else:
                    self.logger.warning("No live system modules available - will create basic initramfs")
            else:
                self.logger.warning("Could not list dracut modules")
        except Exception as e:
            self.logger.warning(f"Failed to check dracut modules: {e}")
        
        # Add custom Z-Forge modules only if available
        if toram_module_available:
            self.logger.info("Adding 90zforge-toram module to dracut configuration")
            dracut_conf += '\n# Custom Z-Forge modules\nadd_dracutmodules+=" 90zforge-toram "\n'
        else:
            self.logger.info("Skipping 90zforge-toram module - not available")
            
        dracut_conf += """
# Exclude problematic modules
omit_dracutmodules+=" bluetooth nfs nbd fcoe fcoe-uefi "

# Include essential kernel modules for ZFS
install_items+=" /lib/modules/$kernel/kernel/fs/zfs/ "

"""
        
        # Add available drivers dynamically
        drivers_to_check = [
            "nvme", "nvme-core", "nvme_common", "nvme-tcp", "nvme-rdma", "nvme-fc", "nvme-fabrics",
            "megaraid_sas", "mpt3sas", "ahci", "sd_mod", "sr_mod"
        ]
        
        available_drivers = []
        for driver in drivers_to_check:
            if driver in available_modules:
                available_drivers.append(driver)
        
        if available_drivers:
            self.logger.info(f"Adding available drivers: {' '.join(available_drivers)}")
            dracut_conf += f'\n# Available storage and NVMe drivers\nadd_drivers+=" {" ".join(available_drivers)} "\n'
        else:
            self.logger.warning("No additional storage drivers found")
            
        dracut_conf += """
# Include necessary filesystems
filesystems+=" squashfs ext4 vfat "

# Ensure necessary binaries are included
install_items+=" /sbin/zfs /sbin/zpool /sbin/mount.zfs "
"""
        
        dracut_conf_path = self.chroot_path / "etc/dracut.conf.d/zforge.conf"
        dracut_conf_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dracut_conf_path, 'w') as f:
            f.write(dracut_conf)
        
        # Create ZFS-specific configuration
        zfs_conf = """# ZFS dracut configuration

# Enable ZFS hostid support
install_optional_items+=" /etc/hostid /etc/zfs/zpool.cache /etc/zfs/vdev_id.conf "

# Include ZFS commands and libraries
install_items+=" /usr/sbin/zfs /usr/sbin/zpool /usr/sbin/zdb /usr/sbin/zed "
install_items+=" /usr/lib/x86_64-linux-gnu/libnvpair.so* "
install_items+=" /usr/lib/x86_64-linux-gnu/libuutil.so* "
install_items+=" /usr/lib/x86_64-linux-gnu/libzfs.so* "
install_items+=" /usr/lib/x86_64-linux-gnu/libzfs_core.so* "
install_items+=" /usr/lib/x86_64-linux-gnu/libzpool.so* "

# ZFS kernel module parameters
kernel_cmdline+=" quiet splash "
"""
        
        zfs_conf_path = self.chroot_path / "etc/dracut.conf.d/zfs.conf"
        with open(zfs_conf_path, 'w') as f:
            f.write(zfs_conf)
        
        # Create hostid if it doesn't exist
        hostid_path = self.chroot_path / "etc/hostid"
        if not hostid_path.exists():
            self.logger.info("Generating ZFS hostid...")
            try:
                # First try zgenhostid if available
                subprocess.run([
                    "chroot", str(self.chroot_path),
                    "zgenhostid"
                ], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                # Fallback to manual generation
                self.logger.info("zgenhostid not available, using fallback method")
                subprocess.run([
                    "chroot", str(self.chroot_path),
                    "bash", "-c", "printf $(openssl rand 4 | od -A n -t x4) > /etc/hostid"
                ], check=True)

        self.logger.info("Dracut configuration completed")

    def _install_toram_module(self):
        """Install custom toram dracut module if available"""
        
        self.logger.info("Checking for custom Z-Forge toram dracut module...")
        
        # Define module name and paths
        custom_module_name = "90zforge-toram"
        host_custom_module_src_dir = Path(__file__).parent.parent / "dracut_toram_module"
        
        # Check if source module exists
        if not host_custom_module_src_dir.exists():
            self.logger.warning(f"Custom toram module source not found at {host_custom_module_src_dir}")
            self.logger.info("Skipping custom toram module installation - will use standard dracut")
            return False
        
        # Check both possible dracut module directories
        possible_dirs = [
            self.chroot_path / "usr/lib/dracut/modules.d",
            self.chroot_path / "lib/dracut/modules.d"
        ]
        
        # Find the correct dracut modules directory
        dracut_modules_dir = None
        for dir_path in possible_dirs:
            if dir_path.exists():
                dracut_modules_dir = dir_path
                break
                
        if not dracut_modules_dir:
            # Create the standard directory if none exist
            dracut_modules_dir = self.chroot_path / "usr/lib/dracut/modules.d"
            self.logger.info(f"Creating dracut modules directory: {dracut_modules_dir}")
            dracut_modules_dir.mkdir(parents=True, exist_ok=True)
            
        chroot_dracut_module_dir = dracut_modules_dir / custom_module_name
        
        # Check if source directory exists
        if not host_custom_module_src_dir.is_dir():
            self.logger.warning(f"Custom dracut module source not found at {host_custom_module_src_dir}, skipping toram support")
            return
        
        # Create module directory in chroot
        self.logger.info(f"Creating dracut module directory: {chroot_dracut_module_dir}")
        chroot_dracut_module_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy module files
        module_setup_src = host_custom_module_src_dir / "module-setup.sh"
        hook_script_src = host_custom_module_src_dir / "zforge-toram-hook.sh"
        
        module_setup_dst = chroot_dracut_module_dir / "module-setup.sh"
        hook_script_dst = chroot_dracut_module_dir / "zforge-toram-hook.sh"
        
        if not module_setup_src.exists() or not hook_script_src.exists():
            self.logger.warning("Custom dracut module scripts not found, skipping toram support")
            return
        
        # Copy files
        self.logger.info(f"Copying module-setup.sh to chroot")
        shutil.copy2(module_setup_src, module_setup_dst)
        self.logger.info(f"Copying zforge-toram-hook.sh to chroot")
        shutil.copy2(hook_script_src, hook_script_dst)
        
        # Set execute permissions
        chmod_path_setup = "/" + str(module_setup_dst.relative_to(self.chroot_path))
        chmod_path_hook = "/" + str(hook_script_dst.relative_to(self.chroot_path))
        
        subprocess.run(["sudo", "chroot", str(self.chroot_path), "chmod", "+x", chmod_path_setup], check=True)
        subprocess.run(["sudo", "chroot", str(self.chroot_path), "chmod", "+x", chmod_path_hook], check=True)
        self.logger.info("Set execute permissions for custom dracut module scripts")
        
        # Verify the module is properly installed
        check_cmd = ["chroot", str(self.chroot_path), "ls", "-la", 
                     "/" + str(chroot_dracut_module_dir.relative_to(self.chroot_path))]
        result = subprocess.run(check_cmd, capture_output=True, text=True)
        self.logger.info(f"Module directory contents: {result.stdout}")
        
        # Also check if dracut can see the module
        list_modules_cmd = ["chroot", str(self.chroot_path), "dracut", "--list-modules"]
        modules_result = subprocess.run(list_modules_cmd, capture_output=True, text=True)
        if "90zforge-toram" in modules_result.stdout:
            self.logger.info("✓ 90zforge-toram module is recognized by dracut")
        else:
            self.logger.warning("✗ 90zforge-toram module NOT recognized by dracut!")
            self.logger.debug(f"Available modules: {modules_result.stdout}")
        
        # Don't add to config here - it's already added in _configure_dracut
        self.logger.info("Custom toram module installed successfully")
        return True
    
    def _generate_initramfs(self, toram_module_available=False):
        """Generate initramfs with dracut"""
        
        self.logger.info("Generating initramfs with dracut...")
        
        # Ensure pseudo-filesystems are mounted
        self._ensure_pseudo_filesystems_mounted()
        
        # Find installed kernel
        kernel_version_cmd = "ls -1 /lib/modules | tail -1"
        result = subprocess.run(
            ["sudo", "chroot", str(self.chroot_path), "bash", "-c", kernel_version_cmd],
            capture_output=True,
            text=True,
            check=True
        )
        
        kernel_version = result.stdout.strip()
        
        if not kernel_version:
            raise Exception("No kernel modules found")
        
        self.logger.info(f"Generating initramfs for kernel {kernel_version}")
        
        # Run depmod first to generate modules.dep
        self.logger.info(f"Running depmod for kernel {kernel_version}...")
        depmod_cmd = ["sudo", "chroot", str(self.chroot_path), "depmod", "-a", kernel_version]
        result = subprocess.run(depmod_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            self.logger.warning(f"depmod failed: {result.stderr}")
        else:
            self.logger.info("depmod completed successfully")
        
        # First, list available dracut modules to debug
        self.logger.info("Listing available dracut modules...")
        list_cmd = ["sudo", "chroot", str(self.chroot_path), "dracut", "--list-modules"]
        list_result = subprocess.run(list_cmd, capture_output=True, text=True)
        self.logger.debug(f"Available modules: {list_result.stdout}")
        
        # Generate initramfs - with verbose output for debugging
        cmd = [
            "sudo", "chroot", str(self.chroot_path),
            "dracut", "-f", "--verbose",
            f"/boot/initramfs-{kernel_version}.img", kernel_version,
            "--no-hostonly"  # Don't use hostonly in chroot
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            self.logger.error(f"Dracut output: {result.stdout}")
            self.logger.error(f"Dracut errors: {result.stderr}")
            
            # Try with minimal modules
            self.logger.warning("Initial dracut failed, trying with minimal configuration...")
            cmd_minimal = [
                "sudo", "chroot", str(self.chroot_path),
                "dracut", "-f",
                "--omit", "90zforge-toram", "--omit", "dmsquash-live", 
                "--omit", "dmsquash-live-autooverlay", "--omit", "livenet",
                "--add", "base", "--add", "systemd", "--add", "kernel-modules",
                "--add", "rootfs-block", "--add", "zfs",
                f"/boot/initramfs-{kernel_version}.img", kernel_version,
                "--no-hostonly"
            ]
            result = subprocess.run(cmd_minimal, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"Minimal dracut also failed: {result.stderr}")
                # Last resort: try with absolute minimal setup
                self.logger.warning("Trying absolute minimal dracut configuration...")
                cmd_absolute_minimal = [
                    "sudo", "chroot", str(self.chroot_path),
                    "dracut", "-f", "--no-hostonly", 
                    "--add", "base", "--add", "systemd",
                    f"/boot/initramfs-{kernel_version}.img", kernel_version
                ]
                result = subprocess.run(cmd_absolute_minimal, capture_output=True, text=True)
                
                if result.returncode != 0:
                    raise Exception(f"All dracut attempts failed: {result.stderr}")
                else:
                    self.logger.info("Absolute minimal initramfs generated successfully")
        
        # Verify initramfs was created
        initramfs_path = self.chroot_path / f"boot/initramfs-{kernel_version}.img"
        if not initramfs_path.exists():
            raise Exception(f"Initramfs not found at {initramfs_path}")
        
        self.logger.info(f"Initramfs generated successfully at {initramfs_path}")
        
        return kernel_version
    
    def _get_dracut_version(self):
        """Get installed dracut version"""
        
        cmd = ["chroot", str(self.chroot_path), "dracut", "--version"]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return "unknown"