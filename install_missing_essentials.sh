#!/bin/bash
# Install missing essential tools for Z-FORGE

set -e

WORKSPACE="/tmp/zforge_workspace"
CHROOT_PATH="$WORKSPACE/chroot"

echo "=== Installing Missing Z-FORGE Essentials ==="

# Check if chroot exists
if [ ! -d "$CHROOT_PATH" ]; then
    echo "Error: Chroot directory not found"
    exit 1
fi

# Mount chroot
mount_chroot() {
    echo "1. Mounting chroot..."
    
    sudo cp /etc/resolv.conf "$CHROOT_PATH/etc/resolv.conf"
    
    if ! mountpoint -q "$CHROOT_PATH/proc" 2>/dev/null; then
        sudo mount -t proc proc "$CHROOT_PATH/proc"
    fi
    if ! mountpoint -q "$CHROOT_PATH/sys" 2>/dev/null; then
        sudo mount -t sysfs sysfs "$CHROOT_PATH/sys"
    fi
    if ! mountpoint -q "$CHROOT_PATH/dev" 2>/dev/null; then
        sudo mount --bind /dev "$CHROOT_PATH/dev"
    fi
    if ! mountpoint -q "$CHROOT_PATH/dev/pts" 2>/dev/null; then
        sudo mount -t devpts devpts "$CHROOT_PATH/dev/pts"
    fi
    
    echo "   ✓ Chroot mounted"
}

# Install critical missing packages
install_critical_packages() {
    echo "2. Installing critical missing packages..."
    
    # Configure environment for clean installation
    sudo chroot "$CHROOT_PATH" /bin/bash -c '
        export DEBIAN_FRONTEND=noninteractive
        export LC_ALL=C.UTF-8
        export LANG=C.UTF-8
        apt-get update -qq
    '
    
    # Essential missing packages
    local essential_packages=(
        "git"                    # Version control - REQUIRED by many modules
        "build-essential"        # Compiler toolchain (includes gcc) - REQUIRED for building
        "openssh-client"         # SSH client (includes scp, sftp) - REQUIRED for remote operations
    )
    
    echo "   Installing: ${essential_packages[*]}"
    echo "   This should be quick (~50-100MB download)"
    
    if sudo chroot "$CHROOT_PATH" /bin/bash -c '
        export DEBIAN_FRONTEND=noninteractive
        export LC_ALL=C.UTF-8
        export LANG=C.UTF-8
        apt-get install -y '"${essential_packages[*]}"'
    '; then
        echo "   ✓ Critical packages installed successfully"
    else
        echo "   ✗ Installation failed"
        return 1
    fi
}

# Install additional commonly needed packages
install_additional_packages() {
    echo "3. Installing additional commonly needed packages..."
    
    local additional_packages=(
        "python3-dev"           # Python development headers
        "pkg-config"            # Package configuration
        "autoconf"              # Build configuration
        "automake"              # Build automation
        "libtool"               # Library tools
        "cmake"                 # Modern build system
        "ninja-build"           # Fast build system
        "meson"                 # Modern build system
        "rsync"                 # File synchronization
        "unzip"                 # Archive extraction
        "zip"                   # Archive creation
        "tar"                   # Archive utility
        "gzip"                  # Compression
        "bzip2"                 # Compression
        "xz-utils"              # Compression
        "patch"                 # Patch utility
        "diffutils"             # Diff utilities
        "findutils"             # Find utilities
        "grep"                  # Text search
        "sed"                   # Stream editor
        "gawk"                  # Text processing
        "bc"                    # Calculator
        "file"                  # File type detection
        "less"                  # Pager
        "nano"                  # Text editor
        "vim-tiny"              # Text editor
    )
    
    echo "   Installing: ${additional_packages[*]}"
    echo "   This may take a few minutes..."
    
    if sudo chroot "$CHROOT_PATH" /bin/bash -c '
        export DEBIAN_FRONTEND=noninteractive
        export LC_ALL=C.UTF-8
        export LANG=C.UTF-8
        apt-get install -y '"${additional_packages[*]}"'
    '; then
        echo "   ✓ Additional packages installed successfully"
    else
        echo "   ⚠ Some additional packages failed (continuing anyway)"
    fi
}

# Verify installation
verify_installation() {
    echo "4. Verifying installation..."
    
    # Check critical tools
    local critical_tools=(
        "/usr/bin/git"
        "/usr/bin/gcc"
        "/usr/bin/scp"
        "/usr/bin/sftp"
        "/usr/bin/ssh"
        "/usr/bin/make"
        "/usr/bin/python3"
        "/usr/bin/curl"
        "/usr/bin/wget"
        "/sbin/fdisk"
    )
    
    local missing=0
    for tool in "${critical_tools[@]}"; do
        if [ -f "$CHROOT_PATH$tool" ]; then
            echo "   ✓ Found: $tool"
        else
            echo "   ✗ Missing: $tool"
            missing=$((missing + 1))
        fi
    done
    
    # Show package versions
    echo "   Checking versions..."
    sudo chroot "$CHROOT_PATH" /bin/bash -c '
        export DEBIAN_FRONTEND=noninteractive
        echo "   Git version: $(git --version 2>/dev/null || echo "Not found")"
        echo "   GCC version: $(gcc --version 2>/dev/null | head -n1 || echo "Not found")"
        echo "   Python version: $(python3 --version 2>/dev/null || echo "Not found")"
        echo "   SSH version: $(ssh -V 2>&1 | head -n1 || echo "Not found")"
    '
    
    return $missing
}

# Clean up
cleanup() {
    echo "5. Cleaning up..."
    
    # Clean package cache to save space
    sudo chroot "$CHROOT_PATH" /bin/bash -c '
        export DEBIAN_FRONTEND=noninteractive
        apt-get clean
        apt-get autoremove -y
    ' 2>/dev/null || true
    
    # Unmount chroot
    sudo umount "$CHROOT_PATH"/{dev/pts,dev,sys,proc} 2>/dev/null || true
    
    # Show final size
    local final_size=$(du -sh "$CHROOT_PATH" 2>/dev/null | cut -f1 || echo "Unknown")
    echo "   Final installation size: $final_size"
    
    echo "   ✓ Cleanup complete"
}

# Main execution
main() {
    echo "Installing missing essential tools for Z-FORGE build"
    echo "Target packages: git, gcc (build-essential), scp/sftp (openssh-client)"
    echo
    
    mount_chroot
    
    if install_critical_packages; then
        install_additional_packages
        
        if verify_installation; then
            missing=$?
            if [ $missing -eq 0 ]; then
                cleanup
                echo
                echo "=== All Essential Tools Installed ==="
                echo "✓ git - Version control"
                echo "✓ gcc - C compiler" 
                echo "✓ scp/sftp - Secure file transfer"
                echo "✓ Complete development environment"
                echo
                echo "Ready to run Z-FORGE build:"
                echo "sudo python3 builder/z-forge.py --build-spec build_spec.yml"
            else
                cleanup
                echo
                echo "=== Most Tools Installed ==="
                echo "$missing tools still missing, but should be sufficient"
                echo "Try running Z-FORGE build:"
                echo "sudo python3 builder/z-forge.py --build-spec build_spec.yml"
            fi
        else
            echo
            echo "=== Installation Issues ==="
            echo "Some tools may be missing"
            echo "Try running Z-FORGE build anyway"
        fi
    else
        echo
        echo "=== Critical Installation Failed ==="
        echo "Could not install essential packages"
        echo "Check network connectivity and try again"
        cleanup
    fi
}

# Run main function
main "$@"