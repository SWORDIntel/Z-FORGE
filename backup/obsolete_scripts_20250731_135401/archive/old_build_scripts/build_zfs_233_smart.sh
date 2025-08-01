#!/bin/bash
# Smart ZFS 2.3.3 Builder - Detects kernel capabilities and adapts
# Handles CONFIG_MODULES issue intelligently

set -e

ZFS_VERSION="2.3.3"
BUILD_DIR="/usr/src"
PACKAGE_DIR="/opt/github/Z-FORGE/prebuilt_packages"
ZFS_SOURCE_DIR="${BUILD_DIR}/zfs-${ZFS_VERSION}"

echo "═══════════════════════════════════════════════════════════════════"
echo "              Smart ZFS ${ZFS_VERSION} Builder"
echo "       Detects kernel capabilities and builds appropriately"
echo "═══════════════════════════════════════════════════════════════════"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    exit 1
fi

# Function to detect kernel configuration
detect_kernel_config() {
    echo "[INFO] Detecting kernel configuration..."
    
    # Check if we have access to kernel config
    if [ -f "/proc/config.gz" ]; then
        CONFIG_MODULES=$(zcat /proc/config.gz | grep "CONFIG_MODULES=" | cut -d= -f2)
    elif [ -f "/lib/modules/$(uname -r)/config" ]; then
        CONFIG_MODULES=$(grep "CONFIG_MODULES=" /lib/modules/$(uname -r)/config | cut -d= -f2)
    elif [ -f "/boot/config-$(uname -r)" ]; then
        CONFIG_MODULES=$(grep "CONFIG_MODULES=" /boot/config-$(uname -r) | cut -d= -f2)
    else
        echo "[WARNING] Cannot detect kernel config - assuming no module support"
        CONFIG_MODULES="n"
    fi
    
    echo "[INFO] CONFIG_MODULES=${CONFIG_MODULES:-n}"
    
    # Check if kernel headers are available
    if [ -d "/lib/modules/$(uname -r)/build" ]; then
        KERNEL_HEADERS="yes"
        echo "[INFO] Kernel headers available at /lib/modules/$(uname -r)/build"
    else
        KERNEL_HEADERS="no"
        echo "[WARNING] Kernel headers not available"
    fi
}

# Function to build with kernel modules
build_with_modules() {
    echo "[INFO] Building ZFS with kernel module support..."
    
    # Install full dependencies including kernel headers
    apt-get install -y \
        build-essential autoconf automake libtool gawk \
        zlib1g-dev uuid-dev libattr1-dev libblkid-dev \
        libssl-dev libaio-dev libelf-dev python3-dev \
        python3-setuptools python3-cffi libffi-dev \
        dkms linux-headers-$(uname -r) || {
        echo "[WARNING] Failed to install kernel headers, falling back to userspace"
        build_userspace_only
        return
    }
    
    # Configure with full kernel support
    ./configure \
        --prefix=/usr \
        --sysconfdir=/etc \
        --sbindir=/sbin \
        --libdir=/usr/lib/x86_64-linux-gnu \
        --with-config=all \
        --enable-systemd \
        --enable-pyzfs \
        --with-systemdunitdir=/lib/systemd/system \
        --with-dracutdir=/usr/lib/dracut \
        --disable-static
        
    BUILD_TYPE="full"
}

# Function to build userspace only
build_userspace_only() {
    echo "[INFO] Building ZFS userspace tools only (no kernel modules)..."
    
    # Install minimal dependencies
    apt-get install -y \
        build-essential autoconf automake libtool gawk \
        zlib1g-dev uuid-dev libattr1-dev libblkid-dev \
        libssl-dev libaio-dev libelf-dev python3-dev \
        python3-setuptools python3-cffi libffi-dev
    
    # Configure for userspace only
    ./configure \
        --prefix=/usr \
        --sysconfdir=/etc \
        --sbindir=/sbin \
        --libdir=/usr/lib/x86_64-linux-gnu \
        --with-config=user \
        --enable-systemd \
        --enable-pyzfs \
        --with-systemdunitdir=/lib/systemd/system \
        --disable-static
        
    BUILD_TYPE="userspace"
}

# Main build process
main() {
    # Create package directory
    mkdir -p "${PACKAGE_DIR}"
    
    # Clean previous attempts
    echo "[1/8] Cleaning previous build attempts..."
    cd "${BUILD_DIR}"
    if [ -d "${ZFS_SOURCE_DIR}" ]; then
        rm -rf "${ZFS_SOURCE_DIR}"
    fi
    
    # Download source if not cached
    ZFS_TARBALL="zfs-${ZFS_VERSION}.tar.gz"
    if [ ! -f "${BUILD_DIR}/${ZFS_TARBALL}" ]; then
        echo "[2/8] Downloading ZFS ${ZFS_VERSION} source..."
        wget -c "https://github.com/openzfs/zfs/releases/download/zfs-${ZFS_VERSION}/${ZFS_TARBALL}"
    else
        echo "[2/8] Using cached ZFS source..."
    fi
    
    # Extract source
    echo "[3/8] Extracting ZFS source..."
    tar -xzf "${ZFS_TARBALL}"
    cd "${ZFS_SOURCE_DIR}"
    
    # Detect kernel capabilities
    echo "[4/8] Detecting kernel capabilities..."
    detect_kernel_config
    
    # Install dependencies and configure based on kernel capabilities
    echo "[5/8] Installing dependencies and configuring build..."
    apt-get update
    
    if [ "$CONFIG_MODULES" = "y" ] && [ "$KERNEL_HEADERS" = "yes" ]; then
        echo "[INFO] Kernel supports modules and headers available - building full ZFS"
        build_with_modules
    else
        echo "[INFO] Kernel doesn't support modules or headers missing - building userspace only"
        build_userspace_only
    fi
    
    # Prepare build
    echo "[6/8] Preparing build environment..."
    ./autogen.sh
    
    # Build
    echo "[7/8] Building ZFS (type: $BUILD_TYPE)..."
    make -j$(nproc)
    
    # Create package
    echo "[8/8] Creating package..."
    TEMP_INSTALL="/tmp/zfs-${ZFS_VERSION}-${BUILD_TYPE}"
    mkdir -p "${TEMP_INSTALL}"
    
    # Install to temporary location
    make install DESTDIR="${TEMP_INSTALL}"
    
    # Create tar.gz package
    cd "${TEMP_INSTALL}"
    tar -czf "${PACKAGE_DIR}/zfs-${ZFS_VERSION}-${BUILD_TYPE}.tar.gz" .
    
    # Create installer script
    cat > "${PACKAGE_DIR}/install_zfs_2_3_3.sh" << EOF
#!/bin/bash
# ZFS 2.3.3 Smart installer for Z-FORGE (Build type: ${BUILD_TYPE})

CHROOT_PATH="\$1"
if [ -z "\$CHROOT_PATH" ]; then
    echo "Usage: \$0 <chroot_path>"
    exit 1
fi

echo "Installing ZFS 2.3.3 (${BUILD_TYPE}) to chroot: \$CHROOT_PATH"

# Extract package to chroot
cd "\$CHROOT_PATH"
tar -xzf /opt/github/Z-FORGE/prebuilt_packages/zfs-${ZFS_VERSION}-${BUILD_TYPE}.tar.gz

# Install Python modules in chroot
chroot "\$CHROOT_PATH" python3 -m pip install pyzfs || true

# Enable services
chroot "\$CHROOT_PATH" systemctl enable zfs-import-cache zfs-mount zfs-share zfs-zed || true

echo "✅ ZFS 2.3.3 (${BUILD_TYPE}) installation complete"
if [ "${BUILD_TYPE}" = "userspace" ]; then
    echo "⚠️  Note: Userspace only - kernel modules handled separately"
fi
EOF
    
    chmod +x "${PACKAGE_DIR}/install_zfs_2_3_3.sh"
    
    # Clean up
    rm -rf "${TEMP_INSTALL}"
    
    # Final report
    echo ""
    echo "═══════════════════════════════════════════════════════════════════"
    echo "                    SMART BUILD COMPLETE"
    echo "═══════════════════════════════════════════════════════════════════"
    echo "✅ ZFS ${ZFS_VERSION} package created (type: ${BUILD_TYPE}):"
    echo "   📦 ${PACKAGE_DIR}/zfs-${ZFS_VERSION}-${BUILD_TYPE}.tar.gz"
    echo "   🔧 ${PACKAGE_DIR}/install_zfs_2_3_3.sh"
    echo ""
    echo "Package size: $(du -h "${PACKAGE_DIR}/zfs-${ZFS_VERSION}-${BUILD_TYPE}.tar.gz" | cut -f1)"
    echo ""
    echo "Build includes:"
    if [ "${BUILD_TYPE}" = "full" ]; then
        echo "   ✅ ZFS userspace tools"
        echo "   ✅ ZFS kernel modules"
        echo "   ✅ DKMS support"
        echo "   ✅ Python bindings"
    else
        echo "   ✅ ZFS userspace tools"
        echo "   ✅ Python bindings"
        echo "   ❌ No kernel modules (CONFIG_MODULES not available)"
    fi
}

# Run main function
main