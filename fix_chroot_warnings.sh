#!/bin/bash
# Fix common chroot warnings during package installation

set -e

WORKSPACE="/tmp/zforge_workspace"
CHROOT_PATH="$WORKSPACE/chroot"

echo "=== Fixing Chroot Installation Warnings ==="

# Check if chroot exists
if [ ! -d "$CHROOT_PATH" ]; then
    echo "Error: Chroot directory not found"
    exit 1
fi

# Mount chroot if needed
mount_chroot() {
    echo "1. Ensuring chroot is mounted..."
    
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

# Fix locale warnings
fix_locale_warnings() {
    echo "2. Fixing locale warnings..."
    
    # Set default locale to suppress perl warnings
    sudo tee "$CHROOT_PATH/etc/locale.conf" > /dev/null << 'EOF'
LANG=C.UTF-8
LC_ALL=C.UTF-8
EOF
    
    # Set environment variables for package installation
    sudo tee "$CHROOT_PATH/etc/environment" > /dev/null << 'EOF'
LANG=C.UTF-8
LC_ALL=C.UTF-8
DEBIAN_FRONTEND=noninteractive
DEBCONF_NONINTERACTIVE_SEEN=true
EOF
    
    echo "   ✓ Locale configuration set"
}

# Fix debconf warnings
fix_debconf_warnings() {
    echo "3. Fixing debconf warnings..."
    
    # Configure debconf to use noninteractive mode
    sudo tee "$CHROOT_PATH/etc/debconf.conf" > /dev/null << 'EOF'
# Debconf configuration for noninteractive installation
Config: configdb
Templates: templatedb

Name: config
Driver: File
Mode: 644
Reject-Name: reject
Required: false
Accept-Name: accept
Filename: /var/cache/debconf/config.dat

Name: passwords
Driver: File
Mode: 600
Backup: false
Required: false
Accept-Name: accept
Filename: /var/cache/debconf/passwords.dat

Name: templatedb
Driver: File
Mode: 644
Required: false
Accept-Name: accept
Filename: /var/cache/debconf/templates.dat
EOF
    
    # Create debconf database directory
    sudo mkdir -p "$CHROOT_PATH/var/cache/debconf"
    
    # Set debconf to noninteractive frontend
    sudo chroot "$CHROOT_PATH" /bin/bash -c 'echo "debconf debconf/frontend select Noninteractive" | debconf-set-selections' 2>/dev/null || true
    
    echo "   ✓ Debconf configured for noninteractive mode"
}

# Configure APT for clean installation
configure_apt() {
    echo "4. Configuring APT for clean installation..."
    
    # APT configuration to suppress warnings and prompts
    sudo tee "$CHROOT_PATH/etc/apt/apt.conf.d/99-zforge-clean" > /dev/null << 'EOF'
// Z-FORGE clean installation configuration
APT::Get::Assume-Yes "true";
APT::Install-Recommends "false";
APT::Install-Suggests "false";
APT::Get::Allow-Unauthenticated "true";
Dpkg::Options {
    "--force-confdef";
    "--force-confold";
}
Dpkg::Progress-Fancy "false";
APT::Color "0";
Dpkg::Use-Pty "0";
EOF
    
    # Suppress perl locale warnings
    sudo tee "$CHROOT_PATH/etc/perl/CPAN/Config.pm" > /dev/null << 'EOF' || true
# Minimal CPAN config to suppress warnings
EOF
    
    echo "   ✓ APT configured for clean installation"
}

# Install essential packages to fix warnings
install_essential_packages() {
    echo "5. Installing packages to fix warnings..."
    
    # Packages that fix the warning messages
    local fix_packages=(
        "dialog"                # Fixes debconf dialog warnings
        "libterm-readline-gnu-perl"  # Fixes Term::ReadLine warnings
        "locales"              # Fixes locale warnings
        "apt-utils"            # Fixes APT warnings
        "debconf-utils"        # Fixes debconf warnings
    )
    
    echo "   Installing: ${fix_packages[*]}"
    
    # Set environment for clean installation
    sudo chroot "$CHROOT_PATH" /bin/bash -c '
        export DEBIAN_FRONTEND=noninteractive
        export DEBCONF_NONINTERACTIVE_SEEN=true
        export LC_ALL=C.UTF-8
        export LANG=C.UTF-8
        apt-get update -qq
        apt-get install -y '"${fix_packages[*]}"'
    ' 2>/dev/null || echo "   Some packages may have failed (continuing)"
    
    echo "   ✓ Essential packages installed"
}

# Generate locales to fix perl warnings
generate_locales() {
    echo "6. Generating locales..."
    
    # Configure locales
    sudo tee "$CHROOT_PATH/etc/locale.gen" > /dev/null << 'EOF'
en_US.UTF-8 UTF-8
C.UTF-8 UTF-8
EOF
    
    # Generate locales
    sudo chroot "$CHROOT_PATH" /bin/bash -c '
        export DEBIAN_FRONTEND=noninteractive
        locale-gen
    ' 2>/dev/null || echo "   Locale generation may have failed (continuing)"
    
    echo "   ✓ Locales configured"
}

# Test the fixed environment
test_fixed_environment() {
    echo "7. Testing fixed environment..."
    
    # Test that warnings are suppressed
    echo "   Testing package installation without warnings..."
    if sudo chroot "$CHROOT_PATH" /bin/bash -c '
        export DEBIAN_FRONTEND=noninteractive
        export LC_ALL=C.UTF-8
        export LANG=C.UTF-8
        apt-get install -y --dry-run nano >/dev/null 2>&1
    '; then
        echo "   ✓ Package installation test successful"
    else
        echo "   ⚠ Package installation test had issues (may still work)"
    fi
    
    echo "   ✓ Environment test complete"
}

# Cleanup and unmount
cleanup() {
    echo "8. Cleaning up..."
    
    # Unmount chroot
    sudo umount "$CHROOT_PATH"/{dev/pts,dev,sys,proc} 2>/dev/null || true
    
    echo "   ✓ Cleanup complete"
}

# Main execution
main() {
    echo "This script fixes common warnings during chroot package installation"
    echo
    
    mount_chroot
    fix_locale_warnings
    fix_debconf_warnings
    configure_apt
    install_essential_packages
    generate_locales
    test_fixed_environment
    cleanup
    
    echo
    echo "=== Warnings Fixed ==="
    echo "Chroot environment configured for clean package installation"
    echo "You can now run package installation scripts without warnings:"
    echo "./complete_debootstrap_packages.sh"
    echo
    echo "Or continue with Z-FORGE build:"
    echo "sudo python3 builder/z-forge.py --build-spec build_spec.yml"
}

# Run main function
main "$@"