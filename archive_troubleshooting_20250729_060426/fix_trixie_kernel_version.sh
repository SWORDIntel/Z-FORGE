#!/bin/bash
# Fix Trixie kernel version issue - ensure we get actual Trixie kernels

set -e

CHROOT_PATH="/tmp/zforge_workspace/chroot"

echo "=== Z-FORGE Trixie Kernel Version Fix ==="
echo "This script ensures you get the proper Trixie (testing) kernel"
echo ""

# Check if chroot exists
if [ ! -d "$CHROOT_PATH" ]; then
    echo "ERROR: Chroot directory not found at $CHROOT_PATH"
    exit 1
fi

# Step 1: Verify we're actually using Trixie
echo "Step 1: Verifying Debian release..."
if [ -f "$CHROOT_PATH/etc/os-release" ]; then
    VERSION_CODENAME=$(grep VERSION_CODENAME "$CHROOT_PATH/etc/os-release" | cut -d'=' -f2 | tr -d '"')
    echo "Detected codename: $VERSION_CODENAME"
else
    echo "WARNING: Could not detect version from os-release"
    VERSION_CODENAME="trixie"
fi

# Step 2: Fix APT sources to use testing/trixie
echo ""
echo "Step 2: Configuring APT sources for Debian Testing/Trixie..."

# Backup current sources
sudo cp "$CHROOT_PATH/etc/apt/sources.list" "$CHROOT_PATH/etc/apt/sources.list.backup.$(date +%Y%m%d_%H%M%S)"

# Create proper Trixie sources
cat << EOF | sudo tee "$CHROOT_PATH/etc/apt/sources.list"
# Debian Testing (Trixie) repositories
deb http://deb.debian.org/debian testing main contrib non-free-firmware
deb-src http://deb.debian.org/debian testing main contrib non-free-firmware

deb http://deb.debian.org/debian-security testing-security main contrib non-free-firmware
deb-src http://deb.debian.org/debian-security testing-security main contrib non-free-firmware

# You can also use the codename directly:
# deb http://deb.debian.org/debian trixie main contrib non-free-firmware
# deb-src http://deb.debian.org/debian trixie main contrib non-free-firmware
EOF

# Step 3: Clear APT cache and update
echo ""
echo "Step 3: Clearing APT cache and updating package lists..."
sudo chroot "$CHROOT_PATH" apt-get clean
sudo rm -rf "$CHROOT_PATH/var/lib/apt/lists/*"
sudo chroot "$CHROOT_PATH" apt-get update

# Step 4: Check what kernels are now available
echo ""
echo "Step 4: Checking available kernels from Testing/Trixie..."
echo "Latest available kernels:"
sudo chroot "$CHROOT_PATH" apt-cache search "^linux-image-[0-9]" | grep -v "dbg\|cloud\|rt" | sort -V | tail -10

# Step 5: Install the testing kernel
echo ""
echo "Step 5: Installing Debian Testing kernel..."

# First, ensure dpkg is in good state
sudo chroot "$CHROOT_PATH" dpkg --configure -a || true

# Try to install the latest testing kernel
echo "Installing linux-image-amd64 from testing..."
if sudo chroot "$CHROOT_PATH" apt-get install -y linux-image-amd64 linux-headers-amd64; then
    echo "Successfully installed testing kernel metapackage"
else
    echo "Metapackage failed, trying specific kernel..."
    
    # Get the latest 6.6.x or newer kernel
    LATEST_KERNEL=$(sudo chroot "$CHROOT_PATH" apt-cache search "^linux-image-[0-9]" | grep -E "linux-image-6\.[6-9]\.|linux-image-[7-9]\." | grep -v "unsigned\|dbg\|cloud\|rt" | sort -V | tail -1 | awk '{print $1}')
    
    if [ -n "$LATEST_KERNEL" ]; then
        echo "Found testing kernel: $LATEST_KERNEL"
        KERNEL_VERSION=$(echo "$LATEST_KERNEL" | sed 's/linux-image-//')
        
        sudo chroot "$CHROOT_PATH" apt-get install -y \
            "$LATEST_KERNEL" \
            "linux-headers-${KERNEL_VERSION}" \
            build-essential \
            dkms
    else
        echo "ERROR: Could not find a proper testing kernel!"
        echo "This might indicate the sources are not properly configured."
    fi
fi

# Step 6: Install ZFS for the new kernel
echo ""
echo "Step 6: Installing ZFS packages..."
sudo chroot "$CHROOT_PATH" apt-get remove -y zfs-initramfs 2>/dev/null || true
sudo chroot "$CHROOT_PATH" apt-get install -y zfsutils-linux zfs-dkms || true

# Step 7: Verify installation
echo ""
echo "Step 7: Verification..."
echo ""
echo "Installed kernels:"
sudo chroot "$CHROOT_PATH" dpkg -l | grep -E "^ii.*linux-image" | grep -v dbg

echo ""
echo "APT policy for linux-image-amd64:"
sudo chroot "$CHROOT_PATH" apt-cache policy linux-image-amd64

echo ""
echo "=== Fix Complete ==="
echo ""
echo "Notes:"
echo "- Debian Testing (Trixie) should have kernel 6.6.x or newer"
echo "- If you're still seeing 6.1.x kernels, the APT cache might need clearing"
echo "- You can force a specific version with: apt-get install linux-image-6.6.13-amd64"
echo ""
echo "To completely refresh APT and try again:"
echo "  sudo chroot $CHROOT_PATH apt-get clean"
echo "  sudo chroot $CHROOT_PATH rm -rf /var/lib/apt/lists/*"
echo "  sudo chroot $CHROOT_PATH apt-get update"