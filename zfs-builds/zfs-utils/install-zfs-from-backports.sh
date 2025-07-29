#!/bin/bash
# Install ZFS from Debian backports or build from git

set -e

echo "=== Installing ZFS 2.3.x ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run with sudo"
    exit 1
fi

# Option 1: Try OpenZFS repository
echo "Adding OpenZFS repository..."
wget -qO - https://apt.openzfs.org/key.asc | apt-key add -
echo "deb https://apt.openzfs.org/debian-testing trixie main" > /etc/apt/sources.list.d/openzfs.list

apt update

echo "Available ZFS versions:"
apt-cache policy zfsutils-linux | head -10

echo ""
echo "Installing ZFS..."
apt install -y zfsutils-linux zfs-dkms

echo ""
echo "ZFS installed!"
zfs --version