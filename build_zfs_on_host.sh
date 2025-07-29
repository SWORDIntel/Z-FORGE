#!/bin/bash
# Build ZFS from OpenZFS GitHub source in the Linux source directory on the host system
# Then copy the built packages to Z-FORGE directory

set -e

echo "════════════════════════════════════════════════════════════════════"
echo "    Z-FORGE ZFS Host Builder - Build from OpenZFS GitHub"
echo "════════════════════════════════════════════════════════════════════"
echo ""

# Configuration
ZFS_VERSION="2.3.3"
ZFS_URL="https://github.com/openzfs/zfs/releases/download/zfs-${ZFS_VERSION}/zfs-${ZFS_VERSION}.tar.gz"
SUDO_PASS="1786"

# Output directory for built packages
OUTPUT_DIR="/opt/github/Z-FORGE/prebuilt_packages"
mkdir -p "$OUTPUT_DIR"

# Create the main build script that will run with sudo
cat > /tmp/zfs_build_main.sh << 'BUILDSCRIPT'
#!/bin/bash
set -e

ZFS_VERSION="2.3.3"
ZFS_URL="https://github.com/openzfs/zfs/releases/download/zfs-${ZFS_VERSION}/zfs-${ZFS_VERSION}.tar.gz"
OUTPUT_DIR="/opt/github/Z-FORGE/prebuilt_packages"

# Function to find Linux source directory
find_linux_src() {
    echo "🔍 Finding Linux source directory..."
    
    # Check common locations
    for dir in /usr/src/linux* /lib/modules/$(uname -r)/build; do
        if [ -d "$dir" ] && [ -f "$dir/Makefile" ]; then
            echo "✅ Found Linux source at: $dir"
            echo "$dir"
            return 0
        fi
    done
    
    echo "❌ No Linux source directory found"
    echo "   Please install kernel headers: sudo apt-get install linux-headers-$(uname -r)"
    return 1
}

# Find Linux source directory
LINUX_SRC=$(find_linux_src)
if [ -z "$LINUX_SRC" ]; then
    exit 1
fi

# Create work directory in Linux source
WORK_DIR="$LINUX_SRC/zfs-build"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

echo ""
echo "📥 Downloading ZFS ${ZFS_VERSION} from OpenZFS GitHub..."

# Download ZFS source
if [ ! -f "zfs-${ZFS_VERSION}.tar.gz" ]; then
    wget -q --show-progress "$ZFS_URL" -O "zfs-${ZFS_VERSION}.tar.gz"
    echo "✅ Downloaded ZFS source"
else
    echo "✅ Using existing ZFS source tarball"
fi

# Extract source
echo "📦 Extracting ZFS source..."
tar -xzf "zfs-${ZFS_VERSION}.tar.gz"
cd "zfs-${ZFS_VERSION}"

# Install build dependencies
echo ""
echo "📚 Installing build dependencies..."
apt-get update -qq
apt-get install -y -qq \
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
    python3 \
    python3-dev \
    python3-setuptools \
    python3-cffi \
    libffi-dev \
    debhelper \
    dh-python \
    po-debconf \
    python3-all-dev \
    python3-sphinx \
    checkinstall

# Run autogen
echo ""
echo "🔧 Running autogen.sh..."
./autogen.sh

# Configure with Linux source
echo ""
echo "⚙️  Configuring ZFS build with Linux source at: $LINUX_SRC"
./configure \
    --with-linux="$LINUX_SRC" \
    --with-linux-obj="$LINUX_SRC" \
    --prefix=/usr \
    --sysconfdir=/etc \
    --localstatedir=/var \
    --libdir=/usr/lib/x86_64-linux-gnu \
    --includedir=/usr/include \
    --with-config=all \
    --enable-systemd \
    --enable-pyzfs

# Build
echo ""
echo "🔨 Building ZFS (this will take a while)..."
make -j$(nproc)

# Build Debian packages
echo ""
echo "📦 Building Debian packages..."

# Try to build all packages
echo "Building userspace packages..."
make deb-utils || echo "⚠️  deb-utils failed, trying alternative method"

echo "Building kernel module packages..."
make deb-kmod || echo "⚠️  deb-kmod failed, trying alternative method"

# Alternative: use dpkg-buildpackage if make deb failed
cd ..
if [ ! -f *.deb ] 2>/dev/null; then
    echo "Trying dpkg-buildpackage..."
    cd "zfs-${ZFS_VERSION}"
    dpkg-buildpackage -b -uc -us || true
    cd ..
fi

# Alternative: manual package creation
if [ ! -f *.deb ] 2>/dev/null; then
    echo "Creating packages manually..."
    cd "zfs-${ZFS_VERSION}"
    
    # Install to a staging directory
    make install DESTDIR="$WORK_DIR/staging"
    
    # Create debian package structure
    cd "$WORK_DIR"
    mkdir -p zfs-manual_{$ZFS_VERSION}/DEBIAN
    mkdir -p zfs-manual_{$ZFS_VERSION}/usr
    
    # Copy files
    cp -r staging/usr/* zfs-manual_{$ZFS_VERSION}/usr/
    
    # Create control file
    cat > zfs-manual_{$ZFS_VERSION}/DEBIAN/control << EOF
Package: zfs-manual
Version: $ZFS_VERSION
Architecture: amd64
Maintainer: Z-FORGE
Description: Manually packaged ZFS from source
 Built from OpenZFS source in Linux kernel tree
EOF
    
    # Build the package
    dpkg-deb --build zfs-manual_{$ZFS_VERSION}
    mv zfs-manual_{$ZFS_VERSION}.deb zfs-manual_${ZFS_VERSION}_amd64.deb
fi

# Collect packages
echo ""
echo "📦 Collecting built packages..."

# Find all .deb files
PACKAGES=$(find . -maxdepth 2 -name "*.deb" -type f)
if [ -z "$PACKAGES" ]; then
    echo "❌ No packages were built"
    exit 1
fi

# Copy packages to Z-FORGE directory
echo ""
echo "📋 Copying packages to Z-FORGE..."
mkdir -p "$OUTPUT_DIR"
for pkg in $PACKAGES; do
    if [ -f "$pkg" ]; then
        pkg_name=$(basename "$pkg")
        cp "$pkg" "$OUTPUT_DIR/"
        echo "✅ Copied: $pkg_name"
    fi
done

# Create installer script
echo ""
echo "📝 Creating installer script..."
cat > "$OUTPUT_DIR/install_zfs_host_built.sh" << 'EOF'
#!/bin/bash
# Install ZFS packages built on host system

set -e

CHROOT_PATH="${1:-/tmp/zforge_workspace/chroot}"
PACKAGES_DIR="$(dirname "$0")"

echo "Installing host-built ZFS packages to $CHROOT_PATH"

# Check if chroot exists
if [ ! -d "$CHROOT_PATH" ]; then
    echo "Error: Chroot directory not found: $CHROOT_PATH"
    exit 1
fi

# Copy packages to chroot
echo "Copying packages to chroot..."
mkdir -p "$CHROOT_PATH/tmp/zfs-packages"
cp "$PACKAGES_DIR"/*.deb "$CHROOT_PATH/tmp/zfs-packages/" 2>/dev/null || true

# Install packages in chroot
echo "Installing ZFS packages..."
chroot "$CHROOT_PATH" /bin/bash -c "
    cd /tmp/zfs-packages
    
    # Install all packages
    dpkg -i *.deb || apt-get install -f -y
    
    # Enable ZFS services
    systemctl enable zfs-import-cache || true
    systemctl enable zfs-mount || true
    systemctl enable zfs-import.target || true
    
    # Update initramfs
    update-initramfs -u || true
    
    # Clean up
    rm -rf /tmp/zfs-packages
"

echo "Host-built ZFS packages installed successfully!"
EOF

chmod +x "$OUTPUT_DIR/install_zfs_host_built.sh"

# Clean up build directory
echo ""
echo "🧹 Cleaning up build directory..."
cd /
rm -rf "$WORK_DIR"

# Summary
echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "✅ ZFS Build Complete!"
echo "════════════════════════════════════════════════════════════════════"
echo ""
echo "📦 Packages location: $OUTPUT_DIR"
echo "🔧 Installer script: $OUTPUT_DIR/install_zfs_host_built.sh"
echo ""
echo "Number of packages built: $(ls -1 $OUTPUT_DIR/*.deb 2>/dev/null | wc -l)"
echo ""
BUILDSCRIPT

chmod +x /tmp/zfs_build_main.sh

# Run the build script with sudo
echo "Running build script with sudo..."
echo "$SUDO_PASS" | sudo -S bash /tmp/zfs_build_main.sh

# Clean up
rm -f /tmp/zfs_build_main.sh

echo "To use in Z-FORGE build:"
echo "  The build system will automatically detect and use these packages"
echo ""
echo "To manually install:"
echo "  $OUTPUT_DIR/install_zfs_host_built.sh [chroot_path]"
echo ""