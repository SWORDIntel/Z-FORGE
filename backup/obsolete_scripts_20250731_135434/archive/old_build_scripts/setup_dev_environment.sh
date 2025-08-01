#!/bin/bash
# Set up complete development environment with ZFS and optionally Proxmox
# Useful for testing Z-FORGE components on the development machine

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "        Z-FORGE Development Environment Setup"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "This will set up your development machine with:"
echo "  - ZFS 2.3.3 (latest stable)"
echo "  - Optional: Proxmox VE 9"
echo "  - Development tools"
echo "  - Test environment"
echo ""

# Function to check system
check_system() {
    echo "[*] System Information:"
    echo "  OS: $(lsb_release -ds 2>/dev/null || cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
    echo "  Kernel: $(uname -r)"
    echo "  Architecture: $(uname -m)"
    echo "  CPU cores: $(nproc)"
    echo "  Memory: $(free -h | grep Mem | awk '{print $2}')"
    echo ""
    
    # Check for virtualization
    if systemd-detect-virt >/dev/null 2>&1; then
        VIRT=$(systemd-detect-virt)
        if [ "$VIRT" != "none" ]; then
            echo "  ⚠️  Virtualization detected: $VIRT"
            echo "     Some features may be limited in VMs"
            echo ""
        fi
    fi
}

# Function to set up ZFS test environment
setup_zfs_test() {
    echo ""
    echo "Setting up ZFS test environment..."
    echo ""
    
    cat > setup_zfs_test_env.sh << 'EOFTEST'
#!/bin/bash
# Create ZFS test environment with file-based pools

set -e

TEST_DIR="/var/lib/zforge-test"
POOL_NAME="zforge-test"

if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    exit 1
fi

echo "Creating ZFS test environment..."

# Create test directory
mkdir -p "$TEST_DIR"

# Create sparse files for testing (1GB each)
echo "Creating test devices..."
for i in {1..3}; do
    truncate -s 1G "$TEST_DIR/disk$i.img"
    echo "  Created $TEST_DIR/disk$i.img (1GB)"
done

# Create test pool
echo ""
echo "Creating test ZFS pool..."
zpool create -f "$POOL_NAME" \
    raidz "$TEST_DIR/disk1.img" "$TEST_DIR/disk2.img" "$TEST_DIR/disk3.img"

# Create datasets
echo "Creating test datasets..."
zfs create "$POOL_NAME/iso"
zfs create "$POOL_NAME/build"
zfs create "$POOL_NAME/cache"

# Set properties
zfs set compression=lz4 "$POOL_NAME"
zfs set atime=off "$POOL_NAME"

# Show status
echo ""
echo "Test environment created!"
echo ""
zpool status "$POOL_NAME"
echo ""
zfs list -r "$POOL_NAME"
echo ""
echo "To destroy test environment:"
echo "  sudo zpool destroy $POOL_NAME"
echo "  sudo rm -rf $TEST_DIR"
EOFTEST

    chmod +x setup_zfs_test_env.sh
    echo "Created setup_zfs_test_env.sh"
    echo "Run with: sudo ./setup_zfs_test_env.sh"
}

# Function to install development tools
install_dev_tools() {
    echo ""
    echo "Installing development tools..."
    
    sudo apt-get update
    sudo apt-get install -y \
        git build-essential vim tmux htop \
        debootstrap cdebootstrap squashfs-tools \
        xorriso isolinux syslinux-common \
        qemu-kvm qemu-utils virtinst virt-manager \
        python3-pip python3-venv \
        curl wget rsync tree \
        genisoimage dosfstools mtools
        
    echo "Development tools installed!"
}

# Main menu
echo "[*] Checking system..."
check_system

echo "What would you like to set up?"
echo ""
echo "1. ZFS only (recommended for development)"
echo "2. ZFS + Proxmox VE (converts system to Proxmox)"
echo "3. ZFS + Development tools"
echo "4. Everything (ZFS + Proxmox + Dev tools)"
echo "5. Just development tools"
echo ""
read -p "Enter your choice [1-5]: " choice

case $choice in
    1)
        echo ""
        echo "Setting up ZFS only..."
        ./build_zfs_host_quick.sh
        setup_zfs_test
        ;;
    2)
        echo ""
        echo "Setting up ZFS + Proxmox VE..."
        echo "WARNING: This will convert your system to Proxmox VE!"
        read -p "Continue? (y/n): " confirm
        if [ "$confirm" = "y" ]; then
            ./build_zfs_host_quick.sh
            ./build_for_host_system.sh
            # Select option 3 (Proxmox)
        fi
        ;;
    3)
        echo ""
        echo "Setting up ZFS + Development tools..."
        install_dev_tools
        ./build_zfs_host_quick.sh
        setup_zfs_test
        ;;
    4)
        echo ""
        echo "Setting up everything..."
        echo "WARNING: This will convert your system to Proxmox VE!"
        read -p "Continue? (y/n): " confirm
        if [ "$confirm" = "y" ]; then
            install_dev_tools
            ./build_zfs_host_quick.sh
            setup_zfs_test
            ./build_for_host_system.sh
        fi
        ;;
    5)
        echo ""
        echo "Installing development tools only..."
        install_dev_tools
        ;;
    *)
        echo "Invalid choice!"
        exit 1
        ;;
esac

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                    Setup Complete!"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "You can now:"
echo "  - Build Z-FORGE ISO: make build"
echo "  - Test ZFS features on your host"
echo "  - Develop and debug Z-FORGE components"
echo ""

if [ -f setup_zfs_test_env.sh ]; then
    echo "To create a test ZFS pool:"
    echo "  sudo ./setup_zfs_test_env.sh"
    echo ""
fi