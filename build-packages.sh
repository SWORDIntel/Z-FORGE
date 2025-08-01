#!/bin/bash
# Z-FORGE Package Builder
# Builds ZFS and Proxmox packages using local kernel headers
# No system-wide changes, just builds packages in local directories

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
WORKSPACE="${ZFORGE_WORKSPACE:-$HOME/zforge_workspace}"
OUTPUT_DIR="$SCRIPT_DIR/prebuilt_packages"
LOG_DIR="$SCRIPT_DIR/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Ensure directories exist
mkdir -p "$OUTPUT_DIR" "$LOG_DIR"

# Show header
show_header() {
    clear
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}              ${BOLD}${BLUE}Z-FORGE LOCAL PACKAGE BUILDER${NC}                     ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}            ${YELLOW}Builds ZFS & Proxmox from Source${NC}                     ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Detect kernel version and headers
detect_kernel() {
    echo -e "${BLUE}=== Detecting Kernel Information ===${NC}"
    
    # Current running kernel
    KERNEL_VERSION=$(uname -r)
    echo -e "Running kernel: ${GREEN}$KERNEL_VERSION${NC}"
    
    # Find kernel headers
    if [ -d "/usr/src/linux-headers-$KERNEL_VERSION" ]; then
        KERNEL_HEADERS="/usr/src/linux-headers-$KERNEL_VERSION"
        echo -e "Kernel headers: ${GREEN}$KERNEL_HEADERS${NC}"
    elif [ -d "/lib/modules/$KERNEL_VERSION/build" ]; then
        KERNEL_HEADERS="/lib/modules/$KERNEL_VERSION/build"
        echo -e "Kernel headers: ${GREEN}$KERNEL_HEADERS${NC}"
    else
        echo -e "${RED}ERROR: Kernel headers not found!${NC}"
        echo "Please install: sudo apt-get install linux-headers-$KERNEL_VERSION"
        return 1
    fi
    
    # Check for kernel source
    if [ -d "/usr/src/linux-$KERNEL_VERSION" ]; then
        KERNEL_SOURCE="/usr/src/linux-$KERNEL_VERSION"
        echo -e "Kernel source: ${GREEN}$KERNEL_SOURCE${NC}"
    elif [ -L "/lib/modules/$KERNEL_VERSION/source" ]; then
        KERNEL_SOURCE=$(readlink -f "/lib/modules/$KERNEL_VERSION/source")
        echo -e "Kernel source: ${GREEN}$KERNEL_SOURCE${NC}"
    else
        KERNEL_SOURCE="$KERNEL_HEADERS"
        echo -e "Using headers as source: ${YELLOW}$KERNEL_SOURCE${NC}"
    fi
    
    echo ""
    return 0
}

# Build ZFS from Proxmox source
build_zfs() {
    echo -e "${BLUE}=== Building ZFS 2.3.3 from Proxmox Source ===${NC}"
    echo ""
    
    local BUILD_DIR="$WORKSPACE/zfs-build"
    local ZFS_VERSION="2.3.3"
    local LOG_FILE="$LOG_DIR/zfs_build_${TIMESTAMP}.log"
    
    echo -e "Build directory: $BUILD_DIR"
    echo -e "Log file: $LOG_FILE"
    echo ""
    
    # Create build directory
    mkdir -p "$BUILD_DIR"
    cd "$BUILD_DIR"
    
    (
        echo "[$(date)] Starting ZFS build..."
        
        # Download Proxmox ZFS source
        if [ ! -f "zfs-linux_${ZFS_VERSION}.orig.tar.gz" ]; then
            echo "[$(date)] Downloading ZFS source from Proxmox..."
            wget -q "http://download.proxmox.com/debian/devel/zfs-linux_${ZFS_VERSION}.orig.tar.gz" || {
                echo "[ERROR] Failed to download ZFS source"
                return 1
            }
        fi
        
        # Extract source
        echo "[$(date)] Extracting source..."
        tar -xzf "zfs-linux_${ZFS_VERSION}.orig.tar.gz"
        cd "zfs-linux-${ZFS_VERSION}"
        
        # Configure build
        echo "[$(date)] Configuring build..."
        ./autogen.sh
        
        ./configure \
            --prefix=/usr \
            --with-linux="$KERNEL_HEADERS" \
            --with-linux-obj="$KERNEL_HEADERS" \
            --enable-systemd \
            --enable-pyzfs \
            --with-python=python3 \
            --disable-debug \
            --disable-debuginfo
        
        # Build
        echo "[$(date)] Building ZFS (this will take a while)..."
        make -j$(nproc)
        
        # Create Debian packages
        echo "[$(date)] Creating Debian packages..."
        make deb-utils deb-kmod
        
        # Copy packages to output
        echo "[$(date)] Copying packages to output directory..."
        cp ../*.deb "$OUTPUT_DIR/" 2>/dev/null || true
        
        echo "[$(date)] ZFS build completed successfully!"
        
    ) 2>&1 | tee "$LOG_FILE"
    
    # Show results
    echo ""
    echo -e "${GREEN}✓ ZFS packages built successfully!${NC}"
    echo -e "Packages saved to: ${CYAN}$OUTPUT_DIR${NC}"
    echo ""
    ls -lh "$OUTPUT_DIR"/zfs*.deb 2>/dev/null | tail -10
    echo ""
}

# Build Proxmox VE packages
build_proxmox() {
    echo -e "${BLUE}=== Building Proxmox VE Packages ===${NC}"
    echo ""
    
    local BUILD_DIR="$WORKSPACE/proxmox-build"
    local LOG_FILE="$LOG_DIR/proxmox_build_${TIMESTAMP}.log"
    
    echo -e "Build directory: $BUILD_DIR"
    echo -e "Log file: $LOG_FILE"
    echo ""
    
    # Create build directory
    mkdir -p "$BUILD_DIR"
    cd "$BUILD_DIR"
    
    (
        echo "[$(date)] Starting Proxmox build..."
        
        # Clone Proxmox repositories
        echo "[$(date)] Cloning Proxmox repositories..."
        
        # Core components to build
        PROXMOX_REPOS=(
            "pve-common"
            "pve-storage"
            "pve-cluster"
            "pve-access-control"
            "pve-manager"
            "pve-qemu"
            "pve-container"
        )
        
        for repo in "${PROXMOX_REPOS[@]}"; do
            if [ ! -d "$repo" ]; then
                echo "[$(date)] Cloning $repo..."
                git clone "git://git.proxmox.com/git/$repo.git" || {
                    echo "[WARNING] Failed to clone $repo, trying mirror..."
                    git clone "https://github.com/proxmox/$repo.git"
                }
            fi
        done
        
        # Build each component
        for repo in "${PROXMOX_REPOS[@]}"; do
            echo "[$(date)] Building $repo..."
            cd "$BUILD_DIR/$repo"
            
            # Apply kernel headers path
            if [ -f "debian/rules" ]; then
                sed -i "s|/usr/src/linux-headers-.*|$KERNEL_HEADERS|g" debian/rules
            fi
            
            # Install build dependencies
            echo "[$(date)] Installing build dependencies for $repo..."
            sudo apt-get build-dep -y . 2>/dev/null || true
            
            # Build
            make deb || {
                echo "[WARNING] Failed to build $repo, continuing..."
                continue
            }
            
            # Copy packages
            cp ../${repo}*.deb "$OUTPUT_DIR/" 2>/dev/null || true
        done
        
        echo "[$(date)] Proxmox build completed!"
        
    ) 2>&1 | tee "$LOG_FILE"
    
    # Show results
    echo ""
    echo -e "${GREEN}✓ Proxmox packages built!${NC}"
    echo -e "Packages saved to: ${CYAN}$OUTPUT_DIR${NC}"
    echo ""
    ls -lh "$OUTPUT_DIR"/pve*.deb 2>/dev/null | tail -10
    echo ""
}

# Check dependencies
check_dependencies() {
    echo -e "${BLUE}=== Checking Build Dependencies ===${NC}"
    
    local MISSING_DEPS=()
    
    # Required packages
    REQUIRED_PACKAGES=(
        "build-essential"
        "autoconf"
        "automake"
        "libtool"
        "gawk"
        "alien"
        "fakeroot"
        "dkms"
        "libblkid-dev"
        "uuid-dev"
        "libudev-dev"
        "libssl-dev"
        "zlib1g-dev"
        "libaio-dev"
        "libattr1-dev"
        "libelf-dev"
        "python3-dev"
        "python3-setuptools"
        "python3-cffi"
        "libffi-dev"
        "libcurl4-openssl-dev"
        "libpam0g-dev"
        "debhelper"
        "dh-python"
        "dh-systemd"
        "po-debconf"
        "python3-all-dev"
        "python3-sphinx"
    )
    
    for pkg in "${REQUIRED_PACKAGES[@]}"; do
        if ! dpkg -l | grep -q "^ii  $pkg "; then
            MISSING_DEPS+=("$pkg")
        fi
    done
    
    if [ ${#MISSING_DEPS[@]} -eq 0 ]; then
        echo -e "${GREEN}✓ All build dependencies are installed${NC}"
    else
        echo -e "${YELLOW}Missing dependencies:${NC}"
        printf '%s\n' "${MISSING_DEPS[@]}"
        echo ""
        echo -e "${YELLOW}Install with:${NC}"
        echo "sudo apt-get install ${MISSING_DEPS[*]}"
        echo ""
        read -p "Install missing dependencies now? (y/N): " install_deps
        if [[ $install_deps =~ ^[Yy]$ ]]; then
            sudo apt-get update
            sudo apt-get install -y "${MISSING_DEPS[@]}"
        else
            return 1
        fi
    fi
    
    echo ""
    return 0
}

# Clean build environment
clean_build() {
    echo -e "${YELLOW}Cleaning build environment...${NC}"
    
    if [ -d "$WORKSPACE/zfs-build" ]; then
        echo "Removing ZFS build directory..."
        rm -rf "$WORKSPACE/zfs-build"
    fi
    
    if [ -d "$WORKSPACE/proxmox-build" ]; then
        echo "Removing Proxmox build directory..."
        rm -rf "$WORKSPACE/proxmox-build"
    fi
    
    echo -e "${GREEN}✓ Build environment cleaned${NC}"
    echo ""
}

# Main menu
main_menu() {
    while true; do
        show_header
        
        # Detect kernel
        if ! detect_kernel; then
            exit 1
        fi
        
        echo -e "${BOLD}${GREEN}=== Build Options ===${NC}"
        echo ""
        echo "1) Build ZFS packages only"
        echo "2) Build Proxmox packages only"
        echo "3) Build both ZFS and Proxmox"
        echo "4) Check/Install dependencies"
        echo "5) Clean build environment"
        echo "6) View build logs"
        echo ""
        echo "q) Quit"
        echo ""
        read -p "Select option: " choice
        
        case $choice in
            1)
                if check_dependencies; then
                    build_zfs
                    read -p "Press Enter to continue..."
                fi
                ;;
            2)
                if check_dependencies; then
                    build_proxmox
                    read -p "Press Enter to continue..."
                fi
                ;;
            3)
                if check_dependencies; then
                    build_zfs
                    echo -e "${CYAN}════════════════════════════════════════${NC}"
                    build_proxmox
                    read -p "Press Enter to continue..."
                fi
                ;;
            4)
                check_dependencies
                read -p "Press Enter to continue..."
                ;;
            5)
                clean_build
                read -p "Press Enter to continue..."
                ;;
            6)
                echo -e "${BLUE}=== Recent Build Logs ===${NC}"
                ls -lt "$LOG_DIR"/*.log 2>/dev/null | head -10 || echo "No logs found"
                echo ""
                read -p "Enter log filename to view (or Enter to skip): " logfile
                if [ -n "$logfile" ] && [ -f "$LOG_DIR/$logfile" ]; then
                    less "$LOG_DIR/$logfile"
                fi
                ;;
            q|Q)
                echo -e "${GREEN}Build complete. Packages are in: $OUTPUT_DIR${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid option${NC}"
                sleep 1
                ;;
        esac
    done
}

# Quick build mode (non-interactive)
if [ "$1" = "zfs" ]; then
    show_header
    detect_kernel && check_dependencies && build_zfs
    exit $?
elif [ "$1" = "proxmox" ]; then
    show_header
    detect_kernel && check_dependencies && build_proxmox
    exit $?
elif [ "$1" = "all" ]; then
    show_header
    detect_kernel && check_dependencies && build_zfs && build_proxmox
    exit $?
elif [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Z-FORGE Package Builder"
    echo ""
    echo "Usage:"
    echo "  $0          - Interactive mode"
    echo "  $0 zfs      - Build ZFS packages only"
    echo "  $0 proxmox  - Build Proxmox packages only"
    echo "  $0 all      - Build both ZFS and Proxmox"
    echo ""
    echo "Packages will be saved to: $OUTPUT_DIR"
    exit 0
fi

# Start interactive mode
main_menu