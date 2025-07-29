#!/bin/bash
# Fix APT sources for ZFS packages with sudo password

CHROOT_PATH="${1:-/tmp/zforge_workspace/chroot}"
SUDO_PASS="1786"

echo "Fixing APT sources for ZFS packages in chroot: $CHROOT_PATH"

# Check if chroot exists
if [ ! -d "$CHROOT_PATH" ]; then
    echo "Error: Chroot path does not exist: $CHROOT_PATH"
    exit 1
fi

# Update sources.list to include contrib
echo "Updating sources.list..."
echo "$SUDO_PASS" | sudo -S sed -i 's/main$/main contrib non-free-firmware/g' "$CHROOT_PATH/etc/apt/sources.list"
echo "$SUDO_PASS" | sudo -S sed -i 's/main non-free-firmware$/main contrib non-free-firmware/g' "$CHROOT_PATH/etc/apt/sources.list"

# Show updated sources
echo "Updated sources.list:"
echo "$SUDO_PASS" | sudo -S grep -v "^#" "$CHROOT_PATH/etc/apt/sources.list" | grep -v "^$"

# Update package lists
echo "Updating package lists..."
echo "$SUDO_PASS" | sudo -S chroot "$CHROOT_PATH" apt-get update

# Check if ZFS packages are available
echo "Checking ZFS package availability..."
echo "$SUDO_PASS" | sudo -S chroot "$CHROOT_PATH" apt-cache policy zfsutils-linux || echo "zfsutils-linux not found"
echo "$SUDO_PASS" | sudo -S chroot "$CHROOT_PATH" apt-cache policy zfs-dkms || echo "zfs-dkms not found"
echo "$SUDO_PASS" | sudo -S chroot "$CHROOT_PATH" apt-cache policy zfs || echo "zfs not found"

# Try to install ZFS packages
echo "Attempting to install ZFS packages..."
echo "$SUDO_PASS" | sudo -S chroot "$CHROOT_PATH" apt-get install -y --no-install-recommends zfsutils-linux zfs-dkms || {
    echo "Standard packages failed, trying alternatives..."
    echo "$SUDO_PASS" | sudo -S chroot "$CHROOT_PATH" apt-get install -y --no-install-recommends zfs || {
        echo "ZFS installation failed - packages may not be available in Trixie yet"
    }
}

echo "APT sources fixed and ZFS installation attempted."