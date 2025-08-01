#!/bin/bash
# Build ZFS 2.3.3 for Z-FORGE Makefile System
# This script builds ZFS 2.3.3 and creates packages for the build system

set -e

ZFS_VERSION="2.3.3"
BUILD_DIR="/usr/src"
PACKAGE_DIR="/opt/github/Z-FORGE/prebuilt_packages"
ZFS_SOURCE_DIR="${BUILD_DIR}/zfs-${ZFS_VERSION}"

echo "═══════════════════════════════════════════════════════════════════"
echo "           Building ZFS ${ZFS_VERSION} for Z-FORGE Makefile"
echo "═══════════════════════════════════════════════════════════════════"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    exit 1
fi

# Create package directory
mkdir -p "${PACKAGE_DIR}"

# Clean previous attempts
echo "[1/8] Cleaning previous build attempts..."
cd "${BUILD_DIR}"
if [ -d "${ZFS_SOURCE_DIR}" ]; then
    rm -rf "${ZFS_SOURCE_DIR}"
fi

# Download source if not cached
ZFS_TARBALL="zfs-${ZFS_VERSION}.tar.gz"
if [ ! -f "${BUILD_DIR}/${ZFS_TARBALL}" ]; then
    echo "[2/8] Downloading ZFS ${ZFS_VERSION} source..."
    wget -c "https://github.com/openzfs/zfs/releases/download/zfs-${ZFS_VERSION}/${ZFS_TARBALL}"
else
    echo "[2/8] Using cached ZFS source..."
fi

# Extract source
echo "[3/8] Extracting ZFS source..."
tar -xzf "${ZFS_TARBALL}"
cd "${ZFS_SOURCE_DIR}"

# Install build dependencies
echo "[4/8] Installing build dependencies..."
apt-get update
apt-get install -y \
    build-essential autoconf automake libtool gawk \
    zlib1g-dev uuid-dev libattr1-dev libblkid-dev \
    libssl-dev libaio-dev libelf-dev python3-dev \
    python3-setuptools python3-cffi libffi-dev \
    dkms linux-headers-$(uname -r)

# Configure build
echo "[5/8] Configuring ZFS build..."
./autogen.sh
./configure \
    --prefix=/usr \
    --sysconfdir=/etc \
    --sbindir=/sbin \
    --libdir=/usr/lib/x86_64-linux-gnu \
    --with-config=all \
    --enable-systemd \
    --enable-pyzfs \
    --with-systemdunitdir=/lib/systemd/system \
    --with-dracutdir=/usr/lib/dracut \
    --disable-static

# Build
echo "[6/8] Building ZFS (this may take 10-15 minutes)..."
make -j$(nproc)

# Create package structure
echo "[7/8] Creating package structure..."
TEMP_INSTALL="/tmp/zfs-${ZFS_VERSION}-install"
mkdir -p "${TEMP_INSTALL}"

# Install to temporary location
make install DESTDIR="${TEMP_INSTALL}"

# Create tar.gz package
echo "[8/8] Creating package..."
cd "${TEMP_INSTALL}"
tar -czf "${PACKAGE_DIR}/zfs-${ZFS_VERSION}-complete.tar.gz" .

# Create installer script
cat > "${PACKAGE_DIR}/install_zfs_${ZFS_VERSION//./_}.sh" << 'EOF'
#!/bin/bash
# ZFS 2.3.3 installer for Z-FORGE

CHROOT_PATH="$1"
if [ -z "$CHROOT_PATH" ]; then
    echo "Usage: $0 <chroot_path>"
    exit 1
fi

echo "Installing ZFS 2.3.3 to chroot: $CHROOT_PATH"

# Extract package to chroot
cd "$CHROOT_PATH"
tar -xzf /opt/github/Z-FORGE/prebuilt_packages/zfs-2.3.3-complete.tar.gz

# Install Python modules in chroot
chroot "$CHROOT_PATH" python3 -m pip install pyzfs || true

# Enable services
chroot "$CHROOT_PATH" systemctl enable zfs-import-cache zfs-mount zfs-share zfs-zed || true

echo "ZFS 2.3.3 installation complete"
EOF

chmod +x "${PACKAGE_DIR}/install_zfs_${ZFS_VERSION//./_}.sh"

# Clean up
rm -rf "${TEMP_INSTALL}"

# Verify
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                           VERIFICATION"
echo "═══════════════════════════════════════════════════════════════════"
echo "✅ ZFS ${ZFS_VERSION} package created:"
echo "   📦 ${PACKAGE_DIR}/zfs-${ZFS_VERSION}-complete.tar.gz"
echo "   🔧 ${PACKAGE_DIR}/install_zfs_${ZFS_VERSION//./_}.sh"
echo ""
echo "Package size: $(du -h "${PACKAGE_DIR}/zfs-${ZFS_VERSION}-complete.tar.gz" | cut -f1)"
echo ""
echo "To use with Makefile system:"
echo "  make deps"
echo "  make build"
echo ""
echo "The build system will automatically detect and use this package."