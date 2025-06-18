#!/usr/bin/env python3
# z-forge/builder/modules/kernel_acquisition.py

"""
Kernel Acquisition Module for Z-Forge.

This module is responsible for obtaining the Linux kernel that will be used
in the Z-Forge ISO. It can fetch the latest stable kernel version from
kernel.org or a specific version defined in the build configuration.
The module handles downloading the kernel source (or precompiled binaries if
that strategy were adopted, though typically source/debs for integration),
verifying its integrity, installing it into the chroot environment, and
then generating an appropriate initramfs using dracut. It also supports
caching downloaded kernels to speed up subsequent builds.
"""

import requests
import subprocess
import re
import tarfile
import hashlib
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple, Any, List
import logging

# Attempt to import GPG for signature verification, but don't make it a hard dependency
try:
    import gpg
    GPG_AVAILABLE = True
except ImportError:
    GPG_AVAILABLE = False
    gpg = None # Make sure gpg is defined


class KernelAcquisition:
    """
    Handles the acquisition, verification, installation, and initramfs generation
    for the Linux kernel within the chroot environment.
    """
    
    def __init__(self, workspace: Path, config: Dict[str, Any]) -> None:
        """
        Initialize the KernelAcquisition module.

        Args:
            workspace: The path to the Z-Forge build workspace. Kernel files
                       will be downloaded to a cache within this workspace,
                       and installation occurs into `workspace/chroot`.
            config: The global build configuration dictionary, containing settings
                    like the desired kernel version and caching preferences.
        """
        self.workspace: Path = workspace
        self.config: Dict[str, Any] = config
        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)
        # API endpoint to get information about kernel releases.
        self.kernel_api_url: str = "https://www.kernel.org/releases.json"
        # Base URL for downloading kernel source tarballs.
        self.kernel_download_base_url: str = "https://cdn.kernel.org/pub/linux/kernel"
        # Directory within the workspace to cache downloaded kernel files.
        self.cache_dir: Path = self.workspace / "cache" / "kernels"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.chroot_path: Path = self.workspace / "chroot"
        
    def execute(self, resume_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Fetch, verify, install the Linux kernel, and generate its initramfs.

        This is the main entry point for the module. It determines the target
        kernel version (latest stable or specific), checks if it's cached,
        downloads and verifies if not, installs it into the chroot, and finally
        triggers dracut to generate the initramfs.

        Args:
            resume_data: Optional dictionary for resuming. (Not heavily used here
                         beyond potentially skipping if a kernel is marked as installed).

        Returns:
            A dictionary containing the status of the kernel acquisition.
            On success: {'status': 'success', 'kernel_version': str,
                         'vmlinuz_path': str, 'initrd_path': str}
            On failure: {'status': 'error', 'error': str, 'module': str}
        """
        
        self.logger.info("Starting Linux kernel acquisition process...")
        
        try:
            # Determine the target kernel version from configuration.
            kernel_version_config: str = self.config.get('builder_config', {}).get('kernel_version', 'latest')
            target_kernel_version: str
            if kernel_version_config == 'latest':
                target_kernel_version = self._get_latest_stable_kernel_version()
            else:
                target_kernel_version = kernel_version_config
                # Basic validation for version string format (e.g., X.Y.Z)
                if not re.match(r"^\d+\.\d+(\.\d+)?(-\S+)?$", target_kernel_version):
                    raise ValueError(f"Invalid kernel version format: {target_kernel_version}. Expected X.Y or X.Y.Z.")

            self.logger.info(f"Target kernel version: {target_kernel_version}")
            
            # Check if this specific kernel version's .deb packages are already installed (simplistic check)
            # A more robust check would involve querying dpkg status in chroot.
            # For now, we assume if _generate_dracut_initramfs finds the kernel, it's "installed".
            # This module focuses on acquisition and initial install/initramfs.
            # Let's assume for now that if resume_data indicates prior success for this module, we can skip.
            if resume_data and resume_data.get('status') == 'success' and resume_data.get('kernel_version') == target_kernel_version:
                 self.logger.info(f"Kernel {target_kernel_version} processing previously marked as successful. Skipping full acquisition.")
                 # Attempt to find paths even if skipping full run, needed for return value.
                 vmlinuz_chroot_path, initrd_chroot_path = self._find_installed_kernel_paths(target_kernel_version)
                 if vmlinuz_chroot_path and initrd_chroot_path:
                    return {
                        'status': 'success',
                        'kernel_version': target_kernel_version,
                        'vmlinuz_path': str(vmlinuz_chroot_path),
                        'initrd_path': str(initrd_chroot_path)
                    }
                 else:
                    self.logger.warning(f"Could not find installed kernel {target_kernel_version} during resume. Proceeding with full acquisition.")


            # For simplicity, this example will focus on installing pre-built Debian kernel packages.
            # Building kernel from source is a more complex process.
            # We'll try to install kernel and headers matching target_kernel_version or latest available.
            
            # Install kernel packages into the chroot
            installed_kernel_package_version = self._install_kernel_packages(target_kernel_version)
            self.logger.info(f"Successfully installed kernel packages for version: {installed_kernel_package_version}")
            
            # Generate dracut initramfs for the installed kernel.
            # The version used by dracut will be the one just installed.
            vmlinuz_path_in_chroot, initrd_path_in_chroot = self._generate_dracut_initramfs(installed_kernel_package_version)
            
            self.logger.info(f"Kernel acquisition and initramfs generation for {installed_kernel_package_version} completed.")
            return {
                'status': 'success',
                'kernel_version': installed_kernel_package_version, # Actual installed version
                'vmlinuz_path': str(vmlinuz_path_in_chroot), # Path inside chroot
                'initrd_path': str(initrd_path_in_chroot)    # Path inside chroot
            }
            
        except Exception as e:
            self.logger.error(f"Kernel acquisition process failed: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _run_chroot_command(self, command: List[str], check: bool = True, **kwargs) -> subprocess.CompletedProcess:
        """Helper to run commands inside the chroot."""
        full_cmd = ["chroot", str(self.chroot_path)] + command
        self.logger.info(f"Executing in chroot: {' '.join(command)}")
        # Allow passing other subprocess.run arguments like 'env'
        result = subprocess.run(full_cmd, check=check, capture_output=True, text=True, **kwargs)
        if result.stdout:
            self.logger.debug(f"Chroot command stdout: {result.stdout.strip()}")
        if result.stderr:
             # Stderr is not always an error, can be progress or warnings
            self.logger.debug(f"Chroot command stderr: {result.stderr.strip()}")
        return result

    def _get_latest_stable_kernel_version(self) -> str:
        """
        Fetch the latest stable kernel version from kernel.org API.

        Returns:
            The version string of the latest stable kernel (e.g., "6.5.8").

        Raises:
            requests.RequestException: If fetching from kernel.org API fails.
            KeyError: If the API response format is unexpected.
        """
        self.logger.info(f"Fetching latest stable kernel version from {self.kernel_api_url}...")
        response = requests.get(self.kernel_api_url, timeout=10)
        response.raise_for_status() # Raise an exception for HTTP errors
        data = response.json()
        # "stable" entry should contain the latest stable release.
        latest_stable_version = data['latest_stable']['version']
        self.logger.info(f"Latest stable kernel version found: {latest_stable_version}")
        return latest_stable_version

    def _install_kernel_packages(self, requested_version: str) -> str:
        """
        Install Linux kernel and header packages into the chroot environment
        using APT. It tries to install a specific version if a full version
        string (like X.Y.Z-ABI-flavor) is given, or the latest available
        for a major version (like X.Y).

        Args:
            requested_version: The desired kernel version string. Can be full
                               (e.g., "6.1.0-13-amd64") or partial (e.g., "6.1").
                               If 'latest', it will try to install the latest available
                               Debian packaged kernel.
        
        Returns:
            The actual version string of the kernel package installed.
        
        Raises:
            subprocess.CalledProcessError: If APT commands fail.
            ValueError: If the kernel package cannot be found or installed.
        """
        self.logger.info(f"Attempting to install kernel packages for version '{requested_version}' into chroot...")
        self._run_chroot_command(["apt-get", "update"])

        # Construct package names. Debian kernel packages are often like:
        # linux-image-X.Y.Z-ABI-flavor or linux-image-amd64 (metapackage)
        # linux-headers-X.Y.Z-ABI-flavor or linux-headers-amd64 (metapackage)
        
        # If a full version like "6.1.0-13-amd64" is given:
        if re.match(r"^\d+\.\d+\.\d+-\d+(-[a-zA-Z0-9]+)+$", requested_version):
            kernel_image_pkg = f"linux-image-{requested_version}"
            kernel_headers_pkg = f"linux-headers-{requested_version}"
        # If a version like "6.1" or "6.1.20" is given, try to find related packages.
        # This is more complex as APT needs specific versions or metapackages.
        # A common approach is to use a metapackage or search for available versions.
        # For simplicity, we'll try a generic approach first, then a more specific one.
        elif requested_version == 'latest' or re.match(r"^\d+\.\d+(\.\d+)?$", requested_version):
            # Try installing the generic metapackage for amd64 first.
            # This usually points to the default kernel for the Debian release.
            kernel_image_pkg = "linux-image-amd64"
            kernel_headers_pkg = "linux-headers-amd64"
            self.logger.info(f"Installing generic metapackages: {kernel_image_pkg}, {kernel_headers_pkg}")
        else: # Fallback for other formats, try direct name
            kernel_image_pkg = f"linux-image-{requested_version}"
            kernel_headers_pkg = f"linux-headers-{requested_version}"

        try:
            self.logger.info(f"Attempting to install: {kernel_image_pkg} and {kernel_headers_pkg}")
            self._run_chroot_command(["apt-get", "install", "-y", "--no-install-recommends", kernel_image_pkg, kernel_headers_pkg])
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to install specific version {kernel_image_pkg}. Error: {e.stderr}")
            # If specific version fails, and it was 'latest' or partial, try generic metapackage if not already tried
            if (requested_version == 'latest' or re.match(r"^\d+\.\d+(\.\d+)?$", requested_version)) and \
               (kernel_image_pkg != "linux-image-amd64"):
                self.logger.info("Trying to install generic 'linux-image-amd64' and 'linux-headers-amd64' as fallback.")
                kernel_image_pkg = "linux-image-amd64"
                kernel_headers_pkg = "linux-headers-amd64"
                self._run_chroot_command(["apt-get", "install", "-y", "--no-install-recommends", kernel_image_pkg, kernel_headers_pkg])
            else:
                raise ValueError(f"Could not install kernel packages for version {requested_version}. Error: {e.stderr}")

        # After installation, determine the exact kernel version installed.
        # This can be found by looking at /lib/modules/ in the chroot.
        # Debian kernel package installs to /boot/vmlinuz-VERSION and /lib/modules/VERSION

        # Find the installed kernel version string from /lib/modules
        # There might be multiple versions if others were previously installed. We need the newest or specific one.
        # This command lists directories in /lib/modules, which correspond to kernel versions.
        # We assume the last one alphabetically is the newest/target if multiple match.
        # A more robust way is to parse dpkg output or check symlinks like /vmlinuz.

        ls_cmd_result = self._run_chroot_command(["ls", "-1", "/lib/modules"])
        installed_versions = [v for v in ls_cmd_result.stdout.strip().split('\n') if v] # Filter empty lines

        if not installed_versions:
            raise ValueError("No kernel versions found in /lib/modules after installation attempt.")

        # Try to find a version that matches the requested_version pattern or is the highest.
        # If 'linux-image-amd64' was installed, it's a meta-package, and we need to find the actual version.
        target_installed_version = ""
        if kernel_image_pkg == "linux-image-amd64": # Metapackage was installed
            # The actual version is likely the highest version number present.
            # This sorting works for typical Debian versions like X.Y.Z-ABI-flavor
            installed_versions.sort(reverse=True)
            if installed_versions:
                target_installed_version = installed_versions[0]
            else: # Should not happen if apt-get install succeeded
                 raise ValueError("Metapackage linux-image-amd64 installed but no kernel found in /lib/modules.")
        else: # A specific version was targeted
            # Try to find the one that matches the specific request (e.g., contains requested_version string)
            # or simply the highest one if direct match is hard.
            best_match = ""
            for v_str in sorted(installed_versions, reverse=True): # Sort to get latest if multiple partial matches
                if requested_version in v_str: # Simplistic match
                    best_match = v_str
                    break
            if best_match:
                target_installed_version = best_match
            elif installed_versions: # Fallback to highest if no good string match
                target_installed_version = installed_versions[0]
            else:
                raise ValueError(f"Could not determine installed kernel version for {requested_version}.")

        self.logger.info(f"Identified installed kernel version as: {target_installed_version}")
        return target_installed_version

    def _find_installed_kernel_paths(self, kernel_version_str: str) -> Tuple[Optional[Path], Optional[Path]]:
        """
        Finds the paths to vmlinuz and initrd.img for a given kernel version string
        within the chroot environment.

        Args:
            kernel_version_str: The kernel version string (e.g., "6.1.0-13-amd64").

        Returns:
            A tuple (vmlinuz_path, initrd_path), where paths are relative to chroot root.
            Returns (None, None) if not found.
        """
        vmlinuz_path = Path("/boot") / f"vmlinuz-{kernel_version_str}"
        initrd_path = Path("/boot") / f"initrd.img-{kernel_version_str}"

        # Check if they exist within the chroot
        if not (self.chroot_path / vmlinuz_path.relative_to("/")).exists():
            self.logger.warning(f"vmlinuz not found at {self.chroot_path / vmlinuz_path.relative_to('/')}")
            vmlinuz_path = None

        if not (self.chroot_path / initrd_path.relative_to("/")).exists():
            # Dracut might not have run yet if we are resuming a very early stage
            self.logger.warning(f"initrd.img not found at {self.chroot_path / initrd_path.relative_to('/')}. May need dracut run.")
            # initrd_path = None # Keep it as a target path for dracut

        return vmlinuz_path, initrd_path


    def _generate_dracut_initramfs(self, kernel_version: str) -> Tuple[Path, Path]:
        """
        Generate the initramfs for the specified kernel version using dracut
        within the chroot environment.

        Args:
            kernel_version: The kernel version string (e.g., "6.1.0-13-amd64")
                            for which to generate the initramfs.

        Returns:
            A tuple containing the chroot-relative paths to the generated
            vmlinuz and initrd image (e.g., Path("/boot/vmlinuz-..."), Path("/boot/initrd.img-...")).
            The vmlinuz path is mostly for confirmation as dracut primarily creates initrd.

        Raises:
            subprocess.CalledProcessError: If dracut command fails.
            FileNotFoundError: If the kernel (vmlinuz) for the version is not found.
        """
        self.logger.info(f"Generating dracut initramfs for kernel {kernel_version} in chroot...")

        # Define paths for kernel image and output initramfs within the chroot.
        # These paths are as seen from *inside* the chroot.
        vmlinuz_chroot_path = Path("/boot") / f"vmlinuz-{kernel_version}"
        initrd_chroot_path = Path("/boot") / f"initrd.img-{kernel_version}"

        # Verify that the kernel (vmlinuz image) actually exists in the chroot.
        if not (self.chroot_path / vmlinuz_chroot_path.relative_to("/")).exists():
            raise FileNotFoundError(f"Kernel image {vmlinuz_chroot_path} not found in chroot at "
                                    f"{self.chroot_path / vmlinuz_chroot_path.relative_to('/')}. Cannot generate initramfs.")

        # Construct and run the dracut command within the chroot.
        # --force: Overwrite existing initramfs.
        # The last argument is the kernel version for which to build the initramfs.
        dracut_cmd: List[str] = [
            "dracut",
            "--force", # Overwrite if exists
            # Add any Z-Forge specific dracut arguments from config if necessary
            # e.g., --add-drivers "module1 module2"
            # "--verbose", # For more detailed output if needed for debugging
            str(initrd_chroot_path), # Output file path for initramfs
            kernel_version           # Kernel version to build for
        ]
        self._run_chroot_command(dracut_cmd)

        self.logger.info(f"Dracut initramfs generated successfully for kernel {kernel_version} at {initrd_chroot_path}.")

        # Return the chroot-relative paths to the kernel and initramfs.
        return vmlinuz_chroot_path, initrd_chroot_path

# Placeholder for methods like _check_cache, _download_kernel, _verify_kernel, _install_kernel (from source), _cache_kernel
# These would be needed for a source-based kernel build or manual .deb download/install.
# Since the current implementation uses apt-get to install pre-built Debian kernel packages,
# these are not fully implemented here.
# Example signatures:
    # def _check_cache(self, kernel_version: str) -> Optional[Path]: ...
    # def _download_kernel_source(self, kernel_version: str) -> Path: ...
    # def _verify_kernel_signature(self, tarball_path: Path, version: str) -> None: ...
    # def _extract_kernel_source(self, tarball_path: Path, extract_to: Path) -> Path: ...
    # def _compile_and_install_kernel_from_source(self, source_path_in_chroot: Path, kernel_version: str) -> str: ...
    # def _cache_kernel_artifacts(self, kernel_version: str, artifacts: List[Path]) -> None: ...

# The original snippet had a _generate_dracut_initramfs without kernel_version argument
# and tried to find it. The new one requires kernel_version for clarity.
# The snippet was:
#    def _generate_dracut_initramfs(self):
#        """Generate dracut initramfs for installed kernel"""
#        self.logger.info("Generating dracut initramfs...")
#        chroot_path = self.workspace / "chroot"
#        # Find installed kernel version
#        kernel_version_cmd = "ls -1 /lib/modules"
#        result = subprocess.run(
#            ["chroot", str(chroot
# This logic is now part of _install_kernel_packages to find the *actual* installed version.
