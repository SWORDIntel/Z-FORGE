#!/bin/bash
# Build ZFS 2.3.3 from source with optimizations

set -e

# Version configuration
ZFS_VERSION="2.3.3"
BUILD_DIR="/usr/src"
ZFS_SOURCE_DIR="${BUILD_DIR}/zfs-${ZFS_VERSION}"

# Optimization flags for Meteor Lake - P-core aware (AVX-512 on P-cores only)
# Using O2 for stability - O3 can cause issues with kernel modules
export CFLAGS="-O2 -march=native -mtune=native -pipe"
export CXXFLAGS="${CFLAGS}"
export LDFLAGS="-Wl,-O1 -Wl,--as-needed"

# Build parallelism - use P-cores only for AVX-512 optimized build
export MAKEFLAGS="-j8"

echo "=== Building ZFS ${ZFS_VERSION} from Source ==="
echo "Build flags: ${CFLAGS}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run with sudo"
    exit 1
fi

# Install build dependencies
echo "Installing build dependencies..."
apt update
apt install -y build-essential autoconf automake libtool gawk alien fakeroot dkms \
    libblkid-dev uuid-dev libudev-dev libssl-dev zlib1g-dev libaio-dev libattr1-dev \
    libelf-dev linux-headers-$(uname -r) python3 python3-dev python3-setuptools \
    python3-cffi libffi-dev python3-packaging python3-distlib python3.13-dev \
    git libcurl4-openssl-dev debhelper

# Install Python modules via pip if not available in apt
echo "Installing Python modules via pip..."
python3.13 -m pip install --break-system-packages distlib packaging setuptools

# Create build directory
mkdir -p ${BUILD_DIR}
cd ${BUILD_DIR}

# Download ZFS source
echo ""
echo "Downloading ZFS ${ZFS_VERSION} source..."
if [ ! -f "zfs-${ZFS_VERSION}.tar.gz" ]; then
    wget -c https://github.com/openzfs/zfs/releases/download/zfs-${ZFS_VERSION}/zfs-${ZFS_VERSION}.tar.gz
fi

# Extract source
echo "Extracting ZFS source..."
if [ ! -d "${ZFS_SOURCE_DIR}" ]; then
    tar -xzf zfs-${ZFS_VERSION}.tar.gz
fi

cd ${ZFS_SOURCE_DIR}

# Fix Python path for configure
export PYTHON=$(which python3.13)
export PYTHON_SETUPTOOLS_LIBDIR=$(python3.13 -c "import setuptools; print(setuptools.__path__[0])" 2>/dev/null || echo "")

# Configure build
echo ""
echo "Configuring ZFS build with Python 3.13..."
echo "Python path: $PYTHON"
./configure \
    --prefix=/usr \
    --sysconfdir=/etc \
    --sbindir=/sbin \
    --libdir=/usr/lib/x86_64-linux-gnu \
    --datadir=/usr/share \
    --includedir=/usr/include \
    --with-udevdir=/lib/udev \
    --libexecdir=/usr/libexec \
    --with-config=all \
    --enable-systemd \
    --enable-pyzfs \
    --with-python=python3.13 \
    PYTHON=python3.13 \
    PYTHON_VERSION=3.13 \
    --with-dracutdir=/usr/lib/dracut \
    --with-systemdunitdir=/lib/systemd/system \
    --with-systemdpresetdir=/lib/systemd/system-preset \
    --with-systemdgeneratordir=/lib/systemd/system-generators

# Build userspace tools on P-cores (AVX-512 capable)
echo ""
echo "Building ZFS userspace tools on P-cores (0-7)..."
taskset -c 0-7 make -j8

# Build kernel modules on P-cores
echo ""
echo "Building ZFS kernel modules on P-cores (0-7)..."
taskset -c 0-7 make -j8 -C module

# Install userspace tools
echo ""
echo "Installing ZFS userspace tools..."
make install

# Install kernel modules
echo ""
echo "Installing ZFS kernel modules..."
make -C module install

# Update module dependencies
echo ""
echo "Updating module dependencies..."
depmod

# Create DKMS configuration
echo ""
echo "Setting up DKMS..."
mkdir -p /usr/src/zfs-${ZFS_VERSION}
cp -r . /usr/src/zfs-${ZFS_VERSION}/

cat > /usr/src/zfs-${ZFS_VERSION}/dkms.conf << EOF
PACKAGE_NAME="zfs"
PACKAGE_VERSION="${ZFS_VERSION}"
AUTOINSTALL="yes"

BUILT_MODULE_NAME[0]="zavl"
BUILT_MODULE_LOCATION[0]="module/avl/"
DEST_MODULE_LOCATION[0]="/updates/dkms/"

BUILT_MODULE_NAME[1]="znvpair"
BUILT_MODULE_LOCATION[1]="module/nvpair/"
DEST_MODULE_LOCATION[1]="/updates/dkms/"

BUILT_MODULE_NAME[2]="zunicode"
BUILT_MODULE_LOCATION[2]="module/unicode/"
DEST_MODULE_LOCATION[2]="/updates/dkms/"

BUILT_MODULE_NAME[3]="zcommon"
BUILT_MODULE_LOCATION[3]="module/zcommon/"
DEST_MODULE_LOCATION[3]="/updates/dkms/"

BUILT_MODULE_NAME[4]="zfs"
BUILT_MODULE_LOCATION[4]="module/zfs/"
DEST_MODULE_LOCATION[4]="/updates/dkms/"

BUILT_MODULE_NAME[5]="spl"
BUILT_MODULE_LOCATION[5]="module/spl/"
DEST_MODULE_LOCATION[5]="/updates/dkms/"

BUILD_DEPENDS[0]="kernel-devel"
EOF

# Add to DKMS
dkms add -m zfs -v ${ZFS_VERSION} || true
dkms build -m zfs -v ${ZFS_VERSION} -k $(uname -r) || true
dkms install -m zfs -v ${ZFS_VERSION} -k $(uname -r) || true

# Load new modules
echo ""
echo "Loading ZFS modules..."
modprobe -r zfs || true
modprobe zfs

# Update initramfs
echo ""
echo "Updating initramfs..."
update-initramfs -u

# Enable ZFS services
echo ""
echo "Enabling ZFS services..."
systemctl enable zfs-import-cache
systemctl enable zfs-mount
systemctl enable zfs-share
systemctl enable zfs-zed

# Verify installation
echo ""
echo "=== ZFS ${ZFS_VERSION} Build Complete ==="
echo "ZFS version: $(zfs --version | head -1)"
echo "Module version: $(modinfo zfs | grep ^version: | awk '{print $2}')"
echo ""
echo "ZFS pool status:"
zpool status

echo ""
echo "Build completed successfully!"
echo "A reboot is recommended to ensure all modules are properly loaded."