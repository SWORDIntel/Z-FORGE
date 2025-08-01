#!/bin/bash
# Download latest available ZFS packages from Debian repositories

set -e

echo "📦 Z-FORGE ZFS Package Finder"
echo "============================="
echo "Finding and downloading latest ZFS packages"
echo ""

OUTPUT_DIR="/opt/github/Z-FORGE/prebuilt_packages"
mkdir -p "$OUTPUT_DIR"

cd "$OUTPUT_DIR"

# Function to find latest ZFS version
find_latest_zfs() {
    local mirror="$1"
    echo "Checking $mirror for ZFS packages..."
    
    # Try to list available versions
    wget -qO- "$mirror/pool/contrib/z/zfs-linux/" 2>/dev/null | \
        grep -oE 'zfsutils-linux_[0-9.]+-[^"]+_amd64\.deb' | \
        sed 's/zfsutils-linux_//' | \
        sed 's/_amd64.deb//' | \
        sort -V | tail -1
}

# Try different mirrors
MIRRORS=(
    "http://deb.debian.org/debian"
    "http://ftp.debian.org/debian"
    "http://ftp.us.debian.org/debian"
)

LATEST_VERSION=""
WORKING_MIRROR=""

for mirror in "${MIRRORS[@]}"; do
    version=$(find_latest_zfs "$mirror")
    if [ -n "$version" ]; then
        LATEST_VERSION="$version"
        WORKING_MIRROR="$mirror"
        echo "Found ZFS version: $LATEST_VERSION at $mirror"
        break
    fi
done

if [ -z "$LATEST_VERSION" ]; then
    echo "❌ Could not find ZFS packages in any mirror"
    exit 1
fi

# Construct package list based on found version
PACKAGES=(
    "zfsutils-linux_${LATEST_VERSION}_amd64.deb"
    "zfs-zed_${LATEST_VERSION}_amd64.deb"
    "zfs-test_${LATEST_VERSION}_amd64.deb"
    "libnvpair3linux_${LATEST_VERSION}_amd64.deb"
    "libuutil3linux_${LATEST_VERSION}_amd64.deb"
    "libzfs4linux_${LATEST_VERSION}_amd64.deb"
    "libzpool5linux_${LATEST_VERSION}_amd64.deb"
    "python3-pyzfs_${LATEST_VERSION}_amd64.deb"
)

# Also try to get architecture-independent packages
ARCH_ALL_PACKAGES=(
    "zfs-initramfs_${LATEST_VERSION}_all.deb"
    "zfs-dracut_${LATEST_VERSION}_all.deb"
    "zfs-dkms_${LATEST_VERSION}_all.deb"
)

echo ""
echo "Downloading ZFS $LATEST_VERSION packages..."
echo ""

SUCCESS=0
FAILED=0

# Download amd64 packages
for package in "${PACKAGES[@]}"; do
    url="$WORKING_MIRROR/pool/contrib/z/zfs-linux/$package"
    echo -n "Downloading $package... "
    
    if [ -f "$package" ]; then
        echo "already exists"
        continue
    fi
    
    if wget -q "$url" 2>/dev/null || wget -q --no-check-certificate "$url" 2>/dev/null; then
        echo "✅"
        ((SUCCESS++))
    else
        echo "❌"
        ((FAILED++))
    fi
done

# Download all packages
for package in "${ARCH_ALL_PACKAGES[@]}"; do
    url="$WORKING_MIRROR/pool/contrib/z/zfs-linux/$package"
    echo -n "Downloading $package... "
    
    if [ -f "$package" ]; then
        echo "already exists"
        continue
    fi
    
    if wget -q "$url" 2>/dev/null || wget -q --no-check-certificate "$url" 2>/dev/null; then
        echo "✅"
        ((SUCCESS++))
    else
        echo "❌"
        ((FAILED++))
    fi
done

echo ""
echo "Download complete!"
echo "✅ Success: $SUCCESS packages"
if [ $FAILED -gt 0 ]; then
    echo "⚠️  Failed: $FAILED packages (some may be optional)"
fi

# Use the same installer script
if [ ! -f "install_zfs_downloaded.sh" ]; then
    cp /opt/github/Z-FORGE/download_zfs_debs.sh .
    ./download_zfs_debs.sh >/dev/null 2>&1 || true
fi

echo ""
echo "📁 Packages saved to: $OUTPUT_DIR"
echo "🔧 ZFS version: $LATEST_VERSION"
echo ""
echo "To use in Z-FORGE build:"
echo "  The build system will automatically detect and use these packages"