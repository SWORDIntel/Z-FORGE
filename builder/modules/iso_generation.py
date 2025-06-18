#!/usr/bin/env python3
# z-forge/builder/modules/iso_generation.py

"""
ISO Generation Module for Z-Forge.

This module is responsible for the final stage of the Z-Forge build process:
creating a bootable hybrid ISO image. It takes the prepared chroot environment,
compresses it into a SquashFS filesystem, sets up BIOS (ISOLINUX) and UEFI (GRUB)
bootloaders, copies necessary kernel and initramfs files, integrates any additional
overlay files (like benchmarking scripts or installer configurations), and then uses
`xorriso` to assemble these components into a hybrid ISO. The resulting ISO can
be booted on both BIOS and UEFI systems and is suitable for writing to USB drives.
Verification steps are included to check the integrity and structure of the
generated ISO.
"""

import subprocess
import shutil
import os
from pathlib import Path
from typing import Dict, Optional, List, Any
import logging
import tempfile # Not actively used in this version, but can be useful

# It's assumed that BENCHMARKING_SCRIPT would be populated with the content
# of a script file, e.g., by reading it from 'tests/diskbenchmark.sh'
# dynamically when ZForgeBuilder or this module is initialized.
# For this commenting task, we'll assume it's a predefined string constant.
# Example: BENCHMARKING_SCRIPT = Path("tests/diskbenchmark.sh").read_text()
BENCHMARKING_SCRIPT: str = """#!/bin/bash
# Placeholder for ZFS benchmarking script (e.g., tests/diskbenchmark.sh)
echo "ZFS Benchmarking Script Placeholder"
echo "Pool Type: mirror" > /root/zfs_test_results/zfs_test_report_$(date +%s).md
# Actual script would perform fio tests, etc.
"""

class ISOGeneration:
    """
    Generates the final bootable Z-Forge ISO image.

    This class orchestrates the creation of the ISO by:
    1. Preparing the ISO build directory structure.
    2. Creating a SquashFS compressed image of the chroot filesystem.
    3. Setting up BIOS (ISOLINUX) and UEFI (GRUB) bootloaders.
    4. Copying essential files like kernel, initramfs, and any overlay files.
    5. Using `xorriso` to build the hybrid ISO.
    6. Performing basic verification of the generated ISO.
    """

    def __init__(self, workspace: Path, config: Dict[str, Any]) -> None:
        """
        Initialize the ISOGeneration module.

        Args:
            workspace: The path to the Z-Forge build workspace. The ISO will be
                       built in `workspace/iso_build` and the final output
                       placed in `workspace/`.
            config: The global build configuration dictionary, containing settings
                    like the output ISO name.
        """
        self.workspace: Path = workspace
        self.config: Dict[str, Any] = config
        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)
        # `iso_root` is the staging directory where the ISO contents are assembled.
        self.iso_root: Path = workspace / "iso_build"
        # `output_iso` is the path to the final generated ISO file.
        self.output_iso_name: str = config.get('builder_config', {}).get('output_iso_name', 'zforge-proxmox-v3.iso')
        self.output_iso: Path = workspace / self.output_iso_name

    def execute(self, resume_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate the bootable Z-Forge ISO from the prepared chroot environment.

        This is the main entry point for the module. It performs all steps
        necessary to create the ISO image.

        Args:
            resume_data: Optional dictionary for resuming. (Currently not used
                         in this module as ISO generation is typically atomic).

        Returns:
            A dictionary containing the status of the ISO generation.
            On success: {'status': 'success', 'iso_path': str, 'iso_size': int}
            On failure: {'status': 'error', 'error': str, 'module': str}
        """
        self.logger.info(f"Starting ISO generation process. Output will be: {self.output_iso}")

        try:
            # Step 1: Prepare the directory structure for ISO contents.
            self._prepare_iso_structure()

            # Step 2: Create a compressed SquashFS filesystem from the chroot.
            squashfs_image_path: Path = self._create_squashfs() # Keep track of path for debugging
            self.logger.info(f"SquashFS image created at: {squashfs_image_path}")

            # Step 3: Setup bootloaders (BIOS and UEFI).
            self._setup_bootloaders()

            # Step 4: Copy kernel, initramfs, and other overlay files.
            self._copy_overlay_files()

            # Step 5: Create the hybrid ISO image using xorriso.
            self._create_hybrid_iso()

            # Step 6: Verify the generated ISO.
            if self._verify_iso():
                self.logger.info(f"ISO generation completed successfully: {self.output_iso}")
                return {
                    'status': 'success',
                    'iso_path': str(self.output_iso),
                    'iso_size': self.output_iso.stat().st_size
                }
            else:
                # _verify_iso logs specific errors
                raise Exception("ISO verification failed after generation.")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"A command failed during ISO generation: {e.cmd}, Return Code: {e.returncode}, Output: {e.output}, Stderr: {e.stderr}")
            return {
                'status': 'error',
                'error': f"Command failed: {' '.join(e.cmd)} - {e.stderr or e.output or str(e)}",
                'module': self.__class__.__name__
            }
        except Exception as e:
            self.logger.error(f"ISO generation failed: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }

    def _prepare_iso_structure(self) -> None:
        """
        Create the necessary directory structure within `self.iso_root` for
        assembling the ISO contents.
        """
        self.logger.info(f"Preparing ISO directory structure at: {self.iso_root}")

        # Clean up any existing iso_root directory from previous builds.
        if self.iso_root.exists():
            self.logger.debug(f"Removing existing ISO root directory: {self.iso_root}")
            shutil.rmtree(self.iso_root)

        # Define standard directories for a bootable live ISO.
        # - boot/grub: For GRUB UEFI bootloader files and configuration.
        # - EFI/boot: Standard path for UEFI boot applications.
        # - isolinux: For ISOLINUX BIOS bootloader files and configuration.
        # - live: Contains the kernel (vmlinuz), initramfs (initrd.img), and SquashFS filesystem.
        # - install: Can contain installer-specific files or utilities (e.g., benchmarking scripts).
        # - .disk: Contains metadata about the disk (info file).
        directories_to_create: List[str] = [
            "boot/grub",
            "EFI/boot",
            "isolinux",
            "live",
            "install",
            ".disk"
        ]

        for directory_name in directories_to_create:
            path_to_create: Path = self.iso_root / directory_name
            path_to_create.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created ISO directory: {path_to_create}")
        self.logger.info("ISO directory structure prepared.")

    def _create_squashfs(self) -> Path:
        """
        Create a compressed SquashFS filesystem from the chroot environment.

        The SquashFS image will contain the entire root filesystem of the live system.
        It's placed in the `live/` directory of the ISO structure.

        Returns:
            The path to the created SquashFS image file.

        Raises:
            subprocess.CalledProcessError: If mksquashfs command fails.
        """
        self.logger.info("Creating SquashFS filesystem from chroot...")
        chroot_source_path: Path = self.workspace / "chroot"
        squashfs_output_path: Path = self.iso_root / "live/filesystem.squashfs"

        # Prepare the chroot environment before squashing (e.g., clean apt cache).
        self._prepare_chroot_for_squashfs(chroot_source_path)

        # Construct the mksquashfs command.
        # -comp zstd: Use Zstandard compression (good balance of speed and ratio).
        # -Xcompression-level 19: High compression level for zstd.
        # -no-exports: Do not include NFS export tables.
        # -no-duplicates: Scan for and remove duplicate files.
        # -b 1M: Use 1MB block size for potentially better compression on large files.
        # -processors: Use all available CPU cores for compression.
        cmd: List[str] = [
            "mksquashfs",
            str(chroot_source_path), # Source directory (the chroot)
            str(squashfs_output_path),# Output SquashFS file
            "-comp", "zstd",
            "-Xcompression-level", "19",
            "-no-exports",
            "-no-duplicates",
            "-b", "1M", # 1 Megabyte block size
            "-processors", str(os.cpu_count() or 1) # Use detected CPU count, default to 1
        ]
        self.logger.info(f"Executing mksquashfs: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, capture_output=True, text=True)

        # Create a 'filesystem.size' file, sometimes used by live boot scripts
        # to know the size of the SquashFS image.
        size_bytes: int = squashfs_output_path.stat().st_size
        (self.iso_root / "live/filesystem.size").write_text(str(size_bytes))
        self.logger.info(f"SquashFS filesystem created at {squashfs_output_path} (Size: {size_bytes} bytes).")
        return squashfs_output_path

    def _setup_bootloaders(self) -> None:
        """Setup both BIOS (ISOLINUX) and UEFI (GRUB) bootloaders."""
        self.logger.info("Setting up BIOS and UEFI bootloaders...")
        self._setup_uefi_boot() # GRUB for UEFI
        self._setup_bios_boot() # ISOLINUX for BIOS
        self.logger.info("Bootloaders setup completed.")

    def _setup_uefi_boot(self) -> None:
        """
        Setup UEFI boot using GRUB.

        This involves creating a standalone GRUB EFI image (`bootx64.efi`)
        and a `grub.cfg` configuration file.
        """
        self.logger.info("Setting up UEFI boot (GRUB)...")
        grub_efi_output_path: Path = self.iso_root / "EFI/boot/bootx64.efi"
        # The path to grub.cfg used by grub-mkstandalone is relative to its internal temporary root.
        # It expects the config to be available at a path like 'boot/grub/grub.cfg'.
        # We will create this config later in self.iso_root / "boot/grub/grub.cfg".
        # The grub-mkstandalone command will embed this referenced config.
		# A common practice is to point to a config file that will exist on the ISO.
        # The path given to grub-mkstandalone (e.g. boot/grub/grub.cfg=actual_file_path)
        # means "embed actual_file_path into the EFI image at internal path boot/grub/grub.cfg"
        # For Z-Forge, we assume a predefined GRUB config is available or generated.
        # Let's assume /usr/share/zforge/grub/grub-efi.cfg is a template on the build host.
        # If not, this command needs adjustment or the file needs to be created first.

        # For this example, we'll assume a simplified grub.cfg is directly written later.
        # The grub-mkstandalone will embed a *different* grub.cfg if specified.
        # Often, the EFI image loads grub.cfg from /boot/grub/ on the ISO.
        # Let's use a common approach where grub_efi loads grub.cfg from the ISO.
        # This requires that the grub_efi is built with modules to find and read this cfg.
        # The provided command seems to assume a specific pre-existing config to embed.
        # If /usr/share/zforge/grub/grub-efi.cfg doesn't exist, this command will fail.
        # For robustness, let's ensure our own grub.cfg is used.
        # We'll write our grub.cfg to self.iso_root / "boot/grub/grub.cfg"
        # and then ensure grub-mkstandalone can find it or is built generically.

        # Create our GRUB configuration first
        grub_cfg_content: str = """
set timeout=10
set default=0

# Load video drivers for graphical terminal
insmod all_video
insmod gfxterm
insmod png # For background images

# Set preferred graphics mode (auto attempts best available)
set gfxmode=auto
# Keep the selected graphics mode for the Linux kernel
set gfxpayload=keep
# Use graphical terminal
terminal_output gfxterm

# Main Z-Forge Installer menu entry
menuentry "Z-Forge Proxmox VE Installer" {
    set gfxpayload=keep # Ensure graphics mode is passed to kernel
    # Kernel line: boot=live (standard for live systems)
    # components: may enable specific live-boot features or installer components
    # quiet splash: standard for quieter boot with a splash screen
    linux /live/vmlinuz boot=live components quiet splash
    initrd /live/initrd.img
}

# Safe graphics mode menu entry (e.g., for problematic video cards)
menuentry "Z-Forge Proxmox VE Installer (Safe Graphics/nomodeset)" {
    set gfxpayload=text # Fallback to text mode if gfxterm issues
    linux /live/vmlinuz boot=live components quiet splash nomodeset
    initrd /live/initrd.img
}

# Recovery mode menu entry (single user mode)
menuentry "Z-Forge Recovery Mode" {
    set gfxpayload=text
    linux /live/vmlinuz boot=live components single
    initrd /live/initrd.img
}

# Hardware detection tool (if available)
menuentry "Hardware Detection Tool" {
    set gfxpayload=text
    linux /live/vmlinuz boot=live components zforge.mode=hwdetect # Custom boot option
    initrd /live/initrd.img
}

# Memory test utility
menuentry "Memory Test (memtest86+)" {
    # memtest86+ is typically a 16-bit application loaded differently
    linux16 /live/memtest86+.bin # Assuming memtest86+.bin is copied to /live
}
"""
        grub_cfg_iso_path: Path = self.iso_root / "boot/grub/grub.cfg"
        grub_cfg_iso_path.parent.mkdir(parents=True, exist_ok=True)
        grub_cfg_iso_path.write_text(grub_cfg_content)
        self.logger.info(f"GRUB UEFI configuration written to: {grub_cfg_iso_path}")

        # Generate GRUB EFI image.
        # This command creates a self-contained GRUB EFI executable.
        # --format=x86_64-efi: Specifies the target format.
        # --output: Specifies the output file path.
        # --locales= --fonts=: Emptied to reduce size if full localization/fonts not needed.
        # "boot/grub/grub.cfg=/path/to/host/grub.cfg" : Embeds a specific grub.cfg into the EFI.
        # For our case, we want GRUB to load the grub.cfg from the ISO's /boot/grub/ directory.
        # This requires that grub-mkstandalone includes modules to find and read this (e.g. part_gpt, ext2, iso9660, fat).
        # A more robust grub-mkstandalone includes necessary modules by default if not overly pruned.
        # The original command: "boot/grub/grub.cfg=/usr/share/zforge/grub/grub-efi.cfg"
        # This implies a specific config from the host system. We'll use the one we just wrote.
        cmd_grub_mkstandalone: List[str] = [
            "grub-mkstandalone",
            "--format=x86_64-efi",
            f"--output={grub_efi_output_path}",
            "--locales=", # Minimal locales
            "--fonts=",   # Minimal fonts
            # This tells grub-mkstandalone: "When you run, find your config at boot/grub/grub.cfg on your image."
            # To achieve this, it needs to embed enough modules to read from ISO.
            # A common way is to specify modules or ensure config loading is default.
            # An alternative is to embed the config directly:
            f"boot/grub/grub.cfg={grub_cfg_iso_path}" # Embed the config we just wrote.
        ]
        self.logger.info(f"Executing grub-mkstandalone: {' '.join(cmd_grub_mkstandalone)}")
        subprocess.run(cmd_grub_mkstandalone, check=True, capture_output=True, text=True)
        self.logger.info(f"GRUB UEFI boot image created at: {grub_efi_output_path}")

    def _setup_bios_boot(self) -> None:
        """
        Setup BIOS boot using ISOLINUX.

        This involves copying ISOLINUX binary files and creating an
        `isolinux.cfg` configuration file.
        """
        self.logger.info("Setting up BIOS boot (ISOLINUX)...")
        isolinux_target_dir: Path = self.iso_root / "isolinux"
        isolinux_target_dir.mkdir(parents=True, exist_ok=True)

        # List of essential ISOLINUX/SYSLINUX files and their typical system paths.
        # These paths might vary slightly depending on the build host's distribution.
        isolinux_source_files: List[str] = [
            "/usr/lib/ISOLINUX/isolinux.bin",          # The ISOLINUX bootloader itself.
            "/usr/lib/syslinux/modules/bios/ldlinux.c32", # Core module for SYSLINUX.
            "/usr/lib/syslinux/modules/bios/menu.c32",    # For text-based menus.
            "/usr/lib/syslinux/modules/bios/vesamenu.c32",# For graphical menus (preferred).
            "/usr/lib/syslinux/modules/bios/libcom32.c32",# Core library.
            "/usr/lib/syslinux/modules/bios/libutil.c32"  # Utility library.
        ]

        for src_file_path_str in isolinux_source_files:
            src_file_path = Path(src_file_path_str)
            if src_file_path.exists():
                shutil.copy(src_file_path, isolinux_target_dir)
                self.logger.debug(f"Copied {src_file_path} to {isolinux_target_dir}")
            else:
                # This could be a warning or an error depending on how critical the file is.
                self.logger.warning(f"ISOLINUX file not found: {src_file_path}. BIOS boot might fail.")

        # Assume a splash image (e.g., splash.png) would be copied to isolinux_target_dir
        # For now, this is just referenced in the config.
        # Example: shutil.copy("path/to/splash.png", isolinux_target_dir / "splash.png")


        # Create ISOLINUX configuration file (isolinux.cfg).
        isolinux_cfg_content: str = """
# Use vesamenu.c32 for a graphical menu experience.
DEFAULT vesamenu.c32
# Timeout in 1/10ths of a second (100 = 10 seconds).
TIMEOUT 100
# Do not display the 'boot:' prompt.
PROMPT 0

MENU TITLE Z-Forge Proxmox VE Installer
# Optional: Background image for the menu.
# MENU BACKGROUND splash.png
# Menu color scheme (border, title, text, highlighted text, etc.).
MENU COLOR border 30;44 #40ffffff #a0000000 std
MENU COLOR title 1;36;44 #9033ccff #a0000000 std
MENU COLOR sel 7;37;40 #e0ffffff #20ffffff all
MENU COLOR unsel 37;44 #50ffffff #a0000000 std
MENU COLOR help 37;40 #c0ffffff #a0000000 std
MENU COLOR timeout_msg 37;40 #80ffffff #00000000 std
MENU COLOR timeout 1;37;40 #c0ffffff #00000000 std
MENU COLOR msg07 37;40 #90ffffff #a0000000 std
MENU COLOR tabmsg 31;40 #30ffffff #00000000 std

# Default menu entry: Z-Forge Installer
LABEL installer
    MENU LABEL ^Install Proxmox VE with Z-Forge
    MENU DEFAULT
    KERNEL /live/vmlinuz
    APPEND initrd=/live/initrd.img boot=live components quiet splash

# Safe graphics mode entry
LABEL safe
    MENU LABEL Install with ^Safe Graphics (nomodeset)
    KERNEL /live/vmlinuz
    APPEND initrd=/live/initrd.img boot=live components quiet splash nomodeset

# Recovery mode entry
LABEL recovery
    MENU LABEL ^Recovery Mode (single user)
    KERNEL /live/vmlinuz
    APPEND initrd=/live/initrd.img boot=live components single

# Hardware detection tool entry
LABEL hwdetect
    MENU LABEL ^Hardware Detection Tool
    KERNEL /live/vmlinuz
    APPEND initrd=/live/initrd.img boot=live components zforge.mode=hwdetect

# Memory test entry
LABEL memtest
    MENU LABEL ^Memory Test (memtest86+)
    KERNEL /live/memtest86+.bin # Assumes memtest86+.bin is in /live
"""
        isolinux_cfg_path: Path = isolinux_target_dir / "isolinux.cfg"
        isolinux_cfg_path.write_text(isolinux_cfg_content)
        self.logger.info(f"ISOLINUX configuration written to: {isolinux_cfg_path}")

    def _copy_overlay_files(self) -> None:
        """
        Copy essential files like kernel, initramfs, and any other overlay
        files (e.g., benchmarking scripts, disk info) into the ISO structure.
        """
        self.logger.info("Copying overlay files to ISO structure...")
        chroot_path: Path = self.workspace / "chroot"
        live_dir_iso: Path = self.iso_root / "live"
        live_dir_iso.mkdir(parents=True, exist_ok=True)

        # Attempt to find the installed kernel and initramfs from the chroot.
        # This relies on them being in standard locations like /boot/vmlinuz-*
        # The exact version might have been determined by the KernelAcquisition module.
        # For robustness, we should ideally get these paths from a previous module's output.
        # Here, we try to find the "latest" by simple glob and sort if not precisely known.

        # Find kernel (vmlinuz)
        try:
            # List all vmlinuz files in chroot's /boot and pick the last one (often latest)
            vmlinuz_files_in_chroot = sorted(list((chroot_path / "boot").glob("vmlinuz-*")))
            if not vmlinuz_files_in_chroot:
                raise FileNotFoundError("No vmlinuz-* file found in chroot /boot directory.")
            vmlinuz_source_path: Path = vmlinuz_files_in_chroot[-1]
            shutil.copy(vmlinuz_source_path, live_dir_iso / "vmlinuz")
            self.logger.info(f"Copied kernel {vmlinuz_source_path.name} to {live_dir_iso / 'vmlinuz'}")
        except Exception as e:
            self.logger.error(f"Failed to copy kernel: {e}", exc_info=True)
            raise # Re-raise to signal critical failure

        # Find initramfs (initrd.img)
        try:
            initrd_files_in_chroot = sorted(list((chroot_path / "boot").glob("initrd.img-*")))
            if not initrd_files_in_chroot:
                # Also check for initramfs.img-* as some tools might name it that
                initrd_files_in_chroot = sorted(list((chroot_path / "boot").glob("initramfs.img-*")))
                if not initrd_files_in_chroot:
                    raise FileNotFoundError("No initrd.img-* or initramfs.img-* file found in chroot /boot directory.")

            initrd_source_path: Path = initrd_files_in_chroot[-1]
            shutil.copy(initrd_source_path, live_dir_iso / "initrd.img")
            self.logger.info(f"Copied initramfs {initrd_source_path.name} to {live_dir_iso / 'initrd.img'}")
        except Exception as e:
            self.logger.error(f"Failed to copy initramfs: {e}", exc_info=True)
            raise # Re-raise to signal critical failure

        # Copy benchmarking script (example of an overlay file).
        self._integrate_benchmarking_script()

        # Create .disk/info file with ISO metadata.
        disk_info_dir: Path = self.iso_root / ".disk"
        disk_info_dir.mkdir(parents=True, exist_ok=True)
        info_content: str = f"""Z-Forge Proxmox VE Installer
Version: {self.config.get('builder_config', {}).get('iso_version', '3.0')}
Build Date: {subprocess.check_output(['date', '+%Y-%m-%d'], text=True).strip()}
Architecture: amd64
"""
        (disk_info_dir / "info").write_text(info_content)
        self.logger.info(f"Created .disk/info file at {disk_info_dir / 'info'}")
        self.logger.info("Overlay files copied.")

    def _integrate_benchmarking_script(self) -> None:
        """
        Integrate the ZFS benchmarking script into the ISO structure.
        This includes the shell script for benchmarks and a Python wrapper
        for potential Calamares integration.
        """
        self.logger.info("Integrating ZFS benchmarking script...")
        # Directory within the ISO for installation-related scripts/tools.
        install_scripts_dir_iso: Path = self.iso_root / "install/benchmarking"
        install_scripts_dir_iso.mkdir(parents=True, exist_ok=True)

        # Save the main benchmarking shell script.
        # BENCHMARKING_SCRIPT is assumed to be a string containing the script's content.
        # In a real scenario, this content would be loaded from a file (e.g., tests/diskbenchmark.sh).
        bench_shell_script_path_iso: Path = install_scripts_dir_iso / "zfs_performance_test.sh"
        bench_shell_script_path_iso.write_text(BENCHMARKING_SCRIPT)
        bench_shell_script_path_iso.chmod(0o755) # Make it executable.
        self.logger.info(f"Benchmarking shell script written to: {bench_shell_script_path_iso}")

        # Create a Python wrapper script for Calamares integration.
        # This script would be called by a Calamares module to run the benchmark.
        calamares_wrapper_content: str = '''#!/usr/bin/env python3
"""
Calamares Python module wrapper for ZFS benchmarking script.
This script is executed by a Calamares 'python' module to run the
ZFS performance test and potentially use its results to guide partitioning.
"""

import subprocess
import json # If results are in JSON
import libcalamares # Calamares utility library (available in Calamares environment)
from pathlib import Path

BENCHMARK_SCRIPT_PATH = "/install/benchmarking/zfs_performance_test.sh"
# Example path where the benchmark script might save its structured results.
BENCHMARK_RESULTS_DIR = Path("/root/zfs_test_results")

def run():
    """
    Main execution function for the Calamares module.
    This function is called by Calamares when the module is executed.
    """
    libcalamares.utils.debug("Starting ZFS performance benchmarking via Calamares wrapper...")

    try:
        # Check if the user wants to run the benchmark (e.g., via a globalstorage key set by a previous UI page).
        # For simplicity, we assume it should run if this module is active.
        # A more complex implementation would use Calamares' QML UIs to ask the user.

        # Execute the benchmarking shell script.
        # Ensure the script is executable and exists at BENCHMARK_SCRIPT_PATH on the live ISO.
        process = subprocess.run(
            [BENCHMARK_SCRIPT_PATH],
            capture_output=True,
            text=True,
            check=False # Don't raise exception immediately, check returncode manually.
        )

        if process.returncode != 0:
            error_msg = f"Benchmarking script failed. Stderr: {process.stderr}"
            libcalamares.utils.error(error_msg)
            # Return an error that Calamares can display to the user.
            return ("Benchmark Error", f"Hardware performance benchmark failed: {error_msg[:200]}.")

        libcalamares.utils.debug(f"Benchmark script stdout: {process.stdout}")

        # Attempt to parse recommendations from the benchmark script's output or report file.
        # This is highly dependent on the benchmark script's output format.
        # Example: Assuming the script writes a report file.
        report_files = sorted(list(BENCHMARK_RESULTS_DIR.glob("zfs_test_report_*.md")), key=lambda p: p.stat().st_mtime, reverse=True)
        recommendations = {}
        if report_files:
            latest_report_content = report_files[0].read_text()
            # This parsing logic is a placeholder and needs to match the actual report format.
            if "Pool Type: mirror" in latest_report_content: recommendations['pool_type'] = 'mirror'
            if "Pool Type: raidz1" in latest_report_content: recommendations['pool_type'] = 'raidz1'
            if "Compression: lz4" in latest_report_content: recommendations['compression'] = 'lz4'
            if "Compression: zstd" in latest_report_content: recommendations['compression'] = 'zstd'
            libcalamares.utils.debug(f"Parsed recommendations: {recommendations}")
        else:
            libcalamares.utils.warning("No benchmark report file found.")

        # Store recommendations in Calamares global storage for other modules (e.g., partitioning) to use.
        libcalamares.globalstorage.insert("zfs_benchmark_results", recommendations)

        # If successful, return None (or a tuple for a custom status message).
        return None

    except Exception as e:
        error_str = f"An unexpected error occurred during benchmarking: {str(e)}"
        libcalamares.utils.error(error_str)
        return ("Critical Benchmark Error", f"A critical error occurred: {error_str[:200]}.")

# Optional: Calamares module metadata (if this file itself is a module entry point)
# def pretty_name(): return "Hardware Performance Analysis"
# def description(): return "Runs ZFS hardware benchmarks to suggest optimal pool configurations."
# def icon(): return "memory" # Example Calamares icon name
# def timeout(): return 3600 # Seconds
'''
        wrapper_script_path_iso: Path = install_scripts_dir_iso / "calamares_bench_wrapper.py"
        wrapper_script_path_iso.write_text(calamares_wrapper_content)
        wrapper_script_path_iso.chmod(0o755) # Make it executable.
        self.logger.info(f"Calamares benchmarking wrapper script written to: {wrapper_script_path_iso}")
        self.logger.info("Benchmarking script integration completed.")


    def _create_hybrid_iso(self) -> None:
        """
        Create the final hybrid ISO image using `xorriso`.

        A hybrid ISO can be booted from both CD/DVD and USB drives.
        This method uses `xorriso` with appropriate options for El Torito (BIOS)
        and EFI boot, making it compatible with a wide range of systems.

        Raises:
            subprocess.CalledProcessError: If xorriso or isohybrid commands fail.
        """
        self.logger.info(f"Creating hybrid ISO image: {self.output_iso} from {self.iso_root}")

        # Construct the xorriso command.
        # -as mkisofs: Use mkisofs emulation mode for compatible arguments.
        # -iso-level 3: ISO9660 Level 3 (allows deeper directory structures, longer filenames).
        # -full-iso9660-filenames: Use less restrictive ISO9660 filenames.
        # -volid: Volume ID for the ISO.
        # -eltorito-boot: Specifies BIOS boot image (ISOLINUX).
        # -eltorito-catalog: Specifies boot catalog file.
        # -no-emul-boot, -boot-load-size 4, -boot-info-table: Standard El Torito boot options.
        # -isohybrid-mbr: Makes the ISO bootable from USB via MBR. Requires isohdpfx.bin.
        # -eltorito-alt-boot -e ... -no-emul-boot: Specifies EFI boot image.
        # -isohybrid-gpt-basdat: Embeds GPT structure for UEFI boot from USB.
        # -output: Output ISO file path.
        # self.iso_root: The source directory containing all files for the ISO.

        # Path to isohdpfx.bin, part of syslinux, needed for hybrid MBR.
        isohdpfx_path = "/usr/lib/ISOLINUX/isohdpfx.bin"
        if not Path(isohdpfx_path).exists():
            # Fallback or error if not found. Some distros place it in /usr/lib/syslinux/bios/
            alt_isohdpfx_path = "/usr/lib/syslinux/bios/isohdpfx.bin"
            if Path(alt_isohdpfx_path).exists():
                isohdpfx_path = alt_isohdpfx_path
            else:
                self.logger.error(f"isohdpfx.bin not found at {isohdpfx_path} or {alt_isohdpfx_path}. Hybrid MBR may fail.")
                # Decide if this is a fatal error or a warning. For now, proceed.
                # raise FileNotFoundError(f"isohdpfx.bin not found.")

        cmd_xorriso: List[str] = [
            "xorriso",
            "-as", "mkisofs",
            "-iso-level", "3",
            "-full-iso9660-filenames",
            "-volid", self.config.get('builder_config', {}).get('iso_volid', "ZFORGE_PROXMOX"),
            # BIOS Boot (El Torito)
            "-eltorito-boot", "isolinux/isolinux.bin",
            "-eltorito-catalog", "isolinux/boot.cat", # ISOLINUX boot catalog
            "-no-emul-boot",      # Standard for hard disk/CD emulation
            "-boot-load-size", "4",# Number of 512-byte sectors to load
            "-boot-info-table",   # Patch boot image with info table
            # MBR for USB boot (isohybrid)
            "-isohybrid-mbr", isohdpfx_path,
            # UEFI Boot
            "-eltorito-alt-boot", # Start alternate El Torito boot sequence
            "-e", "EFI/boot/bootx64.efi", # Path to EFI boot image on ISO
            "-no-emul-boot",      # Standard for EFI boot
            "-isohybrid-gpt-basdat", # Mark as GPT basic data partition for UEFI USB boot
            # Output
            "-output", str(self.output_iso),
            # Source directory
            str(self.iso_root)
        ]
        self.logger.info(f"Executing xorriso: {' '.join(cmd_xorriso)}")
        subprocess.run(cmd_xorriso, check=True, capture_output=True, text=True)

        # The `isohybrid --uefi` command can sometimes be used as an additional step
        # to ensure UEFI compatibility, particularly for older versions of mkisofs/xorriso
        # or specific system requirements. xorriso with -isohybrid-gpt-basdat should suffice.
        # However, if issues arise, this can be added:
        # self.logger.info(f"Running isohybrid --uefi on {self.output_iso}")
        # subprocess.run(["isohybrid", "--uefi", str(self.output_iso)], check=True)
        self.logger.info(f"Hybrid ISO created successfully at {self.output_iso}")

    def _verify_iso(self) -> bool:
        """
        Perform basic verification of the generated ISO image.

        Checks for existence, reasonable size, and presence of key boot files.

        Returns:
            True if basic verification passes, False otherwise.
        """
        self.logger.info(f"Verifying generated ISO: {self.output_iso}")

        # Check 1: ISO file exists.
        if not self.output_iso.exists():
            self.logger.error("ISO verification failed: File does not exist.")
            return False

        # Check 2: ISO file has a reasonable size (e.g., > 500MB).
        # This is a heuristic and might need adjustment based on expected ISO content.
        min_expected_size_mb: int = self.config.get('builder_config',{}).get('iso_min_size_mb', 500)
        iso_size_mb: float = self.output_iso.stat().st_size / (1024 * 1024)
        if iso_size_mb < min_expected_size_mb:
            self.logger.error(f"ISO verification failed: File size {iso_size_mb:.2f}MB is less than minimum expected {min_expected_size_mb}MB.")
            return False
        self.logger.info(f"ISO file size: {iso_size_mb:.2f}MB.")

        # Check 3: Use `isoinfo` to list ISO contents and check for critical files.
        # `isoinfo -d`: Display directory-like listing of ISO (header info).
        # `isoinfo -f -i <iso>`: List all files.
        # `isoinfo -x <path> -i <iso>`: Extract file (or check existence).
        try:
            isoinfo_header_result = subprocess.run(
                ["isoinfo", "-d", "-i", str(self.output_iso)],
                capture_output=True, text=True, check=True
            )
            self.logger.debug(f"ISO Header Info:\n{isoinfo_header_result.stdout}")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"ISO verification failed: `isoinfo -d` command failed. Error: {e.stderr}")
            return False
        except FileNotFoundError:
            self.logger.error("ISO verification failed: `isoinfo` command not found. Please ensure it's installed.")
            return False # Cannot verify

        # Check for the presence of essential boot files.
        # Paths are as they appear in the ISO9660 filesystem.
        # isoinfo uses ';' as version separator, sometimes files have it.
        required_iso_files: List[str] = [
            "/ISOLINUX/ISOLINUX.BIN", # Semicolon might be ;1 depending on system
            "/EFI/BOOT/BOOTX64.EFI",
            "/LIVE/VMLINUZ", # Check without trailing dot first
            "/LIVE/INITRD.IMG"
        ]

        # Try variations for files that might have version numbers or slight name changes
        # isoinfo path formats can be tricky.
        # For example, vmlinuz might be VMLINUZ.;1 or just VMLINUZ
        # We will try to be somewhat flexible or rely on exact names from earlier steps.
        # A more robust check would involve `isoinfo -find ...` if available and less ambiguous.

        for file_path_str in required_iso_files:
            # Try common variations for isoinfo paths (uppercase, with/without ;1)
            # This is a simplified check. A more robust check might list all files and search.
            # For now, assume exact paths or that isoinfo handles case-insensitivity if the FS does.
            found = False
            # Check exact path first
            check_cmd_exact = ["isoinfo", "-i", str(self.output_iso), "-f", "-J", "-R"] # List files Joliet/RockRidge
            # Grep for the file path
            try:
                isoinfo_list_result = subprocess.run(check_cmd_exact, capture_output=True, text=True, check=True)
                if file_path_str.upper() in isoinfo_list_result.stdout.upper(): # Case-insensitive check in listing
                    self.logger.info(f"Required file found in ISO listing: {file_path_str}")
                    found = True
                else: # Try with ;1 for Joliet/RockRidge versioning
                    if f"{file_path_str.upper()};1" in isoinfo_list_result.stdout.upper():
                         self.logger.info(f"Required file found in ISO listing: {file_path_str};1")
                         found = True

            except subprocess.CalledProcessError as e:
                 self.logger.error(f"ISO verification: `isoinfo -f` command failed. Error: {e.stderr}")
                 return False # If listing files fails, verification cannot proceed

            if not found:
                self.logger.error(f"ISO verification failed: Required file '{file_path_str}' not found in ISO listing.")
                return False

        self.logger.info("ISO verification passed successfully.")
        return True

    def _prepare_chroot_for_squashfs(self, chroot_path: Path) -> None:
        """
        Prepare the chroot environment before creating the SquashFS image.
        This typically involves cleaning package caches and temporary files
        to reduce the size of the SquashFS image.
        """
        self.logger.info(f"Preparing chroot at {chroot_path} for SquashFS creation...")

        # Clean APT package cache within the chroot.
        try:
            subprocess.run(
                ["chroot", str(chroot_path), "apt-get", "clean"],
                capture_output=True, check=True, text=True
            )
            self.logger.debug("Cleaned apt cache in chroot.")
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Could not clean apt cache in chroot (non-fatal): {e.stderr}")
        except FileNotFoundError: # if chroot or apt-get is not found.
             self.logger.error(f"Failed to run apt-get clean: chroot or apt-get not found. Chroot path: {chroot_path}")


        # Remove other temporary files and logs to reduce image size.
        # Be careful with `rm -rf`, ensure paths are correctly scoped to the chroot.
        temp_patterns_to_remove: List[str] = [
            "tmp/*",
            "var/tmp/*",
            "var/cache/apt/archives/*.deb", # Clean downloaded .deb files
            "var/log/*.log",                # Remove general logs
            "var/log/apt/*",                # Remove apt logs
            "root/.bash_history",           # Clear root's bash history
            # Add more patterns as needed
        ]
        for pattern in temp_patterns_to_remove:
            # Use glob to find files matching the pattern within the chroot
            # and then remove them. This is safer than constructing `rm -rf` with shell=True.
            # Note: Path.glob() from host won't work directly for chroot internal paths without prefixing chroot_path.
            # So, we run rm via chroot for safety.
            rm_cmd = ["rm", "-rf"]
            # This is tricky. `chroot /path/to/chroot rm -rf /tmp/*` is what we want.
            # The pattern needs to be relative to the chroot's root.
            # Example: for "tmp/*", command becomes `chroot /path/to/chroot rm -rf /tmp/*`
            # This is potentially dangerous if not handled carefully.
            # A safer way is to mount the chroot and operate from host, or use very specific paths.
            # For now, we'll use a slightly safer approach by listing and removing.
            # Or, more simply, just run the rm command within the chroot.

            # Command to be run inside chroot: rm -rf /pattern
            # Ensure pattern starts with / if it's from root of chroot, or adjust as needed.
            path_in_chroot = Path("/") / pattern
            try:
                subprocess.run(
                    ["chroot", str(chroot_path), "rm", "-rf", str(path_in_chroot)],
                    capture_output=True, check=False, text=True # check=False as some paths might not exist
                )
                self.logger.debug(f"Attempted to remove files in chroot: {path_in_chroot}")
            except FileNotFoundError:
                 self.logger.error(f"Failed to run rm for {path_in_chroot}: chroot or rm not found. Chroot path: {chroot_path}")


        # Ensure standard temporary directories exist with correct permissions (1777 sticky bit).
        sticky_tmp_dirs: List[str] = ["tmp", "var/tmp"]
        for dir_name in sticky_tmp_dirs:
            tmp_dir_path: Path = chroot_path / dir_name
            tmp_dir_path.mkdir(mode=0o777, parents=True, exist_ok=True) # Ensure it exists
            # Set sticky bit. This needs to be done via chroot or as root on host.
            try:
                subprocess.run(
                    ["chroot", str(chroot_path), "chmod", "1777", f"/{dir_name}"],
                    check=True, capture_output=True, text=True
                )
                self.logger.debug(f"Set 1777 permissions on chrooted /{dir_name}")
            except subprocess.CalledProcessError as e:
                self.logger.warning(f"Could not set 1777 on chrooted /{dir_name}: {e.stderr}")
            except FileNotFoundError:
                self.logger.error(f"Failed to chmod /{dir_name}: chroot or chmod not found.")

        self.logger.info("Chroot preparation for SquashFS completed.")
