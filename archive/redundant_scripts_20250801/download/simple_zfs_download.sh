#!/bin/bash
# Simple ZFS package download

set -e

cd /opt/github/Z-FORGE/prebuilt_packages

echo "📦 Downloading ZFS packages..."

# Base URL
BASE="http://deb.debian.org/debian/pool/contrib/z/zfs-linux"

# Download each package
PACKAGES=(
    "zfsutils-linux_2.2.2-4~bpo12+1_amd64.deb"
    "zfs-zed_2.2.2-4~bpo12+1_amd64.deb"
    "zfs-test_2.2.2-4~bpo12+1_amd64.deb"
    "zfs-initramfs_2.2.2-4~bpo12+1_all.deb"
    "zfs-dracut_2.2.2-4~bpo12+1_all.deb"
    "zfs-dkms_2.2.2-4~bpo12+1_all.deb"
    "libnvpair3linux_2.2.2-4~bpo12+1_amd64.deb"
    "libuutil3linux_2.2.2-4~bpo12+1_amd64.deb"
    "libzfs4linux_2.2.2-4~bpo12+1_amd64.deb"
    "libzpool5linux_2.2.2-4~bpo12+1_amd64.deb"
    "python3-pyzfs_2.2.2-4~bpo12+1_amd64.deb"
)

for pkg in "${PACKAGES[@]}"; do
    if [ -f "$pkg" ] && [ $(stat -c%s "$pkg" 2>/dev/null || echo 0) -gt 1000 ]; then
        echo "✅ $pkg already exists"
    else
        echo -n "Downloading $pkg... "
        rm -f "$pkg" 2>/dev/null || true
        if wget -q "$BASE/$pkg" && [ -f "$pkg" ]; then
            echo "✅"
        else
            echo "❌"
        fi
    fi
done

echo ""
echo "📊 Downloaded packages:"
ls -lh *.deb 2>/dev/null | grep -v "^total"
echo ""
echo "Total: $(ls -1 *.deb 2>/dev/null | wc -l) packages"