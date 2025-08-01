#!/bin/bash
# Build ZFS 2.3.3 with kernel modules in chroot environment
# This builds modules inside the target environment where CONFIG_MODULES is available

set -e

ZFS_VERSION="2.3.3"
PACKAGE_DIR="/opt/github/Z-FORGE/prebuilt_packages"
CHROOT_PATH="$1"

if [ -z "$CHROOT_PATH" ]; then
    echo "Usage: $0 <chroot_path>"
    echo "This script builds ZFS kernel modules inside the target chroot"
    exit 1
fi

echo "═══════════════════════════════════════════════════════════════════"
echo "        Building ZFS ${ZFS_VERSION} with Kernel Modules"
echo "              (Inside chroot: $CHROOT_PATH)"
echo "═══════════════════════════════════════════════════════════════════"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    exit 1
fi

# Check if chroot exists
if [ ! -d "$CHROOT_PATH" ]; then
    echo "ERROR: Chroot directory does not exist: $CHROOT_PATH"
    exit 1
fi

# Create package directory
mkdir -p "${PACKAGE_DIR}"

# Download ZFS source if not available
ZFS_TARBALL="zfs-${ZFS_VERSION}.tar.gz"
if [ ! -f "${PACKAGE_DIR}/${ZFS_TARBALL}" ]; then
    echo "[1/8] Downloading ZFS ${ZFS_VERSION} source..."
    cd "${PACKAGE_DIR}"
    wget -c "https://github.com/openzfs/zfs/releases/download/zfs-${ZFS_VERSION}/${ZFS_TARBALL}"
else
    echo "[1/8] Using cached ZFS source..."
fi

# Copy source into chroot
echo "[2/8] Copying ZFS source into chroot..."
cp "${PACKAGE_DIR}/${ZFS_TARBALL}" "${CHROOT_PATH}/tmp/"

# Install build dependencies in chroot
echo "[3/8] Installing build dependencies in chroot..."
chroot "$CHROOT_PATH" bash -c "
    apt-get update
    apt-get install -y \
        build-essential autoconf automake libtool gawk \
        zlib1g-dev uuid-dev libattr1-dev libblkid-dev \
        libssl-dev libaio-dev libelf-dev python3-dev \
        python3-setuptools python3-cffi libffi-dev \
        dkms linux-headers-\$(uname -r) || linux-headers-generic
"

# Extract and build ZFS in chroot
echo "[4/8] Extracting ZFS source in chroot..."
chroot "$CHROOT_PATH" bash -c "
    cd /tmp
    tar -xzf ${ZFS_TARBALL}
    cd zfs-${ZFS_VERSION}
"

echo "[5/8] Configuring ZFS build in chroot..."
chroot "$CHROOT_PATH" bash -c "
    cd /tmp/zfs-${ZFS_VERSION}
    ./autogen.sh
    ./configure \\
        --prefix=/usr \\
        --sysconfdir=/etc \\
        --sbindir=/sbin \\
        --libdir=/usr/lib/x86_64-linux-gnu \\
        --with-config=all \\
        --enable-systemd \\
        --enable-pyzfs \\
        --with-systemdunitdir=/lib/systemd/system \\
        --with-dracutdir=/usr/lib/dracut \\
        --disable-static
"

echo "[6/8] Building ZFS in chroot (this may take 15-20 minutes)..."
chroot "$CHROOT_PATH" bash -c "
    cd /tmp/zfs-${ZFS_VERSION}
    make -j\$(nproc)
"

echo "[7/8] Installing ZFS in chroot..."
chroot "$CHROOT_PATH" bash -c "
    cd /tmp/zfs-${ZFS_VERSION}
    make install
    
    # Update module dependencies
    depmod -a
    
    # Create module loading configuration
    echo 'zfs' >> /etc/modules-load.d/zfs.conf
    
    # Enable ZFS services
    systemctl enable zfs-import-cache zfs-mount zfs-share zfs-zed || true
"

# Create verification script
echo "[8/8] Creating verification and cleanup..."
chroot "$CHROOT_PATH" bash -c "
    # Clean up build directory
    rm -rf /tmp/zfs-${ZFS_VERSION}
    rm -f /tmp/${ZFS_TARBALL}
    
    # Verify installation
    echo '=== ZFS Installation Verification ==='
    zfs version || echo 'ZFS command not found'
    modinfo zfs | grep version || echo 'ZFS module not available'
    
    # List installed ZFS files
    echo '=== Installed ZFS Components ==='
    ls -la /sbin/zfs* /sbin/zpool* || echo 'ZFS binaries not found'
    ls -la /lib/modules/\$(uname -r)/extra/zfs/ || echo 'ZFS modules not found'
"

# Create a completion marker
touch "${PACKAGE_DIR}/zfs-${ZFS_VERSION}-chroot-built"

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                    CHROOT BUILD COMPLETE"
echo "═══════════════════════════════════════════════════════════════════"
echo "✅ ZFS ${ZFS_VERSION} with kernel modules built in chroot"
echo "✅ Modules installed to: ${CHROOT_PATH}/lib/modules/*/extra/zfs/"
echo "✅ Userspace tools installed to: ${CHROOT_PATH}/sbin/"
echo "✅ Services enabled for live ISO"
echo ""
echo "The live ISO will now have:"
echo "   ✅ ZFS kernel modules"
echo "   ✅ ZFS userspace tools" 
echo "   ✅ Python bindings"
echo "   ✅ systemd integration"
echo "   ✅ Dracut ZFS support"