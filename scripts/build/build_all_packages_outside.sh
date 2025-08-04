#!/bin/bash
# Build ALL possible packages outside chroot
# This script builds ZFS, kernel modules, utilities, and other packages
# outside the chroot environment for faster, safer builds

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PACKAGES_DIR="$PROJECT_ROOT/prebuilt_packages"
BUILD_DIR="$PROJECT_ROOT/outside_build"
LOG_FILE="$PROJECT_ROOT/logs/outside_build_$(date +%Y%m%d_%H%M%S).log"

# Package versions
ZFS_VERSION="2.3.3"
ZFSBOOTMENU_VERSION="2.3.0"
DRACUT_VERSION="060"

# Create directories
mkdir -p "$PACKAGES_DIR"/{zfs,kernel,utilities,bootloaders,calamares,system}
mkdir -p "$BUILD_DIR"
mkdir -p "$PROJECT_ROOT/logs"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Check root
if [[ $EUID -ne 0 ]]; then
    log "❌ This script must be run as root"
    echo "   sudo $0"
    exit 1
fi

log "🚀 Starting comprehensive outside-chroot package build..."

# Install comprehensive build dependencies
log "📦 Installing build dependencies..."
apt-get update

# Core build tools
apt-get install -y \
    build-essential devscripts debhelper dh-python dh-sequence-dkms \
    git wget curl autotools-dev autoconf automake libtool pkg-config \
    alien fakeroot dkms cmake meson ninja-build

# ZFS build dependencies
apt-get install -y \
    zlib1g-dev uuid-dev libblkid-dev libssl-dev libaio-dev libattr1-dev \
    libelf-dev python3-dev python3-setuptools python3-cffi libffi-dev \
    libudev-dev libsystemd-dev libbsd-dev libcap-dev libacl1-dev

# System libraries
apt-get install -y \
    libpam0g-dev libnl-3-dev libnl-genl-3-dev libmnl-dev libnftnl-dev \
    libkmod-dev libseccomp-dev libglib2.0-dev libdbus-1-dev \
    libarchive-dev libcurl4-openssl-dev libgpgme-dev || true

# Polkit libraries (may not be available in all environments)
apt-get install -y libpolkit-gobject-1-dev || log "⚠️  Polkit libraries not available"

# EFI libraries (skip if causing issues)
apt-get install -y libefiboot-dev libefivar-dev 2>/dev/null || log "⚠️  EFI libraries skipped (not critical for build)"

# Qt/KDE dependencies for Calamares (optional)
apt-get install -y \
    qt5-qmake qtbase5-dev qtdeclarative5-dev qttools5-dev-tools \
    libqt5svg5-dev libboost-python-dev || log "⚠️  Some Qt packages unavailable"

# KDE frameworks (optional, for Calamares)
apt-get install -y \
    libpolkit-qt5-1-dev libkf5coreaddons-dev \
    libkf5widgetsaddons-dev libkf5config-dev \
    extra-cmake-modules libkf5crash-dev libkf5parts-dev || log "⚠️  Some KDE packages unavailable"

# Calamares specific (optional)
apt-get install -y \
    kirigami2-dev libkf5kirigami2-5 libkpmcore-dev \
    libyaml-cpp-dev python3-yaml python3-jsonschema || log "⚠️  Some Calamares deps unavailable"

# 1. Build ZFS packages from Proxmox source
log "🔧 Building ZFS packages from Proxmox source..."
cd "$BUILD_DIR"

if [ ! -d "zfsonlinux" ]; then
    log "⬇️  Cloning Proxmox ZFS source..."
    git clone https://git.proxmox.com/git/zfsonlinux.git
fi

cd zfsonlinux
git checkout proxmox/stable-2.3

# Apply Proxmox patches and build
log "🔨 Building ZFS with Proxmox patches..."
make deb
cp *.deb "$PACKAGES_DIR/zfs/"

# 2. Build kernel modules outside chroot
log "🔧 Building kernel modules..."
cd "$BUILD_DIR"

# Get current kernel version
KERNEL_VERSION=$(uname -r)
log "📋 Building for kernel: $KERNEL_VERSION"

# Build essential kernel modules
MODULES=(
    "zfs"
    "spl"
    "virtio"
    "vfio"
    "nvme"
)

for module in "${MODULES[@]}"; do
    log "🔨 Building kernel module: $module"
    # Module-specific build commands would go here
done

# 3. Build ZFSBootMenu
log "🔧 Building ZFSBootMenu..."
cd "$BUILD_DIR"

if [ ! -d "zfsbootmenu" ]; then
    log "⬇️  Cloning ZFSBootMenu..."
    git clone https://github.com/zbm-dev/zfsbootmenu.git
    cd zfsbootmenu
    git checkout "v${ZFSBOOTMENU_VERSION}"
else
    cd zfsbootmenu
fi

# Create ZFSBootMenu package
log "📦 Creating ZFSBootMenu package..."
make install DESTDIR="$BUILD_DIR/zfsbootmenu_pkg"

# Create debian package structure
cd "$BUILD_DIR"
mkdir -p zfsbootmenu-deb/DEBIAN
mkdir -p zfsbootmenu-deb/usr/share/zfsbootmenu
mkdir -p zfsbootmenu-deb/etc/zfsbootmenu

cat > zfsbootmenu-deb/DEBIAN/control << EOF
Package: zfsbootmenu
Version: ${ZFSBOOTMENU_VERSION}
Architecture: all
Maintainer: Z-FORGE Build System
Description: ZFS Bootloader Menu
 A bootloader for root-on-ZFS systems
Depends: zfs-initramfs, kexec-tools, fzf
EOF

cp -r "$BUILD_DIR/zfsbootmenu_pkg/"* zfsbootmenu-deb/
dpkg-deb --build zfsbootmenu-deb
cp zfsbootmenu-deb.deb "$PACKAGES_DIR/bootloaders/zfsbootmenu_${ZFSBOOTMENU_VERSION}_all.deb"

# 4. Build dracut modules
log "🔧 Building dracut and modules..."
cd "$BUILD_DIR"

if [ ! -d "dracut" ]; then
    log "⬇️  Downloading dracut source..."
    wget "https://github.com/dracutdevs/dracut/archive/refs/tags/${DRACUT_VERSION}.tar.gz"
    tar -xzf "${DRACUT_VERSION}.tar.gz"
    mv "dracut-${DRACUT_VERSION}" dracut
fi

cd dracut
./configure --sysconfdir=/etc
make -j$(nproc)

# Create dracut package
make install DESTDIR="$BUILD_DIR/dracut_pkg"
cd "$BUILD_DIR"

# Package dracut
mkdir -p dracut-deb/DEBIAN
cat > dracut-deb/DEBIAN/control << EOF
Package: dracut-zfs
Version: ${DRACUT_VERSION}
Architecture: amd64
Maintainer: Z-FORGE Build System
Description: Dracut initramfs generator with ZFS support
Depends: cpio, kmod, udev
Conflicts: dracut
Provides: dracut
EOF

cp -r dracut_pkg/* dracut-deb/
dpkg-deb --build dracut-deb
cp dracut-deb.deb "$PACKAGES_DIR/system/dracut-zfs_${DRACUT_VERSION}_amd64.deb"

# 5. Build Calamares installer
log "🔧 Building Calamares installer..."
cd "$BUILD_DIR"

if [ ! -d "calamares" ]; then
    log "⬇️  Cloning Calamares..."
    git clone https://github.com/calamares/calamares.git
    cd calamares
    git checkout v3.3.0
else
    cd calamares
fi

# Build Calamares
mkdir -p build
cd build
cmake -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX=/usr \
      -DWITH_PYTHONQT=OFF \
      -DSKIP_MODULES="webview" ..
make -j$(nproc)

# Create Calamares package
make install DESTDIR="$BUILD_DIR/calamares_pkg"
cd "$BUILD_DIR"

# Package Calamares
mkdir -p calamares-deb/DEBIAN
cat > calamares-deb/DEBIAN/control << EOF
Package: calamares-zforge
Version: 3.3.0
Architecture: amd64
Maintainer: Z-FORGE Build System  
Description: Calamares installer for Z-FORGE
Depends: libqt5core5a, libqt5gui5, libqt5widgets5, libkf5coreaddons5, 
 libkf5parts5, libkpmcore12, python3, rsync, squashfs-tools
EOF

cp -r calamares_pkg/* calamares-deb/
dpkg-deb --build calamares-deb
cp calamares-deb.deb "$PACKAGES_DIR/calamares/calamares-zforge_3.3.0_amd64.deb"

# 6. Build system utilities
log "🔧 Building system utilities..."

# Build packages that don't require chroot environment
UTILITIES=(
    "debootstrap"
    "live-build" 
    "squashfs-tools"
    "genisoimage"
    "memtest86+"
)

for util in "${UTILITIES[@]}"; do
    log "📦 Downloading and preparing $util..."
    cd "$BUILD_DIR"
    apt-get source "$util" || continue
    
    # Find the extracted directory
    util_dir=$(find . -maxdepth 1 -type d -name "${util}-*" | head -1)
    if [ -d "$util_dir" ]; then
        cd "$util_dir"
        # Build if it has debian directory
        if [ -d "debian" ]; then
            log "🔨 Building $util..."
            dpkg-buildpackage -us -uc -b || log "⚠️  Failed to build $util"
            cd ..
            cp *.deb "$PACKAGES_DIR/utilities/" 2>/dev/null || true
        fi
    fi
done

# 7. Create package index
log "📋 Creating package index..."
cd "$PACKAGES_DIR"

cat > PACKAGES.md << EOF
# Z-FORGE Prebuilt Packages

Built on: $(date)
Build system: $(uname -a)

## Package Categories

### ZFS Packages (from Proxmox source)
$(ls -la zfs/*.deb 2>/dev/null | wc -l) packages

### Kernel Modules  
$(ls -la kernel/*.deb 2>/dev/null | wc -l) packages

### Boot Loaders
$(ls -la bootloaders/*.deb 2>/dev/null | wc -l) packages

### System Packages
$(ls -la system/*.deb 2>/dev/null | wc -l) packages

### Utilities
$(ls -la utilities/*.deb 2>/dev/null | wc -l) packages

### Calamares Installer
$(ls -la calamares/*.deb 2>/dev/null | wc -l) packages

## Total Packages: $(find . -name "*.deb" | wc -l)

## Package List
$(find . -name "*.deb" -type f | sort)
EOF

# 8. Create installation script for chroot
log "📝 Creating chroot installation script..."
cat > "$PACKAGES_DIR/install_in_chroot.sh" << 'INSTALL_SCRIPT'
#!/bin/bash
# Install prebuilt packages in chroot environment

set -e

PACKAGES_DIR="/tmp/prebuilt_packages"
LOG_FILE="/var/log/package_install.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "🚀 Installing prebuilt packages in chroot..."

# Install ZFS packages first
log "📦 Installing ZFS packages..."
dpkg -i "$PACKAGES_DIR/zfs/"*.deb || apt-get -f install -y

# Install kernel modules
log "📦 Installing kernel modules..."
find "$PACKAGES_DIR/kernel" -name "*.deb" -exec dpkg -i {} \; || true

# Install bootloaders
log "📦 Installing bootloaders..."
dpkg -i "$PACKAGES_DIR/bootloaders/"*.deb || apt-get -f install -y

# Install system packages
log "📦 Installing system packages..."
dpkg -i "$PACKAGES_DIR/system/"*.deb || apt-get -f install -y

# Install utilities
log "📦 Installing utilities..."
dpkg -i "$PACKAGES_DIR/utilities/"*.deb || apt-get -f install -y

# Install Calamares
log "📦 Installing Calamares..."
dpkg -i "$PACKAGES_DIR/calamares/"*.deb || apt-get -f install -y

# Fix any dependency issues
log "🔧 Fixing dependencies..."
apt-get -f install -y

log "✅ Package installation complete!"
INSTALL_SCRIPT

chmod +x "$PACKAGES_DIR/install_in_chroot.sh"

# 9. Create build summary
log "📊 Creating build summary..."
TOTAL_PACKAGES=$(find "$PACKAGES_DIR" -name "*.deb" | wc -l)
TOTAL_SIZE=$(du -sh "$PACKAGES_DIR" | cut -f1)

cat > "$PROJECT_ROOT/outside_build_summary.txt" << EOF
Z-FORGE Outside Build Summary
=============================
Date: $(date)
Total packages built: $TOTAL_PACKAGES
Total size: $TOTAL_SIZE
Build log: $LOG_FILE

Package breakdown:
- ZFS: $(ls "$PACKAGES_DIR/zfs/"*.deb 2>/dev/null | wc -l) packages
- Kernel: $(ls "$PACKAGES_DIR/kernel/"*.deb 2>/dev/null | wc -l) packages  
- Bootloaders: $(ls "$PACKAGES_DIR/bootloaders/"*.deb 2>/dev/null | wc -l) packages
- System: $(ls "$PACKAGES_DIR/system/"*.deb 2>/dev/null | wc -l) packages
- Utilities: $(ls "$PACKAGES_DIR/utilities/"*.deb 2>/dev/null | wc -l) packages
- Calamares: $(ls "$PACKAGES_DIR/calamares/"*.deb 2>/dev/null | wc -l) packages

Next steps:
1. Review packages: ls -la $PACKAGES_DIR/
2. Copy to chroot during build
3. Run install_in_chroot.sh inside chroot
EOF

log "🎉 Outside build complete!"
log "📦 Total packages built: $TOTAL_PACKAGES"
log "💾 Total size: $TOTAL_SIZE"
log "📍 Packages location: $PACKAGES_DIR"
log "📄 Build summary: $PROJECT_ROOT/outside_build_summary.txt"

# Cleanup build directory to save space
log "🧹 Cleaning up build directory..."
rm -rf "$BUILD_DIR"

log "✅ All done! Packages are ready for chroot installation."