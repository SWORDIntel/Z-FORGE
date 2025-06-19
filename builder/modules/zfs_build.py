#!/usr/bin/env python3
# z-forge/builder/modules/zfs_build.py

"""
ZFS Build Module for Z-Forge.

This module is responsible for integrating OpenZFS into the chroot environment.
It handles the installation of ZFS build dependencies, cloning the OpenZFS
source code (or fetching a specific release), compiling ZFS, and installing
it along with DKMS support. This ensures that ZFS kernel modules can be
automatically rebuilt for new kernels. It also configures dracut specifically
for ZFS, enabling ZFS support in the initramfs, and sets up essential ZFS
services required for a ZFS-on-root system.
"""

import subprocess
import tempfile
import shutil
import requests
from pathlib import Path
from typing import Dict, Optional, List, Any
import logging
import os

class ZFSBuild:
    """
    Handles the compilation and installation of OpenZFS from source.

    This class manages fetching ZFS sources, installing build dependencies,
    compiling ZFS with DKMS support, and configuring the system (dracut, services)
    to use the newly built ZFS.
    """
    
    def __init__(self, workspace: Path, config: Dict[str, Any]) -> None:
        """
        Initialize the ZFSBuild module.

        Args:
            workspace: Path to the Z-Forge build workspace. Operations are
                       typically performed within `workspace/chroot`.
            config: The global build configuration dictionary, containing ZFS-specific
                    settings like the desired version or build options.
        """
        self.workspace: Path = workspace
        self.config: Dict[str, Any] = config
        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)
        # Define the official OpenZFS GitHub repository URL.
        self.zfs_repo_url: str = "https://github.com/openzfs/zfs.git"
        self.chroot_path: Path = self.workspace / "chroot"
        
    def execute(self, resume_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the ZFS build and installation process.

        This is the main entry point for the module. It orchestrates the
        installation of dependencies, fetching ZFS sources, building ZFS,
        configuring DKMS, setting up dracut for ZFS, and enabling ZFS services.

        Args:
            resume_data: Optional dictionary for resuming partial execution.
                         (Currently not heavily utilized in this module beyond potential
                          checks if a ZFS version is already 'installed' marker).

        Returns:
            A dictionary containing the status of the ZFS build operation.
            On success: {'status': 'success', 'zfs_version': str,
                         'features': {'encryption': bool, 'compression': str, 'dkms': bool}}
            On failure: {'status': 'error', 'error': str, 'module': str}
        """
        
        self.logger.info("Starting ZFS build and installation process...")
        
        try:
            # Determine the ZFS version to build.
            zfs_config: Dict[str, Any] = self.config.get('zfs_config', {})
            target_zfs_version: str
            if zfs_config.get('version') == 'latest':
                target_zfs_version = self._get_latest_zfs_release_tag()
                self.logger.info(f"Latest ZFS release tag: {target_zfs_version}")
            else:
                # Default to a known stable version if not specified.
                target_zfs_version = zfs_config.get('version', 'zfs-2.2.4') # Ensure tag format
                if not target_zfs_version.startswith("zfs-"): # Basic validation for tag format
                    target_zfs_version = f"zfs-{target_zfs_version}"

            self.logger.info(f"Target ZFS version for build: {target_zfs_version}")

            # Step 1: Install ZFS build dependencies within the chroot.
            self._install_build_dependencies()
            
            # Step 2: Clone ZFS repository and checkout the target version.
            zfs_source_dir: Path = self._clone_zfs_repository(target_zfs_version)
            
            # Step 3: Build and install ZFS from source.
            self._build_and_install_zfs(zfs_source_dir)
            
            # Step 4: Configure DKMS for ZFS. (Often handled by ZFS install script, but verify)
            self._configure_dkms_for_zfs() # This might be more of a verification step.
            
            # Step 5: Set up dracut for ZFS support in initramfs.
            self._setup_dracut_for_zfs()
            
            # Step 6: Set up ZFS services (e.g., zfs-import-cache, zfs-mount).
            self._setup_zfs_services()
            
            self.logger.info(f"ZFS version {target_zfs_version} built and installed successfully.")
            
            # Return status and information about the built ZFS.
            return {
                'status': 'success',
                'zfs_version': target_zfs_version,
                'features': { # These are typically default/enabled with OpenZFS
                    'encryption': zfs_config.get('enable_encryption', True), # Reflects config intent
                    'compression': zfs_config.get('default_compression', 'lz4'), # Reflects config intent
                    'dkms': True # Assumed if build is successful
                }
            }
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"A command failed during ZFS build: {e.cmd}, Return Code: {e.returncode}, Output: {e.output}, Stderr: {e.stderr}")
            return {
                'status': 'error',
                'error': f"Command failed: {' '.join(e.cmd)} - {e.stderr or e.output or str(e)}",
                'module': self.__class__.__name__
            }
        except Exception as e:
            self.logger.error(f"ZFS build process failed: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }

    def _run_chroot_command(self, command: List[str], cwd: Optional[Path] = None, check: bool = True, env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
        """Helper to run commands inside the chroot."""
        base_cmd = ["chroot", str(self.chroot_path)]
        if env: # if environment variables are provided, use env in chroot
            env_setup = [f"{k}={v}" for k,v in env.items()]
            base_cmd.extend(["env", "-i"] + env_setup) # -i for clean environment

        full_cmd = base_cmd + command

        # Determine current working directory for the chroot command
        chroot_cwd_str = str(cwd) if cwd else None
        if chroot_cwd_str and str(self.chroot_path) in chroot_cwd_str: # Ensure cwd is inside chroot
             actual_cwd_for_chroot = Path(chroot_cwd_str).relative_to(self.chroot_path)
             if not str(actual_cwd_for_chroot).startswith("/"):
                 actual_cwd_for_chroot = Path("/") / actual_cwd_for_chroot
        else: # if cwd is None or not within chroot_path, default to / inside chroot
            actual_cwd_for_chroot = Path("/")


        self.logger.info(f"Executing in chroot (cwd: {actual_cwd_for_chroot}): {' '.join(command)}")

        # We need to run `chroot` itself with `cwd=None` or `/`,
        # then the command *inside* chroot effectively runs from `actual_cwd_for_chroot`.
        # This is tricky with subprocess.run directly. A common way is to do `chroot /path/to/chroot /bin/bash -c 'cd /new/cwd && command'`
        # For simplicity, if cwd is used, we'll use bash -c to handle it.
        if cwd: # If a specific cwd *inside* the chroot is needed
            bash_command = f"cd \"{actual_cwd_for_chroot}\" && {' '.join(command)}"
            # Modify full_cmd to use bash -c
            full_cmd = base_cmd + ["/bin/bash", "-c", bash_command]
            self.logger.debug(f"Effective chroot bash command: {bash_command}")

        result = subprocess.run(full_cmd, check=check, capture_output=True, text=True) # cwd is not set here for chroot command itself
        if result.stdout:
            self.logger.debug(f"Chroot command stdout: {result.stdout.strip()}")
        if result.stderr:
            self.logger.debug(f"Chroot command stderr: {result.stderr.strip()}")
        return result

    def _get_latest_zfs_release_tag(self) -> str:
        """Fetches the latest ZFS release tag from GitHub API."""
        self.logger.info("Fetching latest ZFS release tag from GitHub API...")
        try:
            # The OpenZFS project uses tags like `zfs-2.2.4`
            response = requests.get("https://api.github.com/repos/openzfs/zfs/releases/latest")
            response.raise_for_status() # Raise an exception for HTTP errors
            latest_release_tag = response.json()['tag_name']
            if not latest_release_tag.startswith("zfs-"): # Defensive check
                # Fallback or error if tag format is unexpected
                self.logger.warning(f"Latest release tag '{latest_release_tag}' doesn't match expected 'zfs-X.Y.Z' format. Trying to find a recent tag.")
                response_tags = requests.get("https://api.github.com/repos/openzfs/zfs/tags")
                response_tags.raise_for_status()
                tags = response_tags.json()
                for tag_info in tags:
                    if tag_info['name'].startswith("zfs-2."): # Prioritize zfs-2.x tags
                        latest_release_tag = tag_info['name']
                        self.logger.info(f"Found suitable tag via tags list: {latest_release_tag}")
                        break
                else: # If no suitable tag found
                    raise ValueError("Could not determine a suitable ZFS release tag.")

            return latest_release_tag
        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch latest ZFS release from GitHub: {e}")
            # Fallback to a known recent version if API fails
            fallback_version = "zfs-2.2.4"
            self.logger.warning(f"Falling back to ZFS version: {fallback_version}")
            return fallback_version
        except KeyError:
            self.logger.error("Failed to parse 'tag_name' from GitHub API response.")
            fallback_version = "zfs-2.2.4"
            self.logger.warning(f"Falling back to ZFS version: {fallback_version}")
            return fallback_version


    def _install_build_dependencies(self) -> None:
        """Install ZFS build dependencies into the chroot environment."""
        self.logger.info("Installing ZFS build dependencies in chroot...")
        # Common dependencies for building ZFS. This list might need updates based on ZFS version.
        # Includes DKMS for kernel module management.
        deps = [
            "build-essential", "autoconf", "automake", "libtool", "gawk",
            "alien", "fakeroot", "uuid-dev", "libattr1-dev", "libblkid-dev",
            "libelf-dev", "libudev-dev", "libssl-dev", "zlib1g-dev", "libaio-dev",
            "libattr1-dev", "python3", "python3-dev", "python3-setuptools", "python3-cffi",
            "libffi-dev", "linux-headers-amd64", # Generic headers, specific headers installed by KernelAcquisition
            "dkms"
        ]
        # The command to install dependencies. -y confirms automatically.
        cmd = ["apt-get", "update"]
        self._run_chroot_command(cmd)
        cmd = ["apt-get", "install", "-y"] + deps
        self._run_chroot_command(cmd)
        self.logger.info("ZFS build dependencies installed.")

    def _clone_zfs_repository(self, zfs_version_tag: str) -> Path:
        """
        Clone the ZFS repository into a temporary directory and checkout the specified version tag.
        The temporary directory will be inside the chroot to allow chrooted build steps.
        """
        # Using a directory within the chroot for the source, e.g., /usr/src/zfs
        # This simplifies build commands that might need to run chrooted.
        zfs_chroot_src_dir = Path("/usr/src/zfs_build_source")
        actual_zfs_src_dir = self.chroot_path / zfs_chroot_src_dir.relative_to("/") # Path on host system
        
        self.logger.info(f"Cloning ZFS repository version {zfs_version_tag} into {actual_zfs_src_dir}...")

        if actual_zfs_src_dir.exists():
            self.logger.info(f"ZFS source directory {actual_zfs_src_dir} already exists. Removing it.")
            shutil.rmtree(actual_zfs_src_dir)

        actual_zfs_src_dir.mkdir(parents=True, exist_ok=True)

        # Clone the repository. --depth 1 for shallow clone if only building specific tag.
        # However, to checkout a tag, we might need more history.
        # For specific tag, it's better to clone then checkout.
        # We run git commands on the host, then ZFS build commands in chroot.
        # Alternative: run git clone inside chroot.

        # Let's try running git clone directly into the chroot target path from host.
        # This avoids needing git inside the chroot initially.
        subprocess.run(["git", "clone", self.zfs_repo_url, str(actual_zfs_src_dir)], check=True)
        subprocess.run(["git", "-C", str(actual_zfs_src_dir), "checkout", zfs_version_tag], check=True)

        self.logger.info(f"ZFS repository cloned and checked out to {zfs_version_tag} in {actual_zfs_src_dir}.")
        return zfs_chroot_src_dir # Return path as seen from *inside* the chroot

    def _build_and_install_zfs(self, zfs_source_dir_in_chroot: Path) -> None:
        """Build and install ZFS from the cloned source within the chroot."""
        self.logger.info(f"Building and installing ZFS from {zfs_source_dir_in_chroot} in chroot...")

        # ZFS build process typically involves:
        # 1. ./autogen.sh (if building from git master, not needed for release tarballs/tags usually)
        # 2. ./configure --prefix=/usr --sysconfdir=/etc --sbindir=/usr/sbin --libdir=/usr/lib
        # 3. make -j$(nproc)
        # 4. make install
        # We will run these commands inside the chroot.

        # Run autogen.sh - this is usually needed when building from a git checkout
        self._run_chroot_command(["./autogen.sh"], cwd=zfs_source_dir_in_chroot)

        # Configure build options. Enable DKMS, systemd integration.
        # --with-linux and --with-linux-obj should point to kernel source/headers if not standard.
        # Assuming kernel headers are in their standard location accessible within chroot.
        configure_opts = [
            "--prefix=/usr",
            "--sysconfdir=/etc",
            "--sbindir=/usr/sbin",
            "--libdir=/usr/lib/x86_64-linux-gnu", # Debian specific lib dir
            "--libexecdir=/usr/lib/x86_64-linux-gnu/zfs",
            "--with-config=kernel", # Build kernel modules
            "--enable-dkms",        # Enable DKMS support
            "--with-dkmsdir=/usr/src/zfs_built", # specify a different name to avoid conflict with packaged zfs-dkms
            "--with-systemd",       # Enable systemd integration
            "--with-dracut",        # Enable dracut integration
            # Add other options as needed from self.config
        ]
        self._run_chroot_command(["./configure"] + configure_opts, cwd=zfs_source_dir_in_chroot)

        # Get number of processors for 'make -j'
        nproc = os.cpu_count()
        self._run_chroot_command(["make", f"-j{nproc}"], cwd=zfs_source_dir_in_chroot)

        # Install ZFS
        self._run_chroot_command(["make", "install"], cwd=zfs_source_dir_in_chroot)

        # After 'make install', ZFS DKMS modules should be registered with DKMS.
        self.logger.info("ZFS built and installed successfully.")

    def _configure_dkms_for_zfs(self) -> None:
        """Ensure ZFS modules are correctly registered and built via DKMS."""
        # ZFS 'make install' with '--enable-dkms' should handle DKMS registration.
        # This method can be used to verify or manually trigger DKMS build if needed.
        self.logger.info("Verifying/Configuring DKMS for ZFS...")

        # Example: List dkms status
        dkms_status_result = self._run_chroot_command(["dkms", "status"], check=False)
        self.logger.info(f"DKMS status:\n{dkms_status_result.stdout}")

        # If needed, one could manually add and build:
        # self._run_chroot_command(["dkms", "add", "-m", "zfs", "-v", zfs_kernel_module_version])
        # self._run_chroot_command(["dkms", "build", "-m", "zfs", "-v", zfs_kernel_module_version])
        # self._run_chroot_command(["dkms", "install", "-m", "zfs", "-v", zfs_kernel_module_version, "--force"])
        # However, this is typically handled by ZFS's own install scripts when DKMS is enabled.
        # For now, we assume `make install` did its job.
        self.logger.info("DKMS for ZFS assumed configured by ZFS install scripts.")


    def _setup_dracut_for_zfs(self) -> None:
        """Configure dracut for ZFS support within the chroot."""
        self.logger.info("Setting up dracut ZFS module configuration in chroot...")
        
        # Ensure dracut itself is installed (might be a dependency of ZFS build process or debootstrap)
        # Running this defensively.
        self._run_chroot_command(["apt-get", "install", "-y", "dracut", "dracut-network"], check=False)
        
        # Create ZFS-specific dracut configuration.
        # This tells dracut to include ZFS modules and utilities in the initramfs.
        dracut_zfs_conf_content: str = """# ZFS dracut configuration (etc/dracut.conf.d/zfs.conf)

# Ensure ZFS dracut modules are added.
add_dracutmodules+=" zfs "

# Ensure ZFS filesystem type is recognized by dracut.
filesystems+=" zfs "

# Install items needed for ZFS import during early boot.
# /etc/hostid is crucial for ZFS pool import.
# /etc/zfs/zpool.cache allows importing pools without scanning all devices.
install_optional_items+=" /etc/hostid /etc/zfs/zpool.cache "

# Include essential ZFS command-line utilities in the initramfs.
install_items+=" /usr/sbin/zfs /usr/sbin/zpool "
"""
        # Note: /usr/bin/zfs might be /usr/sbin/zfs depending on distro/build. Check ZFS install paths.
        # The ./configure for ZFS used --sbindir=/usr/sbin.

        dracut_conf_dir: Path = self.chroot_path / "etc/dracut.conf.d"
        dracut_conf_dir.mkdir(parents=True, exist_ok=True)
        dracut_zfs_conf_file: Path = dracut_conf_dir / "zfs.conf" # Specific to ZFS
        with open(dracut_zfs_conf_file, 'w') as f:
            f.write(dracut_zfs_conf_content)
        self.logger.info(f"Dracut ZFS configuration written to {dracut_zfs_conf_file}")

        # Generate /etc/hostid if it doesn't exist. ZFS relies on this.
        # The command checks for existence before generating.
        hostid_check_command = "[ -f /etc/hostid ] || zgenhostid $(hexdump -n 4 -e '\"0x%08x\"' /dev/urandom)"
        self._run_chroot_command(["bash", "-c", hostid_check_command])
        self.logger.info("Ensured /etc/hostid exists in chroot.")

        # It's good practice to regenerate all initramfs images after such changes,
        # or at least the one for the currently targeted kernel.
        # This is often done after kernel installation or by a later "finalize" step.
        # For now, we assume KernelAcquisition or a final build step handles initramfs regeneration.
        # However, if a kernel is already present, we can try to regenerate.
        # Example: self._run_chroot_command(["dracut", "-f", "--regenerate-all"], check=False)
        # This is often better done after a kernel is confirmed to be installed.
        self.logger.info("Dracut configuration for ZFS completed. Initramfs should be regenerated after kernel installation.")

    def _setup_zfs_services(self) -> None:
        """Enable and configure necessary ZFS systemd services within the chroot."""
        self.logger.info("Setting up ZFS systemd services in chroot...")
        
        # ZFS installation typically includes systemd service files.
        # These services manage tasks like mounting ZFS datasets, importing pools, etc.
        # Common services: zfs-import-cache.service, zfs-mount.service, zfs-share.service, zfs-zed.service.

        services_to_enable: List[str] = [
            "zfs-import-cache.service", # Imports pools listed in zpool.cache early in boot
            "zfs-mount.service",        # Mounts ZFS datasets
            "zfs-zed.service",          # ZFS Event Daemon (monitors pool health, handles events)
            "zfs-share.service",       # If NFS/SMB sharing of ZFS datasets is needed
            "zfs-import.target",       # Target that pulls in zfs-import-cache
        ]

        # Enable these services using systemctl (which works on symlinks even in chroot)
        for service in services_to_enable:
            # systemctl enable creates symlinks; it doesn't start the service.
            self._run_chroot_command(["systemctl", "enable", service], check=False) # check=False as some might not be present depending on build options
            self.logger.info(f"Enabled ZFS service (or attempted to): {service}")

        # Create /etc/zfs/zpool.cache if it doesn't exist (it's optional for dracut but good for services)
        # This file is populated when pools are imported.
        zpool_cache_path: Path = self.chroot_path / "etc/zfs/zpool.cache"
        if not zpool_cache_path.exists():
            zpool_cache_path.parent.mkdir(parents=True, exist_ok=True)
            zpool_cache_path.touch() # Create an empty file.
            self.logger.info(f"Created empty zpool.cache at {zpool_cache_path}")

        self.logger.info("ZFS systemd services setup completed.")

# Example of how this might be used (outside the class, for testing or integration)
if __name__ == '__main__':
    # This is placeholder test code
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    mock_workspace = Path("/tmp/zforge_test_workspace_zfs")
    if mock_workspace.exists():
        shutil.rmtree(mock_workspace) # Clean up previous test
    mock_workspace.mkdir(parents=True, exist_ok=True)

    # Create a dummy chroot for basic testing
    mock_chroot = mock_workspace / "chroot"
    mock_chroot.mkdir(parents=True, exist_ok=True)
    (mock_chroot / "etc").mkdir(exist_ok=True)
    (mock_chroot / "usr" / "src").mkdir(parents=True, exist_ok=True)

    # Dummy files/dirs that ZFS build might expect or create
    (mock_chroot / "usr" / "lib" / "x86_64-linux-gnu").mkdir(parents=True, exist_ok=True)
    (mock_chroot / "usr" / "sbin").mkdir(parents=True, exist_ok=True)


    print(f"Created mock workspace and chroot at {mock_workspace}")

    mock_config = {
        'builder_config': {'workspace_path': str(mock_workspace)},
        'zfs_config': {'version': 'latest', 'enable_encryption': True, 'default_compression': 'zstd'},
        'kernel_config': {'version': '6.1.0-13-amd64'} # Example kernel version
    }

    # To run this test, you would need a functional chroot with build tools.
    # The following is more of a conceptual test run.
    # zfs_builder = ZFSBuild(workspace=mock_workspace, config=mock_config)
    # result = zfs_builder.execute()
    # print(f"ZFS Build execution result: {result}")
    print("Conceptual test structure. Full execution requires a prepared chroot and build environment."))
