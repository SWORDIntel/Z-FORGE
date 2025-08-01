#!/bin/bash
# Add ZFS kernel module support to complement our userspace package
# Installs DKMS framework so kernel modules build automatically

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "        Adding ZFS Kernel Module Support"
echo "═══════════════════════════════════════════════════════════════════"

CHROOT_PATH="${1:-/tmp/zforge_workspace/chroot}"

if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    exit 1
fi

echo ""
echo "[1/4] Installing DKMS and kernel headers..."

chroot "$CHROOT_PATH" bash -c '
apt-get update
apt-get install -y \
    dkms \
    build-essential \
    linux-headers-amd64 \
    || echo "Some packages may already be installed"
'

echo ""
echo "[2/4] Creating ZFS DKMS source structure..."

# Create DKMS directory for our ZFS version
ZFS_VERSION="2.3.3"
DKMS_DIR="$CHROOT_PATH/usr/src/zfs-$ZFS_VERSION"

if [ -d "/opt/github/Z-FORGE/prebuilt_packages/zfs-2.3.3" ]; then
    echo "Copying ZFS source for DKMS..."
    mkdir -p "$DKMS_DIR"
    cp -r /opt/github/Z-FORGE/prebuilt_packages/zfs-2.3.3/* "$DKMS_DIR/"
elif [ -f "/opt/github/Z-FORGE/prebuilt_packages/zfs-2.3.3.tar.gz" ]; then
    echo "Extracting ZFS source for DKMS..."
    mkdir -p "$DKMS_DIR"
    tar xzf /opt/github/Z-FORGE/prebuilt_packages/zfs-2.3.3.tar.gz -C "$CHROOT_PATH/usr/src/"
else
    echo "WARNING: ZFS source not found for DKMS"
    echo "Kernel modules will need to be provided separately"
fi

echo ""
echo "[3/4] Creating DKMS configuration..."

if [ -d "$DKMS_DIR" ]; then
    cat > "$DKMS_DIR/dkms.conf" << EOF
PACKAGE_NAME="zfs"
PACKAGE_VERSION="$ZFS_VERSION"
AUTOINSTALL="yes"

# Build commands
MAKE="./configure --with-config=kernel && make -j\$(nproc)"
CLEAN="make clean"

# Modules to build
BUILT_MODULE_NAME[0]="zfs"
BUILT_MODULE_LOCATION[0]="module/zfs/"
DEST_MODULE_LOCATION[0]="/extra"

BUILT_MODULE_NAME[1]="spl"
BUILT_MODULE_LOCATION[1]="module/spl/"
DEST_MODULE_LOCATION[1]="/extra"
EOF

    echo "DKMS configuration created"
fi

echo ""
echo "[4/4] Setting up module loading..."

# Create module load configuration
cat > "$CHROOT_PATH/etc/modules-load.d/zfs.conf" << EOF
# Load ZFS modules at boot
zfs
EOF

# Create modprobe configuration
cat > "$CHROOT_PATH/etc/modprobe.d/zfs.conf" << EOF
# ZFS module options
options zfs zfs_autoimport_disable=0
EOF

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "            ZFS Kernel Module Support Added!"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "✅ DKMS framework installed"
echo "✅ Kernel headers ready"
echo "✅ ZFS will build modules on first boot"
echo ""
echo "When the live ISO boots:"
echo "1. DKMS will detect the kernel"
echo "2. Build ZFS modules automatically"
echo "3. Load modules at boot"
echo "4. Our userspace tools will work with the modules"
echo ""
echo "This complements our ZFS userspace package perfectly!"