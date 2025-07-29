#!/bin/bash
# Quick check of kernel situation

CHROOT_PATH="/tmp/zforge_workspace/chroot"

echo "=== Quick Kernel Check ==="
echo ""

if [ ! -d "$CHROOT_PATH" ]; then
    echo "ERROR: Chroot not found at $CHROOT_PATH"
    exit 1
fi

echo "1. Current sources.list (first 5 lines):"
sudo head -5 "$CHROOT_PATH/etc/apt/sources.list" 2>/dev/null || echo "Cannot read sources.list"

echo ""
echo "2. OS Release info:"
sudo grep -E "PRETTY_NAME|VERSION_CODENAME" "$CHROOT_PATH/etc/os-release" 2>/dev/null || echo "Cannot read os-release"

echo ""
echo "3. Currently installed kernels:"
sudo chroot "$CHROOT_PATH" dpkg -l 2>/dev/null | grep '^ii.*linux-image' | grep -v dbg || echo "No kernels installed"

echo ""
echo "4. What apt would install for linux-image-amd64:"
sudo chroot "$CHROOT_PATH" apt-cache policy linux-image-amd64 2>/dev/null | head -10 || echo "Cannot check policy"

echo ""
echo "5. Available 6.12 kernels:"
sudo chroot "$CHROOT_PATH" apt-cache search "linux-image-6.12" 2>/dev/null | grep -v dbg || echo "No 6.12 kernels found"