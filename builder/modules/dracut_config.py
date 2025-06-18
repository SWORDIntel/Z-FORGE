#!/usr/bin/env python3
# z-forge/builder/modules/dracut_config.py

"""
Dracut Configuration Module
Ensures dracut is properly installed and configured for ZFS
"""

import subprocess
from pathlib import Path
from typing import Dict, Optional
import logging

class DracutConfig:
    """Handles dracut installation and configuration"""
    
    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"
        
    def execute(self, resume_data: Optional[Dict] = None) -> Dict:
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
    
    def _remove_initramfs_tools(self):
        """Remove initramfs-tools if installed"""
        
        self.logger.info("Removing initramfs-tools...")
        
        subprocess.run([
            "chroot", str(self.chroot_path),
            "apt-get", "remove", "-y", "initramfs-tools"
        ], check=False)  # Don't fail if initramfs-tools isn't installed
    
    def _install_dracut(self):
        """Install dracut packages"""
        
        self.logger.info("Installing dracut packages...")
        
        subprocess.run([
            "chroot", str(self.chroot_path),
            "apt-get", "install", "-y",
            "dracut",
            "dracut-core",
            "dracut-network",
            "dracut-squash"
        ], check=True)
    
    def _configure_dracut(self):
        """Configure dracut"""
        
        self.logger.info("Configuring dracut...")
        
        # Create main dracut configuration
        dracut_conf = """# Z-Forge dracut configuration

# Compression method
compress="zstd"

# Include extra modules for ZFS support
add_dracutmodules+=" zfs "

# Include necessary filesystem modules
filesystems+=" zfs "

# Include systemd support
add_dracutmodules+=" systemd "

# Enable hostonly mode for better performance
hostonly="yes"

# Add kernel command line parameters
kernel_cmdline="root=zfs:AUTO"

# Include any additional drivers needed for NVMe
add_drivers+=" nvme "
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
    
    def _generate_initramfs(self):
        """Generate initramfs with dracut"""
        
        self.logger.info("Generating initramfs with dracut...")
        
        # Find installed kernel
        kernel_version_cmd = "ls -1 /lib/modules | tail -1"
        result = subprocess.run(
            ["chroot", str(self.chroot_path), "bash", "-c", kernel_version_cmd],
            capture_output=True,
            text=True,
            check=True
        )
        
        kernel_version = result.stdout.strip()
        
        if not kernel_version:
            raise Exception("No kernel modules found")
        
        self.logger.info(f"Regenerating initramfs for kernel {kernel_version}")
        
        # Generate initramfs
        subprocess.run([
            "chroot", str(self.chroot_path),
            "dracut", "-f", f"/boot/initramfs-{kernel_version}.img", kernel_version,
            "--force", "--verbose"
        ], check=True)
        
        # Create symbolic link for compatibility
        subprocess.run([
            "chroot", str(self.chroot_path),
            "ln", "-sf", f"initramfs-{kernel_version}.img", f"/boot/initrd.img-{kernel_version}"
        ], check=True)
    
    def _get_dracut_version(self):
        """Get installed dracut version"""
        
        result = subprocess.run(
            ["chroot", str(self.chroot_path), "dracut", "--version"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        return "unknown"
