#!/bin/bash
# Z-FORGE ZFS Cross-Compilation Script
# Builds ZFS 2.3.4 on Ubuntu for Debian/Proxmox targets
# Creates prebuilt packages that can be installed in chroot

set -euo pipefail

# Configuration
ZFS_VERSION="2.3.4"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BUILD_DIR="${PROJECT_ROOT}/zfs-cross-build"
OUTPUT_DIR="${PROJECT_ROOT}/prebuilt_packages/zfs-${ZFS_VERSION}"
DEBIAN_KERNEL="6.14.0-15-generic"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_section() { echo -e "${BLUE}==== $1 ====${NC}"; }

# Function to check prerequisites
check_prerequisites() {
    log_section "Checking Prerequisites"
    
    local missing_deps=()
    
    # Check for required packages
    for pkg in build-essential autoconf automake libtool alien \
               libblkid-dev libssl-dev libudev-dev libaio-dev \
               zlib1g-dev uuid-dev libattr1-dev libelf-dev \
               python3-all-dev python3-cffi python3-setuptools \
               python3-packaging dkms debhelper dh-python \
               po-debconf python3-all-dbg python3-dev \
               libpam0g-dev; do
        if ! dpkg -l | grep -q "^ii.*$pkg"; then
            missing_deps+=("$pkg")
        fi
    done
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        log_warning "Missing dependencies: ${missing_deps[*]}"
        log_info "Installing missing dependencies..."
        sudo apt-get update
        sudo apt-get install -y "${missing_deps[@]}"
    else
        log_info "All dependencies satisfied"
    fi
}

# Function to download Debian kernel headers
download_debian_kernel_headers() {
    log_section "Downloading Debian Kernel Headers"
    
    local headers_dir="${BUILD_DIR}/debian-headers"
    mkdir -p "${headers_dir}"
    
    cd "${headers_dir}"
    
    # Download Debian kernel headers for target kernel
    log_info "Downloading Debian kernel headers for ${DEBIAN_KERNEL}..."
    
    # Try to download from Debian repository
    local kernel_headers_urls=(
        "http://deb.debian.org/debian/pool/main/l/linux/linux-headers-${DEBIAN_KERNEL}_all.deb"
        "http://deb.debian.org/debian/pool/main/l/linux/linux-headers-${DEBIAN_KERNEL}_amd64.deb"
        "http://deb.debian.org/debian/pool/main/l/linux/linux-headers-common_all.deb"
    )
    
    for url in "${kernel_headers_urls[@]}"; do
        local filename=$(basename "$url")
        if [ ! -f "$filename" ]; then
            log_info "Downloading $filename..."
            wget "$url" 2>/dev/null || log_warning "Could not download $filename"
        fi
    done
    
    # Extract headers
    log_info "Extracting kernel headers..."
    for deb in *.deb; do
        [ -f "$deb" ] && dpkg-deb -x "$deb" .
    done
    
    # Find the kernel headers path
    local kernel_headers_path
    kernel_headers_path=$(find . -type d -name "linux-headers-${DEBIAN_KERNEL}" | head -1)
    
    if [ -z "$kernel_headers_path" ]; then
        log_warning "Debian kernel headers not found, will build userspace only"
        echo ""
    else
        log_info "Kernel headers found at: $kernel_headers_path"
        echo "$(pwd)/$kernel_headers_path"
    fi
}

# Function to download and extract ZFS source
prepare_zfs_source() {
    log_section "Preparing ZFS ${ZFS_VERSION} Source"
    
    mkdir -p "${BUILD_DIR}"
    cd "${BUILD_DIR}"
    
    # Download ZFS if needed
    if [ ! -f "zfs-${ZFS_VERSION}.tar.gz" ]; then
        log_info "Downloading ZFS ${ZFS_VERSION}..."
        wget "https://github.com/openzfs/zfs/releases/download/zfs-${ZFS_VERSION}/zfs-${ZFS_VERSION}.tar.gz"
    fi
    
    # Extract
    log_info "Extracting ZFS source..."
    rm -rf "zfs-${ZFS_VERSION}"
    tar -xzf "zfs-${ZFS_VERSION}.tar.gz"
    
    cd "zfs-${ZFS_VERSION}"
}

# Function to build ZFS userspace tools
build_zfs_userspace() {
    log_section "Building ZFS Userspace Tools"
    
    cd "${BUILD_DIR}/zfs-${ZFS_VERSION}"
    
    # Configure for userspace only (no kernel modules)
    log_info "Configuring ZFS userspace build..."
    ./configure \
        --prefix=/usr \
        --libdir=/usr/lib/x86_64-linux-gnu \
        --includedir=/usr/include \
        --datarootdir=/usr/share \
        --with-config=user \
        --with-systemdunitdir=/lib/systemd/system \
        --with-systemdpresetdir=/lib/systemd/system-preset \
        --with-systemdgeneratordir=/lib/systemd/system-generators \
        --enable-systemd \
        --enable-pyzfs \
        --disable-static
    
    # Build userspace
    log_info "Building userspace tools (this may take a while)..."
    make -j$(nproc)
    
    # Create Debian packages for userspace
    log_info "Creating userspace Debian packages..."
    make deb-utils
    
    # Copy packages to output
    mkdir -p "${OUTPUT_DIR}/userspace"
    cp ../*.deb "${OUTPUT_DIR}/userspace/" 2>/dev/null || true
    
    log_info "Userspace packages created successfully"
}

# Function to build ZFS kernel modules for Debian
build_zfs_kernel_modules() {
    log_section "Building ZFS Kernel Modules for Debian"
    
    local kernel_headers_path="$1"
    
    if [ -z "$kernel_headers_path" ] || [ ! -d "$kernel_headers_path" ]; then
        log_warning "Skipping kernel module build - no headers available"
        return 0
    fi
    
    cd "${BUILD_DIR}/zfs-${ZFS_VERSION}"
    
    # Clean previous build
    make distclean 2>/dev/null || true
    
    # Configure for kernel modules
    log_info "Configuring ZFS kernel module build for Debian kernel..."
    ./configure \
        --prefix=/usr \
        --with-linux="$kernel_headers_path" \
        --with-linux-obj="$kernel_headers_path" \
        --with-config=kernel \
        --enable-linux-builtin=no
    
    # Build kernel modules
    log_info "Building kernel modules..."
    make -j$(nproc)
    
    # Create kernel module packages
    log_info "Creating kernel module Debian packages..."
    make deb-kmod
    
    # Copy packages to output
    mkdir -p "${OUTPUT_DIR}/kernel-modules"
    cp ../*kmod*.deb "${OUTPUT_DIR}/kernel-modules/" 2>/dev/null || true
    
    log_info "Kernel module packages created successfully"
}

# Function to build Proxmox-specific packages
build_proxmox_packages() {
    log_section "Building Proxmox-Compatible Packages"
    
    cd "${BUILD_DIR}/zfs-${ZFS_VERSION}"
    
    # Clean and reconfigure for Proxmox
    make distclean 2>/dev/null || true
    
    # Proxmox uses specific ZFS configuration
    log_info "Configuring for Proxmox VE..."
    ./configure \
        --prefix=/usr \
        --with-config=user \
        --with-systemdunitdir=/lib/systemd/system \
        --with-systemdpresetdir=/lib/systemd/system-preset \
        --with-systemdgeneratordir=/lib/systemd/system-generators \
        --enable-systemd \
        --enable-pyzfs \
        --disable-static \
        --with-zfsexecdir=/usr/lib/zfs \
        --with-mounthelperdir=/usr/sbin
    
    # Build with Proxmox optimizations
    CFLAGS="-O2 -fPIC" make -j$(nproc)
    
    # Create Proxmox packages
    make deb-utils
    
    # Copy to Proxmox output
    mkdir -p "${OUTPUT_DIR}/proxmox"
    cp ../*.deb "${OUTPUT_DIR}/proxmox/" 2>/dev/null || true
    
    log_info "Proxmox packages created successfully"
}

# Function to create installation script
create_install_script() {
    log_section "Creating Installation Script"
    
    cat > "${OUTPUT_DIR}/install_prebuilt_zfs.sh" <<'EOF'
#!/bin/bash
# Install prebuilt ZFS packages in chroot environment

set -euo pipefail

PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_TYPE="${1:-all}"  # all, userspace, kernel, proxmox

echo "Installing prebuilt ZFS packages..."

case "$INSTALL_TYPE" in
    userspace)
        echo "Installing userspace packages only..."
        dpkg -i "${PACKAGE_DIR}/userspace/"*.deb || apt-get -f install -y
        ;;
    kernel)
        echo "Installing kernel modules only..."
        dpkg -i "${PACKAGE_DIR}/kernel-modules/"*.deb || apt-get -f install -y
        ;;
    proxmox)
        echo "Installing Proxmox-compatible packages..."
        dpkg -i "${PACKAGE_DIR}/proxmox/"*.deb || apt-get -f install -y
        ;;
    all|*)
        echo "Installing all packages..."
        dpkg -i "${PACKAGE_DIR}/userspace/"*.deb || apt-get -f install -y
        [ -d "${PACKAGE_DIR}/kernel-modules" ] && \
            dpkg -i "${PACKAGE_DIR}/kernel-modules/"*.deb || apt-get -f install -y
        ;;
esac

# Configure ZFS services
systemctl enable zfs-import-cache
systemctl enable zfs-import-scan
systemctl enable zfs-mount
systemctl enable zfs-share
systemctl enable zfs-zed
systemctl enable zfs.target

echo "ZFS installation complete!"
EOF
    
    chmod +x "${OUTPUT_DIR}/install_prebuilt_zfs.sh"
    log_info "Installation script created"
}

# Function to create build info
create_build_info() {
    log_section "Creating Build Information"
    
    cat > "${OUTPUT_DIR}/BUILD_INFO.txt" <<EOF
ZFS Cross-Compilation Build Information
========================================
Build Date: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
Build Host: $(uname -a)
ZFS Version: ${ZFS_VERSION}
Target System: Debian/Proxmox
Target Kernel: ${DEBIAN_KERNEL}

Package Types Built:
- Userspace tools (architecture-specific, kernel-independent)
- Kernel modules (if headers available)
- Proxmox-optimized packages

Installation Instructions:
1. Copy this directory to the chroot environment
2. Run: ./install_prebuilt_zfs.sh [all|userspace|kernel|proxmox]

Notes:
- Userspace packages work across kernel versions
- Kernel modules must match target kernel exactly
- Proxmox packages optimized for PVE environment
EOF
    
    log_info "Build information created"
}

# Main execution
main() {
    log_section "Z-FORGE ZFS Cross-Compilation for Debian/Proxmox"
    log_info "Building ZFS ${ZFS_VERSION} on Ubuntu for Debian targets"
    
    # Check prerequisites
    check_prerequisites
    
    # Prepare build directory
    rm -rf "${BUILD_DIR}"
    mkdir -p "${BUILD_DIR}"
    mkdir -p "${OUTPUT_DIR}"
    
    # Download Debian kernel headers (optional for kernel modules)
    kernel_headers_path=$(download_debian_kernel_headers)
    
    # Prepare ZFS source
    prepare_zfs_source
    
    # Build userspace tools
    build_zfs_userspace
    
    # Build kernel modules if headers available
    if [ -n "$kernel_headers_path" ]; then
        build_zfs_kernel_modules "$kernel_headers_path"
    fi
    
    # Build Proxmox-specific packages
    build_proxmox_packages
    
    # Create installation script
    create_install_script
    
    # Create build info
    create_build_info
    
    log_section "Build Complete!"
    log_info "Prebuilt packages available at: ${OUTPUT_DIR}"
    log_info ""
    log_info "Package types created:"
    [ -d "${OUTPUT_DIR}/userspace" ] && log_info "  - Userspace tools: ${OUTPUT_DIR}/userspace/"
    [ -d "${OUTPUT_DIR}/kernel-modules" ] && log_info "  - Kernel modules: ${OUTPUT_DIR}/kernel-modules/"
    [ -d "${OUTPUT_DIR}/proxmox" ] && log_info "  - Proxmox packages: ${OUTPUT_DIR}/proxmox/"
    log_info ""
    log_info "To use in Z-FORGE build:"
    log_info "  1. Packages are automatically detected by build system"
    log_info "  2. Or manually install in chroot: ./install_prebuilt_zfs.sh"
}

# Run main function
main "$@"