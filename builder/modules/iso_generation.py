import logging
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Optional

class ISOGeneration:
    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"

    def execute(self, resume_data: Optional[Dict] = None) -> Dict:
        self.logger.info("Checking for required tools (xorriso, mksquashfs)...")

        required_tools = ["xorriso", "mksquashfs"]
        missing_tools = []
        for tool in required_tools:
            if not shutil.which(tool):
                missing_tools.append(tool)

        if missing_tools:
            error_msg = f"Missing required tools: {', '.join(missing_tools)}. Please install them and try again."
            self.logger.error(error_msg)
            return {'status': 'error', 'error': error_msg, 'module': self.__class__.__name__}

        self.logger.info("Required tools found.")

        self.logger.info("Preparing ISO staging directory...")
        self.iso_staging_path = self.workspace / "iso_staging"

        # Clean up any previous staging directory
        if self.iso_staging_path.exists():
            self.logger.info(f"Removing existing staging directory: {self.iso_staging_path}")
            shutil.rmtree(self.iso_staging_path)

        self.iso_staging_path.mkdir(parents=True)
        self.logger.info(f"Created ISO staging directory: {self.iso_staging_path}")

        # Create common subdirectories for ISO structure
        # (e.g., for bootloader, live filesystem image)
        # Standard live CD structure often includes 'boot', 'live', 'isolinux' (for BIOS GRUB/Syslinux), 'EFI'

        (self.iso_staging_path / "boot").mkdir()
        (self.iso_staging_path / "boot" / "grub").mkdir() # For GRUB config and modules
        (self.iso_staging_path / "live").mkdir()          # For the SquashFS image
        (self.iso_staging_path / "EFI" / "BOOT").mkdir(parents=True, exist_ok=True) # For UEFI bootloader

        self.logger.info("ISO staging directory structure created.")

        self.logger.info("Packaging chroot into SquashFS image...")

        # Path to the chroot directory (source)
        # self.chroot_path should already be defined in __init__ as self.workspace / "chroot"

        # Path for the output SquashFS file
        squashfs_image_path = self.iso_staging_path / "live" / "filesystem.squashfs"

        # mksquashfs command
        # We need to exclude pseudo-filesystems and potentially other temporary files.
        # Common exclusions: /proc, /sys, /dev, /tmp, /run, /media, /mnt, /var/tmp, /var/cache/apt/archives (if not already cleaned)
        # Also, the squashfs image itself if it were somehow being created inside the chroot.
        mksquashfs_cmd = [
            "mksquashfs",
            str(self.chroot_path),  # Source directory
            str(squashfs_image_path), # Output file
            "-noappend",          # Overwrite existing file
            "-e",                 # Exclude list follows
            "proc", "sys", "dev", "tmp", "run", "media", "mnt",
            "var/tmp", "var/cache/apt/archives", # Example common excludes relative to chroot root
            "tmp/zforge_workspace" # Exclude the workspace if it's mounted/linked inside chroot
        ]

        self.logger.info(f"Running mksquashfs: {' '.join(mksquashfs_cmd)}")

        try:
            # Using subprocess.run directly. Ensure errors are caught.
            # For potentially long operations, consider logging stdout/stderr periodically or on completion.
            process = subprocess.run(mksquashfs_cmd, check=True, capture_output=True, text=True)
            self.logger.info(f"mksquashfs stdout:\n{process.stdout}")
            if process.stderr: # mksquashfs often outputs stats to stderr
                self.logger.info(f"mksquashfs stderr:\n{process.stderr}")
            self.logger.info(f"SquashFS image created successfully at {squashfs_image_path}")

        except subprocess.CalledProcessError as e:
            error_msg = f"mksquashfs failed with return code {e.returncode}.\nStdout:\n{e.stdout}\nStderr:\n{e.stderr}"
            self.logger.error(error_msg)
            return {'status': 'error', 'error': error_msg, 'module': self.__class__.__name__}
        except FileNotFoundError: # If mksquashfs command itself is not found (should be caught by earlier check, but good practice)
            error_msg = "mksquashfs command not found. This should have been caught by earlier checks."
            self.logger.error(error_msg)
            return {'status': 'error', 'error': error_msg, 'module': self.__class__.__name__}

        self.logger.info("Copying kernel and initramfs to ISO staging area...")

        chroot_boot_path = self.chroot_path / "boot"
        staging_boot_path = self.iso_staging_path / "boot"

        # Find the kernel (vmlinuz-*). We need to pick one, typically the latest or a configured one.
        # For simplicity, let's try to find the most generic vmlinuz link or the latest version.
        # A more robust solution might involve getting the kernel version from KernelAcquisition module's output or config.

        kernel_files = list(chroot_boot_path.glob("vmlinuz-*"))
        initramfs_files = list(chroot_boot_path.glob("initramfs-*.img")) # Dracut uses initramfs-*.img
        # Also consider initrd.img-* if that's a symlink created by dracut_config.py
        initrd_symlinks = list(chroot_boot_path.glob("initrd.img-*"))

        if not kernel_files:
            error_msg = "No kernel (vmlinuz-*) found in chroot /boot directory."
            self.logger.error(error_msg)
            return {'status': 'error', 'error': error_msg, 'module': self.__class__.__name__}

        # Simple strategy: use the first one found or sort to get the latest.
        # Sorting them should generally put the latest version last.
        kernel_files.sort()
        selected_kernel_file = kernel_files[-1]

        # For initramfs, try to find one that matches the selected kernel version.
        # Example kernel filename: vmlinuz-5.10.0-8-amd64
        # Corresponding initramfs: initramfs-5.10.0-8-amd64.img
        kernel_version_suffix = selected_kernel_file.name.replace("vmlinuz-", "")

        selected_initramfs_file = chroot_boot_path / f"initramfs-{kernel_version_suffix}.img"
        if not selected_initramfs_file.exists():
            # Fallback: try to find any initramfs if direct match fails
            if initramfs_files:
                initramfs_files.sort()
                selected_initramfs_file = initramfs_files[-1]
                self.logger.warning(f"Could not find initramfs matching kernel {kernel_version_suffix}. Using {selected_initramfs_file.name} as fallback.")
            elif initrd_symlinks: # Check symlinks too
                 initrd_symlinks.sort()
                 # Symlinks might point to the actual initramfs, so resolve it
                 resolved_symlink = (chroot_boot_path / initrd_symlinks[-1].name).resolve()
                 if resolved_symlink.exists() and resolved_symlink.name.startswith("initramfs-"):
                     selected_initramfs_file = resolved_symlink
                     self.logger.warning(f"Could not find initramfs matching kernel {kernel_version_suffix}. Using symlinked {selected_initramfs_file.name} as fallback.")
                 else:
                    error_msg = "No initramfs (*.img or initrd.img-*) found in chroot /boot directory."
                    self.logger.error(error_msg)
                    return {'status': 'error', 'error': error_msg, 'module': self.__class__.__name__}
            else:
                error_msg = f"No initramfs found for kernel {kernel_version_suffix}, and no other initramfs files found."
                self.logger.error(error_msg)
                return {'status': 'error', 'error': error_msg, 'module': self.__class__.__name__}

        # Define destination paths in staging
        staged_kernel_path = staging_boot_path / "vmlinuz"  # Generic name for GRUB
        staged_initramfs_path = staging_boot_path / "initrd.img" # Generic name for GRUB

        try:
            self.logger.info(f"Copying {selected_kernel_file} to {staged_kernel_path}")
            shutil.copy2(selected_kernel_file, staged_kernel_path)

            self.logger.info(f"Copying {selected_initramfs_file} to {staged_initramfs_path}")
            shutil.copy2(selected_initramfs_file, staged_initramfs_path)

            self.logger.info("Kernel and initramfs copied successfully.")

        except Exception as e:
            error_msg = f"Failed to copy kernel/initramfs: {str(e)}"
            self.logger.error(error_msg)
            return {'status': 'error', 'error': error_msg, 'module': self.__class__.__name__}

        self.logger.info("Configuring GRUB for ISO boot...")

        grub_cfg_path = self.iso_staging_path / "boot" / "grub" / "grub.cfg"

        # Basic GRUB configuration for a live ISO
        # It's important that the paths to kernel (vmlinuz), initrd (initrd.img),
        # and the squashfs file (filesystem.squashfs) are correct from GRUB's perspective
        # once it's booted from the ISO.
        # The findiso parameter helps locate the .squashfs file on the ISO.
        # 'boot=live' is a common parameter for live-boot based systems.
        # Other parameters might be needed depending on the live system setup (e.g. from live-config).

        # Retrieve kernel command line parameters from config if available
        # Default from dracut_config.py was "root=zfs:AUTO", but for live ISO, it's different.
        # The live_environment.py module set LIVE_BOOT_APPEND="quiet splash"
        # We need parameters like 'boot=live', 'findiso=', potentially 'toram' later.

        # Let's construct a suitable cmdline.
        # 'findiso=/live/filesystem.squashfs' assumes the squashfs is at /live/filesystem.squashfs on the ISO.
        # 'boot=live' is standard for live-boot.
        # 'union=overlay' or 'union=aufs' might be needed if not default in live-boot.
        # 'quiet splash' are common for a cleaner boot.

        kernel_cmdline_params = [
            "boot=live",
            "findiso=/live/filesystem.squashfs", # Path to squashfs *on the ISO*
            "union=overlay", # Common for modern live systems
            "quiet",
            "splash",
            # Add any specific parameters from self.config if needed for Z-Forge live environment
            # For example, self.config.get('live_config', {}).get('kernel_append', "")
        ]
        kernel_cmdline = " ".join(kernel_cmdline_params)

        grub_cfg_content = f"""
set timeout=5
set default="0"

menuentry "Z-Forge Live" {{
    linux /boot/vmlinuz {kernel_cmdline}
    initrd /boot/initrd.img
}}

# Add other entries if needed, e.g., for memtest, EFI firmware setup
menuentry "Reboot" {{
    reboot
}}

menuentry "Shutdown" {{
    halt
}}
"""

        try:
            self.logger.info(f"Writing GRUB configuration to {grub_cfg_path}")
            with open(grub_cfg_path, "w") as f:
                f.write(grub_cfg_content)
            self.logger.info("GRUB configuration written successfully.")

        except Exception as e:
            error_msg = f"Failed to write GRUB configuration: {str(e)}"
            self.logger.error(error_msg)
            return {'status': 'error', 'error': error_msg, 'module': self.__class__.__name__}

    self.logger.info("Creating bootable ISO image with xorriso...")

    iso_output_name = self.config.get('builder_config', {}).get('output_iso_name', 'zforge-live.iso')
    final_iso_path = self.workspace / iso_output_name # Output ISO to the workspace for now

    # Ensure grubx64.efi is staged for UEFI boot
    grub_efi_file_src_path_str = "/usr/lib/grub/x86_64-efi/grubx64.efi" # Path on HOST
    grub_efi_file_src = Path(grub_efi_file_src_path_str)
    staged_grub_efi_dst = self.iso_staging_path / "EFI" / "BOOT" / "BOOTX64.EFI" # Path in ISO staging

    if not grub_efi_file_src.exists():
        error_msg = f"GRUB EFI file {grub_efi_file_src_path_str} not found on host. Cannot create UEFI bootable ISO."
        self.logger.error(error_msg)
        return {'status': 'error', 'error': error_msg, 'module': self.__class__.__name__}
    try:
        staged_grub_efi_dst.parent.mkdir(parents=True, exist_ok=True) # Ensure EFI/BOOT exists
        shutil.copy2(grub_efi_file_src, staged_grub_efi_dst)
        self.logger.info(f"Copied GRUB EFI file {grub_efi_file_src_path_str} to {staged_grub_efi_dst}")
    except Exception as e:
        error_msg = f"Failed to copy GRUB EFI file: {str(e)}"
        self.logger.error(error_msg)
        return {'status': 'error', 'error': error_msg, 'module': self.__class__.__name__}

    xorriso_cmd = [
        "xorriso",
        "-as", "mkisofs",
        "-o", str(final_iso_path),
        "-iso-level", "3", # For Joliet/Rock Ridge extensions, long filenames
        "-volid", "ZFORGE_LIVE", # Volume ID

        # UEFI Boot Configuration:
        # Specifies the EFI boot image. The file must be in the ISO at the given path.
        # BOOTX64.EFI at /EFI/BOOT/ is the standard path for removable media.
        "-eltorito-alt-boot",
        "-e", "EFI/BOOT/BOOTX64.EFI", # Path to EFI boot image *on the ISO*
        "-no-emul-boot",

        # Add all files from the staging directory to the ISO root
        # This means contents of self.iso_staging_path will be at the root of the ISO.
        str(self.iso_staging_path)
    ]

    self.logger.info(f"Running xorriso: {' '.join(xorriso_cmd)}")

    try:
        process = subprocess.run(xorriso_cmd, check=True, capture_output=True, text=True)
        self.logger.info(f"xorriso stdout:\n{process.stdout}")
        # xorriso often uses stderr for progress/info and not just errors.
        self.logger.info(f"xorriso stderr:\n{process.stderr}")
        self.logger.info(f"ISO image created successfully at {final_iso_path}")

        return {'status': 'success', 'iso_path': str(final_iso_path), 'module': self.__class__.__name__}

    except subprocess.CalledProcessError as e:
        error_msg = f"xorriso failed with return code {e.returncode}.\nCommand: {' '.join(e.cmd)}\nStdout:\n{e.stdout}\nStderr:\n{e.stderr}"
        self.logger.error(error_msg)
        if final_iso_path.exists():
            try:
                final_iso_path.unlink()
            except Exception as del_e:
                self.logger.error(f"Additionally, failed to delete partial ISO {final_iso_path}: {del_e}")
        return {'status': 'error', 'error': error_msg, 'module': self.__class__.__name__}
    except FileNotFoundError: # Should be caught by initial tool check for xorriso
        error_msg = "xorriso command not found. This should have been caught by earlier checks."
        self.logger.error(error_msg)
        return {'status': 'error', 'error': error_msg, 'module': self.__class__.__name__}
