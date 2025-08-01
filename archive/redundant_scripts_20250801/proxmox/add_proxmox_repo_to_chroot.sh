#!/bin/bash
# Add Proxmox VE 9 repository to chroot environment
# This enables installation of Proxmox packages in the live CD

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "        Adding Proxmox VE 9 Repository to Chroot"
echo "═══════════════════════════════════════════════════════════════════"

CHROOT_PATH="${1:-${CHROOT_PATH:-/home/john/zforge_workspace/chroot}}"

if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    echo "Usage: sudo $0 [chroot_path]"
    exit 1
fi

if [ ! -d "$CHROOT_PATH" ]; then
    echo "ERROR: Chroot directory not found: $CHROOT_PATH"
    echo ""
    echo "Please bootstrap the chroot first:"
    echo "  sudo scripts/chroot/bootstrap_chroot.sh auto"
    exit 1
fi

echo "Target chroot: $CHROOT_PATH"
echo ""

echo "[1/5] Mounting filesystems in chroot..."
for fs in proc sys dev dev/pts; do
    if ! mountpoint -q "$CHROOT_PATH/$fs" 2>/dev/null; then
        mkdir -p "$CHROOT_PATH/$fs"
        mount --bind "/$fs" "$CHROOT_PATH/$fs"
        echo "  Mounted $fs"
    else
        echo "  $fs already mounted"
    fi
done

echo ""
echo "[2/5] Adding Proxmox VE repository..."

# Create Proxmox sources list
cat > "$CHROOT_PATH/etc/apt/sources.list.d/proxmox.list" << EOF
# Proxmox VE 9 Repository
deb http://download.proxmox.com/debian/pve trixie pve-no-subscription

# Proxmox Enterprise (commented out - requires subscription)
# deb https://enterprise.proxmox.com/debian/pve trixie pve-enterprise
EOF

echo "  Created /etc/apt/sources.list.d/proxmox.list"

echo ""
echo "[3/5] Adding Proxmox GPG key..."

# Download and add Proxmox GPG key
chroot "$CHROOT_PATH" bash -c '
# Try multiple methods to get the GPG key
if wget -q -O /tmp/proxmox-release-bookworm.gpg https://enterprise.proxmox.com/debian/proxmox-release-bookworm.gpg; then
    cp /tmp/proxmox-release-bookworm.gpg /etc/apt/trusted.gpg.d/
    echo "  GPG key added from enterprise.proxmox.com"
elif curl -fsSL https://enterprise.proxmox.com/debian/proxmox-release-bookworm.gpg -o /etc/apt/trusted.gpg.d/proxmox-release-bookworm.gpg; then
    echo "  GPG key added via curl"
else
    echo "  WARNING: Could not download GPG key"
    echo "  Packages may not install without key verification"
fi
'

echo ""
echo "[4/5] Updating package lists..."
chroot "$CHROOT_PATH" apt-get update

echo ""
echo "[5/5] Verifying Proxmox packages are available..."
echo "Checking for key Proxmox packages..."

chroot "$CHROOT_PATH" bash -c '
echo "Available Proxmox packages:"
apt-cache search proxmox-ve | head -5
echo ""
echo "PVE kernel packages:"
apt-cache search pve-kernel | head -3
echo ""
echo "Corosync/cluster packages:"
apt-cache search corosync | head -2
'

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                Proxmox Repository Added!"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "Proxmox VE 9 repository is now available in the chroot."
echo ""
echo "Key packages available:"
echo "  - proxmox-ve              (meta-package)"
echo "  - pve-manager             (web interface)"
echo "  - pve-kernel-*            (Proxmox kernels)"
echo "  - corosync                (cluster)"
echo "  - pve-container           (LXC)"
echo "  - pve-qemu-kvm            (QEMU/KVM)"
echo ""
echo "To install Proxmox in chroot:"
echo "  sudo chroot $CHROOT_PATH apt-get install -y proxmox-ve"
echo ""
echo "Or let the build system install it automatically:"
echo "  make build"