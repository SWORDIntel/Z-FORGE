#!/bin/bash
# Clean workspace and restart Z-FORGE build with working network

set -e

echo "=== Clean Workspace and Restart Z-FORGE Build ==="

WORKSPACE="/tmp/zforge_workspace"

# Clean existing workspace
clean_workspace() {
    echo "1. Cleaning existing workspace..."
    
    if [ -d "$WORKSPACE" ]; then
        echo "   Unmounting any mounted filesystems..."
        sudo umount "$WORKSPACE/chroot"/{dev/pts,dev,sys,proc} 2>/dev/null || true
        
        echo "   Removing workspace directory..."
        sudo rm -rf "$WORKSPACE"
        echo "   ✓ Workspace cleaned"
    else
        echo "   ✓ No existing workspace to clean"
    fi
}

# Set up proper host DNS
setup_host_dns() {
    echo "2. Setting up host DNS for network connectivity..."
    
    # Since DoH worked, let's use a direct approach with working IPs
    # Get Debian repo IP from our previous DoH query
    local debian_ip="151.101.2.132"  # From the DoH response
    
    # Create temporary hosts entry
    if ! grep -q "deb.debian.org" /etc/hosts 2>/dev/null; then
        echo "   Adding Debian repository to /etc/hosts..."
        echo "$debian_ip deb.debian.org" | sudo tee -a /etc/hosts
        echo "$debian_ip security.debian.org" | sudo tee -a /etc/hosts
        echo "$debian_ip ftp.debian.org" | sudo tee -a /etc/hosts
        echo "   ✓ Added repository entries to hosts file"
    else
        echo "   ✓ Repository entries already in hosts file"
    fi
}

# Test network connectivity
test_network() {
    echo "3. Testing network connectivity..."
    
    # Test repository access
    if curl -s --connect-timeout 10 --max-time 30 http://deb.debian.org/debian/ls-lR.gz | head -n 1 >/dev/null 2>&1; then
        echo "   ✓ Can reach Debian repository"
        return 0
    else
        echo "   ✗ Cannot reach Debian repository"
        return 1
    fi
}

# Configure debootstrap for our environment
configure_debootstrap() {
    echo "4. Configuring debootstrap environment..."
    
    # Set environment variables for stable network operation
    export DEBIAN_FRONTEND=noninteractive
    export LC_ALL=C
    export LANG=C
    
    # Create a custom debootstrap configuration
    mkdir -p ~/.debootstrap
    cat > ~/.debootstrap/config << 'EOF'
# Custom debootstrap configuration for USB tether
export DEBOOTSTRAP_OPTIONS="--verbose --no-check-gpg"
export DEBIAN_FRONTEND=noninteractive
EOF
    
    echo "   ✓ Debootstrap environment configured"
}

# Start Z-FORGE build
start_build() {
    echo "5. Starting Z-FORGE build..."
    
    echo "   Running: sudo python3 builder/z-forge.py --build-spec build_spec.yml"
    echo "   This will create a fresh debootstrap installation"
    echo
    
    # Add a small delay to ensure network is stable
    echo "   Waiting 5 seconds for network stability..."
    sleep 5
    
    sudo python3 builder/z-forge.py --build-spec build_spec.yml
}

# Alternative: Manual debootstrap with our network fix
manual_debootstrap() {
    echo "5. Alternative: Manual debootstrap with network fixes..."
    
    # Create workspace
    sudo mkdir -p "$WORKSPACE"
    
    # Run minimal debootstrap first
    echo "   Running minimal debootstrap..."
    local cmd=(
        sudo debootstrap
        --arch=amd64
        --variant=minbase
        --no-check-gpg
        trixie
        "$WORKSPACE/chroot"
        http://deb.debian.org/debian
    )
    
    echo "   Command: ${cmd[*]}"
    
    if "${cmd[@]}"; then
        echo "   ✓ Minimal debootstrap successful"
        
        # Set up chroot with network access
        echo "   Setting up chroot network..."
        
        # Copy hosts file to chroot
        sudo cp /etc/hosts "$WORKSPACE/chroot/etc/hosts"
        
        # Mount filesystems
        sudo mount -t proc proc "$WORKSPACE/chroot/proc"
        sudo mount -t sysfs sysfs "$WORKSPACE/chroot/sys"
        sudo mount --bind /dev "$WORKSPACE/chroot/dev"
        sudo mount -t devpts devpts "$WORKSPACE/chroot/dev/pts"
        
        # Install additional packages manually
        echo "   Installing additional packages in chroot..."
        sudo chroot "$WORKSPACE/chroot" /bin/bash -c '
            export DEBIAN_FRONTEND=noninteractive
            export LC_ALL=C
            export LANG=C
            apt-get update
            apt-get install -y locales linux-base sudo bash-completion apt-transport-https ca-certificates curl wget gnupg gpgv
        '
        
        if [ $? -eq 0 ]; then
            echo "   ✓ Manual debootstrap completed successfully"
            echo
            echo "   Now run Z-FORGE build:"
            echo "   sudo python3 builder/z-forge.py --build-spec build_spec.yml --resume"
            return 0
        else
            echo "   ✗ Package installation failed"
            return 1
        fi
    else
        echo "   ✗ Minimal debootstrap failed"
        return 1
    fi
}

# Main execution
main() {
    echo "This script will clean the workspace and restart Z-FORGE with network fixes"
    echo
    
    clean_workspace
    setup_host_dns
    
    if test_network; then
        configure_debootstrap
        
        echo
        echo "=== Ready to Start Build ==="
        echo "Choose approach:"
        echo "1. Let Z-FORGE handle debootstrap (recommended)"
        echo "2. Manual debootstrap first, then Z-FORGE"
        echo
        read -p "Enter choice (1 or 2): " choice
        
        case $choice in
            1)
                start_build
                ;;
            2)
                if manual_debootstrap; then
                    echo "Manual debootstrap successful. Now you can run:"
                    echo "sudo python3 builder/z-forge.py --build-spec build_spec.yml --resume"
                fi
                ;;
            *)
                echo "Invalid choice. Running default option 1..."
                start_build
                ;;
        esac
    else
        echo
        echo "=== Network Issues Detected ==="
        echo "Repository access is not working"
        echo "Try:"
        echo "1. Reconnect your USB tether"
        echo "2. Check mobile data connection"
        echo "3. Run this script again"
    fi
}

# Run main function
main "$@"