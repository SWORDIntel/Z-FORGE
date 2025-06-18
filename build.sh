#!/bin/bash
# z-forge/build.sh - Execute Z-Forge build

set -e

echo "═══════════════════════════════════════════════════════"
echo "            Z-FORGE V3 BUILD SYSTEM"
echo "           PROXMOX VE BOOTSTRAP ISO"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "Build Configuration:"
echo "  - Debian Release: bookworm"
echo "  - Kernel: Latest stable (6.8+)"
echo "  - ZFS: Latest OpenZFS"
echo "  - Proxmox: VE 8.2"
echo ""
echo "Press Enter to continue or Ctrl+C to abort..."
read

# Check for root
if [ "$EUID" -ne 0 ]; then
    echo "[!] This script must be run as root"
    exit 1
fi

# Install base dependencies
echo "[*] Installing build dependencies..."
apt-get update
apt-get install -y \
    python3 \
    python3-pip \
    python3-yaml \
    python3-npyscreen \
    debootstrap \
    xorriso \
    squashfs-tools \
    grub-pc-bin \
    grub-efi-amd64-bin \
    mtools \
    dosfstools

# Install Python dependencies
pip3 install --break-system-packages \
    tqdm \
    requests \
    python-gnupg

# Execute builder
cd "$(dirname "$0")"
python3 builder/z_forge.py

echo "[+] Build process initiated"
