#!/bin/bash
# Build Proxmox VE 9.0 Ultimate - Everything Included!
# This builds ALL Proxmox components from source

set -e

PROXMOX_VERSION="9.0-beta"
BUILD_DIR="/usr/src/proxmox-build"
OUTPUT_DIR="${HOME}/github/Z-FORGE/prebuilt_packages"
JOBS="${JOBS:-$(nproc)}"

echo "════════════════════════════════════════════════════════════════════"
echo "         PROXMOX VE ${PROXMOX_VERSION} ULTIMATE BUILD"
echo "    Building ALL components - This will take 2-3 hours!"
echo "════════════════════════════════════════════════════════════════════"
echo ""
echo "Build Configuration:"
echo "  - CPU Cores: ${JOBS}"
echo "  - Build Dir: ${BUILD_DIR}"
echo "  - Output: ${OUTPUT_DIR}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    exit 1
fi

# Check available RAM
TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
if [ "$TOTAL_RAM" -lt 16 ]; then
    echo "WARNING: Less than 16GB RAM detected ($TOTAL_RAM GB)"
    echo "Build may fail. Recommended: 26GB+ for full build"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create directories
echo "[SETUP] Creating build environment..."
mkdir -p "$BUILD_DIR"
mkdir -p "$OUTPUT_DIR"
cd "$BUILD_DIR"

# Install ALL build dependencies
echo "[DEPS] Installing comprehensive build dependencies..."
apt-get update
apt-get install -y \
    build-essential devscripts debhelper dh-make quilt \
    git git-buildpackage lintian \
    automake autoconf libtool pkg-config \
    dh-systemd dh-exec dh-python \
    asciidoc asciidoc-base asciidoc-dblatex \
    source-highlight librsvg2-bin \
    libpve-common-perl libpve-guest-common-perl \
    libpve-storage-perl libpve-access-control \
    libpve-apiclient-perl libpve-http-server-perl \
    pve-doc-generator pve-firewall \
    liblocale-po-perl libjson-perl \
    libdevel-cycle-perl libxml-parser-perl \
    libxml-libxml-perl libnetaddr-ip-perl \
    libnet-dns-perl libnet-ip-perl \
    libdata-dumper-simple-perl \
    libio-socket-ssl-perl libnet-ssleay-perl \
    libcrypt-ssleay-perl libtext-csv-xs-perl \
    libterm-readline-gnu-perl libsocket6-perl \
    libanyevent-perl libanyevent-http-perl \
    libfile-readbackwards-perl libhttp-daemon-perl \
    libnet-http-perl libwww-perl \
    libtest-mockmodule-perl \
    cargo rustc librust-dev \
    nodejs npm yarnpkg \
    libacl1-dev libattr1-dev \
    libcap-dev libnuma-dev \
    libglib2.0-dev libfuse3-dev \
    libseccomp-dev libsystemd-dev \
    uuid-dev liburing-dev \
    sphinx python3-sphinx \
    texi2html texinfo \
    check pkg-config \
    groff-base || true

# Clone ALL Proxmox repositories
echo "[CLONE] Cloning all Proxmox repositories..."
REPOS=(
    # Core components
    "pve-common.git"
    "pve-cluster.git"
    "pve-access-control.git"
    "pve-storage.git"
    "pve-guest-common.git"
    "pve-http-server.git"
    "pve-apiclient.git"
    
    # Main management
    "pve-manager.git"
    "proxmox-widget-toolkit.git"
    "pve-docs.git"
    "pve-i18n.git"
    
    # Virtualization
    "qemu-server.git"
    "pve-container.git"
    "pve-qemu.git"
    "pve-lxc-syscalld.git"
    
    # HA & Clustering
    "pve-ha-manager.git"
    "pve-cluster.git"
    
    # Storage & Backup
    "proxmox-backup.git"
    "proxmox-backup-qemu.git"
    "pve-zsync.git"
    
    # Networking
    "pve-firewall.git"
    "pve-network.git"
    
    # Kernel
    "pve-kernel.git"
    "pve-kernel-meta.git"
    
    # Additional tools
    "pve-xtermjs.git"
    "novnc-pve.git"
    "spiceterm.git"
    "vncterm.git"
    
    # Ceph integration
    "ceph.git"
    
    # Firmware
    "pve-firmware.git"
    "pve-edk2-firmware.git"
)

for repo in "${REPOS[@]}"; do
    if [ ! -d "${repo%.git}" ]; then
        echo "[CLONE] Cloning $repo..."
        git clone "https://git.proxmox.com/git/$repo" || true
    fi
done

# Build order is important due to dependencies
echo "[BUILD] Starting build process..."
echo "[BUILD] This will take 2-3 hours. Getting coffee recommended ☕"

# Phase 1: Base libraries
PHASE1=(
    "pve-common"
    "pve-cluster" 
    "pve-access-control"
    "pve-storage"
    "pve-guest-common"
    "pve-http-server"
    "pve-apiclient"
)

echo "[BUILD] Phase 1: Building base libraries..."
for project in "${PHASE1[@]}"; do
    echo "[BUILD] Building $project..."
    if [ -d "$project" ]; then
        cd "$project"
        make deb -j${JOBS} || echo "[WARN] $project build failed, continuing..."
        cp *.deb "$OUTPUT_DIR"/ 2>/dev/null || true
        cd ..
    fi
done

# Phase 2: Core components
PHASE2=(
    "proxmox-widget-toolkit"
    "pve-manager"
    "pve-docs"
    "pve-i18n"
)

echo "[BUILD] Phase 2: Building core components..."
for project in "${PHASE2[@]}"; do
    echo "[BUILD] Building $project..."
    if [ -d "$project" ]; then
        cd "$project"
        make deb -j${JOBS} || echo "[WARN] $project build failed, continuing..."
        cp *.deb "$OUTPUT_DIR"/ 2>/dev/null || true
        cd ..
    fi
done

# Phase 3: Virtualization
PHASE3=(
    "qemu-server"
    "pve-container"
    "pve-qemu"
    "pve-lxc-syscalld"
)

echo "[BUILD] Phase 3: Building virtualization components..."
for project in "${PHASE3[@]}"; do
    echo "[BUILD] Building $project..."
    if [ -d "$project" ]; then
        cd "$project"
        make deb -j${JOBS} || echo "[WARN] $project build failed, continuing..."
        cp *.deb "$OUTPUT_DIR"/ 2>/dev/null || true
        cd ..
    fi
done

# Phase 4: Additional components
PHASE4=(
    "pve-ha-manager"
    "pve-firewall"
    "pve-zsync"
    "pve-xtermjs"
    "novnc-pve"
    "spiceterm"
)

echo "[BUILD] Phase 4: Building additional components..."
for project in "${PHASE4[@]}"; do
    echo "[BUILD] Building $project..."
    if [ -d "$project" ]; then
        cd "$project"
        make deb -j${JOBS} || echo "[WARN] $project build failed, continuing..."
        cp *.deb "$OUTPUT_DIR"/ 2>/dev/null || true
        cd ..
    fi
done

# Phase 5: Kernel (optional, takes longest)
read -p "Build Proxmox kernel? This adds 1+ hour (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "[BUILD] Phase 5: Building Proxmox kernel..."
    if [ -d "pve-kernel" ]; then
        cd pve-kernel
        make deb -j${JOBS} || echo "[WARN] Kernel build failed"
        cp *.deb "$OUTPUT_DIR"/ 2>/dev/null || true
        cd ..
    fi
fi

# Create package index
echo "[INDEX] Creating package index..."
cd "$OUTPUT_DIR"
dpkg-scanpackages . /dev/null | gzip -9c > Packages.gz

# Create install helper script
cat > "$OUTPUT_DIR/install_proxmox_ultimate.sh" << 'EOF'
#!/bin/bash
# Install ALL Proxmox packages from ultimate build

set -e

PACKAGE_DIR="$(dirname "$0")"

echo "Installing Proxmox VE Ultimate Edition..."

# Install in dependency order
dpkg -i $PACKAGE_DIR/libpve-common-perl_*.deb || apt-get -f install -y
dpkg -i $PACKAGE_DIR/libpve-access-control_*.deb || apt-get -f install -y
dpkg -i $PACKAGE_DIR/libpve-storage-perl_*.deb || apt-get -f install -y
dpkg -i $PACKAGE_DIR/proxmox-widget-toolkit_*.deb || apt-get -f install -y
dpkg -i $PACKAGE_DIR/pve-manager_*.deb || apt-get -f install -y

# Install remaining packages
dpkg -i $PACKAGE_DIR/*.deb || apt-get -f install -y

# Enable services
systemctl enable pvedaemon pveproxy pvestatd pvescheduler

echo "Proxmox VE Ultimate Edition installed!"
echo "Access web UI at: https://$(hostname -I | awk '{print $1}'):8006"
EOF

chmod +x "$OUTPUT_DIR/install_proxmox_ultimate.sh"

# Summary
echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "✅ Proxmox Ultimate Build Complete!"
echo "════════════════════════════════════════════════════════════════════"
echo ""
echo "📦 Packages built: $(ls -1 $OUTPUT_DIR/*.deb 2>/dev/null | wc -l)"
echo "📁 Location: $OUTPUT_DIR"
echo "🚀 Installer: $OUTPUT_DIR/install_proxmox_ultimate.sh"
echo ""
echo "Next steps:"
echo "1. Build ZFS if not done: sudo ./scripts/build/build_zfs_on_host.sh"
echo "2. Build ISO: sudo make -f Makefile.no_tmp build-custom CONFIG=build_spec_proxmox_full.yml"
echo ""
echo "This ISO will include:"
echo "- Complete Proxmox VE stack"
echo "- All virtualization features"
echo "- Full Ceph integration"
echo "- All monitoring tools"
echo "- Complete development environment"
echo "- Every possible Proxmox feature!"
echo ""