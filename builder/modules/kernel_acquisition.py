#!/usr/bin/env python3
# z-forge/builder/modules/kernel_acquisition.py

"""
Kernel Acquisition Module for Z-Forge.

This module is responsible for obtaining the Linux kernel that will be used
in the Z-Forge ISO. It can fetch the latest stable kernel version from
kernel.org or a specific version defined in the build configuration.

The module handles downloading the kernel source or Debian packages,
verifying integrity, installing into the chroot environment, and
generating an appropriate initramfs using dracut with ZFS support.
"""

import requests
import subprocess
import re
import tarfile
import hashlib
import shutil
import os
import time
from pathlib import Path
from typing import Dict, Optional, Tuple, Any, List
import logging

# Attempt to import GPG for signature verification, but don't make it a hard dependency
try:
    import gpg
    GPG_AVAILABLE = True
except ImportError:
    GPG_AVAILABLE = False
    gpg = None  # Make sure gpg is defined


class KernelAcquisition:
    """
    Handles the acquisition, verification, installation, and initramfs generation
    for the Linux kernel within the chroot environment.
    """
    
    def __init__(self, workspace: Path, config: Dict[str, Any]) -> None:
        """
        Initialize the KernelAcquisition module.

        Args:
            workspace: The path to the Z-Forge build workspace.
            config: The global build configuration dictionary.
        """
        self.workspace: Path = workspace
        self.config: Dict[str, Any] = config
        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)
        
        # Configure log level from config
        log_level = logging.INFO
        if self.config.get('builder_config', {}).get('enable_debug', False):
            log_level = logging.DEBUG
        self.logger.setLevel(log_level)
        
        # API endpoint to get information about kernel releases
        self.kernel_api_url: str = "https://www.kernel.org/releases.json"
        
        # Base URL for downloading kernel source tarballs
        self.kernel_download_base_url: str = "https://cdn.kernel.org/pub/linux/kernel"
        
        # Directory within the workspace to cache downloaded kernel files
        self.cache_dir: Path = self.workspace / "cache" / "kernels"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Path to the chroot environment
        self.chroot_path: Path = self.workspace / "chroot"
        
        # Whether to cache kernel packages
        self.should_cache = self.config.get('builder_config', {}).get('cache_packages', True)
        
        # Check if we should build from source or use Debian packages
        self.build_from_source = self.config.get('kernel_config', {}).get('build_from_source', False)
        
    def execute(self, resume_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the kernel acquisition process.

        Args:
            resume_data: Optional dictionary for resuming a previous build.

        Returns:
            A dictionary containing the status of the kernel acquisition.
        """
        self.logger.info("Starting Linux kernel acquisition process...")
        
        try:
            # Determine if we're working with ZFS native encryption
            zfs_encryption_enabled = self.config.get('zfs_config', {}).get('enable_encryption', False)
            if zfs_encryption_enabled:
                self.logger.info("ZFS native encryption is enabled - ensuring kernel has required support")
            
            # Determine the target kernel version from configuration
            kernel_version_config: str = self.config.get('builder_config', {}).get('kernel_version', 'latest')
            target_kernel_version: str
            
            if kernel_version_config == 'latest':
                target_kernel_version = self._get_latest_stable_kernel_version()
            else:
                target_kernel_version = kernel_version_config
                # Basic validation for version string format
                if not re.match(r"^\d+\.\d+(\.\d+)?(-\S+)?$", target_kernel_version):
                    raise ValueError(f"Invalid kernel version format: {target_kernel_version}. Expected X.Y or X.Y.Z.")

            self.logger.info(f"Target kernel version: {target_kernel_version}")
            
            # Check if this kernel has already been installed
            if resume_data and resume_data.get('status') == 'success' and resume_data.get('kernel_version') == target_kernel_version:
                self.logger.info(f"Kernel {target_kernel_version} processing previously completed. Checking installation...")
                
                vmlinuz_chroot_path, initrd_chroot_path = self._find_installed_kernel_paths(target_kernel_version)
                if vmlinuz_chroot_path and initrd_chroot_path:
                    self.logger.info(f"Found previously installed kernel {target_kernel_version}. Skipping reinstallation.")
                    return {
                        'status': 'success',
                        'kernel_version': target_kernel_version,
                        'vmlinuz_path': str(vmlinuz_chroot_path),
                        'initrd_path': str(initrd_chroot_path)
                    }
                else:
                    self.logger.warning(f"Could not find previously installed kernel {target_kernel_version}. Will proceed with installation.")

            # Ensure necessary packages for kernel installation
            self._prepare_chroot_environment(zfs_encryption_enabled)
            
            # Install kernel packages
            if self.build_from_source:
                # Source-based installation
                installed_kernel_version = self._install_kernel_from_source(target_kernel_version)
            else:
                # Debian package based installation
                installed_kernel_version = self._install_kernel_packages(target_kernel_version)
            
            self.logger.info(f"Successfully installed kernel version: {installed_kernel_version}")
            
            # Install ZFS kernel modules for the new kernel
            self._install_zfs_module(installed_kernel_version)
            
            # Generate dracut initramfs with ZFS support
            vmlinuz_path_in_chroot, initrd_path_in_chroot = self._generate_dracut_initramfs(
                installed_kernel_version, zfs_encryption_enabled
            )
            
            self.logger.info(f"Kernel acquisition and initramfs generation completed for {installed_kernel_version}")
            return {
                'status': 'success',
                'kernel_version': installed_kernel_version,
                'vmlinuz_path': str(vmlinuz_path_in_chroot),
                'initrd_path': str(initrd_path_in_chroot)
            }
            
        except Exception as e:
            self.logger.error(f"Kernel acquisition failed: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _run_chroot_command(self, command: List[str], check: bool = True, **kwargs) -> subprocess.CompletedProcess:
        """
        Helper to run commands inside the chroot environment.
        
        Args:
            command: The command to run within the chroot.
            check: Whether to raise an exception on non-zero exit codes.
            kwargs: Additional arguments to pass to subprocess.run.
            
        Returns:
            The completed process object.
        """
        # Ensure the chroot directory exists before attempting to run commands
        if not self.chroot_path.exists():
            raise FileNotFoundError(f"Chroot directory {self.chroot_path} does not exist. Has debootstrap been run?")
        
        # Prepare the full command
        full_cmd = ["chroot", str(self.chroot_path)] + command
        self.logger.info(f"Executing in chroot: {' '.join(command)}")
        
        # Run the command with specified options
        result = subprocess.run(full_cmd, check=check, capture_output=True, text=True, **kwargs)
        
        # Log output appropriately
        if result.stdout:
            self.logger.debug(f"Chroot command stdout: {result.stdout.strip()}")
        if result.stderr:
            log_level = logging.WARNING if result.returncode != 0 else logging.DEBUG
            self.logger.log(log_level, f"Chroot command stderr: {result.stderr.strip()}")
            
        return result

    def _get_latest_stable_kernel_version(self) -> str:
        """
        Fetch the latest stable kernel version from kernel.org API.
        
        Returns:
            The version string of the latest stable kernel.
            
        Raises:
            Various exceptions if fetching or parsing fails.
        """
        max_retries = 3
        for retry in range(max_retries):
            try:
                self.logger.info(f"Fetching latest stable kernel version from {self.kernel_api_url}...")
                
                response = requests.get(self.kernel_api_url, timeout=15)
                response.raise_for_status()  # Raise an exception for HTTP errors
                
                data = response.json()
                latest_stable_version = data['latest_stable']['version']
                
                self.logger.info(f"Latest stable kernel version found: {latest_stable_version}")
                return latest_stable_version
                
            except requests.RequestException as e:
                if retry < max_retries - 1:
                    wait_time = 2 ** retry  # Exponential backoff: 1, 2, 4 seconds
                    self.logger.warning(f"Request to kernel.org API failed. Retrying in {wait_time}s. Error: {e}")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Failed to fetch kernel version after {max_retries} attempts.")
                    raise
            except (KeyError, ValueError) as e:
                self.logger.error("Failed to parse kernel.org API response")
                raise
                
    def _prepare_chroot_environment(self, zfs_encryption_enabled: bool = False) -> None:
        """
        Prepare the chroot environment for kernel installation.
        
        Args:
            zfs_encryption_enabled: Whether ZFS encryption support is needed.
        """
        self.logger.info("Preparing chroot environment for kernel installation...")
        
        # Update package lists
        self._run_chroot_command(["apt-get", "update"])
        
        # Install necessary packages
        required_packages = [
            "dracut",
            "dracut-core",
            "linux-base",
            "initramfs-tools",
            "zfsutils-linux",
            "zfs-dkms",
            "dkms"
        ]
        
        # Add encryption-related packages if needed
        if zfs_encryption_enabled:
            required_packages.extend([
                "cryptsetup",
                "keyutils",
                "libpam-zfs"
            ])
        
        # For source builds, we need additional packages
        if self.build_from_source:
            required_packages.extend([
                "build-essential",
                "libncurses-dev",
                "bison",
                "flex",
                "libssl-dev",
                "libelf-dev",
                "bc"
            ])
        
        # Install all required packages
        self._run_chroot_command([
            "apt-get", "install", "-y", "--no-install-recommends"
        ] + required_packages)
        
        # Ensure /boot is properly mounted if it's a separate partition
        # This is normally handled by the earlier debootstrap module
        
        # Create directories needed for kernel modules
        os.makedirs(self.chroot_path / "lib" / "modules", exist_ok=True)
        
    def _install_kernel_packages(self, requested_version: str) -> str:
        """
        Install Debian kernel packages into the chroot environment.
        
        Args:
            requested_version: The desired kernel version.
            
        Returns:
            The actual installed kernel version.
        """
        self.logger.info(f"Installing kernel packages for version '{requested_version}'...")
        
        # Determine which packages to install
        # Parse the version to determine appropriate package names
        kernel_pkg_suffix = ""
        
        # If we have a specific Debian package version
        if re.match(r"^\d+\.\d+\.\d+-\d+(-[a-zA-Z0-9]+)+$", requested_version):
            kernel_image_pkg = f"linux-image-{requested_version}"
            kernel_headers_pkg = f"linux-headers-{requested_version}"
        # For major versions like 6.1, use metapackage or find best match
        elif requested_version == 'latest' or re.match(r"^\d+\.\d+(\.\d+)?$", requested_version):
            # Check for specific proxmox kernel first
            proxmox_major_version = self.config.get('proxmox_config', {}).get('version', 'latest')
            if proxmox_major_version == 'latest':
                # Use Proxmox 8.x kernel by default
                kernel_image_pkg = "proxmox-kernel-6.8"
                kernel_headers_pkg = "proxmox-kernel-headers-6.8"
            else:
                # Try to match based on Proxmox version
                # For now, hardcode some known good matchings
                if proxmox_major_version.startswith("8"):
                    kernel_image_pkg = "proxmox-kernel-6.8"
                    kernel_headers_pkg = "proxmox-kernel-headers-6.8"
                else:
                    kernel_image_pkg = "linux-image-amd64"
                    kernel_headers_pkg = "linux-headers-amd64"
        else:
            # Fallback to direct name
            kernel_image_pkg = f"linux-image-{requested_version}"
            kernel_headers_pkg = f"linux-headers-{requested_version}"
        
        # Install kernel packages
        try:
            # First attempt with specific packages
            self.logger.info(f"Installing kernel packages: {kernel_image_pkg}, {kernel_headers_pkg}")
            
            # Add Proxmox repositories if needed
            if "proxmox" in kernel_image_pkg:
                self._configure_proxmox_repo()
            
            # Install the kernel packages
            self._run_chroot_command([
                "apt-get", "install", "-y", "--no-install-recommends",
                kernel_image_pkg, kernel_headers_pkg
            ])
        except subprocess.CalledProcessError as e:
            # If first attempt failed, try fallback to generic packages
            if "proxmox" in kernel_image_pkg or kernel_image_pkg == "linux-image-amd64":
                # Already tried with metapackage, so this is a real error
                raise ValueError(f"Failed to install kernel packages: {e.stderr}")
            
            self.logger.warning(f"Failed to install specific kernel version. Trying generic metapackage.")
            kernel_image_pkg = "linux-image-amd64"
            kernel_headers_pkg = "linux-headers-amd64"
            
            self._run_chroot_command([
                "apt-get", "install", "-y", "--no-install-recommends",
                kernel_image_pkg, kernel_headers_pkg
            ])
        
        # Find the actual installed kernel version
        ls_result = self._run_chroot_command(["ls", "-1", "/lib/modules"])
        installed_versions = ls_result.stdout.strip().split('\n')
        
        if not installed_versions:
            raise ValueError("No kernel versions found in /lib/modules after installation")
        
        # Sort versions to find the highest or best match
        # For Debian-style version strings (e.g., 6.1.0-13-amd64), this naive sort is not accurate
        # but should work for selecting the most recently added version
        installed_versions.sort(key=self._sort_kernel_versions, reverse=True)
        
        # Try to find a version that matches the requested pattern
        target_version = ""
        
        # If a specific full version was requested
        if re.match(r"^\d+\.\d+\.\d+-\d+(-[a-zA-Z0-9]+)+$", requested_version):
            # Look for exact match
            if requested_version in installed_versions:
                target_version = requested_version
            # Otherwise assume the highest version
            else:
                target_version = installed_versions[0]
        # If a major/minor version was requested
        elif re.match(r"^\d+\.\d+(\.\d+)?$", requested_version):
            # Find the first version that starts with the requested version
            for version in installed_versions:
                if version.startswith(requested_version) or f"-{requested_version}-" in version:
                    target_version = version
                    break
            # If no match, use the highest
            if not target_version:
                target_version = installed_versions[0]
        # Otherwise, just use the highest
        else:
            target_version = installed_versions[0]
        
        self.logger.info(f"Identified installed kernel version: {target_version}")
        return target_version
    
    def _sort_kernel_versions(self, version: str) -> tuple:
        """
        Helper function for sorting kernel versions.
        
        Args:
            version: A kernel version string like 6.1.0-13-amd64
            
        Returns:
            A tuple that can be used for sorting versions
        """
        # Split into components
        if re.match(r"^\d+\.\d+\.\d+-\d+(-[a-zA-Z0-9]+)+$", version):
            # Format: X.Y.Z-ABI-flavor
            major, rest = version.split('.', 1)
            minor, rest = rest.split('.', 1)
            patch, rest = rest.split('-', 1)
            abi, flavor = rest.split('-', 1)
            
            # Return as sortable tuple
            return (int(major), int(minor), int(patch), int(abi), flavor)
        else:
            # If doesn't match expected format, use string sorting
            return (version,)
    
    def _configure_proxmox_repo(self) -> None:
        """
        Configure Proxmox repositories in the chroot environment.
        """
        self.logger.info("Configuring Proxmox repositories...")
        
        # Add repository key
        self._run_chroot_command([
            "bash", "-c", 
            "wget -qO- 'https://enterprise.proxmox.com/debian/proxmox-release-bookworm.gpg' | apt-key add -"
        ], check=False)  # apt-key is deprecated but still works
        
        # Add repository to sources.list.d
        sources_list = """# Proxmox kernel repositories
deb http://download.proxmox.com/debian/pve bookworm pve-no-subscription
"""
        # Write the sources list file
        sources_path = self.chroot_path / "etc" / "apt" / "sources.list.d" / "proxmox.list"
        with open(sources_path, "w") as f:
            f.write(sources_list)
        
        # Update package lists
        self._run_chroot_command(["apt-get", "update"])
    
    def _install_kernel_from_source(self, requested_version: str) -> str:
        """
        Build and install the Linux kernel from source.
        
        Args:
            requested_version: The desired kernel version.
            
        Returns:
            The actual installed kernel version.
        """
        self.logger.info(f"Building and installing kernel {requested_version} from source...")
        
        # Determine download URL for kernel source
        kernel_major = requested_version.split('.')[0]
        kernel_url = f"{self.kernel_download_base_url}/v{kernel_major}.x/linux-{requested_version}.tar.xz"
        
        # Create working directory in chroot
        build_dir = "/usr/src/linux-build"
        self._run_chroot_command(["mkdir", "-p", build_dir])
        
        # Download kernel source
        tar_path = f"/tmp/linux-{requested_version}.tar.xz"
        self._run_chroot_command([
            "wget", "-O", tar_path, kernel_url
        ])
        
        # Extract kernel source
        self._run_chroot_command([
            "tar", "-xf", tar_path, "-C", "/usr/src"
        ])
        
        # Configure kernel build
        src_dir = f"/usr/src/linux-{requested_version}"
        self._run_chroot_command([
            "cp", "/boot/config-$(uname -r)", f"{src_dir}/.config"
        ], check=False)  # May fail if config doesn't exist
        
        # Make sure ZFS config options are enabled
        zfs_config_options = """
CONFIG_ZFS=m
CONFIG_CRYPTO_CCM=y
CONFIG_CRYPTO_GCM=y
CONFIG_CRYPTO_CHACHA20POLY1305=y
CONFIG_ZLIB_DEFLATE=y
"""
        config_file = self.chroot_path / "usr" / "src" / f"linux-{requested_version}" / ".config"
        if config_file.exists():
            with open(config_file, "a") as f:
                f.write(zfs_config_options)
        
        # Build and install kernel
        self._run_chroot_command([
            "bash", "-c", f"cd {src_dir} && make olddefconfig && make -j$(nproc) && make modules_install && make install"
        ])
        
        # Find the installed kernel version
        ls_result = self._run_chroot_command(["ls", "-1", "/lib/modules"])
        installed_versions = ls_result.stdout.strip().split('\n')
        
        if not installed_versions:
            raise ValueError("No kernel versions found in /lib/modules after installation")
        
        # Sort by version and take the newest
        installed_versions.sort(key=self._sort_kernel_versions, reverse=True)
        target_version = installed_versions[0]
        
        self.logger.info(f"Built and installed kernel version: {target_version}")
        return target_version
    
    def _install_zfs_module(self, kernel_version: str) -> None:
        """
        Install ZFS kernel module for the specified kernel version.
        
        Args:
            kernel_version: The kernel version to install ZFS for.
        """
        self.logger.info(f"Installing ZFS module for kernel {kernel_version}...")
        
        # Ensure ZFS packages are installed
        self._run_chroot_command([
            "apt-get", "install", "-y", "zfs-dkms", "zfsutils-linux"
        ])
        
        # Build ZFS module for the kernel
        try:
            self._run_chroot_command([
                "dkms", "autoinstall", "-k", kernel_version
            ])
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"DKMS autoinstall failed: {e.stderr}")
            
            # Try more direct approach
            self._run_chroot_command([
                "dkms", "install", "zfs/2.2.0", "-k", kernel_version
            ], check=False)  # Don't fail if this doesn't work
            
        # Verify ZFS module was installed
        self.logger.info("Verifying ZFS module installation...")
        modules_path = self.chroot_path / "lib" / "modules" / kernel_version / "updates" / "dkms" / "zfs"
        
        if not modules_path.exists():
            self.logger.warning(f"ZFS module directory {modules_path} not found, but continuing anyway")

    def _find_installed_kernel_paths(self, kernel_version_str: str) -> Tuple[Optional[Path], Optional[Path]]:
        """
        Find paths to vmlinuz and initrd.img for the given kernel version.
        
        Args:
            kernel_version_str: The kernel version string.
            
        Returns:
            Paths to vmlinuz and initrd.img, or None if not found.
        """
        vmlinuz_path = Path("/boot") / f"vmlinuz-{kernel_version_str}"
        initrd_path = Path("/boot") / f"initrd.img-{kernel_version_str}"

        # Check if they exist within the chroot
        chroot_vmlinuz_path = self.chroot_path / vmlinuz_path.relative_to("/")
        chroot_initrd_path = self.chroot_path / initrd_path.relative_to("/")
        
        if not chroot_vmlinuz_path.exists():
            self.logger.warning(f"vmlinuz not found at {chroot_vmlinuz_path}")
            vmlinuz_path = None

        if not chroot_initrd_path.exists():
            self.logger.warning(f"initrd.img not found at {chroot_initrd_path}")
            initrd_path = None

        return vmlinuz_path, initrd_path
    
    def _generate_dracut_initramfs(self, kernel_version: str, include_encryption: bool = False) -> Tuple[Path, Path]:
        """
        Generate initramfs for the specified kernel using dracut with ZFS support.
        
        Args:
            kernel_version: The kernel version to generate initramfs for.
            include_encryption: Whether to include encryption support.
            
        Returns:
            Paths to vmlinuz and initrd.img.
        """
        self.logger.info(f"Generating dracut initramfs for kernel {kernel_version} with ZFS support...")

        # Define paths as seen from inside the chroot
        vmlinuz_path = Path("/boot") / f"vmlinuz-{kernel_version}"
        initrd_path = Path("/boot") / f"initrd.img-{kernel_version}"

        # Verify that vmlinuz exists
        chroot_vmlinuz_path = self.chroot_path / vmlinuz_path.relative_to("/")
        if not chroot_vmlinuz_path.exists():
            raise FileNotFoundError(f"Kernel image {vmlinuz_path} not found in chroot")

        # Create custom dracut.conf.d file for ZFS
        dracut_conf = """# ZFS dracut configuration
add_dracutmodules+=" zfs "
omit_dracutmodules+=" btrfs "
"""
        
        # Add encryption support if needed
        if include_encryption:
            dracut_conf += """
# ZFS encryption support
add_dracutmodules+=" crypt "
install_items+=" /usr/bin/zfs /usr/bin/zpool /lib/udev/zvol_id /lib/udev/vdev_id /etc/zfs/zroot.key "
"""
        
        # Write dracut configuration
        conf_path = self.chroot_path / "etc" / "dracut.conf.d" / "zfs.conf"
        conf_path.parent.mkdir(parents=True, exist_ok=True)
        with open(conf_path, "w") as f:
            f.write(dracut_conf)

        # Build dracut command
        dracut_cmd = [
            "dracut",
            "--force",  # Overwrite if exists
            "--verbose",  # More detailed output
            "--kver", kernel_version,  # Explicit kernel version
            str(initrd_path)  # Output file path
        ]
        
        # Run dracut command
        self._run_chroot_command(dracut_cmd)

        # Verify the initramfs was created
        chroot_initrd_path = self.chroot_path / initrd_path.relative_to("/")
        if not chroot_initrd_path.exists():
            raise FileNotFoundError(f"Failed to generate initramfs at {initrd_path}")

        self.logger.info(f"Successfully generated dracut initramfs with ZFS support at {initrd_path}")
        return vmlinuz_path, initrd_path
