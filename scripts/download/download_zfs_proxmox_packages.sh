#!/bin/bash
# Download ZFS 2.3.3 and Proxmox packages from official repositories

set -euo pipefail

DOWNLOAD_DIR="/opt/github/Z-FORGE/prebuilt_packages"
ZFS_DIR="$DOWNLOAD_DIR/zfs"
PROXMOX_DIR="$DOWNLOAD_DIR/proxmox"

# Create directories
mkdir -p "$ZFS_DIR"
mkdir -p "$PROXMOX_DIR"

echo "=== Downloading ZFS 2.3.3 and Proxmox Packages ==="
echo "Download directory: $DOWNLOAD_DIR"
echo ""

# Proxmox repository base URL
PROXMOX_REPO="http://download.proxmox.com/debian/pve/dists/bookworm/pve-no-subscription/binary-amd64"

# Function to download with progress
download_package() {
    local url=$1
    local dest=$2
    local filename=$(basename "$url")
    
    if [ -f "$dest/$filename" ]; then
        echo "  ✓ $filename already exists, skipping..."
    else
        echo "  → Downloading $filename..."
        wget -q --show-progress -O "$dest/$filename" "$url" || {
            echo "  ✗ Failed to download $filename"
            rm -f "$dest/$filename"
            return 1
        }
        echo "  ✓ Downloaded $filename"
    fi
}

# ZFS 2.3.3 packages
echo "Downloading ZFS 2.3.3 packages..."
echo "================================"

ZFS_PACKAGES=(
    # Core libraries
    "libuutil3linux_2.3.3-pve1_amd64.deb"
    "libnvpair3linux_2.3.3-pve1_amd64.deb"
    "libzpool5linux_2.3.3-pve1_amd64.deb"
    "libzfs4linux_2.3.3-pve1_amd64.deb"
    
    # ZFS utilities
    "zfsutils-linux_2.3.3-pve1_amd64.deb"
    "zfs-zed_2.3.3-pve1_amd64.deb"
    
    # Kernel modules
    "zfs-dkms_2.3.3-pve1_all.deb"
    
    # Initramfs and dracut support
    "zfs-initramfs_2.3.3-pve1_all.deb"
    "zfs-dracut_2.3.3-pve1_all.deb"
    
    # Test and debug tools (optional)
    "zfs-test_2.3.3-pve1_amd64.deb"
    "zfs-dbg_2.3.3-pve1_amd64.deb"
    
    # Python bindings
    "python3-pyzfs_2.3.3-pve1_amd64.deb"
)

for pkg in "${ZFS_PACKAGES[@]}"; do
    download_package "$PROXMOX_REPO/$pkg" "$ZFS_DIR" || true
done

# Proxmox VE packages (core components)
echo ""
echo "Downloading Proxmox VE packages..."
echo "=================================="

PROXMOX_PACKAGES=(
    # Base system
    "proxmox-ve_9.0-2_all.deb"
    "pve-manager_9.0-2_amd64.deb"
    "pve-kernel-6.8_6.8.12-4_all.deb"
    "pve-kernel-6.8.12-4-pve_6.8.12-4_amd64.deb"
    
    # Core libraries and dependencies
    "libpve-common-perl_9.0-3_all.deb"
    "libpve-storage-perl_9.0-4_all.deb"
    "libpve-access-control_9.0-2_all.deb"
    "libpve-guest-common-perl_6.0-2_all.deb"
    "libpve-http-server-perl_6.0-1_all.deb"
    "libpve-apiclient-perl_3.3.2_all.deb"
    
    # Cluster and HA
    "pve-cluster_9.0-2_amd64.deb"
    "pve-ha-manager_4.0.5_amd64.deb"
    
    # Storage plugins
    "libpve-storage-perl_9.0-4_all.deb"
    
    # Qemu/KVM
    "qemu-server_9.0-8_amd64.deb"
    "pve-qemu-kvm_9.0.2-3_amd64.deb"
    
    # Container support
    "pve-container_6.0-2_all.deb"
    "lxc-pve_6.0.0-1_amd64.deb"
    
    # Backup
    "proxmox-backup-client_3.3.0-1_amd64.deb"
    "pve-zsync_2.3-1_all.deb"
    
    # Firewall
    "pve-firewall_5.0.7_amd64.deb"
    
    # Web interface dependencies
    "libjs-extjs_7.0.0-5_all.deb"
    "pve-xtermjs_5.3.0-3_all.deb"
)

for pkg in "${PROXMOX_PACKAGES[@]}"; do
    download_package "$PROXMOX_REPO/$pkg" "$PROXMOX_DIR" || true
done

# Download package lists for reference
echo ""
echo "Downloading package lists..."
echo "============================"

# Get the full package list
wget -q -O "$DOWNLOAD_DIR/Packages_pve-no-subscription.gz" \
    "http://download.proxmox.com/debian/pve/dists/bookworm/pve-no-subscription/binary-amd64/Packages.gz"

if [ -f "$DOWNLOAD_DIR/Packages_pve-no-subscription.gz" ]; then
    gunzip -f "$DOWNLOAD_DIR/Packages_pve-no-subscription.gz"
    echo "  ✓ Package list downloaded to Packages_pve-no-subscription"
fi

# Create index files
echo ""
echo "Creating package indexes..."
echo "=========================="

# ZFS package index
(cd "$ZFS_DIR" && ls -1 *.deb 2>/dev/null > packages.list || true)
echo "  ✓ Created $ZFS_DIR/packages.list"

# Proxmox package index
(cd "$PROXMOX_DIR" && ls -1 *.deb 2>/dev/null > packages.list || true)
echo "  ✓ Created $PROXMOX_DIR/packages.list"

# Summary
echo ""
echo "=== Download Summary ==="
echo "ZFS packages downloaded: $(ls -1 $ZFS_DIR/*.deb 2>/dev/null | wc -l)"
echo "Proxmox packages downloaded: $(ls -1 $PROXMOX_DIR/*.deb 2>/dev/null | wc -l)"
echo "Total size: $(du -sh $DOWNLOAD_DIR | cut -f1)"
echo ""
echo "Package locations:"
echo "  ZFS: $ZFS_DIR"
echo "  Proxmox: $PROXMOX_DIR"
echo ""
echo "To view all available Proxmox packages:"
echo "  grep '^Package:' $DOWNLOAD_DIR/Packages_pve-no-subscription | sort | uniq"
echo ""
echo "Download complete! These packages are saved as backup."
echo "You can now proceed with the full build."