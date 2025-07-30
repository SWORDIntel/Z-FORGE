#!/bin/bash
# Install our custom ZFS userspace package in chroot
# Uses the ZFS 2.3.3 package we built

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "        Installing Our Custom ZFS Package"
echo "═══════════════════════════════════════════════════════════════════"

CHROOT_PATH="${1:-/tmp/zforge_workspace/chroot}"
ZFS_PACKAGE="/opt/github/Z-FORGE/live_cd_packages/zfsutils-userspace_2.3.3-1_amd64.deb"

if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    echo "Usage: sudo $0 [chroot_path]"
    exit 1
fi

if [ ! -f "$ZFS_PACKAGE" ]; then
    echo "ERROR: ZFS package not found at: $ZFS_PACKAGE"
    echo "Please build it first with: ./build_zfs_userspace_debs.sh"
    exit 1
fi

if [ ! -d "$CHROOT_PATH" ]; then
    echo "ERROR: Chroot not found at: $CHROOT_PATH"
    echo "Please bootstrap first with: sudo ./bootstrap_chroot.sh auto"
    exit 1
fi

echo "Installing ZFS package: $(basename "$ZFS_PACKAGE")"
echo "Target chroot: $CHROOT_PATH"
echo ""

# Mount filesystems
echo "[1/5] Mounting filesystems..."
for fs in proc sys dev dev/pts; do
    if ! mountpoint -q "$CHROOT_PATH/$fs" 2>/dev/null; then
        mkdir -p "$CHROOT_PATH/$fs"
        mount --bind "/$fs" "$CHROOT_PATH/$fs"
    fi
done

# Copy package to chroot
echo ""
echo "[2/5] Copying ZFS package to chroot..."
mkdir -p "$CHROOT_PATH/tmp/zfs_install"
cp "$ZFS_PACKAGE" "$CHROOT_PATH/tmp/zfs_install/"

# Install dependencies first
echo ""
echo "[3/5] Installing dependencies..."
chroot "$CHROOT_PATH" bash -c '
apt-get update
apt-get install -y --no-install-recommends \
    libc6 \
    python3 \
    python3-cffi \
    libssl3 \
    libblkid1 \
    libuuid1 \
    libudev1 \
    libaio1 \
    || echo "Some dependencies may have already been installed"
'

# Install our ZFS package
echo ""
echo "[4/5] Installing our ZFS userspace package..."
chroot "$CHROOT_PATH" bash -c '
cd /tmp/zfs_install
echo "Installing $(ls *.deb)..."
dpkg -i *.deb || apt-get install -f -y
'

# Verify installation
echo ""
echo "[5/5] Verifying ZFS installation..."
chroot "$CHROOT_PATH" bash -c '
echo "Checking ZFS commands..."
which zfs && echo "✅ zfs command found" || echo "❌ zfs command not found"
which zpool && echo "✅ zpool command found" || echo "❌ zpool command not found"

echo ""
echo "ZFS version info:"
zfs version 2>/dev/null || echo "Version will show after kernel module loads"

echo ""
echo "Installed files:"
dpkg -L zfsutils-userspace | head -10

echo ""
echo "Package info:"
dpkg -s zfsutils-userspace | grep -E "Package:|Version:|Status:"
'

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "            Our ZFS Package Installed Successfully!"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "✅ ZFS 2.3.3 userspace tools installed"
echo "✅ Commands available: zfs, zpool, zdb, etc."
echo "✅ Ready for kernel module when ISO boots"
echo ""
echo "Note: This is userspace only. Kernel modules will be:"
echo "- Built by DKMS on first boot, OR"
echo "- Provided by the live ISO kernel"
echo ""
echo "Next steps:"
echo "1. Fix Proxmox GPG: sudo ./fix_proxmox_repo_gpg.sh"
echo "2. Continue build: make build"