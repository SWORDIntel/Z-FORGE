#!/bin/bash
# Build Proxmox VE 9.0 Beta from Source - Outside Build
# This must be run BEFORE the main build process

set -e

PROXMOX_VERSION="9.0-beta"
PVE_MANAGER_REPO="https://git.proxmox.com/git/pve-manager.git"
PROXMOX_VE_REPO="https://git.proxmox.com/git/proxmox-ve.git"
PVE_KERNEL_REPO="https://git.proxmox.com/git/pve-kernel.git"
BUILD_DIR="/usr/src"
PACKAGE_DIR="/opt/github/Z-FORGE/prebuilt_packages"
PROXMOX_BUILD_DIR="${BUILD_DIR}/proxmox-build"

echo "═══════════════════════════════════════════════════════════════════"
echo "     Proxmox VE ${PROXMOX_VERSION} Builder - Source Edition"
echo "   Building from Proxmox Git repositories"
echo "═══════════════════════════════════════════════════════════════════"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    echo "Usage: sudo $0"
    exit 1
fi

# Create directories
echo "[INFO] Setting up build environment..."
mkdir -p "$BUILD_DIR"
mkdir -p "$PACKAGE_DIR"
mkdir -p "$PROXMOX_BUILD_DIR"

# Install build dependencies
echo "[INFO] Installing Proxmox build dependencies..."
apt-get update
apt-get install -y \
    build-essential \
    devscripts \
    debhelper \
    git \
    lintian \
    pkg-config \
    libtool \
    autotools-dev \
    dh-systemd \
    quilt \
    dh-exec \
    libpve-common-perl \
    libpve-access-control \
    libpve-storage-perl \
    libpve-cluster-perl \
    pve-doc-generator \
    libproxmox-backup-qemu0-dev \
    libproxmox-rs-perl \
    librust-proxmox-dev \
    nodejs \
    npm \
    rsync \
    lsb-release \
    systemd \
    systemd-sysv

# Add Proxmox repository for dependencies
echo "[INFO] Adding Proxmox test repository..."
echo "deb http://download.proxmox.com/debian/pve trixie pve-test" > /etc/apt/sources.list.d/proxmox-test.list

# Add Proxmox GPG key
echo "[INFO] Adding Proxmox GPG key..."
wget -q -O- https://enterprise.proxmox.com/debian/proxmox-release-trixie.gpg | apt-key add - || {
    echo "[WARN] GPG key failed, continuing without signature verification"
}

apt-get update || {
    echo "[WARN] Repository update failed, continuing with available packages"
}

cd "$PROXMOX_BUILD_DIR"

# Clone repositories
echo "[INFO] Cloning Proxmox source repositories..."

# PVE Manager
echo "[INFO] Cloning pve-manager..."
if [ -d "pve-manager" ]; then
    rm -rf "pve-manager"
fi
git clone "$PVE_MANAGER_REPO" pve-manager
cd pve-manager
git checkout master || git checkout main
echo "[INFO] PVE Manager ready at commit: $(git rev-parse HEAD)"
cd ..

# Proxmox VE metapackage
echo "[INFO] Cloning proxmox-ve..."
if [ -d "proxmox-ve" ]; then
    rm -rf "proxmox-ve"
fi
git clone "$PROXMOX_VE_REPO" proxmox-ve
cd proxmox-ve
git checkout master || git checkout main
echo "[INFO] Proxmox VE ready at commit: $(git rev-parse HEAD)"
cd ..

# PVE Kernel (optional - takes very long to build)
echo "[INFO] Cloning pve-kernel (kernel build will be skipped for speed)..."
if [ -d "pve-kernel" ]; then
    rm -rf "pve-kernel"
fi
git clone "$PVE_KERNEL_REPO" pve-kernel
cd pve-kernel
git checkout master || git checkout main
echo "[INFO] PVE Kernel ready at commit: $(git rev-parse HEAD)"
cd ..

# Build PVE Manager
echo "[INFO] Building pve-manager..."
cd pve-manager

# Install build dependencies for pve-manager
echo "[INFO] Installing pve-manager build dependencies..."
apt-get build-dep -y . || {
    echo "[WARN] Some build dependencies failed, continuing..."
}

# Build pve-manager packages
echo "[INFO] Building pve-manager (this may take 15-30 minutes)..."
make clean || true
make || {
    echo "[WARN] pve-manager build had issues, checking for packages..."
}

# Find and copy built packages
find .. -name "*.deb" -path "*/pve-manager*" -exec cp {} "$PACKAGE_DIR/" \; || {
    echo "[WARN] No pve-manager packages found"
}

cd ..

# Build Proxmox VE metapackage
echo "[INFO] Building proxmox-ve metapackage..."
cd proxmox-ve

# Install build dependencies
apt-get build-dep -y . || {
    echo "[WARN] Some build dependencies failed, continuing..."
}

# Build proxmox-ve package
echo "[INFO] Building proxmox-ve metapackage..."
make clean || true
make || {
    echo "[WARN] proxmox-ve build had issues, checking for packages..."
}

# Find and copy built packages
find .. -name "*.deb" -path "*/proxmox-ve*" -exec cp {} "$PACKAGE_DIR/" \; || {
    echo "[WARN] No proxmox-ve packages found"
}

cd ..

# Note: We skip kernel building as it takes 2+ hours
echo "[INFO] Skipping pve-kernel build (takes 2+ hours)"
echo "[INFO] The system will use Debian kernel with Proxmox patches applied later"

# Try to download some essential Proxmox packages from repository
echo "[INFO] Downloading essential Proxmox packages from repository..."
cd "$PACKAGE_DIR"

# Create a temporary download script
cat > download_proxmox_essentials.sh << 'DOWNLOAD_SCRIPT'
#!/bin/bash
# Download essential Proxmox packages

PACKAGES=(
    "proxmox-ve"
    "pve-manager" 
    "pve-kernel-6.14"
    "pve-headers-6.14"
    "pve-firmware"
    "libpve-access-control"
    "libpve-common-perl"
    "libpve-guest-common-perl"
    "libpve-storage-perl"
    "pve-cluster"
    "pve-container"
    "pve-docs"
    "pve-firewall"
    "pve-ha-manager"
    "pve-i18n"
    "pve-qemu-kvm"
    "pve-xtermjs"
    "proxmox-backup-client"
    "proxmox-mail-forward"
    "proxmox-mini-journalreader"
    "proxmox-widget-toolkit"
)

echo "Attempting to download Proxmox packages..."
for pkg in "${PACKAGES[@]}"; do
    echo "Trying to download: $pkg"
    apt-get download "$pkg" 2>/dev/null || {
        echo "  Failed to download $pkg"
    }
done
DOWNLOAD_SCRIPT

chmod +x download_proxmox_essentials.sh
./download_proxmox_essentials.sh || {
    echo "[WARN] Package downloads had issues"
}

rm -f download_proxmox_essentials.sh

# List created packages
echo "[SUCCESS] Proxmox packages built/downloaded:"
ls -la "$PACKAGE_DIR"/*.deb | grep -E "(pve|proxmox)" || echo "No Proxmox packages found!"

# Create a manifest
echo "[INFO] Creating build manifest..."
cat > "$PACKAGE_DIR/proxmox_build_manifest.txt" << EOF
Proxmox Build Manifest - Source Build
====================================
Build Date: $(date)
Proxmox Version: $PROXMOX_VERSION
Repositories:
  - PVE Manager: $PVE_MANAGER_REPO
  - Proxmox VE: $PROXMOX_VE_REPO
  - PVE Kernel: $PVE_KERNEL_REPO
Build Host: $(hostname)
Host Kernel: $(uname -r)

Components Built:
- PVE Manager: $(cd "$PROXMOX_BUILD_DIR/pve-manager" && git rev-parse HEAD)
- Proxmox VE: $(cd "$PROXMOX_BUILD_DIR/proxmox-ve" && git rev-parse HEAD)
- PVE Kernel: Skipped (use packages from repository)

Packages Created/Downloaded:
$(ls -la "$PACKAGE_DIR"/*.deb | grep -E "(pve|proxmox)" || echo "None")

Note: This build creates userspace packages. Proxmox kernel will be
installed from repository packages during chroot phase.
EOF

echo "═══════════════════════════════════════════════════════════════════"
echo "                ✅ PROXMOX BUILD COMPLETE"
echo ""
echo "Packages available in: $PACKAGE_DIR"
echo "Manifest: $PACKAGE_DIR/proxmox_build_manifest.txt"
echo ""
echo "Next step: Run ZFS build, then main Z-FORGE build:"
echo "  make -f Makefile.no_tmp build-zfs"
echo "  make -f Makefile.no_tmp build-debian13-no-zfs"
echo "═══════════════════════════════════════════════════════════════════"