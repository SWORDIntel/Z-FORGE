#!/bin/bash
# Install all prebuilt packages in chroot

set -e

PACKAGES_DIR="/tmp/prebuilt_packages"

echo "=== Installing Prebuilt Packages ==="

# Install ZFS if packages exist
if [ -d "$PACKAGES_DIR/zfs" ] && [ -n "$(ls -A $PACKAGES_DIR/zfs/*.deb 2>/dev/null)" ]; then
    echo "Installing ZFS packages..."
    cd "$PACKAGES_DIR/zfs"
    if [ -x "./install.sh" ]; then
        ./install.sh
    else
        dpkg -i *.deb || apt-get -f install -y
    fi
fi

# Install Proxmox if packages exist
if [ -d "$PACKAGES_DIR/proxmox" ] && [ -n "$(ls -A $PACKAGES_DIR/proxmox/*.deb 2>/dev/null)" ]; then
    echo "Installing Proxmox packages..."
    cd "$PACKAGES_DIR/proxmox"
    dpkg -i *.deb || apt-get -f install -y
fi

# Install kernel modules if they exist
if [ -d "$PACKAGES_DIR/kernel" ] && [ -n "$(ls -A $PACKAGES_DIR/kernel/*.deb 2>/dev/null)" ]; then
    echo "Installing kernel packages..."
    cd "$PACKAGES_DIR/kernel"
    dpkg -i *.deb || apt-get -f install -y
fi

# Install bootloaders if they exist
if [ -d "$PACKAGES_DIR/bootloaders" ] && [ -n "$(ls -A $PACKAGES_DIR/bootloaders/*.deb 2>/dev/null)" ]; then
    echo "Installing bootloader packages..."
    cd "$PACKAGES_DIR/bootloaders"
    dpkg -i *.deb || apt-get -f install -y
fi

echo "=== Prebuilt package installation complete ==="
