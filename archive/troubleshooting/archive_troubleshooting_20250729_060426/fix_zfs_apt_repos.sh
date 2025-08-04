#!/bin/bash
# Fix APT repository configuration for ZFS package installation in chroot

set -e

CHROOT_PATH="/tmp/zforge_workspace/chroot"

echo "=== ZFS APT Repository Fix Script ==="
echo "Chroot path: $CHROOT_PATH"

# Check if chroot exists
if [ ! -d "$CHROOT_PATH" ]; then
    echo "ERROR: Chroot directory not found at $CHROOT_PATH"
    exit 1
fi

# Detect Debian version
if [ -f "$CHROOT_PATH/etc/os-release" ]; then
    DEBIAN_VERSION=$(grep VERSION_CODENAME "$CHROOT_PATH/etc/os-release" | cut -d'=' -f2 | tr -d '"')
elif [ -f "$CHROOT_PATH/etc/debian_version" ]; then
    VERSION_NUM=$(cat "$CHROOT_PATH/etc/debian_version")
    if [[ "$VERSION_NUM" == *"13"* ]]; then
        DEBIAN_VERSION="trixie"
    elif [[ "$VERSION_NUM" == *"12"* ]]; then
        DEBIAN_VERSION="bookworm"
    else
        DEBIAN_VERSION="trixie"
    fi
else
    DEBIAN_VERSION="trixie"
fi

echo "Detected Debian version: $DEBIAN_VERSION"

# Backup existing sources.list
if [ -f "$CHROOT_PATH/etc/apt/sources.list" ]; then
    echo "Backing up existing sources.list..."
    sudo cp "$CHROOT_PATH/etc/apt/sources.list" "$CHROOT_PATH/etc/apt/sources.list.backup"
fi

# Create new sources.list with contrib
echo "Creating new sources.list with contrib repository..."
cat << EOF | sudo tee "$CHROOT_PATH/etc/apt/sources.list"
# Debian $DEBIAN_VERSION repositories with contrib for ZFS
deb http://deb.debian.org/debian $DEBIAN_VERSION main contrib non-free-firmware
deb-src http://deb.debian.org/debian $DEBIAN_VERSION main contrib non-free-firmware

deb http://deb.debian.org/debian-security $DEBIAN_VERSION-security main contrib non-free-firmware
deb-src http://deb.debian.org/debian-security $DEBIAN_VERSION-security main contrib non-free-firmware
EOF

# Add updates repo for stable releases
if [[ "$DEBIAN_VERSION" != "trixie" && "$DEBIAN_VERSION" != "sid" && "$DEBIAN_VERSION" != "testing" && "$DEBIAN_VERSION" != "unstable" ]]; then
    cat << EOF | sudo tee -a "$CHROOT_PATH/etc/apt/sources.list"

deb http://deb.debian.org/debian $DEBIAN_VERSION-updates main contrib non-free-firmware
deb-src http://deb.debian.org/debian $DEBIAN_VERSION-updates main contrib non-free-firmware
EOF
fi

echo ""
echo "Updating package index in chroot..."
sudo chroot "$CHROOT_PATH" apt-get update

echo ""
echo "Checking available ZFS packages..."
sudo chroot "$CHROOT_PATH" apt-cache search '^zfs' | head -10

echo ""
echo "Installing ZFS packages..."
# Try to install ZFS packages
if sudo chroot "$CHROOT_PATH" apt-get install -y --no-install-recommends zfsutils-linux zfs-dkms; then
    echo "Successfully installed ZFS packages!"
else
    echo "Primary installation failed, trying fallback..."
    if sudo chroot "$CHROOT_PATH" apt-get install -y --no-install-recommends zfsutils-linux; then
        echo "Successfully installed zfsutils-linux!"
    else
        echo "ERROR: Failed to install ZFS packages"
        exit 1
    fi
fi

echo ""
echo "=== ZFS APT repository fix completed successfully! ==="