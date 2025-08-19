#!/bin/bash
# Fix ZFS build with proper header configuration

set -e

cd /usr/src/zfs-2.3.3

# Clean previous attempts
echo "Cleaning previous build..."
make distclean || true
rm -rf debian/tmp debian/openzfs-* debian/.debhelper

# Ensure autogen is run
echo "Running autogen.sh..."
./autogen.sh

# Configure with proper paths
echo "Configuring build..."
./configure \
    --prefix=/usr \
    --sysconfdir=/etc \
    --sbindir=/sbin \
    --libdir=/usr/lib/x86_64-linux-gnu \
    --includedir=/usr/include \
    --with-config=user \
    --enable-systemd \
    --disable-pyzfs \
    --with-systemdunitdir=/lib/systemd/system \
    --with-systemdpresetdir=/lib/systemd/system-preset \
    --with-systemdgeneratordir=/lib/systemd/system-generators

# Build userspace only first
echo "Building userspace tools..."
make -j8

# Now build kernel modules separately
echo "Configuring kernel modules..."
./configure \
    --with-config=kernel \
    --with-linux=/lib/modules/$(uname -r)/build \
    --with-linux-obj=/lib/modules/$(uname -r)/build

echo "Building kernel modules..."
cd module
make -j8

# Install everything
cd ..
echo "Installing..."
sudo make install
sudo ldconfig

echo ""
echo "Build complete!"
echo "ZFS version: $(zfs --version 2>/dev/null || echo 'not found')"