#!/bin/bash
# Complete recovery and installation script for Z-FORGE Trixie build

set +e  # Don't exit on error, we're handling them

CHROOT_PATH="/tmp/zforge_workspace/chroot"

echo "=== Z-FORGE Build Recovery and Kernel Installation ==="
echo "This script will:"
echo "1. Fix any dpkg/apt issues"
echo "2. Configure proper repositories"
echo "3. Install Trixie kernel with ZFS support"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "error")
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
        "success")
            echo -e "${GREEN}[SUCCESS]${NC} $message"
            ;;
        "warning")
            echo -e "${YELLOW}[WARNING]${NC} $message"
            ;;
        *)
            echo "[INFO] $message"
            ;;
    esac
}

# Check if running as root/sudo
if [ "$EUID" -ne 0 ]; then 
    print_status "error" "Please run this script with sudo"
    exit 1
fi

# Check if chroot exists
if [ ! -d "$CHROOT_PATH" ]; then
    print_status "error" "Chroot directory not found at $CHROOT_PATH"
    exit 1
fi

# Phase 1: Recovery
print_status "info" "Phase 1: System Recovery"
echo "========================================"

# Kill any running apt/dpkg processes in chroot
print_status "info" "Checking for running package management processes..."
for pid in $(lsof +D "$CHROOT_PATH" 2>/dev/null | grep -E '(apt|dpkg)' | awk '{print $2}' | sort -u); do
    print_status "warning" "Killing process $pid"
    kill -9 $pid 2>/dev/null || true
done

# Remove lock files
print_status "info" "Removing lock files..."
rm -f "$CHROOT_PATH"/var/lib/dpkg/lock* 2>/dev/null || true
rm -f "$CHROOT_PATH"/var/lib/apt/lists/lock* 2>/dev/null || true
rm -f "$CHROOT_PATH"/var/cache/apt/archives/lock* 2>/dev/null || true

# Fix dpkg database
print_status "info" "Fixing dpkg database..."
chroot "$CHROOT_PATH" dpkg --configure -a 2>/dev/null || true
chroot "$CHROOT_PATH" apt-get install -f -y 2>/dev/null || true

# Clean package cache
print_status "info" "Cleaning package cache..."
chroot "$CHROOT_PATH" apt-get clean
chroot "$CHROOT_PATH" apt-get autoclean

# Phase 2: Repository Configuration
echo ""
print_status "info" "Phase 2: Repository Configuration"
echo "========================================"

# Detect Debian version
DEBIAN_VERSION="trixie"
if [ -f "$CHROOT_PATH/etc/os-release" ]; then
    VERSION_CODENAME=$(grep VERSION_CODENAME "$CHROOT_PATH/etc/os-release" 2>/dev/null | cut -d'=' -f2 | tr -d '"')
    [ -n "$VERSION_CODENAME" ] && DEBIAN_VERSION="$VERSION_CODENAME"
fi

print_status "info" "Detected Debian version: $DEBIAN_VERSION"

# Configure repositories
print_status "info" "Configuring APT repositories..."
cat > "$CHROOT_PATH/etc/apt/sources.list" << EOF
# Debian $DEBIAN_VERSION repositories with contrib for ZFS
deb http://deb.debian.org/debian $DEBIAN_VERSION main contrib non-free-firmware
deb-src http://deb.debian.org/debian $DEBIAN_VERSION main contrib non-free-firmware

deb http://deb.debian.org/debian-security $DEBIAN_VERSION-security main contrib non-free-firmware
deb-src http://deb.debian.org/debian-security $DEBIAN_VERSION-security main contrib non-free-firmware
EOF

# Update package lists
print_status "info" "Updating package lists..."
if chroot "$CHROOT_PATH" apt-get update; then
    print_status "success" "Package lists updated"
else
    print_status "error" "Failed to update package lists"
    exit 1
fi

# Phase 3: Kernel Installation
echo ""
print_status "info" "Phase 3: Kernel Installation"
echo "========================================"

# Install prerequisites
print_status "info" "Installing prerequisites..."
PREREQS="build-essential dkms bc kmod linux-base"
for pkg in $PREREQS; do
    if chroot "$CHROOT_PATH" apt-get install -y $pkg 2>/dev/null; then
        print_status "success" "Installed $pkg"
    else
        print_status "warning" "Could not install $pkg"
    fi
done

# Find best kernel to install
print_status "info" "Finding available kernels..."
KERNEL_LIST=$(chroot "$CHROOT_PATH" apt-cache search '^linux-image-[0-9]' | grep 'amd64' | grep -v 'dbg' | sort -V)

if [ -z "$KERNEL_LIST" ]; then
    print_status "error" "No kernels found!"
    exit 1
fi

echo "Available kernels:"
echo "$KERNEL_LIST" | tail -5

# Try to install kernel
KERNEL_INSTALLED=false

# First try metapackage
print_status "info" "Attempting to install kernel metapackage..."
if chroot "$CHROOT_PATH" apt-get install -y linux-image-amd64 linux-headers-amd64 2>/dev/null; then
    KERNEL_INSTALLED=true
    print_status "success" "Kernel metapackage installed"
else
    print_status "warning" "Metapackage installation failed, trying specific versions..."
    
    # Try specific kernels
    echo "$KERNEL_LIST" | tail -5 | while IFS= read -r kernel_line; do
        [ -z "$kernel_line" ] && continue
        
        KERNEL_PKG=$(echo "$kernel_line" | awk '{print $1}')
        KERNEL_VERSION=$(echo "$KERNEL_PKG" | sed 's/linux-image-//')
        HEADERS_PKG="linux-headers-${KERNEL_VERSION}"
        
        print_status "info" "Trying: $KERNEL_PKG"
        
        if chroot "$CHROOT_PATH" apt-get install -y "$KERNEL_PKG" "$HEADERS_PKG" 2>/dev/null; then
            KERNEL_INSTALLED=true
            print_status "success" "Installed kernel: $KERNEL_PKG"
            break
        fi
    done
fi

# Phase 4: ZFS Installation
echo ""
print_status "info" "Phase 4: ZFS Installation"
echo "========================================"

# Remove conflicting packages
print_status "info" "Removing conflicting packages..."
chroot "$CHROOT_PATH" apt-get remove -y zfs-initramfs 2>/dev/null || true

# Install ZFS
print_status "info" "Installing ZFS packages..."
ZFS_PACKAGES="zfsutils-linux zfs-dkms"
if chroot "$CHROOT_PATH" apt-get install -y $ZFS_PACKAGES; then
    print_status "success" "ZFS packages installed"
    
    # Try dracut support
    if chroot "$CHROOT_PATH" apt-get install -y zfs-dracut 2>/dev/null; then
        print_status "success" "ZFS dracut support installed"
    else
        print_status "warning" "Could not install zfs-dracut"
    fi
else
    print_status "error" "Failed to install ZFS packages"
fi

# Phase 5: Verification
echo ""
print_status "info" "Phase 5: Verification"
echo "========================================"

# Check installed packages
print_status "info" "Checking installed packages..."

echo ""
echo "Kernels:"
chroot "$CHROOT_PATH" dpkg -l | grep -E '^ii.*linux-image' || print_status "warning" "No kernels installed"

echo ""
echo "Headers:"
chroot "$CHROOT_PATH" dpkg -l | grep -E '^ii.*linux-headers' || print_status "warning" "No headers installed"

echo ""
echo "ZFS:"
chroot "$CHROOT_PATH" dpkg -l | grep -E '^ii.*zfs' || print_status "warning" "No ZFS packages installed"

# Check DKMS
echo ""
print_status "info" "DKMS Status:"
chroot "$CHROOT_PATH" dkms status 2>/dev/null || print_status "warning" "DKMS not available"

# Final dpkg check
echo ""
print_status "info" "Final system check..."
if chroot "$CHROOT_PATH" dpkg --audit 2>/dev/null; then
    print_status "success" "System package database is clean"
else
    print_status "warning" "Some package issues remain"
fi

# Summary
echo ""
echo "========================================"
print_status "info" "Recovery and installation complete!"
echo ""
echo "Next steps:"
echo "1. If kernel installation failed, check the output above for specific errors"
echo "2. You may need to manually select a different kernel version"
echo "3. To check available kernels: sudo chroot $CHROOT_PATH apt-cache search linux-image"
echo ""
echo "Manual commands if needed:"
echo "  sudo chroot $CHROOT_PATH dpkg --configure -a"
echo "  sudo chroot $CHROOT_PATH apt-get install -f"
echo "  sudo chroot $CHROOT_PATH apt-get install linux-image-amd64 linux-headers-amd64"