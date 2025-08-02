#!/bin/bash
# Enhanced ZFS userspace utilities build with optimizations
# Version: 2.0

set -euo pipefail

# Configuration
ZFS_VERSION="${ZFS_VERSION:-2.3.3}"
ZFS_SRC="${ZFS_SRC:-/usr/src/zfs-${ZFS_VERSION}}"
OUTPUT_DIR="${OUTPUT_DIR:-/opt/github/Z-FORGE/prebuilt_packages/userspace}"
BUILD_DIR="${BUILD_DIR:-/tmp/zfs-userspace-build-$$}"
LOG_FILE="${LOG_FILE:-/tmp/zfs-userspace-build-$(date +%Y%m%d_%H%M%S).log}"
DOWNLOAD_URL="https://github.com/openzfs/zfs/releases/download/zfs-${ZFS_VERSION}/zfs-${ZFS_VERSION}.tar.gz"

# Build optimization flags
OPTIMIZATION_LEVEL="${OPTIMIZATION_LEVEL:-2}" # 0=none, 1=size, 2=speed, 3=aggressive
ENABLE_LTO="${ENABLE_LTO:-true}"
ENABLE_STATIC="${ENABLE_STATIC:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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
echo "    Enhanced ZFS ${ZFS_VERSION} Userspace Build v2.0" | tee -a "$LOG_FILE"
echo "    (No Kernel Modules - Utilities Only)" | tee -a "$LOG_FILE"
echo "════════════════════════════════════════════════════════════════════" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
log "Build log: $LOG_FILE"
log "Optimization level: $OPTIMIZATION_LEVEL"
log "Link-time optimization: $ENABLE_LTO"

# Function to detect CPU features
detect_cpu_features() {
    log "Detecting CPU features for optimization..."
    
    CPU_FLAGS=""
    
    # Check for AVX support
    if grep -q "avx2" /proc/cpuinfo; then
        CPU_FLAGS="$CPU_FLAGS -mavx2"
        info "AVX2 support detected"
    elif grep -q "avx" /proc/cpuinfo; then
        CPU_FLAGS="$CPU_FLAGS -mavx"
        info "AVX support detected"
    fi
    
    # Check for SSE support
    if grep -q "sse4_2" /proc/cpuinfo; then
        CPU_FLAGS="$CPU_FLAGS -msse4.2"
        info "SSE4.2 support detected"
    fi
    
    # Check for AES-NI
    if grep -q "aes" /proc/cpuinfo; then
        CPU_FLAGS="$CPU_FLAGS -maes"
        info "AES-NI support detected"
    fi
    
    export CPU_FLAGS
}

# Function to set optimization flags
set_optimization_flags() {
    log "Setting optimization flags..."
    
    case $OPTIMIZATION_LEVEL in
        0)
            export CFLAGS="-O0 -g"
            export CXXFLAGS="-O0 -g"
            info "Debug build (no optimization)"
            ;;
        1)
            export CFLAGS="-Os -ffunction-sections -fdata-sections"
            export CXXFLAGS="-Os -ffunction-sections -fdata-sections"
            export LDFLAGS="-Wl,--gc-sections"
            info "Size optimization enabled"
            ;;
        2)
            export CFLAGS="-O2 -march=native $CPU_FLAGS"
            export CXXFLAGS="-O2 -march=native $CPU_FLAGS"
            info "Speed optimization enabled"
            ;;
        3)
            export CFLAGS="-O3 -march=native -mtune=native $CPU_FLAGS -fomit-frame-pointer"
            export CXXFLAGS="-O3 -march=native -mtune=native $CPU_FLAGS -fomit-frame-pointer"
            info "Aggressive optimization enabled"
            ;;
    esac
    
    # Add LTO if enabled
    if [ "$ENABLE_LTO" = "true" ]; then
        export CFLAGS="$CFLAGS -flto"
        export CXXFLAGS="$CXXFLAGS -flto"
        export LDFLAGS="${LDFLAGS:-} -flto"
        info "Link-time optimization enabled"
    fi
    
    # Add security hardening flags
    export CFLAGS="$CFLAGS -fstack-protector-strong -D_FORTIFY_SOURCE=2"
    export CXXFLAGS="$CXXFLAGS -fstack-protector-strong -D_FORTIFY_SOURCE=2"
    export LDFLAGS="${LDFLAGS:-} -Wl,-z,relro -Wl,-z,now"
    
    log "CFLAGS: $CFLAGS"
    log "LDFLAGS: ${LDFLAGS:-}"
}

# Function to download and extract source
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

# Function to install minimal dependencies
install_dependencies() {
    log "Installing userspace build dependencies..."
    
    # Update package lists
    sudo apt-get update || warning "Package update had issues"
    
    # Minimal dependencies for userspace
    DEPS=(
        build-essential autoconf automake libtool gawk
        libblkid-dev uuid-dev libudev-dev libssl-dev zlib1g-dev
        libaio-dev libattr1-dev python3 python3-dev
        python3-setuptools python3-cffi libffi-dev python3-packaging
        debhelper dh-python po-debconf
        libpam0g-dev libselinux1-dev libcurl4-openssl-dev
    )
    
    # Optional optimization tools
    OPT_DEPS=(
        ccache python3-sphinx python3-all-dev
    )
    
    # Install main dependencies
    for dep in "${DEPS[@]}"; do
        if ! dpkg -l | grep -q "^ii  $dep "; then
            log "Installing $dep..."
            sudo apt-get install -y "$dep" || warning "Failed to install $dep"
        fi
    done
    
    # Try to install optional dependencies
    for dep in "${OPT_DEPS[@]}"; do
        sudo apt-get install -y "$dep" 2>/dev/null || true
    done
    
    # Setup ccache if available
    if command -v ccache &> /dev/null; then
        export CC="ccache gcc"
        export CXX="ccache g++"
        info "ccache enabled for faster rebuilds"
    fi
    
    success "Dependencies installed"
}

# Function to configure userspace build
configure_userspace() {
    log "Configuring ZFS userspace build..."
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
    
    # Configure options
    CONFIGURE_OPTS=(
        --without-linux
        --with-config=user
        --prefix=/usr
        --sysconfdir=/etc
        --localstatedir=/var
        --libdir=/usr/lib
        --includedir=/usr/include
        --datarootdir=/usr/share
        --enable-systemd
        --enable-pyzfs
        --with-python=3
        --with-mounthelperdir=/sbin
    )
    
    # Add static build if requested
    if [ "$ENABLE_STATIC" = "true" ]; then
        CONFIGURE_OPTS+=("--enable-static" "--disable-shared")
        info "Static build enabled"
    fi
    
    # Configure
    log "Running configure..."
    ./configure "${CONFIGURE_OPTS[@]}" || {
        error "Configure failed"
        exit 1
    }
    
    success "Configuration complete (userspace only)"
}

# Function to build userspace utilities
build_userspace() {
    log "Building ZFS userspace utilities..."
    cd "$ZFS_SRC"
    
    # Determine optimal job count
    JOBS=$(nproc)
    if [ "$JOBS" -gt 4 ]; then
        JOBS=$((JOBS - 1))  # Leave one core free
    fi
    
    log "Building with $JOBS parallel jobs..."
    
    # Build userspace
    if make -j"$JOBS" 2>&1 | tee -a "$LOG_FILE"; then
        success "Userspace build completed successfully"
    else
        error "Build failed"
        exit 1
    fi
    
    # Run basic tests if available
    if [ -f "Makefile" ] && grep -q "^test:" Makefile; then
        log "Running basic tests..."
        make test 2>&1 | tee -a "$LOG_FILE" || warning "Some tests failed"
    fi
}

# Function to build packages
build_packages() {
    log "Building Debian userspace packages..."
    cd "$ZFS_SRC"
    
    # Create output directory
    mkdir -p "$OUTPUT_DIR"
    
    # Build userspace packages
    log "Building deb-utils packages..."
    if make deb-utils 2>&1 | tee -a "$LOG_FILE"; then
        success "Userspace packages built"
    else
        warning "Package build had issues, trying alternative method..."
        
        # Alternative: use checkinstall
        if command -v checkinstall &> /dev/null; then
            log "Using checkinstall to create package..."
            sudo checkinstall --pkgname=zfs-userspace \
                            --pkgversion="$ZFS_VERSION" \
                            --backup=no \
                            --deldoc=yes \
                            --fstrans=no \
                            --default \
                            make install || warning "checkinstall failed"
        fi
    fi
    
    # Collect packages
    log "Collecting built packages..."
    find . -maxdepth 2 -name "*.deb" -type f ! -name "*kmod*" ! -name "*dkms*" \
         -exec cp {} "$OUTPUT_DIR/" \; 2>/dev/null || true
    
    # Also check parent directory
    find .. -maxdepth 1 -name "*.deb" -type f ! -name "*kmod*" ! -name "*dkms*" \
         -exec cp {} "$OUTPUT_DIR/" \; 2>/dev/null || true
    
    # Count packages
    PACKAGE_COUNT=$(ls -1 "$OUTPUT_DIR"/*.deb 2>/dev/null | wc -l)
    
    if [ "$PACKAGE_COUNT" -eq 0 ]; then
        error "No packages were built"
        exit 1
    fi
    
    success "Built $PACKAGE_COUNT userspace packages"
}

# Function to create lightweight installer
create_installer() {
    log "Creating userspace installer script..."
    
    cat > "$OUTPUT_DIR/install_zfs_userspace.sh" << 'EOF'
#!/bin/bash
# ZFS Userspace Package Installer

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing ZFS userspace utilities from $SCRIPT_DIR..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

# Check for kernel modules
if ! lsmod | grep -q "^zfs "; then
    echo "WARNING: ZFS kernel module not loaded!"
    echo "This installer only provides userspace utilities."
    echo "You need to install kernel modules separately."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install packages
echo "Installing userspace packages..."
dpkg -i "$SCRIPT_DIR"/*.deb || apt-get install -f -y

# Verify installation
echo ""
echo "Verifying installation..."
for cmd in zfs zpool zdb; do
    if command -v $cmd &> /dev/null; then
        echo "✓ $cmd installed: $(which $cmd)"
    else
        echo "✗ $cmd not found"
    fi
done

echo ""
echo "ZFS userspace utilities installation complete!"
echo ""
echo "Note: These are userspace tools only. You still need:"
echo "  - ZFS kernel modules (zfs-dkms or distribution package)"
echo "  - Proper kernel configuration"
echo ""
echo "To check ZFS status: zpool status"
EOF
    
    chmod +x "$OUTPUT_DIR/install_zfs_userspace.sh"
    success "Installer script created"
}

# Function to optimize installed size
optimize_packages() {
    log "Optimizing package sizes..."
    
    if [ "$OPTIMIZATION_LEVEL" -ge 1 ]; then
        cd "$OUTPUT_DIR"
        
        for pkg in *.deb; do
            if [ -f "$pkg" ]; then
                log "Optimizing $pkg..."
                
                # Extract package
                dpkg-deb -x "$pkg" tmp_extract
                dpkg-deb -e "$pkg" tmp_extract/DEBIAN
                
                # Strip binaries
                find tmp_extract -type f -executable -exec strip --strip-unneeded {} \; 2>/dev/null || true
                
                # Remove docs if size optimization
                if [ "$OPTIMIZATION_LEVEL" -eq 1 ]; then
                    rm -rf tmp_extract/usr/share/doc
                    rm -rf tmp_extract/usr/share/man
                fi
                
                # Repack
                dpkg-deb -b tmp_extract "${pkg}.new"
                mv "${pkg}.new" "$pkg"
                rm -rf tmp_extract
                
                info "Optimized $(basename "$pkg")"
            fi
        done
    fi
}

# Function to generate detailed report
generate_report() {
    log "Generating build report..."
    
    REPORT_FILE="$OUTPUT_DIR/userspace_build_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "ZFS Userspace Build Report"
        echo "========================="
        echo ""
        echo "Build Configuration:"
        echo "-------------------"
        echo "Date: $(date)"
        echo "ZFS Version: $ZFS_VERSION"
        echo "System: $(uname -a)"
        echo "Distribution: $(lsb_release -d 2>/dev/null | cut -f2 || echo "Unknown")"
        echo "Optimization Level: $OPTIMIZATION_LEVEL"
        echo "Link-time Optimization: $ENABLE_LTO"
        echo "Static Build: $ENABLE_STATIC"
        echo ""
        echo "CPU Features Detected:"
        echo "---------------------"
        echo "$CPU_FLAGS"
        echo ""
        echo "Build Flags:"
        echo "-----------"
        echo "CFLAGS: ${CFLAGS:-default}"
        echo "LDFLAGS: ${LDFLAGS:-default}"
        echo ""
        echo "Packages Built:"
        echo "--------------"
        ls -lh "$OUTPUT_DIR"/*.deb 2>/dev/null || echo "No packages found"
        echo ""
        echo "Total Size: $(du -sh "$OUTPUT_DIR" | cut -f1)"
        echo ""
        echo "Package Details:"
        echo "---------------"
        for pkg in "$OUTPUT_DIR"/*.deb; do
            if [ -f "$pkg" ]; then
                echo ""
                echo "$(basename "$pkg"):"
                dpkg -I "$pkg" | grep -E "Package:|Version:|Architecture:|Description:|Installed-Size:"
                echo "  File size: $(ls -lh "$pkg" | awk '{print $5}')"
            fi
        done
        echo ""
        echo "Build Log: $LOG_FILE"
    } > "$REPORT_FILE"
    
    success "Build report saved to $REPORT_FILE"
}

# Main execution
main() {
    detect_cpu_features
    set_optimization_flags
    download_source
    install_dependencies
    configure_userspace
    build_userspace
    build_packages
    optimize_packages
    create_installer
    generate_report
    
    # Summary
    echo ""
    echo "════════════════════════════════════════════════════════════════════"
    echo "✅ ZFS Userspace Build Complete!"
    echo "════════════════════════════════════════════════════════════════════"
    echo ""
    echo "📦 Packages built: $PACKAGE_COUNT (userspace only)"
    echo "📁 Location: $OUTPUT_DIR"
    echo "📝 Build log: $LOG_FILE"
    echo "📋 Build report: $OUTPUT_DIR/userspace_build_report_*.txt"
    echo "⚡ Optimization: Level $OPTIMIZATION_LEVEL"
    echo ""
    echo "To install userspace utilities:"
    echo "  sudo $OUTPUT_DIR/install_zfs_userspace.sh"
    echo ""
    echo "Remember: You still need ZFS kernel modules!"
    echo "  - Install zfs-dkms from your distribution, or"
    echo "  - Build kernel modules separately"
    echo ""
}

# Parse command line options
while [[ $# -gt 0 ]]; do
    case $1 in
        --optimize)
            OPTIMIZATION_LEVEL="$2"
            shift 2
            ;;
        --no-lto)
            ENABLE_LTO=false
            shift
            ;;
        --static)
            ENABLE_STATIC=true
            shift
            ;;
        --version)
            ZFS_VERSION="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --optimize <0-3>    Set optimization level (default: 2)"
            echo "  --no-lto           Disable link-time optimization"
            echo "  --static           Build static binaries"
            echo "  --version <ver>    Set ZFS version (default: 2.3.3)"
            echo "  --help             Show this help"
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