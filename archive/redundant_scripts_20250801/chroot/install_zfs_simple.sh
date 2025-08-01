#!/bin/bash
# Simple ZFS installation script - no complex operations
set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "        Simple ZFS Package Installation"
echo "═══════════════════════════════════════════════════════════════════"

# Configuration - Use original user's HOME, not root's
ORIGINAL_USER=${SUDO_USER:-$(logname 2>/dev/null || echo $USER)}
ORIGINAL_HOME=$(eval echo "~$ORIGINAL_USER" 2>/dev/null || echo "$HOME")
CHROOT_PATH="$ORIGINAL_HOME/zforge_workspace/chroot"
ZFS_PACKAGE="/opt/github/Z-FORGE/live_cd_packages/zfsutils-userspace_2.3.3-1_amd64.deb"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    exit 1
fi

# Check if ZFS package exists
if [ ! -f "$ZFS_PACKAGE" ]; then
    echo "ERROR: ZFS package not found at: $ZFS_PACKAGE"
    exit 1
fi

# Check if chroot exists
if [ ! -d "$CHROOT_PATH" ]; then
    echo "ERROR: Chroot not found at: $CHROOT_PATH"
    echo "Run: sudo ./bootstrap_chroot.sh"
    exit 1
fi

echo "Original user: $ORIGINAL_USER"
echo "Chroot path: $CHROOT_PATH"
echo "ZFS package: $ZFS_PACKAGE"
echo ""

# Copy ZFS package to chroot
echo "Step 1: Copying ZFS package to chroot..."
cp "$ZFS_PACKAGE" "$CHROOT_PATH/tmp/"

# Install using chroot
echo "Step 2: Installing ZFS package in chroot..."
echo "1786" | sudo -S ./use_arch_chroot.sh "$CHROOT_PATH" /bin/bash -c "cd /tmp && dpkg -i $(basename $ZFS_PACKAGE) || apt-get install -f -y"

echo ""
echo "Step 3: Verifying installation..."
echo "1786" | sudo -S ./use_arch_chroot.sh "$CHROOT_PATH" /bin/bash -c "dpkg -l | grep zfs"

echo ""
echo "✅ ZFS package installation complete!"
echo ""
echo "Next steps:"
echo "1. Run build: make -f Makefile.no_tmp build"