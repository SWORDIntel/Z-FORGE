#!/bin/bash
# Fix network connectivity for existing Z-FORGE chroot

set -e

WORKSPACE="${ZFORGE_WORKSPACE:-/home/john/zforge_workspace}"
CHROOT_PATH="$WORKSPACE/chroot"

echo "=== Fixing Network for Existing Z-FORGE Chroot ==="

# Check if chroot exists
if [ ! -d "$CHROOT_PATH" ] || [ ! -f "$CHROOT_PATH/bin/bash" ]; then
    echo "Error: No existing chroot found at $CHROOT_PATH"
    exit 1
fi

echo "Found existing chroot, fixing network connectivity..."

# Fix DNS resolution
fix_dns() {
    echo "1. Fixing DNS resolution..."
    
    # Check if host has resolv.conf and copy it if available
    if [ -f "/etc/resolv.conf" ]; then
        echo "   Using host DNS configuration..."
        sudo cp /etc/resolv.conf "$CHROOT_PATH/etc/resolv.conf"
    else
        echo "   Host missing /etc/resolv.conf, creating fallback DNS config..."
    fi
    
    # Always create a robust fallback DNS config (overwrites any existing)
    sudo tee "$CHROOT_PATH/etc/resolv.conf" > /dev/null << 'EOF'
# DNS servers for tethered connections
nameserver 9.9.9.9
nameserver 8.8.8.8  
nameserver 1.1.1.1
nameserver 8.8.4.4
options timeout:10
options attempts:3
options rotate
EOF
    
    echo "   ✓ DNS configuration updated"
}

# Mount necessary filesystems
mount_filesystems() {
    echo "2. Ensuring filesystems are mounted..."
    
    # Mount proc if not mounted
    if ! mountpoint -q "$CHROOT_PATH/proc" 2>/dev/null; then
        sudo mount -t proc proc "$CHROOT_PATH/proc"
        echo "   ✓ Mounted /proc"
    else
        echo "   ✓ /proc already mounted"
    fi
    
    # Mount sys if not mounted
    if ! mountpoint -q "$CHROOT_PATH/sys" 2>/dev/null; then
        sudo mount -t sysfs sysfs "$CHROOT_PATH/sys"
        echo "   ✓ Mounted /sys"
    else
        echo "   ✓ /sys already mounted"
    fi
    
    # Mount dev if not mounted
    if ! mountpoint -q "$CHROOT_PATH/dev" 2>/dev/null; then
        sudo mount --bind /dev "$CHROOT_PATH/dev"
        echo "   ✓ Mounted /dev"
    else
        echo "   ✓ /dev already mounted"
    fi
    
    # Mount dev/pts if not mounted
    if ! mountpoint -q "$CHROOT_PATH/dev/pts" 2>/dev/null; then
        sudo mount -t devpts devpts "$CHROOT_PATH/dev/pts"
        echo "   ✓ Mounted /dev/pts"
    else
        echo "   ✓ /dev/pts already mounted"
    fi
}

# Test and fix network connectivity
test_and_fix_network() {
    echo "3. Testing and fixing network connectivity..."
    
    # Test DNS resolution
    echo "   Testing DNS resolution..."
    if sudo chroot "$CHROOT_PATH" /bin/bash -c 'nslookup deb.debian.org >/dev/null 2>&1'; then
        echo "   ✓ DNS resolution working"
    else
        echo "   ⚠ DNS resolution failed, trying alternative..."
        
        # Try alternative DNS servers
        sudo tee "$CHROOT_PATH/etc/resolv.conf" > /dev/null << 'EOF'
nameserver 1.1.1.1
nameserver 8.8.8.8
nameserver 9.9.9.9
options timeout:15
options attempts:5
EOF
        
        if sudo chroot "$CHROOT_PATH" /bin/bash -c 'nslookup deb.debian.org >/dev/null 2>&1'; then
            echo "   ✓ DNS working with alternative servers"
        else
            echo "   ✗ DNS still failing"
        fi
    fi
    
    # Test HTTP connectivity
    echo "   Testing repository connectivity..."
    if sudo chroot "$CHROOT_PATH" /bin/bash -c 'curl -s --connect-timeout 10 --max-time 30 http://deb.debian.org/debian/ls-lR.gz | head -n 1 >/dev/null 2>&1'; then
        echo "   ✓ Repository connectivity working"
    else
        echo "   ⚠ Repository connectivity issues"
    fi
}

# Update APT for better reliability
update_apt_config() {
    echo "4. Updating APT configuration for better reliability..."
    
    # Create APT config optimized for unstable connections
    sudo tee "$CHROOT_PATH/etc/apt/apt.conf.d/99-network-reliability" > /dev/null << 'EOF'
// Network reliability optimizations
Acquire::Retries "5";
Acquire::http::Timeout "60";
Acquire::https::Timeout "60";
Acquire::ftp::Timeout "60";
Acquire::http::Pipeline-Depth "0";
Acquire::BrokenProxy "true";
APT::Get::Assume-Yes "true";
APT::Install-Recommends "false";
APT::Install-Suggests "false";
Dpkg::Progress-Fancy "false";
EOF
    
    echo "   ✓ APT configured for network reliability"
}

# Refresh APT cache
refresh_apt() {
    echo "5. Refreshing APT package cache..."
    
    # Try to update package lists with retries
    local attempts=0
    local max_attempts=3
    
    while [ $attempts -lt $max_attempts ]; do
        attempts=$((attempts + 1))
        echo "   Attempt $attempts/$max_attempts: apt-get update"
        
        if sudo chroot "$CHROOT_PATH" /bin/bash -c '
            export DEBIAN_FRONTEND=noninteractive
            apt-get update 2>/dev/null
        '; then
            echo "   ✓ APT cache updated successfully"
            return 0
        else
            if [ $attempts -lt $max_attempts ]; then
                echo "   Retrying in 10 seconds..."
                sleep 10
            else
                echo "   ⚠ APT update failed after $max_attempts attempts"
                echo "   Will try with --fix-missing during build"
            fi
        fi
    done
}

# Test package installation
test_package_install() {
    echo "6. Testing package installation..."
    
    # Try a simple package install test
    if sudo chroot "$CHROOT_PATH" /bin/bash -c '
        export DEBIAN_FRONTEND=noninteractive
        apt-get install -y --dry-run nano >/dev/null 2>&1
    '; then
        echo "   ✓ Package installation test successful"
    else
        echo "   ⚠ Package installation test failed"
        echo "   Build may encounter issues with package downloads"
    fi
}

# Main execution
main() {
    echo "Fixing network connectivity for existing Z-FORGE chroot"
    echo "Chroot location: $CHROOT_PATH"
    echo
    
    fix_dns
    mount_filesystems
    test_and_fix_network
    update_apt_config
    refresh_apt
    test_package_install
    
    echo
    echo "=== Network Fix Complete ==="
    echo "Your existing chroot should now have working network connectivity"
    echo
    echo "Resume Z-FORGE build with:"
    echo "sudo python3 builder/z-forge.py --build-spec build_spec.yml --resume"
    echo
    echo "If you still get network errors, try switching your USB tether connection"
    echo "or run this script again if the connection stabilizes"
}

# Run main function
main "$@"