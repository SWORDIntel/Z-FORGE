#!/bin/bash
# Download essential packages for Z-FORGE build (outside chroot)
# Run this script after reboot to prepare packages

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOWNLOAD_DIR="$PROJECT_ROOT/downloaded_packages"
LOG_FILE="$PROJECT_ROOT/logs/download_$(date +%Y%m%d_%H%M%S).log"

# Create directories
mkdir -p "$DOWNLOAD_DIR"
mkdir -p "$PROJECT_ROOT/logs"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "📥 Starting package download process..."

# Check internet connectivity
if ! ping -c 1 8.8.8.8 &> /dev/null; then
    log "❌ No internet connection"
    exit 1
fi

cd "$DOWNLOAD_DIR"

# Download ZFS packages from Debian repositories
log "⬇️  Downloading ZFS packages..."
apt-get update
apt-get download \
    zfsutils-linux \
    zfs-dkms \
    zfs-initramfs \
    zfs-zed \
    libzfs4linux \
    libnvpair3linux \
    libuutil3linux \
    libzpool5linux || log "⚠️  Some ZFS packages failed to download"

# Download kernel packages
log "⬇️  Downloading kernel packages..."
apt-get download \
    linux-image-generic \
    linux-headers-generic \
    linux-image-amd64 \
    linux-headers-amd64 || log "⚠️  Some kernel packages failed to download"

# Download build essentials
log "⬇️  Downloading build packages..."
apt-get download \
    build-essential \
    devscripts \
    debhelper \
    git \
    wget \
    curl \
    autotools-dev \
    autoconf \
    automake \
    libtool \
    pkg-config || log "⚠️  Some build packages failed to download"

# Download live system packages
log "⬇️  Downloading live system packages..."
apt-get download \
    live-boot \
    live-config \
    live-config-systemd \
    squashfs-tools \
    xorriso \
    isolinux \
    syslinux-common || log "⚠️  Some live packages failed to download"

# Download ZFS source tarballs
log "⬇️  Downloading ZFS source..."
wget -c https://github.com/openzfs/zfs/releases/download/zfs-2.3.3/zfs-2.3.3.tar.gz || log "⚠️  ZFS source download failed"

# Download Proxmox packages if available
log "⬇️  Attempting Proxmox package downloads..."
echo "deb http://download.proxmox.com/debian/pve bookworm pve-no-subscription" > /etc/apt/sources.list.d/pve-install-repo.list
wget -O /etc/apt/trusted.gpg.d/proxmox-release-bookworm.gpg https://enterprise.proxmox.com/debian/proxmox-release-bookworm.gpg || log "⚠️  Proxmox GPG failed"
apt-get update || log "⚠️  Proxmox repo update failed"
apt-get download \
    proxmox-ve \
    pve-kernel-6.8 \
    pve-headers-6.8 || log "⚠️  Proxmox packages failed to download"

# Create download manifest
log "📋 Creating download manifest..."
cat > "$DOWNLOAD_DIR/download_manifest.txt" << EOF
# Z-FORGE Downloaded Packages
# Downloaded on: $(date)
# System: $(uname -a)

Total .deb files: $(find "$DOWNLOAD_DIR" -name "*.deb" | wc -l)
Total .tar.gz files: $(find "$DOWNLOAD_DIR" -name "*.tar.gz" | wc -l)

Package list:
$(ls -la "$DOWNLOAD_DIR"/*.deb 2>/dev/null | head -30)

Source tarballs:
$(ls -la "$DOWNLOAD_DIR"/*.tar.gz 2>/dev/null)
EOF

# Create installation script
log "📝 Creating installation script..."
cat > "$DOWNLOAD_DIR/install_downloaded_packages.sh" << 'EOF'
#!/bin/bash
# Install downloaded packages to chroot environment
# Usage: ./install_downloaded_packages.sh /path/to/chroot

CHROOT_PATH="${1:-/tmp/zforge_workspace/chroot}"

if [ ! -d "$CHROOT_PATH" ]; then
    echo "❌ Chroot path does not exist: $CHROOT_PATH"
    exit 1
fi

echo "📦 Installing downloaded packages to $CHROOT_PATH"

# Copy packages to chroot
mkdir -p "$CHROOT_PATH/tmp/downloaded_packages"
cp *.deb "$CHROOT_PATH/tmp/downloaded_packages/" 2>/dev/null || true

# Install in chroot
chroot "$CHROOT_PATH" /bin/bash -c "
    cd /tmp/downloaded_packages
    dpkg -i *.deb || apt-get install -f -y
    rm -rf /tmp/downloaded_packages
"

echo "✅ Package installation complete!"
EOF

chmod +x "$DOWNLOAD_DIR/install_downloaded_packages.sh"

log "🎉 Package download complete!"
log "📍 Packages saved to: $DOWNLOAD_DIR"
log "📄 Download log: $LOG_FILE"
echo ""
echo "Downloaded packages:"
echo "- $(find "$DOWNLOAD_DIR" -name "*.deb" | wc -l) Debian packages"
echo "- $(find "$DOWNLOAD_DIR" -name "*.tar.gz" | wc -l) Source tarballs"
echo ""
echo "Next steps:"
echo "1. Review packages: ls -la $DOWNLOAD_DIR"
echo "2. Install to chroot: $DOWNLOAD_DIR/install_downloaded_packages.sh"