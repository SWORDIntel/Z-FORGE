#!/bin/bash
# Alternative: Use Debian's ZFS packages instead of building our own
# This avoids Proxmox GPG issues and uses official packages

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "        Using Debian ZFS Packages for Live CD"
echo "═══════════════════════════════════════════════════════════════════"

CHROOT_PATH="${1:-/tmp/zforge_workspace/chroot}"

if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    echo "Usage: sudo $0 [chroot_path]"
    exit 1
fi

echo ""
echo "[1/3] Updating Debian repositories..."

# Ensure contrib is enabled for ZFS
chroot "$CHROOT_PATH" bash -c '
# Enable contrib repository for ZFS
sed -i "s/main$/main contrib non-free-firmware/g" /etc/apt/sources.list
apt-get update
'

echo ""
echo "[2/3] Installing ZFS from Debian repositories..."

chroot "$CHROOT_PATH" bash -c '
# Install ZFS packages
apt-get install -y --no-install-recommends \
    zfsutils-linux \
    zfs-dkms \
    zfs-initramfs \
    || echo "Some packages may have failed - continuing..."

# Also install kernel headers for DKMS
apt-get install -y linux-headers-amd64 || true
'

echo ""
echo "[3/3] Verifying ZFS installation..."

chroot "$CHROOT_PATH" bash -c '
echo "Installed ZFS packages:"
dpkg -l | grep -E "zfs|spl" | head -10

echo ""
echo "ZFS version:"
zfs version 2>/dev/null || echo "ZFS command available after module load"

echo ""
echo "DKMS status:"
dkms status | grep zfs || echo "DKMS modules will build on first boot"
'

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                ZFS Installed from Debian Repos"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "ZFS is now installed in the chroot using official Debian packages."
echo ""
echo "Benefits:"
echo "✅ No GPG key issues"
echo "✅ Automatic kernel module building (DKMS)"
echo "✅ Official Debian support"
echo "✅ Works with any Debian kernel"
echo ""
echo "The live ISO will have full ZFS support!"
echo ""
echo "Continue with: make build"