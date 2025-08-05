#!/bin/bash
# Diagnose package installation issues in chroot

set -euo pipefail

WORKSPACE="${ZFORGE_WORKSPACE:-/home/john/zforge_workspace}"
CHROOT_PATH="$WORKSPACE/chroot"

echo "=== Diagnosing Chroot Package Installation Issues ==="

# Check if chroot exists
if [ ! -d "$CHROOT_PATH" ]; then
    echo "❌ ERROR: Chroot directory not found at $CHROOT_PATH"
    exit 1
fi

# Check chroot network
echo "1. Checking chroot network configuration..."
if [ -f "$CHROOT_PATH/etc/resolv.conf" ]; then
    echo "   Nameservers:"
    cat "$CHROOT_PATH/etc/resolv.conf" | grep nameserver || echo "   No nameservers found!"
else
    echo "   ❌ No resolv.conf found!"
fi

# Check APT sources in chroot
echo ""
echo "2. Checking chroot APT sources..."
if [ -f "$CHROOT_PATH/etc/apt/sources.list" ]; then
    echo "   Main sources:"
    grep -v "^#" "$CHROOT_PATH/etc/apt/sources.list" | grep -v "^$" | head -5
else
    echo "   ❌ No sources.list found!"
fi

# Check APT cache status in chroot
echo ""
echo "3. Checking APT cache in chroot..."
if [ -d "$CHROOT_PATH/var/lib/apt/lists" ]; then
    COUNT=$(find "$CHROOT_PATH/var/lib/apt/lists" -name "*_Packages" | wc -l)
    echo "   Package lists: $COUNT files"
    if [ $COUNT -eq 0 ]; then
        echo "   ❌ No package lists found! Need to run apt update in chroot."
    fi
else
    echo "   ❌ APT lists directory not found!"
fi

# Test package installation
echo ""
echo "4. Testing package installation in chroot..."
TEST_PKG="nano"  # Small, simple package for testing

# Update package lists first
echo "   Updating package lists..."
if chroot "$CHROOT_PATH" apt-get update; then
    echo "   ✅ Package lists updated successfully"
else
    echo "   ❌ Failed to update package lists"
    echo "   Attempting to fix..."
    
    # Fix DNS
    echo "nameserver 8.8.8.8" > "$CHROOT_PATH/etc/resolv.conf"
    echo "nameserver 8.8.4.4" >> "$CHROOT_PATH/etc/resolv.conf"
    
    # Retry update
    chroot "$CHROOT_PATH" apt-get update || echo "   Still failing!"
fi

# Try to install test package
echo ""
echo "   Testing installation of '$TEST_PKG'..."
if chroot "$CHROOT_PATH" apt-get install -y --no-install-recommends "$TEST_PKG" 2>&1; then
    echo "   ✅ Test package installed successfully"
    chroot "$CHROOT_PATH" dpkg -l "$TEST_PKG" | grep "^ii"
else
    echo "   ❌ Failed to install test package"
fi

# Check specific live environment packages
echo ""
echo "5. Checking availability of live environment packages..."
LIVE_PACKAGES=(
    "live-boot"
    "live-boot-initramfs-tools"
    "live-config"
    "live-config-systemd"
    "network-manager"
    "grub-pc"
    "grub-efi-amd64"
    "squashfs-tools"
    "xorriso"
)

for pkg in "${LIVE_PACKAGES[@]}"; do
    if chroot "$CHROOT_PATH" apt-cache show "$pkg" >/dev/null 2>&1; then
        echo "   ✅ $pkg - available"
    else
        echo "   ❌ $pkg - NOT FOUND"
    fi
done

# Check for held or broken packages
echo ""
echo "6. Checking for package issues..."
echo "   Held packages:"
chroot "$CHROOT_PATH" dpkg --get-selections | grep hold || echo "   None"

echo ""
echo "   Broken packages:"
chroot "$CHROOT_PATH" dpkg -l | grep -E "^[^i]" | head -5 || echo "   None found"

# Summary and recommendations
echo ""
echo "=== Summary and Recommendations ==="

if [ ! -f "$CHROOT_PATH/etc/resolv.conf" ] || [ $(cat "$CHROOT_PATH/etc/resolv.conf" | grep nameserver | wc -l) -eq 0 ]; then
    echo "❌ Network is not configured in chroot"
    echo "   Fix: echo 'nameserver 8.8.8.8' > $CHROOT_PATH/etc/resolv.conf"
fi

if [ ! -d "$CHROOT_PATH/var/lib/apt/lists" ] || [ $(find "$CHROOT_PATH/var/lib/apt/lists" -name "*_Packages" | wc -l) -eq 0 ]; then
    echo "❌ APT cache is empty"
    echo "   Fix: chroot $CHROOT_PATH apt-get update"
fi

echo ""
echo "To manually test package installation:"
echo "  chroot $CHROOT_PATH"
echo "  apt-get update"
echo "  apt-get install -y live-boot"
echo "  exit"