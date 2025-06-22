#!/usr/bin/env bash
# Z-FORGE V3 — Build Environment Checker
# Verifies that essential tools for building the ISO are present on the host.
#───────────────────────────────────────────────────────────────────

set -euo pipefail

echo "════════════════════════════════════════════════════════════════"
echo "          Z-FORGE V3  BUILD ENVIRONMENT CHECKER"
echo "════════════════════════════════════════════════════════════════"
echo

FAILED_CHECKS=0

# Helper function to check for a command
check_command() {
    local cmd_name="$1"
    local purpose="$2"
    local package_hint="${3:-$cmd_name}" # Package name to suggest if different from command

    echo -n "[?] Checking for ${cmd_name}... "
    if command -v "${cmd_name}" &>/dev/null; then
        echo "OK ($(command -v "${cmd_name}"))"
        if [[ "${cmd_name}" == "python3" ]]; then
            local py_version
            py_version=$(python3 --version 2>&1)
            echo "    Version: ${py_version}"
            if ! python3 -c "import sys; assert sys.version_info >= (3, 8), 'Python 3.8+ required'" &>/dev/null; then
                echo "[!] ERROR: Python 3.8 or higher is required. Found ${py_version}."
                echo "    Purpose: Core build scripts and modules."
                FAILED_CHECKS=$((FAILED_CHECKS + 1))
            fi
        elif [[ "${cmd_name}" == "git" ]]; then
            local git_version
            git_version=$(git --version 2>&1)
            echo "    Version: ${git_version}"
        fi
    else
        echo "[!] ERROR: ${cmd_name} not found."
        echo "    Purpose: ${purpose}"
        echo "    Please install it (e.g., 'sudo apt install ${package_hint}' or your system's equivalent)."
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
    echo
}

# Helper function to check for a Python module
check_python_module() {
    local module_name="$1"
    local purpose="$2"
    local package_hint="${3:-python3-$module_name}"

    echo -n "[?] Checking for Python module ${module_name}... "
    if python3 -c "import ${module_name}" &>/dev/null; then
        echo "OK"
    else
        echo "[!] ERROR: Python module ${module_name} not found."
        echo "    Purpose: ${purpose}"
        echo "    Please install it (e.g., 'pip install ${module_name}' or 'sudo apt install ${package_hint}')."
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
    echo
}


# --- Essential Commands ---
check_command "python3" "Running build scripts and modules." "python3"
check_command "git" "Cloning ZFS source code and other repositories." "git"
check_command "chroot" "Creating and managing the build chroot environment." "coreutils" # typically part of coreutils
check_command "debootstrap" "Creating the initial Debian chroot environment." "debootstrap"
check_command "xorriso" "Generating the final ISO image." "xorriso"
check_command "curl" "Fetching files from the internet (used by Python 'requests' or directly)." "curl"
check_command "mkisofs" "Generating the final ISO image (alternative, xorriso is preferred)." "genisoimage" # Often a symlink to xorriso or part of cdrtools/genisoimage

# --- Build System Utilities ---
check_command "make" "Compiling ZFS and potentially other software." "build-essential"
check_command "gcc" "C compiler, required for ZFS and other compiled components." "build-essential"
check_command "gawk" "Text processing, often used in build scripts (ZFS dependency)." "gawk"
check_command "autoconf" "Generating configure scripts (ZFS dependency)." "autoconf"
check_command "automake" "Generating Makefiles (ZFS dependency)." "automake"
check_command "libtool" "Shared library management (ZFS dependency)." "libtool"

# --- Filesystem and Disk Utilities (less critical for host, more for chroot setup by scripts) ---
# These are more likely to be used by debootstrap or within the chroot, but good to be aware of.
# For now, we assume debootstrap and chroot commands handle their internal needs if they are present.
# check_command "truncate" "Creating image files." "coreutils"
# check_command "mkfs.vfat" "Creating FAT32 filesystems for EFI partitions." "dosfstools"
# check_command "mount" "Mounting filesystems." "util-linux"
# check_command "umount" "Unmounting filesystems." "util-linux"

# --- Python Modules ---
# Only check if python3 itself was found and is a suitable version
if command -v "python3" &>/dev/null && python3 -c "import sys; assert sys.version_info >= (3, 8)" &>/dev/null; then
    check_python_module "requests" "Fetching ZFS release information from GitHub API." "python3-requests"
else
    echo "[!] Skipping Python module checks as Python 3.8+ is not available."
    # Increment failed checks because dependent modules won't work
    if ! python3 -c "import sys; assert sys.version_info >= (3, 8)" &>/dev/null; then
      # only increment if it hasn't been already by the python version check
      if [[ $(grep -c "ERROR: Python 3.8 or higher is required" /dev/stdout) -eq 0 ]]; then # A bit hacky to check previous output
          # This path might not be hit if FAILED_CHECKS was already incremented by python version check.
          # A more robust way would be a flag. For now, this is simple.
          : # FAILED_CHECKS already incremented by python version check
      fi
    fi
fi


# --- Final Verdict ---
echo "────────────────────────────────────────────────────────────────"
if [[ ${FAILED_CHECKS} -eq 0 ]]; then
    echo "[✓] All essential build environment checks passed."
    echo "    Your system appears to have the necessary tools to proceed with the ISO build."
    exit 0
else
    echo "[X] ${FAILED_CHECKS} critical error(s) found in build environment!"
    echo "    Please install or correct the missing/failed items listed above before attempting the build."
    exit 1
fi
