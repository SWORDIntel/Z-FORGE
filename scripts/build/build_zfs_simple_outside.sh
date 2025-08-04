#!/bin/bash
# Simple ZFS package builder - builds ZFS outside chroot
# This is a minimal version that focuses just on ZFS

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PACKAGES_DIR="$PROJECT_ROOT/prebuilt_packages/zfs"
BUILD_DIR="$PROJECT_ROOT/zfs_build_tmp"
LOG_FILE="$PROJECT_ROOT/logs/zfs_build_$(date +%Y%m%d_%H%M%S).log"

# Create directories
mkdir -p "$PACKAGES_DIR"
mkdir -p "$PROJECT_ROOT/logs"
mkdir -p "$BUILD_DIR"

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

log "🚀 Starting simple ZFS package build..."

# Install minimal dependencies for ZFS
log "📦 Installing ZFS build dependencies..."
apt-get update
apt-get install -y \
    build-essential \
    autotools-dev \
    autoconf \
    automake \
    libtool \
    gawk \
    alien \
    fakeroot \
    checkinstall \
    dkms \
    libblkid-dev \
    uuid-dev \
    libudev-dev \
    libssl-dev \
    zlib1g-dev \
    libaio-dev \
    libattr1-dev \
    libelf-dev \
    python3 \
    python3-dev \
    python3-setuptools \
    python3-cffi \
    libffi-dev \
    libpam0g-dev \
    libnvpair3linux \
    libuutil3linux || true

# Build ZFS from Proxmox source
log "🔧 Building ZFS from Proxmox source..."
cd "$BUILD_DIR"

# Option 1: Try Proxmox source first
if git clone https://git.proxmox.com/git/zfsonlinux.git 2>/dev/null; then
    log "✅ Using Proxmox ZFS source"
    cd zfsonlinux
    
    # Check for debian directory
    if [ -d "debian" ]; then
        log "📦 Building Debian packages..."
        dpkg-buildpackage -b -uc -us || {
            log "⚠️  Debian package build failed, trying make deb..."
            make deb
        }
    else
        log "📦 No debian directory, using make deb..."
        make deb
    fi
else
    # Option 2: Fallback to OpenZFS
    log "⚠️  Proxmox source unavailable, using OpenZFS..."
    
    ZFS_VERSION="2.3.3"
    if [ ! -f "zfs-${ZFS_VERSION}.tar.gz" ]; then
        log "⬇️  Downloading ZFS ${ZFS_VERSION}..."
        wget "https://github.com/openzfs/zfs/releases/download/zfs-${ZFS_VERSION}/zfs-${ZFS_VERSION}.tar.gz"
    fi
    
    log "📦 Extracting ZFS source..."
    tar -xzf "zfs-${ZFS_VERSION}.tar.gz"
    cd "zfs-${ZFS_VERSION}"
    
    log "🔧 Configuring ZFS..."
    sh autogen.sh
    
    # Configure for Debian package building
    ./configure \
        --prefix=/usr \
        --sysconfdir=/etc \
        --localstatedir=/var \
        --libdir=/usr/lib/x86_64-linux-gnu \
        --includedir=/usr/include \
        --datarootdir=/usr/share \
        --with-config=user \
        --with-systemdunitdir=/lib/systemd/system \
        --with-systemdpresetdir=/lib/systemd/system-preset \
        --with-systemdgeneratordir=/lib/systemd/system-generators \
        --enable-systemd \
        --enable-pyzfs \
        --disable-sysvinit
    
    log "🔨 Building ZFS..."
    make -j$(nproc)
    
    log "📦 Creating Debian packages using checkinstall..."
    
    # Create a description file for checkinstall
    cat > description-pak << EOF
ZFS Filesystem for Linux
OpenZFS userspace and kernel modules
EOF
    
    # Use checkinstall to create .deb package
    checkinstall -D -y \
        --pkgname=zfsutils-linux \
        --pkgversion="${ZFS_VERSION}" \
        --pkgrelease=1 \
        --maintainer="Z-FORGE Build System" \
        --pkggroup=admin \
        --pakdir="$PACKAGES_DIR" \
        --nodoc \
        --strip=no \
        --stripso=no \
        --addso=yes \
        --fstrans=yes \
        --reset-uids=yes \
        --backup=no \
        --install=no \
        make install || {
            log "⚠️  Checkinstall failed, trying alien conversion..."
            
            # Alternative: Build RPM and convert to DEB
            log "📦 Building RPM packages first..."
            make rpm-utils || true
            
            log "🔄 Converting RPM to DEB with alien..."
            find . -name "*.rpm" -type f | while read rpm; do
                alien -d -c "$rpm" || log "⚠️  Failed to convert $rpm"
            done
            
            # Move generated .deb files
            find . -name "*.deb" -type f -exec mv {} "$PACKAGES_DIR/" \;
        }
fi

# Copy all .deb files to packages directory
log "📦 Collecting built packages..."
cd "$BUILD_DIR"
find . -name "*.deb" -type f -exec cp {} "$PACKAGES_DIR/" \;

# Count packages
PACKAGE_COUNT=$(ls "$PACKAGES_DIR/"*.deb 2>/dev/null | wc -l)

if [ "$PACKAGE_COUNT" -gt 0 ]; then
    log "✅ Successfully built $PACKAGE_COUNT ZFS packages!"
    log "📍 Packages location: $PACKAGES_DIR"
    ls -la "$PACKAGES_DIR/"
    
    # Create package list
    cat > "$PACKAGES_DIR/PACKAGES.txt" << EOF
ZFS Packages Built on $(date)
============================
$(ls -1 "$PACKAGES_DIR/"*.deb)

Total: $PACKAGE_COUNT packages
EOF
    
    # Create simple install script
    cat > "$PACKAGES_DIR/install_zfs.sh" << 'INSTALL_SCRIPT'
#!/bin/bash
# Install ZFS packages in correct order

set -e

echo "Installing ZFS packages..."

# Install in dependency order
dpkg -i libnvpair*.deb libuutil*.deb libzfs*.deb libzpool*.deb || true
dpkg -i zfs-dkms*.deb || true  
dpkg -i zfs-initramfs*.deb zfs-zed*.deb zfsutils*.deb || true

# Fix any missing dependencies
apt-get -f install -y

echo "ZFS installation complete!"
INSTALL_SCRIPT
    
    chmod +x "$PACKAGES_DIR/install_zfs.sh"
    
else
    log "❌ No packages were built!"
    exit 1
fi

# Cleanup build directory
log "🧹 Cleaning up build directory..."
cd "$PROJECT_ROOT"
rm -rf "$BUILD_DIR"

log "🎉 ZFS package build complete!"
log "📄 Build log: $LOG_FILE"
echo ""
echo "Next steps:"
echo "1. Review packages: ls -la $PACKAGES_DIR/"
echo "2. Copy to chroot during build or install directly"
echo "3. Run install_zfs.sh to install packages"