#!/bin/bash
# Build ZFS .deb packages specifically for the live CD
# Creates packages that can be installed in the chroot

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "        Build ZFS .deb Packages for Live CD"
echo "═══════════════════════════════════════════════════════════════════"

ZFS_VERSION="2.3.3"
BUILD_DIR="/tmp/zfs_deb_build_$$"
OUTPUT_DIR="/opt/github/Z-FORGE/live_cd_packages"

# Create directories
mkdir -p "$BUILD_DIR" "$OUTPUT_DIR"

echo ""
echo "[1/8] Installing build dependencies..."
echo "Run this command:"
echo "sudo apt-get update && sudo apt-get install -y build-essential autoconf automake libtool gawk alien fakeroot dkms libblkid-dev uuid-dev libudev-dev libssl-dev zlib1g-dev libaio-dev libattr1-dev libelf-dev linux-headers-\$(uname -r) python3 python3-dev python3-setuptools python3-cffi libffi-dev debhelper dh-python po-debconf python3-all-dev python3-sphinx"

echo ""
echo "[2/8] Downloading ZFS source..."
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
echo "[3/8] Configuring for .deb package creation..."
./configure \
    --enable-systemd \
    --enable-pyzfs \
    --with-config=all

echo ""
echo "[4/8] Building .deb packages (this takes time)..."
echo "Run this command:"
echo "cd $BUILD_DIR/zfs-${ZFS_VERSION} && make -j\$(nproc) deb-utils deb-kmod"

echo ""
echo "[5/8] After build completes, copy packages..."
echo "cd $BUILD_DIR/zfs-${ZFS_VERSION}"
echo "cp *.deb $OUTPUT_DIR/"

# Create installation script for the packages
cat > "$OUTPUT_DIR/install_zfs_debs_in_chroot.sh" << 'EOFINSTALL'
#!/bin/bash
# Install ZFS .deb packages in chroot for live CD

set -e

CHROOT_PATH="${1:-/tmp/zforge_workspace/chroot}"
PACKAGE_DIR="$(dirname "$0")"

if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    exit 1
fi

echo "Installing ZFS .deb packages in chroot..."

# Mount filesystems
for fs in proc sys dev dev/pts; do
    if ! mountpoint -q "$CHROOT_PATH/$fs" 2>/dev/null; then
        mkdir -p "$CHROOT_PATH/$fs"
        mount --bind "/$fs" "$CHROOT_PATH/$fs"
    fi
done

# Copy packages to chroot
mkdir -p "$CHROOT_PATH/tmp/zfs_debs"
cp "$PACKAGE_DIR"/*.deb "$CHROOT_PATH/tmp/zfs_debs/" 2>/dev/null || true

# Install in chroot
chroot "$CHROOT_PATH" bash -c '
cd /tmp/zfs_debs

echo "Installing ZFS kernel module packages..."
dpkg -i *-dkms_*.deb || true
dpkg -i *kmod*.deb || true

echo "Installing ZFS utilities..."
dpkg -i zfsutils-linux_*.deb || true
dpkg -i libnvpair*.deb || true
dpkg -i libuutil*.deb || true
dpkg -i libzfs*.deb || true
dpkg -i libzpool*.deb || true

echo "Installing remaining packages..."
dpkg -i *.deb || true

# Configure packages
dpkg --configure -a || true

# Load ZFS module if possible
modprobe zfs || echo "ZFS module not loaded (normal in chroot)"
'

echo "ZFS packages installed in chroot!"
echo "Packages available for live CD."
EOFINSTALL

chmod +x "$OUTPUT_DIR/install_zfs_debs_in_chroot.sh"

echo ""
echo "[6/8] Creating package verification script..."
cat > "$OUTPUT_DIR/verify_zfs_packages.sh" << 'EOFVERIFY'
#!/bin/bash
# Verify ZFS packages are ready for live CD

PACKAGE_DIR="$(dirname "$0")"
cd "$PACKAGE_DIR"

echo "ZFS .deb packages for live CD:"
echo "=============================="

if ls *.deb >/dev/null 2>&1; then
    for deb in *.deb; do
        echo "✅ $deb ($(du -h "$deb" | cut -f1))"
    done
    
    echo ""
    echo "Total packages: $(ls *.deb | wc -l)"
    echo "Total size: $(du -sh *.deb | tail -1 | cut -f1)"
    echo ""
    echo "To install in chroot:"
    echo "  sudo ./install_zfs_debs_in_chroot.sh"
else
    echo "❌ No .deb packages found"
    echo ""
    echo "Build packages with:"
    echo "  cd $BUILD_DIR/zfs-${ZFS_VERSION}"
    echo "  make -j\$(nproc) deb-utils deb-kmod"
    echo "  cp *.deb $OUTPUT_DIR/"
fi
EOFVERIFY

chmod +x "$OUTPUT_DIR/verify_zfs_packages.sh"

echo ""
echo "[7/8] Creating quick build script..."
cat > "$OUTPUT_DIR/quick_build_zfs_debs.sh" << 'EOFQUICK'
#!/bin/bash
# Quick build of ZFS .deb packages

set -e

BUILD_DIR="/tmp/zfs_deb_build_$$"
ZFS_VERSION="2.3.3"

echo "Building ZFS .deb packages..."

# Use existing source if available
if [ -f "/opt/github/Z-FORGE/prebuilt_packages/zfs-2.3.3.tar.gz" ]; then
    mkdir -p "$BUILD_DIR"
    cd "$BUILD_DIR"
    cp "/opt/github/Z-FORGE/prebuilt_packages/zfs-2.3.3.tar.gz" .
    tar xzf "zfs-${ZFS_VERSION}.tar.gz"
    cd "zfs-${ZFS_VERSION}"
    
    echo "Configuring..."
    ./configure --enable-systemd --enable-pyzfs --with-config=all
    
    echo "Building packages..."
    make -j$(nproc) deb-utils deb-kmod
    
    echo "Copying packages..."
    cp *.deb "$(dirname "$0")/"
    
    echo "Build complete!"
    echo "Packages available in: $(dirname "$0")"
else
    echo "ERROR: ZFS source not found"
    echo "Download first or use the main build script"
fi
EOFQUICK

chmod +x "$OUTPUT_DIR/quick_build_zfs_debs.sh"

echo ""
echo "[8/8] Summary and next steps..."
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                    Setup Complete"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "Package directory: $OUTPUT_DIR"
echo "Build directory: $BUILD_DIR"
echo ""
echo "To build the .deb packages:"
echo "1. Install dependencies (see command above)"
echo "2. cd $BUILD_DIR/zfs-${ZFS_VERSION}"
echo "3. make -j\$(nproc) deb-utils deb-kmod"
echo "4. cp *.deb $OUTPUT_DIR/"
echo ""
echo "Or use the quick build:"
echo "  cd $OUTPUT_DIR && ./quick_build_zfs_debs.sh"
echo ""
echo "To verify packages:"
echo "  $OUTPUT_DIR/verify_zfs_packages.sh"
echo ""
echo "To install in live CD chroot:"
echo "  sudo $OUTPUT_DIR/install_zfs_debs_in_chroot.sh"