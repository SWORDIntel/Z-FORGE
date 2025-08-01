#!/bin/bash
# Fix APT sources for ZFS packages

CHROOT_PATH="${1:-${CHROOT_PATH:-/home/john/zforge_workspace/chroot}}"

echo "Fixing APT sources for ZFS packages in chroot: $CHROOT_PATH"

# Check if chroot exists
if [ ! -d "$CHROOT_PATH" ]; then
    echo "Error: Chroot path does not exist: $CHROOT_PATH"
    exit 1
fi

# Update sources.list to include contrib
echo "Updating sources.list..."
sudo sed -i 's/main$/main contrib non-free-firmware/g' "$CHROOT_PATH/etc/apt/sources.list"
sudo sed -i 's/main non-free-firmware$/main contrib non-free-firmware/g' "$CHROOT_PATH/etc/apt/sources.list"

# Show updated sources
echo "Updated sources.list:"
grep -v "^#" "$CHROOT_PATH/etc/apt/sources.list" | grep -v "^$"

# Update package lists
echo "Updating package lists..."
sudo chroot "$CHROOT_PATH" apt-get update

# Check if ZFS packages are available
echo "Checking ZFS package availability..."
sudo chroot "$CHROOT_PATH" apt-cache policy zfsutils-linux || echo "zfsutils-linux not found"
sudo chroot "$CHROOT_PATH" apt-cache policy zfs-dkms || echo "zfs-dkms not found"
sudo chroot "$CHROOT_PATH" apt-cache policy zfs || echo "zfs not found"

echo "APT sources fixed. You can now try installing ZFS packages."
