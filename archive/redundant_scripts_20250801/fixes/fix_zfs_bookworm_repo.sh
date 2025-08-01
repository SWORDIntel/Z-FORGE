#!/bin/bash
# Add Debian Bookworm repository for ZFS packages

CHROOT_PATH="${1:-${CHROOT_PATH:-/home/john/zforge_workspace/chroot}}"
SUDO_PASS="1786"

echo "Adding Debian Bookworm repository for ZFS packages..."

# Create apt sources list for bookworm ZFS
echo "$SUDO_PASS" | sudo -S tee "$CHROOT_PATH/etc/apt/sources.list.d/bookworm-zfs.list" > /dev/null << EOF
# Debian Bookworm repository for ZFS packages
deb http://deb.debian.org/debian bookworm main contrib non-free-firmware
deb http://deb.debian.org/debian bookworm-backports main contrib non-free-firmware
EOF

# Create apt preferences to pin ZFS packages from bookworm
echo "$SUDO_PASS" | sudo -S tee "$CHROOT_PATH/etc/apt/preferences.d/zfs-bookworm" > /dev/null << EOF
# Pin ZFS packages from bookworm
Package: zfsutils-linux zfs-dkms zfs-zed libzfs4linux libzpool5linux libnvpair3linux libuutil3linux
Pin: release n=bookworm
Pin-Priority: 900

Package: zfsutils-linux zfs-dkms zfs-zed libzfs4linux libzpool5linux libnvpair3linux libuutil3linux  
Pin: release n=bookworm-backports
Pin-Priority: 850

# Prevent other packages from bookworm
Package: *
Pin: release n=bookworm
Pin-Priority: 100

Package: *
Pin: release n=bookworm-backports
Pin-Priority: 100
EOF

# Update package lists
echo "Updating package lists..."
echo "$SUDO_PASS" | sudo -S chroot "$CHROOT_PATH" apt-get update

# Check ZFS package availability
echo "Checking ZFS packages from bookworm..."
echo "$SUDO_PASS" | sudo -S chroot "$CHROOT_PATH" apt-cache policy zfsutils-linux

# Install ZFS packages
echo "Installing ZFS packages from bookworm..."
echo "$SUDO_PASS" | sudo -S chroot "$CHROOT_PATH" apt-get install -y --no-install-recommends -t bookworm-backports zfsutils-linux zfs-dkms || {
    echo "Trying without backports..."
    echo "$SUDO_PASS" | sudo -S chroot "$CHROOT_PATH" apt-get install -y --no-install-recommends -t bookworm zfsutils-linux zfs-dkms || {
        echo "Trying minimal ZFS installation..."
        echo "$SUDO_PASS" | sudo -S chroot "$CHROOT_PATH" apt-get install -y --no-install-recommends -t bookworm zfsutils-linux
    }
}

echo "ZFS installation from bookworm repository completed."