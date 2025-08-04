#!/bin/bash
# Diagnose kernel version issues in Z-FORGE chroot

set -e

CHROOT_PATH="/tmp/zforge_workspace/chroot"

echo "=== Z-FORGE Kernel Version Diagnosis ==="
echo "Date: $(date)"
echo "Chroot: $CHROOT_PATH"
echo ""

# Check if chroot exists
if [ ! -d "$CHROOT_PATH" ]; then
    echo "ERROR: Chroot directory not found at $CHROOT_PATH"
    exit 1
fi

# Function to run command in chroot and capture output
chroot_run() {
    sudo chroot "$CHROOT_PATH" "$@" 2>&1 || echo "Command failed: $*"
}

# 1. Check Debian version
echo "1. Debian Version Information:"
echo "==============================="
if [ -f "$CHROOT_PATH/etc/debian_version" ]; then
    echo "debian_version: $(cat "$CHROOT_PATH/etc/debian_version")"
fi

if [ -f "$CHROOT_PATH/etc/os-release" ]; then
    echo ""
    echo "os-release:"
    grep -E "PRETTY_NAME|VERSION|VERSION_ID|VERSION_CODENAME" "$CHROOT_PATH/etc/os-release" || true
fi

# 2. Check APT sources
echo ""
echo "2. APT Sources Configuration:"
echo "==============================="
echo "Contents of sources.list:"
cat "$CHROOT_PATH/etc/apt/sources.list" 2>/dev/null || echo "sources.list not found"

if [ -d "$CHROOT_PATH/etc/apt/sources.list.d" ]; then
    echo ""
    echo "Additional sources in sources.list.d:"
    ls -la "$CHROOT_PATH/etc/apt/sources.list.d/" 2>/dev/null || echo "No additional sources"
fi

# 3. Check APT policy
echo ""
echo "3. APT Policy (repository priorities):"
echo "==============================="
chroot_run apt policy | head -20

# 4. Check available kernels
echo ""
echo "4. Available Kernel Packages:"
echo "==============================="
echo "Latest 10 kernel images available:"
chroot_run apt-cache search "^linux-image-[0-9]" | grep -v "dbg\|cloud\|rt" | sort -V | tail -10

echo ""
echo "Kernel metapackages:"
chroot_run apt-cache search "^linux-image-" | grep -E "^linux-image-(amd64|generic)" | sort

# 5. Check what would be installed
echo ""
echo "5. What Would Be Installed:"
echo "==============================="
echo "Simulating linux-image-amd64 installation:"
chroot_run apt-get install -s linux-image-amd64 2>&1 | grep -E "^(Inst|Conf)" | head -10

# 6. Check for version pinning
echo ""
echo "6. APT Preferences/Pinning:"
echo "==============================="
if [ -f "$CHROOT_PATH/etc/apt/preferences" ]; then
    cat "$CHROOT_PATH/etc/apt/preferences"
else
    echo "No /etc/apt/preferences file"
fi

if [ -d "$CHROOT_PATH/etc/apt/preferences.d" ]; then
    echo ""
    echo "Files in preferences.d:"
    ls -la "$CHROOT_PATH/etc/apt/preferences.d/" 2>/dev/null || echo "No preferences.d files"
fi

# 7. Check currently installed kernels
echo ""
echo "7. Currently Installed Kernels:"
echo "==============================="
chroot_run dpkg -l | grep -E "^ii.*linux-image" || echo "No kernels installed"

# 8. Check for held packages
echo ""
echo "8. Held Packages:"
echo "==============================="
chroot_run apt-mark showhold | grep -E "linux-" || echo "No linux packages on hold"

# 9. Check architecture
echo ""
echo "9. System Architecture:"
echo "==============================="
echo "dpkg architecture: $(chroot_run dpkg --print-architecture)"
echo "Foreign architectures: $(chroot_run dpkg --print-foreign-architectures)"

# 10. Specific kernel version check
echo ""
echo "10. Specific Version Information:"
echo "==============================="
echo "Checking for kernel 6.1.0-28:"
chroot_run apt-cache show linux-image-6.1.0-28-amd64 2>&1 | grep -E "^(Package|Version|Source|Filename)" || echo "Package not found"

echo ""
echo "=== Diagnosis Complete ==="
echo ""
echo "Key findings:"
echo "1. Check if VERSION_CODENAME matches your expected Debian release"
echo "2. Verify sources.list points to correct Debian release"
echo "3. Look for any version pinning that might force specific kernels"
echo "4. Check if the kernel version matches the Debian release"
echo ""
echo "Debian releases and their kernel versions:"
echo "- Debian 11 (Bullseye): 5.10.x"
echo "- Debian 12 (Bookworm): 6.1.x"
echo "- Debian 13 (Trixie/Testing): 6.6.x or newer"
echo ""
echo "If seeing 6.1.x kernels in Trixie, the sources might be mixed!"