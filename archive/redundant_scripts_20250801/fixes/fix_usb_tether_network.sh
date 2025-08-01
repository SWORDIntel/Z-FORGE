#!/bin/bash
# Comprehensive USB tether network fix for Z-FORGE

set -e

echo "=== USB Tether Network Fix for Z-FORGE ==="

# Check USB tether connection
check_usb_tether() {
    echo "1. Checking USB tether connection..."
    
    # Look for USB network interfaces
    local usb_interfaces=$(ip link show | grep -E "(usb|rndis|cdc)" | head -3)
    if [ -n "$usb_interfaces" ]; then
        echo "   Found USB network interfaces:"
        echo "$usb_interfaces" | sed 's/^/     /'
    else
        echo "   No obvious USB network interfaces found"
    fi
    
    # Check default route
    local default_route=$(ip route show default 2>/dev/null | head -1)
    if [ -n "$default_route" ]; then
        echo "   Default route: $default_route"
    else
        echo "   ⚠ No default route found"
    fi
    
    # Check if we can reach gateway
    local gateway=$(ip route show default | awk '{print $3}' | head -1)
    if [ -n "$gateway" ]; then
        echo "   Testing gateway connectivity..."
        if ping -c 1 -W 3 "$gateway" >/dev/null 2>&1; then
            echo "   ✓ Gateway $gateway is reachable"
            return 0
        else
            echo "   ✗ Gateway $gateway is NOT reachable"
            return 1
        fi
    else
        echo "   ✗ No gateway found"
        return 1
    fi
}

# Fix host network configuration
fix_host_network() {
    echo "2. Fixing host network configuration..."
    
    # Get the USB interface name
    local usb_interface=$(ip route show default | awk '{print $5}' | head -1)
    if [ -z "$usb_interface" ]; then
        # Try to find USB interface manually
        usb_interface=$(ip link show | grep -E "(usb|rndis|cdc)" | awk -F: '{print $2}' | tr -d ' ' | head -1)
    fi
    
    if [ -n "$usb_interface" ]; then
        echo "   Using interface: $usb_interface"
        
        # Restart the interface
        echo "   Restarting network interface..."
        sudo ip link set "$usb_interface" down 2>/dev/null || true
        sleep 2
        sudo ip link set "$usb_interface" up 2>/dev/null || true
        sleep 3
        
        # Try to get DHCP lease
        echo "   Requesting DHCP lease..."
        sudo dhclient -r "$usb_interface" 2>/dev/null || true
        sudo dhclient "$usb_interface" 2>/dev/null || true
        sleep 3
    else
        echo "   ⚠ Could not identify USB interface"
    fi
}

# Create fallback DNS configuration
create_fallback_dns() {
    echo "3. Creating fallback DNS configuration..."
    
    # Create a temporary resolv.conf
    local temp_resolv="/tmp/resolv.conf.zforge"
    cat > "$temp_resolv" << 'EOF'
# Fallback DNS for USB tethering
nameserver 9.9.9.9
nameserver 8.8.8.8
nameserver 1.1.1.1
nameserver 8.8.4.4
nameserver 208.67.222.222
nameserver 208.67.220.220
options timeout:10
options attempts:2
options rotate
EOF
    
    # Try to use it
    if [ -L "/etc/resolv.conf" ]; then
        echo "   /etc/resolv.conf is a symlink, creating backup and replacing..."
        sudo cp "/etc/resolv.conf" "/etc/resolv.conf.backup" 2>/dev/null || true
        sudo rm "/etc/resolv.conf" 2>/dev/null || true
        sudo cp "$temp_resolv" "/etc/resolv.conf"
    else
        echo "   Backing up and replacing /etc/resolv.conf..."
        sudo cp "/etc/resolv.conf" "/etc/resolv.conf.backup" 2>/dev/null || true
        sudo cp "$temp_resolv" "/etc/resolv.conf"
    fi
    
    echo "   ✓ Fallback DNS configuration created"
    rm -f "$temp_resolv"
}

# Test and fix DNS step by step
test_dns_step_by_step() {
    echo "4. Testing DNS step by step..."
    
    # Test each DNS server individually
    local dns_servers=("9.9.9.9" "8.8.8.8" "1.1.1.1" "8.8.4.4")
    local working_dns=""
    
    for dns in "${dns_servers[@]}"; do
        echo "   Testing DNS server: $dns"
        if nslookup deb.debian.org "$dns" >/dev/null 2>&1; then
            echo "   ✓ DNS server $dns is working"
            working_dns="$dns"
            break
        else
            echo "   ✗ DNS server $dns failed"
        fi
    done
    
    if [ -n "$working_dns" ]; then
        echo "   ✓ Found working DNS: $working_dns"
        
        # Create minimal resolv.conf with just the working DNS
        sudo tee /etc/resolv.conf > /dev/null << EOF
nameserver $working_dns
options timeout:15
options attempts:1
EOF
        return 0
    else
        echo "   ✗ No DNS servers are working"
        return 1
    fi
}

# Fix chroot with working DNS
fix_chroot_with_working_dns() {
    echo "5. Configuring chroot with working DNS..."
    
    # Copy the working host DNS to chroot
    if [ -f "/etc/resolv.conf" ]; then
        sudo cp /etc/resolv.conf ${CHROOT_PATH:-/home/john/zforge_workspace/chroot}/etc/resolv.conf
        echo "   ✓ Copied working DNS config to chroot"
    else
        echo "   ✗ No working DNS config to copy"
        return 1
    fi
    
    # Fix locale issue in chroot
    echo "   Fixing locale issues in chroot..."
    sudo chroot ${CHROOT_PATH:-/home/john/zforge_workspace/chroot} /bin/bash -c '
        export LC_ALL=C
        export LANG=C
        export DEBIAN_FRONTEND=noninteractive
    ' 2>/dev/null || true
    
    # Test chroot DNS
    echo "   Testing chroot DNS..."
    if sudo chroot ${CHROOT_PATH:-/home/john/zforge_workspace/chroot} /bin/bash -c '
        export LC_ALL=C
        export LANG=C
        nslookup deb.debian.org >/dev/null 2>&1
    '; then
        echo "   ✓ Chroot DNS working"
        return 0
    else
        echo "   ✗ Chroot DNS still not working"
        return 1
    fi
}

# Configure APT with minimal settings
configure_minimal_apt() {
    echo "6. Configuring APT with minimal reliable settings..."
    
    sudo tee ${CHROOT_PATH:-/home/john/zforge_workspace/chroot}/etc/apt/apt.conf.d/99-zforge-minimal > /dev/null << 'EOF'
// Minimal reliable APT configuration
Acquire::Retries "10";
Acquire::http::Timeout "300";
Acquire::https::Timeout "300";
Acquire::http::Pipeline-Depth "0";
APT::Get::Assume-Yes "true";
APT::Install-Recommends "false";
APT::Install-Suggests "false";
Dpkg::Progress-Fancy "false";
Dpkg::Use-Pty "0";
APT::Color "0";
APT::Get::AllowUnauthenticated "true";
EOF
    
    echo "   ✓ Minimal APT configuration applied"
}

# Final test
final_test() {
    echo "7. Final connectivity test..."
    
    # Test host
    echo "   Testing host connectivity to Debian repository..."
    if curl -s --connect-timeout 10 --max-time 30 http://deb.debian.org/debian/ls-lR.gz | head -n 1 >/dev/null 2>&1; then
        echo "   ✓ Host can reach Debian repository"
    else
        echo "   ⚠ Host cannot reach Debian repository"
    fi
    
    # Test chroot
    echo "   Testing chroot connectivity..."
    if sudo chroot ${CHROOT_PATH:-/home/john/zforge_workspace/chroot} /bin/bash -c '
        export LC_ALL=C
        export LANG=C
        export DEBIAN_FRONTEND=noninteractive
        curl -s --connect-timeout 10 --max-time 30 http://deb.debian.org/debian/ls-lR.gz | head -n 1 >/dev/null 2>&1
    '; then
        echo "   ✓ Chroot can reach Debian repository"
        return 0
    else
        echo "   ✗ Chroot cannot reach Debian repository"
        return 1
    fi
}

# Main execution
main() {
    echo "Comprehensive fix for USB tethered network connectivity"
    echo "This will attempt multiple approaches to fix the connection"
    echo
    
    # Check if chroot exists
    if [ ! -d "${CHROOT_PATH:-/home/john/zforge_workspace/chroot}" ]; then
        echo "✗ Chroot directory not found"
        exit 1
    fi
    
    # Step-by-step fixes
    if check_usb_tether; then
        echo "   USB tether appears to be working"
    else
        echo "   USB tether has issues, attempting to fix..."
        fix_host_network
        sleep 5
        
        if ! check_usb_tether; then
            echo "   ⚠ USB tether still has issues, trying DNS workarounds..."
        fi
    fi
    
    create_fallback_dns
    
    if test_dns_step_by_step; then
        if fix_chroot_with_working_dns; then
            configure_minimal_apt
            
            if final_test; then
                echo
                echo "=== Network Fix Successful ✓ ==="
                echo "USB tether network is working for both host and chroot"
                echo
                echo "Resume Z-FORGE build:"
                echo "sudo python3 builder/z-forge.py --build-spec build_spec.yml --resume"
            else
                echo
                echo "=== Partial Success ⚠ ==="
                echo "DNS is working but repository access is limited"
                echo "Try Z-FORGE build anyway (it might work):"
                echo "sudo python3 builder/z-forge.py --build-spec build_spec.yml --resume"
            fi
        else
            echo
            echo "=== Host Fixed, Chroot Issues ⚠ ==="
            echo "Host network is working but chroot has issues"
            echo "You may need to reconnect your USB tether"
        fi
    else
        echo
        echo "=== Network Fix Failed ✗ ==="
        echo "Unable to establish working network connection"
        echo "Try:"
        echo "1. Reconnect your USB tether device"
        echo "2. Switch to a different USB port"
        echo "3. Try mobile hotspot instead of USB tether"
        echo "4. Run this script again after reconnecting"
    fi
}

# Run main function
main "$@"