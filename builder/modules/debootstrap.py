#!/usr/bin/env python3
# z-forge/builder/modules/debootstrap.py

"""
Debootstrap Module for Z-Forge.

This module is responsible for creating a minimal Debian base system within
a chroot environment. It uses the `debootstrap` utility to download and install
the necessary packages for the specified Debian release. After the base system
is installed, it performs essential configurations such as setting up package
sources, hostname, locale, and timezone. Crucially, it also installs and
configures `dracut`, an initramfs generator, which is essential for booting
the final ISO, especially with ZFS root filesystems.
"""

import subprocess
import os
from pathlib import Path
from typing import Dict, Optional, List, Any
import logging

class Debootstrap:
    """
    Handles the Debian bootstrapping process into a chroot directory.

    This class encapsulates all operations related to creating the initial
    Debian environment, including running `debootstrap`, configuring basic
    system settings (network, package sources, locale), and installing
    core utilities and `dracut`.
    """
    
    def __init__(self, workspace: Path, config: Dict[str, Any]) -> None:
        """
        Initialize the Debootstrap module.

        Args:
            workspace: The path to the Z-Forge build workspace. The chroot
                       environment will be created under `workspace/chroot`.
            config: The global build configuration dictionary, which contains
                    settings like the target Debian release.
        """
        
        self.workspace: Path = workspace
        self.config: Dict[str, Any] = config
        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)
        # Define the path for the chroot environment.
        self.chroot_path: Path = workspace / "chroot"
        
    def execute(self, resume_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the debootstrap process to create and configure the Debian base system.

        This is the main entry point for the module. It orchestrates the
        debootstrap run, system configuration, and dracut installation.
        It supports resuming by checking `resume_data`.

        Args:
            resume_data: Optional dictionary that might contain information
                         about a previous run, allowing the module to skip
                         steps if they were already completed. Currently, it
                         checks for a 'completed' flag.

        Returns:
            A dictionary containing the status of the debootstrap operation.
            On success: {'status': 'success', 'debian_release': str,
                         'chroot_path': str, 'completed': True}
            On failure: {'status': 'error', 'error': str, 'module': str}
        """
        
        self.logger.info("Starting debootstrap process...")
        
        try:
            # Determine the Debian release from the build configuration.
            debian_release: str = self.config.get('builder_config', {}).get('debian_release', 'bookworm')
            
            # Check if debootstrap has already been completed in a previous run.
            if resume_data and resume_data.get('completed', False):
                self.logger.info(f"Debootstrap for {debian_release} already completed, skipping.")
                return {
                    'status': 'success',
                    'debian_release': debian_release,
                    'chroot_path': str(self.chroot_path),
                    'completed': True
                }
            
            # Ensure the chroot parent directory exists.
            self.chroot_path.mkdir(parents=True, exist_ok=True)

            # Step 1: Run the debootstrap command.
            self._run_debootstrap(debian_release)
            
            # Step 2: Configure the basic system settings within the chroot.
            self._configure_system(debian_release)
            
            # Step 3: Install and configure dracut.
            self._install_dracut()
            
            self.logger.info(f"Debootstrap completed successfully for Debian {debian_release}.")
            
            return {
                'status': 'success',
                'debian_release': debian_release,
                'chroot_path': str(self.chroot_path),
                'completed': True # Mark as completed for potential resume.
            }
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"A command failed during debootstrap: {e.cmd}, Return Code: {e.returncode}, Output: {e.output}, Stderr: {e.stderr}")
            return {
                'status': 'error',
                'error': f"Command failed: {' '.join(e.cmd)} - {e.stderr or e.output or str(e)}",
                'module': self.__class__.__name__
            }
        except Exception as e:
            self.logger.error(f"Debootstrap process failed: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _run_debootstrap(self, debian_release: str) -> None:
        """
        Execute the `debootstrap` command to create the minimal Debian system.

        Args:
            debian_release: The target Debian release name (e.g., "bookworm").

        Raises:
            subprocess.CalledProcessError: If the debootstrap command fails.
        """

        self.logger.info(f"Running debootstrap for Debian {debian_release} into {self.chroot_path}...")

        # Define essential packages to include in the base system.
        include_packages: List[str] = [
            "locales",        # For locale generation
            "linux-base",     # Basic Linux system files
            "sudo",           # For privilege escalation
            "bash-completion",# Shell completion
            "apt-transport-https", # For HTTPS APT repositories
            "ca-certificates",# For SSL/TLS certificate validation
            "curl", "wget",   # For downloading files
            "gnupg"           # For package signing and verification
        ]
        
        # Construct the debootstrap command.
        # --arch=amd64: Specifies the architecture.
        # --include: Specifies additional packages to install.
        # debian_release: The target Debian version.
        # self.chroot_path: The target directory for the chroot.
        # http://deb.debian.org/debian: The Debian mirror URL.
        cmd: List[str] = [
            "debootstrap",
            "--arch=amd64",
            f"--include={','.join(include_packages)}",
            debian_release,
            str(self.chroot_path),
            "http://deb.debian.org/debian" # Using a standard Debian mirror
        ]
        
        self.logger.info(f"Executing debootstrap command: {' '.join(cmd)}")
        # Execute the command, raising an exception on failure.
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        self.logger.info("Debootstrap command completed successfully.")
    
    def _configure_system(self, debian_release: str) -> None:
        """
        Perform basic system configuration within the chroot environment.

        This includes setting up APT sources, hostname, hosts file, fstab,
        updating packages, installing essential utilities, and configuring
        locale and timezone.

        Args:
            debian_release: The Debian release name.
        """
        
        self.logger.info("Configuring basic system settings in chroot...")
        
        # Configure /etc/apt/sources.list to include main, updates, security, and backports repositories.
        # non-free-firmware is included for broader hardware compatibility.
        sources_list_content: str = f"""# Main Debian repositories
deb http://deb.debian.org/debian {debian_release} main contrib non-free non-free-firmware
deb http://deb.debian.org/debian {debian_release}-updates main contrib non-free non-free-firmware
deb http://security.debian.org/debian-security {debian_release}-security main contrib non-free non-free-firmware

# Backports repository (useful for newer software on a stable base)
deb http://deb.debian.org/debian {debian_release}-backports main contrib non-free non-free-firmware
"""
        
        sources_path: Path = self.chroot_path / "etc/apt/sources.list"
        with open(sources_path, 'w') as f:
            f.write(sources_list_content)
        self.logger.debug(f"Configured {sources_path}")
        
        # Configure /etc/hostname.
        hostname_path: Path = self.chroot_path / "etc/hostname"
        with open(hostname_path, 'w') as f:
            f.write("zforge\n") # Default hostname for the system being built.
        self.logger.debug(f"Configured {hostname_path}")
        
        # Configure /etc/hosts.
        hosts_content: str = """127.0.0.1   localhost
127.0.1.1   zforge

# The following lines are desirable for IPv6 capable hosts
::1     localhost ip6-localhost ip6-loopback
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
"""
        hosts_path: Path = self.chroot_path / "etc/hosts"
        with open(hosts_path, 'w') as f:
            f.write(hosts_content)
        self.logger.debug(f"Configured {hosts_path}")
        
        # Configure a minimal /etc/fstab.
        # The actual fstab will be generated during installation by Calamares or another installer.
        fstab_content: str = """# /etc/fstab: static file system information.
# Use 'blkid' to print the universally unique identifier for a
# device; this may be used with UUID= as a more robust way to name devices
# that works even if disks are added and removed.

# <file system>  <mount point>  <type>  <options>  <dump>  <pass>
proc             /proc          proc    defaults   0       0
"""
        fstab_path: Path = self.chroot_path / "etc/fstab"
        with open(fstab_path, 'w') as f:
            f.write(fstab_content)
        self.logger.debug(f"Configured {fstab_path}")
        
        # Update package lists and upgrade installed packages within the chroot.
        self.logger.info("Updating package lists and upgrading packages in chroot...")
        self._run_chroot_command(["apt-get", "update"])
        self._run_chroot_command(["apt-get", "upgrade", "-y"]) # -y to auto-confirm.
        
        # Install some essential packages for a functional system and for subsequent build steps.
        essential_packages: List[str] = [
            "build-essential",  # For compiling software (e.g., ZFS DKMS modules)
            "python3",          # Python interpreter
            "python3-distutils",# For Python package building/installation
            "vim", "nano",      # Text editors
            "less", "htop",     # System utilities
            "net-tools",        # Networking utilities (e.g., ifconfig)
            "iproute2",         # Modern networking utilities (e.g., ip addr)
            "iputils-ping"      # For network diagnostics
        ]
        self.logger.info(f"Installing essential packages: {', '.join(essential_packages)}")
        self._run_chroot_command(["apt-get", "install", "-y"] + essential_packages)
        
        # Generate the en_US.UTF-8 locale.
        self.logger.info("Generating en_US.UTF-8 locale...")
        self._run_chroot_command(["locale-gen", "en_US.UTF-8"])
        # TODO: Could make locale configurable via build_spec.yml
        
        # Set the default timezone to UTC.
        self.logger.info("Setting timezone to UTC...")
        self._run_chroot_command(["ln", "-sf", "/usr/share/zoneinfo/UTC", "/etc/localtime"])
        self.logger.info("Basic system configuration in chroot completed.")
    
    def _install_dracut(self) -> None:
        """
        Install and configure dracut within the chroot environment.

        Dracut is used to generate the initramfs. This method ensures
        `initramfs-tools` is removed (if present, to avoid conflicts) and
        then installs `dracut` and its necessary components. A basic
        dracut configuration tailored for Z-Forge (including ZFS and systemd
        support) is also created.
        """
        
        self.logger.info("Installing and configuring dracut in chroot...")
        
        # Remove initramfs-tools to prevent conflicts with dracut.
        # `check=False` as it's not an error if it's not installed.
        self.logger.debug("Attempting to remove initramfs-tools if present...")
        self._run_chroot_command(["apt-get", "remove", "-y", "initramfs-tools"], check=False)
        
        # Install dracut and related packages.
        dracut_packages: List[str] = [
            "dracut",         # Core dracut utility
            "dracut-core",    # Core dracut modules
            "dracut-network", # Modules for network support in initramfs (e.g., for network unlock)
            "dracut-squash"   # Modules for squashfs, if live media uses it directly
        ]
        self.logger.info(f"Installing dracut packages: {', '.join(dracut_packages)}")
        self._run_chroot_command(["apt-get", "install", "-y"] + dracut_packages)
        
        # Create a base dracut configuration file for Z-Forge.
        # This configuration ensures ZFS, systemd, and NVMe support are included.
        # It also sets compression to zstd and enables hostonly mode for smaller initramfs.
        dracut_conf_content: str = """# Z-Forge dracut configuration (etc/dracut.conf.d/zforge.conf)

# Compression method for the initramfs (zstd offers good compression and speed)
compress="zstd"

# Add dracut modules necessary for ZFS root and systemd.
add_dracutmodules+=" zfs systemd "

# Ensure ZFS filesystem type is recognized by dracut.
filesystems+=" zfs "

# Enable hostonly mode: creates a smaller initramfs tailored to the current hardware.
# For a generic ISO, this might be set to "no", or specific drivers added.
# However, 'hostonly="yes"' is often used even for ISOs if the kernel/drivers are generic enough.
hostonly="yes"

# Kernel command line parameters to be embedded in the initramfs.
# 'root=zfs:AUTO' tells the system to find the ZFS root pool automatically.
kernel_cmdline="root=zfs:AUTO"

# Add any additional drivers needed, e.g., for NVMe drives.
add_drivers+=" nvme "
"""
        
        dracut_conf_dir: Path = self.chroot_path / "etc/dracut.conf.d"
        dracut_conf_dir.mkdir(parents=True, exist_ok=True) # Ensure directory exists.
        dracut_conf_file: Path = dracut_conf_dir / "zforge.conf"
        with open(dracut_conf_file, 'w') as f:
            f.write(dracut_conf_content)
        self.logger.info(f"Dracut configuration written to {dracut_conf_file}")
        self.logger.info("Dracut installation and basic configuration completed.")
    
    def _run_chroot_command(self, command: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """
        Helper method to run a command within the chroot environment.

        Args:
            command: A list of strings representing the command and its arguments.
            check: If True, a `subprocess.CalledProcessError` will be raised
                   if the command returns a non-zero exit code. Defaults to True.

        Returns:
            A `subprocess.CompletedProcess` instance.

        Raises:
            subprocess.CalledProcessError: If `check` is True and the command fails.
        """
        
        # Prepend "chroot" and the chroot path to the command.
        full_cmd: List[str] = ["chroot", str(self.chroot_path)] + command
        self.logger.info(f"Executing in chroot: {' '.join(command)}")
        
        # Run the command.
        # `text=True` decodes stdout/stderr as strings.
        # `capture_output=True` is useful if we need to inspect output/errors from this helper.
        result = subprocess.run(full_cmd, check=check, capture_output=True, text=True)
        if result.stdout:
            self.logger.debug(f"Chroot command stdout: {result.stdout.strip()}")
        if result.stderr:
            self.logger.debug(f"Chroot command stderr: {result.stderr.strip()}") # Use debug for stderr as it might be noisy
        return result
