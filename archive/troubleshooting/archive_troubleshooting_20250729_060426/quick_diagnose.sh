#!/bin/bash
# Quick diagnosis of current issues

CHROOT="/tmp/zforge_workspace/chroot"

echo "=== Quick System Diagnosis ==="
echo

# Check if chroot is accessible
echo "1. Checking chroot access..."
if [ -d "$CHROOT" ]; then
    echo "✓ Chroot exists"
    # Check if we can access it
    if sudo ls "$CHROOT" >/dev/null 2>&1; then
        echo "✓ Chroot accessible with sudo"
    else
        echo "✗ Cannot access chroot with sudo"
    fi
else
    echo "✗ Chroot not found at $CHROOT"
    exit 1
fi

# Check current kernel situation
echo
echo "2. Current kernel situation:"
echo "Installed kernels:"
sudo chroot "$CHROOT" dpkg -l 2>/dev/null | grep '^ii.*linux-image' | awk '{print "  - " $2}' || echo "  ✗ Cannot list kernels"

# Check apt sources
echo
echo "3. APT sources (first line):"
sudo head -1 "$CHROOT/etc/apt/sources.list" 2>/dev/null || echo "  ✗ Cannot read sources.list"

# Check for dpkg locks
echo
echo "4. Checking for lock files:"
LOCKS=$(sudo find "$CHROOT/var/lib/dpkg" "$CHROOT/var/cache/apt" -name "*lock*" 2>/dev/null | wc -l)
if [ "$LOCKS" -gt 0 ]; then
    echo "  ✗ Found $LOCKS lock files"
else
    echo "  ✓ No lock files found"
fi

# Check dpkg status
echo
echo "5. DPKG status:"
if sudo chroot "$CHROOT" dpkg --audit >/dev/null 2>&1; then
    echo "  ✓ DPKG database is clean"
else
    echo "  ✗ DPKG database has issues"
    echo "  First few issues:"
    sudo chroot "$CHROOT" dpkg --audit 2>&1 | head -5
fi

# Check if apt-get update works
echo
echo "6. Testing apt-get update:"
if sudo chroot "$CHROOT" apt-get update >/dev/null 2>&1; then
    echo "  ✓ apt-get update works"
else
    echo "  ✗ apt-get update fails"
fi

# Check available 6.12 kernels
echo
echo "7. Available 6.12 kernels:"
KERNELS=$(sudo chroot "$CHROOT" apt-cache search "^linux-image-6.12" 2>/dev/null | wc -l)
if [ "$KERNELS" -gt 0 ]; then
    echo "  ✓ Found $KERNELS kernel(s) available"
    sudo chroot "$CHROOT" apt-cache search "^linux-image-6.12" 2>/dev/null | head -3 | awk '{print "    - " $1}'
else
    echo "  ✗ No 6.12 kernels found"
fi

echo
echo "=== End Diagnosis ==="