#!/bin/bash
# Z-FORGE debootstrap fix optimized for USB tethered connections

set -e

WORKSPACE="${ZFORGE_WORKSPACE:-/home/john/zforge_workspace}"
CHROOT_PATH="$WORKSPACE/chroot"

echo "=== USB Tether-Optimized Debootstrap Fix ==="
echo "Optimized for unstable/slow connections"

# Function to test connection stability
test_connection_stability() {
    echo "1. Testing connection stability..."
    
    local failures=0
    for i in {1..5}; do
        echo "   Test $i/5: Pinging deb.debian.org..."
        if ! ping -c 2 -W 5 deb.debian.org >/dev/null 2>&1; then
            failures=$((failures + 1))
            echo "   ⚠ Ping $i failed"
        else
            echo "   ✓ Ping $i successful"
        fi
        sleep 1
    done
    
    if [ $failures -gt 2 ]; then
        echo "   ⚠ Connection unstable ($failures/5 failures)"
        echo "   Continuing with extra retry logic..."
    else
        echo "   ✓ Connection seems stable"
    fi
}

# Function to clean up
cleanup() {
    echo "2. Cleaning previous attempts..."
    if [ -d "$CHROOT_PATH" ]; then
        sudo umount "$CHROOT_PATH"/{dev/pts,dev,sys,proc} 2>/dev/null || true
        sudo rm -rf "$CHROOT_PATH"
    fi
    sudo mkdir -p "$WORKSPACE"
    echo "   ✓ Cleanup complete"
}

# Function to run ultra-minimal debootstrap
run_minimal_debootstrap() {
    echo "3. Running ultra-minimal debootstrap (tether-optimized)..."
    echo "   This minimizes download size for unstable connections"
    
    # Use absolute minimal package set
    local cmd=(
        sudo debootstrap
        --arch=amd64
        --variant=minbase
        --include="base-files,base-passwd,bash,coreutils"
        --exclude="systemd-timesyncd,rsyslog"
        trixie
        "$CHROOT_PATH"
        http://deb.debian.org/debian
    )
    
    echo "   Command: ${cmd[*]}"
    echo "   Minimal download size: ~50MB (vs normal ~200MB)"
    
    # Run with multiple retry attempts for tethered connections
    local attempts=0
    local max_attempts=3
    
    while [ $attempts -lt $max_attempts ]; do
        attempts=$((attempts + 1))
        echo "   Attempt $attempts/$max_attempts..."
        
        if timeout 900 "${cmd[@]}"; then
            echo "   ✓ Minimal debootstrap successful!"
            return 0
        else
            echo "   ✗ Attempt $attempts failed"
            if [ $attempts -lt $max_attempts ]; then
                echo "   Cleaning and retrying in 10 seconds..."
                sudo rm -rf "$CHROOT_PATH"
                sleep 10
            fi
        fi
    done
    
    echo "   ✗ All debootstrap attempts failed"
    return 1
}

# Function to setup chroot environment
setup_chroot() {
    echo "4. Setting up chroot environment..."
    
    # Create resolv.conf with multiple DNS servers for reliability
    sudo tee "$CHROOT_PATH/etc/resolv.conf" > /dev/null << 'EOF'
# Multiple DNS servers for tethered connections
nameserver 8.8.8.8
nameserver 9.9.9.9
nameserver 1.1.1.1
nameserver 8.8.4.4
options timeout:10
options attempts:3
EOF
    
    # Mount filesystems
    sudo mount -t proc proc "$CHROOT_PATH/proc"
    sudo mount -t sysfs sysfs "$CHROOT_PATH/sys"  
    sudo mount --bind /dev "$CHROOT_PATH/dev"
    sudo mount -t devpts devpts "$CHROOT_PATH/dev/pts"
    
    echo "   ✓ Chroot environment ready"
}

# Function to install packages with retry logic
install_packages_with_retry() {
    echo "5. Installing required packages (with retry logic)..."
    
    # Configure APT for unstable connections
    sudo tee "$CHROOT_PATH/etc/apt/apt.conf.d/99-tether-optimized" > /dev/null << 'EOF'
// Optimized for tethered connections
Acquire::Retries "5";
Acquire::http::Timeout "60";
Acquire::https::Timeout "60";
Acquire::ftp::Timeout "60";
APT::Get::Assume-Yes "true";
APT::Install-Recommends "false";
APT::Install-Suggests "false";
Dpkg::Progress-Fancy "false";
EOF
    
    # Update package lists with retries
    echo "   Updating package lists..."
    local update_attempts=0
    while [ $update_attempts -lt 3 ]; do
        update_attempts=$((update_attempts + 1))
        echo "   Update attempt $update_attempts/3..."
        
        if sudo chroot "$CHROOT_PATH" apt-get update; then
            echo "   ✓ Package lists updated"
            break
        else
            if [ $update_attempts -lt 3 ]; then
                echo "   Retrying in 15 seconds..."
                sleep 15
            else
                echo "   ⚠ Update failed, continuing anyway..."
            fi
        fi
    done
    
    # Install packages in small groups to reduce failure impact
    local package_groups=(
        "locales sudo"
        "bash-completion ca-certificates"
        "curl wget"
        "apt-transport-https gnupg gpgv"
        "linux-base"
    )
    
    for group in "${package_groups[@]}"; do
        echo "   Installing: $group"
        local install_attempts=0
        
        while [ $install_attempts -lt 3 ]; do
            install_attempts=$((install_attempts + 1))
            echo "     Attempt $install_attempts/3..."
            
            if sudo chroot "$CHROOT_PATH" apt-get install -y $group; then
                echo "     ✓ Installed: $group"
                break
            else
                if [ $install_attempts -lt 3 ]; then
                    echo "     Retrying in 10 seconds..."
                    sleep 10
                else
                    echo "     ⚠ Failed to install: $group (continuing anyway)"
                fi
            fi
        done
    done
}

# Function to cleanup and verify
cleanup_and_verify() {
    echo "6. Cleaning up and verifying..."
    
    # Unmount filesystems
    sudo umount "$CHROOT_PATH"/{dev/pts,dev,sys,proc} 2>/dev/null || true
    
    # Verify installation
    if [ -f "$CHROOT_PATH/bin/bash" ] && [ -f "$CHROOT_PATH/etc/debian_version" ]; then
        echo "   ✓ Installation verified"
        local size=$(du -sh "$CHROOT_PATH" | cut -f1)
        echo "   Installation size: $size"
        return 0
    else
        echo "   ✗ Installation incomplete"
        return 1
    fi
}

# Main execution
main() {
    echo "This script is optimized for USB tethered connections"
    echo "It uses minimal downloads and extensive retry logic"
    echo
    
    test_connection_stability
    cleanup
    
    if run_minimal_debootstrap; then
        setup_chroot
        install_packages_with_retry
        
        if cleanup_and_verify; then
            echo
            echo "=== Success! ==="
            echo "Debootstrap completed despite tethered connection"
            echo "Ready to run Z-FORGE build:"
            echo "sudo python3 builder/z-forge.py --build-spec build_spec.yml"
        else
            echo
            echo "=== Partial Success ==="
            echo "Basic system installed but some packages may be missing"
            echo "Try running the build anyway - it may work"
        fi
    else
        echo
        echo "=== Failed ==="
        echo "Debootstrap failed even with retry logic"
        echo "Suggestions:"
        echo "1. Wait for better connection stability"
        echo "2. Try switching to different tether (WiFi hotspot vs USB)"
        echo "3. Use a wired connection if available"
        echo "4. Try during off-peak hours for better carrier performance"
    fi
}

# Run main function
main "$@"