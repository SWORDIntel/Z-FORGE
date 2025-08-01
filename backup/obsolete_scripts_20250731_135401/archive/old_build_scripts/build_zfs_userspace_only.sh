#!/bin/bash
# Build ZFS 2.3.3 userspace tools only (no kernel modules)
# This avoids kernel dependency issues

set -e

SUDO_PASS="1786"

# Create build script
cat > /tmp/zfs_userspace_build.sh << 'BUILDSCRIPT'
#!/bin/bash
set -e

ZFS_VERSION="2.3.3"
BUILD_DIR="/tmp/zfs-userspace-build"
OUTPUT_DIR="/opt/github/Z-FORGE/prebuilt_packages"

echo "=== Building ZFS ${ZFS_VERSION} Userspace Tools ==="

# Clean build directory
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Download ZFS source
echo "Downloading ZFS source..."
wget -q https://github.com/openzfs/zfs/releases/download/zfs-${ZFS_VERSION}/zfs-${ZFS_VERSION}.tar.gz
tar -xzf zfs-${ZFS_VERSION}.tar.gz
cd zfs-${ZFS_VERSION}

# Install minimal dependencies
echo "Installing dependencies..."
apt-get update -qq
apt-get install -y -qq \
    build-essential \
    autoconf \
    automake \
    libtool \
    gawk \
    libblkid-dev \
    uuid-dev \
    libudev-dev \
    libssl-dev \
    zlib1g-dev \
    libaio-dev \
    libattr1-dev \
    libelf-dev \
    python3-dev \
    python3-setuptools \
    python3-cffi \
    libffi-dev

# Run autogen
echo "Running autogen..."
./autogen.sh

# Configure for userspace only
echo "Configuring (userspace only)..."
./configure \
    --prefix=/usr \
    --sysconfdir=/etc \
    --localstatedir=/var \
    --with-config=user \
    --enable-systemd \
    --enable-pyzfs

# Build
echo "Building..."
make -j$(nproc)

# Create simple packages
echo "Creating packages..."
mkdir -p "$OUTPUT_DIR"

# Package the binaries
echo "Packaging binaries..."
make install DESTDIR="$BUILD_DIR/install"

# Create a tarball
cd "$BUILD_DIR/install"
tar -czf "$OUTPUT_DIR/zfs-userspace-${ZFS_VERSION}.tar.gz" .

# Create extraction script
cat > "$OUTPUT_DIR/install_zfs_userspace.sh" << 'EOF'
#!/bin/bash
# Install ZFS userspace tools

set -e

CHROOT_PATH="${1:-/tmp/zforge_workspace/chroot}"
SCRIPT_DIR="$(dirname "$0")"

echo "Installing ZFS userspace tools to $CHROOT_PATH"

# Extract files
tar -xzf "$SCRIPT_DIR/zfs-userspace-*.tar.gz" -C "$CHROOT_PATH"

# Update library cache
chroot "$CHROOT_PATH" ldconfig

echo "ZFS userspace tools installed!"
EOF
chmod +x "$OUTPUT_DIR/install_zfs_userspace.sh"

echo ""
echo "✅ Build complete!"
echo "📦 Package: $OUTPUT_DIR/zfs-userspace-${ZFS_VERSION}.tar.gz"
echo "🔧 Installer: $OUTPUT_DIR/install_zfs_userspace.sh"

# Clean up
cd /
rm -rf "$BUILD_DIR"
BUILDSCRIPT

chmod +x /tmp/zfs_userspace_build.sh

# Run with sudo
echo "Building ZFS userspace tools..."
echo "$SUDO_PASS" | sudo -S /tmp/zfs_userspace_build.sh

rm -f /tmp/zfs_userspace_build.sh