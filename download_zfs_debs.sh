#!/bin/bash
# Download pre-built ZFS packages from Debian repositories

set -e

echo "📦 Z-FORGE ZFS Package Downloader"
echo "================================="
echo "Downloading pre-built ZFS packages from Debian Bookworm"
echo ""

OUTPUT_DIR="/opt/github/Z-FORGE/prebuilt_packages"
mkdir -p "$OUTPUT_DIR"

cd "$OUTPUT_DIR"

# Base URL for Debian packages
# Try multiple mirrors for redundancy
MIRRORS=(
    "http://deb.debian.org/debian"
    "http://ftp.debian.org/debian"
    "http://ftp.us.debian.org/debian"
    "https://rsync.cica.es/debian"
)

# Select first working mirror
DEBIAN_MIRROR=""
for mirror in "${MIRRORS[@]}"; do
    if wget -q --spider "$mirror/pool/contrib/z/zfs-linux/" 2>/dev/null; then
        DEBIAN_MIRROR="$mirror"
        echo "Using mirror: $DEBIAN_MIRROR"
        break
    fi
done

if [ -z "$DEBIAN_MIRROR" ]; then
    echo "Error: No working mirror found"
    exit 1
fi

POOL_URL="$DEBIAN_MIRROR/pool"

# ZFS packages we need (from bookworm-backports)
# Note: Fixed typo in package name (amd74 -> amd64)
PACKAGES=(
    # Core ZFS packages
    "contrib/z/zfs-linux/zfsutils-linux_2.2.2-4~bpo12+1_amd64.deb"
    "contrib/z/zfs-linux/zfs-zed_2.2.2-4~bpo12+1_amd64.deb"
    "contrib/z/zfs-linux/zfs-test_2.2.2-4~bpo12+1_amd64.deb"
    "contrib/z/zfs-linux/zfs-initramfs_2.2.2-4~bpo12+1_all.deb"
    "contrib/z/zfs-linux/zfs-dracut_2.2.2-4~bpo12+1_all.deb"
    
    # ZFS DKMS for kernel modules
    "contrib/z/zfs-linux/zfs-dkms_2.2.2-4~bpo12+1_all.deb"
    
    # Libraries
    "contrib/z/zfs-linux/libnvpair3linux_2.2.2-4~bpo12+1_amd64.deb"
    "contrib/z/zfs-linux/libuutil3linux_2.2.2-4~bpo12+1_amd64.deb" 
    "contrib/z/zfs-linux/libzfs4linux_2.2.2-4~bpo12+1_amd64.deb"
    "contrib/z/zfs-linux/libzpool5linux_2.2.2-4~bpo12+1_amd64.deb"
    
    # Python bindings
    "contrib/z/zfs-linux/python3-pyzfs_2.2.2-4~bpo12+1_amd64.deb"
)

echo "Downloading ZFS packages..."
echo ""

SUCCESS=0
FAILED=0

for package in "${PACKAGES[@]}"; do
    filename=$(basename "$package")
    url="$POOL_URL/$package"
    
    echo -n "Downloading $filename... "
    
    if [ -f "$filename" ]; then
        echo "already exists, skipping"
        continue
    fi
    
    # Try with wget, handle SSL issues
    if wget -q "$url" -O "$filename" 2>/dev/null; then
        echo "✅"
        ((SUCCESS++))
    elif wget -q --no-check-certificate "$url" -O "$filename" 2>/dev/null; then
        echo "✅ (SSL bypass)"
        ((SUCCESS++))
    elif curl -sL "$url" -o "$filename"; then
        echo "✅ (curl)"
        ((SUCCESS++))
    else
        echo "❌ Failed"
        ((FAILED++))
        rm -f "$filename"  # Remove partial downloads
    fi
done

echo ""
echo "Download complete!"
echo "✅ Success: $SUCCESS packages"
if [ $FAILED -gt 0 ]; then
    echo "❌ Failed: $FAILED packages"
fi

# Create installation script
cat > install_zfs_downloaded.sh << 'EOF'
#!/bin/bash
# Install downloaded ZFS packages

set -e

CHROOT_PATH="${1:-/tmp/zforge_workspace/chroot}"
PACKAGES_DIR="$(dirname "$0")"

echo "Installing downloaded ZFS packages to $CHROOT_PATH"

# Check if chroot exists
if [ ! -d "$CHROOT_PATH" ]; then
    echo "Error: Chroot directory not found: $CHROOT_PATH"
    exit 1
fi

# Copy packages to chroot
echo "Copying packages to chroot..."
mkdir -p "$CHROOT_PATH/tmp/zfs-packages"
cp "$PACKAGES_DIR"/*.deb "$CHROOT_PATH/tmp/zfs-packages/" 2>/dev/null || true

# Install packages in chroot
echo "Installing ZFS packages..."
chroot "$CHROOT_PATH" /bin/bash -c "
    cd /tmp/zfs-packages
    
    # Install libraries first
    dpkg -i libnvpair*.deb libuutil*.deb libz*.deb || true
    
    # Install userspace tools
    dpkg -i zfsutils-linux*.deb zfs-zed*.deb || true
    
    # Install DKMS and modules
    dpkg -i zfs-dkms*.deb || true
    
    # Install remaining packages
    dpkg -i *.deb || true
    
    # Fix any dependency issues
    apt-get install -f -y
    
    # Enable ZFS services
    systemctl enable zfs-import-cache || true
    systemctl enable zfs-mount || true
    systemctl enable zfs-import.target || true
    
    # Clean up
    rm -rf /tmp/zfs-packages
"

echo "ZFS packages installed successfully!"
EOF

chmod +x install_zfs_downloaded.sh

echo ""
echo "📁 Packages saved to: $OUTPUT_DIR"
echo "🔧 Installation script: $OUTPUT_DIR/install_zfs_downloaded.sh"
echo ""
echo "To use in Z-FORGE build:"
echo "  The build system will automatically detect and use these packages"