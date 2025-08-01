#!/bin/bash
# Download ZFS packages from OpenZFS repository

set -e

OUTPUT_DIR="/opt/github/Z-FORGE/prebuilt_packages"
mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

echo "📦 Downloading ZFS packages from OpenZFS repository"
echo "=================================================="

# Add OpenZFS repository key
echo "Adding OpenZFS repository key..."
wget -qO openzfs-key.asc https://apt.openzfs.org/key.asc

# Get package list from OpenZFS
echo "Fetching package list..."
BASE_URL="https://apt.openzfs.org/debian-testing"

# Download Packages file to see what's available
wget -q "$BASE_URL/dists/trixie/main/binary-amd64/Packages.gz" -O Packages.gz
gunzip Packages.gz

# Extract ZFS package URLs
echo "Finding ZFS packages..."
grep -E "^Filename:|^Package:" Packages | grep -B1 -E "zfs|libnvpair|libuutil|libzfs|libzpool|pyzfs" | grep "^Filename:" | awk '{print $2}' > zfs_files.txt

# Download packages
echo ""
echo "Downloading packages..."
while read -r file; do
    filename=$(basename "$file")
    echo -n "Downloading $filename... "
    
    if [ -f "$filename" ] && [ $(stat -c%s "$filename" 2>/dev/null || echo 0) -gt 1000 ]; then
        echo "already exists"
    else
        if wget -q "$BASE_URL/$file" -O "$filename"; then
            echo "✅"
        else
            echo "❌"
        fi
    fi
done < zfs_files.txt

# Clean up
rm -f Packages zfs_files.txt openzfs-key.asc

echo ""
echo "📊 Downloaded packages:"
ls -lh *.deb 2>/dev/null | grep -v "^total"
echo ""
echo "Total: $(ls -1 *.deb 2>/dev/null | wc -l) packages"

# Create installer script
cat > install_openzfs_packages.sh << 'EOF'
#!/bin/bash
# Install OpenZFS packages

set -e

CHROOT_PATH="${1:-${CHROOT_PATH:-/home/john/zforge_workspace/chroot}}"
PACKAGES_DIR="$(dirname "$0")"

echo "Installing OpenZFS packages to $CHROOT_PATH"

# Copy packages to chroot
mkdir -p "$CHROOT_PATH/tmp/zfs-packages"
cp "$PACKAGES_DIR"/*.deb "$CHROOT_PATH/tmp/zfs-packages/" 2>/dev/null || true

# Install packages in chroot
chroot "$CHROOT_PATH" /bin/bash -c "
    cd /tmp/zfs-packages
    
    # Install in correct order
    dpkg -i libnvpair*.deb libuutil*.deb libz*.deb || true
    dpkg -i zfsutils-linux*.deb zfs-zed*.deb || true
    dpkg -i zfs-dkms*.deb zfs-initramfs*.deb || true
    dpkg -i *.deb || true
    
    # Fix dependencies
    apt-get install -f -y
    
    # Enable services
    systemctl enable zfs-import-cache || true
    systemctl enable zfs-mount || true
    
    # Clean up
    rm -rf /tmp/zfs-packages
"

echo "OpenZFS packages installed!"
EOF
chmod +x install_openzfs_packages.sh

echo ""
echo "✅ Download complete!"
echo "🔧 Installer: $OUTPUT_DIR/install_openzfs_packages.sh"