#!/bin/bash
# Install ZFS 2.3.3 packages in correct order

set -e

echo "Installing ZFS 2.3.3 packages..."

# Install dependencies first
apt-get update
apt-get install -y --no-install-recommends \
    libc6 \
    libblkid1 \
    libuuid1 \
    zlib1g \
    python3

# Install ZFS libraries in order
dpkg -i libuutil3*.deb || apt-get -f install -y
dpkg -i libnvpair3*.deb || apt-get -f install -y
dpkg -i libzpool5*.deb libzfs4*.deb || apt-get -f install -y

# Install ZFS utilities
dpkg -i zfsutils-linux*.deb zfs-zed*.deb || apt-get -f install -y

# Install ZFS initramfs support
dpkg -i zfs-initramfs*.deb || apt-get -f install -y

# Fix any remaining dependencies
apt-get -f install -y

echo "ZFS 2.3.3 installation complete!"
zfs --version
