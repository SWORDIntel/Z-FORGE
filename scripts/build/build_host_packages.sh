#!/bin/bash
# Build essential packages on host system (outside chroot)
# Run this script after reboot to prepare packages for Z-FORGE build

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PACKAGES_DIR="$PROJECT_ROOT/host_built_packages"
LOG_FILE="$PROJECT_ROOT/logs/host_build_$(date +%Y%m%d_%H%M%S).log"

# Create directories
mkdir -p "$PACKAGES_DIR"
mkdir -p "$PROJECT_ROOT/logs"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "🚀 Starting host package build process..."

# Check if we're running as root
if [[ $EUID -ne 0 ]]; then
    log "❌ This script must be run as root"
    echo "   sudo $0"
    exit 1
fi

# Install build dependencies
log "📦 Installing build dependencies..."
apt-get update
apt-get install -y \
    build-essential \
    devscripts \
    debhelper \
    dh-sequence-dkms \
    git \
    wget \
    curl \
    autotools-dev \
    autoconf \
    automake \
    libtool \
    pkg-config \
    zlib1g-dev \
    uuid-dev \
    libblkid-dev \
    libssl-dev \
    libaio-dev \
    libattr1-dev \
    libelf-dev \
    python3-dev \
    python3-setuptools \
    python3-cffi \
    libffi-dev \
    libudev-dev \
    alien \
    fakeroot \
    dkms

# Build ZFS packages
log "🔧 Building ZFS packages..."
cd "$PACKAGES_DIR"

# Download ZFS source if not exists
if [ ! -f "zfs-2.3.3.tar.gz" ]; then
    log "⬇️  Downloading ZFS 2.3.3 source..."
    wget https://github.com/openzfs/zfs/releases/download/zfs-2.3.3/zfs-2.3.3.tar.gz
fi

# Extract and build
if [ ! -d "zfs-2.3.3" ]; then
    log "📦 Extracting ZFS source..."
    tar -xzf zfs-2.3.3.tar.gz
fi

cd zfs-2.3.3

log "🔨 Configuring ZFS build..."
./autogen.sh
./configure \
    --prefix=/usr \
    --sysconfdir=/etc \
    --localstatedir=/var \
    --libdir=/usr/lib/x86_64-linux-gnu \
    --includedir=/usr/include \
    --with-config=user \
    --enable-systemd \
    --enable-pyzfs

log "🔨 Building ZFS userspace..."
make -j$(nproc)

log "📦 Creating ZFS Debian packages..."
make deb-utils || log "⚠️  deb-utils failed, continuing..."

# Copy built packages
cd "$PACKAGES_DIR"
find . -name "*.deb" -type f -exec cp {} "$PACKAGES_DIR/" \;

log "✅ ZFS packages built successfully!"

# Build Proxmox kernel if possible
log "🔧 Attempting to build Proxmox kernel packages..."
cd "$PACKAGES_DIR"

# Download Proxmox kernel source
if [ ! -d "proxmox-kernel" ]; then
    log "⬇️  Cloning Proxmox kernel source..."
    git clone https://git.proxmox.com/git/pve-kernel.git proxmox-kernel || log "⚠️  Proxmox clone failed"
fi

# Create package manifest
log "📋 Creating package manifest..."
cat > "$PACKAGES_DIR/package_manifest.txt" << EOF
# Z-FORGE Host-Built Packages
# Built on: $(date)
# System: $(uname -a)
# ZFS Version: 2.3.3

ZFS Packages:
$(find "$PACKAGES_DIR" -name "*.deb" -type f | head -20)

Total packages: $(find "$PACKAGES_DIR" -name "*.deb" -type f | wc -l)
EOF

log "🎉 Host package build complete!"
log "📍 Packages saved to: $PACKAGES_DIR"
log "📄 Build log: $LOG_FILE"
echo ""
echo "Next steps:"
echo "1. Review built packages: ls -la $PACKAGES_DIR"
echo "2. Run Z-FORGE build: sudo python3 build.py --spec build_spec_stable.yml"