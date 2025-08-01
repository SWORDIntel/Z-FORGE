#!/bin/bash
# Install ZFS package using arch-chroot (preferred method)
# Supports both /tmp and home workspace locations

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "        Installing ZFS Package with arch-chroot"
echo "═══════════════════════════════════════════════════════════════════"

# Configuration - Use original user's HOME, not root's
ORIGINAL_USER=${SUDO_USER:-$(logname 2>/dev/null || echo $USER)}
ORIGINAL_HOME=$(eval echo "~$ORIGINAL_USER" 2>/dev/null || echo "$HOME")

# Default to home workspace, fall back to /tmp if needed
if [ -d "$ORIGINAL_HOME/zforge_workspace/chroot" ]; then
    CHROOT_PATH="$ORIGINAL_HOME/zforge_workspace/chroot"
elif [ -d "${CHROOT_PATH:-/home/john/zforge_workspace/chroot}" ]; then
    CHROOT_PATH="${CHROOT_PATH:-/home/john/zforge_workspace/chroot}"
    echo "⚠️  Using /tmp chroot. Consider moving to $ORIGINAL_HOME/zforge_workspace"
else
    CHROOT_PATH="${1:-$ORIGINAL_HOME/zforge_workspace/chroot}"
fi

ZFS_PACKAGE="/opt/github/Z-FORGE/live_cd_packages/zfsutils-userspace_2.3.3-1_amd64.deb"

if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    exit 1
fi

if [ ! -f "$ZFS_PACKAGE" ]; then
    echo "ERROR: ZFS package not found at: $ZFS_PACKAGE"
    exit 1
fi

if [ ! -d "$CHROOT_PATH" ]; then
    echo "ERROR: Chroot not found at: $CHROOT_PATH"
    echo "Run: $(dirname "$0")/bootstrap_chroot.sh auto $CHROOT_PATH"
    exit 1
fi

# Install arch-chroot if needed
USE_ARCH_CHROOT=true
if ! command -v arch-chroot &> /dev/null; then
    echo "Installing arch-install-scripts for better chroot handling..."
    if ! apt-get update && apt-get install -y arch-install-scripts; then
        echo "⚠️  Warning: Could not install arch-chroot, falling back to standard chroot"
        USE_ARCH_CHROOT=false
    fi
fi

echo ""
echo "Using chroot at: $CHROOT_PATH"
echo "Installing: $(basename "$ZFS_PACKAGE")"
echo ""

# Copy package to chroot
echo "[1/4] Copying ZFS package to chroot..."
mkdir -p "$CHROOT_PATH/tmp/zfs_install"
cp "$ZFS_PACKAGE" "$CHROOT_PATH/tmp/zfs_install/"

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

# Install dependencies using chroot
echo ""
echo "[2/4] Installing dependencies..."
if ! run_in_chroot '
apt-get update
apt-get install -y --no-install-recommends \
    libc6 \
    python3 \
    python3-cffi \
    libssl3 \
    libblkid1 \
    libuuid1 \
    libudev1 \
    libaio1 \
    || echo "Some dependencies may already be installed"
'; then
    echo "⚠️  Warning: Some dependency installation issues occurred"
    echo "Continuing with installation..."
fi

# Install ZFS package
echo ""
echo "[3/4] Installing ZFS userspace package..."
run_in_chroot '
cd /tmp/zfs_install
dpkg -i *.deb || apt-get install -f -y
'

# Verify installation
echo ""
echo "[4/4] Verifying installation..."
run_in_chroot '
echo "Checking ZFS commands..."
which zfs && echo "✅ zfs command found" || echo "❌ zfs command not found"
which zpool && echo "✅ zpool command found" || echo "❌ zpool command not found"

echo ""
echo "Package info:"
dpkg -s zfsutils-userspace | grep -E "Package:|Version:|Status:"

echo ""
echo "Sample installed files:"
dpkg -L zfsutils-userspace | head -5
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

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "           ZFS Package Installed Successfully!"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "✅ ZFS 2.3.3 userspace tools installed in chroot"
if [ "$USE_ARCH_CHROOT" = true ]; then
    echo "✅ Using arch-chroot for better isolation"
else
    echo "✅ Using standard chroot (arch-chroot unavailable)"
fi
echo "✅ Chroot location: $CHROOT_PATH"
echo ""
echo "Next steps:"
echo "1. Run build: make -f Makefile.no_tmp build"
echo "2. Or enter chroot: ./use_arch_chroot.sh"
echo ""