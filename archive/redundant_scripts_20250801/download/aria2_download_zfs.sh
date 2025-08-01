#!/bin/bash
# Download ZFS packages using aria2c for faster parallel downloads

set -e

OUTPUT_DIR="/opt/github/Z-FORGE/prebuilt_packages"
mkdir -p "$OUTPUT_DIR"

# Base URL
MIRROR="http://deb.debian.org/debian"
POOL_URL="$MIRROR/pool"

# Create a download list file for aria2
cat > "$OUTPUT_DIR/zfs_downloads.txt" << EOF
${POOL_URL}/contrib/z/zfs-linux/zfsutils-linux_2.2.2-4~bpo12+1_amd64.deb
${POOL_URL}/contrib/z/zfs-linux/zfs-zed_2.2.2-4~bpo12+1_amd64.deb
${POOL_URL}/contrib/z/zfs-linux/zfs-test_2.2.2-4~bpo12+1_amd64.deb
${POOL_URL}/contrib/z/zfs-linux/zfs-initramfs_2.2.2-4~bpo12+1_all.deb
${POOL_URL}/contrib/z/zfs-linux/zfs-dracut_2.2.2-4~bpo12+1_all.deb
${POOL_URL}/contrib/z/zfs-linux/zfs-dkms_2.2.2-4~bpo12+1_all.deb
${POOL_URL}/contrib/z/zfs-linux/libnvpair3linux_2.2.2-4~bpo12+1_amd64.deb
${POOL_URL}/contrib/z/zfs-linux/libuutil3linux_2.2.2-4~bpo12+1_amd64.deb
${POOL_URL}/contrib/z/zfs-linux/libzfs4linux_2.2.2-4~bpo12+1_amd64.deb
${POOL_URL}/contrib/z/zfs-linux/libzpool5linux_2.2.2-4~bpo12+1_amd64.deb
${POOL_URL}/contrib/z/zfs-linux/python3-pyzfs_2.2.2-4~bpo12+1_amd64.deb
EOF

echo "📦 Downloading ZFS packages with aria2c..."
echo "=================================="

# Check if aria2c is installed
if ! command -v aria2c &> /dev/null; then
    echo "Installing aria2c..."
    sudo apt-get update -qq
    sudo apt-get install -y aria2
fi

# Remove any small/corrupt files
find "$OUTPUT_DIR" -name "*.deb" -size -1000c -delete 2>/dev/null || true

# Download all files in parallel
echo "Starting parallel download..."
aria2c \
    --input-file="$OUTPUT_DIR/zfs_downloads.txt" \
    --dir="$OUTPUT_DIR" \
    --max-concurrent-downloads=5 \
    --split=5 \
    --max-connection-per-server=5 \
    --min-split-size=1M \
    --continue=true \
    --auto-file-renaming=false \
    --allow-overwrite=true \
    --console-log-level=notice \
    --summary-interval=10

# Clean up
rm -f "$OUTPUT_DIR/zfs_downloads.txt"

echo ""
echo "✅ Download complete!"
echo ""
echo "📁 Downloaded packages:"
ls -lh "$OUTPUT_DIR"/*.deb 2>/dev/null || echo "No .deb files found"

echo ""
echo "📊 Package count: $(ls -1 "$OUTPUT_DIR"/*.deb 2>/dev/null | wc -l)"

# Create install script if it doesn't exist
if [ ! -f "install_zfs_downloaded.sh" ]; then
    echo ""
    echo "Creating installation script..."
    cp /opt/github/Z-FORGE/download_zfs_debs.sh . 2>/dev/null || true
fi

echo ""
echo "To use in Z-FORGE build:"
echo "  The build system will automatically detect and use these packages"