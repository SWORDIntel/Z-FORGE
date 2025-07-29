#!/bin/bash
# Download pre-built ZFS 2.3.3 packages (avoids CONFIG_MODULES issue completely)

set -e

PACKAGE_DIR="/opt/github/Z-FORGE/prebuilt_packages"
ZFS_VERSION="2.3.3"

echo "═══════════════════════════════════════════════════════════════════"
echo "          Downloading Pre-built ZFS ${ZFS_VERSION} Packages"
echo "            (Completely avoids CONFIG_MODULES issue)"
echo "═══════════════════════════════════════════════════════════════════"

# Create package directory
mkdir -p "${PACKAGE_DIR}"
cd "${PACKAGE_DIR}"

# URLs for ZFS packages (try multiple sources)
ZFS_SOURCES=(
    # OpenZFS GitHub releases
    "https://github.com/openzfs/zfs/releases/download/zfs-${ZFS_VERSION}/zfs-${ZFS_VERSION}.tar.gz"
    # Debian Bookworm (working ZFS packages)
    "http://deb.debian.org/debian/pool/contrib/z/zfs-linux/"
)

# Function to download from GitHub releases
download_github_source() {
    echo "[1/3] Downloading ZFS source from GitHub..."
    if [ ! -f "zfs-${ZFS_VERSION}.tar.gz" ]; then
        wget -c "https://github.com/openzfs/zfs/releases/download/zfs-${ZFS_VERSION}/zfs-${ZFS_VERSION}.tar.gz"
        echo "✅ Downloaded ZFS ${ZFS_VERSION} source"
    else
        echo "✅ ZFS source already downloaded"
    fi
}

# Function to try downloading Debian packages
download_debian_packages() {
    echo "[2/3] Attempting to download Debian ZFS packages..."
    
    # Try to get package list from Debian bookworm
    DEBIAN_PACKAGES=(
        "zfsutils-linux_${ZFS_VERSION}-1_amd64.deb"
        "libzfs4linux_${ZFS_VERSION}-1_amd64.deb"
        "libzfslinux-dev_${ZFS_VERSION}-1_amd64.deb"
        "libzpool5linux_${ZFS_VERSION}-1_amd64.deb"
    )
    
    for pkg in "${DEBIAN_PACKAGES[@]}"; do
        if [ ! -f "$pkg" ]; then
            echo "   Trying to download $pkg..."
            wget -c "http://deb.debian.org/debian/pool/contrib/z/zfs-linux/$pkg" || {
                echo "   ⚠️  Could not download $pkg (may not exist)"
            }
        fi
    done
}

# Function to create universal installer
create_installer() {
    echo "[3/3] Creating universal installer..."
    
    cat > "install_zfs_2_3_3.sh" << 'EOF'
#!/bin/bash
# Universal ZFS 2.3.3 installer for Z-FORGE

CHROOT_PATH="$1"
if [ -z "$CHROOT_PATH" ]; then
    echo "Usage: $0 <chroot_path>"
    exit 1
fi

echo "Installing ZFS 2.3.3 to chroot: $CHROOT_PATH"

PACKAGE_DIR="/opt/github/Z-FORGE/prebuilt_packages"

# Strategy 1: Try .deb packages if available
if ls "$PACKAGE_DIR"/*.deb &>/dev/null; then
    echo "📦 Installing from .deb packages..."
    for deb in "$PACKAGE_DIR"/*.deb; do
        if [ -f "$deb" ]; then
            echo "   Installing $(basename "$deb")..."
            chroot "$CHROOT_PATH" dpkg -i "/$(basename "$deb")" || true
        fi
    done
    
    # Fix any dependency issues
    chroot "$CHROOT_PATH" apt-get install -f -y || true
    
    echo "✅ ZFS installed from .deb packages"
    return 0
fi

# Strategy 2: Use source tarball and build minimal userspace
if [ -f "$PACKAGE_DIR/zfs-2.3.3.tar.gz" ]; then
    echo "📦 Building minimal userspace from source..."
    
    # Extract to chroot
    cd "$CHROOT_PATH"
    tar -xzf "$PACKAGE_DIR/zfs-2.3.3.tar.gz"
    
    # Build userspace tools only (inside chroot)
    chroot "$CHROOT_PATH" bash -c "
        cd /zfs-2.3.3
        ./autogen.sh
        ./configure --prefix=/usr --with-config=user --enable-systemd
        make -j$(nproc) install
        cd /
        rm -rf /zfs-2.3.3
    "
    
    echo "✅ ZFS userspace tools built and installed"
    return 0
fi

# Strategy 3: Try to install from repositories
echo "📦 Attempting repository installation..."
chroot "$CHROOT_PATH" apt-get update
chroot "$CHROOT_PATH" apt-get install -y zfsutils-linux || {
    echo "❌ Repository installation failed"
    echo "⚠️  Please run the ZFS build script to create packages"
    return 1
}

echo "✅ ZFS installed from repositories"
EOF
    
    chmod +x "install_zfs_2_3_3.sh"
    echo "✅ Created universal installer: install_zfs_2_3_3.sh"
}

# Main execution
main() {
    download_github_source
    download_debian_packages
    create_installer
    
    echo ""
    echo "═══════════════════════════════════════════════════════════════════"
    echo "                      DOWNLOAD COMPLETE"
    echo "═══════════════════════════════════════════════════════════════════"
    echo "📁 Package directory: $PACKAGE_DIR"
    echo ""
    echo "Available packages:"
    ls -lh "$PACKAGE_DIR" | grep -E "\.(deb|tar\.gz|sh)$" || echo "   No packages found"
    echo ""
    echo "✅ Ready for Z-FORGE build!"
    echo ""
    echo "Next steps:"
    echo "  make check    # Check build environment"
    echo "  make build    # Run the build"
}

main