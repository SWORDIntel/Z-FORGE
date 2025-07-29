#!/bin/bash
# Safe kernel installation for Debian Trixie with comprehensive error handling

set -e

CHROOT_PATH="/tmp/zforge_workspace/chroot"

echo "=== Safe Trixie Kernel Installation ==="
echo "This script will safely install the Debian Trixie kernel with proper error handling"
echo ""

# Function to handle dpkg errors
fix_dpkg_if_needed() {
    echo "Checking dpkg status..."
    if ! sudo chroot "$CHROOT_PATH" dpkg --audit > /dev/null 2>&1; then
        echo "DPKG issues detected, attempting to fix..."
        sudo chroot "$CHROOT_PATH" dpkg --configure -a || true
        sudo chroot "$CHROOT_PATH" apt-get install -f -y || true
    fi
}

# Function to safely install packages
safe_apt_install() {
    local packages="$@"
    local max_retries=3
    local retry=0
    
    while [ $retry -lt $max_retries ]; do
        echo "Attempting to install: $packages (attempt $((retry+1))/$max_retries)"
        
        # Fix any dpkg issues first
        fix_dpkg_if_needed
        
        # Try to install
        if sudo chroot "$CHROOT_PATH" apt-get install -y $packages; then
            echo "Successfully installed: $packages"
            return 0
        else
            echo "Installation failed, cleaning up..."
            
            # Clean up
            sudo chroot "$CHROOT_PATH" apt-get clean
            sudo chroot "$CHROOT_PATH" apt-get update
            
            # Remove problematic packages if any
            if [ $retry -eq 1 ]; then
                echo "Attempting to remove conflicting packages..."
                sudo chroot "$CHROOT_PATH" apt-get autoremove -y || true
            fi
            
            retry=$((retry+1))
        fi
    done
    
    echo "ERROR: Failed to install $packages after $max_retries attempts"
    return 1
}

# Check if chroot exists
if [ ! -d "$CHROOT_PATH" ]; then
    echo "ERROR: Chroot directory not found at $CHROOT_PATH"
    exit 1
fi

# Step 1: Fix any existing dpkg issues
echo ""
echo "Step 1: Ensuring dpkg is in a clean state..."
fix_dpkg_if_needed

# Step 2: Update sources and package lists
echo ""
echo "Step 2: Updating package lists..."
sudo chroot "$CHROOT_PATH" apt-get update

# Step 3: Install essential packages first
echo ""
echo "Step 3: Installing essential packages..."
safe_apt_install build-essential dkms bc kmod

# Step 4: Find and install appropriate kernel
echo ""
echo "Step 4: Finding appropriate kernel packages..."

# Try to find signed kernels first (preferred)
KERNEL_SEARCH=$(sudo chroot "$CHROOT_PATH" apt-cache search '^linux-image-[0-9]' | grep -v 'unsigned' | grep 'amd64' | sort -V | tail -5)

if [ -z "$KERNEL_SEARCH" ]; then
    echo "No signed kernels found, searching for unsigned kernels..."
    KERNEL_SEARCH=$(sudo chroot "$CHROOT_PATH" apt-cache search '^linux-image-[0-9]' | grep 'amd64' | sort -V | tail -5)
fi

echo "Available kernels:"
echo "$KERNEL_SEARCH"

# Try to install the latest available kernel
KERNEL_INSTALLED=false

# First try the metapackage
echo ""
echo "Attempting to install kernel metapackage..."
if safe_apt_install linux-image-amd64 linux-headers-amd64; then
    KERNEL_INSTALLED=true
    echo "Kernel metapackage installed successfully"
else
    echo "Metapackage installation failed, trying specific versions..."
    
    # Try specific kernels from the search
    while IFS= read -r kernel_line; do
        if [ -z "$kernel_line" ]; then
            continue
        fi
        
        KERNEL_PKG=$(echo "$kernel_line" | awk '{print $1}')
        KERNEL_VERSION=$(echo "$KERNEL_PKG" | sed 's/linux-image-//')
        HEADERS_PKG="linux-headers-${KERNEL_VERSION}"
        
        echo ""
        echo "Trying kernel: $KERNEL_PKG"
        
        if safe_apt_install "$KERNEL_PKG" "$HEADERS_PKG"; then
            KERNEL_INSTALLED=true
            echo "Successfully installed kernel: $KERNEL_PKG"
            break
        fi
    done <<< "$KERNEL_SEARCH"
fi

if [ "$KERNEL_INSTALLED" = false ]; then
    echo ""
    echo "ERROR: Could not install any kernel package!"
    echo "Manual intervention may be required."
    exit 1
fi

# Step 5: Install ZFS packages
echo ""
echo "Step 5: Installing ZFS packages..."

# Remove conflicting packages first
echo "Removing conflicting packages..."
sudo chroot "$CHROOT_PATH" apt-get remove -y zfs-initramfs || true

# Install ZFS with fallbacks
if safe_apt_install zfsutils-linux zfs-dkms; then
    echo "ZFS base packages installed successfully"
    
    # Try to install dracut support
    if safe_apt_install zfs-dracut; then
        echo "ZFS dracut support installed"
    else
        echo "WARNING: Could not install zfs-dracut, but core ZFS is installed"
    fi
else
    echo "ERROR: Failed to install ZFS packages"
    exit 1
fi

# Step 6: Verify installation
echo ""
echo "Step 6: Verifying installation..."

echo ""
echo "Installed kernels:"
sudo chroot "$CHROOT_PATH" dpkg -l | grep -E '^ii.*linux-image' || echo "No kernels found!"

echo ""
echo "Installed headers:"
sudo chroot "$CHROOT_PATH" dpkg -l | grep -E '^ii.*linux-headers' || echo "No headers found!"

echo ""
echo "ZFS packages:"
sudo chroot "$CHROOT_PATH" dpkg -l | grep -E '^ii.*zfs' || echo "No ZFS packages found!"

echo ""
echo "DKMS status:"
sudo chroot "$CHROOT_PATH" dkms status || echo "DKMS not available"

# Final dpkg check
echo ""
echo "Final system check..."
fix_dpkg_if_needed

echo ""
echo "=== Installation completed! ==="
echo ""
echo "If you encountered any errors, you can:"
echo "1. Run: sudo /opt/github/Z-FORGE/fix_dpkg_interrupted.sh"
echo "2. Then re-run this script"
echo ""
echo "To manually fix dpkg issues in chroot:"
echo "  sudo chroot $CHROOT_PATH dpkg --configure -a"
echo "  sudo chroot $CHROOT_PATH apt-get install -f"