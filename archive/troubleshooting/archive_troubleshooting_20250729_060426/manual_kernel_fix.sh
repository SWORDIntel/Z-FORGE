#!/bin/bash
# Manual kernel fix based on log analysis

echo "🔧 Manual Kernel Fix - Targeting Specific Package"
echo "Based on log analysis, the issue is version naming mismatch"
echo

CHROOT="/tmp/zforge_workspace/chroot"

# The exact kernel we want (from the log)
TARGET_KERNEL="linux-image-6.12.38+deb13-amd64"
TARGET_HEADERS="linux-headers-6.12.38+deb13-amd64"

echo "Target kernel: $TARGET_KERNEL"
echo "Target headers: $TARGET_HEADERS"
echo

# Step 1: Remove metapackages that might be causing conflicts
echo "Step 1: Removing metapackages..."
sudo chroot "$CHROOT" apt-get remove -y linux-image-amd64 linux-headers-amd64 2>/dev/null || true

# Step 2: Install the exact packages
echo "Step 2: Installing exact kernel packages..."
if sudo chroot "$CHROOT" apt-get install -y --no-install-recommends \
    "$TARGET_KERNEL" \
    "$TARGET_HEADERS" \
    build-essential \
    dkms; then
    echo "✅ SUCCESS: Installed $TARGET_KERNEL"
else
    echo "❌ Failed to install specific kernel, trying alternatives..."
    
    # Try just the kernel without headers
    if sudo chroot "$CHROOT" apt-get install -y --no-install-recommends "$TARGET_KERNEL"; then
        echo "✅ Kernel installed, trying headers separately..."
        sudo chroot "$CHROOT" apt-get install -y "$TARGET_HEADERS" || echo "⚠️ Headers failed but kernel is installed"
    else
        echo "❌ Even basic kernel installation failed"
        exit 1
    fi
fi

# Step 3: Reinstall metapackages
echo "Step 3: Reinstalling metapackages for future updates..."
sudo chroot "$CHROOT" apt-get install -y linux-image-amd64 linux-headers-amd64 || true

# Step 4: Verify
echo "Step 4: Final verification..."
echo "Installed kernels:"
sudo chroot "$CHROOT" dpkg -l | grep '^ii.*linux-image' | grep -v dbg

if sudo chroot "$CHROOT" dpkg -l | grep -q '^ii.*linux-image-6\.12'; then
    echo
    echo "🎉 SUCCESS: Kernel 6.12+ is now installed!"
else
    echo
    echo "❌ FAILED: No 6.12+ kernel found"
    exit 1
fi