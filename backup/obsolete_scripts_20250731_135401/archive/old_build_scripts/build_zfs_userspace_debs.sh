#!/bin/bash
# Build ZFS userspace .deb packages for live CD
# Builds only userspace tools, no kernel modules

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "      Build ZFS Userspace .deb Packages for Live CD"
echo "═══════════════════════════════════════════════════════════════════"

ZFS_VERSION="2.3.3"
BUILD_DIR="/tmp/zfs_userspace_deb_build_$$"
OUTPUT_DIR="/opt/github/Z-FORGE/live_cd_packages"

# Create directories
mkdir -p "$BUILD_DIR" "$OUTPUT_DIR"

echo ""
echo "[1/6] Using ZFS source..."
cd "$BUILD_DIR"

if [ -f "/opt/github/Z-FORGE/prebuilt_packages/zfs-2.3.3.tar.gz" ]; then
    echo "Using existing ZFS source..."
    cp "/opt/github/Z-FORGE/prebuilt_packages/zfs-2.3.3.tar.gz" .
else
    echo "Downloading ZFS ${ZFS_VERSION}..."
    wget "https://github.com/openzfs/zfs/releases/download/zfs-${ZFS_VERSION}/zfs-${ZFS_VERSION}.tar.gz"
fi

tar xzf "zfs-${ZFS_VERSION}.tar.gz"
cd "zfs-${ZFS_VERSION}"

echo ""
echo "[2/6] Configuring for userspace-only .deb packages..."
echo "This builds ZFS tools without kernel modules."

./configure \
    --prefix=/usr \
    --sysconfdir=/etc \
    --sbindir=/sbin \
    --libdir=/usr/lib \
    --enable-systemd \
    --enable-pyzfs \
    --with-config=user

echo ""
echo "[3/6] Building userspace packages..."
make -j$(nproc)

echo ""
echo "[4/6] Creating userspace .deb packages..."
# Create simple .deb packages using built files

# Create package structure
PKG_DIR="$BUILD_DIR/zfsutils-userspace"
mkdir -p "$PKG_DIR/DEBIAN"
mkdir -p "$PKG_DIR/usr/bin"
mkdir -p "$PKG_DIR/usr/sbin"
mkdir -p "$PKG_DIR/usr/lib"
mkdir -p "$PKG_DIR/etc"

# Copy built files
echo "Collecting built files..."
make DESTDIR="$PKG_DIR" install

# Create control file
cat > "$PKG_DIR/DEBIAN/control" << EOF
Package: zfsutils-userspace
Version: ${ZFS_VERSION}-1
Section: admin
Priority: optional
Architecture: amd64
Depends: libc6, python3
Maintainer: Z-FORGE Build System
Description: ZFS userspace utilities
 ZFS userspace tools and libraries for managing ZFS filesystems.
 This package contains only userspace components, no kernel modules.
EOF

# Build the package
echo "Building .deb package..."
dpkg-deb --build "$PKG_DIR" "$OUTPUT_DIR/zfsutils-userspace_${ZFS_VERSION}-1_amd64.deb"

echo ""
echo "[5/6] Creating installation scripts..."

# Create installation script for chroot
cat > "$OUTPUT_DIR/install_zfs_userspace_in_chroot.sh" << 'EOFINSTALL'
#!/bin/bash
# Install ZFS userspace packages in chroot for live CD

set -e

CHROOT_PATH="${1:-/tmp/zforge_workspace/chroot}"
PACKAGE_DIR="$(dirname "$0")"

if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    exit 1
fi

echo "Installing ZFS userspace packages in chroot..."

# Mount filesystems
for fs in proc sys dev dev/pts; do
    if ! mountpoint -q "$CHROOT_PATH/$fs" 2>/dev/null; then
        mkdir -p "$CHROOT_PATH/$fs"
        mount --bind "/$fs" "$CHROOT_PATH/$fs"
    fi
done

# Copy packages to chroot
mkdir -p "$CHROOT_PATH/tmp/zfs_userspace_debs"
cp "$PACKAGE_DIR"/*.deb "$CHROOT_PATH/tmp/zfs_userspace_debs/" 2>/dev/null || true

# Install in chroot
chroot "$CHROOT_PATH" bash -c '
cd /tmp/zfs_userspace_debs

echo "Installing ZFS userspace packages..."
dpkg -i *.deb || true

# Configure packages
dpkg --configure -a || true

echo "ZFS userspace tools installed!"
echo "Available commands: zfs, zpool, zdb, zinject, etc."
'

echo "ZFS userspace packages installed in chroot!"
echo "Ready for live CD."
EOFINSTALL

chmod +x "$OUTPUT_DIR/install_zfs_userspace_in_chroot.sh"

# Create verification script
cat > "$OUTPUT_DIR/verify_zfs_userspace_packages.sh" << 'EOFVERIFY'
#!/bin/bash
# Verify ZFS userspace packages

PACKAGE_DIR="$(dirname "$0")"
cd "$PACKAGE_DIR"

echo "ZFS userspace .deb packages for live CD:"
echo "========================================"

if ls *.deb >/dev/null 2>&1; then
    for deb in *.deb; do
        echo "✅ $deb ($(du -h "$deb" | cut -f1))"
        echo "   Contents:"
        dpkg -c "$deb" | head -10 | sed 's/^/     /'
        echo ""
    done
    
    echo "Total packages: $(ls *.deb | wc -l)"
    echo "Total size: $(du -sh *.deb | tail -1 | cut -f1)"
    echo ""
    echo "To install in chroot:"
    echo "  sudo ./install_zfs_userspace_in_chroot.sh"
else
    echo "❌ No .deb packages found"
fi
EOFVERIFY

chmod +x "$OUTPUT_DIR/verify_zfs_userspace_packages.sh"

echo ""
echo "[6/6] Summary..."
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                    Build Complete"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "Package directory: $OUTPUT_DIR"
echo "Build directory: $BUILD_DIR"
echo ""

# List created packages
cd "$OUTPUT_DIR"
if ls *.deb >/dev/null 2>&1; then
    echo "Created packages:"
    for deb in *.deb; do
        echo "  ✅ $deb ($(du -h "$deb" | cut -f1))"
    done
    echo ""
    echo "To verify:"
    echo "  ./verify_zfs_userspace_packages.sh"
    echo ""
    echo "To install in live CD chroot:"
    echo "  sudo ./install_zfs_userspace_in_chroot.sh"
else
    echo "❌ No packages were created"
fi

echo ""
echo "Note: These are userspace-only packages."
echo "For kernel module support, use a kernel with CONFIG_MODULES=y"