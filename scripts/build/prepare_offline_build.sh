#!/bin/bash
# Prepare everything needed for offline Z-FORGE build
# Downloads all packages, sources, and tools needed

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OFFLINE_DIR="$PROJECT_ROOT/offline_build_cache"
LOG_FILE="$PROJECT_ROOT/logs/offline_prep_$(date +%Y%m%d_%H%M%S).log"

# Create directories
mkdir -p "$OFFLINE_DIR"/{packages,sources,tools,configs}
mkdir -p "$PROJECT_ROOT/logs"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "🎯 Preparing offline build environment..."

if [[ $EUID -ne 0 ]]; then
    log "❌ This script must be run as root"
    echo "   sudo $0"
    exit 1
fi

cd "$OFFLINE_DIR"

# Update package lists
log "📋 Updating package lists..."
apt-get update

# Download all ZFS-related packages
log "📦 Downloading ZFS ecosystem..."
ZFS_PACKAGES=(
    "zfsutils-linux"
    "zfs-dkms"
    "zfs-initramfs" 
    "zfs-zed"
    "libzfs4linux"
    "libnvpair3linux"
    "libuutil3linux"
    "libzpool5linux"
    "zfs-test"
)

for pkg in "${ZFS_PACKAGES[@]}"; do
    log "⬇️  Downloading $pkg..."
    apt-get download "$pkg" 2>/dev/null || log "⚠️  Failed to download $pkg"
done

# Download kernel and build tools
log "📦 Downloading build environment..."
BUILD_PACKAGES=(
    "build-essential"
    "linux-headers-$(uname -r)"
    "linux-image-$(uname -r)"
    "dkms"
    "devscripts"
    "debhelper"
    "git"
    "wget"
    "curl"
    "autotools-dev"
    "autoconf"
    "automake"
    "libtool"
    "pkg-config"
    "zlib1g-dev"
    "uuid-dev"
    "libblkid-dev"
    "libssl-dev"
    "libaio-dev"
    "libattr1-dev"
    "libelf-dev"
    "python3-dev"
    "python3-setuptools"
    "python3-cffi"
    "libffi-dev"
    "libudev-dev"
    "alien"
    "fakeroot"
)

for pkg in "${BUILD_PACKAGES[@]}"; do
    log "⬇️  Downloading $pkg..."
    apt-get download "$pkg" 2>/dev/null || log "⚠️  Failed to download $pkg"
done

# Download live system packages
log "📦 Downloading live system packages..."
LIVE_PACKAGES=(
    "live-boot"
    "live-config"
    "live-config-systemd"
    "squashfs-tools"
    "xorriso"
    "isolinux"
    "syslinux-common"
    "grub-efi-amd64"
    "grub-pc-bin"
    "memtest86+"
)

for pkg in "${LIVE_PACKAGES[@]}"; do
    log "⬇️  Downloading $pkg..."
    apt-get download "$pkg" 2>/dev/null || log "⚠️  Failed to download $pkg"
done

# Move packages to organized directory
mv *.deb packages/ 2>/dev/null || true

# Download source packages
log "📥 Downloading source packages..."
cd sources

# ZFS source
log "⬇️  Downloading ZFS 2.3.3 source..."
wget -c https://github.com/openzfs/zfs/releases/download/zfs-2.3.3/zfs-2.3.3.tar.gz || log "⚠️  ZFS source failed"

# Kernel source
log "⬇️  Downloading kernel source..."
KERNEL_VERSION=$(uname -r | cut -d'-' -f1)
wget -c https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-${KERNEL_VERSION}.tar.xz || log "⚠️  Kernel source failed"

# Proxmox source
log "⬇️  Downloading Proxmox sources..."
git clone https://git.proxmox.com/git/pve-kernel.git || log "⚠️  Proxmox kernel clone failed"
git clone https://git.proxmox.com/git/zfsonlinux.git || log "⚠️  Proxmox ZFS clone failed"

# Create build tools
cd ../tools
log "🔧 Creating build tools..."

# Create ZFS builder
cat > build_zfs_offline.sh << 'EOFZFS'
#!/bin/bash
# Build ZFS from offline sources

set -e
SOURCE_DIR="../sources"
PACKAGE_DIR="../packages"

echo "🔨 Building ZFS from offline sources..."

# Extract ZFS
cd "$SOURCE_DIR"
if [ ! -d "zfs-2.3.3" ]; then
    tar -xzf zfs-2.3.3.tar.gz
fi

cd zfs-2.3.3

# Configure and build
./autogen.sh
./configure \
    --prefix=/usr \
    --sysconfdir=/etc \
    --localstatedir=/var \
    --libdir=/usr/lib/x86_64-linux-gnu \
    --with-config=user \
    --enable-systemd

make -j$(nproc)
make deb-utils

# Copy packages
find . -name "*.deb" -exec cp {} "$PACKAGE_DIR/" \;

echo "✅ ZFS build complete!"
EOFZFS

chmod +x build_zfs_offline.sh

# Create package installer
cat > install_to_chroot.sh << 'EOFINSTALL'
#!/bin/bash
# Install offline packages to chroot

CHROOT_PATH="${1:-/tmp/zforge_workspace/chroot}"
PACKAGE_DIR="../packages"

if [ ! -d "$CHROOT_PATH" ]; then
    echo "❌ Chroot not found: $CHROOT_PATH"
    exit 1
fi

echo "📦 Installing offline packages to $CHROOT_PATH"

# Copy packages
mkdir -p "$CHROOT_PATH/tmp/offline_packages"
cp "$PACKAGE_DIR"/*.deb "$CHROOT_PATH/tmp/offline_packages/"

# Install
chroot "$CHROOT_PATH" /bin/bash -c "
    cd /tmp/offline_packages
    dpkg -i *.deb || apt-get install -f -y
    rm -rf /tmp/offline_packages
"

echo "✅ Offline package installation complete!"
EOFINSTALL

chmod +x install_to_chroot.sh

# Create configurations
cd ../configs
log "⚙️  Creating build configurations..."

# Create optimized build spec
cat > build_spec_offline.yml << 'EOFSPEC'
# Z-FORGE Offline Build Specification
metadata:
  name: "Z-FORGE Offline Build"
  version: "3.0-offline"
  description: "Build using pre-downloaded packages"

build:
  workspace:
    base_path: "${HOME}/zforge_workspace"
    use_tmp: false
    cleanup_on_success: false

modules:
  - name: "WorkspaceSetup"
    enabled: true
  - name: "Debootstrap" 
    enabled: true
    config:
      suite: "trixie"
      use_cache: true
      cache_dir: "${PWD}/offline_build_cache/packages"
  - name: "OfflinePackageInstaller"
    enabled: true
    config:
      package_dir: "${PWD}/offline_build_cache/packages"
  - name: "ZfsBuild"
    enabled: true
    config:
      method: "offline_source"
      source_dir: "${PWD}/offline_build_cache/sources/zfs-2.3.3"
  - name: "LiveEnvironment"
    enabled: true
  - name: "IsoGeneration"
    enabled: true
EOFSPEC

# Create offline build script
cat > ../build_offline.sh << 'EOFBUILD'
#!/bin/bash
# Complete offline build script

set -e

echo "🚀 Starting Z-FORGE offline build..."

# Check offline cache
if [ ! -d "offline_build_cache" ]; then
    echo "❌ Offline cache not found. Run prepare_offline_build.sh first."
    exit 1
fi

# Build ZFS if needed
echo "🔧 Building ZFS packages..."
cd offline_build_cache/tools
./build_zfs_offline.sh

# Run main build
cd ../..
echo "🏗️  Starting main build..."
sudo python3 build.py --spec offline_build_cache/configs/build_spec_offline.yml

echo "✅ Offline build complete!"
EOFBUILD

chmod +x ../build_offline.sh

# Create manifest
cd "$OFFLINE_DIR"
log "📋 Creating offline build manifest..."
cat > offline_manifest.txt << EOF
# Z-FORGE Offline Build Cache
# Created: $(date)
# System: $(uname -a)

Package Statistics:
- .deb packages: $(find packages -name "*.deb" | wc -l)
- Source tarballs: $(find sources -name "*.tar.*" | wc -l)
- Git repositories: $(find sources -name ".git" -type d | wc -l)

Build Tools:
- build_zfs_offline.sh
- install_to_chroot.sh
- build_offline.sh

Configurations:
- build_spec_offline.yml

Usage:
1. Build ZFS: cd offline_build_cache/tools && ./build_zfs_offline.sh
2. Full build: ./build_offline.sh
3. Manual install: cd offline_build_cache/tools && ./install_to_chroot.sh /path/to/chroot

Cache size: $(du -sh . | cut -f1)
EOF

log "🎉 Offline build preparation complete!"
log "📍 Cache created at: $OFFLINE_DIR"
log "📄 Preparation log: $LOG_FILE"
echo ""
echo "Offline cache ready:"
echo "- $(find packages -name "*.deb" | wc -l) packages downloaded"
echo "- $(find sources -name "*.tar.*" | wc -l) source tarballs"
echo "- Build tools created"
echo ""
echo "After reboot, run: ./offline_build_cache/build_offline.sh"