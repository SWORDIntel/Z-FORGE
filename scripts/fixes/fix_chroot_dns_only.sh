#!/bin/bash
# Fix DNS in chroot only - host network is working

set -e

echo "=== Fixing Chroot DNS (Host Network is Working) ==="

# Extract working DNS from DoH response
extract_dns_from_doh() {
    echo "1. Getting Debian repository IP addresses from DNS over HTTPS..."
    
    local ips=$(curl -s -H "accept: application/dns-json" "https://1.1.1.1/dns-query?name=deb.debian.org&type=A" | \
               grep -o '"data":"[0-9.]*"' | cut -d'"' -f4)
    
    if [ -n "$ips" ]; then
        echo "   Found Debian repository IPs:"
        echo "$ips" | sed 's/^/     /'
        echo "$ips"
    else
        echo "   Could not extract IPs"
        return 1
    fi
}

# Create hosts file workaround
create_hosts_workaround() {
    echo "2. Creating /etc/hosts workaround for chroot..."
    
    local debian_ips=$(extract_dns_from_doh)
    local primary_ip=$(echo "$debian_ips" | head -n1)
    
    if [ -n "$primary_ip" ]; then
        echo "   Using primary IP: $primary_ip"
        
        # Add to chroot hosts file
        sudo tee -a /tmp/zforge_workspace/chroot/etc/hosts > /dev/null << EOF

# Z-FORGE DNS workaround
$primary_ip deb.debian.org
$primary_ip security.debian.org
$primary_ip ftp.debian.org
EOF
        
        echo "   ✓ Added Debian repository entries to chroot /etc/hosts"
        return 0
    else
        echo "   ✗ Could not get repository IP"
        return 1
    fi
}

# Test chroot connectivity with hosts file
test_chroot_with_hosts() {
    echo "3. Testing chroot connectivity with hosts file..."
    
    # Test basic connectivity to repository
    if sudo chroot /tmp/zforge_workspace/chroot /bin/bash -c '
        export LC_ALL=C
        export LANG=C
        export DEBIAN_FRONTEND=noninteractive
        curl -s --connect-timeout 10 --max-time 30 http://deb.debian.org/debian/ls-lR.gz | head -n 1 >/dev/null 2>&1
    '; then
        echo "   ✓ Chroot can reach Debian repository via hosts file"
        return 0
    else
        echo "   ✗ Chroot still cannot reach repository"
        return 1
    fi
}

# Configure APT for hosts file usage
configure_apt_for_hosts() {
    echo "4. Configuring APT for hosts file usage..."
    
    sudo tee /tmp/zforge_workspace/chroot/etc/apt/apt.conf.d/99-zforge-hosts > /dev/null << 'EOF'
// APT configuration for hosts file DNS workaround
Acquire::Retries "3";
Acquire::http::Timeout "120";
Acquire::https::Timeout "120";
Acquire::http::Pipeline-Depth "0";
APT::Get::Assume-Yes "true";
APT::Install-Recommends "false";
APT::Install-Suggests "false";
Dpkg::Progress-Fancy "false";
Dpkg::Use-Pty "0";
APT::Color "0";
EOF
    
    echo "   ✓ APT configured for hosts file usage"
}

# Test APT update
test_apt_update() {
    echo "5. Testing APT update in chroot..."
    
    if sudo chroot /tmp/zforge_workspace/chroot /bin/bash -c '
        export LC_ALL=C
        export LANG=C
        export DEBIAN_FRONTEND=noninteractive
        apt-get update >/dev/null 2>&1
    '; then
        echo "   ✓ APT update successful"
        return 0
    else
        echo "   Testing with verbose output..."
        sudo chroot /tmp/zforge_workspace/chroot /bin/bash -c '
            export LC_ALL=C
            export LANG=C
            export DEBIAN_FRONTEND=noninteractive
            apt-get update 2>&1 | head -20
        '
        return 1
    fi
}

# Alternative: Copy host DNS config
copy_host_dns() {
    echo "6. Alternative: Copying host DNS configuration..."
    
    # Check if host has working resolv.conf
    if [ -f "/etc/resolv.conf" ]; then
        echo "   Copying host /etc/resolv.conf to chroot..."
        sudo cp /etc/resolv.conf /tmp/zforge_workspace/chroot/etc/resolv.conf
        
        # Test if this works
        if sudo chroot /tmp/zforge_workspace/chroot /bin/bash -c '
            export LC_ALL=C
            export LANG=C
            command -v host >/dev/null && host deb.debian.org >/dev/null 2>&1
        '; then
            echo "   ✓ Chroot DNS working with host configuration"
            return 0
        else
            echo "   ⚠ Host DNS config didn't work in chroot"
            return 1
        fi
    else
        echo "   ✗ No host resolv.conf to copy"
        return 1
    fi
}

# Main execution
main() {
    echo "Since your host network is working (DoH works), this will fix chroot DNS"
    echo
    
    # Check if chroot exists and is mounted
    if [ ! -d "/tmp/zforge_workspace/chroot" ]; then
        echo "✗ Chroot directory not found"
        exit 1
    fi
    
    # Ensure chroot is mounted
    if ! mountpoint -q /tmp/zforge_workspace/chroot/proc 2>/dev/null; then
        echo "   Mounting chroot filesystems..."
        sudo mount -t proc proc /tmp/zforge_workspace/chroot/proc
        sudo mount -t sysfs sysfs /tmp/zforge_workspace/chroot/sys
        sudo mount --bind /dev /tmp/zforge_workspace/chroot/dev
        sudo mount -t devpts devpts /tmp/zforge_workspace/chroot/dev/pts
    fi
    
    # Try hosts file workaround first
    if create_hosts_workaround; then
        configure_apt_for_hosts
        
        if test_chroot_with_hosts; then
            if test_apt_update; then
                echo
                echo "=== Chroot DNS Fixed with Hosts File ✓ ==="
                echo "Chroot can now access Debian repositories"
                echo
                echo "Resume Z-FORGE build:"
                echo "sudo python3 builder/z-forge.py --build-spec build_spec.yml --resume"
                exit 0
            else
                echo "   Repository access working but APT update failed"
            fi
        fi
    fi
    
    # Try copying host DNS as alternative
    if copy_host_dns; then
        if test_apt_update; then
            echo
            echo "=== Chroot DNS Fixed with Host Config ✓ ==="
            echo "Chroot DNS now working with host configuration"
            echo
            echo "Resume Z-FORGE build:"
            echo "sudo python3 builder/z-forge.py --build-spec build_spec.yml --resume"
            exit 0
        fi
    fi
    
    echo
    echo "=== Partial Fix ⚠ ==="
    echo "Repository IPs added to hosts file but APT may still have issues"
    echo "Try running Z-FORGE build anyway:"
    echo "sudo python3 builder/z-forge.py --build-spec build_spec.yml --resume"
}

# Run main function
main "$@"