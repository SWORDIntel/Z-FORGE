#!/usr/bin/env python3
import os
import shutil
import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional

# Try to import tqdm, but make it optional
try:
    from tqdm import tqdm
except ImportError:
    # Fallback to simple iteration
    tqdm = lambda x, **kwargs: x

from builder.core.lockfile import BuildLockfile

class BootloaderSetup:
    """
    Configures bootloader to load an encrypted ZFS root using zfsbootmenu or OpenCore chainloading
    with native ZFS full-disk encryption (no LUKS).

    Config keys:
      - loader: "zfsbootmenu" or "opencore"
      - efi_partition: "/dev/sdXY"             # EFI partition device
      - efi_mountpoint: "/boot/efi"            # mountpoint for EFI
      - zfs_pool: "rpool"                       # ZFS root pool name
      - framebuffer: optional framebuffer args  # e.g. "video=efifb"
      - opencore_efi: "/boot/efi/EFI/OC/OpenCore.efi"  # if loader=="opencore"
    """

    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        logging.basicConfig(level=logging.INFO,
                            format="%(asctime)s %(levelname)s %(message)s")

    def _run(self, cmd):
        try:
            self.logger.debug(f"Running: {' '.join(cmd)}")
            subprocess.run(cmd, check=True, timeout=30)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Bootloader command failed: {e}")
            raise

    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[BuildLockfile] = None) -> Dict:
        self.logger.info("=== BootloaderSetup start ===")
        
        # Check if we're building an ISO (no partitions available)
        is_iso_build = self.config.get('builder_config', {}).get('output_iso_name') is not None
        if is_iso_build:
            self.logger.info("ISO build detected - skipping bootloader setup (will be handled by ISO generation)")
            return {
                'status': 'success',
                'message': 'Skipped for ISO build',
                'skipped': True
            }
        
        resume = resume_data or {}
        result = {"completed_steps": []}

        try:
            # Step 1: Mount EFI partition
            if "mount_efi" not in resume:
                efi_dev = self.config.get("efi_partition")
                if not efi_dev:
                    return {
                        'status': 'error',
                        'error': "efi_partition not specified in config",
                        'module': self.__class__.__name__
                    }
                mount_pt = self.config.get("efi_mountpoint", "/boot/efi")
                os.makedirs(mount_pt, exist_ok=True)
                self._run(["mount", efi_dev, mount_pt])
                self.logger.info(f"Mounted EFI partition {efi_dev} at {mount_pt}.")
                result["completed_steps"].append("mount_efi")

            loader = self.config.get("loader", "zfsbootmenu").lower()
            framebuffer = self.config.get("framebuffer", "")
            zpool = self.config.get("zfs_pool")
            if not zpool:
                return {
                    'status': 'error',
                    'error': "zfs_pool not specified in config",
                    'module': self.__class__.__name__
                }

            # Build kernel options for native ZFS encryption unlock
            profile_name = self.config.get("hardening_profile", "UNCLASS").upper()

            profiles = {
                "UNCLASS": [
                    "slab_nomerge",
                    "init_on_alloc=1",
                ],
                "CLASSIFIED": [
                    "slab_nomerge",
                    "init_on_alloc=1",
                    "lockdown=confidentiality",
                ],
                "TS": [
                    "slab_nomerge",
                    "init_on_alloc=1",
                    "lockdown=confidentiality",
                    "mce=off",
                    "page_alloc.shuffle=1",
                ]
            }

            kernel_opts = profiles.get(profile_name, profiles["UNCLASS"])
            self.logger.info(f"Applying '{profile_name}' kernel hardening profile.")

            if framebuffer:
                kernel_opts.append(framebuffer)
            # zfsbootmenu handles dataset passphrase prompts natively
            kernel_opts.append(f"root=ZFS={zpool}")

            # Configure loader
            if loader == "zfsbootmenu":
                if "install_zbm" not in resume:
                    # Install zfsbootmenu EFI binary
                    # Check in chroot first, then fall back to host
                    src = None
                    chroot_src = self.workspace / "chroot" / "usr/bin/zfsbootmenu.efi"
                    host_src = Path("/usr/bin/zfsbootmenu.efi")
                    
                    if chroot_src.exists():
                        src = str(chroot_src)
                    elif host_src.exists():
                        src = str(host_src)
                    else:
                        return {
                            'status': 'error',
                            'error': "zfsbootmenu.efi not found in chroot or host",
                            'module': self.__class__.__name__
                        }
                    dst = Path(self.config.get("efi_mountpoint", "/boot/efi")) / "EFI" / "zfsbootmenu" / "zfsbootmenu.efi"
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    self.logger.info(f"Copied zfsbootmenu EFI to {dst}.")
                    result["completed_steps"].append("install_zbm")

                if "create_zbm_entry" not in resume:
                    # Create EFI boot entry via efibootmgr
                    label = "ZFSBootMenu"
                    # EFI path uses backslashes
                    path = "\\EFI\\zfsbootmenu\\zfsbootmenu.efi"
                    opts = ' '.join(kernel_opts)
                    self._run([
                        "efibootmgr", "-c",
                        "-d", self.config.get("efi_partition", ""),
                        "-p", self.config.get("efi_partition_number", "1"),
                        "-L", label,
                        "-l", path,
                        "-u", opts
                    ])
                    self.logger.info("Created EFI boot entry for zfsbootmenu.")
                    result["completed_steps"].append("create_zbm_entry")

            elif loader == "opencore":
                # Chainload OpenCore, then zfsbootmenu
                if "install_oc" not in resume:
                    oc_src = self.config.get("opencore_efi")
                    oc_dst = Path(self.config.get("efi_mountpoint", "/boot/efi")) / "EFI" / "BOOT" / "BOOTX64.EFI"
                    oc_dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(oc_src, oc_dst)
                    self.logger.info(f"Installed OpenCore to {oc_dst}.")
                    result["completed_steps"].append("install_oc")

                if "create_oc_entry" not in resume:
                    label = "OpenCore"
                    path = "\\EFI\\BOOT\\BOOTX64.EFI"
                    # OpenCore reads its own config; no kernel options here
                    self._run([
                        "efibootmgr", "-c",
                        "-d", self.config.get("efi_partition", ""),
                        "-p", self.config.get("efi_partition_number", "1"),
                        "-L", label,
                        "-l", path
                    ])
                    self.logger.info("Created EFI boot entry for OpenCore.")
                    result["completed_steps"].append("create_oc_entry")

            else:
                self.logger.error(f"Unsupported loader specified: {loader}")
                return {
                    'status': 'error',
                    'error': f"Unsupported loader specified: {loader}",
                    'module': self.__class__.__name__
                }

            self.logger.info("=== BootloaderSetup complete ===")
            return {
                'status': 'success',
                **result
            }
            
        except Exception as e:
            self.logger.error(f"BootloaderSetup failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }

