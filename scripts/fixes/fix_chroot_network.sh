#!/bin/bash
# Fix Z-FORGE chroot network connectivity

set -e

CHROOT_PATH="/tmp/zforge_workspace/chroot"

echo "=== Fixing Z-FORGE Chroot Network Connectivity ==="

# Check if chroot exists
if [ ! -d "$CHROOT_PATH" ]; then
    echo "Error: Chroot directory not found at $CHROOT_PATH"
    exit 1
fi

echo "1. Copying host resolv.conf to chroot..."
sudo cp /etc/resolv.conf "$CHROOT_PATH/etc/resolv.conf"
echo "   ✓ DNS configuration copied"

echo "2. Ensuring /proc, /sys, /dev are mounted in chroot..."
# Mount proc if not already mounted
if ! mountpoint -q "$CHROOT_PATH/proc"; then
    sudo mount -t proc proc "$CHROOT_PATH/proc"
    echo "   ✓ /proc mounted"
else
    echo "   ✓ /proc already mounted"
fi

# Mount sys if not already mounted  
if ! mountpoint -q "$CHROOT_PATH/sys"; then
    sudo mount -t sysfs sysfs "$CHROOT_PATH/sys"
    echo "   ✓ /sys mounted"
else
    echo "   ✓ /sys already mounted"
fi

# Mount dev if not already mounted
if ! mountpoint -q "$CHROOT_PATH/dev"; then
    sudo mount --bind /dev "$CHROOT_PATH/dev"
    echo "   ✓ /dev bind mounted"
else
    echo "   ✓ /dev already mounted"
fi

# Mount dev/pts if not already mounted
if ! mountpoint -q "$CHROOT_PATH/dev/pts"; then
    sudo mount -t devpts devpts "$CHROOT_PATH/dev/pts"
    echo "   ✓ /dev/pts mounted"
else
    echo "   ✓ /dev/pts already mounted"
fi

echo "3. Testing network connectivity in chroot..."
if sudo chroot "$CHROOT_PATH" ping -c 1 8.8.8.8 &>/dev/null; then
    echo "   ✓ Network connectivity working"
else
    echo "   ⚠ Network test failed - checking DNS..."
fi

echo "4. Testing DNS resolution in chroot..."
if sudo chroot "$CHROOT_PATH" nslookup deb.debian.org &>/dev/null; then
    echo "   ✓ DNS resolution working"
else
    echo "   ⚠ DNS resolution failed - trying to fix..."
    
    # Create a more robust resolv.conf
    echo "nameserver 9.9.9.9" | sudo tee "$CHROOT_PATH/etc/resolv.conf" > /dev/null
    echo "nameserver 8.8.8.8" | sudo tee -a "$CHROOT_PATH/etc/resolv.conf" > /dev/null
    echo "nameserver 1.1.1.1" | sudo tee -a "$CHROOT_PATH/etc/resolv.conf" > /dev/null
    echo "   ✓ Fallback DNS servers configured"
    
    # Test again
    if sudo chroot "$CHROOT_PATH" nslookup deb.debian.org &>/dev/null; then
        echo "   ✓ DNS resolution now working"
    else
        echo "   ✗ DNS resolution still failing"
    fi
fi

echo "5. Verifying APT can reach repositories..."
if sudo chroot "$CHROOT_PATH" apt-get update -qq &>/dev/null; then
    echo "   ✓ APT repositories accessible"
else
    echo "   ⚠ APT update failed - trying with --fix-missing..."
    sudo chroot "$CHROOT_PATH" apt-get update --fix-missing || echo "   ✗ APT update still failing"
fi

echo
echo "=== Network Fix Complete ==="
echo "You can now resume the build with:"
echo "sudo python3 builder/z-forge.py --build-spec build_spec.yml --resume"