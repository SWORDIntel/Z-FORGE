#!/bin/bash
# Complete ZFS 2.3.3 Build Workflow
# Builds ZFS outside chroot, then installs into Z-FORGE chroot
# Version: 1.0

set -euo pipefail

# Configuration
ZFS_VERSION="${ZFS_VERSION:-2.3.3}"
WORKSPACE_DIR="${WORKSPACE_DIR:-$HOME/zforge_workspace}"
BUILD_DIR="${BUILD_DIR:-$WORKSPACE_DIR/zfs_build}"
PACKAGES_DIR="${PACKAGES_DIR:-/opt/github/Z-FORGE/prebuilt_packages}"
CHROOT_PATH="${CHROOT_PATH:-$WORKSPACE_DIR/chroot}"
LOG_FILE="${LOG_FILE:-$WORKSPACE_DIR/zfs_complete_build_$(date +%Y%m%d_%H%M%S).log}"

# Build options
BUILD_TYPE="${BUILD_TYPE:-full}" # full, userspace, kernel
OPTIMIZE="${OPTIMIZE:-2}"
SKIP_BUILD="${SKIP_BUILD:-false}"
SKIP_CHROOT="${SKIP_CHROOT:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $*" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${CYAN}[INFO]${NC} $*" | tee -a "$LOG_FILE"
}

phase() {
    echo -e "\n${MAGENTA}═══ $* ═══${NC}\n" | tee -a "$LOG_FILE"
}

# Header
cat << EOF | tee "$LOG_FILE"
════════════════════════════════════════════════════════════════════
    Complete ZFS ${ZFS_VERSION} Build & Install Workflow
════════════════════════════════════════════════════════════════════
Build Type: $BUILD_TYPE
Optimization Level: $OPTIMIZE
Workspace: $WORKSPACE_DIR
Packages: $PACKAGES_DIR
Chroot: $CHROOT_PATH
Log: $LOG_FILE
════════════════════════════════════════════════════════════════════
EOF

# Check if running as root when needed
check_root() {
    if [ "$EUID" -ne 0 ]; then 
        error "This operation requires root privileges"
        info "Please run with sudo"
        exit 1
    fi
}

# Phase 1: Prepare build environment
prepare_build_env() {
    phase "Phase 1: Preparing build environment"
    
    # Create directories
    log "Creating workspace directories..."
    mkdir -p "$BUILD_DIR"
    mkdir -p "$PACKAGES_DIR"
    mkdir -p "$WORKSPACE_DIR"
    
    # Check disk space (need at least 5GB)
    local available_space=$(df "$WORKSPACE_DIR" | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 5242880 ]; then
        error "Insufficient disk space. Need at least 5GB free"
        exit 1
    fi
    
    # Install build dependencies
    log "Installing build dependencies..."
    if [ "$EUID" -eq 0 ] || sudo -n true 2>/dev/null; then
        sudo apt-get update || warning "apt update had issues"
        
        # Core build dependencies
        local deps=(
            build-essential autoconf automake libtool gawk alien
            libblkid-dev uuid-dev libudev-dev libssl-dev zlib1g-dev
            libaio-dev libattr1-dev libelf-dev python3 python3-dev
            python3-setuptools python3-cffi libffi-dev python3-packaging
            debhelper dh-python po-debconf python3-all-dev python3-sphinx
            libpam0g-dev libselinux1-dev libcurl4-openssl-dev
            linux-headers-$(uname -r)
        )
        
        for dep in "${deps[@]}"; do
            sudo apt-get install -y "$dep" 2>/dev/null || warning "Failed to install $dep"
        done
    else
        warning "Cannot install dependencies without sudo access"
        info "Please install build dependencies manually"
    fi
    
    success "Build environment prepared"
}

# Phase 2: Build ZFS from source
build_zfs() {
    phase "Phase 2: Building ZFS $ZFS_VERSION from source"
    
    cd "$BUILD_DIR"
    
    # Download source if needed
    if [ ! -f "zfs-${ZFS_VERSION}.tar.gz" ]; then
        log "Downloading ZFS source..."
        wget --progress=bar:force \
            "https://github.com/openzfs/zfs/releases/download/zfs-${ZFS_VERSION}/zfs-${ZFS_VERSION}.tar.gz" || {
            error "Failed to download ZFS source"
            exit 1
        }
    fi
    
    # Extract source
    log "Extracting source..."
    rm -rf "zfs-${ZFS_VERSION}"
    tar -xzf "zfs-${ZFS_VERSION}.tar.gz"
    cd "zfs-${ZFS_VERSION}"
    
    # Run autogen
    log "Running autogen.sh..."
    sh autogen.sh
    
    # Configure based on build type
    log "Configuring build (type: $BUILD_TYPE)..."
    case "$BUILD_TYPE" in
        full)
            ./configure \
                --with-linux=/usr/src/linux-headers-$(uname -r) \
                --with-linux-obj=/usr/src/linux-headers-$(uname -r) \
                --prefix=/usr \
                --sysconfdir=/etc \
                --localstatedir=/var \
                --libdir=/usr/lib \
                --includedir=/usr/include \
                --with-config=all \
                --enable-systemd \
                --enable-pyzfs \
                --with-python=3
            ;;
        userspace)
            ./configure \
                --without-linux \
                --with-config=user \
                --prefix=/usr \
                --sysconfdir=/etc \
                --localstatedir=/var \
                --libdir=/usr/lib \
                --includedir=/usr/include \
                --enable-systemd \
                --enable-pyzfs \
                --with-python=3
            ;;
        kernel)
            ./configure \
                --with-linux=/usr/src/linux-headers-$(uname -r) \
                --with-linux-obj=/usr/src/linux-headers-$(uname -r) \
                --with-config=kernel
            ;;
    esac
    
    # Set optimization flags
    case "$OPTIMIZE" in
        0) export CFLAGS="-O0 -g" ;;
        1) export CFLAGS="-Os" ;;
        2) export CFLAGS="-O2 -march=native" ;;
        3) export CFLAGS="-O3 -march=native -mtune=native" ;;
    esac
    
    # Build
    log "Building ZFS (this will take a while)..."
    make -j$(nproc) || {
        error "Build failed"
        exit 1
    }
    
    # Build packages
    log "Building Debian packages..."
    case "$BUILD_TYPE" in
        full)
            make deb-utils deb-dkms || make deb
            ;;
        userspace)
            make deb-utils
            ;;
        kernel)
            make deb-kmod || make deb-dkms
            ;;
    esac
    
    # Collect packages
    log "Collecting packages..."
    find . -name "*.deb" -exec cp {} "$PACKAGES_DIR/" \;
    
    # Count packages
    local pkg_count=$(ls -1 "$PACKAGES_DIR"/*.deb 2>/dev/null | wc -l)
    success "Built $pkg_count packages"
}

# Phase 3: Bootstrap chroot environment
bootstrap_chroot() {
    phase "Phase 3: Bootstrapping chroot environment"
    
    check_root
    
    if [ -d "$CHROOT_PATH" ]; then
        warning "Chroot already exists at $CHROOT_PATH"
        read -p "Delete and recreate? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log "Removing existing chroot..."
            rm -rf "$CHROOT_PATH"
        else
            log "Using existing chroot"
            return 0
        fi
    fi
    
    log "Creating new chroot with debootstrap..."
    
    # Ensure debootstrap is installed
    if ! command -v debootstrap &> /dev/null; then
        apt-get install -y debootstrap
    fi
    
    # Bootstrap Debian Trixie
    debootstrap --arch=amd64 \
                --include=apt,apt-utils,bash,systemd,systemd-sysv \
                trixie "$CHROOT_PATH" http://deb.debian.org/debian || {
        error "Debootstrap failed"
        exit 1
    }
    
    # Configure chroot
    log "Configuring chroot..."
    
    # Setup APT sources
    cat > "$CHROOT_PATH/etc/apt/sources.list" << EOF
deb http://deb.debian.org/debian trixie main contrib non-free non-free-firmware
deb-src http://deb.debian.org/debian trixie main contrib non-free non-free-firmware
deb http://security.debian.org/debian-security trixie-security main contrib non-free non-free-firmware
EOF
    
    # Copy DNS config
    cp /etc/resolv.conf "$CHROOT_PATH/etc/resolv.conf"
    
    # Create basic directories
    mkdir -p "$CHROOT_PATH"/{proc,sys,dev,dev/pts,run}
    
    success "Chroot bootstrapped"
}

# Phase 4: Install ZFS into chroot
install_zfs_chroot() {
    phase "Phase 4: Installing ZFS into chroot"
    
    check_root
    
    # Mount necessary filesystems
    log "Mounting filesystems..."
    mount -t proc proc "$CHROOT_PATH/proc" 2>/dev/null || true
    mount -t sysfs sys "$CHROOT_PATH/sys" 2>/dev/null || true
    mount -o bind /dev "$CHROOT_PATH/dev" 2>/dev/null || true
    mount -t devpts devpts "$CHROOT_PATH/dev/pts" 2>/dev/null || true
    
    # Copy packages to chroot
    log "Copying ZFS packages to chroot..."
    mkdir -p "$CHROOT_PATH/tmp/zfs-packages"
    cp "$PACKAGES_DIR"/*.deb "$CHROOT_PATH/tmp/zfs-packages/" || {
        error "No packages found to install"
        exit 1
    }
    
    # Install packages
    log "Installing ZFS packages in chroot..."
    
    # Create installation script
    cat > "$CHROOT_PATH/tmp/install_zfs.sh" << 'INSTALL_SCRIPT'
#!/bin/bash
set -e

echo "Updating package lists..."
apt-get update

echo "Installing dependencies..."
apt-get install -y --no-install-recommends \
    libaio1 libblkid1 libcurl4 libelf1 libnvpair3linux \
    libpam0g libselinux1 libssl3 libudev1 libuutil3linux \
    libzfs4linux libzpool5linux python3 python3-cffi

echo "Installing ZFS packages..."
cd /tmp/zfs-packages

# Install in correct order
# 1. Libraries first
dpkg -i libnvpair*linux_*.deb libuutil*linux_*.deb 2>/dev/null || true
dpkg -i libzfs*linux_*.deb libzpool*linux_*.deb 2>/dev/null || true

# 2. Utilities
dpkg -i zfs-zed_*.deb zfsutils-linux_*.deb 2>/dev/null || true

# 3. Kernel modules (if present)
if ls *-kmod*.deb 1> /dev/null 2>&1; then
    dpkg -i *-kmod*.deb 2>/dev/null || true
fi

if ls *-dkms*.deb 1> /dev/null 2>&1; then
    dpkg -i *-dkms*.deb 2>/dev/null || true
fi

# 4. Python bindings
dpkg -i python*-pyzfs_*.deb 2>/dev/null || true

# Fix any dependency issues
apt-get install -f -y

echo "Configuring ZFS services..."
# Create necessary directories
mkdir -p /etc/zfs
touch /etc/zfs/zpool.cache

# Enable services (will activate on real boot)
systemctl enable zfs-import-cache.service 2>/dev/null || true
systemctl enable zfs-mount.service 2>/dev/null || true
systemctl enable zfs.target 2>/dev/null || true

echo "ZFS installation complete!"
INSTALL_SCRIPT
    
    chmod +x "$CHROOT_PATH/tmp/install_zfs.sh"
    
    # Run installation
    chroot "$CHROOT_PATH" /tmp/install_zfs.sh || {
        error "ZFS installation failed"
        exit 1
    }
    
    # Cleanup
    rm -rf "$CHROOT_PATH/tmp/zfs-packages"
    rm -f "$CHROOT_PATH/tmp/install_zfs.sh"
    
    # Unmount filesystems
    umount "$CHROOT_PATH"/{dev/pts,dev,sys,proc} 2>/dev/null || true
    
    success "ZFS installed in chroot"
}

# Phase 5: Verify installation
verify_installation() {
    phase "Phase 5: Verifying installation"
    
    check_root
    
    # Mount filesystems
    mount -t proc proc "$CHROOT_PATH/proc" 2>/dev/null || true
    mount -t sysfs sys "$CHROOT_PATH/sys" 2>/dev/null || true
    mount -o bind /dev "$CHROOT_PATH/dev" 2>/dev/null || true
    
    # Check installed packages
    log "Checking installed ZFS packages..."
    chroot "$CHROOT_PATH" dpkg -l | grep -E "zfs|zpool" || warning "No ZFS packages found"
    
    # Check binaries
    log "Checking ZFS binaries..."
    for cmd in zfs zpool zdb; do
        if chroot "$CHROOT_PATH" which "$cmd" &>/dev/null; then
            info "✓ $cmd found at $(chroot "$CHROOT_PATH" which "$cmd")"
        else
            warning "✗ $cmd not found"
        fi
    done
    
    # Check version
    log "Checking ZFS version..."
    chroot "$CHROOT_PATH" /bin/bash -c "zfs version 2>/dev/null || echo 'ZFS module not loaded (normal in chroot)'"
    
    # Unmount
    umount "$CHROOT_PATH"/{dev,sys,proc} 2>/dev/null || true
    
    success "Verification complete"
}

# Generate summary report
generate_summary() {
    local report_file="$WORKSPACE_DIR/zfs_build_summary_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "ZFS Build & Install Summary"
        echo "=========================="
        echo ""
        echo "Date: $(date)"
        echo "ZFS Version: $ZFS_VERSION"
        echo "Build Type: $BUILD_TYPE"
        echo "Optimization: Level $OPTIMIZE"
        echo ""
        echo "Workspace: $WORKSPACE_DIR"
        echo "Packages: $PACKAGES_DIR"
        echo "Chroot: $CHROOT_PATH"
        echo ""
        echo "Packages built:"
        ls -la "$PACKAGES_DIR"/*.deb 2>/dev/null || echo "No packages found"
        echo ""
        echo "Chroot size: $(du -sh "$CHROOT_PATH" 2>/dev/null | cut -f1)"
        echo ""
        echo "To use this chroot with Z-FORGE:"
        echo "1. Set CHROOT_PATH=$CHROOT_PATH"
        echo "2. Run your Z-FORGE build"
        echo ""
        echo "To manually enter chroot:"
        echo "sudo chroot $CHROOT_PATH /bin/bash"
    } | tee "$report_file"
    
    info "Summary saved to: $report_file"
}

# Main execution
main() {
    # Parse command line options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --type)
                BUILD_TYPE="$2"
                shift 2
                ;;
            --optimize)
                OPTIMIZE="$2"
                shift 2
                ;;
            --workspace)
                WORKSPACE_DIR="$2"
                shift 2
                ;;
            --chroot)
                CHROOT_PATH="$2"
                shift 2
                ;;
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --skip-chroot)
                SKIP_CHROOT=true
                shift
                ;;
            --help)
                cat << EOF
Usage: $0 [options]

Options:
    --type <full|userspace|kernel>  Build type (default: full)
    --optimize <0-3>                 Optimization level (default: 2)
    --workspace <path>               Workspace directory
    --chroot <path>                  Chroot path
    --skip-build                     Skip ZFS build (use existing packages)
    --skip-chroot                    Skip chroot bootstrap
    --help                           Show this help

Example:
    # Full build and install
    sudo $0

    # Userspace only, high optimization
    sudo $0 --type userspace --optimize 3

    # Use existing packages, just bootstrap chroot
    sudo $0 --skip-build
EOF
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Execute phases
    if [ "$SKIP_BUILD" = "false" ]; then
        prepare_build_env
        build_zfs
    else
        info "Skipping ZFS build phase"
    fi
    
    if [ "$SKIP_CHROOT" = "false" ]; then
        bootstrap_chroot
        install_zfs_chroot
        verify_installation
    else
        info "Skipping chroot phases"
    fi
    
    generate_summary
    
    # Final message
    echo ""
    echo "════════════════════════════════════════════════════════════════════"
    echo "✅ Complete ZFS Build & Install Workflow Finished!"
    echo "════════════════════════════════════════════════════════════════════"
    echo ""
    echo "📦 Packages: $PACKAGES_DIR"
    echo "🏗️  Chroot: $CHROOT_PATH"
    echo "📝 Log: $LOG_FILE"
    echo ""
    echo "Next steps:"
    echo "1. Review the summary report"
    echo "2. Test chroot: sudo chroot $CHROOT_PATH /bin/bash"
    echo "3. Use with Z-FORGE: export CHROOT_PATH=$CHROOT_PATH"
    echo ""
}

# Check for basic requirements
if ! command -v debootstrap &> /dev/null && [ "$SKIP_CHROOT" = "false" ]; then
    error "debootstrap is required but not installed"
    info "Install with: sudo apt-get install debootstrap"
    exit 1
fi

# Run main function
main "$@"