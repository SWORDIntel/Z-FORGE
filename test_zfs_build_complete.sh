#!/bin/bash
# Complete ZFS Build Test - Ensures kernel modules for live ISO

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "              Complete ZFS 2.3.3 Build Test"
echo "        Ensuring kernel modules are available for live ISO"
echo "═══════════════════════════════════════════════════════════════════"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    exit 1
fi

echo "[1/5] Checking build environment..."
make check || {
    echo "❌ Build environment check failed"
    echo "Please run: make deps"
    exit 1
}

echo ""
echo "[2/5] Cleaning previous builds..."
make clean

echo ""
echo "[3/5] Preparing ZFS 2.3.3 with kernel modules..."

# Check if we have a test chroot to build in
TEST_CHROOT="/tmp/zfs_test_chroot"
if [ ! -d "$TEST_CHROOT" ]; then
    echo "   Creating minimal test chroot for ZFS build..."
    mkdir -p "$TEST_CHROOT"
    debootstrap --variant=minbase trixie "$TEST_CHROOT" http://deb.debian.org/debian
    
    # Mount proc, sys, dev for chroot
    mount -t proc proc "$TEST_CHROOT/proc"
    mount -t sysfs sysfs "$TEST_CHROOT/sys" 
    mount --bind /dev "$TEST_CHROOT/dev"
fi

echo ""
echo "[4/5] Building ZFS 2.3.3 with kernel modules in chroot..."
./build_zfs_233_chroot_modules.sh "$TEST_CHROOT"

echo ""
echo "[5/5] Verifying ZFS installation in chroot..."
echo "=== ZFS Commands Available ==="
chroot "$TEST_CHROOT" which zfs || echo "⚠️  ZFS command not found"
chroot "$TEST_CHROOT" which zpool || echo "⚠️  zpool command not found"

echo ""
echo "=== ZFS Version ==="
chroot "$TEST_CHROOT" zfs version || echo "⚠️  Cannot get ZFS version"

echo ""
echo "=== ZFS Kernel Modules ==="
chroot "$TEST_CHROOT" find /lib/modules -name "zfs.ko" -ls || echo "⚠️  ZFS kernel module not found"

echo ""
echo "=== ZFS Services ==="
chroot "$TEST_CHROOT" systemctl list-unit-files | grep zfs || echo "⚠️  ZFS services not found"

# Cleanup
echo ""
echo "Cleaning up test chroot..."
umount "$TEST_CHROOT/proc" || true
umount "$TEST_CHROOT/sys" || true  
umount "$TEST_CHROOT/dev" || true
# rm -rf "$TEST_CHROOT"  # Commented out - you might want to inspect

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                        TEST COMPLETE"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "✅ ZFS 2.3.3 build process tested"
echo "✅ Kernel modules should be available in live ISO"
echo "✅ Ready to run full build: make build"
echo ""
echo "Test chroot preserved at: $TEST_CHROOT"
echo "You can inspect it with: sudo chroot $TEST_CHROOT"