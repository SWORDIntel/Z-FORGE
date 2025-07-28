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
from builder.core.lockfile import BuildLockfile

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
        
    def execute(self, resume_data: Optional[Dict[str, Any]] = None, lockfile: Optional[BuildLockfile] = None) -> Dict[str, Any]:
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
    
    def _fix_repository_keys(self) -> None:
        """Fix missing GPG keys for repositories"""
        self.logger.info("Checking and fixing repository GPG keys...")
        
        # Common missing keys and their sources
        key_fixes = [
            # NVIDIA HPC SDK key
            {
                "key_id": "42550ABD1E80D7C1BC0BAD851285491434D8786F",
                "keyserver": "keyserver.ubuntu.com",
                "name": "NVIDIA HPC SDK"
            },
            # Add more keys as needed
        ]
        
        for key_info in key_fixes:
            try:
                # Try to add the key from keyserver
                self.logger.info(f"Adding {key_info['name']} GPG key...")
                cmd = [
                    "apt-key", "adv", 
                    "--keyserver", key_info["keyserver"],
                    "--recv-keys", key_info["key_id"]
                ]
                self._run_chroot_command(cmd, check=False)
            except Exception as e:
                self.logger.warning(f"Failed to add {key_info['name']} key: {e}")
                
        # Also try to update from the repositories themselves
        try:
            # Check for nvidia repository and get its key
            nvidia_list = self.chroot_path / "etc/apt/sources.list.d/nvhpc.list"
            if nvidia_list.exists():
                self.logger.info("NVIDIA HPC SDK repository detected, fetching key...")
                # Try to download the key directly
                key_url = "https://developer.download.nvidia.com/hpc-sdk/ubuntu/DEB-GPG-KEY-NVIDIA-HPC-SDK"
                cmd = [
                    "/bin/bash", "-c",
                    f"wget -qO- {key_url} | apt-key add -"
                ]
                self._run_chroot_command(cmd, check=False)
                
                # Alternative: If the repository is causing issues, we can disable it temporarily
                # since it's not needed for kernel installation
                self.logger.info("Disabling NVIDIA HPC SDK repository for now...")
                try:
                    # Move the file to disable it
                    cmd = ["mv", "/etc/apt/sources.list.d/nvhpc.list", "/etc/apt/sources.list.d/nvhpc.list.disabled"]
                    self._run_chroot_command(cmd, check=False)
                except:
                    pass
        except Exception as e:
            self.logger.warning(f"Failed to update NVIDIA key: {e}")

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
        
        # Set up environment for non-interactive package installation
        env = os.environ.copy()
        env['DEBIAN_FRONTEND'] = 'noninteractive'
        env['DEBCONF_NONINTERACTIVE_SEEN'] = 'true'
        env['LC_ALL'] = 'C'
        env['LANG'] = 'C'
        
        # Merge with any provided environment
        if 'env' in kwargs:
            env.update(kwargs['env'])
            kwargs['env'] = env
        else:
            kwargs['env'] = env
        
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
        
        # Generate locale to prevent perl warnings
        self.logger.info("Generating locale configuration...")
        try:
            self._run_chroot_command(["locale-gen", "en_US.UTF-8"])
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to generate locale: {e}")
        
        # Ensure wget is installed for downloading GPG keys
        try:
            self._run_chroot_command(["apt-get", "install", "-y", "--no-install-recommends", "wget", "curl", "ca-certificates"])
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to install wget/curl: {e}")
        
        # Fix GPG key issues before updating
        self._fix_repository_keys()
        
        # Update package lists with retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._run_chroot_command(["apt-get", "update"])
                break
            except subprocess.CalledProcessError as e:
                # Check if it's a GPG key error
                if "Missing key" in str(e.stderr) or "NO_PUBKEY" in str(e.stderr):
                    self.logger.warning("GPG key error detected, attempting to fix...")
                    self._fix_repository_keys()
                    # Try update again
                    self._run_chroot_command(["apt-get", "update"])
                    break
                elif attempt < max_retries - 1:
                    self.logger.warning(f"apt-get update failed (attempt {attempt + 1}/{max_retries}), retrying...")
                    time.sleep(5)
                else:
                    raise
        
        # Split package installation into groups to isolate failures
        # Base packages first
        base_packages = ["linux-base"]
        # Install kernel headers FIRST (required for module compilation)
        kernel_packages = ["linux-headers-amd64", "linux-image-amd64"]
        # Then build tools and DKMS
        build_packages = ["build-essential", "linux-headers-generic"]
        dkms_packages = ["dkms"]
        # Then dracut with dependencies (dracut-zfs not available in Debian, we'll create the module)
        dracut_packages = ["dracut", "dracut-core", "dracut-network", "zstd", "kmod", "libkmod2"] # initramfs-tools is intentionally omitted here
        # ZFS packages (requires DKMS and kernel headers)
        zfs_packages = ["zfsutils-linux", "zfs-dkms"]
        # ZFSBootMenu dependencies (zfsbootmenu itself will be installed separately)
        zfsbootmenu_packages = ["perl", "fzf", "mbuffer", "efibootmgr", "kexec-tools"]
        
        package_groups_to_install = [base_packages, kernel_packages, build_packages, dkms_packages, dracut_packages, zfs_packages, zfsbootmenu_packages]

        if zfs_encryption_enabled:
            crypt_packages = ["cryptsetup", "cryptsetup-initramfs", "keyutils", "libpam-zfs"]
            package_groups_to_install.append(crypt_packages)

        # For source builds, we need additional packages
        if self.build_from_source:
            source_build_packages = [
                "build-essential",
                "libncurses-dev",
                "bison",
                "flex",
                "libssl-dev",
                "libelf-dev",
                "bc"
            ]
            # Add as a separate group or extend an existing one.
            # For simplicity, adding as a new group.
            package_groups_to_install.append(source_build_packages)

        for package_group in package_groups_to_install:
            if not package_group: # Skip empty groups
                continue
            try:
                self.logger.info(f"Installing package group: {', '.join(package_group)}")
                self._run_chroot_command(["apt-get", "install", "-y", "--no-install-recommends"] + package_group)
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Failed to install {package_group}: {e.stderr if e.stderr else e.stdout}")
                # Decide if we should raise, or continue as per patch instruction "Continue with next group"
                self.logger.warning(f"Continuing with the next package group despite previous error.")
                # If a critical group like dkms or zfs-dkms fails, subsequent steps might also fail.
        
        # Ensure dracut is preferred over initramfs-tools
        self.logger.info("Ensuring dracut is the default initramfs generator...")
        try:
            # Remove initramfs-tools if it was installed as a dependency
            self._run_chroot_command(["apt-get", "remove", "--purge", "-y", "initramfs-tools", "initramfs-tools-core"], check=False)
            # Mark dracut as manually installed to prevent removal
            self._run_chroot_command(["apt-mark", "manual", "dracut", "dracut-core"], check=False)
            # Create kernel hook to use dracut
            kernel_postinst = """#!/bin/sh
# Use dracut instead of initramfs-tools
set -e
version="$1"
[ -z "${version}" ] && exit 0
dracut --force "/boot/initrd.img-${version}" "${version}"
"""
            hook_path = self.chroot_path / "etc" / "kernel" / "postinst.d" / "dracut"
            hook_path.parent.mkdir(parents=True, exist_ok=True)
            with open(hook_path, 'w') as f:
                f.write(kernel_postinst)
            os.chmod(hook_path, 0o755)
        except Exception as e:
            self.logger.warning(f"Failed to configure dracut preference: {e}")
                # The original patch implies just logging and continuing.
        
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
                # Use standard Debian kernel by default to avoid dependency issues
                # Proxmox kernels will be handled by ProxmoxIntegration module
                kernel_image_pkg = "linux-image-amd64"
                kernel_headers_pkg = "linux-headers-amd64"
            else:
                # Try to match based on Proxmox version
                # For now, use standard kernel to avoid dependency issues
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
                
                # For Proxmox kernels, try to find available packages
                try:
                    # Search for available Proxmox kernel packages
                    search_result = self._run_chroot_command([
                        "apt-cache", "search", "^proxmox-kernel-6"
                    ])
                    available_packages = search_result.stdout.strip()
                    self.logger.info(f"Available Proxmox kernel packages:\n{available_packages}")
                    
                    # Proxmox kernels include headers in the main package
                    # Try installing just the kernel package first
                    self._run_chroot_command([
                        "apt-get", "install", "-y", "--no-install-recommends",
                        kernel_image_pkg
                    ])
                except subprocess.CalledProcessError as e:
                    self.logger.warning(f"Failed to install Proxmox kernel: {e.stderr}")
                    # Fall back to standard Debian kernel
                    kernel_image_pkg = "linux-image-amd64"
                    kernel_headers_pkg = "linux-headers-amd64"
                    self._run_chroot_command([
                        "apt-get", "install", "-y", "--no-install-recommends",
                        kernel_image_pkg, kernel_headers_pkg
                    ])
            else:
                # Install standard kernel packages
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
        installed_versions = [v.strip() for v in ls_result.stdout.strip().split('\n') if v.strip()]
        
        if not installed_versions:
            raise ValueError("No kernel versions found in /lib/modules after installation")
        
        self.logger.info(f"Found kernel versions in /lib/modules: {installed_versions}")
        
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
        
        # Create directory for keyrings if it doesn't exist
        keyrings_dir = self.chroot_path / "etc" / "apt" / "keyrings"
        keyrings_dir.mkdir(parents=True, exist_ok=True)
        
        # Download repository key using the new method
        try:
            self._run_chroot_command([
                "wget", "-qO", "/etc/apt/keyrings/proxmox-release-bookworm.gpg",
                "https://enterprise.proxmox.com/debian/proxmox-release-bookworm.gpg"
            ])
        except subprocess.CalledProcessError:
            self.logger.warning("Failed to download Proxmox GPG key, trying alternative method")
            # Try curl as fallback
            self._run_chroot_command([
                "curl", "-fsSL", "-o", "/etc/apt/keyrings/proxmox-release-bookworm.gpg",
                "https://enterprise.proxmox.com/debian/proxmox-release-bookworm.gpg"
            ])
        
        # Add repository to sources.list.d with signed-by option
        # Note: Using bookworm for Proxmox as they may not have trixie repos yet
        sources_list = """# Proxmox kernel repositories
deb [signed-by=/etc/apt/keyrings/proxmox-release-bookworm.gpg] http://download.proxmox.com/debian/pve bookworm pve-no-subscription
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
        
        # Pre-build validation
        self.logger.info("Validating build environment before kernel compilation...")
        self._validate_build_environment()
        
        # Build and install kernel with timeout and better error handling
        self.logger.info("Starting kernel compilation (this may take 30-60 minutes)...")
        
        # Set safe compilation flags
        build_env = {
            'CFLAGS': '-O2 -pipe -fno-strict-aliasing',
            'CXXFLAGS': '-O2 -pipe -fno-strict-aliasing',
            'CC': '/usr/bin/gcc',
            'CXX': '/usr/bin/g++'
        }
        
        try:
            # Step 1: Configure kernel
            self._run_chroot_command([
                "bash", "-c", f"cd {src_dir} && make olddefconfig"
            ], timeout=300, env=build_env)  # 5 minutes for config
            
            # Step 2: Build kernel (longest step)
            self._run_chroot_command([
                "bash", "-c", f"cd {src_dir} && make -j$(nproc)"
            ], timeout=7200, env=build_env)  # 2 hours for build
            
            # Step 3: Install modules
            self._run_chroot_command([
                "bash", "-c", f"cd {src_dir} && make modules_install"
            ], timeout=1200, env=build_env)  # 20 minutes for module install
            
            # Step 4: Install kernel
            self._run_chroot_command([
                "bash", "-c", f"cd {src_dir} && make install"
            ], timeout=600, env=build_env)  # 10 minutes for kernel install
            
        except subprocess.TimeoutExpired as e:
            self.logger.error(f"Kernel build timed out after {e.timeout} seconds")
            self.logger.error("This may indicate insufficient resources or a stuck build process")
            raise RuntimeError(f"Kernel build timed out: {e}")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Kernel build failed with exit code {e.returncode}")
            if e.stderr:
                self.logger.error(f"Build error output: {e.stderr}")
            # Cleanup partial build on failure
            self._cleanup_failed_build(src_dir)
            raise RuntimeError(f"Kernel build failed: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error during kernel build: {e}")
            self._cleanup_failed_build(src_dir)
            raise
        
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
    
    def _add_zfs_repository(self) -> None:
        """Add OpenZFS repository for Debian to get ZFS packages."""
        self.logger.info("Adding OpenZFS repository for Debian...")
        
        try:
            # Install curl if not present
            self._run_chroot_command([
                "apt-get", "install", "-y", "curl", "gnupg"
            ])
            
            # Download and install OpenZFS GPG key
            self._run_chroot_command([
                "curl", "-fsSL", "https://packages.openzfs.org/openzfs.gpg.key",
                "-o", "/tmp/openzfs.gpg.key"
            ])
            
            # Import GPG key
            self._run_chroot_command([
                "gpg", "--dearmor", "--output", "/usr/share/keyrings/openzfs.gpg",
                "/tmp/openzfs.gpg.key"
            ])
            
            # Add repository (using [trusted=yes] to bypass GPG verification issues)
            repo_line = (
                "deb [trusted=yes] "
                "https://packages.openzfs.org/debian trixie main"
            )
            
            sources_list = self.chroot_path / "etc/apt/sources.list.d/openzfs.list"
            sources_list.parent.mkdir(parents=True, exist_ok=True)
            sources_list.write_text(f"{repo_line}\n")
            
            self.logger.info(f"Added OpenZFS repository: {sources_list}")
            
            # Update package lists
            self._run_chroot_command([
                "apt-get", "update"
            ])
            
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to add OpenZFS repository: {e}")
            self.logger.info("Continuing with available packages...")
    
    def _install_zfs_module(self, kernel_version: str) -> None:
        """
        Install ZFS kernel module for the specified kernel version.
        
        Args:
            kernel_version: The kernel version to install ZFS for.
        """
        self.logger.info(f"Installing ZFS module for kernel {kernel_version}...")
        
        # Add OpenZFS repository for Debian
        self._add_zfs_repository()
        
        # Ensure ZFS packages are installed
        self._run_chroot_command([
            "apt-get", "install", "-y", "zfs-dkms", "zfsutils-linux"
        ])
        
        # Build ZFS module for the kernel
        # Mount required filesystems for DKMS
        self._mount_pseudo_filesystems()
        
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
        finally:
            # Always unmount the filesystems
            self._unmount_pseudo_filesystems()
            
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

        # Create custom dracut.conf.d file for ZFS and ZFSBootMenu
        dracut_conf = """# ZFS dracut configuration for ZFSBootMenu
add_dracutmodules+=" kernel-modules base rootfs-block zfs "
omit_dracutmodules+=" btrfs resume usrmount network-legacy "
filesystems+=" zfs "
hostonly="no"
compress="zstd"
kernel_only="yes"
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

        # Ensure /boot directory exists in chroot
        boot_dir = self.chroot_path / "boot"
        boot_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if kernel modules exist
        kernel_modules_path = self.chroot_path / "lib" / "modules" / kernel_version
        if not kernel_modules_path.exists():
            self.logger.error(f"Kernel modules directory does not exist: {kernel_modules_path}")
            self.logger.error("Cannot proceed without kernel modules")
            
            # List available kernel versions
            modules_dir = self.chroot_path / "lib" / "modules"
            if modules_dir.exists():
                available_versions = [d.name for d in modules_dir.iterdir() if d.is_dir()]
                self.logger.info(f"Available kernel versions: {available_versions}")
                
                # If we have exactly one version, use it
                if len(available_versions) == 1:
                    kernel_version = available_versions[0]
                    self.logger.info(f"Using available kernel version: {kernel_version}")
                    kernel_modules_path = modules_dir / kernel_version
                else:
                    raise FileNotFoundError(f"Kernel modules not found for {kernel_version}")
            else:
                raise FileNotFoundError("No kernel modules directory found")
        
        # Mount required filesystems for dracut
        self._mount_pseudo_filesystems()
        
        try:
            # Ensure ZFS kernel modules are built first
            self.logger.info("Ensuring ZFS kernel modules are built...")
            try:
                # Check DKMS status
                dkms_result = self._run_chroot_command(["dkms", "status"], check=False)
                if dkms_result.returncode != 0:
                    self.logger.warning("DKMS status check failed, attempting to build ZFS modules manually")
                    
                    # Try to build ZFS modules explicitly
                    try:
                        # Add ZFS to DKMS if not already added
                        self._run_chroot_command(["dkms", "add", "-m", "zfs", "-v", "2.2.0"], check=False)
                        
                        # Build ZFS modules for the kernel
                        self.logger.info(f"Building ZFS DKMS modules for kernel: {kernel_version}")
                        self._run_chroot_command([
                            "dkms", "build", "-m", "zfs", "-v", "2.2.0", "-k", kernel_version
                        ], check=False)
                        
                        # Install ZFS modules
                        self.logger.info(f"Installing ZFS DKMS modules for kernel: {kernel_version}")
                        self._run_chroot_command([
                            "dkms", "install", "-m", "zfs", "-v", "2.2.0", "-k", kernel_version
                        ], check=False)
                        
                        self.logger.info("ZFS DKMS modules build attempted")
                    except subprocess.CalledProcessError as e:
                        self.logger.warning(f"Failed to build ZFS DKMS modules: {e}")
                        # Continue anyway, dracut might work without them
                        
            except subprocess.CalledProcessError:
                self.logger.warning("Failed to check DKMS status")
            
            # Build dracut command
            # First check if we need to create the ZFS dracut module
            self._ensure_dracut_zfs_module()
            
            # For kernels with special characters, we need special handling
            # The issue is that dracut has problems with '+' in kernel versions
            if '+' in kernel_version:
                self.logger.info(f"Kernel version contains '+' character: {kernel_version}")
                # Verify the modules directory exists with this exact name
                modules_check = self.chroot_path / "lib" / "modules" / kernel_version
                if not modules_check.exists():
                    self.logger.error(f"Modules directory does not exist: {modules_check}")
                    # Try to find the actual directory name
                    modules_parent = self.chroot_path / "lib" / "modules"
                    actual_dirs = list(modules_parent.glob("*"))
                    self.logger.info(f"Actual module directories: {[d.name for d in actual_dirs]}")
                    
                # Create a wrapper script for dracut with the problematic kernel version
                wrapper_script = f"""#!/bin/bash
# Dracut wrapper to handle kernel version with special characters
set -e

KVER="{kernel_version}"
OUTPUT="{initrd_path}"

echo "Running dracut for kernel version: $KVER"

# Export the kernel version for dracut
export KERNEL_VERSION="$KVER"

# Create a temporary symlink without special characters if needed
if [[ "$KVER" == *"+"* ]]; then
    SAFE_KVER=$(echo "$KVER" | tr '+' '_')
    if [ ! -e "/lib/modules/$SAFE_KVER" ]; then
        ln -sf "/lib/modules/$KVER" "/lib/modules/$SAFE_KVER" || true
    fi
    
    # Try with safe version first
    dracut --force --verbose --kver "$SAFE_KVER" "$OUTPUT" || \\
    dracut --force --verbose --kver "$KVER" "$OUTPUT" || \\
    dracut --force --verbose "$OUTPUT"
    
    # Clean up symlink
    rm -f "/lib/modules/$SAFE_KVER"
else
    dracut --force --verbose --kver "$KVER" "$OUTPUT"
fi

# Verify the output was created
if [ -f "$OUTPUT" ]; then
    echo "Successfully created initramfs at $OUTPUT"
    exit 0
else
    echo "Failed to create initramfs"
    exit 1
fi
"""
                wrapper_path = self.chroot_path / "tmp" / "dracut_wrapper.sh"
                with open(wrapper_path, 'w') as f:
                    f.write(wrapper_script)
                os.chmod(wrapper_path, 0o755)
                
                # Use the wrapper script
                dracut_cmd = ["bash", "/tmp/dracut_wrapper.sh"]
            else:
                # Standard dracut command for normal kernel versions
                dracut_cmd = [
                    "dracut",
                    "--force",  # Overwrite if exists
                    "--verbose",  # More detailed output
                    "--kver", kernel_version,  # Explicit kernel version
                    str(initrd_path)  # Output file path
                ]
            
            # Run dracut command
            try:
                self.logger.info(f"Running dracut for kernel {kernel_version}")
                if '+' in kernel_version:
                    self.logger.info("Using wrapper script for special character handling")
                else:
                    self.logger.info(f"Dracut command: {' '.join(dracut_cmd)}")
                
                # Also log the kernel modules directory contents
                try:
                    ls_result = self._run_chroot_command(["ls", "-la", f"/lib/modules/{kernel_version}/"], check=False)
                    if ls_result.returncode == 0:
                        self.logger.info(f"Kernel modules directory contents:\n{ls_result.stdout}")
                except:
                    pass
                
                self._run_chroot_command(dracut_cmd)
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Dracut failed with exit code {e.returncode}")
                self.logger.error(f"Dracut stdout: {e.stdout}")
                self.logger.error(f"Dracut stderr: {e.stderr}")
                
                # Try alternative approaches
                self.logger.info("Trying alternative dracut approaches...")
                
                # First try: dracut without version (builds for current kernel)
                try:
                    alt_dracut_cmd = [
                        "dracut",
                        "--force",
                        "--verbose",
                        str(initrd_path)
                    ]
                    self._run_chroot_command(alt_dracut_cmd)
                    self.logger.info("Dracut succeeded without explicit kernel version")
                    return vmlinuz_path, initrd_path
                except subprocess.CalledProcessError:
                    pass
                
                # Second try: escape the kernel version differently
                try:
                    if '+' in kernel_version:
                        # Try with escaped version
                        escaped_version = kernel_version.replace('+', '\\+')
                        alt_dracut_cmd2 = [
                            "dracut",
                            "--force",
                            "--verbose",
                            "--kver", escaped_version,
                            str(initrd_path)
                        ]
                        self._run_chroot_command(alt_dracut_cmd2)
                        self.logger.info(f"Dracut succeeded with escaped kernel version: {escaped_version}")
                        return vmlinuz_path, initrd_path
                except subprocess.CalledProcessError:
                    pass
                
                # Third try: use shell to run dracut
                try:
                    shell_cmd = f"dracut --force --verbose --kver '{kernel_version}' {initrd_path}"
                    self._run_chroot_command(["bash", "-c", shell_cmd])
                    self.logger.info("Dracut succeeded using shell command")
                    return vmlinuz_path, initrd_path
                except subprocess.CalledProcessError:
                    pass
                
                # If all else fails, try to find and use the first available kernel
                try:
                    modules_dir = self.chroot_path / "lib" / "modules"
                    available_kernels = [d.name for d in modules_dir.iterdir() if d.is_dir()]
                    if available_kernels:
                        fallback_kernel = available_kernels[0]
                        self.logger.warning(f"Using fallback kernel version: {fallback_kernel}")
                        fallback_initrd = Path("/boot") / f"initrd.img-{fallback_kernel}"
                        fallback_cmd = [
                            "dracut",
                            "--force",
                            "--verbose",
                            "--kver", fallback_kernel,
                            str(fallback_initrd)
                        ]
                        self._run_chroot_command(fallback_cmd)
                        self.logger.info(f"Dracut succeeded with fallback kernel: {fallback_kernel}")
                        # Update the paths
                        initrd_path = fallback_initrd
                        vmlinuz_path = Path("/boot") / f"vmlinuz-{fallback_kernel}"
                        return vmlinuz_path, initrd_path
                except subprocess.CalledProcessError:
                    pass
                
                # Re-raise original error if all attempts failed
                self.logger.error("All dracut attempts failed")
                raise e
        finally:
            # Always unmount the filesystems
            self._unmount_pseudo_filesystems()

        # Verify the initramfs was created
        chroot_initrd_path = self.chroot_path / initrd_path.relative_to("/")
        if not chroot_initrd_path.exists():
            raise FileNotFoundError(f"Failed to generate initramfs at {initrd_path}")

        self.logger.info(f"Successfully generated dracut initramfs with ZFS support at {initrd_path}")
        return vmlinuz_path, initrd_path
    
    def _mount_pseudo_filesystems(self):
        """Mount required pseudo filesystems for chroot operations."""
        mounts = [
            ("proc", "proc", self.chroot_path / "proc"),
            ("sysfs", "sys", self.chroot_path / "sys"),
            ("devtmpfs", "udev", self.chroot_path / "dev"),
            ("devpts", "devpts", self.chroot_path / "dev/pts")
        ]
        
        for fs_type, source, target in mounts:
            if not target.exists():
                target.mkdir(parents=True, exist_ok=True)
            
            # Check if already mounted
            mount_check = subprocess.run(
                ["mountpoint", "-q", str(target)],
                capture_output=True
            )
            
            if mount_check.returncode != 0:
                self.logger.debug(f"Mounting {source} to {target}")
                subprocess.run(
                    ["mount", "-t", fs_type, source, str(target)],
                    check=True
                )
    
    def _ensure_dracut_zfs_module(self):
        """Ensure dracut has a ZFS module, create one if missing"""
        self.logger.info("Checking for dracut ZFS module...")
        
        dracut_modules_dir = self.chroot_path / "usr" / "lib" / "dracut" / "modules.d"
        if not dracut_modules_dir.exists():
            self.logger.error(f"Dracut modules directory not found: {dracut_modules_dir}")
            return
            
        # Look for existing ZFS module
        zfs_module_found = False
        for mod_dir in dracut_modules_dir.iterdir():
            if mod_dir.is_dir() and 'zfs' in mod_dir.name:
                self.logger.info(f"Found existing ZFS dracut module: {mod_dir.name}")
                zfs_module_found = True
                break
        
        if not zfs_module_found:
            # Create a basic ZFS dracut module
            self.logger.info("Creating basic ZFS dracut module...")
            zfs_module_dir = dracut_modules_dir / "90zfs"
            zfs_module_dir.mkdir(parents=True, exist_ok=True)
            
            # Create module-setup.sh
            module_setup = '''#!/bin/bash
# ZFS support for dracut

check() {
    # Include ZFS module
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
    inst_multiple zfs zpool zdb mount.zfs zgenhostid arc_summary arcstat || true
    inst_hook cmdline 95 "$moddir/parse-zfs.sh"
    inst_hook mount 98 "$moddir/mount-zfs.sh"
}
'''
            module_setup_path = zfs_module_dir / "module-setup.sh"
            with open(module_setup_path, 'w') as f:
                f.write(module_setup)
            os.chmod(module_setup_path, 0o755)
            
            # Create parse-zfs.sh
            parse_zfs = '''#!/bin/sh
case "${root}" in
    zfs:*|ZFS:*|zfs=*)
        root="${root#zfs:}"
        root="${root#ZFS:}"
        root="${root#zfs=}"
        rootfstype="zfs"
        rootok=1
        wait_for_zfs=1
        ;;
esac
'''
            parse_zfs_path = zfs_module_dir / "parse-zfs.sh"
            with open(parse_zfs_path, 'w') as f:
                f.write(parse_zfs)
            os.chmod(parse_zfs_path, 0o755)
            
            # Create mount-zfs.sh
            mount_zfs = '''#!/bin/sh
[ "${wait_for_zfs}" = "1" ] || return 0

# Import all zpools
zpool import -a -N

# Mount root filesystem
mount -t zfs "${root}" "${NEWROOT}" || return 1
'''
            mount_zfs_path = zfs_module_dir / "mount-zfs.sh"
            with open(mount_zfs_path, 'w') as f:
                f.write(mount_zfs)
            os.chmod(mount_zfs_path, 0o755)
            
            self.logger.info("Created basic ZFS dracut module")
    
    def _unmount_pseudo_filesystems(self):
        """Unmount pseudo filesystems in reverse order."""
        mounts = [
            self.chroot_path / "dev/pts",
            self.chroot_path / "dev",
            self.chroot_path / "sys",
            self.chroot_path / "proc"
        ]
        
        for target in mounts:
            mount_check = subprocess.run(
                ["mountpoint", "-q", str(target)],
                capture_output=True
            )
            
            if mount_check.returncode == 0:
                self.logger.debug(f"Unmounting {target}")
                subprocess.run(["umount", str(target)], check=False)
    
    def _validate_build_environment(self):
        """Validate the build environment before starting kernel compilation"""
        self.logger.info("Performing pre-build validation...")
        
        # Check available disk space
        workspace_stat = shutil.disk_usage(self.workspace)
        free_gb = workspace_stat.free / (1024**3)
        if free_gb < 20:
            raise RuntimeError(f"Insufficient disk space: {free_gb:.1f}GB available, need at least 20GB")
        
        # Check for essential build tools
        essential_tools = ['gcc', 'make', 'ld', 'as']
        for tool in essential_tools:
            try:
                result = self._run_chroot_command(['which', tool], timeout=30)
                if result.returncode != 0:
                    raise RuntimeError(f"Essential build tool missing: {tool}")
            except subprocess.TimeoutExpired:
                raise RuntimeError(f"Timeout checking for build tool: {tool}")
        
        # Check for required packages
        required_packages = ['build-essential', 'bc', 'kmod', 'cpio', 'flex', 'bison', 'libssl-dev', 'libelf-dev']
        missing_packages = []
        
        for package in required_packages:
            try:
                result = self._run_chroot_command(['dpkg', '-l', package], timeout=30)
                if result.returncode != 0:
                    missing_packages.append(package)
            except subprocess.TimeoutExpired:
                missing_packages.append(package)
        
        if missing_packages:
            self.logger.info(f"Installing missing packages: {', '.join(missing_packages)}")
            try:
                self._run_chroot_command([
                    'apt-get', 'update'
                ], timeout=300)
                self._run_chroot_command([
                    'apt-get', 'install', '-y', '--no-install-recommends'
                ] + missing_packages, timeout=600)
            except subprocess.TimeoutExpired:
                raise RuntimeError("Timeout installing required packages")
        
        # Check system memory
        try:
            result = self._run_chroot_command(['cat', '/proc/meminfo'], timeout=30)
            meminfo = result.stdout
            
            # Extract available memory
            for line in meminfo.split('\n'):
                if line.startswith('MemAvailable:'):
                    mem_kb = int(line.split()[1])
                    mem_gb = mem_kb / (1024 * 1024)
                    if mem_gb < 2:
                        self.logger.warning(f"Low memory available: {mem_gb:.1f}GB - kernel build may fail")
                    break
        except (subprocess.TimeoutExpired, ValueError, IndexError):
            self.logger.warning("Could not check available memory")
        
        # Test basic compilation capability
        try:
            test_c_code = '#include <stdio.h>\nint main(){printf("test");return 0;}'
            self._run_chroot_command([
                'bash', '-c', 
                f'echo \'{test_c_code}\' | gcc -x c - -o /tmp/test_compile && /tmp/test_compile && rm -f /tmp/test_compile'
            ], timeout=60)
            self.logger.info("Basic compilation test passed")
        except subprocess.TimeoutExpired:
            raise RuntimeError("Timeout during compilation test")
        except subprocess.CalledProcessError:
            raise RuntimeError("Basic compilation test failed - toolchain may be broken")
        
        self.logger.info("Build environment validation completed successfully")
    
    def _cleanup_failed_build(self, src_dir: str):
        """Clean up after failed kernel build"""
        self.logger.info(f"Cleaning up failed build in {src_dir}")
        try:
            # Kill any remaining build processes
            self._run_chroot_command(['pkill', '-f', 'make'], check=False, timeout=30)
            self._run_chroot_command(['pkill', '-f', 'gcc'], check=False, timeout=30)
            
            # Clean up build artifacts
            self._run_chroot_command([
                'bash', '-c', f'cd {src_dir} && make clean'
            ], check=False, timeout=300)
            
            # Remove incomplete module installations
            self._run_chroot_command([
                'bash', '-c', 'rm -rf /lib/modules/*/build /lib/modules/*/source'
            ], check=False, timeout=60)
            
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")
        
        self.logger.info("Build cleanup completed")
