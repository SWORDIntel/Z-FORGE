#!/bin/bash
# Comprehensive bootstrap script with multiple options
# Supports debootstrap, cdebootstrap, and manual methods

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "           Z-FORGE Chroot Bootstrap Tool"
echo "═══════════════════════════════════════════════════════════════════"

CHROOT_PATH="/tmp/zforge_workspace/chroot"
DEBIAN_RELEASE="trixie"
DEBIAN_MIRROR="http://deb.debian.org/debian"

# Check available tools
echo "[*] Checking available bootstrap tools..."
echo ""

DEBOOTSTRAP_AVAILABLE=false
CDEBOOTSTRAP_AVAILABLE=false

if command -v debootstrap >/dev/null 2>&1; then
    DEBOOTSTRAP_AVAILABLE=true
    echo "✅ debootstrap is available ($(which debootstrap))"
else
    echo "❌ debootstrap is NOT available"
fi

if command -v cdebootstrap >/dev/null 2>&1; then
    CDEBOOTSTRAP_AVAILABLE=true
    echo "✅ cdebootstrap is available ($(which cdebootstrap))"
else
    echo "❌ cdebootstrap is NOT available"
fi

echo ""

# Function to use debootstrap
use_debootstrap() {
    echo "Using debootstrap to create chroot..."
    
    debootstrap \
        --variant=minbase \
        --include=systemd,systemd-sysv,udev,kmod,live-boot,live-config,squashfs-tools,e2fsprogs \
        "$DEBIAN_RELEASE" \
        "$CHROOT_PATH" \
        "$DEBIAN_MIRROR"
}

# Function to use cdebootstrap
use_cdebootstrap() {
    echo "Using cdebootstrap to create chroot..."
    
    cdebootstrap \
        --flavour=minimal \
        --include=systemd,systemd-sysv,udev,kmod,live-boot,live-config,squashfs-tools,e2fsprogs \
        "$DEBIAN_RELEASE" \
        "$CHROOT_PATH" \
        "$DEBIAN_MIRROR"
}

# Function to install bootstrap tools
install_bootstrap_tools() {
    echo "═══════════════════════════════════════════════════════════════════"
    echo "           Installing Bootstrap Tools"
    echo "═══════════════════════════════════════════════════════════════════"
    echo ""
    
    if [ "$EUID" -ne 0 ]; then
        echo "To install bootstrap tools, run:"
        echo ""
        echo "For debootstrap:"
        echo "  sudo apt-get update"
        echo "  sudo apt-get install debootstrap"
        echo ""
        echo "For cdebootstrap (lighter, written in C):"
        echo "  sudo apt-get update"
        echo "  sudo apt-get install cdebootstrap"
        echo ""
        echo "Then run this script again with sudo."
    else
        echo "Choose which tool to install:"
        echo "1. debootstrap (standard, more features)"
        echo "2. cdebootstrap (faster, written in C)"
        echo "3. Both"
        echo "4. Skip"
        echo ""
        read -p "Your choice [1-4]: " choice
        
        case $choice in
            1)
                apt-get update
                apt-get install -y debootstrap
                ;;
            2)
                apt-get update
                apt-get install -y cdebootstrap
                ;;
            3)
                apt-get update
                apt-get install -y debootstrap cdebootstrap
                ;;
            4)
                echo "Skipping installation."
                ;;
            *)
                echo "Invalid choice."
                ;;
        esac
    fi
}

# Main script logic
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: This script must be run with sudo"
    echo "Usage: sudo $0 [debootstrap|cdebootstrap|auto]"
    echo ""
    
    if ! $DEBOOTSTRAP_AVAILABLE && ! $CDEBOOTSTRAP_AVAILABLE; then
        echo "No bootstrap tools found. Install options:"
        install_bootstrap_tools
    fi
    exit 1
fi

# Parse command line argument
BOOTSTRAP_METHOD="${1:-auto}"

# Backup existing chroot if it exists
if [ -d "$CHROOT_PATH" ]; then
    echo "Backing up existing chroot..."
    mv "$CHROOT_PATH" "${CHROOT_PATH}.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Create workspace
mkdir -p "$(dirname "$CHROOT_PATH")"

# Execute based on method
case "$BOOTSTRAP_METHOD" in
    debootstrap)
        if $DEBOOTSTRAP_AVAILABLE; then
            use_debootstrap
        else
            echo "ERROR: debootstrap is not installed"
            install_bootstrap_tools
            exit 1
        fi
        ;;
        
    cdebootstrap)
        if $CDEBOOTSTRAP_AVAILABLE; then
            use_cdebootstrap
        else
            echo "ERROR: cdebootstrap is not installed"
            install_bootstrap_tools
            exit 1
        fi
        ;;
        
    auto)
        # Prefer cdebootstrap if available (faster)
        if $CDEBOOTSTRAP_AVAILABLE; then
            echo "Auto-selected: cdebootstrap (faster)"
            use_cdebootstrap
        elif $DEBOOTSTRAP_AVAILABLE; then
            echo "Auto-selected: debootstrap"
            use_debootstrap
        else
            echo "ERROR: No bootstrap tool available"
            install_bootstrap_tools
            exit 1
        fi
        ;;
        
    *)
        echo "Usage: $0 [debootstrap|cdebootstrap|auto]"
        echo ""
        echo "Options:"
        echo "  debootstrap  - Use standard debootstrap"
        echo "  cdebootstrap - Use C-based cdebootstrap (faster)"
        echo "  auto         - Automatically choose best available"
        echo ""
        echo "Available tools:"
        $DEBOOTSTRAP_AVAILABLE && echo "  - debootstrap"
        $CDEBOOTSTRAP_AVAILABLE && echo "  - cdebootstrap"
        exit 1
        ;;
esac

# Post-bootstrap configuration
if [ -d "$CHROOT_PATH" ]; then
    echo ""
    echo "Configuring chroot environment..."
    
    # Mount necessary filesystems
    for fs in proc sys dev dev/pts; do
        if ! mountpoint -q "$CHROOT_PATH/$fs" 2>/dev/null; then
            mkdir -p "$CHROOT_PATH/$fs"
            mount --bind "/$fs" "$CHROOT_PATH/$fs"
        fi
    done
    
    # Configure apt sources
    cat > "$CHROOT_PATH/etc/apt/sources.list" << EOF
deb $DEBIAN_MIRROR $DEBIAN_RELEASE main contrib non-free-firmware
deb $DEBIAN_MIRROR $DEBIAN_RELEASE-updates main contrib non-free-firmware
deb http://security.debian.org/debian-security $DEBIAN_RELEASE-security main contrib non-free-firmware
EOF
    
    # Update package cache
    chroot "$CHROOT_PATH" apt-get update
    
    echo ""
    echo "═══════════════════════════════════════════════════════════════════"
    echo "                  Bootstrap Complete!"
    echo "═══════════════════════════════════════════════════════════════════"
    echo ""
    echo "Chroot created at: $CHROOT_PATH"
    echo "Bootstrap method: $BOOTSTRAP_METHOD"
    echo ""
    echo "Next steps:"
    echo "1. Continue with 'make build' to complete the ISO"
    echo "2. To enter chroot: sudo chroot $CHROOT_PATH /bin/bash"
fi