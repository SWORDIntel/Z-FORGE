#!/bin/bash
# Build ZFS packages the Debian way
# This script builds proper Debian packages for ZFS

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PACKAGES_DIR="$PROJECT_ROOT/prebuilt_packages/zfs"
BUILD_DIR="$PROJECT_ROOT/zfs_debian_build"
LOG_FILE="$PROJECT_ROOT/logs/zfs_debian_build_$(date +%Y%m%d_%H%M%S).log"

ZFS_VERSION="2.3.3"

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

log "🚀 Starting Debian-style ZFS package build..."

# Install build dependencies
log "📦 Installing build dependencies..."
apt-get update
apt-get install -y \
    build-essential \
    debhelper \
    debhelper-compat \
    dh-python \
    dh-sequence-dkms \
    autotools-dev \
    autoconf \
    automake \
    libtool \
    gawk \
    dkms \
    libblkid-dev \
    uuid-dev \
    libudev-dev \
    libssl-dev \
    zlib1g-dev \
    libaio-dev \
    libattr1-dev \
    libelf-dev \
    python3-all-dev \
    python3-setuptools \
    python3-cffi \
    libffi-dev \
    po-debconf \
    libpam0g-dev \
    libselinux1-dev \
    libcurl4-openssl-dev

cd "$BUILD_DIR"

# Method 1: Try building from Debian source package
log "🔧 Method 1: Trying Debian source package..."

# Add Debian experimental/unstable sources temporarily
cat > /tmp/zfs-sources.list << EOF
deb-src http://deb.debian.org/debian experimental main contrib
deb-src http://deb.debian.org/debian unstable main contrib
EOF

# Try to get ZFS source package
if cp /tmp/zfs-sources.list /etc/apt/sources.list.d/zfs-temp.list; then
    apt-get update
    
    # Try to download ZFS source package
    if apt-get source zfs-linux 2>/dev/null || apt-get source zfsutils-linux 2>/dev/null; then
        log "✅ Got Debian ZFS source package"
        
        # Find the extracted directory
        ZFS_DIR=$(find . -maxdepth 1 -type d -name "zfs*" | head -1)
        
        if [ -n "$ZFS_DIR" ] && [ -d "$ZFS_DIR" ]; then
            cd "$ZFS_DIR"
            log "📦 Building Debian packages..."
            
            # Build without signing
            dpkg-buildpackage -us -uc -b
            
            cd ..
            # Copy built packages
            find . -maxdepth 1 -name "*.deb" -exec cp {} "$PACKAGES_DIR/" \;
            
            # Clean up sources
            rm -f /etc/apt/sources.list.d/zfs-temp.list
            apt-get update
            
            PACKAGE_COUNT=$(ls "$PACKAGES_DIR/"*.deb 2>/dev/null | wc -l)
            if [ "$PACKAGE_COUNT" -gt 0 ]; then
                log "✅ Successfully built $PACKAGE_COUNT packages using Debian method!"
                # Skip to package listing
                cd "$BUILD_DIR"
            else
                log "⚠️  Debian build didn't produce packages, trying Method 2..."
            fi
        fi
    else
        log "⚠️  Could not get Debian source package"
    fi
    
    # Clean up sources
    rm -f /etc/apt/sources.list.d/zfs-temp.list
    apt-get update
fi

# Method 2: Build from upstream with Debian packaging
PACKAGE_COUNT=$(ls "$PACKAGES_DIR/"*.deb 2>/dev/null | wc -l)
if [ "$PACKAGE_COUNT" -eq 0 ]; then
    log "🔧 Method 2: Building from upstream with Debian packaging..."
    
    cd "$BUILD_DIR"
    
    # Download ZFS source
    if [ ! -f "zfs-${ZFS_VERSION}.tar.gz" ]; then
        log "⬇️  Downloading ZFS ${ZFS_VERSION}..."
        wget "https://github.com/openzfs/zfs/releases/download/zfs-${ZFS_VERSION}/zfs-${ZFS_VERSION}.tar.gz"
    fi
    
    # Extract
    tar -xzf "zfs-${ZFS_VERSION}.tar.gz"
    cd "zfs-${ZFS_VERSION}"
    
    # Create debian directory if it doesn't exist
    if [ ! -d "debian" ]; then
        log "📝 Creating debian packaging directory..."
        mkdir -p debian
        
        # Create minimal debian/control file
        cat > debian/control << 'CONTROL'
Source: zfsutils-linux
Section: contrib/admin
Priority: optional
Maintainer: Z-FORGE Build System <build@zforge.local>
Build-Depends: debhelper-compat (= 12),
               dh-python,
               dh-sequence-dkms,
               libaio-dev,
               libblkid-dev,
               libssl-dev,
               libtool,
               libudev-dev,
               python3-all-dev,
               uuid-dev,
               zlib1g-dev
Standards-Version: 4.5.0

Package: zfsutils-linux
Architecture: amd64
Depends: ${shlibs:Depends}, ${misc:Depends}, ${python3:Depends}
Description: command-line tools to manage OpenZFS filesystems
 OpenZFS is a storage platform.
 .
 This package provides the zfs and zpool commands.

Package: libzfs4linux
Architecture: amd64
Depends: ${shlibs:Depends}, ${misc:Depends}
Description: OpenZFS library
 OpenZFS filesystem library for Linux.

Package: zfs-dkms
Architecture: all
Depends: ${misc:Depends}, dkms
Description: OpenZFS kernel modules (DKMS)
 OpenZFS kernel modules built using DKMS.
CONTROL

        # Create debian/rules
        cat > debian/rules << 'RULES'
#!/usr/bin/make -f

%:
	dh $@ --with python3,dkms

override_dh_auto_configure:
	./autogen.sh
	dh_auto_configure -- \
		--prefix=/usr \
		--with-config=user \
		--enable-systemd \
		--enable-pyzfs

override_dh_install:
	dh_install
	# Additional install steps if needed

override_dh_dkms:
	dh_dkms -V $(DEB_VERSION_UPSTREAM)
RULES
        chmod +x debian/rules

        # Create debian/changelog
        cat > debian/changelog << CHANGELOG
zfsutils-linux (${ZFS_VERSION}-1) unstable; urgency=medium

  * Z-FORGE build of ZFS ${ZFS_VERSION}

 -- Z-FORGE Build System <build@zforge.local>  $(date -R)
CHANGELOG

        # Create debian/compat
        echo "12" > debian/compat
    fi
    
    # Build packages
    log "📦 Building Debian packages..."
    
    # First run autogen
    sh autogen.sh
    
    # Build with dpkg-buildpackage
    dpkg-buildpackage -us -uc -b || {
        log "⚠️  Full build failed, trying minimal build..."
        
        # Try a simpler approach
        ./configure --with-config=user --prefix=/usr
        make -j$(nproc)
        
        # Create packages manually
        log "📦 Creating packages manually with checkinstall..."
        checkinstall -D -y \
            --pkgname=zfsutils-linux \
            --pkgversion="${ZFS_VERSION}" \
            --maintainer="Z-FORGE" \
            --pakdir="$PACKAGES_DIR" \
            --backup=no \
            --install=no \
            make install
    }
    
    # Copy any .deb files created
    cd "$BUILD_DIR"
    find . -name "*.deb" -type f -exec cp {} "$PACKAGES_DIR/" \;
fi

# Final package count and summary
cd "$BUILD_DIR"
PACKAGE_COUNT=$(ls "$PACKAGES_DIR/"*.deb 2>/dev/null | wc -l)

if [ "$PACKAGE_COUNT" -gt 0 ]; then
    log "✅ Successfully built $PACKAGE_COUNT ZFS packages!"
    log "📍 Packages location: $PACKAGES_DIR"
    ls -la "$PACKAGES_DIR/"
    
    # Create package list
    cat > "$PACKAGES_DIR/PACKAGES.txt" << EOF
ZFS Debian Packages
Built: $(date)
Version: ${ZFS_VERSION}
Count: $PACKAGE_COUNT packages

Files:
$(ls -1 "$PACKAGES_DIR/"*.deb 2>/dev/null)
EOF
    
    # Create install script
    cat > "$PACKAGES_DIR/install_zfs.sh" << 'INSTALL_SCRIPT'
#!/bin/bash
set -e

echo "Installing ZFS packages..."

# Install dependencies first
apt-get update
apt-get install -y dkms

# Install packages in order
for pkg in libnvpair*.deb libuutil*.deb libzfs*.deb libzpool*.deb; do
    [ -f "$pkg" ] && dpkg -i "$pkg" || true
done

# Install DKMS package
[ -f zfs-dkms*.deb ] && dpkg -i zfs-dkms*.deb || true

# Install main packages
dpkg -i *.deb || true

# Fix dependencies
apt-get -f install -y

# Load module
modprobe zfs || true

echo "ZFS installation complete!"
zfs version || echo "ZFS module not loaded yet"
INSTALL_SCRIPT
    
    chmod +x "$PACKAGES_DIR/install_zfs.sh"
    
else
    log "❌ No packages were built!"
    log "Check the log for errors: $LOG_FILE"
    exit 1
fi

# Cleanup
log "🧹 Cleaning up..."
cd "$PROJECT_ROOT"
rm -rf "$BUILD_DIR"

log "🎉 Build complete!"
log "📄 Log file: $LOG_FILE"

echo ""
echo "Next steps:"
echo "1. Review packages: ls -la $PACKAGES_DIR/"
echo "2. Install with: cd $PACKAGES_DIR && sudo ./install_zfs.sh"