#!/bin/bash
# Enhanced ZFS build script with xtables loop fix
# Version: 2.1

set -euo pipefail

# Configuration
ZFS_VERSION="${ZFS_VERSION:-2.3.3}"
ZFS_SRC="${ZFS_SRC:-/usr/src/zfs-${ZFS_VERSION}}"
OUTPUT_DIR="${OUTPUT_DIR:-/opt/github/Z-FORGE/prebuilt_packages}"
BUILD_DIR="${BUILD_DIR:-/tmp/zfs-build-$$}"
LOG_FILE="${LOG_FILE:-/tmp/zfs-build-$(date +%Y%m%d_%H%M%S).log}"
DOWNLOAD_URL="https://github.com/openzfs/zfs/releases/download/zfs-${ZFS_VERSION}/zfs-${ZFS_VERSION}.tar.gz"

# Build method selection
BUILD_METHOD="${BUILD_METHOD:-makefile}" # makefile or debian

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
echo "    Enhanced ZFS ${ZFS_VERSION} Build Script v2.1 (xtables fix)" | tee -a "$LOG_FILE"
echo "════════════════════════════════════════════════════════════════════" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
log "Build log: $LOG_FILE"
log "Build method: $BUILD_METHOD"

# Function to check system requirements
check_requirements() {
    log "Checking system requirements..."
    
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
    
    # Core build dependencies - MINIMAL SET to avoid xtables issues
    DEPS=(
        build-essential
        autoconf
        automake
        libtool
        gawk
        alien
        fakeroot
        libblkid-dev
        uuid-dev
        libudev-dev
        libssl-dev
        zlib1g-dev
        libaio-dev
        libattr1-dev
        libelf-dev
        python3
        python3-dev
        python3-setuptools
        python3-cffi
        libffi-dev
    )
    
    # Install main dependencies
    for dep in "${DEPS[@]}"; do
        if ! dpkg -l | grep -q "^ii  $dep "; then
            log "Installing $dep..."
            sudo apt-get install -y "$dep" || warning "Failed to install $dep"
        fi
    done
    
    # Only install debian packaging tools if using debian method
    if [ "$BUILD_METHOD" = "debian" ]; then
        DEBIAN_DEPS=(
            debhelper
            dh-python
            po-debconf
            python3-all-dev
            python3-sphinx
        )
        
        for dep in "${DEBIAN_DEPS[@]}"; do
            sudo apt-get install -y "$dep" 2>/dev/null || warning "Optional package $dep not available"
        done
    fi
    
    success "Dependencies installed"
}

# Function to build using Makefile method (avoids xtables loop)
build_with_makefile() {
    log "Building ZFS using Makefile method..."
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
    
    # Configure with minimal options
    log "Configuring build..."
    ./configure \
        --prefix=/usr \
        --with-linux=/usr/src/linux-headers-$(uname -r) \
        --with-linux-obj=/usr/src/linux-headers-$(uname -r) \
        --disable-debug \
        --disable-debuginfo || {
        error "Configure failed"
        exit 1
    }
    
    # Build
    log "Building ZFS..."
    make -j$(nproc) || {
        error "Build failed"
        exit 1
    }
    
    # Create packages using checkinstall or alien
    log "Creating packages..."
    
    # Create staging directory
    STAGE_DIR="$BUILD_DIR/staging"
    mkdir -p "$STAGE_DIR"
    
    # Install to staging
    make install DESTDIR="$STAGE_DIR" || {
        error "Staging install failed"
        exit 1
    }
    
    # Create simple tarball package
    cd "$STAGE_DIR"
    tar -czf "$OUTPUT_DIR/zfs-${ZFS_VERSION}-$(uname -r).tar.gz" .
    
    success "Created tarball package"
}

# Function to build Debian packages (original method)
build_debian_packages() {
    log "Building Debian packages..."
    cd "$ZFS_SRC"
    
    # Create output directory
    mkdir -p "$OUTPUT_DIR"
    
    # Try to build packages without triggering xtables loop
    log "Building with deb-utils only (avoiding deb-dkms to prevent loops)..."
    
    # Set timeout for make to prevent infinite loops
    timeout 1800 make -j$(nproc) deb-utils 2>&1 | tee -a "$LOG_FILE" || {
        warning "deb-utils build timed out or failed"
        return 1
    }
    
    # Collect packages
    log "Collecting built packages..."
    find . -maxdepth 2 -name "*.deb" -type f -exec cp {} "$OUTPUT_DIR/" \; 2>/dev/null || true
    find .. -maxdepth 1 -name "*.deb" -type f -exec cp {} "$OUTPUT_DIR/" \; 2>/dev/null || true
    
    # Count packages
    PACKAGE_COUNT=$(ls -1 "$OUTPUT_DIR"/*.deb 2>/dev/null | wc -l)
    
    if [ "$PACKAGE_COUNT" -eq 0 ]; then
        warning "No Debian packages were built"
        return 1
    fi
    
    success "Built $PACKAGE_COUNT packages"
    return 0
}

# Alternative: Build kernel modules separately
build_kmod_only() {
    log "Building kernel modules only..."
    cd "$ZFS_SRC"
    
    # Configure for kernel only
    ./configure \
        --with-linux=/usr/src/linux-headers-$(uname -r) \
        --with-linux-obj=/usr/src/linux-headers-$(uname -r) \
        --with-config=kernel || {
        error "Kernel configure failed"
        exit 1
    }
    
    # Build modules
    make -j$(nproc) || {
        error "Module build failed"
        exit 1
    }
    
    # Install modules to temporary location
    KMOD_DIR="$BUILD_DIR/kmods"
    mkdir -p "$KMOD_DIR"
    make install DESTDIR="$KMOD_DIR" || {
        error "Module install failed"
        exit 1
    }
    
    # Package modules
    cd "$KMOD_DIR"
    tar -czf "$OUTPUT_DIR/zfs-kmod-${ZFS_VERSION}-$(uname -r).tar.gz" .
    
    success "Kernel modules packaged"
}

# Function to create installer script
create_installer() {
    log "Creating installer script..."
    
    if [ -f "$OUTPUT_DIR/zfs-${ZFS_VERSION}-$(uname -r).tar.gz" ]; then
        # Installer for tarball
        cat > "$OUTPUT_DIR/install_zfs_tarball.sh" << 'EOF'
#!/bin/bash
# ZFS Tarball Installer

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZFS_TARBALL=$(ls -1 "$SCRIPT_DIR"/zfs-*.tar.gz | head -1)

if [ -z "$ZFS_TARBALL" ]; then
    echo "No ZFS tarball found!"
    exit 1
fi

echo "Installing ZFS from $ZFS_TARBALL..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

# Extract to root
echo "Extracting files..."
tar -xzf "$ZFS_TARBALL" -C / || {
    echo "Extraction failed!"
    exit 1
}

# Update library cache
ldconfig

# Load ZFS module
echo "Loading ZFS module..."
modprobe zfs || echo "Module load failed (may need reboot)"

echo "ZFS installation complete!"
echo "Run 'zfs version' to verify installation"
EOF
        chmod +x "$OUTPUT_DIR/install_zfs_tarball.sh"
    fi
    
    # Keep original installer for .deb files if they exist
    if ls "$OUTPUT_DIR"/*.deb >/dev/null 2>&1; then
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

# Install packages
dpkg -i "$SCRIPT_DIR"/*.deb || apt-get install -f -y

# Load ZFS module
modprobe zfs || true

echo "ZFS installation complete!"
EOF
        chmod +x "$OUTPUT_DIR/install_zfs.sh"
    fi
    
    success "Installer script(s) created"
}

# Main execution
main() {
    check_requirements
    download_source
    install_dependencies
    
    # Try different build methods
    case "$BUILD_METHOD" in
        makefile)
            build_with_makefile
            ;;
        debian)
            if ! build_debian_packages; then
                warning "Debian package build failed, falling back to makefile method"
                build_with_makefile
            fi
            ;;
        both)
            build_with_makefile
            build_kmod_only
            ;;
        *)
            error "Unknown build method: $BUILD_METHOD"
            exit 1
            ;;
    esac
    
    create_installer
    
    # Summary
    echo ""
    echo "════════════════════════════════════════════════════════════════════"
    echo "✅ ZFS Build Complete!"
    echo "════════════════════════════════════════════════════════════════════"
    echo ""
    echo "📁 Output location: $OUTPUT_DIR"
    echo "📝 Build log: $LOG_FILE"
    echo ""
    
    # List what was built
    echo "Built files:"
    ls -la "$OUTPUT_DIR"/ 2>/dev/null | grep -E "\.(deb|tar\.gz)$" || echo "No packages found"
    echo ""
    
    if [ -f "$OUTPUT_DIR/install_zfs_tarball.sh" ]; then
        echo "To install from tarball:"
        echo "  sudo $OUTPUT_DIR/install_zfs_tarball.sh"
    fi
    
    if [ -f "$OUTPUT_DIR/install_zfs.sh" ]; then
        echo "To install from .deb packages:"
        echo "  sudo $OUTPUT_DIR/install_zfs.sh"
    fi
    echo ""
}

# Parse command line options
while [[ $# -gt 0 ]]; do
    case $1 in
        --method)
            if [ -z "${2:-}" ]; then
                error "Option --method requires an argument"
                exit 1
            fi
            BUILD_METHOD="$2"
            shift 2
            ;;
        --version)
            if [ -z "${2:-}" ]; then
                error "Option --version requires an argument"
                exit 1
            fi
            ZFS_VERSION="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --method <makefile|debian|both>  Build method (default: makefile)"
            echo "  --version <ver>                  ZFS version (default: 2.3.3)"
            echo "  --help                           Show this help"
            echo ""
            echo "Build methods:"
            echo "  makefile - Direct make install to tarball (avoids xtables loop)"
            echo "  debian   - Try to build .deb packages (may hit xtables issue)"
            echo "  both     - Build both tarball and kernel modules"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main function
main "$@"