#!/bin/bash
# Z-FORGE Quick Environment Builder
# Builds ZFS and Proxmox in the chroot environment using local kernel headers
# This is a wrapper that sets up the environment and runs the build scripts

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Set up environment
export ZFORGE_WORKSPACE="${ZFORGE_WORKSPACE:-$HOME/zforge_workspace}"
export CHROOT_PATH="$ZFORGE_WORKSPACE/chroot"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}          Z-FORGE QUICK ENVIRONMENT PACKAGE BUILDER               ${BLUE}║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Detect kernel version
KERNEL_VERSION=$(uname -r)
echo -e "Host kernel: ${GREEN}$KERNEL_VERSION${NC}"

# Find kernel headers on host
if [ -d "/usr/src/linux-headers-$KERNEL_VERSION" ]; then
    HOST_KERNEL_HEADERS="/usr/src/linux-headers-$KERNEL_VERSION"
elif [ -d "/lib/modules/$KERNEL_VERSION/build" ]; then
    HOST_KERNEL_HEADERS="/lib/modules/$KERNEL_VERSION/build"
else
    echo -e "${RED}ERROR: Kernel headers not found on host!${NC}"
    echo "Install with: sudo apt-get install linux-headers-$KERNEL_VERSION"
    exit 1
fi

echo -e "Host headers: ${GREEN}$HOST_KERNEL_HEADERS${NC}"
echo ""

# Function to check if chroot exists
check_chroot() {
    if [ ! -d "$CHROOT_PATH/usr" ]; then
        echo -e "${RED}ERROR: Chroot not found at $CHROOT_PATH${NC}"
        echo "Run: sudo ./scripts/chroot/bootstrap_chroot.sh auto"
        return 1
    fi
    return 0
}

# Function to copy kernel headers to chroot
setup_chroot_headers() {
    echo -e "${BLUE}Setting up kernel headers in chroot...${NC}"
    
    # Create directory in chroot
    sudo mkdir -p "$CHROOT_PATH/usr/src"
    
    # Copy kernel headers
    if [ ! -d "$CHROOT_PATH/usr/src/linux-headers-$KERNEL_VERSION" ]; then
        echo "Copying kernel headers to chroot..."
        sudo cp -r "$HOST_KERNEL_HEADERS" "$CHROOT_PATH/usr/src/linux-headers-$KERNEL_VERSION"
    fi
    
    # Create symlinks
    sudo mkdir -p "$CHROOT_PATH/lib/modules/$KERNEL_VERSION"
    sudo ln -sf "/usr/src/linux-headers-$KERNEL_VERSION" "$CHROOT_PATH/lib/modules/$KERNEL_VERSION/build"
    sudo ln -sf "/usr/src/linux-headers-$KERNEL_VERSION" "$CHROOT_PATH/lib/modules/$KERNEL_VERSION/source"
    
    echo -e "${GREEN}✓ Kernel headers configured in chroot${NC}"
}

# Build ZFS using existing script
build_zfs_env() {
    echo ""
    echo -e "${BLUE}=== Building ZFS in Chroot Environment ===${NC}"
    
    # Use the existing ZFS build script
    if [ -f "./scripts/build/build_zfs_on_host.sh" ]; then
        # Export kernel version for the script
        export KERNEL_VERSION
        export KERNEL_HEADERS="/usr/src/linux-headers-$KERNEL_VERSION"
        
        echo "Running ZFS build script..."
        sudo -E ./scripts/build/build_zfs_on_host.sh
    else
        echo -e "${RED}ERROR: ZFS build script not found!${NC}"
        return 1
    fi
}

# Build Proxmox using existing script
build_proxmox_env() {
    echo ""
    echo -e "${BLUE}=== Building Proxmox in Chroot Environment ===${NC}"
    
    # Use the existing Proxmox build script
    if [ -f "./scripts/build/build_proxmox_on_host.sh" ]; then
        echo "Running Proxmox build script..."
        sudo -E ./scripts/build/build_proxmox_on_host.sh
    else
        echo -e "${YELLOW}Proxmox build script not found, using manual method...${NC}"
        
        # Manual Proxmox build in chroot
        cat > /tmp/build_proxmox_chroot.sh << 'EOF'
#!/bin/bash
set -e

# Inside chroot
echo "Installing Proxmox build dependencies..."
apt-get update
apt-get install -y git build-essential devscripts debhelper

# Clone and build basic Proxmox components
cd /tmp
git clone git://git.proxmox.com/git/pve-common.git || true
cd pve-common
make deb || true
cp *.deb /tmp/ 2>/dev/null || true

echo "Proxmox build attempted"
EOF
        
        chmod +x /tmp/build_proxmox_chroot.sh
        sudo cp /tmp/build_proxmox_chroot.sh "$CHROOT_PATH/tmp/"
        sudo ./scripts/chroot/use_arch_chroot.sh /tmp/build_proxmox_chroot.sh
        
        # Copy packages out
        sudo cp "$CHROOT_PATH/tmp/"*.deb prebuilt_packages/ 2>/dev/null || true
    fi
}

# Main execution
main() {
    # Check prerequisites
    if ! check_chroot; then
        exit 1
    fi
    
    # Setup kernel headers in chroot
    setup_chroot_headers
    
    # Parse command line
    case "${1:-all}" in
        zfs)
            build_zfs_env
            ;;
        proxmox)
            build_proxmox_env
            ;;
        all|both)
            build_zfs_env
            echo -e "${BLUE}════════════════════════════════════════${NC}"
            build_proxmox_env
            ;;
        *)
            echo "Usage: $0 [zfs|proxmox|all]"
            echo ""
            echo "  zfs      - Build only ZFS packages"
            echo "  proxmox  - Build only Proxmox packages"
            echo "  all      - Build both (default)"
            exit 1
            ;;
    esac
    
    # Show results
    echo ""
    echo -e "${GREEN}=== Build Complete ===${NC}"
    echo "Packages location: $SCRIPT_DIR/prebuilt_packages/"
    ls -lh prebuilt_packages/*.deb 2>/dev/null | tail -20 || echo "No packages found"
}

# Run main
main "$@"