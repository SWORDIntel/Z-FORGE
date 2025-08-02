#!/bin/bash
# Enhanced ZFS build script with better error handling and features
# Version: 2.0

set -euo pipefail

# Configuration
ZFS_VERSION="${ZFS_VERSION:-2.3.3}"
ZFS_SRC="${ZFS_SRC:-/usr/src/zfs-${ZFS_VERSION}}"
OUTPUT_DIR="${OUTPUT_DIR:-/opt/github/Z-FORGE/prebuilt_packages}"
BUILD_DIR="${BUILD_DIR:-/tmp/zfs-build-$$}"
LOG_FILE="${LOG_FILE:-/tmp/zfs-build-$(date +%Y%m%d_%H%M%S).log}"
DOWNLOAD_URL="https://github.com/openzfs/zfs/releases/download/zfs-${ZFS_VERSION}/zfs-${ZFS_VERSION}.tar.gz"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Cleanup function
cleanup() {
    if [ -d "$BUILD_DIR" ]; then
        log "Cleaning up build directory..."
        rm -rf "$BUILD_DIR"
    fi
}

trap cleanup EXIT

# Header
echo "════════════════════════════════════════════════════════════════════" | tee "$LOG_FILE"
echo "    Enhanced ZFS ${ZFS_VERSION} Build Script v2.0" | tee -a "$LOG_FILE"
echo "════════════════════════════════════════════════════════════════════" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
log "Build log: $LOG_FILE"

# Function to check system requirements
check_requirements() {
    log "Checking system requirements..."
    
    # Check if running as sudo
    if [ "$EUID" -eq 0 ]; then
        warning "Running as root. Some operations may have different behavior."
    fi
    
    # Check kernel headers
    KERNEL_VERSION=$(uname -r)
    if [ ! -d "/usr/src/linux-headers-${KERNEL_VERSION}" ]; then
        error "Kernel headers not found for ${KERNEL_VERSION}"
        log "Installing kernel headers..."
        sudo apt-get update && sudo apt-get install -y linux-headers-${KERNEL_VERSION} || {
            error "Failed to install kernel headers"
            exit 1
        }
    fi
    
    # Check available disk space (need at least 2GB)
    AVAILABLE_SPACE=$(df /tmp | awk 'NR==2 {print $4}')
    if [ "$AVAILABLE_SPACE" -lt 2097152 ]; then
        error "Insufficient disk space. Need at least 2GB free in /tmp"
        exit 1
    fi
    
    success "System requirements checked"
}

# Function to download and extract ZFS source
download_source() {
    if [ ! -d "$ZFS_SRC" ]; then
        log "ZFS source not found at $ZFS_SRC"
        
        # Create temporary directory
        mkdir -p "$BUILD_DIR"
        cd "$BUILD_DIR"
        
        # Download source
        if [ ! -f "zfs-${ZFS_VERSION}.tar.gz" ]; then
            log "Downloading ZFS ${ZFS_VERSION} source..."
            wget --progress=bar:force "$DOWNLOAD_URL" || {
                error "Failed to download ZFS source"
                exit 1
            }
        fi
        
        # Extract to /usr/src
        log "Extracting source to /usr/src..."
        sudo tar -xzf "zfs-${ZFS_VERSION}.tar.gz" -C /usr/src/ || {
            error "Failed to extract ZFS source"
            exit 1
        }
        
        success "ZFS source ready at $ZFS_SRC"
    else
        log "Using existing ZFS source at $ZFS_SRC"
    fi
}

# Function to install build dependencies
install_dependencies() {
    log "Installing build dependencies..."
    
    # Update package lists
    sudo apt-get update || warning "Package update had issues"
    
    # Core build dependencies
    DEPS=(
        build-essential autoconf automake libtool gawk
        libblkid-dev uuid-dev libudev-dev libssl-dev zlib1g-dev
        libaio-dev libattr1-dev libelf-dev python3 python3-dev
        python3-setuptools python3-cffi libffi-dev python3-packaging
        debhelper dh-python po-debconf python3-all-dev python3-sphinx
        libpam0g-dev libselinux1-dev libcurl4-openssl-dev
    )
    
    # Try to install DKMS support
    DKMS_DEPS=(
        dkms debhelper-compat dh-sequence-dkms
    )
    
    # Install main dependencies
    for dep in "${DEPS[@]}"; do
        if ! dpkg -l | grep -q "^ii  $dep "; then
            log "Installing $dep..."
            sudo apt-get install -y "$dep" || warning "Failed to install $dep"
        fi
    done
    
    # Try to install DKMS dependencies
    for dep in "${DKMS_DEPS[@]}"; do
        sudo apt-get install -y "$dep" 2>/dev/null || warning "DKMS package $dep not available"
    done
    
    success "Dependencies installed"
}

# Function to configure build
configure_build() {
    log "Configuring ZFS build..."
    cd "$ZFS_SRC"
    
    # Clean any previous builds
    if [ -f Makefile ]; then
        log "Cleaning previous build..."
        make distclean 2>/dev/null || true
    fi
    
    # Run autogen
    log "Running autogen.sh..."
    sh autogen.sh || {
        error "autogen.sh failed"
        exit 1
    }
    
    # Detect Linux source/headers
    LINUX_SRC="/usr/src/linux-headers-$(uname -r)"
    if [ ! -d "$LINUX_SRC" ]; then
        LINUX_SRC="/lib/modules/$(uname -r)/build"
    fi
    
    log "Using Linux source: $LINUX_SRC"
    
    # Configure with optimal settings
    log "Running configure..."
    ./configure \
        --with-linux="$LINUX_SRC" \
        --with-linux-obj="$LINUX_SRC" \
        --prefix=/usr \
        --sysconfdir=/etc \
        --localstatedir=/var \
        --libdir=/usr/lib \
        --includedir=/usr/include \
        --with-config=all \
        --enable-systemd \
        --enable-pyzfs \
        --with-python=3 \
        --with-mounthelperdir=/sbin || {
        error "Configure failed"
        exit 1
    }
    
    success "Configuration complete"
}

# Function to build ZFS
build_zfs() {
    log "Building ZFS (this may take a while)..."
    cd "$ZFS_SRC"
    
    # Determine optimal job count
    JOBS=$(nproc)
    if [ "$JOBS" -gt 4 ]; then
        JOBS=$((JOBS - 1))  # Leave one core free
    fi
    
    log "Building with $JOBS parallel jobs..."
    
    # First try to build everything
    if make -j"$JOBS" 2>&1 | tee -a "$LOG_FILE"; then
        success "Build completed successfully"
    else
        warning "Full build failed, trying userspace only..."
        make clean
        make -j"$JOBS" deb-utils 2>&1 | tee -a "$LOG_FILE" || {
            error "Build failed"
            exit 1
        }
    fi
}

# Function to build packages
build_packages() {
    log "Building Debian packages..."
    cd "$ZFS_SRC"
    
    # Create output directory
    mkdir -p "$OUTPUT_DIR"
    
    # Try different package building methods
    PACKAGES_BUILT=false
    
    # Method 1: make deb
    if ! $PACKAGES_BUILT; then
        log "Trying: make deb-utils deb-dkms..."
        if make -j$(nproc) deb-utils deb-dkms 2>&1 | tee -a "$LOG_FILE"; then
            PACKAGES_BUILT=true
        else
            warning "Full package build failed"
        fi
    fi
    
    # Method 2: just userspace packages
    if ! $PACKAGES_BUILT; then
        log "Trying: make deb-utils..."
        if make -j$(nproc) deb-utils 2>&1 | tee -a "$LOG_FILE"; then
            PACKAGES_BUILT=true
        else
            warning "Userspace package build failed"
        fi
    fi
    
    # Method 3: dpkg-buildpackage
    if ! $PACKAGES_BUILT; then
        log "Trying: dpkg-buildpackage..."
        if dpkg-buildpackage -b -uc -us 2>&1 | tee -a "$LOG_FILE"; then
            PACKAGES_BUILT=true
        else
            warning "dpkg-buildpackage failed"
        fi
    fi
    
    # Collect packages
    log "Collecting built packages..."
    find . -maxdepth 2 -name "*.deb" -type f -exec cp {} "$OUTPUT_DIR/" \; 2>/dev/null || true
    
    # Also check parent directory
    find .. -maxdepth 1 -name "*.deb" -type f -exec cp {} "$OUTPUT_DIR/" \; 2>/dev/null || true
    
    # Count packages
    PACKAGE_COUNT=$(ls -1 "$OUTPUT_DIR"/*.deb 2>/dev/null | wc -l)
    
    if [ "$PACKAGE_COUNT" -eq 0 ]; then
        error "No packages were built"
        exit 1
    fi
    
    success "Built $PACKAGE_COUNT packages"
}

# Function to create installer script
create_installer() {
    log "Creating installer script..."
    
    cat > "$OUTPUT_DIR/install_zfs.sh" << 'EOF'
#!/bin/bash
# ZFS Package Installer

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing ZFS packages from $SCRIPT_DIR..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

# Install packages in correct order
KMOD_PKGS=$(ls -1 "$SCRIPT_DIR"/*-kmod*.deb 2>/dev/null || true)
UTIL_PKGS=$(ls -1 "$SCRIPT_DIR"/*.deb 2>/dev/null | grep -v kmod || true)

# Install kernel modules first
if [ -n "$KMOD_PKGS" ]; then
    echo "Installing kernel modules..."
    dpkg -i $KMOD_PKGS || apt-get install -f -y
fi

# Install utilities
if [ -n "$UTIL_PKGS" ]; then
    echo "Installing utilities..."
    dpkg -i $UTIL_PKGS || apt-get install -f -y
fi

# Load ZFS module
echo "Loading ZFS module..."
modprobe zfs || true

# Enable services
echo "Enabling ZFS services..."
systemctl enable zfs-import-cache.service || true
systemctl enable zfs-mount.service || true
systemctl enable zfs-import.target || true

echo "ZFS installation complete!"
echo "Run 'zfs version' to verify installation"
EOF
    
    chmod +x "$OUTPUT_DIR/install_zfs.sh"
    success "Installer script created"
}

# Function to generate build report
generate_report() {
    log "Generating build report..."
    
    REPORT_FILE="$OUTPUT_DIR/build_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "ZFS Build Report"
        echo "================"
        echo ""
        echo "Build Date: $(date)"
        echo "ZFS Version: $ZFS_VERSION"
        echo "Kernel Version: $(uname -r)"
        echo "Distribution: $(lsb_release -d | cut -f2)"
        echo ""
        echo "Packages Built:"
        echo "--------------"
        ls -la "$OUTPUT_DIR"/*.deb 2>/dev/null || echo "No packages found"
        echo ""
        echo "Package Contents:"
        echo "----------------"
        for pkg in "$OUTPUT_DIR"/*.deb; do
            if [ -f "$pkg" ]; then
                echo ""
                echo "$(basename "$pkg"):"
                dpkg -I "$pkg" | grep -E "Package:|Version:|Architecture:|Description:"
            fi
        done
        echo ""
        echo "Build Log: $LOG_FILE"
    } > "$REPORT_FILE"
    
    success "Build report saved to $REPORT_FILE"
}

# Main execution
main() {
    check_requirements
    download_source
    install_dependencies
    configure_build
    build_zfs
    build_packages
    create_installer
    generate_report
    
    # Summary
    echo ""
    echo "════════════════════════════════════════════════════════════════════"
    echo "✅ ZFS Build Complete!"
    echo "════════════════════════════════════════════════════════════════════"
    echo ""
    echo "📦 Packages built: $PACKAGE_COUNT"
    echo "📁 Location: $OUTPUT_DIR"
    echo "📝 Build log: $LOG_FILE"
    echo "📋 Build report: $OUTPUT_DIR/build_report_*.txt"
    echo ""
    echo "To install ZFS:"
    echo "  sudo $OUTPUT_DIR/install_zfs.sh"
    echo ""
    echo "To use in Z-FORGE:"
    echo "  The build system will automatically detect these packages"
    echo ""
}

# Run main function
main "$@"