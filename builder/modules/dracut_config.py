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
            # Remove initramfs-tools
            self._remove_initramfs_tools()
            
            # Install dracut packages
            self._install_dracut()
            
            # Configure dracut
            self._configure_dracut()
            
            # Install custom toram module
            self._install_toram_module()
            
            # Generate initramfs with dracut
            self._generate_initramfs()
            
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
        
        cmd = [
            "chroot", str(self.chroot_path),
            "apt-get", "remove", "-y", "initramfs-tools", "initramfs-tools-core"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            self.logger.info("initramfs-tools removed successfully")
        else:
            self.logger.info("initramfs-tools not installed or already removed")
    
    def _install_dracut(self):
        """Install dracut and required packages"""
        
        self.logger.info("Installing dracut packages...")
        
        packages = [
            "dracut",
            "dracut-core",
            "dracut-network",
            "dracut-squash",
            "binutils",  # For lsinitrd
            "pigz",      # For parallel compression
            "squashfs-tools",  # For mksquashfs/unsquashfs needed by dmsquash-live
            "dmsetup",   # Device mapper tools
            "kpartx"     # For partition mapping
        ]
        
        cmd = [
            "chroot", str(self.chroot_path),
            "apt-get", "install", "-y", "--no-install-recommends"
        ] + packages
        
        subprocess.run(cmd, check=True)
        
        self.logger.info("Dracut packages installed successfully")
    
    def _configure_dracut(self):
        """Configure dracut for ZFS boot"""
        
        self.logger.info("Configuring dracut...")
        
        # Create main dracut configuration
        dracut_conf = """# Z-Forge dracut configuration

# Compression (zstd offers good balance)
compress="zstd"

# Don't include host-specific files by default
hostonly="no"

# Add essential modules
add_dracutmodules+=" base systemd systemd-initrd kernel-modules rootfs-block terminfo udev-rules "
add_dracutmodules+=" dracut-systemd fs-lib shutdown "

# ZFS support
add_dracutmodules+=" zfs "

# Custom Z-Forge modules
add_dracutmodules+=" 90zforge-toram "

# Exclude problematic modules
omit_dracutmodules+=" bluetooth nfs "

# Include any additional drivers needed for NVMe
add_drivers+=" nvme nvme-core nvme-tcp nvme-rdma nvme-fc nvme-fabrics "

# Dell PowerEdge R730xd specific drivers
add_drivers+=" megaraid_sas mpt3sas "

# Include squashfs support for live boot
filesystems+=" squashfs "
"""
        
        dracut_conf_path = self.chroot_path / "etc/dracut.conf.d/zforge.conf"
        dracut_conf_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dracut_conf_path, 'w') as f:
            f.write(dracut_conf)
        
        # Create ZFS-specific configuration
        zfs_conf = """# ZFS dracut configuration

# Enable ZFS hostid support
install_optional_items+=" /etc/hostid /etc/zfs/zpool.cache "

# Include ZFS commands
install_items+=" /usr/bin/zfs /usr/bin/zpool "
"""
        
        zfs_conf_path = self.chroot_path / "etc/dracut.conf.d/zfs.conf"
        with open(zfs_conf_path, 'w') as f:
            f.write(zfs_conf)
        
        # Create hostid if it doesn't exist
        hostid_path = self.chroot_path / "etc/hostid"
        if not hostid_path.exists():
            subprocess.run([
                "chroot", str(self.chroot_path),
                "bash", "-c", "zgenhostid $(hexdump -n 4 -e '\"0x%08x\"' /dev/urandom)"
            ], check=True)

        self.logger.info("Dracut configuration completed")

    def _install_toram_module(self):
        """Install custom toram dracut module"""
        
        self.logger.info("Installing custom Z-Forge toram dracut module...")
        
        # Define module name and paths
        custom_module_name = "90zforge-toram"
        host_custom_module_src_dir = Path(__file__).parent.parent / "dracut_toram_module"
        
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
            self.logger.error("Could not find dracut modules directory")
            return
            
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
        
        # Don't add to config here - it's already added in _configure_dracut
        self.logger.info("Custom toram module installed successfully")
    
    def _generate_initramfs(self):
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
            
            # Try without the custom toram module if it fails
            self.logger.warning("Trying without custom toram module...")
            cmd_fallback = [
                "sudo", "chroot", str(self.chroot_path),
                "dracut", "-f",
                "--omit", "90zforge-toram",
                f"/boot/initramfs-{kernel_version}.img", kernel_version,
                "--no-hostonly"
            ]
            result = subprocess.run(cmd_fallback, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Failed to generate initramfs: {result.stderr}")
        
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