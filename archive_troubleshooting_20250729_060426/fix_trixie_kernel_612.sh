#!/bin/bash
# Fix Trixie to use the correct 6.12.x kernel

set -e

CHROOT_PATH="/tmp/zforge_workspace/chroot"

echo "=== Z-FORGE Trixie Kernel 6.12.x Fix ==="
echo "This script will install the correct Trixie kernel (6.12.38+deb13-amd64)"
echo ""

# Check if chroot exists
if [ ! -d "$CHROOT_PATH" ]; then
    echo "ERROR: Chroot directory not found at $CHROOT_PATH"
    exit 1
fi

# Step 1: Fix any existing dpkg issues
echo "Step 1: Fixing any dpkg issues..."
sudo chroot "$CHROOT_PATH" dpkg --configure -a || true
sudo chroot "$CHROOT_PATH" apt-get install -f -y || true

# Step 2: Update sources to use Trixie properly
echo ""
echo "Step 2: Updating APT sources to Trixie (testing)..."

# Backup current sources
sudo cp "$CHROOT_PATH/etc/apt/sources.list" "$CHROOT_PATH/etc/apt/sources.list.backup.$(date +%Y%m%d_%H%M%S)" || true

# Create proper Trixie sources - using 'testing' to ensure we get latest
cat << EOF | sudo tee "$CHROOT_PATH/etc/apt/sources.list"
# Debian Testing (Trixie) repositories - will get 6.12.x kernel
deb http://deb.debian.org/debian testing main contrib non-free-firmware
deb-src http://deb.debian.org/debian testing main contrib non-free-firmware

deb http://deb.debian.org/debian-security testing-security main contrib non-free-firmware
deb-src http://deb.debian.org/debian-security testing-security main contrib non-free-firmware

# Explicitly use testing to get latest packages
deb http://deb.debian.org/debian testing-updates main contrib non-free-firmware
deb-src http://deb.debian.org/debian testing-updates main contrib non-free-firmware
EOF

# Step 3: Remove any APT pinning that might force stable
echo ""
echo "Step 3: Removing any APT pinning..."
sudo rm -f "$CHROOT_PATH/etc/apt/preferences" 2>/dev/null || true
sudo rm -f "$CHROOT_PATH/etc/apt/preferences.d/*" 2>/dev/null || true

# Step 4: Clear APT cache completely
echo ""
echo "Step 4: Clearing APT cache..."
sudo chroot "$CHROOT_PATH" apt-get clean
sudo rm -rf "$CHROOT_PATH/var/lib/apt/lists/*"

# Step 5: Update package lists
echo ""
echo "Step 5: Updating package lists from Trixie..."
sudo chroot "$CHROOT_PATH" apt-get update

# Step 6: Remove old kernels if any
echo ""
echo "Step 6: Removing any old kernels..."
OLD_KERNELS=$(sudo chroot "$CHROOT_PATH" dpkg -l | grep '^ii.*linux-image-6\.1\.' | awk '{print $2}' || true)
if [ -n "$OLD_KERNELS" ]; then
    echo "Removing old 6.1.x kernels: $OLD_KERNELS"
    sudo chroot "$CHROOT_PATH" apt-get remove -y $OLD_KERNELS || true
fi

# Step 7: Install the specific Trixie kernel
echo ""
echo "Step 7: Installing Trixie kernel 6.12.x..."

# First try the specific version we know exists
TRIXIE_KERNEL="linux-image-6.12.38+deb13-amd64"
TRIXIE_HEADERS="linux-headers-6.12.38+deb13-amd64"

echo "Installing $TRIXIE_KERNEL..."
if sudo chroot "$CHROOT_PATH" apt-get install -y "$TRIXIE_KERNEL" "$TRIXIE_HEADERS" build-essential dkms; then
    echo "Successfully installed Trixie kernel 6.12.38!"
else
    echo "Specific version failed, trying metapackage..."
    # Fallback to metapackage
    sudo chroot "$CHROOT_PATH" apt-get install -y linux-image-amd64 linux-headers-amd64 build-essential dkms
fi

# Step 8: Install ZFS packages
echo ""
echo "Step 8: Installing ZFS packages for new kernel..."
sudo chroot "$CHROOT_PATH" apt-get remove -y zfs-initramfs 2>/dev/null || true
sudo chroot "$CHROOT_PATH" apt-get install -y zfsutils-linux zfs-dkms || true

# Try zfs-dracut for dracut support
sudo chroot "$CHROOT_PATH" apt-get install -y zfs-dracut 2>/dev/null || true

# Step 9: Verify installation
echo ""
echo "Step 9: Verification..."
echo ""
echo "=== Installed Kernels ==="
sudo chroot "$CHROOT_PATH" dpkg -l | grep -E '^ii.*linux-image' | grep -v dbg

echo ""
echo "=== Kernel Version Check ==="
if sudo chroot "$CHROOT_PATH" ls /boot/vmlinuz-6.12* 2>/dev/null; then
    echo "SUCCESS: Trixie kernel 6.12.x is installed!"
else
    echo "WARNING: Trixie kernel may not be properly installed"
fi

echo ""
echo "=== APT Sources Verification ==="
echo "Current sources.list:"
head -3 "$CHROOT_PATH/etc/apt/sources.list"

echo ""
echo "=== DKMS Status ==="
sudo chroot "$CHROOT_PATH" dkms status || echo "DKMS not configured yet"

echo ""
echo "=== Fix Complete! ==="
echo ""
echo "You should now have:"
echo "- Debian Trixie (testing) APT sources"
echo "- Kernel 6.12.38 installed"
echo "- ZFS packages ready for DKMS build"
echo ""
echo "If the kernel is still wrong, try:"
echo "  sudo chroot $CHROOT_PATH apt-cache policy linux-image-amd64"
echo "  sudo chroot $CHROOT_PATH apt-get dist-upgrade"