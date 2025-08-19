#!/bin/bash
# Fix ZFS module version mismatch

set -e

echo "=== Fixing ZFS Module Version ==="

# Check current status
echo "Current status:"
echo "Userspace: $(zfs --version | head -1)"
echo "Kernel module: $(modinfo zfs | grep version | head -1)"

# Remove old modules
echo ""
echo "Removing old ZFS modules..."
modprobe -r zfs || true
modprobe -r zcommon || true
modprobe -r znvpair || true
modprobe -r zunicode || true
modprobe -r zavl || true
modprobe -r spl || true

# Check for old DKMS versions
echo "Checking DKMS..."
dkms status | grep zfs || echo "No DKMS ZFS found"

# Remove old DKMS if exists
for version in $(dkms status | grep zfs | cut -d',' -f2 | cut -d':' -f1 | tr -d ' '); do
    echo "Removing DKMS version: $version"
    dkms remove zfs/$version --all || true
done

# Install new modules from our build
echo ""
echo "Installing new ZFS 2.3.3 modules..."
cd /usr/src/zfs-build-minimal/zfs-2.3.3/module

# Force install our modules
cp spl.ko /lib/modules/$(uname -r)/extra/
cp zfs.ko /lib/modules/$(uname -r)/extra/

# Update module dependencies
echo "Updating module dependencies..."
depmod -a

# Load new modules
echo "Loading ZFS 2.3.3 modules..."
modprobe spl
modprobe zfs

# Verify
echo ""
echo "=== Verification ==="
echo "Userspace: $(zfs --version | head -1)"
echo "Kernel module: $(modinfo zfs | grep version | head -1)"

# Test ZFS functionality
echo ""
echo "Testing ZFS pool status..."
zpool status

echo ""
echo "ZFS 2.3.3 installation complete!"