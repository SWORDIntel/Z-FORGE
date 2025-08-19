#!/bin/bash
# Quick download of all ZFS packages from Debian Bookworm

set -e

OUTPUT_DIR="/opt/github/Z-FORGE/prebuilt_packages"
cd "$OUTPUT_DIR"

# Base URL
MIRROR="http://deb.debian.org/debian"
POOL_URL="$MIRROR/pool"

# List of all packages we need
PACKAGES=(
    "contrib/z/zfs-linux/zfsutils-linux_2.2.2-4~bpo12+1_amd64.deb"
    "contrib/z/zfs-linux/zfs-zed_2.2.2-4~bpo12+1_amd64.deb"
    "contrib/z/zfs-linux/zfs-test_2.2.2-4~bpo12+1_amd64.deb"
    "contrib/z/zfs-linux/zfs-initramfs_2.2.2-4~bpo12+1_all.deb"
    "contrib/z/zfs-linux/zfs-dracut_2.2.2-4~bpo12+1_all.deb"
    "contrib/z/zfs-linux/zfs-dkms_2.2.2-4~bpo12+1_all.deb"
    "contrib/z/zfs-linux/libnvpair3linux_2.2.2-4~bpo12+1_amd64.deb"
    "contrib/z/zfs-linux/libuutil3linux_2.2.2-4~bpo12+1_amd64.deb"
    "contrib/z/zfs-linux/libzfs4linux_2.2.2-4~bpo12+1_amd64.deb"
    "contrib/z/zfs-linux/libzpool5linux_2.2.2-4~bpo12+1_amd64.deb"
    "contrib/z/zfs-linux/python3-pyzfs_2.2.2-4~bpo12+1_amd64.deb"
)

echo "📦 Downloading all ZFS packages..."
echo ""

SUCCESS=0
FAILED=0

for package in "${PACKAGES[@]}"; do
    filename=$(basename "$package")
    url="$POOL_URL/$package"
    
    echo -n "Downloading $filename... "
    
    # Skip if already exists and has size > 1000 bytes
    if [ -f "$filename" ] && [ $(stat -c%s "$filename") -gt 1000 ]; then
        echo "already exists (valid)"
        ((SUCCESS++))
        continue
    fi
    
    # Remove if exists but too small
    [ -f "$filename" ] && rm -f "$filename"
    
    # Try wget first
    if wget -q "$url" -O "$filename" 2>/dev/null && [ -f "$filename" ] && [ $(stat -c%s "$filename") -gt 1000 ]; then
        echo "✅ (wget)"
        ((SUCCESS++))
    # Try curl as fallback
    elif curl -sL "$url" -o "$filename" && [ -f "$filename" ] && [ $(stat -c%s "$filename") -gt 1000 ]; then
        echo "✅ (curl)"
        ((SUCCESS++))
    else
        echo "❌ Failed"
        ((FAILED++))
        rm -f "$filename"
    fi
done

echo ""
echo "Download complete!"
echo "✅ Success: $SUCCESS packages"
if [ $FAILED -gt 0 ]; then
    echo "❌ Failed: $FAILED packages"
fi

echo ""
echo "📁 Packages location: $OUTPUT_DIR"
ls -lh *.deb 2>/dev/null || echo "No .deb files found"