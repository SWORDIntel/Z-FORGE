#!/usr/bin/env python3
# z-forge/builder/modules/iso_generation.py

"""
ISO Generation Module
Creates bootable hybrid ISO with all Z-Forge components
"""

import subprocess
import shutil
import os
from pathlib import Path
from typing import Dict, Optional
import logging
import tempfile

class ISOGeneration:
    """Generates the final bootable ISO"""

    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.iso_root = workspace / "iso_build"
        self.output_iso = workspace / config.get('builder_config', {}).get('output_iso_name', 'zforge-proxmox-v3.iso')

    def execute(self, resume_data: Optional[Dict] = None) -> Dict:
        """
        Generate bootable ISO from prepared chroot

        Returns:
            Dict with ISO path and build status
        """

        self.logger.info("Starting ISO generation...")

        try:
            # Prepare ISO directory structure
            self._prepare_iso_structure()

            # Create squashfs filesystem
            squashfs_path = self._create_squashfs()

            # Setup bootloaders (BIOS and UEFI)
            self._setup_bootloaders()

            # Copy additional files
            self._copy_overlay_files()

            # Create the hybrid ISO
            self._create_hybrid_iso()

            # Verify ISO
            if self._verify_iso():
                return {
                    'status': 'success',
                    'iso_path': str(self.output_iso),
                    'iso_size': self.output_iso.stat().st_size
                }
            else:
                raise Exception("ISO verification failed")

        except Exception as e:
            self.logger.error(f"ISO generation failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }

    def _prepare_iso_structure(self):
        """Create ISO directory structure"""

        self.logger.info("Preparing ISO directory structure...")

        # Clean and create directories
        if self.iso_root.exists():
            shutil.rmtree(self.iso_root)

        directories = [
            "boot/grub",
            "EFI/boot",
            "isolinux",
            "live",
            "install",
            ".disk"
        ]

        for directory in directories:
            (self.iso_root / directory).mkdir(parents=True, exist_ok=True)

    def _create_squashfs(self) -> Path:
        """Create compressed filesystem from chroot"""

        self.logger.info("Creating squashfs filesystem...")

        chroot_path = self.workspace / "chroot"
        squashfs_path = self.iso_root / "live/filesystem.squashfs"

        # Prepare chroot for squashing
        self._prepare_chroot_for_squashfs(chroot_path)

        # Create squashfs with optimal compression
        cmd = [
            "mksquashfs",
            str(chroot_path),
            str(squashfs_path),
            "-comp", "zstd",
            "-Xcompression-level", "19",
            "-no-exports",
            "-no-duplicates",
            "-b", "1M",
            "-processors", str(os.cpu_count())
        ]

        subprocess.run(cmd, check=True)

        # Create filesystem.size
        size = squashfs_path.stat().st_size
        (self.iso_root / "live/filesystem.size").write_text(str(size))

        return squashfs_path

    def _setup_bootloaders(self):
        """Setup BIOS and UEFI bootloaders"""

        self.logger.info("Setting up bootloaders...")

        # GRUB for UEFI
        self._setup_uefi_boot()

        # ISOLINUX for BIOS
        self._setup_bios_boot()

    def _setup_uefi_boot(self):
        """Setup UEFI boot with GRUB"""

        # Create GRUB image
        grub_efi = self.iso_root / "EFI/boot/bootx64.efi"

        # Generate GRUB EFI image
        cmd = [
            "grub-mkstandalone",
            "--format=x86_64-efi",
            "--output=" + str(grub_efi),
            "--locales=",
            "--fonts=",
            "boot/grub/grub.cfg=/usr/share/zforge/grub/grub-efi.cfg"
        ]

        subprocess.run(cmd, check=True)

        # Create GRUB configuration
        grub_cfg = """
set timeout=10
set default=0

insmod all_video
insmod gfxterm
insmod png

set gfxmode=auto
set gfxpayload=keep
terminal_output gfxterm

menuentry "Z-Forge Proxmox VE Installer" {
    set gfxpayload=keep
    linux /live/vmlinuz boot=live components quiet splash
    initrd /live/initrd.img
}

menuentry "Z-Forge Proxmox VE Installer (Safe Graphics)" {
    set gfxpayload=text
    linux /live/vmlinuz boot=live components quiet splash nomodeset
    initrd /live/initrd.img
}

menuentry "Z-Forge Recovery Mode" {
    set gfxpayload=text
    linux /live/vmlinuz boot=live components single
    initrd /live/initrd.img
}

menuentry "Hardware Detection Tool" {
    set gfxpayload=text
    linux /live/vmlinuz boot=live components zforge.mode=hwdetect
    initrd /live/initrd.img
}

menuentry "Memory Test (memtest86+)" {
    linux16 /live/memtest86+.bin
}
"""

        (self.iso_root / "boot/grub/grub.cfg").write_text(grub_cfg)

    def _setup_bios_boot(self):
        """Setup BIOS boot with ISOLINUX"""

        # Copy isolinux files
        isolinux_files = [
            "/usr/lib/ISOLINUX/isolinux.bin",
            "/usr/lib/syslinux/modules/bios/ldlinux.c32",
            "/usr/lib/syslinux/modules/bios/menu.c32",
            "/usr/lib/syslinux/modules/bios/vesamenu.c32",
            "/usr/lib/syslinux/modules/bios/libcom32.c32",
            "/usr/lib/syslinux/modules/bios/libutil.c32"
        ]

        for src in isolinux_files:
            if Path(src).exists():
                shutil.copy(src, self.iso_root / "isolinux/")

        # Create isolinux configuration
        isolinux_cfg = """
DEFAULT vesamenu.c32
TIMEOUT 100
PROMPT 0

MENU TITLE Z-Forge Proxmox VE Installer
MENU BACKGROUND splash.png
MENU COLOR border 30;44 #40ffffff #a0000000 std
MENU COLOR title 1;36;44 #9033ccff #a0000000 std
MENU COLOR sel 7;37;40 #e0ffffff #20ffffff all
MENU COLOR unsel 37;44 #50ffffff #a0000000 std
MENU COLOR help 37;40 #c0ffffff #a0000000 std
MENU COLOR timeout_msg 37;40 #80ffffff #00000000 std
MENU COLOR timeout 1;37;40 #c0ffffff #00000000 std
MENU COLOR msg07 37;40 #90ffffff #a0000000 std
MENU COLOR tabmsg 31;40 #30ffffff #00000000 std

LABEL installer
    MENU LABEL ^Install Proxmox VE with Z-Forge
    MENU DEFAULT
    KERNEL /live/vmlinuz
    APPEND initrd=/live/initrd.img boot=live components quiet splash

LABEL safe
    MENU LABEL Install with ^Safe Graphics
    KERNEL /live/vmlinuz
    APPEND initrd=/live/initrd.img boot=live components quiet splash nomodeset

LABEL recovery
    MENU LABEL ^Recovery Mode
    KERNEL /live/vmlinuz
    APPEND initrd=/live/initrd.img boot=live components single

LABEL hwdetect
    MENU LABEL ^Hardware Detection Tool
    KERNEL /live/vmlinuz
    APPEND initrd=/live/initrd.img boot=live components zforge.mode=hwdetect

LABEL memtest
    MENU LABEL ^Memory Test
    KERNEL /live/memtest86+.bin
"""

        (self.iso_root / "isolinux/isolinux.cfg").write_text(isolinux_cfg)

    def _copy_overlay_files(self):
        """Copy overlay files including benchmarking script"""

        self.logger.info("Copying overlay files...")

        # Copy kernel and initrd
        chroot_path = self.workspace / "chroot"

        # Find latest kernel
        vmlinuz_path = list(chroot_path.glob("boot/vmlinuz-*"))[-1]
        initrd_path = list(chroot_path.glob("boot/initrd.img-*"))[-1]

        shutil.copy(vmlinuz_path, self.iso_root / "live/vmlinuz")
        shutil.copy(initrd_path, self.iso_root / "live/initrd.img")

        # Copy benchmarking script
        self._integrate_benchmarking_script()

        # Create .disk/info
        info_content = f"""Z-Forge Proxmox VE Installer
Version: 3.0
Build Date: {subprocess.check_output(['date', '+%Y-%m-%d'], text=True).strip()}
Architecture: amd64
"""
        (self.iso_root / ".disk/info").write_text(info_content)

    def _integrate_benchmarking_script(self):
        """Integrate the ZFS benchmarking script"""

        # Create benchmarking module directory
        bench_dir = self.iso_root / "install/benchmarking"
        bench_dir.mkdir(parents=True, exist_ok=True)

        # Save the benchmarking script
        bench_script = bench_dir / "zfs_performance_test.sh"
        bench_script.write_text(BENCHMARKING_SCRIPT)
        bench_script.chmod(0o755)

        # Create wrapper for Calamares integration
        wrapper_script = bench_dir / "calamares_bench_wrapper.py"
        wrapper_content = '''#!/usr/bin/env python3
"""
Calamares wrapper for ZFS benchmarking script
Integrates hardware testing into the installation workflow
"""

import subprocess
import json
import tempfile
import libcalamares
from pathlib import Path

def run_benchmark():
    """Execute benchmarking and parse results"""

    # Run the benchmark script
    result = subprocess.run(
        ["/install/benchmarking/zfs_performance_test.sh"],
        capture_output=True,
        text=True
    )

    # Parse the report file
    report_files = list(Path("/root/zfs_test_results").glob("zfs_test_report_*.md"))
    if report_files:
        latest_report = max(report_files, key=lambda p: p.stat().st_mtime)
        report_content = latest_report.read_text()

        # Extract recommendations
        recommendations = parse_recommendations(report_content)

        # Store in global storage for partitioning module
        libcalamares.globalstorage.insert("zfs_benchmark_results", recommendations)

        return recommendations

    return None

def parse_recommendations(report_content):
    """Parse benchmark report for recommendations"""

    recommendations = {
        'pool_type': 'mirror',  # default
        'compression': 'lz4',
        'devices': [],
        'special_devices': [],
        'cache_devices': []
    }

    # Extract pool configuration recommendation
    if 'Hybrid Pool Configuration' in report_content:
        recommendations['pool_type'] = 'hybrid'
    elif 'All-Flash Pool Configuration' in report_content:
        recommendations['pool_type'] = 'all-flash'
    elif 'RAID-Z2' in report_content:
        recommendations['pool_type'] = 'raidz2'
    elif 'RAID-Z1' in report_content:
        recommendations['pool_type'] = 'raidz1'

    # Extract compression recommendation
    if 'compression=zstd' in report_content:
        recommendations['compression'] = 'zstd-3'

    return recommendations

# Calamares module interface
def pretty_name():
    return "Hardware Performance Analysis"

def run():
    """Main Calamares entry point"""

    libcalamares.utils.debug("Starting ZFS performance benchmarking...")

    try:
        # Ask user if they want to run benchmarking
        if should_run_benchmark():
            results = run_benchmark()

            if results:
                libcalamares.utils.debug(f"Benchmark results: {results}")
                return None
            else:
                return ("Benchmark failed",
                        "Failed to complete hardware benchmarking. "
                        "Continuing with default settings.")
        else:
            # User skipped benchmarking
            libcalamares.globalstorage.insert("zfs_benchmark_results", None)
            return None

    except Exception as e:
        libcalamares.utils.error(f"Benchmarking error: {str(e)}")
        return None  # Non-fatal error

def should_run_benchmark():
    """Check if user wants to run benchmarking"""

    # In a real implementation, this would show a dialog
    # For now, we'll check a global storage flag
    return libcalamares.globalstorage.value("run_benchmarking", True)
'''
        wrapper_script.write_text(wrapper_content)
        wrapper_script.chmod(0o755)

    def _create_hybrid_iso(self):
        """Create the final hybrid ISO"""

        self.logger.info("Creating hybrid ISO...")

        # Create ISO with xorriso
        cmd = [
            "xorriso",
            "-as", "mkisofs",
            "-iso-level", "3",
            "-full-iso9660-filenames",
            "-volid", "ZFORGE_PROXMOX",
            "-eltorito-boot", "isolinux/isolinux.bin",
            "-eltorito-catalog", "isolinux/boot.cat",
            "-no-emul-boot",
            "-boot-load-size", "4",
            "-boot-info-table",
            "-isohybrid-mbr", "/usr/lib/ISOLINUX/isohdpfx.bin",
            "-eltorito-alt-boot",
            "-e", "EFI/boot/bootx64.efi",
            "-no-emul-boot",
            "-isohybrid-gpt-basdat",
            "-output", str(self.output_iso),
            str(self.iso_root)
        ]

        subprocess.run(cmd, check=True)

        # Make ISO hybrid for USB boot
        subprocess.run(["isohybrid", "--uefi", str(self.output_iso)], check=True)

    def _verify_iso(self) -> bool:
        """Verify the generated ISO"""

        self.logger.info("Verifying ISO...")

        # Check if ISO exists and has reasonable size
        if not self.output_iso.exists():
            return False

        size_mb = self.output_iso.stat().st_size / (1024 * 1024)
        if size_mb < 500:  # Minimum expected size
            self.logger.error(f"ISO too small: {size_mb}MB")
            return False

        # Verify ISO structure
        result = subprocess.run(
            ["isoinfo", "-d", "-i", str(self.output_iso)],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return False

        # Check for required files
        required_files = [
            "/ISOLINUX/ISOLINUX.BIN;1",
            "/EFI/BOOT/BOOTX64.EFI;1",
            "/LIVE/VMLINUZ.;1",
            "/LIVE/INITRD.IMG;1"
        ]

        for file in required_files:
            check_cmd = ["isoinfo", "-i", str(self.output_iso), "-x", file]
            result = subprocess.run(check_cmd, capture_output=True)
            if result.returncode != 0:
                self.logger.error(f"Missing required file: {file}")
                return False

        self.logger.info("ISO verification passed")
        return True

    def _prepare_chroot_for_squashfs(self, chroot_path: Path):
        """Prepare chroot before creating squashfs"""

        # Clean package cache
        subprocess.run(
            ["chroot", str(chroot_path), "apt-get", "clean"],
            capture_output=True
        )

        # Remove temporary files
        for temp_dir in ["tmp/*", "var/tmp/*", "var/cache/apt/archives/*.deb"]:
            subprocess.run(
                ["rm", "-rf", f"{chroot_path}/{temp_dir}"],
                capture_output=True
            )

        # Create necessary directories
        for directory in ["tmp", "var/tmp"]:
            (chroot_path / directory).mkdir(exist_ok=True)
            (chroot_path / directory).chmod(0o1777)
