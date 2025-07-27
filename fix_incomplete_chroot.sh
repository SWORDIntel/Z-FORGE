#!/bin/bash
# Fix incomplete chroot installation

set -e

echo "=== Fixing Incomplete Chroot Installation ==="

WORKSPACE="/tmp/zforge_workspace"
CHROOT_PATH="$WORKSPACE/chroot"

# Check chroot state
check_chroot_state() {
    echo "1. Checking chroot state..."
    
    if [ ! -d "$CHROOT_PATH" ]; then
        echo "   ✗ No chroot directory found"
        return 1
    fi
    
    # Check if basic commands exist
    local missing_commands=()
    local basic_commands=("/usr/bin/env" "/bin/bash" "/usr/bin/apt-get" "/bin/ls")
    
    for cmd in "${basic_commands[@]}"; do
        if [ ! -f "$CHROOT_PATH$cmd" ]; then
            missing_commands+=("$cmd")
        fi
    done
    
    if [ ${#missing_commands[@]} -gt 0 ]; then
        echo "   ✗ Missing essential commands:"
        printf "     %s\n" "${missing_commands[@]}"
        return 1
    else
        echo "   ✓ Basic commands present"
        return 0
    fi
}

# Clean and recreate chroot
clean_and_recreate() {
    echo "2. Cleaning and recreating chroot..."
    
    # Unmount any mounted filesystems
    echo "   Unmounting filesystems..."
    sudo umount "$CHROOT_PATH"/{dev/pts,dev,sys,proc} 2>/dev/null || true
    
    # Remove corrupted chroot
    echo "   Removing corrupted chroot..."
    sudo rm -rf "$CHROOT_PATH"
    
    # Create fresh directory
    sudo mkdir -p "$CHROOT_PATH"
    
    echo "   ✓ Chroot directory cleaned and recreated"
}

# Run minimal debootstrap
run_minimal_debootstrap() {
    echo "3. Running minimal debootstrap..."
    
    # Ensure network access via hosts file
    if ! grep -q "deb.debian.org" /etc/hosts; then
        echo "   Adding Debian repository to hosts file..."
        echo "151.101.2.132 deb.debian.org" | sudo tee -a /etc/hosts
        echo "151.101.2.132 security.debian.org" | sudo tee -a /etc/hosts
    fi
    
    # Run absolute minimal debootstrap
    local debootstrap_cmd=(
        sudo debootstrap
        --arch=amd64
        --variant=minbase
        --include="coreutils,util-linux,bash,apt"
        --no-check-gpg
        trixie
        "$CHROOT_PATH"
        http://deb.debian.org/debian
    )
    
    echo "   Running: ${debootstrap_cmd[*]}"
    echo "   This may take several minutes..."
    
    if "${debootstrap_cmd[@]}"; then
        echo "   ✓ Minimal debootstrap completed"
        return 0
    else
        echo "   ✗ Minimal debootstrap failed"
        return 1
    fi
}

# Verify and test chroot
verify_chroot() {
    echo "4. Verifying chroot installation..."
    
    # Check essential commands
    local essential_commands=("/usr/bin/env" "/bin/bash" "/usr/bin/apt-get")
    local missing=0
    
    for cmd in "${essential_commands[@]}"; do
        if [ -f "$CHROOT_PATH$cmd" ]; then
            echo "   ✓ Found: $cmd"
        else
            echo "   ✗ Missing: $cmd"
            missing=$((missing + 1))
        fi
    done
    
    if [ $missing -eq 0 ]; then
        echo "   ✓ All essential commands present"
        
        # Test chroot execution
        echo "   Testing chroot execution..."
        if sudo chroot "$CHROOT_PATH" /bin/bash -c 'echo "Chroot test successful"'; then
            echo "   ✓ Chroot execution working"
            return 0
        else
            echo "   ✗ Chroot execution failed"
            return 1
        fi
    else
        echo "   ✗ $missing essential commands missing"
        return 1
    fi
}

# Set up chroot for Z-FORGE
setup_for_zforge() {
    echo "5. Setting up chroot for Z-FORGE..."
    
    # Copy hosts file for network access
    echo "   Copying network configuration..."
    sudo cp /etc/hosts "$CHROOT_PATH/etc/hosts"
    
    # Mount filesystems
    echo "   Mounting filesystems..."
    sudo mount -t proc proc "$CHROOT_PATH/proc"
    sudo mount -t sysfs sysfs "$CHROOT_PATH/sys"
    sudo mount --bind /dev "$CHROOT_PATH/dev"
    sudo mount -t devpts devpts "$CHROOT_PATH/dev/pts"
    
    # Update package lists
    echo "   Updating package lists in chroot..."
    if sudo chroot "$CHROOT_PATH" /bin/bash -c '
        export DEBIAN_FRONTEND=noninteractive
        export LC_ALL=C
        export LANG=C
        apt-get update
    '; then
        echo "   ✓ Package lists updated"
        return 0
    else
        echo "   ⚠ Package update had issues (may still work)"
        return 1
    fi
}

# Test package installation
test_package_installation() {
    echo "6. Testing package installation..."
    
    echo "   Installing test package (nano)..."
    if sudo chroot "$CHROOT_PATH" /bin/bash -c '
        export DEBIAN_FRONTEND=noninteractive
        export LC_ALL=C
        export LANG=C
        apt-get install -y nano
    '; then
        echo "   ✓ Package installation working"
        return 0
    else
        echo "   ✗ Package installation failed"
        return 1
    fi
}

# Main execution
main() {
    echo "This script will fix the incomplete chroot installation"
    echo "Target: $CHROOT_PATH"
    echo
    
    if check_chroot_state; then
        echo "Chroot appears to be working. Testing Z-FORGE compatibility..."
        setup_for_zforge
        
        if test_package_installation; then
            echo
            echo "=== Chroot is Working ✓ ==="
            echo "Resume Z-FORGE build:"
            echo "sudo python3 builder/z-forge.py --build-spec build_spec.yml --resume"
        else
            echo
            echo "=== Chroot Needs Recreation ⚠ ==="
            echo "Package installation is failing, recreating chroot..."
            clean_and_recreate
            run_minimal_debootstrap
            verify_chroot
            setup_for_zforge
        fi
    else
        echo "Chroot is incomplete or corrupted. Recreating..."
        clean_and_recreate
        
        if run_minimal_debootstrap; then
            if verify_chroot; then
                if setup_for_zforge; then
                    if test_package_installation; then
                        echo
                        echo "=== Chroot Fixed Successfully ✓ ==="
                        echo "Fresh chroot created and tested"
                        echo
                        echo "Resume Z-FORGE build:"
                        echo "sudo python3 builder/z-forge.py --build-spec build_spec.yml --resume"
                    else
                        echo
                        echo "=== Chroot Created but Package Issues ⚠ ==="
                        echo "Basic chroot works but package installation has issues"
                        echo "Try running Z-FORGE build anyway"
                    fi
                else
                    echo
                    echo "=== Chroot Setup Issues ⚠ ==="
                    echo "Chroot created but network setup failed"
                fi
            else
                echo
                echo "=== Chroot Verification Failed ✗ ==="
                echo "Debootstrap completed but chroot is not functional"
            fi
        else
            echo
            echo "=== Debootstrap Failed ✗ ==="
            echo "Could not create minimal chroot"
            echo "Check network connectivity and try again"
        fi
    fi
}

# Run main function
main "$@"