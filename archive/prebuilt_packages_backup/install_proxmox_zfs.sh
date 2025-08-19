#!/bin/bash
# Install Proxmox ZFS packages

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

echo "Installing Proxmox ZFS packages..."

# Install in correct order
cd "$SCRIPT_DIR"

# Libraries first
dpkg -i libnvpair3linux_*.deb libuutil3linux_*.deb || true
dpkg -i libzfs4linux_*.deb libzpool5linux_*.deb || true

# Then utilities
dpkg -i zfsutils-linux_*.deb zfs-zed_*.deb || true
dpkg -i zfs-initramfs_*.deb || true

# Fix any dependencies
apt-get install -f -y

echo "Proxmox ZFS packages installed!"
