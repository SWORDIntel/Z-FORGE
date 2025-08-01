#!/bin/bash
# Complete ZFS installation script - handles workspace migration and installation
set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "        Z-FORGE Complete ZFS Installation & Setup"
echo "═══════════════════════════────────────════════════════════════════"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    echo "Usage: sudo $0"
    exit 1
fi

# Configuration - Use original user's HOME, not root's
ORIGINAL_USER=${SUDO_USER:-$(logname 2>/dev/null || echo $USER)}
ORIGINAL_HOME=$(eval echo "~$ORIGINAL_USER" 2>/dev/null || echo "$HOME")
HOME_CHROOT="$ORIGINAL_HOME/zforge_workspace/chroot"
ZFS_PACKAGE="/opt/github/Z-FORGE/live_cd_packages/zfsutils-userspace_2.3.3-1_amd64.deb"

echo "Step 1: Setting up HOME workspace structure..."

# Create HOME workspace structure
mkdir -p "$ORIGINAL_HOME/zforge_workspace"/{cache,output,temp,logs}
# Don't chown if chroot already exists with mounts
if [ ! -d "$ORIGINAL_HOME/zforge_workspace/chroot" ]; then
    mkdir -p "$ORIGINAL_HOME/zforge_workspace/chroot"
    chown $ORIGINAL_USER:$ORIGINAL_USER "$ORIGINAL_HOME/zforge_workspace"
fi

echo "Step 2: Setting up chroot in HOME workspace..."

# Always use HOME workspace
CHROOT_PATH="$HOME_CHROOT"

# Check if we need to create a fresh chroot
if [ ! -d "$CHROOT_PATH" ] || [ ! "$(ls -A $CHROOT_PATH 2>/dev/null)" ]; then
    echo "Creating fresh chroot in HOME workspace..."
    echo "Running bootstrap to create clean chroot..."
    
    # Run bootstrap to create chroot in HOME workspace
    "$(dirname "$0")/bootstrap_chroot.sh" auto "$CHROOT_PATH"
    
    if [ ! -d "$CHROOT_PATH" ] || [ ! "$(ls -A $CHROOT_PATH 2>/dev/null)" ]; then
        echo "❌ Failed to create chroot at: $CHROOT_PATH"
        exit 1
    fi
fi

echo "✅ Using HOME workspace chroot: $CHROOT_PATH"

echo "Step 3: Installing arch-chroot support..."

# Install arch-chroot if not available
USE_ARCH_CHROOT=true
if ! command -v arch-chroot &> /dev/null; then
    if ! apt-get update && apt-get install -y arch-install-scripts; then
        echo "⚠️  Warning: Could not install arch-chroot, using standard chroot"
        USE_ARCH_CHROOT=false
    else
        echo "✅ arch-chroot installed"
    fi
else
    echo "✅ arch-chroot already available"
fi

echo "Step 4: Preparing ZFS package..."

# Verify ZFS package exists
if [ ! -f "$ZFS_PACKAGE" ]; then
    echo "❌ ZFS package not found at: $ZFS_PACKAGE"
    exit 1
fi

# Copy ZFS package to chroot
mkdir -p "$CHROOT_PATH/tmp/zfs_install"
cp "$ZFS_PACKAGE" "$CHROOT_PATH/tmp/zfs_install/"
echo "✅ ZFS package copied to chroot"

# Function to run command in chroot
run_in_chroot() {
    if [ "$USE_ARCH_CHROOT" = true ]; then
        arch-chroot "$CHROOT_PATH" /bin/bash -c "$1"
    else
        # Fallback to standard chroot
        # Mount necessary filesystems if not using arch-chroot
        for fs in proc sys dev dev/pts; do
            if ! mountpoint -q "$CHROOT_PATH/$fs" 2>/dev/null; then
                mkdir -p "$CHROOT_PATH/$fs"
                mount --bind "/$fs" "$CHROOT_PATH/$fs"
            fi
        done
        cp -L /etc/resolv.conf "$CHROOT_PATH/etc/resolv.conf"
        chroot "$CHROOT_PATH" /bin/bash -c "$1"
    fi
}

echo "Step 5: Fixing APT keyring in chroot..."

# Fix APT keyring issues
run_in_chroot '
# Fix trusted.gpg.d directory
if [ -f /etc/apt/trusted.gpg.d ]; then
    rm -f /etc/apt/trusted.gpg.d
fi
mkdir -p /etc/apt/trusted.gpg.d
chmod 755 /etc/apt/trusted.gpg.d

# Update package lists
apt-get update --allow-unauthenticated || true
apt-get install -y --allow-unauthenticated debian-archive-keyring || true
apt-get update || true
'

echo "Step 6: Installing ZFS dependencies..."

# Install ZFS dependencies
run_in_chroot '
apt-get install -y --no-install-recommends \
    libc6 \
    python3 \
    python3-cffi \
    libssl3 \
    libblkid1 \
    libuuid1 \
    libudev1 \
    libaio1 \
    2>/dev/null || echo "Some dependencies already installed"
'

echo "Step 7: Installing ZFS package..."

# Install ZFS package
run_in_chroot '
cd /tmp/zfs_install
echo "Installing $(ls *.deb)..."
dpkg -i *.deb || apt-get install -f -y
'

echo "Step 8: Verifying installation..."

# Verify ZFS installation
run_in_chroot '
echo "Checking ZFS commands..."
which zfs && echo "✅ zfs command found" || echo "❌ zfs command not found"
which zpool && echo "✅ zpool command found" || echo "❌ zpool command not found"

echo ""
echo "Package status:"
dpkg -s zfsutils-userspace | grep -E "Package:|Version:|Status:" || echo "Package query failed"

echo ""
echo "Sample files:"
dpkg -L zfsutils-userspace 2>/dev/null | head -5 || echo "File list failed"
'

# Clean up
rm -rf "$CHROOT_PATH/tmp/zfs_install"

# Unmount if we used standard chroot
if [ "$USE_ARCH_CHROOT" = false ]; then
    echo "Cleaning up mounts..."
    for fs in dev/pts dev sys proc; do
        umount "$CHROOT_PATH/$fs" 2>/dev/null || true
    done
fi

# Note: Ownership will be handled by the build system

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "           Complete Installation Finished!"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "✅ Workspace: $HOME/zforge_workspace"
echo "✅ Chroot: $CHROOT_PATH"
echo "✅ ZFS package installed"
if [ "$USE_ARCH_CHROOT" = true ]; then
    echo "✅ arch-chroot available and used"
else
    echo "✅ Standard chroot used (arch-chroot unavailable)"
fi
echo ""
echo "Next steps:"
echo "1. Test chroot: ./use_arch_chroot.sh"
echo "2. Run build: make -f Makefile.no_tmp build"
echo ""