#!/bin/bash
# Upgrade ZFS to 2.3.3 for kernel 6.13 compatibility

set -e

echo "=== ZFS 2.3.3 Upgrade Script ==="
echo "Current ZFS version: $(zfs --version | head -1)"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run with sudo"
    exit 1
fi

# Check for root pool
echo "Checking ZFS pools..."
zpool list
echo ""

ROOT_POOL=$(mount | grep -E "^.* on / type zfs" | cut -d' ' -f1 | cut -d'/' -f1)
if [ -n "$ROOT_POOL" ]; then
    echo "System is running on ZFS root pool: $ROOT_POOL"
    echo "This pool cannot be exported during upgrade."
    echo ""
fi

# Create snapshot for safety
echo "Creating snapshot before upgrade..."
for pool in $(zpool list -H -o name); do
    echo "Creating snapshot: ${pool}@before-zfs-upgrade"
    zfs snapshot -r ${pool}@before-zfs-upgrade || true
done

# Add ZFS testing repository for latest version
echo ""
echo "Adding ZFS repository..."
echo "deb http://deb.debian.org/debian bookworm-backports main contrib" > /etc/apt/sources.list.d/bookworm-backports.list

# Update package list
apt update

# Stop ZFS services that can be stopped
echo ""
echo "Stopping ZFS services..."
systemctl stop zfs-zed || true
systemctl stop zfs-import-cache || true

# Install ZFS 2.3.3 from backports
echo ""
echo "Installing ZFS 2.3.3..."
apt install -t bookworm-backports zfsutils-linux zfs-dkms zfs-zed

# The upgrade will handle module rebuild via DKMS automatically
echo ""
echo "ZFS modules will be rebuilt automatically by DKMS..."

# Restart ZFS services
echo ""
echo "Restarting ZFS services..."
systemctl start zfs-import-cache || true
systemctl start zfs-zed || true

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
echo "IMPORTANT: Since the root pool couldn't be exported during upgrade,"
echo "          a reboot is recommended to ensure all modules are properly loaded."
echo ""
echo "Snapshots created:"
zfs list -t snapshot | grep @before-zfs-upgrade

echo ""
echo "To rollback if needed:"
echo "  zfs rollback -r ${ROOT_POOL}@before-zfs-upgrade"
echo ""
echo "To remove snapshots after successful testing:"
echo "  zfs destroy -r ${ROOT_POOL}@before-zfs-upgrade"