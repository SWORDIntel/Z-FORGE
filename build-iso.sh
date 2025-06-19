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
  encryption:
    default_enabled: true
    default_algorithm: 'aes-256-gcm'
    pbkdf_iterations: 350000
    prompt_during_install: true

# Bootloader configuration
bootloader_config:
  primary: zfsbootmenu      # Specifies the primary bootloader (e.g., GRUB, systemd-boot, ZFSBootMenu).
  enable_opencore: true     # Option to include OpenCore for specific hardware compatibility (e.g., macOS).
  opencore_drivers:         # List of OpenCore drivers to include if OpenCore is enabled.
    - NvmExpressDxe.efi
    - OpenRuntime.efi
  encryption_support: true # Enable bootloader encryption support

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
  - name: DracutConfig # This will be addressed further in plan step 3
    enabled: true
  - name: ProxmoxIntegration  # Installs and configures Proxmox VE.
    enabled: true
  - name: BootloaderSetup # Added
    enabled: true
  - name: LiveEnvironment # This was in build-iso.sh's list but not in z-forge.py's default. For now, keep it.
    enabled: true
  - name: CalamaresIntegration # Integrates the Calamares installer if used.
    enabled: true
  - name: SecurityHardening # Added
    enabled: true
  - name: EncryptionSupport # Added
    enabled: true
  - name: ISOGeneration       # Creates the final bootable ISO image.
    enabled: true

# Calamares configuration
calamares_config:
  modules:
    - welcome
    - locale
    - keyboard
    - partition
    - zfsrootselect  # Our custom ZFS module with encryption
    - users
    - summary
    - install
    - finished
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
