#!/bin/bash
# Fix Z-FORGE debootstrap tar extraction errors

set -e

WORKSPACE="${ZFORGE_WORKSPACE:-/home/john/zforge_workspace}"
CHROOT_PATH="$WORKSPACE/chroot"

echo "=== Z-FORGE Debootstrap Error Fix ==="

# Function to check disk space
check_disk_space() {
    local required_gb=10
    local available_gb=$(df /tmp | tail -1 | awk '{print int($4/1024/1024)}')
    
    echo "Available space in /tmp: ${available_gb}GB"
    if [ "$available_gb" -lt "$required_gb" ]; then
        echo "⚠ Warning: Only ${available_gb}GB available, ${required_gb}GB recommended"
        echo "Consider cleaning /tmp or using a different workspace"
        return 1
    else
        echo "✓ Sufficient disk space available"
        return 0
    fi
}

# Function to clean up previous build
cleanup_previous_build() {
    echo "1. Cleaning up previous build artifacts..."
    
    if [ -d "$CHROOT_PATH" ]; then
        echo "   Unmounting any mounted filesystems..."
        
        # Unmount in reverse order
        for mount in dev/pts dev sys proc; do
            if mountpoint -q "$CHROOT_PATH/$mount" 2>/dev/null; then
                echo "   Unmounting $CHROOT_PATH/$mount..."
                sudo umount "$CHROOT_PATH/$mount" || echo "   Failed to unmount $mount (may not be mounted)"
            fi
        done
        
        echo "   Removing chroot directory..."
        sudo rm -rf "$CHROOT_PATH"
        echo "   ✓ Chroot cleaned up"
    else
        echo "   ✓ No previous chroot found"
    fi
    
    # Clean debootstrap cache
    if [ -d "/var/cache/apt/archives" ]; then
        echo "   Cleaning APT cache..."
        sudo apt-get clean || true
        echo "   ✓ APT cache cleaned"
    fi
}

# Function to fix workspace permissions
fix_workspace_permissions() {
    echo "2. Fixing workspace permissions..."
    
    # Ensure workspace directory exists
    sudo mkdir -p "$WORKSPACE"
    
    # Fix ownership and permissions
    sudo chown -R "$(id -u):$(id -g)" "$WORKSPACE" 2>/dev/null || true
    sudo chmod 755 "$WORKSPACE"
    
    echo "   ✓ Workspace permissions fixed"
}

# Function to test network connectivity
test_network() {
    echo "3. Testing network connectivity..."
    
    # Test DNS resolution
    if nslookup deb.debian.org >/dev/null 2>&1; then
        echo "   ✓ DNS resolution working"
    else
        echo "   ✗ DNS resolution failed"
        return 1
    fi
    
    # Test HTTP connectivity
    if curl -s --connect-timeout 5 http://deb.debian.org/debian/ls-lR.gz | head -n 1 | grep -q "drwxr-xr-x"; then
        echo "   ✓ Debian repository accessible"
    else
        echo "   ⚠ Repository connection test failed"
    fi
}

# Function to run debootstrap with better error handling
run_fixed_debootstrap() {
    echo "4. Running debootstrap with improved settings..."
    
    # Use more reliable debootstrap options
    local debootstrap_cmd=(
        sudo debootstrap
        --verbose
        --arch=amd64
        --variant=minbase
        --include="locales,linux-base,sudo,bash-completion,apt-transport-https,ca-certificates,curl,wget,gnupg"
        --exclude="systemd-timesyncd"
        trixie
        "$CHROOT_PATH"
        http://deb.debian.org/debian
    )
    
    echo "   Command: ${debootstrap_cmd[*]}"
    echo "   This may take 5-15 minutes depending on network speed..."
    echo
    
    # Run with timeout and better error capture
    if timeout 1800 "${debootstrap_cmd[@]}"; then
        echo "   ✓ Debootstrap completed successfully"
        return 0
    else
        local exit_code=$?
        echo "   ✗ Debootstrap failed with exit code: $exit_code"
        
        # Check for specific error patterns
        if [ -f "/tmp/debootstrap.log" ]; then
            echo "   Checking debootstrap log for errors..."
            if grep -q "tar.*failed" /tmp/debootstrap.log; then
                echo "   → Tar extraction error detected"
            elif grep -q "failed to download" /tmp/debootstrap.log; then
                echo "   → Download error detected"
            elif grep -q "No space left" /tmp/debootstrap.log; then
                echo "   → Disk space error detected"
            fi
        fi
        
        return $exit_code
    fi
}

# Function to verify the debootstrap result
verify_debootstrap() {
    echo "5. Verifying debootstrap installation..."
    
    if [ ! -d "$CHROOT_PATH" ]; then
        echo "   ✗ Chroot directory not created"
        return 1
    fi
    
    if [ ! -f "$CHROOT_PATH/bin/bash" ]; then
        echo "   ✗ Basic system files missing"
        return 1
    fi
    
    if [ ! -f "$CHROOT_PATH/etc/debian_version" ]; then
        echo "   ✗ Debian system files missing"
        return 1
    fi
    
    echo "   ✓ Debootstrap installation verified"
    
    # Show some stats
    local file_count=$(find "$CHROOT_PATH" -type f | wc -l)
    local dir_size=$(du -sh "$CHROOT_PATH" | cut -f1)
    echo "   Files created: $file_count"
    echo "   Directory size: $dir_size"
}

# Function to prepare for Z-FORGE build
prepare_for_build() {
    echo "6. Preparing for Z-FORGE build..."
    
    # Set proper permissions
    sudo chmod 755 "$CHROOT_PATH"
    
    # Create necessary mount points
    sudo mkdir -p "$CHROOT_PATH"/{proc,sys,dev,dev/pts}
    
    echo "   ✓ Ready for Z-FORGE build"
}

# Main execution
main() {
    echo "Starting debootstrap error fix..."
    echo
    
    # Run all fixes
    check_disk_space || {
        echo "Please free up disk space and try again"
        exit 1
    }
    
    cleanup_previous_build
    fix_workspace_permissions
    
    test_network || {
        echo "Please check network connectivity and try again"
        exit 1
    }
    
    run_fixed_debootstrap || {
        echo
        echo "=== Debootstrap Failed ==="
        echo "Possible solutions:"
        echo "1. Check network connectivity: ping deb.debian.org"
        echo "2. Try a different mirror by editing the script"
        echo "3. Check disk space: df -h /tmp"
        echo "4. Try running this script again"
        echo "5. Check system logs: sudo journalctl -f"
        exit 1
    }
    
    verify_debootstrap
    prepare_for_build
    
    echo
    echo "=== Fix Complete ==="
    echo "Debootstrap has been successfully completed."
    echo "You can now run the Z-FORGE build:"
    echo "sudo python3 builder/z-forge.py --build-spec build_spec.yml"
}

# Run main function
main "$@"