#!/bin/bash
# Minimal ZFS 2.3.3 build - just essentials

set -e

# Version configuration
ZFS_VERSION="2.3.3"
BUILD_DIR="/usr/src/zfs-build-minimal"
ZFS_SOURCE_DIR="${BUILD_DIR}/zfs-${ZFS_VERSION}"

echo "=== Minimal ZFS ${ZFS_VERSION} Build ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run with sudo"
    exit 1
fi

# Install minimal dependencies
echo "Installing build dependencies..."
apt update
apt install -y \
    build-essential \
    autoconf \
    automake \
    libtool \
    gawk \
    alien \
    fakeroot \
    dkms \
    libblkid-dev \
    uuid-dev \
    libudev-dev \
    libssl-dev \
    zlib1g-dev \
    libaio-dev \
    libattr1-dev \
    libelf-dev \
    linux-headers-$(uname -r)

# Create clean build directory
echo "Creating build directory..."
rm -rf ${BUILD_DIR}
mkdir -p ${BUILD_DIR}
cd ${BUILD_DIR}

# Download ZFS source
echo "Downloading ZFS ${ZFS_VERSION} source..."
wget https://github.com/openzfs/zfs/releases/download/zfs-${ZFS_VERSION}/zfs-${ZFS_VERSION}.tar.gz

# Extract source
echo "Extracting source..."
tar -xzf zfs-${ZFS_VERSION}.tar.gz
cd ${ZFS_SOURCE_DIR}

# Run autogen
echo "Running autogen.sh..."
./autogen.sh

# Configure - userspace only first
echo "Configuring userspace..."
./configure \
    --prefix=/usr \
    --sysconfdir=/etc \
    --sbindir=/sbin \
    --libdir=/usr/lib/x86_64-linux-gnu \
    --with-config=user \
    --enable-systemd \
    --disable-pyzfs

# Build userspace
echo "Building userspace on P-cores..."
make -j16

# Install userspace
echo "Installing userspace..."
make install
ldconfig

# Now configure kernel modules
echo "Configuring kernel modules..."
make distclean
./autogen.sh
./configure \
    --with-config=kernel \
    --with-linux=/lib/modules/$(uname -r)/build \
    --with-linux-obj=/lib/modules/$(uname -r)/build

# Build kernel modules
echo "Building kernel modules on P-cores..."
cd module
make -j16

# Install kernel modules
echo "Installing kernel modules..."
make install

# Load modules
echo "Loading ZFS modules..."
depmod -a
modprobe zfs

# Enable services
echo "Enabling ZFS services..."
systemctl daemon-reload
systemctl enable zfs-import-cache zfs-mount zfs-share zfs-zed

# Verify
echo ""
echo "=== Installation Complete ==="
echo "ZFS version:"
zfs --version || echo "Error: zfs command not found"
echo ""
echo "Kernel module:"
modinfo zfs | grep version || echo "Error: module not loaded"

echo ""
echo "If modules aren't loaded, reboot and they should load automatically."