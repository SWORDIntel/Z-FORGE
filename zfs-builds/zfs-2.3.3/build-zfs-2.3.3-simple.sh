#!/bin/bash
# Simple ZFS 2.3.3 build script with error handling

set -e

# Version configuration
ZFS_VERSION="2.3.3"
BUILD_DIR="/usr/src"
ZFS_SOURCE_DIR="${BUILD_DIR}/zfs-${ZFS_VERSION}"

echo "=== Building ZFS ${ZFS_VERSION} from Source (Simple) ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run with sudo"
    exit 1
fi

# Clean previous attempts
echo "Cleaning previous build attempts..."
cd ${BUILD_DIR}
if [ -d "${ZFS_SOURCE_DIR}" ]; then
    echo "Removing old build directory..."
    rm -rf "${ZFS_SOURCE_DIR}"
fi

# Download fresh source
echo "Downloading ZFS ${ZFS_VERSION} source..."
wget -c https://github.com/openzfs/zfs/releases/download/zfs-${ZFS_VERSION}/zfs-${ZFS_VERSION}.tar.gz

# Extract source
echo "Extracting ZFS source..."
tar -xzf zfs-${ZFS_VERSION}.tar.gz
cd ${ZFS_SOURCE_DIR}

# Simple configure without Python bindings (often problematic)
echo "Configuring ZFS build..."
./configure \
    --prefix=/usr \
    --sysconfdir=/etc \
    --sbindir=/sbin \
    --libdir=/usr/lib/x86_64-linux-gnu \
    --with-config=all \
    --enable-systemd \
    --disable-pyzfs \
    --with-systemdunitdir=/lib/systemd/system

# Build with basic optimizations
echo "Building ZFS..."
make -j8

# Install
echo "Installing ZFS..."
make install DESTDIR=/ || {
    echo "Install failed, trying with forced directory creation..."
    mkdir -p /usr/include/libzfs
    make install DESTDIR=/
}

# Update module dependencies
echo "Updating module dependencies..."
depmod -a

# Load modules
echo "Loading ZFS modules..."
modprobe zfs || true

# Enable services
echo "Enabling ZFS services..."
systemctl daemon-reload
systemctl enable zfs-import-cache zfs-mount zfs-share zfs-zed || true

# Verify
echo ""
echo "=== Verification ==="
zfs --version || echo "ZFS command not found"
modinfo zfs | grep version || echo "Module not loaded"

echo ""
echo "Build complete. A reboot is recommended."