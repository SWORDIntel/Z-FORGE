#!/bin/bash
# Quick ZFS Bootstrap Script
# Simplified workflow for building ZFS and setting up chroot

set -euo pipefail

# Simple configuration
WORKSPACE="$HOME/zforge_workspace"
ZFS_VERSION="2.3.3"
SUDO_PASS="${SUDO_PASS:-}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}         Quick ZFS ${ZFS_VERSION} Bootstrap for Z-FORGE${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════════${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${YELLOW}This script needs root privileges.${NC}"
    echo "Please run with: sudo $0"
    exit 1
fi

# Step 1: Prepare
echo -e "\n${GREEN}Step 1: Preparing environment...${NC}"
mkdir -p "$WORKSPACE"/{build,chroot}
cd "$WORKSPACE/build"

# Install dependencies
echo "Installing build dependencies..."
apt-get update
apt-get install -y debootstrap wget \
    build-essential autoconf automake libtool gawk \
    libblkid-dev uuid-dev libudev-dev libssl-dev zlib1g-dev \
    libaio-dev libattr1-dev libelf-dev python3 python3-dev \
    python3-setuptools python3-cffi libffi-dev python3-packaging \
    debhelper dh-python po-debconf \
    linux-headers-$(uname -r) || true

# Step 2: Build ZFS
echo -e "\n${GREEN}Step 2: Building ZFS ${ZFS_VERSION}...${NC}"

# Download if needed
if [ ! -f "zfs-${ZFS_VERSION}.tar.gz" ]; then
    wget --progress=bar:force \
        "https://github.com/openzfs/zfs/releases/download/zfs-${ZFS_VERSION}/zfs-${ZFS_VERSION}.tar.gz"
fi

# Extract and build
rm -rf "zfs-${ZFS_VERSION}"
tar -xzf "zfs-${ZFS_VERSION}.tar.gz"
cd "zfs-${ZFS_VERSION}"

echo "Configuring..."
sh autogen.sh
./configure \
    --with-linux=/usr/src/linux-headers-$(uname -r) \
    --with-linux-obj=/usr/src/linux-headers-$(uname -r) \
    --enable-systemd \
    --enable-pyzfs

echo "Building (this will take 10-20 minutes)..."
make -j$(nproc)

echo "Creating packages..."
make deb-utils deb-dkms || make deb-utils

# Collect packages
mkdir -p /opt/github/Z-FORGE/prebuilt_packages
find . -name "*.deb" -exec cp {} /opt/github/Z-FORGE/prebuilt_packages/ \;

# Step 3: Bootstrap chroot
echo -e "\n${GREEN}Step 3: Bootstrapping Debian chroot...${NC}"
cd "$WORKSPACE"

if [ -d "chroot" ] && [ "$(ls -A chroot)" ]; then
    echo "Chroot already exists. Skipping bootstrap."
else
    debootstrap --arch=amd64 \
                --include=systemd,systemd-sysv,apt,bash \
                trixie chroot http://deb.debian.org/debian
fi

# Step 4: Install ZFS in chroot
echo -e "\n${GREEN}Step 4: Installing ZFS in chroot...${NC}"

# Setup chroot
cat > chroot/etc/apt/sources.list << EOF
deb http://deb.debian.org/debian trixie main contrib non-free non-free-firmware
deb http://security.debian.org/debian-security trixie-security main contrib non-free non-free-firmware
EOF

cp /etc/resolv.conf chroot/etc/resolv.conf

# Copy packages
mkdir -p chroot/tmp/zfs-packages
cp /opt/github/Z-FORGE/prebuilt_packages/*.deb chroot/tmp/zfs-packages/

# Mount and install
mount -t proc proc chroot/proc
mount -t sysfs sys chroot/sys
mount -o bind /dev chroot/dev
mount -t devpts devpts chroot/dev/pts

chroot chroot /bin/bash -c '
    apt-get update
    cd /tmp/zfs-packages
    dpkg -i *.deb || apt-get install -f -y
    rm -rf /tmp/zfs-packages
'

# Unmount
umount chroot/{dev/pts,dev,sys,proc} || true

# Step 5: Summary
echo -e "\n${GREEN}════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ ZFS Bootstrap Complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Workspace: $WORKSPACE"
echo "Packages: /opt/github/Z-FORGE/prebuilt_packages/"
echo "Chroot: $WORKSPACE/chroot"
echo ""
echo "To use with Z-FORGE:"
echo "  export CHROOT_PATH=$WORKSPACE/chroot"
echo "  cd /opt/github/Z-FORGE"
echo "  make build"
echo ""
echo "To test chroot:"
echo "  sudo chroot $WORKSPACE/chroot /bin/bash"
echo "  # Inside chroot: zfs version"
echo ""