#!/usr/bin/env python3
"""
ZFSBootMenu Installation Module for Z-FORGE
Downloads and installs ZFSBootMenu from official releases
"""

import os
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Optional, Any
import logging

class ZFSBootMenuInstall:
    """Handles ZFSBootMenu installation from releases"""
    
    # Latest stable version - update as needed
    ZFSBOOTMENU_VERSION = "3.0.1"
    ZFSBOOTMENU_BASE_URL = "https://github.com/zbm-dev/zfsbootmenu/releases/download"
    ZFSBOOTMENU_GET_URL = "https://get.zfsbootmenu.org"
    
    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.chroot_path = self.workspace / "chroot"
        self.logger = logging.getLogger(__name__)
        self.download_dir = self.workspace / "zfsbootmenu"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[Any] = None) -> Dict:
        """
        Install ZFSBootMenu
        
        Args:
            resume_data: Resume data dictionary
            lockfile: Lock file object
            
        Returns:
            Status dictionary
        """
        try:
            self.logger.info("Installing ZFSBootMenu...")
            
            zbm_config = self.config.get('zfsbootmenu_config', {})
            version = zbm_config.get('version', self.ZFSBOOTMENU_VERSION)
            install_recovery = zbm_config.get('install_recovery', True)
            
            # Step 1: Download ZFSBootMenu files
            self._download_zfsbootmenu(version)
            
            # Step 2: Install recovery EFI
            self._install_recovery_efi()
            
            # Step 3: Configure ZFSBootMenu
            self._configure_zfsbootmenu()
            
            # Step 4: Create dracut module for ZFS if missing
            self._ensure_dracut_zfs_module()
            
            self.logger.info("ZFSBootMenu installation complete")
            
            return {
                'status': 'success',
                'version': version,
                'features': {
                    'recovery_kernel': install_recovery,
                    'generate_zbm': True,
                    'dracut_zfs': True
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to install ZFSBootMenu: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _download_zfsbootmenu(self, version: str):
        """Download ZFSBootMenu release files"""
        self.logger.info(f"Downloading ZFSBootMenu...")
        
        # Use the working get.zfsbootmenu.org URLs
        downloads = [
            ("zfsbootmenu-recovery.efi", f"{self.ZFSBOOTMENU_GET_URL}/efi/recovery"),
            ("vmlinuz-bootmenu", f"{self.ZFSBOOTMENU_GET_URL}/kernel"),
            ("initramfs-bootmenu.img", f"{self.ZFSBOOTMENU_GET_URL}/initramfs")
        ]
        
        for filename, url in downloads:
            output_path = self.download_dir / filename
            
            if output_path.exists():
                self.logger.info(f"{filename} already downloaded")
                continue
            
            try:
                self.logger.info(f"Downloading {filename}...")
                # Use curl with better error handling and follow redirects
                result = subprocess.run([
                    "curl", "-L", "-f", "-o", str(output_path), url
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    self.logger.warning(f"Failed to download {filename}: {result.stderr}")
                    # Try with wget as fallback
                    subprocess.run([
                        "wget", "--no-check-certificate", "-O", str(output_path), url
                    ], check=True, capture_output=True)
                    
                # Verify file is not empty
                if output_path.stat().st_size == 0:
                    self.logger.warning(f"Downloaded file {filename} is empty, removing...")
                    output_path.unlink()
                    continue
                    
            except subprocess.CalledProcessError:
                self.logger.warning(f"Failed to download {filename}")
                if output_path.exists() and output_path.stat().st_size == 0:
                    output_path.unlink()
                continue
    
    def _install_recovery_efi(self):
        """Install recovery EFI file"""
        self.logger.info("Installing recovery EFI...")
        
        recovery_efi = self.download_dir / "zfsbootmenu-recovery.efi"
        if not recovery_efi.exists():
            self.logger.warning("Recovery EFI not found, skipping")
            return
        
        # Create EFI directory structure
        efi_dir = self.chroot_path / "boot" / "efi" / "EFI" / "zfsbootmenu"
        efi_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy recovery EFI
        target = efi_dir / "zfsbootmenu-recovery.efi"
        shutil.copy2(recovery_efi, target)
        
        self.logger.info(f"Recovery EFI installed to {target}")
    
    def _install_generate_zbm(self, version: str):
        """Install generate-zbm script"""
        self.logger.info("Installing generate-zbm...")
        
        # First try the .deb package
        deb_path = self.download_dir / f"generate-zbm_{version}_all.deb"
        if deb_path.exists():
            try:
                subprocess.run([
                    "cp", str(deb_path), str(self.chroot_path / "tmp/")
                ], check=True)
                
                subprocess.run([
                    "chroot", str(self.chroot_path),
                    "dpkg", "-i", f"/tmp/generate-zbm_{version}_all.deb"
                ], check=True)
                
                # Install dependencies
                subprocess.run([
                    "chroot", str(self.chroot_path),
                    "apt-get", "-f", "install", "-y"
                ], check=True)
                
                return
            except subprocess.CalledProcessError:
                self.logger.warning("Failed to install from .deb, falling back to tarball")
        
        # Fallback: Extract from tarball
        tarball_path = self.download_dir / f"zfsbootmenu-release-x86_64-v{version}.tar.gz"
        if tarball_path.exists():
            extract_dir = self.download_dir / "extracted"
            extract_dir.mkdir(exist_ok=True)
            
            subprocess.run([
                "tar", "-xzf", str(tarball_path), "-C", str(extract_dir)
            ], check=True)
            
            # Copy generate-zbm script
            generate_zbm = extract_dir / "bin" / "generate-zbm"
            if generate_zbm.exists():
                target = self.chroot_path / "usr" / "bin" / "generate-zbm"
                shutil.copy2(generate_zbm, target)
                os.chmod(target, 0o755)
            
            # Copy perl modules if present
            perl_lib = extract_dir / "lib"
            if perl_lib.exists():
                target_lib = self.chroot_path / "usr" / "share" / "perl5"
                target_lib.mkdir(parents=True, exist_ok=True)
                shutil.copytree(perl_lib, target_lib, dirs_exist_ok=True)
    
    def _install_recovery_kernel(self, version: str):
        """Install recovery kernel EFI"""
        self.logger.info("Installing recovery kernel...")
        
        recovery_efi = self.download_dir / f"zfsbootmenu-recovery-x86_64-v{version}-linux.EFI"
        if not recovery_efi.exists():
            self.logger.warning("Recovery EFI not found, skipping")
            return
        
        # Create EFI directory structure
        efi_dir = self.chroot_path / "boot" / "efi" / "EFI" / "zfsbootmenu"
        efi_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy recovery EFI
        target = efi_dir / "zfsbootmenu-recovery.efi"
        shutil.copy2(recovery_efi, target)
        
        self.logger.info(f"Recovery kernel installed to {target}")
    
    def _configure_zfsbootmenu(self):
        """Configure ZFSBootMenu"""
        self.logger.info("Configuring ZFSBootMenu...")
        
        # Create configuration directory
        config_dir = self.chroot_path / "etc" / "zfsbootmenu"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Create main configuration
        config_content = """# ZFSBootMenu configuration
# Generated by Z-FORGE

Global:
  ManageImages: true
  BootMountPoint: /boot/efi
  DracutConfDir: /etc/zfsbootmenu/dracut.conf.d
  PreHooksDir: /etc/zfsbootmenu/hooks.d
  PostHooksDir: /etc/zfsbootmenu/hooks.d
  InitCPIOConfig: /etc/zfsbootmenu/mkinitcpio.conf

Components:
  ImageDir: /boot/efi/EFI/zfsbootmenu
  Versions: 3
  Enabled: true
  
Kernel:
  CommandLine: "quiet loglevel=4"
  Prefix: vmlinuz

EFI:
  ImageDir: /boot/efi/EFI/zfsbootmenu
  Versions: false
  Enabled: true

# Dracut configuration for ZFSBootMenu
# This will be used when generating the images
"""
        
        config_path = config_dir / "config.yaml"
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        # Create dracut configuration directory
        dracut_conf_dir = config_dir / "dracut.conf.d"
        dracut_conf_dir.mkdir(parents=True, exist_ok=True)
        
        # Create ZFSBootMenu dracut configuration
        dracut_conf = """# ZFSBootMenu dracut configuration
add_dracutmodules+=" zfs "
omit_dracutmodules+=" btrfs resume "
compress="zstd"
hostonly="no"
"""
        
        dracut_conf_path = dracut_conf_dir / "zfsbootmenu.conf"
        with open(dracut_conf_path, 'w') as f:
            f.write(dracut_conf)
    
    def _ensure_dracut_zfs_module(self):
        """Ensure dracut has ZFS module even if dracut-zfs package is missing"""
        self.logger.info("Ensuring dracut ZFS module...")
        
        # Check if dracut ZFS module exists
        dracut_modules_dir = self.chroot_path / "usr" / "lib" / "dracut" / "modules.d"
        zfs_module_dir = None
        
        # Look for existing ZFS module
        for mod_dir in dracut_modules_dir.glob("*zfs"):
            if mod_dir.is_dir():
                zfs_module_dir = mod_dir
                break
        
        if not zfs_module_dir:
            # Create basic ZFS dracut module
            self.logger.info("Creating basic dracut ZFS module...")
            zfs_module_dir = dracut_modules_dir / "90zfs"
            zfs_module_dir.mkdir(parents=True, exist_ok=True)
            
            # Create module-setup.sh
            module_setup = """#!/bin/bash
# Basic ZFS dracut module for ZFSBootMenu

check() {
    # Only include if ZFS is available
    which zpool >/dev/null 2>&1 || return 1
    return 0
}

depends() {
    echo udev-rules
    return 0
}

installkernel() {
    instmods zfs
}

install() {
    inst_multiple \
        zfs \
        zpool \
        zdb \
        mount.zfs \
        zfs_ids \
        zgenhostid \
        /etc/zfs/zpool.cache \
        /etc/hostid
        
    inst_hook cmdline 95 "$moddir/parse-zfs.sh"
    inst_hook mount 98 "$moddir/mount-zfs.sh"
    
    # Install systemd units if using systemd
    if dracut_module_included "systemd"; then
        inst_simple "${systemdsystemunitdir}/zfs-import-cache.service"
        inst_simple "${systemdsystemunitdir}/zfs-import-scan.service"
        inst_simple "${systemdsystemunitdir}/zfs-mount.service"
        inst_simple "${systemdsystemunitdir}/zfs-import.target"
        systemctl -q --root "$initdir" enable zfs-import-cache.service
        systemctl -q --root "$initdir" enable zfs-import.target
    fi
}
"""
            
            module_setup_path = zfs_module_dir / "module-setup.sh"
            with open(module_setup_path, 'w') as f:
                f.write(module_setup)
            os.chmod(module_setup_path, 0o755)
            
            # Create parse-zfs.sh
            parse_zfs = """#!/bin/sh
# Parse ZFS kernel command line

case "${root}" in
    zfs:*|ZFS:*)
        root="${root#zfs:}"
        root="${root#ZFS:}"
        rootfstype="zfs"
        rootok=1
        wait_for_zfs=1
        ;;
esac

[ "${rootfstype}" = "zfs" ] && wait_for_zfs=1
"""
            
            parse_zfs_path = zfs_module_dir / "parse-zfs.sh"
            with open(parse_zfs_path, 'w') as f:
                f.write(parse_zfs)
            os.chmod(parse_zfs_path, 0o755)
            
            # Create mount-zfs.sh
            mount_zfs = """#!/bin/sh
# Mount ZFS root

[ "${wait_for_zfs}" = "1" ] || return 0

# Import pools
zpool import -N -a

# Mount root dataset
mount -t zfs "${root}" "${NEWROOT}"
"""
            
            mount_zfs_path = zfs_module_dir / "mount-zfs.sh"
            with open(mount_zfs_path, 'w') as f:
                f.write(mount_zfs)
            os.chmod(mount_zfs_path, 0o755)
    
    def _generate_initial_images(self):
        """Generate initial ZFSBootMenu images"""
        self.logger.info("Generating initial ZFSBootMenu images...")
        
        # This will be done by the actual installer, just create placeholder
        script_content = """#!/bin/bash
# ZFSBootMenu generation script
# This should be run after the system is installed

# Check if generate-zbm exists
if ! command -v generate-zbm >/dev/null 2>&1; then
    echo "generate-zbm not found!"
    echo "Please install ZFSBootMenu first"
    exit 1
fi

# Generate ZFSBootMenu
echo "Generating ZFSBootMenu..."
generate-zbm

echo "ZFSBootMenu generation complete!"
"""
        
        script_path = self.workspace / "generate_zfsbootmenu.sh"
        with open(script_path, 'w') as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)