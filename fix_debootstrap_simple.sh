#!/bin/bash
# Simple Z-FORGE debootstrap fix with alternative approach

set -e

WORKSPACE="/tmp/zforge_workspace"
CHROOT_PATH="$WORKSPACE/chroot"

echo "=== Simple Debootstrap Fix ==="

# Clean up completely
echo "1. Complete cleanup..."
if [ -d "$CHROOT_PATH" ]; then
    sudo umount "$CHROOT_PATH"/{dev/pts,dev,sys,proc} 2>/dev/null || true
    sudo rm -rf "$CHROOT_PATH"
fi
sudo mkdir -p "$WORKSPACE"

# Check disk space
echo "2. Checking disk space..."
available=$(df /tmp | tail -1 | awk '{print int($4/1024/1024)}')
echo "Available: ${available}GB"
if [ "$available" -lt 8 ]; then
    echo "Error: Need at least 8GB free space"
    exit 1
fi

# Try minimal debootstrap first
echo "3. Running minimal debootstrap..."
if sudo debootstrap \
    --arch=amd64 \
    --variant=minbase \
    --include="locales,sudo,bash-completion,ca-certificates,curl,wget" \
    trixie \
    "$CHROOT_PATH" \
    http://deb.debian.org/debian; then
    
    echo "✓ Minimal debootstrap successful"
    
    # Now add additional packages inside chroot
    echo "4. Installing additional packages..."
    
    # Copy DNS config
    sudo cp /etc/resolv.conf "$CHROOT_PATH/etc/resolv.conf"
    
    # Mount necessary filesystems
    sudo mount -t proc proc "$CHROOT_PATH/proc"
    sudo mount -t sysfs sysfs "$CHROOT_PATH/sys"
    sudo mount --bind /dev "$CHROOT_PATH/dev"
    sudo mount -t devpts devpts "$CHROOT_PATH/dev/pts"
    
    # Update and install additional packages
    sudo chroot "$CHROOT_PATH" apt-get update
    sudo chroot "$CHROOT_PATH" apt-get install -y \
        linux-base \
        apt-transport-https \
        gnupg \
        gpgv
    
    echo "✓ Additional packages installed"
    
    # Unmount for clean state
    sudo umount "$CHROOT_PATH"/{dev/pts,dev,sys,proc}
    
    echo "✓ Debootstrap completed successfully"
    echo "Ready to run Z-FORGE build"
    
else
    echo "✗ Debootstrap failed"
    
    # Try alternative mirror
    echo "5. Trying alternative mirror..."
    sudo rm -rf "$CHROOT_PATH"
    
    if sudo debootstrap \
        --arch=amd64 \
        --variant=minbase \
        --include="locales,sudo,bash-completion" \
        trixie \
        "$CHROOT_PATH" \
        http://mirror.us.leaseweb.net/debian/; then
        
        echo "✓ Alternative mirror successful"
    else
        echo "✗ All attempts failed"
        echo "Try running: sudo apt-get update && sudo apt-get install debootstrap"
        exit 1
    fi
fi

echo
echo "=== Success ==="
echo "Run: sudo python3 builder/z-forge.py --build-spec build_spec.yml"