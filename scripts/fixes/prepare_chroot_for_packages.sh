#!/bin/bash
# Prepare chroot environment for package installation

set -euo pipefail

WORKSPACE="${ZFORGE_WORKSPACE:-/home/john/zforge_workspace}"
CHROOT_PATH="$WORKSPACE/chroot"

if [ ! -d "$CHROOT_PATH" ]; then
    echo "❌ ERROR: Chroot not found at $CHROOT_PATH"
    exit 1
fi

echo "=== Preparing Chroot for Package Installation ==="

# Function to safely mount
safe_mount() {
    local type=$1
    local source=$2
    local target=$3
    
    if ! mountpoint -q "$target" 2>/dev/null; then
        echo "  Mounting $target..."
        mount $type "$source" "$target"
    else
        echo "  $target already mounted"
    fi
}

# 1. Mount all required filesystems
echo "Mounting filesystems..."
safe_mount "-t proc" "proc" "$CHROOT_PATH/proc"
safe_mount "-t sysfs" "sysfs" "$CHROOT_PATH/sys"
safe_mount "-o bind" "/dev" "$CHROOT_PATH/dev"
safe_mount "-t devpts" "devpts" "$CHROOT_PATH/dev/pts"

# 2. Set up network
echo ""
echo "Setting up network..."
cp /etc/resolv.conf "$CHROOT_PATH/etc/resolv.conf"

# 3. Create diversion for initramfs in chroot
echo ""
echo "Setting up dpkg diversions for chroot..."
# Divert update-initramfs to avoid errors in chroot
chroot "$CHROOT_PATH" dpkg-divert --local --rename --add /usr/sbin/update-initramfs
cat > "$CHROOT_PATH/usr/sbin/update-initramfs" << 'EOF'
#!/bin/sh
# Dummy update-initramfs for chroot environment
echo "update-initramfs: Disabled in chroot environment"
exit 0
EOF
chmod +x "$CHROOT_PATH/usr/sbin/update-initramfs"

# 4. Install essential packages first
echo ""
echo "Installing essential packages..."
chroot "$CHROOT_PATH" apt-get update

# Install in specific order to avoid dependency issues
ESSENTIAL_PACKAGES=(
    "kmod"                    # Provides depmod
    "busybox"                # Basic utilities
    "initramfs-tools-core"   # Core initramfs without triggers
)

for pkg in "${ESSENTIAL_PACKAGES[@]}"; do
    echo "  Installing $pkg..."
    chroot "$CHROOT_PATH" apt-get install -y --no-install-recommends "$pkg" || echo "  ⚠️  $pkg failed (continuing)"
done

# 5. Create minimal kernel module directory structure
echo ""
echo "Creating kernel module structure..."
KERNEL_VERSION=$(chroot "$CHROOT_PATH" ls /lib/modules/ 2>/dev/null | head -1)
if [ -z "$KERNEL_VERSION" ]; then
    # Create a dummy kernel version directory
    KERNEL_VERSION="6.12.38+deb13-amd64"
    echo "  Creating dummy module directory for $KERNEL_VERSION..."
    mkdir -p "$CHROOT_PATH/lib/modules/$KERNEL_VERSION"
    touch "$CHROOT_PATH/lib/modules/$KERNEL_VERSION/modules.builtin"
    touch "$CHROOT_PATH/lib/modules/$KERNEL_VERSION/modules.order"
fi

# 6. Run depmod to create module dependencies
echo ""
echo "Generating module dependencies..."
chroot "$CHROOT_PATH" depmod -a "$KERNEL_VERSION" 2>/dev/null || echo "  ⚠️  depmod warnings (OK for chroot)"

# 7. Remove diversion after package installation
cleanup_diversion() {
    echo ""
    echo "Cleaning up diversions..."
    rm -f "$CHROOT_PATH/usr/sbin/update-initramfs"
    chroot "$CHROOT_PATH" dpkg-divert --local --rename --remove /usr/sbin/update-initramfs
}

# Set trap to clean up on exit
trap cleanup_diversion EXIT

echo ""
echo "=== Chroot Prepared ==="
echo ""
echo "The chroot is now ready for package installation."
echo "Initramfs generation has been disabled to avoid errors."
echo ""
echo "To install packages in the chroot:"
echo "  chroot $CHROOT_PATH apt-get install -y <package>"
echo ""
echo "When the build is complete, run:"
echo "  $0 --cleanup"
echo ""

# Handle cleanup argument
if [ "${1:-}" = "--cleanup" ]; then
    cleanup_diversion
    
    # Unmount filesystems
    echo "Unmounting filesystems..."
    umount "$CHROOT_PATH/dev/pts" 2>/dev/null || true
    umount "$CHROOT_PATH/dev" 2>/dev/null || true
    umount "$CHROOT_PATH/sys" 2>/dev/null || true
    umount "$CHROOT_PATH/proc" 2>/dev/null || true
    
    echo "✅ Cleanup complete"
fi