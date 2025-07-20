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
from pathlib import Path
from typing import Dict, Optional, List, Any
import logging
from builder.core.lockfile import BuildLockfile

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
        
    def execute(self, resume_data: Optional[Dict[str, Any]] = None, lockfile: Optional[BuildLockfile] = None) -> Dict[str, Any]:
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
            lockfile: Optional BuildLockfile instance for recording package versions and checksums.

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
            
            # Ensure the chroot parent directory exists with proper permissions.
            self.chroot_path.mkdir(parents=True, exist_ok=True)
            
            # Set permissions on workspace directories, but avoid special filesystems
            self.logger.info("Setting permissions on workspace directories...")
            # Only set permissions on the workspace root and chroot directory itself
            # Avoid recursive chmod that might hit mounted filesystems
            subprocess.run(["sudo", "chmod", "777", str(self.workspace)], check=True)
            subprocess.run(["sudo", "chmod", "777", str(self.chroot_path)], check=True)
            
            # Set permissions on workspace subdirectories individually, avoiding chroot
            for item in self.workspace.iterdir():
                if item.name != "chroot" and item.is_dir():
                    try:
                        subprocess.run(["sudo", "chmod", "-R", "777", str(item)], check=True)
                    except subprocess.CalledProcessError:
                        # If setting permissions fails, just log and continue
                        self.logger.warning(f"Could not set permissions on {item}, continuing...")

            # Step 1: Run the debootstrap command.
            self._run_debootstrap(debian_release)
            
            # Step 2: Mount essential filesystems in chroot.
            self._mount_chroot_filesystems()
            
            # Step 3: Configure the basic system settings within the chroot.
            self._configure_system(debian_release)
            
            # Step 4: Install and configure dracut.
            self._install_dracut()
            
            # Step 5: Unmount chroot filesystems
            self._unmount_chroot_filesystems()
            
            self.logger.info(f"Debootstrap completed successfully for Debian {debian_release}.")
            
            return {
                'status': 'success',
                'debian_release': debian_release,
                'chroot_path': str(self.chroot_path),
                'completed': True # Mark as completed for potential resume.
            }
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"A command failed during debootstrap: {e.cmd}, Return Code: {e.returncode}, Output: {e.output}, Stderr: {e.stderr}")
            # Try to unmount filesystems if they were mounted
            try:
                self._unmount_chroot_filesystems()
            except:
                pass  # Best effort cleanup
            return {
                'status': 'error',
                'error': f"Command failed: {' '.join(e.cmd)} - {e.stderr or e.output or str(e)}",
                'module': self.__class__.__name__
            }
        except Exception as e:
            self.logger.error(f"Debootstrap process failed: {e}", exc_info=True)
            # Try to unmount filesystems if they were mounted
            try:
                self._unmount_chroot_filesystems()
            except:
                pass  # Best effort cleanup
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
        
        # Verify chroot directory exists and has proper permissions
        self.logger.info(f"Verifying chroot directory: {self.chroot_path}")
        if not self.chroot_path.exists():
            self.logger.error(f"Chroot directory does not exist: {self.chroot_path}")
            raise RuntimeError(f"Chroot directory missing: {self.chroot_path}")
        
        # Check permissions
        import os
        stat_info = os.stat(self.chroot_path)
        self.logger.info(f"Chroot directory permissions: {oct(stat_info.st_mode)}, owned by {stat_info.st_uid}:{stat_info.st_gid}")
        
        # Ensure directory is writable
        if not os.access(self.chroot_path, os.W_OK):
            self.logger.error("Chroot directory is not writable!")
            # Try to fix permissions
            self.logger.info("Attempting to fix chroot directory permissions...")
            subprocess.run(["sudo", "chmod", "777", str(self.chroot_path)], check=True)
            subprocess.run(["sudo", "chown", f"{os.getuid()}:{os.getgid()}", str(self.chroot_path)], check=True)

        # Define essential packages to include in the base system.
        include_packages: List[str] = [
            "locales",        # For locale generation
            "linux-base",     # Basic Linux system files
            "sudo",           # For privilege escalation
            "bash-completion",# Shell completion
            "apt-transport-https", # For HTTPS APT repositories
            "ca-certificates",# For SSL/TLS certificate validation
            "curl", "wget",   # For downloading files
            "gnupg",          # For package signing and verification
            "gpgv"            # Required for APT package verification
        ]
        
        # Construct the debootstrap command.
        # --arch=amd64: Specifies the architecture.
        # --include: Specifies additional packages to install.
        # debian_release: The target Debian version.
        # self.chroot_path: The target directory for the chroot.
        # http://deb.debian.org/debian: The Debian mirror URL.
        cmd: List[str] = [
            "sudo",
            "debootstrap",
            "--verbose",      # Add verbose flag for more detailed output
            "--arch=amd64",
            f"--include={','.join(include_packages)}",
            debian_release,
            str(self.chroot_path),
            "http://deb.debian.org/debian" # Using a standard Debian mirror
        ]
        
        self.logger.info(f"Executing debootstrap command: {' '.join(cmd)}")
        # Execute the command with a 30-minute timeout for the initial debootstrap
        # This process downloads many packages and can take time on slow connections
        try:
            # Run without capturing output initially to see real-time progress
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=1800)  # 30 minutes
            
            if result.stdout:
                self.logger.debug(f"Debootstrap stdout:\n{result.stdout}")
            if result.stderr:
                self.logger.warning(f"Debootstrap stderr:\n{result.stderr}")
                
            self.logger.info("Debootstrap command completed successfully.")
        except subprocess.TimeoutExpired as e:
            self.logger.error("Debootstrap command timed out after 30 minutes")
            if e.stdout:
                self.logger.error(f"Partial stdout:\n{e.stdout}")
            if e.stderr:
                self.logger.error(f"Partial stderr:\n{e.stderr}")
            raise
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Debootstrap failed with exit code {e.returncode}")
            if e.stdout:
                self.logger.error(f"Stdout:\n{e.stdout}")
            if e.stderr:
                self.logger.error(f"Stderr:\n{e.stderr}")
            raise
    
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
        # Note: Trixie (testing) doesn't have -updates or -backports
        if debian_release == "trixie":
            sources_list_content: str = f"""# Main Debian repositories
deb http://deb.debian.org/debian {debian_release} main contrib non-free non-free-firmware
deb http://deb.debian.org/debian-security {debian_release}-security main contrib non-free non-free-firmware
"""
        else:
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
192.168.0.1 
9.9.9.9
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
        
        # Configure additional repositories (Dell OpenManage)
        self._configure_dell_repositories()
        
        # Update package lists and upgrade installed packages within the chroot.
        self.logger.info("Updating package lists and upgrading packages in chroot...")
        self._run_chroot_command(["apt-get", "update"])
        self._run_chroot_command(["apt-get", "upgrade", "-y"]) # -y to auto-confirm.
        
        # Install essential packages in groups to avoid timeout issues
        # Group 1: Basic utilities and network tools
        basic_packages = [
            "vim", "nano",      # Text editors
            "less", "htop",     # System utilities
            "net-tools",        # Networking utilities (e.g., ifconfig)
            "iproute2",         # Modern networking utilities (e.g., ip addr)
            "iputils-ping"      # For network diagnostics
        ]
        self.logger.info(f"Installing basic packages: {', '.join(basic_packages)}")
        try:
            self._run_chroot_command(["apt-get", "install", "-y"] + basic_packages)
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to install some basic packages: {e}")
        
        # Group 2: Python packages
        python_packages = [
            "python3",          # Python interpreter
            "python3-distutils" # For Python package building/installation
        ]
        self.logger.info(f"Installing Python packages: {', '.join(python_packages)}")
        try:
            self._run_chroot_command(["apt-get", "install", "-y"] + python_packages)
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to install Python packages: {e}")
        
        # Group 3: Build tools (this is the largest group)
        build_packages = [
            "build-essential"   # For compiling software (e.g., ZFS DKMS modules)
        ]
        self.logger.info(f"Installing build packages (this may take a while): {', '.join(build_packages)}")
        try:
            self._run_chroot_command(["apt-get", "install", "-y"] + build_packages)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to install build-essential: {e}")
            # This is critical for ZFS DKMS, so we should probably fail here
            raise
        
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
    
    def _run_chroot_command(self, command: List[str], check: bool = True, timeout: Optional[int] = None) -> subprocess.CompletedProcess:
        """
        Helper method to run a command within the chroot environment.

        Args:
            command: A list of strings representing the command and its arguments.
            check: If True, a `subprocess.CalledProcessError` will be raised
                   if the command returns a non-zero exit code. Defaults to True.
            timeout: Optional timeout in seconds. Defaults to 300 (5 minutes).

        Returns:
            A `subprocess.CompletedProcess` instance.

        Raises:
            subprocess.CalledProcessError: If `check` is True and the command fails.
            subprocess.TimeoutExpired: If the command times out.
        """
        
        # Set default timeout based on command type
        if timeout is None:
            # Longer timeout for package installation commands
            if len(command) > 0 and command[0] in ["apt-get", "apt"]:
                if len(command) > 1 and command[1] in ["install", "upgrade", "dist-upgrade"]:
                    timeout = 1200  # 20 minutes for package installations
                else:
                    timeout = 600   # 10 minutes for other apt operations
            else:
                timeout = 300  # 5 minutes default for other commands
        
        # Prepend environment variables for apt/dpkg commands to run non-interactively
        if command[0] in ["apt-get", "apt", "dpkg", "dpkg-reconfigure"]:
            # Add environment variables inside the chroot
            command = ["env", "DEBIAN_FRONTEND=noninteractive", "APT_LISTCHANGES_FRONTEND=none"] + command
            self.logger.debug("Setting non-interactive environment for package management command")
            
            # Add -y flag to apt-get commands if not present
            if command[2] in ["apt-get", "apt"] and "-y" not in command:
                # Find the subcommand position (install, remove, etc.)
                subcommand_idx = 3
                if subcommand_idx < len(command) and command[subcommand_idx] in ["install", "remove", "upgrade", "dist-upgrade", "autoremove"]:
                    command.insert(subcommand_idx + 1, "-y")
        
        # Prepend "chroot" and the chroot path to the command.
        full_cmd: List[str] = ["sudo", "chroot", str(self.chroot_path)] + command
        self.logger.info(f"Executing in chroot: {' '.join(command)}")
        
        try:
            # Run the command with timeout.
            # `text=True` decodes stdout/stderr as strings.
            # `capture_output=True` is useful if we need to inspect output/errors from this helper.
            result = subprocess.run(full_cmd, check=check, capture_output=True, text=True, timeout=timeout)
            if result.stdout:
                self.logger.debug(f"Chroot command stdout: {result.stdout.strip()}")
            if result.stderr:
                self.logger.debug(f"Chroot command stderr: {result.stderr.strip()}") # Use debug for stderr as it might be noisy
            return result
        except subprocess.TimeoutExpired as e:
            self.logger.error(f"Command timed out after {timeout} seconds: {' '.join(command)}")
            raise
    
    def _configure_dell_repositories(self) -> None:
        """
        Configure Dell OpenManage repositories for Dell server hardware support.
        """
        self.logger.info("Configuring Dell OpenManage repositories...")
        
        # Create directory for keyrings if it doesn't exist
        keyrings_dir = self.chroot_path / "etc" / "apt" / "keyrings"
        keyrings_dir.mkdir(parents=True, exist_ok=True)
        
        # Download and install Dell GPG key
        try:
            # Download Dell GPG key
            self._run_chroot_command([
                "wget", "-qO", "/etc/apt/keyrings/dell-omsa.gpg",
                "https://linux.dell.com/repo/pgp_pubkeys/0x1285491434D8786F.asc"
            ])
            self.logger.info("Downloaded Dell GPG key")
        except subprocess.CalledProcessError:
            self.logger.warning("Failed to download Dell GPG key, trying alternative method")
            try:
                self._run_chroot_command([
                    "curl", "-fsSL", "-o", "/etc/apt/keyrings/dell-omsa.gpg",
                    "https://linux.dell.com/repo/pgp_pubkeys/0x1285491434D8786F.asc"
                ])
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Failed to download Dell GPG key: {e}")
                return
        
        # Add Dell repository
        dell_sources = """# Dell OpenManage Server Administrator
deb [signed-by=/etc/apt/keyrings/dell-omsa.gpg] https://linux.dell.com/repo/community/openmanage/11100/jammy jammy main
"""
        dell_sources_path = self.chroot_path / "etc" / "apt" / "sources.list.d" / "dell-omsa.list"
        with open(dell_sources_path, "w") as f:
            f.write(dell_sources)
        self.logger.info("Added Dell OpenManage repository")
        
        # Also add MegaRAID repository for LSI/Broadcom RAID controllers
        megaraid_sources = """# MegaRAID Storage Manager
deb [trusted=yes] http://hwraid.le-vert.net/debian trixie main
"""
        megaraid_sources_path = self.chroot_path / "etc" / "apt" / "sources.list.d" / "megaraid.list"
        with open(megaraid_sources_path, "w") as f:
            f.write(megaraid_sources)
        self.logger.info("Added MegaRAID repository")
    
    def _mount_chroot_filesystems(self) -> None:
        """
        Mount essential filesystems in the chroot environment.
        
        This includes /dev, /dev/pts, /proc, /sys which are required
        for many operations within the chroot.
        """
        
        self.logger.info("Mounting essential filesystems in chroot...")
        
        # Create mount points if they don't exist
        mount_points = {
            'dev': 'devtmpfs',
            'dev/pts': 'devpts',
            'proc': 'proc',
            'sys': 'sysfs'
        }
        
        for mount_point, fs_type in mount_points.items():
            mount_path = self.chroot_path / mount_point
            mount_path.mkdir(parents=True, exist_ok=True)
            
            # Check if already mounted
            try:
                result = subprocess.run(['sudo', 'mountpoint', '-q', str(mount_path)], 
                                     capture_output=True)
                if result.returncode == 0:
                    self.logger.debug(f"{mount_path} is already mounted, skipping")
                    continue
            except:
                pass  # mountpoint command might not exist
            
            # Mount the filesystem
            if mount_point == 'dev':
                # Bind mount /dev
                cmd = ['sudo', 'mount', '--bind', '/dev', str(mount_path)]
            elif mount_point == 'dev/pts':
                cmd = ['sudo', 'mount', '-t', fs_type, 'devpts', str(mount_path)]
            else:
                cmd = ['sudo', 'mount', '-t', fs_type, fs_type, str(mount_path)]
            
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                self.logger.debug(f"Mounted {fs_type} on {mount_path}")
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Failed to mount {mount_path}: {e}")
                raise
    
    def _unmount_chroot_filesystems(self) -> None:
        """
        Unmount filesystems that were mounted in the chroot.
        
        This should be called when debootstrap is complete or on error.
        """
        
        self.logger.info("Unmounting chroot filesystems...")
        
        # Unmount in reverse order
        mount_points = ['dev/pts', 'dev', 'proc', 'sys']
        
        for mount_point in mount_points:
            mount_path = self.chroot_path / mount_point
            
            if mount_path.exists():
                try:
                    # Check if mounted
                    result = subprocess.run(['sudo', 'mountpoint', '-q', str(mount_path)], 
                                         capture_output=True)
                    if result.returncode != 0:
                        continue  # Not mounted
                    
                    # Unmount
                    subprocess.run(['sudo', 'umount', str(mount_path)], check=True, 
                                 capture_output=True, text=True)
                    self.logger.debug(f"Unmounted {mount_path}")
                except subprocess.CalledProcessError as e:
                    self.logger.warning(f"Failed to unmount {mount_path}: {e}")
                    # Continue with other unmounts
