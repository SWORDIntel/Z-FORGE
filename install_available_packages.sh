#!/bin/bash
# Install whatever packages we have downloaded into the chroot

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "          Installing Available Downloaded Packages"
echo "═══════════════════════════════════════════════════════════════════"

CHROOT_PATH="${1:-/tmp/zforge_workspace/chroot}"

if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    exit 1
fi

# Find all .deb files we've downloaded
echo "[1/4] Finding downloaded packages..."
PACKAGE_DIRS=(
    "/opt/github/Z-FORGE/snapshot_packages_working"
    "/opt/github/Z-FORGE/snapshot_packages_fixed"
    "/opt/github/Z-FORGE/snapshot_packages"
    "/opt/github/Z-FORGE/essential_debs"
    "/opt/github/Z-FORGE/apt_downloaded_packages"
)

TEMP_DIR="/tmp/all_debs_$$"
mkdir -p "$TEMP_DIR"

FOUND=0
for dir in "${PACKAGE_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "Checking $dir..."
        for deb in "$dir"/*.deb; do
            if [ -f "$deb" ]; then
                cp "$deb" "$TEMP_DIR/" 2>/dev/null || true
                ((FOUND++))
            fi
        done
    fi
done

echo "Found $FOUND .deb files"

if [ $FOUND -eq 0 ]; then
    echo "ERROR: No .deb files found to install"
    exit 1
fi

echo ""
echo "[2/4] Preparing chroot environment..."

# Create essential directories
mkdir -p "$CHROOT_PATH"/{bin,sbin,usr/bin,usr/sbin,lib,lib64,etc,proc,sys,dev,tmp,var/lib/dpkg}

# Create dpkg status file if missing
touch "$CHROOT_PATH/var/lib/dpkg/status"

# Copy packages to chroot
echo "[3/4] Copying packages to chroot..."
mkdir -p "$CHROOT_PATH/tmp/manual_debs"
cp "$TEMP_DIR"/*.deb "$CHROOT_PATH/tmp/manual_debs/"

# Mount filesystems
echo "Mounting filesystems..."
for fs in proc sys dev dev/pts; do
    if ! mountpoint -q "$CHROOT_PATH/$fs" 2>/dev/null; then
        mkdir -p "$CHROOT_PATH/$fs"
        mount --bind "/$fs" "$CHROOT_PATH/$fs" || true
    fi
done

echo ""
echo "[4/4] Installing packages..."

# Install packages
chroot "$CHROOT_PATH" bash -c '
cd /tmp/manual_debs

echo "Available packages:"
ls -1 *.deb

echo ""
echo "Installing packages..."

# Force install all packages
for deb in *.deb; do
    echo -n "Installing $deb... "
    if dpkg --force-depends --force-confnew -i "$deb" 2>/dev/null; then
        echo "✅"
    else
        echo "❌"
    fi
done

# Try to configure
echo ""
echo "Configuring packages..."
dpkg --configure -a 2>/dev/null || true
'

# Clean up
rm -rf "$TEMP_DIR"

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                    Installation Complete"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "Packages have been installed in: $CHROOT_PATH"
echo ""
echo "Next steps:"
echo "1. Run 'make build' to continue the build process"
echo "2. Check logs/zforge_build_*.log for any errors"