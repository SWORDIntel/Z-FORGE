#!/bin/bash
# Build ZFS and Proxmox components for the host system
# This allows testing and development outside the ISO

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "       Build ZFS and Proxmox for Host System"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "This script builds components for your current system, not the ISO."
echo "Useful for:"
echo "  - Testing ZFS 2.3.3 on your development machine"
echo "  - Setting up Proxmox VE on the host"
echo "  - Development and debugging"
echo ""

# Function to display menu
show_menu() {
    echo "What would you like to build?"
    echo ""
    echo "1. ZFS 2.3.3 (kernel modules + userspace)"
    echo "2. ZFS 2.3.3 (userspace tools only)"
    echo "3. Proxmox VE 9 packages"
    echo "4. Both ZFS and Proxmox"
    echo "5. ZFS from Debian repositories"
    echo "6. Create .deb packages (for distribution)"
    echo ""
    echo "0. Exit"
    echo ""
    read -p "Enter your choice [0-6]: " choice
}

# Build ZFS for host
build_zfs_host() {
    echo ""
    echo "Building ZFS 2.3.3 for host system..."
    echo ""
    
    # Check kernel support
    if grep -q "CONFIG_MODULES=y" /boot/config-$(uname -r) 2>/dev/null; then
        echo "✅ Kernel supports modules"
        ./scripts/build/build_zfs_233_smart.sh
    else
        echo "❌ Kernel doesn't support modules, building userspace only"
        ./scripts/build/build_zfs_233_userspace_only.sh
    fi
}

# Build ZFS userspace only
build_zfs_userspace() {
    echo ""
    echo "Building ZFS 2.3.3 userspace tools only..."
    ./scripts/build/build_zfs_233_userspace_only.sh
}

# Install Proxmox on host
install_proxmox_host() {
    echo ""
    echo "Installing Proxmox VE 9 on host system..."
    echo ""
    
    cat > install_proxmox_host.sh << 'EOFPROX'
#!/bin/bash
# Install Proxmox VE on the host system

set -e

if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    exit 1
fi

echo "Installing Proxmox VE 9..."

# Add Proxmox repository
echo "Adding Proxmox repository..."
wget https://enterprise.proxmox.com/debian/proxmox-release-bookworm.gpg -O /etc/apt/trusted.gpg.d/proxmox-release-bookworm.gpg

echo "deb http://download.proxmox.com/debian/pve bookworm pve-no-subscription" > /etc/apt/sources.list.d/pve-install-repo.list

# Update package list
apt-get update

# Install Proxmox VE
echo "Installing Proxmox packages..."
apt-get install -y proxmox-ve postfix open-iscsi chrony

echo ""
echo "Proxmox VE installed!"
echo "Access web interface at: https://$(hostname -I | awk '{print $1}'):8006"
echo "Default login: root with system password"
EOFPROX

    chmod +x install_proxmox_host.sh
    echo ""
    echo "Created install_proxmox_host.sh"
    echo "Run with: sudo ./install_proxmox_host.sh"
    echo ""
    echo "WARNING: This will convert your system to Proxmox VE!"
    echo "Only proceed if you want Proxmox on this host."
}

# Install ZFS from repos
install_zfs_repos() {
    echo ""
    echo "Installing ZFS from Debian repositories..."
    echo ""
    
    cat > install_zfs_debian.sh << 'EOFZFS'
#!/bin/bash
# Install ZFS from Debian repositories

set -e

if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    exit 1
fi

echo "Installing ZFS from Debian repos..."

# Enable contrib
sed -i 's/main$/main contrib non-free-firmware/g' /etc/apt/sources.list

# Update
apt-get update

# Install ZFS
apt-get install -y zfsutils-linux zfs-dkms zfs-zed

# Load module
modprobe zfs

# Check status
zfs version

echo "ZFS installed from Debian repositories!"
EOFZFS

    chmod +x install_zfs_debian.sh
    echo "Created install_zfs_debian.sh"
    echo "Run with: sudo ./install_zfs_debian.sh"
}

# Build .deb packages
build_deb_packages() {
    echo ""
    echo "Building .deb packages for distribution..."
    echo ""
    
    cat > build_zfs_debs.sh << 'EOFDEB'
#!/bin/bash
# Build ZFS .deb packages

set -e

BUILD_DIR="/tmp/zfs_deb_build"
ZFS_VERSION="2.3.3"

echo "Building ZFS ${ZFS_VERSION} .deb packages..."

# Install build dependencies
sudo apt-get update
sudo apt-get install -y build-essential autoconf automake libtool gawk \
    alien fakeroot dkms libblkid-dev uuid-dev libudev-dev libssl-dev \
    zlib1g-dev libaio-dev libattr1-dev libelf-dev linux-headers-$(uname -r) \
    python3 python3-dev python3-setuptools python3-cffi libffi-dev \
    debhelper dh-python po-debconf python3-all-dev python3-sphinx

# Create build directory
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Download ZFS
wget https://github.com/openzfs/zfs/releases/download/zfs-${ZFS_VERSION}/zfs-${ZFS_VERSION}.tar.gz
tar xzf zfs-${ZFS_VERSION}.tar.gz
cd zfs-${ZFS_VERSION}

# Configure for .deb creation
./configure --enable-systemd

# Build packages
make -j$(nproc) deb-utils deb-kmod

echo ""
echo "Packages built in: $BUILD_DIR/zfs-${ZFS_VERSION}"
echo ""
ls -la *.deb

echo ""
echo "To install:"
echo "cd $BUILD_DIR/zfs-${ZFS_VERSION}"
echo "sudo dpkg -i *.deb"
EOFDEB

    chmod +x build_zfs_debs.sh
    echo "Created build_zfs_debs.sh"
    echo "Run with: ./build_zfs_debs.sh"
}

# Main loop
while true; do
    show_menu
    
    case $choice in
        1)
            build_zfs_host
            ;;
        2)
            build_zfs_userspace
            ;;
        3)
            install_proxmox_host
            ;;
        4)
            build_zfs_host
            install_proxmox_host
            ;;
        5)
            install_zfs_repos
            ;;
        6)
            build_deb_packages
            ;;
        0)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo "Invalid choice!"
            ;;
    esac
    
    echo ""
    read -p "Press Enter to continue..."
    echo ""
done