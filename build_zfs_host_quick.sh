#!/bin/bash
# Quick ZFS 2.3.3 build for the host system
# Builds and installs ZFS directly on the current machine

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "        Quick ZFS 2.3.3 Build for Host System"
echo "═══════════════════════════════════════════════════════════════════"

ZFS_VERSION="2.3.3"
BUILD_DIR="/tmp/zfs_host_build_$$"

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo "WARNING: Running as root. This will install ZFS system-wide."
    read -p "Continue? (y/n): " confirm
    if [ "$confirm" != "y" ]; then
        exit 1
    fi
fi

echo ""
echo "[1/6] Installing build dependencies..."

sudo apt-get update
sudo apt-get install -y \
    build-essential autoconf automake libtool gawk alien fakeroot \
    dkms libblkid-dev uuid-dev libudev-dev libssl-dev zlib1g-dev \
    libaio-dev libattr1-dev libelf-dev linux-headers-$(uname -r) \
    python3 python3-dev python3-setuptools python3-cffi libffi-dev \
    python3-packaging python3-distutils

echo ""
echo "[2/6] Creating build directory..."
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

echo ""
echo "[3/6] Downloading ZFS ${ZFS_VERSION}..."
wget -q https://github.com/openzfs/zfs/releases/download/zfs-${ZFS_VERSION}/zfs-${ZFS_VERSION}.tar.gz
tar xzf zfs-${ZFS_VERSION}.tar.gz
cd zfs-${ZFS_VERSION}

echo ""
echo "[4/6] Configuring ZFS build..."

# Configure based on kernel module support
if grep -q "CONFIG_MODULES=y" /boot/config-$(uname -r) 2>/dev/null; then
    echo "Building with kernel module support..."
    ./configure \
        --prefix=/usr \
        --sysconfdir=/etc \
        --sbindir=/sbin \
        --libdir=/usr/lib \
        --enable-systemd \
        --enable-pyzfs \
        --with-config=all
else
    echo "Building userspace tools only (no kernel module support)..."
    ./configure \
        --prefix=/usr \
        --sysconfdir=/etc \
        --sbindir=/sbin \
        --libdir=/usr/lib \
        --enable-systemd \
        --enable-pyzfs \
        --with-config=user
fi

echo ""
echo "[5/6] Building ZFS (this may take a while)..."
make -j$(nproc)

echo ""
echo "[6/6] Installing ZFS..."
sudo make install
sudo ldconfig

# Load the module if built
if [ -f "/lib/modules/$(uname -r)/extra/zfs.ko" ]; then
    echo ""
    echo "Loading ZFS kernel module..."
    sudo modprobe zfs || echo "Module loading failed - may need reboot"
fi

# Enable services
echo ""
echo "Enabling ZFS services..."
sudo systemctl preset zfs-import-cache zfs-import-scan zfs-mount zfs-share zfs-zed zfs.target || true
sudo systemctl enable zfs.target || true

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                ZFS ${ZFS_VERSION} Build Complete!"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# Check installation
if command -v zfs >/dev/null 2>&1; then
    echo "✅ ZFS installed successfully!"
    echo ""
    echo "Version information:"
    zfs version 2>/dev/null || echo "ZFS command found but version check failed"
    echo ""
    echo "Kernel module status:"
    lsmod | grep zfs || echo "No ZFS kernel modules loaded"
else
    echo "❌ ZFS command not found in PATH"
fi

echo ""
echo "Build directory: $BUILD_DIR"
echo ""
echo "Next steps:"
echo "1. Create a ZFS pool: sudo zpool create mypool /dev/sdX"
echo "2. Create datasets: sudo zfs create mypool/dataset"
echo "3. Check status: sudo zpool status"
echo ""
echo "To remove build directory:"
echo "  rm -rf $BUILD_DIR"