#!/bin/bash
# Upgrade ZFS to 2.3.3+ on Debian Trixie

set -e

echo "=== ZFS Upgrade Script for Debian Trixie ==="
echo "Current ZFS version: $(zfs --version | head -1)"
echo "Debian version: $(cat /etc/debian_version)"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run with sudo"
    exit 1
fi

# Remove old bookworm backports if exists
rm -f /etc/apt/sources.list.d/bookworm-backports.list

# For Trixie, we need experimental or sid for latest ZFS
echo "Adding Debian experimental repository for ZFS 2.3.3..."
cat > /etc/apt/sources.list.d/debian-experimental.list << EOF
deb http://deb.debian.org/debian experimental main contrib non-free non-free-firmware
EOF

# Add apt preferences to prevent unwanted upgrades from experimental
cat > /etc/apt/preferences.d/zfs-experimental << EOF
Package: *
Pin: release a=experimental
Pin-Priority: 1

Package: zfsutils-linux zfs-dkms zfs-zed libzfs4t64 libzpool5t64 libnvpair3t64 libuutil3t64
Pin: release a=experimental
Pin-Priority: 600
EOF

# Update package list
echo "Updating package list..."
apt update

# Check available versions
echo ""
echo "Available ZFS versions:"
apt-cache policy zfsutils-linux | grep -A5 "Version table"

# Install latest ZFS
echo ""
echo "Installing latest ZFS..."
apt install -t experimental zfsutils-linux zfs-dkms zfs-zed -y

# Verify installation
echo ""
echo "=== Upgrade Complete ==="
echo "New ZFS version: $(zfs --version | head -1)"
echo ""

# Check module status
echo "Checking ZFS module status..."
if lsmod | grep -q zfs; then
    echo "ZFS module loaded. Version: $(modinfo zfs | grep ^version: | awk '{print $2}')"
else
    echo "WARNING: ZFS module not loaded. A reboot may be required."
fi

echo ""
echo "ZFS pool status:"
zpool status

echo ""
echo "IMPORTANT: A reboot is recommended to ensure all modules are properly loaded."
echo ""
echo "Snapshots available for rollback:"
zfs list -t snapshot | grep @before-zfs-upgrade | head -5

echo ""
echo "After reboot, verify with: zfs --version"