#!/bin/bash
# Check kernel versions across Debian releases

echo "=== Debian Release Kernel Versions ==="
echo "This helps identify which Debian release you're actually using"
echo ""

# Function to check kernel version for a release
check_release_kernel() {
    local release=$1
    local desc=$2
    
    echo "Checking $desc ($release):"
    echo -n "  Latest kernel: "
    
    # Use a temporary directory for apt lists
    TEMP_APT=$(mktemp -d)
    
    # Fetch package info for the release
    curl -s "http://deb.debian.org/debian/dists/$release/main/binary-amd64/Packages.gz" | \
        gzip -d | \
        grep -A 10 "^Package: linux-image-[0-9]" | \
        grep "^Package: " | \
        sed 's/Package: //' | \
        grep -v "dbg\|cloud\|rt\|unsigned" | \
        sort -V | \
        tail -1
    
    rm -rf "$TEMP_APT"
    echo ""
}

# Check each release
echo "Current Debian releases and their kernel versions:"
echo "================================================="
check_release_kernel "oldstable" "Debian 11 Bullseye"
check_release_kernel "stable" "Debian 12 Bookworm"
check_release_kernel "testing" "Debian 13 Trixie"
check_release_kernel "unstable" "Debian Sid"

echo ""
echo "Kernel version patterns:"
echo "========================"
echo "5.10.x = Debian 11 (Bullseye/oldstable)"
echo "6.1.x  = Debian 12 (Bookworm/stable)"
echo "6.6.x+ = Debian 13 (Trixie/testing)"
echo "Latest = Debian Sid (unstable)"

echo ""
echo "If your chroot is fetching 6.1.x kernels but should be on Trixie,"
echo "it means the APT sources are pointing to stable (Bookworm) instead of testing."

# If we have access to the chroot, check what it's actually using
CHROOT_PATH="/tmp/zforge_workspace/chroot"
if [ -d "$CHROOT_PATH" ]; then
    echo ""
    echo "Your chroot configuration:"
    echo "========================="
    
    if [ -f "$CHROOT_PATH/etc/apt/sources.list" ]; then
        echo "First line of sources.list:"
        head -1 "$CHROOT_PATH/etc/apt/sources.list" | grep -o "deb.*debian.*" || echo "Could not parse sources.list"
    fi
    
    if [ -f "$CHROOT_PATH/etc/os-release" ]; then
        echo ""
        echo "OS Release info:"
        grep -E "VERSION_CODENAME|VERSION_ID" "$CHROOT_PATH/etc/os-release" || true
    fi
fi