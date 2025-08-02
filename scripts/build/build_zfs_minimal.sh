#!/bin/bash
# Minimal ZFS build - no signing, no DKMS, no debian packages
# Just builds ZFS binaries and creates a simple tarball

set -e

echo "════════════════════════════════════════════════════════════════════"
echo "    Minimal ZFS 2.3.3 Build (No modules, no signing)"
echo "════════════════════════════════════════════════════════════════════"

# Simple variables
ZFS_VERSION="2.3.3"
BUILD_DIR="/tmp/zfs-minimal-build"
OUTPUT_DIR="/opt/github/Z-FORGE/prebuilt_packages"

# Clean up any previous attempts
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
mkdir -p "$OUTPUT_DIR"

cd "$BUILD_DIR"

# Download if needed
if [ ! -f "$OUTPUT_DIR/zfs-${ZFS_VERSION}.tar.gz" ]; then
    echo "Downloading ZFS source..."
    wget -q --show-progress "https://github.com/openzfs/zfs/releases/download/zfs-${ZFS_VERSION}/zfs-${ZFS_VERSION}.tar.gz"
    cp "zfs-${ZFS_VERSION}.tar.gz" "$OUTPUT_DIR/"
else
    echo "Using cached source..."
    cp "$OUTPUT_DIR/zfs-${ZFS_VERSION}.tar.gz" .
fi

# Extract
echo "Extracting..."
tar -xzf "zfs-${ZFS_VERSION}.tar.gz"
cd "zfs-${ZFS_VERSION}"

# Install minimal deps only
echo "Installing minimal dependencies..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    build-essential \
    autoconf \
    automake \
    libtool \
    libblkid-dev \
    uuid-dev \
    libudev-dev \
    libssl-dev \
    zlib1g-dev \
    libattr1-dev \
    libelf-dev

# Configure for userspace only - NO KERNEL MODULES
echo "Configuring (userspace only - no kernel modules)..."
sh autogen.sh
./configure \
    --with-config=user \
    --prefix=/usr \
    --sysconfdir=/etc \
    --localstatedir=/var \
    --disable-debug \
    --disable-systemd \
    --disable-pyzfs

# Build
echo "Building userspace tools..."
make -j$(nproc)

# Install to staging
STAGE_DIR="$BUILD_DIR/install"
rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR"

echo "Installing to staging..."
make install DESTDIR="$STAGE_DIR"

# Create tarball
cd "$STAGE_DIR"
echo "Creating tarball..."
tar -czf "$OUTPUT_DIR/zfs-userspace-${ZFS_VERSION}.tar.gz" .

# Create simple installer
cat > "$OUTPUT_DIR/install_zfs_minimal.sh" << 'EOF'
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

echo "Installing minimal ZFS userspace tools..."

# Extract
tar -xzf "$SCRIPT_DIR/zfs-userspace-*.tar.gz" -C /

# Update library cache
ldconfig

echo "Done! ZFS userspace tools installed."
echo "Note: This is userspace only - no kernel modules included."
echo "You'll need kernel modules from your distribution."
EOF

chmod +x "$OUTPUT_DIR/install_zfs_minimal.sh"

# Cleanup
cd /
rm -rf "$BUILD_DIR"

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "✅ Build Complete!"
echo "════════════════════════════════════════════════════════════════════"
echo ""
echo "Output: $OUTPUT_DIR/zfs-userspace-${ZFS_VERSION}.tar.gz"
echo "Installer: $OUTPUT_DIR/install_zfs_minimal.sh"
echo ""
echo "This build contains ZFS userspace utilities only (zfs, zpool, etc.)"
echo "No kernel modules, no DKMS, no signing issues!"
echo ""