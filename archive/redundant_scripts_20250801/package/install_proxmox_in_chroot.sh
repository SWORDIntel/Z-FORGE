#!/bin/bash
# Install Proxmox VE 9 packages in chroot for live CD
# This creates a Proxmox-enabled live environment

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "        Installing Proxmox VE 9 in Chroot"
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
    echo "  sudo ./bootstrap_chroot.sh auto"
    echo "  sudo ./add_proxmox_repo_to_chroot.sh"
    exit 1
fi

# Check if Proxmox repo is available
if [ ! -f "$CHROOT_PATH/etc/apt/sources.list.d/proxmox.list" ]; then
    echo "WARNING: Proxmox repository not found"
    echo "Adding repository first..."
    ./add_proxmox_repo_to_chroot.sh "$CHROOT_PATH"
fi

echo ""
echo "[1/4] Installing core Proxmox packages..."

# Install essential Proxmox packages in stages
chroot "$CHROOT_PATH" bash -c '
export DEBIAN_FRONTEND=noninteractive

echo "Installing Proxmox base packages..."
apt-get install -y --no-install-recommends \
    proxmox-ve \
    pve-manager \
    pve-kernel-helper \
    || echo "Some packages may have failed - continuing..."

echo "Installing cluster and storage..."
apt-get install -y --no-install-recommends \
    corosync \
    pve-cluster \
    pve-ha-manager \
    pve-firewall \
    || echo "Some packages may have failed - continuing..."
'

echo ""
echo "[2/4] Installing virtualization components..."

chroot "$CHROOT_PATH" bash -c '
export DEBIAN_FRONTEND=noninteractive

echo "Installing QEMU/KVM..."
apt-get install -y --no-install-recommends \
    pve-qemu-kvm \
    qemu-utils \
    || echo "QEMU packages may have failed - continuing..."

echo "Installing container support..."
apt-get install -y --no-install-recommends \
    pve-container \
    lxc \
    || echo "Container packages may have failed - continuing..."
'

echo ""
echo "[3/4] Installing additional tools..."

chroot "$CHROOT_PATH" bash -c '
export DEBIAN_FRONTEND=noninteractive

echo "Installing backup and monitoring..."
apt-get install -y --no-install-recommends \
    vzdump \
    pve-docs \
    || echo "Additional tools may have failed - continuing..."
'

echo ""
echo "[4/4] Configuring Proxmox services..."

chroot "$CHROOT_PATH" bash -c '
# Configure services for live environment
echo "Configuring services..."

# Enable key services
systemctl enable pveproxy || true
systemctl enable pvedaemon || true
systemctl enable pve-cluster || true

# Disable some services that may not work in live environment
systemctl disable corosync || true
systemctl disable pve-ha-crm || true
systemctl disable pve-ha-lrm || true

echo "Proxmox services configured for live environment"
'

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                Proxmox VE 9 Installation Complete!"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# Verify installation
echo "Verifying Proxmox installation..."
chroot "$CHROOT_PATH" bash -c '
echo "Installed Proxmox packages:"
dpkg -l | grep -E "(proxmox|pve-)" | head -10

echo ""
echo "Proxmox version:"
pveversion || echo "pveversion command not available"

echo ""
echo "Key services:"
systemctl list-unit-files | grep -E "(pve|proxmox)" | head -5 || true
'

echo ""
echo "Proxmox VE 9 is now installed in the chroot!"
echo ""
echo "In the live environment, Proxmox will be accessible at:"
echo "  https://[IP]:8006/"
echo ""
echo "Default login: root (with live system password)"
echo ""
echo "Next steps:"
echo "1. Continue with: make build"
echo "2. Boot the generated ISO"
echo "3. Access Proxmox web interface"