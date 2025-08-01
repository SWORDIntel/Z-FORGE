#!/bin/bash
# Fix DNS for systemd-resolved systems with USB tethering

set -e

echo "=== Fixing DNS for systemd-resolved System ==="

# Check if systemd-resolved is running
check_systemd_resolved() {
    echo "1. Checking systemd-resolved status..."
    
    if systemctl is-active systemd-resolved >/dev/null 2>&1; then
        echo "   ✓ systemd-resolved is running"
        return 0
    else
        echo "   ✗ systemd-resolved is not running"
        return 1
    fi
}

# Configure systemd-resolved for USB tethering
configure_systemd_resolved() {
    echo "2. Configuring systemd-resolved for USB tethering..."
    
    # Create or update resolved.conf
    sudo tee /etc/systemd/resolved.conf > /dev/null << 'EOF'
[Resolve]
DNS=9.9.9.9 8.8.8.8 1.1.1.1 8.8.4.4
FallbackDNS=1.0.0.1 208.67.222.222
Domains=
DNSSEC=no
DNSOverTLS=no
Cache=yes
DNSStubListener=yes
ReadEtcHosts=yes
EOF

    echo "   ✓ systemd-resolved configuration updated"
    
    # Restart systemd-resolved
    echo "   Restarting systemd-resolved..."
    sudo systemctl restart systemd-resolved
    
    # Wait a moment for it to start
    sleep 2
    
    if systemctl is-active systemd-resolved >/dev/null 2>&1; then
        echo "   ✓ systemd-resolved restarted successfully"
    else
        echo "   ✗ systemd-resolved failed to restart"
        return 1
    fi
}

# Fix chroot DNS (bypass systemd-resolved)
fix_chroot_dns() {
    echo "3. Fixing chroot DNS (bypass systemd-resolved)..."
    
    # Create direct DNS config for chroot
    sudo tee ${CHROOT_PATH:-/home/john/zforge_workspace/chroot}/etc/resolv.conf > /dev/null << 'EOF'
# Direct DNS for chroot (bypasses systemd-resolved)
nameserver 9.9.9.9
nameserver 8.8.8.8
nameserver 1.1.1.1
nameserver 8.8.4.4
options timeout:15
options attempts:3
options rotate
options edns0
EOF
    
    echo "   ✓ Chroot DNS configured to bypass systemd-resolved"
}

# Mount chroot filesystems
mount_chroot() {
    echo "4. Mounting chroot filesystems..."
    
    local mounts=(
        "proc:proc:${CHROOT_PATH:-/home/john/zforge_workspace/chroot}/proc"
        "sysfs:sys:${CHROOT_PATH:-/home/john/zforge_workspace/chroot}/sys"
        "bind:dev:${CHROOT_PATH:-/home/john/zforge_workspace/chroot}/dev"
        "devpts:dev/pts:${CHROOT_PATH:-/home/john/zforge_workspace/chroot}/dev/pts"
    )
    
    for mount_spec in "${mounts[@]}"; do
        local type=$(echo "$mount_spec" | cut -d: -f1)
        local name=$(echo "$mount_spec" | cut -d: -f2)
        local path=$(echo "$mount_spec" | cut -d: -f3)
        
        if mountpoint -q "$path" 2>/dev/null; then
            echo "   ✓ $name already mounted"
        else
            case $type in
                "proc")
                    sudo mount -t proc proc "$path"
                    ;;
                "sysfs")
                    sudo mount -t sysfs sysfs "$path"
                    ;;
                "bind")
                    sudo mount --bind /dev "$path"
                    ;;
                "devpts")
                    sudo mount -t devpts devpts "$path"
                    ;;
            esac
            echo "   ✓ Mounted $name"
        fi
    done
}

# Configure APT for reliability
configure_apt() {
    echo "5. Configuring APT for network reliability..."
    
    sudo tee ${CHROOT_PATH:-/home/john/zforge_workspace/chroot}/etc/apt/apt.conf.d/99-zforge-network > /dev/null << 'EOF'
// Z-FORGE network reliability configuration
Acquire::Retries "5";
Acquire::http::Timeout "120";
Acquire::https::Timeout "120";
Acquire::ftp::Timeout "120";
Acquire::http::Pipeline-Depth "0";
Acquire::BrokenProxy "true";
Acquire::http::No-Cache "false";
Acquire::http::Max-Age "86400";
APT::Get::Assume-Yes "true";
APT::Install-Recommends "false";
APT::Install-Suggests "false";
Dpkg::Progress-Fancy "false";
Dpkg::Use-Pty "0";
APT::Color "0";
EOF

    echo "   ✓ APT configured for unreliable connections"
}

# Test DNS resolution
test_dns() {
    echo "6. Testing DNS resolution..."
    
    # Test host DNS
    echo "   Testing host DNS..."
    if nslookup deb.debian.org >/dev/null 2>&1; then
        echo "   ✓ Host DNS working"
    else
        echo "   ⚠ Host DNS not working"
        
        # Try resolvectl flush cache
        sudo resolvectl flush-caches 2>/dev/null || true
        
        if nslookup deb.debian.org >/dev/null 2>&1; then
            echo "   ✓ Host DNS working after cache flush"
        else
            echo "   ✗ Host DNS still not working"
        fi
    fi
    
    # Test chroot DNS
    echo "   Testing chroot DNS..."
    if sudo chroot ${CHROOT_PATH:-/home/john/zforge_workspace/chroot} /bin/bash -c 'nslookup deb.debian.org >/dev/null 2>&1'; then
        echo "   ✓ Chroot DNS working"
    else
        echo "   ✗ Chroot DNS not working"
        return 1
    fi
}

# Test APT functionality
test_apt() {
    echo "7. Testing APT functionality..."
    
    echo "   Testing APT update in chroot..."
    if sudo chroot ${CHROOT_PATH:-/home/john/zforge_workspace/chroot} /bin/bash -c '
        export DEBIAN_FRONTEND=noninteractive
        apt-get update >/dev/null 2>&1
    '; then
        echo "   ✓ APT update successful"
        return 0
    else
        echo "   ⚠ APT update failed (retrying with verbose output)..."
        
        # Retry with verbose output for debugging
        sudo chroot ${CHROOT_PATH:-/home/john/zforge_workspace/chroot} /bin/bash -c '
            export DEBIAN_FRONTEND=noninteractive
            apt-get update
        ' || true
        
        return 1
    fi
}

# Main execution
main() {
    echo "This script fixes DNS for systemd-resolved systems with USB tethering"
    echo "Target: Z-FORGE chroot at ${CHROOT_PATH:-/home/john/zforge_workspace/chroot}"
    echo
    
    # Check if chroot exists
    if [ ! -d "${CHROOT_PATH:-/home/john/zforge_workspace/chroot}" ]; then
        echo "✗ Chroot directory not found at ${CHROOT_PATH:-/home/john/zforge_workspace/chroot}"
        exit 1
    fi
    
    if check_systemd_resolved; then
        configure_systemd_resolved
    else
        echo "   systemd-resolved not running, using alternative approach"
    fi
    
    fix_chroot_dns
    mount_chroot
    configure_apt
    
    if test_dns; then
        if test_apt; then
            echo
            echo "=== DNS Fix Complete ✓ ==="
            echo "Both host and chroot DNS are working"
            echo "APT is ready for package downloads"
            echo
            echo "Resume Z-FORGE build:"
            echo "sudo python3 builder/z-forge.py --build-spec build_spec.yml --resume"
        else
            echo
            echo "=== DNS Fixed, APT Issues ⚠ ==="
            echo "DNS is working but APT has issues"
            echo "Try running Z-FORGE build anyway:"
            echo "sudo python3 builder/z-forge.py --build-spec build_spec.yml --resume"
        fi
    else
        echo
        echo "=== DNS Fix Failed ✗ ==="
        echo "Unable to resolve DNS issues"
        echo "Check your USB tether connection and try again"
    fi
}

# Run main function
main "$@"