#!/bin/bash
# Z-FORGE V3 - ISO build script
# This script automates the process of building a Z-FORGE V3 ISO.
# It sets up the build environment, installs necessary packages,
# configures the system using a series of Python modules, and
# finally generates a bootable ISO image.

# Exit immediately if a command exits with a non-zero status.
set -e

# Display a header for the build process.
echo "════════════════════════════════════════════════════════════════"
echo "                Z-FORGE V3 ISO BUILD PROCESS"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Section: Root Check
# This section ensures that the script is run with root privileges.
# Root privileges are required for tasks like package installation and chroot operations.
if [ "$EUID" -ne 0 ]; then 
    echo "[!] This script must be run as root"
    exit 1
fi

# Section: Configuration
# This section defines key variables used throughout the script.
# WORKSPACE: The directory where build artifacts will be stored.
# ISO_OUTPUT: The path where the final ISO image will be saved.
# LOG_FILE: The file where build logs will be written.
WORKSPACE="/tmp/zforge_workspace"
ISO_OUTPUT="$PWD/zforge-proxmox-v3.iso"
LOG_FILE="$PWD/zforge-build.log"

# Section: Workspace Setup
# This section creates the workspace directory if it doesn't already exist.
echo "[*] Creating workspace at $WORKSPACE..."
mkdir -p "$WORKSPACE"

# Section: Logging Initialization
# This section initializes the log file with a timestamp.
# All major script actions will be logged to this file and also printed to the console.
echo "[*] Build started at $(date)" | tee "$LOG_FILE"

# Save the directory where the script is located.
# This is used to resolve paths to other scripts and configuration files.
SCRIPT_DIR="$PWD"

# Add the script directory to the Python path.
# This allows Python modules in the 'builder' subdirectory to be imported.
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Function: ensure_dracut_installed
# This function ensures that dracut is installed and configured within the chroot environment.
# Dracut is used to create an initramfs, which is essential for booting the system.
# It removes initramfs-tools (an alternative) if present, installs dracut and related packages,
# and sets up basic ZFS configuration for dracut.
# It also generates a hostid if one doesn't exist, which is important for ZFS.
# Arguments:
#   None
# Returns:
#   None
ensure_dracut_installed() {
    echo "[*] Ensuring dracut is properly installed..." | tee -a "$LOG_FILE"
    
    # Execute commands within the chroot environment.
    chroot "$WORKSPACE/chroot" /bin/bash -c "
        # Remove initramfs-tools to avoid conflicts with dracut.
        # The '|| true' ensures the script doesn't fail if initramfs-tools is not installed.
        apt-get remove -y initramfs-tools || true
        
        # Install dracut and its core, network, and squashfs components.
        apt-get install -y dracut dracut-core dracut-network dracut-squash
        
        # Configure dracut to include ZFS support.
        # This creates a configuration file for dracut to load ZFS modules.
        mkdir -p /etc/dracut.conf.d
        echo 'add_dracutmodules+=\" zfs \"' > /etc/dracut.conf.d/zfs.conf
        echo 'filesystems+=\" zfs \"' >> /etc/dracut.conf.d/zfs.conf
        
        # Create a unique hostid if it doesn't exist.
        # ZFS uses the hostid to identify the system.
        if [ ! -f /etc/hostid ]; then
            zgenhostid \$(hexdump -n 4 -e '\"0x%08x\"' /dev/urandom)
        fi
    "
}

# Function: ensure_dracut_module_exists
# This function dynamically creates a Python module named 'dracut_config.py' if it doesn't already exist.
# This module is responsible for more detailed dracut configuration during the Python-based build phase.
# The content of the Python module is written here using a heredoc.
# This approach allows for self-contained script logic without requiring separate Python files for this specific utility.
# The Python module 'DracutConfig' handles:
# - Removing initramfs-tools.
# - Installing dracut packages.
# - Applying detailed dracut configuration based on 'build_spec.yml'.
# - Generating the initramfs image.
# - Retrieving the dracut version.
# Arguments:
#   None
# Returns:
#   None
ensure_dracut_module_exists() {
    # Check if the dracut_config.py module already exists.
    if [ ! -f "$SCRIPT_DIR/builder/modules/dracut_config.py" ]; then
        echo "[*] Creating DracutConfig module..." | tee -a "$LOG_FILE"
        # Create the Python module using a heredoc.
        cat > "$SCRIPT_DIR/builder/modules/dracut_config.py" << 'EOF'
#!/usr/bin/env python3

"""
Dracut Configuration Module
Ensures dracut is properly installed and configured for ZFS
"""

import subprocess
from pathlib import Path
from typing import Dict, Optional
import logging

class DracutConfig:
    """Handles dracut installation and configuration"""
    
    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"
        
    def execute(self, resume_data: Optional[Dict] = None) -> Dict:
        """
        Install and configure dracut
        
        Returns:
            Dict with configuration status
        """
        
        self.logger.info("Starting dracut configuration...")
        
        try:
            # Remove initramfs-tools
            self._remove_initramfs_tools()
            
            # Install dracut packages
            self._install_dracut()
            
            # Configure dracut
            self._configure_dracut()
            
            # Generate initramfs with dracut
            self._generate_initramfs()
            
            return {
                'status': 'success',
                'dracut_version': self._get_dracut_version()
            }
            
        except Exception as e:
            self.logger.error(f"Dracut configuration failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _remove_initramfs_tools(self):
        """Remove initramfs-tools if installed"""
        
        self.logger.info("Removing initramfs-tools...")
        
        subprocess.run([
            "chroot", str(self.chroot_path),
            "apt-get", "remove", "-y", "initramfs-tools"
        ], check=False)  # Don't fail if initramfs-tools isn't installed
    
    def _install_dracut(self):
        """Install dracut packages"""
        
        self.logger.info("Installing dracut packages...")
        
        subprocess.run([
            "chroot", str(self.chroot_path),
            "apt-get", "install", "-y",
            "dracut",
            "dracut-core",
            "dracut-network",
            "dracut-squash"
        ], check=True)
    
    def _configure_dracut(self):
        """Configure dracut"""
        
        self.logger.info("Configuring dracut...")
        
        # Get dracut config from build configuration
        dracut_cfg = self.config.get('dracut_config', {})
        modules = dracut_cfg.get('modules', ['zfs', 'systemd', 'network'])
        compress = dracut_cfg.get('compress', 'zstd')
        hostonly = 'yes' if dracut_cfg.get('hostonly', True) else 'no'
        kernel_cmdline = dracut_cfg.get('kernel_cmdline', 'root=zfs:AUTO')
        extra_drivers = dracut_cfg.get('extra_drivers', ['nvme'])
        
        # Create main dracut configuration
        dracut_conf = f"""# Z-Forge dracut configuration

# Compression method
compress="{compress}"

# Include extra modules
add_dracutmodules+=" {' '.join(modules)} "

# Include necessary filesystem modules
filesystems+=" zfs "

# Enable hostonly mode
hostonly="{hostonly}"

# Add kernel command line parameters
kernel_cmdline="{kernel_cmdline}"

# Include any additional drivers
add_drivers+=" {' '.join(extra_drivers)} "
"""
        
        dracut_conf_path = self.chroot_path / "etc/dracut.conf.d/zforge.conf"
        dracut_conf_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dracut_conf_path, 'w') as f:
            f.write(dracut_conf)
        
        # Create ZFS-specific configuration
        zfs_conf = """# ZFS dracut configuration

# Enable ZFS hostid support
install_optional_items+=" /etc/hostid /etc/zfs/zpool.cache "

# Include ZFS commands
install_items+=" /usr/bin/zfs /usr/bin/zpool "
"""
        
        zfs_conf_path = self.chroot_path / "etc/dracut.conf.d/zfs.conf"
        with open(zfs_conf_path, 'w') as f:
            f.write(zfs_conf)
        
        # Create hostid if it doesn't exist
        hostid_path = self.chroot_path / "etc/hostid"
        if not hostid_path.exists():
            subprocess.run([
                "chroot", str(self.chroot_path),
                "bash", "-c", "zgenhostid $(hexdump -n 4 -e '\"0x%08x\"' /dev/urandom)"
            ], check=True)
    
    def _generate_initramfs(self):
        """Generate initramfs with dracut"""
        
        self.logger.info("Generating initramfs with dracut...")
        
        # Find installed kernel
        kernel_version_cmd = "ls -1 /lib/modules | tail -1"
        result = subprocess.run(
            ["chroot", str(self.chroot_path), "bash", "-c", kernel_version_cmd],
            capture_output=True,
            text=True,
            check=True
        )
        
        kernel_version = result.stdout.strip()
        
        if not kernel_version:
            raise Exception("No kernel modules found")
        
        self.logger.info(f"Regenerating initramfs for kernel {kernel_version}")
        
        # Generate initramfs
        subprocess.run([
            "chroot", str(self.chroot_path),
            "dracut", "-f", f"/boot/initramfs-{kernel_version}.img", kernel_version,
            "--force", "--verbose"
        ], check=True)
        
        # Create symbolic link for compatibility
        subprocess.run([
            "chroot", str(self.chroot_path),
            "ln", "-sf", f"initramfs-{kernel_version}.img", f"/boot/initrd.img-{kernel_version}"
        ], check=True)
    
    def _get_dracut_version(self):
        """Get installed dracut version"""
        
        result = subprocess.run(
            ["chroot", str(self.chroot_path), "dracut", "--version"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        return "unknown"
EOF
        chmod +x "$SCRIPT_DIR/builder/modules/dracut_config.py"
    fi
}

        # Make the generated Python module executable.
        chmod +x "$SCRIPT_DIR/builder/modules/dracut_config.py"
    fi
}

# Function: run_module
# This function executes a specified Python builder module.
# It uses a short Python script to instantiate 'ZForgeBuilder' with the 'build_spec.yml'
# configuration and then calls the 'execute_module' method for the given module name.
# Output from the Python script (both stdout and stderr) is logged.
# If the module execution fails (non-zero exit code from Python or 'status' is not 'success'),
# the script exits.
# Arguments:
#   $1: module_name - The name of the Python module to execute (e.g., "WorkspaceSetup").
# Returns:
#   None (exits on failure).
run_module() {
    local module=$1
    echo "[*] Running module: $module" | tee -a "$LOG_FILE"
    
    # Execute the Python module runner.
    # This inline Python script imports the necessary builder components and runs the specified module.
    python3 -c "
import sys
from builder.core.builder import ZForgeBuilder
# Initialize the builder with the path to the build specification file.
builder = ZForgeBuilder('$SCRIPT_DIR/build_spec.yml')
# Execute the specified module.
result = builder.execute_module('$module')
# Check if the module execution was successful.
if result.get('status') != 'success':
    print(f\"[!] Module $module failed: {result.get('error')}\")
    sys.exit(1)  # Exit Python script with an error code if the module failed.
" 2>&1 | tee -a "$LOG_FILE" # Redirect stdout and stderr to log file and console.
    
    # Check the exit status of the Python command.
    # PIPESTATUS[0] holds the exit status of the first command in a pipe.
    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        echo "[!] Module $module failed!" | tee -a "$LOG_FILE"
        exit 1 # Exit the bash script if the Python command failed.
    fi
}

# Section: Build Pipeline Execution
# This section orchestrates the main build process.
echo "[*] Starting build pipeline..." | tee -a "$LOG_FILE"

# Ensure the dynamically created dracut_config.py Python module exists.
# This is called early to make sure the module is available if needed by other Python modules.
ensure_dracut_module_exists

# Section: Default Build Specification
# This section creates a default 'build_spec.yml' file if one doesn't already exist.
# The 'build_spec.yml' file contains the configuration for the entire build process,
# including Debian release, kernel versions, Proxmox settings, ZFS options,
# bootloader configurations, dracut settings, and the list of modules to run.
# This ensures that the build can run even without a pre-existing configuration file.
if [ ! -f "$SCRIPT_DIR/build_spec.yml" ]; then
    echo "[*] Creating default build configuration..." | tee -a "$LOG_FILE"
    # Create 'build_spec.yml' using a heredoc.
    cat > "$SCRIPT_DIR/build_spec.yml" << 'EOF'
# Z-Forge Build Configuration

# General builder settings
builder_config:
  debian_release: bookworm  # Specifies the Debian release to use for the base system.
  kernel_version: latest    # Specifies the kernel version to install. 'latest' usually means the latest stable.
  output_iso_name: zforge-proxmox-v3.iso # The filename for the generated ISO.
  enable_debug: true        # Enables or disables debug logging or features in Python modules.
  workspace_path: /tmp/zforge_workspace # Overrides the default workspace path if needed.
  cache_packages: true      # Enables or disables caching of downloaded Debian packages.

# Proxmox VE specific configuration
proxmox_config:
  version: latest           # Specifies the Proxmox VE version to install.
  minimal_install: true     # If true, installs a minimal set of Proxmox packages.
  include_packages:         # A list of additional packages to install related to Proxmox.
    - proxmox-ve
    - pve-kernel-6.8
    - zfs-dkms
    - zfsutils-linux
    - pve-zsync

# ZFS (Zettabyte File System) configuration
zfs_config:
  version: latest           # Specifies the ZFS version to use or build.
  build_from_source: true   # If true, ZFS will be compiled from source.
  enable_encryption: true   # Enables ZFS native encryption support.
  default_compression: lz4  # Sets the default compression algorithm for ZFS.

# Bootloader configuration
bootloader_config:
  primary: zfsbootmenu      # Specifies the primary bootloader (e.g., GRUB, systemd-boot, ZFSBootMenu).
  enable_opencore: true     # Option to include OpenCore for specific hardware compatibility (e.g., macOS).
  opencore_drivers:         # List of OpenCore drivers to include if OpenCore is enabled.
    - NvmExpressDxe.efi
    - OpenRuntime.efi

# Dracut (initramfs generator) configuration
dracut_config:
  modules:                  # List of dracut modules to include in the initramfs.
    - zfs
    - systemd
    - network
  compress: zstd            # Compression method for the initramfs image (e.g., gzip, lz4, zstd).
  hostonly: true            # If true, dracut creates a smaller initramfs tailored to the build host.
  kernel_cmdline: "root=zfs:AUTO" # Kernel command line parameters related to root filesystem and ZFS.
  extra_drivers:            # Additional kernel drivers to include in the initramfs.
    - nvme

# List of Python builder modules to execute in order.
# Each module performs a specific part of the build process.
# 'enabled: true' means the module will be run.
modules:
  - name: WorkspaceSetup      # Sets up the initial workspace directories.
    enabled: true
  - name: Debootstrap         # Creates a minimal Debian system in the chroot.
    enabled: true
  - name: KernelAcquisition   # Downloads and installs the specified Linux kernel.
    enabled: true
  - name: ZFSBuild            # Builds and installs ZFS if 'build_from_source' is true.
    enabled: true
  - name: DracutConfig        # Configures and runs dracut to generate the initramfs. This uses the Python module.
    enabled: true
  - name: ProxmoxIntegration  # Installs and configures Proxmox VE.
    enabled: true
  - name: LiveEnvironment     # Configures the live environment settings (e.g., user accounts, services).
    enabled: true
  - name: CalamaresIntegration # Integrates the Calamares installer if used.
    enabled: true
  - name: ISOGeneration       # Creates the final bootable ISO image.
    enabled: true
EOF
fi

# Section: Module Execution Loop
# This section defines the sequence of Python builder modules to be executed.
# It iterates through an array of module names and calls 'run_module' for each.
# It also includes a special hook 'after_debootstrap' that runs a bash function
# immediately after the 'Debootstrap' Python module completes.
modules=(
    "WorkspaceSetup"
    "Debootstrap"
    "KernelAcquisition"
    "ZFSBuild"
    "DracutConfig"
    "ProxmoxIntegration"
    "LiveEnvironment"
    # CalamaresIntegration is handled separately below
    # "CalamaresIntegration"
    "ISOGeneration"
)

# Function: after_debootstrap
# This function is a special hook executed after the 'Debootstrap' Python module.
# Its purpose is to perform immediate post-debootstrap tasks within the bash script,
# specifically ensuring dracut is installed in the chroot using the bash function
# 'ensure_dracut_installed'. This might be for initial setup before the more
# comprehensive 'DracutConfig' Python module runs.
# Arguments:
#   None
# Returns:
#   None
after_debootstrap() {
    echo "[*] Post-Debootstrap: Ensuring dracut is installed..." | tee -a "$LOG_FILE"
    # Call the bash function to install/configure dracut at a basic level.
    ensure_dracut_installed
}

# Loop through the defined Python modules and execute them.
for module in "${modules[@]}"; do
    if [ "$module" == "ISOGeneration" ]; then
        # Calamares setup and integration must happen before ISOGeneration
        echo "[*] Setting up Calamares modules..." | tee -a "$LOG_FILE"
        if ! ./setup-calamares-modules.sh; then
            echo "[!] Failed to set up Calamares modules. Aborting." | tee -a "$LOG_FILE"
            exit 1
        fi
        run_module "CalamaresIntegration"
    fi

    run_module "$module" # Execute the current Python module.
    
    # Check for special hooks that need to run after certain Python modules.
    # This allows for bash-level operations to be interleaved with Python module execution.
    if [ "$module" == "Debootstrap" ]; then
        # If the 'Debootstrap' module has just finished, call the 'after_debootstrap' bash function.
        after_debootstrap
    fi
done

# Section: Final Steps and Verification
# This section performs final checks, generates checksums for the ISO,
# and provides instructions for testing the ISO.
if [ -f "$ISO_OUTPUT" ]; then
    echo "[*] Build completed successfully!" | tee -a "$LOG_FILE"
    echo "[*] ISO location: $ISO_OUTPUT" | tee -a "$LOG_FILE"
    echo "[*] ISO size: $(du -h "$ISO_OUTPUT" | cut -f1)" | tee -a "$LOG_FILE"

    # Generate SHA256 and MD5 checksums for the created ISO file.
    # This allows users to verify the integrity of the downloaded/copied ISO.
    echo "[*] Generating checksums..." | tee -a "$LOG_FILE"
    sha256sum "$ISO_OUTPUT" > "$ISO_OUTPUT.sha256"
    md5sum "$ISO_OUTPUT" > "$ISO_OUTPUT.md5"
else
    # If the ISO file was not created, report a build failure and exit.
    echo "[!] Build failed: ISO file not created" | tee -a "$LOG_FILE"
    exit 1
fi

# Display completion message and next steps.
echo "" | tee -a "$LOG_FILE"
echo "════════════════════════════════════════════════════════════════"
echo "                    BUILD COMPLETE"
echo "════════════════════════════════════════════════════════════════"
echo "" | tee -a "$LOG_FILE"
echo "Next steps:" | tee -a "$LOG_FILE"
echo "1. Test ISO in virtual machine:" | tee -a "$LOG_FILE"
echo "   qemu-system-x86_64 -m 4G -cdrom $ISO_OUTPUT -enable-kvm" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "2. Write to USB drive:" | tee -a "$LOG_FILE"
echo "   dd if=$ISO_OUTPUT of=/dev/sdX bs=4M status=progress" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
