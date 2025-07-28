#!/bin/bash
# Z-FORGE staged debootstrap - minimal first, then add essentials

set -e

WORKSPACE="/tmp/zforge_workspace"
CHROOT_PATH="$WORKSPACE/chroot"

echo "=== Staged Debootstrap for Z-FORGE ==="
echo "Stage 1: Minimal system (~50MB)"
echo "Stage 2: Z-FORGE essentials (~100MB more)"

# Cleanup
cleanup() {
    echo "1. Cleaning previous attempts..."
    if [ -d "$CHROOT_PATH" ]; then
        sudo umount "$CHROOT_PATH"/{dev/pts,dev,sys,proc} 2>/dev/null || true
        sudo rm -rf "$CHROOT_PATH"
    fi
    sudo mkdir -p "$WORKSPACE"
    echo "   ✓ Cleanup complete"
}

# Stage 1: Absolute minimal debootstrap
stage1_minimal() {
    echo "2. Stage 1: Installing minimal Debian system..."
    
    local cmd=(
        sudo debootstrap
        --arch=amd64
        --variant=minbase
        --include="base-files,base-passwd,bash,coreutils,util-linux"
        trixie
        "$CHROOT_PATH"
        http://deb.debian.org/debian
    )
    
    echo "   Download size: ~50MB"
    echo "   Command: ${cmd[*]}"
    
    if timeout 600 "${cmd[@]}"; then
        echo "   ✓ Stage 1 complete - minimal system installed"
        return 0
    else
        echo "   ✗ Stage 1 failed"
        return 1
    fi
}

# Setup chroot for package installation
setup_chroot() {
    echo "3. Setting up chroot environment..."
    
    # DNS configuration
    sudo tee "$CHROOT_PATH/etc/resolv.conf" > /dev/null << 'EOF'
nameserver 9.9.9.9
nameserver 8.8.8.8
nameserver 1.1.1.1
EOF
    
    # Mount filesystems
    sudo mount -t proc proc "$CHROOT_PATH/proc"
    sudo mount -t sysfs sysfs "$CHROOT_PATH/sys"
    sudo mount --bind /dev "$CHROOT_PATH/dev"
    sudo mount -t devpts devpts "$CHROOT_PATH/dev/pts"
    
    echo "   ✓ Chroot ready for package installation"
}

# Stage 2: Install Z-FORGE essential packages
stage2_essentials() {
    echo "4. Stage 2: Installing Z-FORGE essentials..."
    
    # Update package lists
    echo "   Updating package lists..."
    sudo chroot "$CHROOT_PATH" apt-get update
    
    # Critical packages for Z-FORGE (in order of importance)
    local critical_packages=(
        "ca-certificates"      # SSL certificates - REQUIRED for HTTPS
        "curl wget"           # Download tools - REQUIRED by many modules  
        "gnupg gpgv"          # Package verification - REQUIRED
        "apt-transport-https" # HTTPS repos - REQUIRED for some repos
    )
    
    echo "   Installing critical packages..."
    for package_group in "${critical_packages[@]}"; do
        echo "     Installing: $package_group"
        if sudo chroot "$CHROOT_PATH" apt-get install -y $package_group; then
            echo "     ✓ Installed: $package_group"
        else
            echo "     ✗ FAILED: $package_group (this may cause build issues)"
            return 1
        fi
    done
    
    # Important packages for Z-FORGE (nice to have, but build can work without)
    local important_packages=(
        "locales"            # Locale support
        "sudo"               # Privilege escalation
        "linux-base"         # Linux system files
        "bash-completion"    # Shell completion
    )
    
    echo "   Installing important packages..."
    for package_group in "${important_packages[@]}"; do
        echo "     Installing: $package_group"
        if sudo chroot "$CHROOT_PATH" apt-get install -y $package_group; then
            echo "     ✓ Installed: $package_group"
        else
            echo "     ⚠ Failed: $package_group (continuing anyway)"
        fi
    done
    
    echo "   ✓ Stage 2 complete - Z-FORGE essentials installed"
}

# Verify and cleanup
verify_installation() {
    echo "5. Verifying installation..."
    
    # Check critical files
    local required_files=(
        "/bin/bash"
        "/usr/bin/curl"
        "/usr/bin/wget" 
        "/etc/debian_version"
        "/etc/ssl/certs/ca-certificates.crt"
    )
    
    local missing_files=0
    for file in "${required_files[@]}"; do
        if [ -f "$CHROOT_PATH$file" ]; then
            echo "   ✓ Found: $file"
        else
            echo "   ✗ Missing: $file"
            missing_files=$((missing_files + 1))
        fi
    done
    
    # Unmount filesystems
    sudo umount "$CHROOT_PATH"/{dev/pts,dev,sys,proc} 2>/dev/null || true
    
    # Report results
    local total_size=$(du -sh "$CHROOT_PATH" | cut -f1)
    echo "   Installation size: $total_size"
    
    if [ $missing_files -eq 0 ]; then
        echo "   ✓ All critical files present"
        return 0
    else
        echo "   ⚠ $missing_files critical files missing"
        return 1
    fi
}

# Main execution
main() {
    echo "This approach minimizes download while ensuring Z-FORGE compatibility"
    echo
    
    cleanup
    
    if stage1_minimal; then
        setup_chroot
        
        if stage2_essentials; then
            if verify_installation; then
                echo
                echo "=== Complete Success ==="
                echo "Full Z-FORGE-compatible system installed"
                echo "Total download: ~150MB (vs standard ~200MB)"
                echo
                echo "Ready to run Z-FORGE build:"
                echo "sudo python3 builder/z-forge.py --build-spec build_spec.yml"
            else
                echo
                echo "=== Partial Success ==="
                echo "System installed but some files missing"
                echo "Try running build anyway - may still work"
            fi
        else
            echo
            echo "=== Stage 2 Failed ==="
            echo "Minimal system installed but essentials failed"
            echo "You can try the ultra-minimal approach with ./fix_debootstrap_tether.sh"
        fi
    else
        echo
        echo "=== Stage 1 Failed ==="
        echo "Even minimal debootstrap failed"
        echo "Check connection and disk space"
    fi
}

# Run main function
main "$@"