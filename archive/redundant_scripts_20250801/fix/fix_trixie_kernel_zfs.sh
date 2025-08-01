#!/bin/bash
# Comprehensive fix for Debian Trixie kernel and ZFS compatibility

set -e

echo "=== Z-FORGE Trixie Kernel & ZFS Fix ==="
echo "This script will:"
echo "1. Update APT sources to include contrib repository"
echo "2. Install Debian Trixie kernel with headers"
echo "3. Install ZFS with DKMS support"
echo "4. Patch kernel acquisition module for future builds"
echo ""

CHROOT_PATH="${CHROOT_PATH:-/home/john/zforge_workspace/chroot}"

# Function to detect Debian release
detect_debian_release() {
    if [ -f "$CHROOT_PATH/etc/os-release" ]; then
        grep VERSION_CODENAME "$CHROOT_PATH/etc/os-release" | cut -d'=' -f2 | tr -d '"'
    elif [ -f "$CHROOT_PATH/etc/debian_version" ]; then
        VERSION=$(cat "$CHROOT_PATH/etc/debian_version")
        if [[ "$VERSION" == *"13"* ]] || [[ "$VERSION" == *"trixie"* ]]; then
            echo "trixie"
        elif [[ "$VERSION" == *"12"* ]]; then
            echo "bookworm"
        else
            echo "trixie"
        fi
    else
        echo "trixie"
    fi
}

# Check if chroot exists
if [ ! -d "$CHROOT_PATH" ]; then
    echo "ERROR: Chroot directory not found at $CHROOT_PATH"
    echo "Please ensure the Z-FORGE build has created the chroot environment."
    exit 1
fi

DEBIAN_RELEASE=$(detect_debian_release)
echo "Detected Debian release: $DEBIAN_RELEASE"

# Step 1: Fix APT sources
echo ""
echo "Step 1: Configuring APT sources with contrib repository..."
cat << EOF | sudo tee "$CHROOT_PATH/etc/apt/sources.list"
# Debian $DEBIAN_RELEASE repositories with contrib for ZFS
deb http://deb.debian.org/debian $DEBIAN_RELEASE main contrib non-free-firmware
deb-src http://deb.debian.org/debian $DEBIAN_RELEASE main contrib non-free-firmware

deb http://deb.debian.org/debian-security $DEBIAN_RELEASE-security main contrib non-free-firmware
deb-src http://deb.debian.org/debian-security $DEBIAN_RELEASE-security main contrib non-free-firmware
EOF

# Update package index
echo "Updating package index..."
sudo chroot "$CHROOT_PATH" apt-get update

# Step 2: Install kernel with headers
echo ""
echo "Step 2: Installing Debian $DEBIAN_RELEASE kernel with headers..."

# Get latest available kernel
LATEST_KERNEL=$(sudo chroot "$CHROOT_PATH" apt-cache search '^linux-image-[0-9]' | grep -E 'linux-image-[0-9]+\.[0-9]+\.[0-9]+-[0-9]+-amd64' | sort -V | tail -1 | awk '{print $1}')

if [ -z "$LATEST_KERNEL" ]; then
    echo "WARNING: Could not find specific kernel version, using metapackage"
    KERNEL_PKG="linux-image-amd64"
    HEADERS_PKG="linux-headers-amd64"
else
    echo "Found latest kernel: $LATEST_KERNEL"
    KERNEL_VERSION=$(echo "$LATEST_KERNEL" | sed 's/linux-image-//')
    KERNEL_PKG="$LATEST_KERNEL"
    HEADERS_PKG="linux-headers-${KERNEL_VERSION}"
fi

# Install kernel, headers, and build tools
echo "Installing kernel packages..."
sudo chroot "$CHROOT_PATH" apt-get install -y \
    $KERNEL_PKG \
    $HEADERS_PKG \
    linux-headers-generic \
    build-essential \
    dkms \
    bc \
    kmod

# Step 3: Install ZFS with DKMS
echo ""
echo "Step 3: Installing ZFS with DKMS support..."

# Remove conflicting packages
sudo chroot "$CHROOT_PATH" apt-get remove -y zfs-initramfs 2>/dev/null || true

# Install ZFS packages
if sudo chroot "$CHROOT_PATH" apt-get install -y zfsutils-linux zfs-dkms zfs-dracut; then
    echo "ZFS packages installed successfully!"
else
    echo "WARNING: zfs-dracut failed, installing without it..."
    sudo chroot "$CHROOT_PATH" apt-get install -y zfsutils-linux zfs-dkms
fi

# Check DKMS status
echo ""
echo "Checking DKMS status..."
sudo chroot "$CHROOT_PATH" dkms status || true

# Step 4: Patch kernel acquisition module
echo ""
echo "Step 4: Patching kernel acquisition module for future builds..."
if [ -f "/opt/github/Z-FORGE/kernel_acquisition_trixie_patch.py" ]; then
    python3 /opt/github/Z-FORGE/kernel_acquisition_trixie_patch.py
else
    echo "WARNING: Patch script not found, skipping module patching"
fi

# Verify installation
echo ""
echo "=== Verification ==="
echo "Installed kernel:"
sudo chroot "$CHROOT_PATH" dpkg -l | grep linux-image | grep '^ii'

echo ""
echo "Installed ZFS packages:"
sudo chroot "$CHROOT_PATH" dpkg -l | grep -E '^ii.*(zfs|spl)' || echo "No ZFS packages found"

echo ""
echo "ZFS module status:"
sudo chroot "$CHROOT_PATH" modinfo zfs 2>/dev/null || echo "ZFS module not yet built"

echo ""
echo "=== Fix completed! ==="
echo ""
echo "Next steps:"
echo "1. The build system should now be able to continue with ZFS integration"
echo "2. DKMS will automatically build ZFS modules for the installed kernel"
echo "3. Future builds will use the patched kernel acquisition module"