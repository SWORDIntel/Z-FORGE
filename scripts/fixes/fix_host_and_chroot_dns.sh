#!/bin/bash
# Fix DNS for both host and chroot

set -e

echo "=== Fixing DNS for Host and Chroot ==="

# Fix host DNS first (for USB tethering)
fix_host_dns() {
    echo "1. Fixing host DNS configuration..."
    
    if [ ! -f "/etc/resolv.conf" ]; then
        echo "   Creating host /etc/resolv.conf..."
        sudo tee /etc/resolv.conf > /dev/null << 'EOF'
# DNS configuration for USB tethering
nameserver 9.9.9.9
nameserver 8.8.8.8
nameserver 1.1.1.1
nameserver 8.8.4.4
options timeout:10
options attempts:3
EOF
        echo "   ✓ Host DNS configuration created"
    else
        echo "   ✓ Host /etc/resolv.conf already exists"
    fi
    
    # Test host DNS
    echo "   Testing host DNS resolution..."
    if nslookup deb.debian.org >/dev/null 2>&1; then
        echo "   ✓ Host DNS working"
    else
        echo "   ⚠ Host DNS not working (USB tether may need reconnection)"
    fi
}

# Run the existing chroot network fix
fix_chroot_network() {
    echo "2. Running chroot network fix..."
    
    if [ -f "./fix_existing_chroot_network.sh" ]; then
        chmod +x ./fix_existing_chroot_network.sh
        ./fix_existing_chroot_network.sh
    else
        echo "   ✗ fix_existing_chroot_network.sh not found"
        return 1
    fi
}

# Main execution
main() {
    echo "Fixing DNS configuration for USB tethered connection"
    echo
    
    fix_host_dns
    echo
    fix_chroot_network
    
    echo
    echo "=== DNS Fix Complete ==="
    echo "Both host and chroot should now have working DNS"
    echo
    echo "Resume Z-FORGE build with:"
    echo "sudo python3 builder/z-forge.py --build-spec build_spec.yml --resume"
}

# Run main function
main "$@"