#!/usr/bin/env python3
"""
ZFS Encryption Module for Z-FORGE
Handles ZFS native encryption setup and key management
"""

import os
import subprocess
import secrets
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging

class ZfsEncryption:
    """Handles ZFS native encryption configuration"""
    
    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.chroot_path = self.workspace / "chroot"
        self.logger = logging.getLogger(__name__)
        self.key_directory = self.workspace / "keys"
        self.key_directory.mkdir(parents=True, exist_ok=True)
        
    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[Any] = None) -> Dict:
        """
        Configure ZFS encryption support
        
        Args:
            resume_data: Resume data dictionary
            lockfile: Lock file object
            
        Returns:
            Status dictionary
        """
        try:
            self.logger.info("Configuring ZFS encryption support...")
            
            encryption_config = self.config.get('encryption_config', {})
            enable_encryption = encryption_config.get('enable', True)
            key_format = encryption_config.get('key_format', 'raw')  # raw or passphrase
            cipher = encryption_config.get('cipher', 'aes-256-gcm')
            
            if not enable_encryption:
                self.logger.info("Encryption disabled in configuration")
                return {
                    'status': 'success',
                    'encryption_enabled': False
                }
            
            # Step 1: Generate encryption keys
            key_path = self._generate_encryption_key(key_format)
            
            # Step 2: Install encryption dependencies
            self._install_encryption_dependencies()
            
            # Step 3: Configure dracut for encryption
            self._configure_dracut_encryption()
            
            # Step 4: Create ZFS pool creation script with encryption
            self._create_encrypted_pool_script(cipher, key_format, key_path)
            
            # Step 5: Setup key management for boot
            self._setup_boot_key_management(key_path)
            
            # Step 6: Configure ZFSBootMenu for encryption
            self._configure_zfsbootmenu_encryption()
            
            self.logger.info("ZFS encryption configuration complete")
            
            return {
                'status': 'success',
                'encryption_enabled': True,
                'cipher': cipher,
                'key_format': key_format,
                'key_path': str(key_path),
                'features': {
                    'zfs_native_encryption': True,
                    'boot_time_unlock': True,
                    'emergency_recovery': True
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to configure ZFS encryption: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _generate_encryption_key(self, key_format: str) -> Path:
        """Generate encryption key or passphrase"""
        self.logger.info(f"Generating {key_format} encryption key...")
        
        if key_format == 'raw':
            # Generate 32-byte random key for AES-256
            key_data = secrets.token_bytes(32)
            key_path = self.key_directory / "zroot.key"
            
            with open(key_path, 'wb') as f:
                f.write(key_data)
            
            # Set restrictive permissions
            os.chmod(key_path, 0o400)
            
        elif key_format == 'passphrase':
            # Generate strong passphrase
            passphrase = secrets.token_urlsafe(32)
            key_path = self.key_directory / "zroot.passphrase"
            
            with open(key_path, 'w') as f:
                f.write(passphrase)
            
            os.chmod(key_path, 0o400)
        
        else:
            raise ValueError(f"Unknown key format: {key_format}")
        
        self.logger.info(f"Encryption key saved to {key_path}")
        return key_path
    
    def _install_encryption_dependencies(self):
        """Install packages needed for ZFS encryption"""
        self.logger.info("Installing encryption dependencies...")
        
        packages = [
            "cryptsetup",
            "cryptsetup-initramfs",
            "keyutils",
            "libpam-zfs"
        ]
        
        cmd = ["chroot", str(self.chroot_path), "apt-get", "install", "-y"] + packages
        subprocess.run(cmd, check=True)
    
    def _configure_dracut_encryption(self):
        """Configure dracut for ZFS encryption support"""
        self.logger.info("Configuring dracut for encryption...")
        
        dracut_conf = """# ZFS encryption support
add_dracutmodules+=" zfs-crypt crypt crypt-gpg "
install_items+=" /usr/bin/zfs /usr/bin/zpool /lib/*/libicp.so* /lib/*/libzfs_core.so* "
"""
        
        conf_path = self.chroot_path / "etc" / "dracut.conf.d" / "zfs-encryption.conf"
        conf_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(conf_path, 'w') as f:
            f.write(dracut_conf)
    
    def _create_encrypted_pool_script(self, cipher: str, key_format: str, key_path: Path):
        """Create script for creating encrypted ZFS pool"""
        self.logger.info("Creating encrypted pool creation script...")
        
        if key_format == 'raw':
            key_option = f"-O keyformat=raw -O keylocation=file://{key_path}"
        else:
            key_option = f"-O keyformat=passphrase -O keylocation=file://{key_path}"
        
        script_content = f"""#!/bin/bash
# ZFS Encrypted Pool Creation Script
# Generated by Z-FORGE

set -e

POOL_NAME="${{1:-zroot}}"
DISK="${{2}}"

if [ -z "$DISK" ]; then
    echo "Usage: $0 <pool_name> <disk>"
    echo "Example: $0 zroot /dev/nvme0n1"
    exit 1
fi

echo "Creating encrypted ZFS pool '$POOL_NAME' on $DISK..."

# Wipe disk
wipefs -af "$DISK"
sgdisk --zap-all "$DISK"

# Create partitions
echo "Creating partitions..."
sgdisk -n1:1M:+1G -t1:EF00 "$DISK"  # EFI partition
sgdisk -n2:0:+4G -t2:BE00 "$DISK"   # Boot pool partition  
sgdisk -n3:0:0 -t3:BF00 "$DISK"     # Root pool partition

# Wait for partitions
sleep 2
partprobe "$DISK"
sleep 2

# Format EFI partition
echo "Formatting EFI partition..."
mkfs.vfat -F32 -n EFI "${{DISK}}-part1" || mkfs.vfat -F32 -n EFI "${{DISK}}p1"

# Create boot pool (unencrypted for ZFSBootMenu)
echo "Creating boot pool..."
zpool create -f \\
    -o ashift=12 \\
    -o autotrim=on \\
    -O acltype=posixacl \\
    -O compression=lz4 \\
    -O normalization=formD \\
    -O relatime=on \\
    -O xattr=sa \\
    -O mountpoint=/boot \\
    -R /mnt \\
    bpool "${{DISK}}-part2" || bpool "${{DISK}}p2"

# Create encrypted root pool
echo "Creating encrypted root pool..."
zpool create -f \\
    -o ashift=12 \\
    -o autotrim=on \\
    -O acltype=posixacl \\
    -O compression=zstd \\
    -O dnodesize=auto \\
    -O normalization=formD \\
    -O relatime=on \\
    -O xattr=sa \\
    -O encryption={cipher} \\
    {key_option} \\
    -O mountpoint=/ \\
    -R /mnt \\
    "$POOL_NAME" "${{DISK}}-part3" || "$POOL_NAME" "${{DISK}}p3"

# Create datasets
echo "Creating datasets..."
zfs create -o mountpoint=none "$POOL_NAME/ROOT"
zfs create -o mountpoint=/ "$POOL_NAME/ROOT/debian"
zfs create -o mountpoint=/home "$POOL_NAME/home"
zfs create -o mountpoint=/var "$POOL_NAME/var"
zfs create -o mountpoint=/var/log "$POOL_NAME/var/log"

# Create boot datasets
zfs create -o mountpoint=/boot bpool/BOOT
zfs create -o mountpoint=/boot/efi bpool/BOOT/EFI

# Mount EFI
mkdir -p /mnt/boot/efi
mount "${{DISK}}-part1" /mnt/boot/efi || mount "${{DISK}}p1" /mnt/boot/efi

echo "Encrypted ZFS pool created successfully!"
echo "Root pool: $POOL_NAME (encrypted with {cipher})"
echo "Boot pool: bpool (unencrypted)"
"""
        
        script_path = self.workspace / "create_encrypted_pool.sh"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        os.chmod(script_path, 0o755)
        
        # Also copy to chroot
        chroot_script = self.chroot_path / "usr" / "local" / "bin" / "create_encrypted_pool.sh"
        shutil.copy2(script_path, chroot_script)
    
    def _setup_boot_key_management(self, key_path: Path):
        """Setup key management for boot time"""
        self.logger.info("Setting up boot-time key management...")
        
        # Copy key to chroot
        chroot_key_dir = self.chroot_path / "etc" / "zfs"
        chroot_key_dir.mkdir(parents=True, exist_ok=True)
        
        chroot_key_path = chroot_key_dir / key_path.name
        shutil.copy2(key_path, chroot_key_path)
        os.chmod(chroot_key_path, 0o400)
        
        # Create systemd service for early key loading
        service_content = """[Unit]
Description=Load ZFS encryption keys
DefaultDependencies=no
Before=zfs-import.target
After=zfs-load-module.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/zfs load-key -a

[Install]
WantedBy=zfs-import.target
"""
        
        service_path = self.chroot_path / "etc" / "systemd" / "system" / "zfs-load-keys.service"
        with open(service_path, 'w') as f:
            f.write(service_content)
        
        # Enable service
        cmd = ["chroot", str(self.chroot_path), "systemctl", "enable", "zfs-load-keys.service"]
        subprocess.run(cmd, check=False)  # Don't fail if systemd not available
    
    def _configure_zfsbootmenu_encryption(self):
        """Configure ZFSBootMenu for encrypted pools"""
        self.logger.info("Configuring ZFSBootMenu for encryption...")
        
        # Create ZFSBootMenu hook for encryption
        hook_content = """#!/bin/bash
# ZFSBootMenu encryption hook

# Function to unlock encrypted datasets
zfs_unlock_datasets() {
    local pool="$1"
    
    # Check if pool has encrypted datasets
    if zfs list -H -o encryption,keystatus "$pool" | grep -q "^aes.*unavailable"; then
        echo "Encrypted datasets found in $pool"
        
        # Try to load keys from standard locations
        for keyfile in /etc/zfs/*.key /boot/*.key; do
            if [ -f "$keyfile" ]; then
                echo "Trying key: $keyfile"
                zfs load-key -L "file://$keyfile" "$pool" 2>/dev/null && break
            fi
        done
        
        # If still locked, prompt for passphrase
        if zfs list -H -o keystatus "$pool" | grep -q "unavailable"; then
            echo "Please enter passphrase for $pool:"
            zfs load-key "$pool"
        fi
    fi
}

# Hook into ZFSBootMenu
case "$1" in
    pre-import)
        # Nothing needed pre-import
        ;;
    post-import)
        # Unlock datasets after import
        for pool in $(zpool list -H -o name); do
            zfs_unlock_datasets "$pool"
        done
        ;;
esac
"""
        
        hook_path = self.chroot_path / "etc" / "zfsbootmenu" / "hooks" / "encryption.sh"
        hook_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(hook_path, 'w') as f:
            f.write(hook_content)
        
        os.chmod(hook_path, 0o755)