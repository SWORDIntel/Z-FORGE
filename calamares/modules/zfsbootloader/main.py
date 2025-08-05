#!/usr/bin/env python3
"""
ZFS Bootloader Configuration Module for Calamares
Configures bootloader for ZFS root systems
"""

import os
import subprocess
from typing import Dict, Optional

class ZfsbootloaderJob:
    """Calamares job for configuring ZFS bootloader"""
    
    def __init__(self):
        self.config = {}
        self.root_pool = 'rpool'
        self.boot_device = '/dev/sda'
        
    def configure_grub_zfs(self) -> bool:
        """Configure GRUB for ZFS boot"""
        try:
            # Update GRUB configuration for ZFS
            grub_config = """
# ZFS Boot Configuration
GRUB_CMDLINE_LINUX="root=ZFS={pool}/ROOT/debian"
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"
GRUB_TERMINAL=console
""".format(pool=self.root_pool)
            
            # Write GRUB defaults
            grub_defaults = "/target/etc/default/grub"
            if os.path.exists(grub_defaults):
                with open(grub_defaults, 'a') as f:
                    f.write(grub_config)
            
            # Install GRUB to boot device
            subprocess.run([
                'chroot', '/target',
                'grub-install', self.boot_device
            ], check=True)
            
            # Update GRUB configuration
            subprocess.run([
                'chroot', '/target',
                'update-grub'
            ], check=True)
            
            return True
            
        except Exception as e:
            print(f"Error configuring GRUB: {e}")
            return False
    
    def configure_zfs_initramfs(self) -> bool:
        """Configure initramfs for ZFS"""
        try:
            # Ensure ZFS is included in initramfs
            initramfs_config = "/target/etc/initramfs-tools/modules"
            if os.path.exists(os.path.dirname(initramfs_config)):
                with open(initramfs_config, 'a') as f:
                    f.write("\n# ZFS modules\n")
                    f.write("zfs\n")
            
            # Update initramfs
            subprocess.run([
                'chroot', '/target',
                'update-initramfs', '-u', '-k', 'all'
            ], check=True)
            
            return True
            
        except Exception as e:
            print(f"Error configuring initramfs: {e}")
            return False
    
    def configure_systemd_boot(self) -> bool:
        """Configure systemd-boot for ZFS (UEFI systems)"""
        try:
            # Check if system is UEFI
            if not os.path.exists('/sys/firmware/efi'):
                return True  # Skip for BIOS systems
            
            # Create systemd-boot entry
            entry_config = """
title   Debian GNU/Linux
linux   /vmlinuz
initrd  /initrd.img
options root=ZFS={pool}/ROOT/debian rw quiet splash
""".format(pool=self.root_pool)
            
            entry_file = "/target/boot/efi/loader/entries/debian.conf"
            os.makedirs(os.path.dirname(entry_file), exist_ok=True)
            
            with open(entry_file, 'w') as f:
                f.write(entry_config)
            
            return True
            
        except Exception as e:
            print(f"Error configuring systemd-boot: {e}")
            return False
    
    def run(self) -> Optional[str]:
        """Main execution method for Calamares"""
        try:
            print("Configuring bootloader for ZFS...")
            
            # Configure GRUB
            if not self.configure_grub_zfs():
                return "Failed to configure GRUB for ZFS"
            
            # Configure initramfs
            if not self.configure_zfs_initramfs():
                return "Failed to configure initramfs for ZFS"
            
            # Configure systemd-boot if UEFI
            if not self.configure_systemd_boot():
                return "Failed to configure systemd-boot"
            
            print("ZFS bootloader configuration complete")
            return None  # Success
            
        except Exception as e:
            return f"Failed to configure ZFS bootloader: {str(e)}"

# Module metadata
def main():
    """Entry point for testing"""
    job = ZfsbootloaderJob({'rootPool': 'rpool', 'bootDevice': '/dev/sda'})
    print("ZFS bootloader module initialized")

if __name__ == "__main__":
    main()
