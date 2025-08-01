#!/bin/bash
# Build ZFS 2.3.3 Userspace Only (No Kernel Modules)
# This avoids the CONFIG_MODULES issue entirely

set -e

ZFS_VERSION="2.3.3"
BUILD_DIR="/usr/src"
PACKAGE_DIR="/opt/github/Z-FORGE/prebuilt_packages"
ZFS_SOURCE_DIR="${BUILD_DIR}/zfs-${ZFS_VERSION}"

echo "═══════════════════════════════════════════════════════════════════"
echo "         Building ZFS ${ZFS_VERSION} USERSPACE ONLY"
echo "         (Avoids CONFIG_MODULES kernel issue)"
echo "═══════════════════════════════════════════════════════════════════"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    exit 1
fi

# Create package directory
mkdir -p "${PACKAGE_DIR}"

# Clean previous attempts
echo "[1/7] Cleaning previous build attempts..."
cd "${BUILD_DIR}"
if [ -d "${ZFS_SOURCE_DIR}" ]; then
    rm -rf "${ZFS_SOURCE_DIR}"
fi

# Download source if not cached
ZFS_TARBALL="zfs-${ZFS_VERSION}.tar.gz"
if [ ! -f "${BUILD_DIR}/${ZFS_TARBALL}" ]; then
    echo "[2/7] Downloading ZFS ${ZFS_VERSION} source..."
    wget -c "https://github.com/openzfs/zfs/releases/download/zfs-${ZFS_VERSION}/${ZFS_TARBALL}"
else
    echo "[2/7] Using cached ZFS source..."
fi

# Extract source
echo "[3/7] Extracting ZFS source..."
tar -xzf "${ZFS_TARBALL}"
cd "${ZFS_SOURCE_DIR}"

# Install minimal build dependencies (no kernel headers)
echo "[4/7] Installing userspace build dependencies..."
apt-get update
apt-get install -y \
    build-essential autoconf automake libtool gawk \
    zlib1g-dev uuid-dev libattr1-dev libblkid-dev \
    libssl-dev libaio-dev libelf-dev python3-dev \
    python3-setuptools python3-cffi libffi-dev

# Configure for userspace only (no kernel modules)
echo "[5/7] Configuring ZFS userspace build..."
./autogen.sh
./configure \
    --prefix=/usr \
    --sysconfdir=/etc \
    --sbindir=/sbin \
    --libdir=/usr/lib/x86_64-linux-gnu \
    --with-config=user \
    --enable-systemd \
    --enable-pyzfs \
    --with-systemdunitdir=/lib/systemd/system \
    --disable-static

# Build userspace tools only
echo "[6/7] Building ZFS userspace tools..."
make -j$(nproc)

# Create package structure
echo "[7/7] Creating userspace package..."
TEMP_INSTALL="/tmp/zfs-${ZFS_VERSION}-userspace"
mkdir -p "${TEMP_INSTALL}"

# Install to temporary location
make install DESTDIR="${TEMP_INSTALL}"

# Create tar.gz package
cd "${TEMP_INSTALL}"
tar -czf "${PACKAGE_DIR}/zfs-${ZFS_VERSION}-userspace.tar.gz" .

# Create installer script
cat > "${PACKAGE_DIR}/install_zfs_2_3_3.sh" << 'EOF'
#!/bin/bash
# ZFS 2.3.3 Userspace installer for Z-FORGE

CHROOT_PATH="$1"
if [ -z "$CHROOT_PATH" ]; then
    echo "Usage: $0 <chroot_path>"
    exit 1
fi

echo "Installing ZFS 2.3.3 userspace tools to chroot: $CHROOT_PATH"

# Extract package to chroot
cd "$CHROOT_PATH"
tar -xzf /opt/github/Z-FORGE/prebuilt_packages/zfs-2.3.3-userspace.tar.gz

# Install Python modules in chroot
chroot "$CHROOT_PATH" python3 -m pip install pyzfs || true

# Note: No kernel modules - will use host ZFS modules or install separately
echo "✅ ZFS 2.3.3 userspace tools installation complete"
echo "⚠️  Note: This is userspace only - kernel modules handled separately"
EOF

chmod +x "${PACKAGE_DIR}/install_zfs_2_3_3.sh"

# Clean up
rm -rf "${TEMP_INSTALL}"

# Verify
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                    USERSPACE BUILD COMPLETE"
echo "═══════════════════════════════════════════════════════════════════"
echo "✅ ZFS ${ZFS_VERSION} userspace package created:"
echo "   📦 ${PACKAGE_DIR}/zfs-${ZFS_VERSION}-userspace.tar.gz"
echo "   🔧 ${PACKAGE_DIR}/install_zfs_2_3_3.sh"
echo ""
echo "Package size: $(du -h "${PACKAGE_DIR}/zfs-${ZFS_VERSION}-userspace.tar.gz" | cut -f1)"
echo ""
echo "⚠️  IMPORTANT: This build includes:"
echo "   ✅ ZFS userspace tools (zfs, zpool, zdb, etc.)"
echo "   ✅ Python bindings (pyzfs)"
echo "   ✅ systemd service files"
echo "   ❌ NO kernel modules (avoids CONFIG_MODULES issue)"
echo ""
echo "For kernel modules, use pre-built packages or host installation."